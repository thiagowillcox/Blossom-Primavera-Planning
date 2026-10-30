"""Offline review summary. This is not an Oracle REST request payload."""
import hashlib
import json
from collections import Counter,defaultdict
from decimal import Decimal,DecimalException
from pathlib import Path
import openpyxl
from zipfile import BadZipFile
from ..validation import topology
from .client import SERVER,ConnectionFailure


def amount(value, *, signed=False):
    try:result=Decimal(str(value))
    except DecimalException:
        raise ConnectionFailure('O Excel contém um valor numérico não reconhecido.') from None
    if not result.is_finite() or (not signed and result<0):
        raise ConnectionFailure('O Excel contém um valor negativo ou não finito.')
    return result


def prepare_preview(workbook_path, selection_path, destination):
    selection=json.loads(Path(selection_path).read_text(encoding='utf-8'))
    project=selection.get('projeto_selecionado',{})
    if selection.get('servidor')!=SERVER or type(project.get('projectId')) is not int or project['projectId']<=0:
        raise ConnectionFailure('Seleção local de projeto inválida. Execute Listar_Projetos_Primavera.bat primeiro.')
    path=Path(workbook_path)
    try:workbook=openpyxl.load_workbook(path,read_only=True,data_only=True)
    except (BadZipFile,openpyxl.utils.exceptions.InvalidFileException):
        raise ConnectionFailure('O arquivo não é uma planilha Excel compatível.') from None
    required={'WBS','Atividades','Atribuicoes_Funcoes','Relacionamentos','Matriz_Regras','Parametros','Pendencias','Auditoria_HH'}
    try:
        if not required.issubset(workbook.sheetnames):
            raise ConnectionFailure('Escolha o pré-cronograma Excel gerado pelo Blossom Planning, não a LD.')
        tables={}
        for name in required:
            values=workbook[name].values
            header=next(values,())
            tables[name]=[dict(zip(header,row)) for row in values if any(v is not None for v in row)]
    finally:workbook.close()
    activities=tables['Atividades']
    if any('tipo_linha' in a for a in activities):
        activities=[a for a in activities if a['tipo_linha']=='atividade']
    if not activities or not all(a.get('id') and a.get('etapa') in (0,1,2,3,4) for a in activities):
        raise ConnectionFailure('A aba Atividades não possui o formato esperado pelo Blossom Planning.')
    topology(activities,tables['Relacionamentos'])
    topology(tables['WBS'],[{'predecessora':w['pai'],'sucessora':w['id']} for w in tables['WBS'] if w.get('pai')])
    ids={a['id'] for a in activities};wbs_ids={w['id'] for w in tables['WBS']}
    if any(a.get('wbs_id') not in wbs_ids for a in activities):raise ConnectionFailure('Atividade sem WBS válida.')
    totals=defaultdict(Decimal)
    for row in tables['Atribuicoes_Funcoes']:
        if row.get('atividade_id') not in ids:raise ConnectionFailure('Atribuição sem atividade válida.')
        totals[row['atividade_id']]+=amount(row['hh'])
    if any(abs(totals[a['id']] - amount(a['hh'])) > Decimal('.000001') for a in activities):
        raise ConnectionFailure('HH das atribuições divergem das atividades; gere e confira o Excel novamente.')
    if any(abs(amount(row['diferenca'],signed=True)) > Decimal('.000001') for row in tables['Auditoria_HH']):
        raise ConnectionFailure('A auditoria do Excel apresenta divergências de HH.')
    pending=Counter(row['codigo'] for row in tables['Pendencias'])
    missing_duration=sum(a.get('duracao_dias') is None for a in activities)
    for activity in activities:
        if activity.get('duracao_dias') is not None:amount(activity['duracao_dias'])
    technical=sum(bool(a.get('prerequisitos_tecnicos_pendentes')) for a in activities)
    params={r['parametro']:r['valor'] for r in tables['Parametros']}
    report={'tipo':'previa_interna_nao_e_payload_oracle','servidor':SERVER,'projeto_destino':project,
        'envio_implementado':False,'pronto_para_envio':False,
        'contagens':{'wbs':len(tables['WBS']),'atividades':len(activities),
                     'atribuicoes_funcoes':len(tables['Atribuicoes_Funcoes']),
                     'relacionamentos':len(tables['Relacionamentos'])},
        'hh_planejadas':str(sum((amount(a['hh']) for a in activities),Decimal(0))),
        'atividades_sem_duracao':missing_duration,
        'atividades_com_entradas_tecnicas_pendentes':technical if params.get('versao_motor')=='0.5.0' else None,
        'aviso_versao':None if params.get('versao_motor')=='0.5.0' else 'A marcação técnica desta versão não foi confirmada; gere novamente com o motor atual.',
        'pendencias_por_categoria':dict(pending),'origem':{'arquivo':path.name,
         'xlsx_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
         'ld_sha256':params.get('ld_sha256'),'manual_sha256':params.get('manual_sha256')},
        'confirmacoes_necessarias':['Campos e unidades da API Oracle para WBS, atividades e atribuições',
            'Calendário e data-base do projeto Oracle','Mapeamento das funções comerciais para recursos/papéis Oracle',
            'Resolução ou validação das pendências técnicas e durações antes do envio definitivo']}
    target=Path(destination);target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    return report
