"""Role-hours integration bound to an already verified structural upload."""
import hashlib
import html
import json
import urllib.request
from collections import defaultdict
from datetime import datetime,timezone
from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory
import openpyxl
from .client import ReadSession, SERVER, ConnectionFailure, _exchange, _json
from .draft import positive_id, field_equal, durable_write
from .preview import prepare_preview, amount

TOL=Decimal('0.000001')
ROLE_CODES={'Gerente':'BL-GER','ESênior':'BL-ENG-SR','EPleno':'BL-ENG-PL','EJúnior':'BL-ENG-JR',
    'PSênior':'BL-PRJ-SR','PPleno':'BL-PRJ-PL','PJúnior':'BL-PRJ-JR','Desenh.':'BL-DES'}


def load_package(excel, record):
    """Bytes only; no user supplied file paths, credentials or executable config."""
    journal=json.loads(record)
    if (journal.get('servidor')!=SERVER or journal.get('estado')!='estrutura_conferida_prazos_e_hh_pendentes'
        or journal.get('solicitacao_pendente') is not None
        or journal.get('origem',{}).get('xlsx_sha256')!=hashlib.sha256(excel).hexdigest()):
        raise ConnectionFailure('Envie o Excel original e o registro do envio estrutural concluído correspondente.')
    pid=positive_id(journal.get('projectId'))
    with TemporaryDirectory(prefix='blossom-hours-') as name:
        root=Path(name);path=root/'cronograma.xlsx';path.write_bytes(excel)
        selection=root/'selection.json';selection.write_text(json.dumps({'servidor':SERVER,'projeto_selecionado':{'projectId':pid}}))
        report=prepare_preview(path,selection,root/'review.json')
        workbook=openpyxl.load_workbook(path,read_only=True,data_only=True)
        try:
            tables={}
            for key in ('WBS','Atividades','Atribuicoes_Funcoes','Relacionamentos'):
                rows=workbook[key].values;header=next(rows)
                tables[key]=[dict(zip(header,row)) for row in rows if any(v is not None for v in row)]
        finally:workbook.close()
    tables['Atividades']=[a for a in tables['Atividades'] if a.get('tipo_linha','atividade')=='atividade']
    for table,key in [('Atividades','atividades'),('WBS','wbs')]:
        mapping=journal.get(key,{})
        if not isinstance(mapping,dict) or set(mapping)!={a['id'] for a in tables[table]}:
            raise ConnectionFailure('O registro não contém os mesmos IDs da planilha.')
        ids=[positive_id(v) for v in mapping.values()]
        if len(set(ids))!=len(ids):raise ConnectionFailure('IDs Oracle repetidos no registro.')
    seen=set();roles=defaultdict(Decimal)
    for a in tables['Atribuicoes_Funcoes']:
        if not isinstance(a.get('id'),str) or not a['id'] or len(a['id'])>57 or a['id'] in seen:
            raise ConnectionFailure('Identificadores de atribuição inválidos ou repetidos.')
        seen.add(a['id'])
        if amount(a['hh'])<=0:raise ConnectionFailure('Atribuição sem horas positivas.')
        roles[a['funcao']]+=amount(a['hh'])
    if abs(sum(roles.values(),Decimal(0))-amount(report['hh_planejadas']))>TOL:
        raise ConnectionFailure('A soma das horas por função não fecha com o planejamento.')
    return {'projectId':pid,'source_sha256':report['origem']['xlsx_sha256'],'journal':journal,'tables':tables,
        'hh_por_funcao':{k:str(v) for k,v in sorted(roles.items())},'hh_planejadas':report['hh_planejadas'],
        'aviso_versao_tecnica':report['aviso_versao']}


class EffortSession(ReadSession):
    def read(self,path):
        raw=self._get(path,'Consulta de funções e horas',limit=33554432,allow_empty=True)
        return _json(raw,'Consulta de funções e horas') if raw else []

    def rows(self,path):
        result=self.read(path)
        if not isinstance(result,list) or any(not isinstance(r,dict) for r in result):
            raise ConnectionFailure('A consulta de horas não retornou a lista documentada.')
        return result

    def binding(self,package):
        pid=package['projectId'];project=self.read('project/'+str(pid))
        if not isinstance(project,dict) or project.get('projectId')!=pid:
            raise ConnectionFailure('Projeto do registro não encontrado.')
        if not html.unescape(str(project.get('projectName',''))).strip().upper().startswith('TESTE'):
            raise ConnectionFailure('Nesta versão, o envio de horas está limitado a projetos cujo nome começa com TESTE.')
        activities=self.rows('activity/project/'+str(pid))
        by_id={a.get('activityId'):a for a in activities}
        if len(by_id)!=len(activities) or set(by_id)!=set(package['journal']['atividades'].values()):
            raise ConnectionFailure('As atividades do Oracle diferem do registro ou a consulta está incompleta.')
        for a in package['tables']['Atividades']:
            row=by_id[package['journal']['atividades'][a['id']]]
            if (row.get('projectId')!=pid or row.get('activityCode')!=a['id']
                or not field_equal('activityName',row.get('activityName'),a['nome'])
                or row.get('wbsId')!=package['journal']['wbs'][a['wbs_id']]
                or row.get('activityStatus')!='NOT_STARTED'):
                raise ConnectionFailure('Uma atividade foi alterada ou iniciada no Oracle. Confira antes de enviar horas.')
        groups=self.rows('wbs/project/'+str(pid))
        by_wbs={r.get('wbsId'):r for r in groups}
        roots=[r for r in groups if r.get('parentId') in (None,0)]
        if (len(roots)!=1 or len(by_wbs)!=len(groups)
            or set(by_wbs)!=set(package['journal']['wbs'].values())|{roots[0].get('wbsId')}):
            raise ConnectionFailure('A estrutura WBS foi alterada ou a consulta está incompleta.')
        for w in package['tables']['WBS']:
            row=by_wbs[package['journal']['wbs'][w['id']]]
            parent=package['journal']['wbs'][w['pai']] if w.get('pai') else roots[0]['wbsId']
            if row.get('parentId')!=parent or row.get('wbsCode')!=w['codigo'] or not field_equal('wbsName',row.get('wbsName'),w['nome']):
                raise ConnectionFailure('Uma WBS foi alterada desde o envio estrutural.')
        return project

    def catalog(self,package):
        project=self.binding(package);pid=package['projectId']
        assigned=self.rows('resource/projectId/'+str(pid));ids={r.get('resourceId') for r in assigned}
        rows=list(assigned);wid=positive_id(project.get('workspaceId'));visited=set()
        # Follow the documented workspace parent, retaining inherited roles without creating new ones.
        for _ in range(20):
            if wid in visited:raise ConnectionFailure('Hierarquia de workspace circular.')
            visited.add(wid)
            rows+=self.rows('resource/workspace/'+str(wid))
            workspace=self.read('workspace/'+str(wid))
            if not isinstance(workspace,dict) or workspace.get('workspaceId')!=wid:
                raise ConnectionFailure('Não foi possível conferir o workspace das funções.')
            parent=workspace.get('parentId')
            if parent in (None,0):break
            wid=positive_id(parent)
        else:raise ConnectionFailure('A hierarquia de workspaces excedeu o limite de conferência.')
        catalog={}
        for r in rows:
            if r.get('resourceClass')!='ROLE' or r.get('resourceType')!='LABOR' or r.get('resourceStatus')!='ACTIVE':continue
            rid=positive_id(r.get('resourceId'))
            selected={k:r.get(k) for k in ('resourceId','resourceCode','resourceName','resourceClass','resourceType','resourceStatus','workspaceId')}
            if rid in catalog and catalog[rid]!=dict(selected,assigned_to_project=rid in ids):
                raise ConnectionFailure('Cadastro de função inconsistente entre consultas.')
            catalog[rid]=dict(selected,assigned_to_project=rid in ids)
        return project,list(catalog.values())

    def mutation(self,route,payload=None,*,expected=(201,)):
        if not self._token:raise ConnectionFailure('Sessão Oracle encerrada.')
        # Only explicit assignment creates and resource-to-project association are allowed.
        parts=route.split('/')
        associate=(len(parts)==5 and parts[0]=='resource' and parts[2:4]==['assign','project']
            and parts[1].isascii() and parts[1].isdigit() and parts[4].isascii() and parts[4].isdigit())
        if route!='assignment/batch' and not associate:raise ConnectionFailure('Operação de horas não permitida.')
        request=urllib.request.Request(SERVER+'/api/restapi/'+route,method='POST',
            data=b'' if payload is None else json.dumps(payload,ensure_ascii=False,allow_nan=False).encode(),
            headers={'Authorization':'Bearer '+self._token,'Accept':'application/json','Content-Type':'application/json'})
        raw=_exchange(self._opener,request,'Envio de horas',limit=33554432,expected=expected)
        return _json(raw,'Envio de horas') if raw else None


def plan_hours(package,mapping,catalog):
    needed=set(package['hh_por_funcao'])
    if set(mapping)!=needed:raise ConnectionFailure('Escolha uma função Oracle para cada função com horas na LD.')
    if len(set(mapping.values()))!=len(mapping):raise ConnectionFailure('Cada função da LD precisa de um cadastro Oracle distinto.')
    roles={r['resourceId']:r for r in catalog}
    for key,rid in mapping.items():
        positive_id(rid)
        if rid not in roles:raise ConnectionFailure('Função fora do catálogo ativo consultado.')
    payloads=[]
    for a in package['tables']['Atribuicoes_Funcoes']:
        hh=amount(a['hh']);number=float(hh)
        if abs(Decimal(str(number))-hh)>TOL:raise ConnectionFailure('Precisão das horas excede o limite de envio.')
        payloads.append({'assignmentCode':'BL-'+a['id'],'projectId':package['projectId'],
            'activityId':package['journal']['atividades'][a['atividade_id']],
            'resourceId':mapping[a['funcao']],'resourceClass':'ROLE',
            'plannedUnits':number,'remainingUnits':number,'driveActivityDates':False})
    return {'servidor':SERVER,'projectId':package['projectId'],'source_sha256':package['source_sha256'],
        'mapping':mapping,'hh_planejadas':package['hh_planejadas'],
        'hh_por_funcao':package['hh_por_funcao'],'payloads':payloads,
        'associar_funcoes':[rid for rid in mapping.values() if not roles[rid]['assigned_to_project']],
        'aviso':'HH de trabalho para funções LABOR; não são duração. Sem envio de taxas, datas ou avanço.'}


def partition_hours(plan,existing):
    """Deterministic codes and activity/role pairs prevent adding duplicate workload."""
    expected={p['assignmentCode']:p for p in plan['payloads']};found={};pairs={};assignment_ids=set()
    for row in existing:
        pair=(row.get('activityId'),row.get('resourceId'))
        pairs.setdefault(pair,[]).append(row)
        code=row.get('assignmentCode')
        if code not in expected:continue
        if code in found:raise ConnectionFailure('Há atribuições repetidas no Oracle.')
        p=expected[code]
        if any(row.get(k)!=p[k] for k in ('activityId','resourceId','resourceClass')):
            raise ConnectionFailure('Uma atribuição existente usa outra atividade ou função.')
        if row.get('projectId') not in (None,plan['projectId']):raise ConnectionFailure('Atribuição de outro projeto.')
        if (abs(amount(row.get('plannedUnits'))-amount(p['plannedUnits']))>TOL
            or abs(amount(row.get('remainingUnits'))-amount(p['remainingUnits']))>TOL
            or amount(row.get('actualUnits',0) or 0)!=0):
            raise ConnectionFailure('As horas existentes diferem ou já possuem avanço; nenhuma será sobrescrita.')
        identifier=positive_id(row.get('assignmentId'))
        if identifier in assignment_ids:raise ConnectionFailure('IDs de atribuição repetidos na resposta Oracle.')
        assignment_ids.add(identifier);found[code]=row
    for p in expected.values():
        others=pairs.get((p['activityId'],p['resourceId']),[])
        if len(others)>1 or (others and others[0].get('assignmentCode')!=p['assignmentCode']):
            raise ConnectionFailure('Já existe outra atribuição para a mesma atividade e função. Confira para não somar horas em duplicidade.')
    return [p for code,p in expected.items() if code not in found],found


def sync_hours(session,package,plan,journal_path,progress=lambda message:None):
    # Revalidate live data and catalog at the moment of the explicit write confirmation.
    _,catalog=session.catalog(package)
    checked=plan_hours(package,plan['mapping'],catalog)
    if any(checked[k]!=plan[k] for k in ('payloads','source_sha256','projectId')):
        raise ConnectionFailure('A prévia de horas mudou; consulte novamente.')
    pid=plan['projectId'];path=Path(journal_path)
    sha=hashlib.sha256(json.dumps({k:plan[k] for k in ('projectId','source_sha256','mapping','payloads')},sort_keys=True,ensure_ascii=False).encode()).hexdigest()
    existing=session.rows('assignment/project/'+str(pid))
    missing,found=partition_hours(plan,existing)
    state={'servidor':SERVER,'projectId':pid,'source_sha256':package['source_sha256'],'plan_sha256':sha,
        'estado':'em_andamento','confirmadas':{k:r['assignmentId'] for k,r in found.items()},'pendente':None}
    if path.exists():
        old=json.loads(path.read_text())
        if old.get('plan_sha256')!=sha:raise ConnectionFailure('Há registro de horas de outra prévia. Preserve e confira antes de continuar.')
        pending=old.get('pendente')
        if pending:
            if pending['tipo']=='atribuicoes' and any(code not in found for code in pending['codigos']):
                raise ConnectionFailure('Um lote anterior tem resultado incerto. Consulte o Oracle; ele não será repetido automaticamente.')
            if pending['tipo']=='funcao' and pending['resourceId'] in checked['associar_funcoes']:
                raise ConnectionFailure('Associação de função anterior com resultado incerto. Confira o Oracle.')
    durable_write(path,state)
    try:
        for rid in checked['associar_funcoes']:
            state['pendente']={'tipo':'funcao','resourceId':rid};durable_write(path,state)
            session.mutation(f'resource/{positive_id(rid)}/assign/project/{pid}',expected=(204,))
            state['pendente']=None;durable_write(path,state)
        for start in range(0,len(missing),50):
            rows=missing[start:start+50]
            state['pendente']={'tipo':'atribuicoes','codigos':[r['assignmentCode'] for r in rows]};durable_write(path,state)
            result=session.mutation('assignment/batch',rows)
            if not isinstance(result,list) or len(result)!=len(rows):raise ConnectionFailure('Resposta de lote incompleta. Preserve o registro antes de repetir.')
            partial=dict(plan,payloads=rows)
            absent,confirmed=partition_hours(partial,result)
            if absent:raise ConnectionFailure('O Oracle não confirmou todas as horas do lote.')
            state['confirmadas'].update({k:r['assignmentId'] for k,r in confirmed.items()})
            state['pendente']=None;durable_write(path,state)
            progress('Atribuições conferidas: '+str(len(state['confirmadas']))+'/'+str(len(plan['payloads'])))
        after=session.rows('assignment/project/'+str(pid))
        missing,found=partition_hours(plan,after)
        if missing:raise ConnectionFailure('A leitura final não confirmou todas as horas.')
        state['confirmadas']={k:r['assignmentId'] for k,r in found.items()}
        state['hh_conferidas']=str(sum((amount(r['plannedUnits']) for r in found.values()),Decimal(0)))
        if abs(amount(state['hh_conferidas'])-amount(plan['hh_planejadas']))>TOL:raise ConnectionFailure('A soma final de HH não fecha.')
        state['estado']='horas_conferidas';durable_write(path,state)
        return state
    except BaseException as exc:
        state['estado']='interrompido_conferir_oracle'
        state['erro']=str(exc) if isinstance(exc,ConnectionFailure) else 'Operação interrompida; confira o Oracle antes de repetir.'
        durable_write(path,state);raise


def diagnose_hours(session,package,plan,record=None):
    """Read-only snapshot of expected role-hours and actual Oracle assignments.

    This intentionally does not call sync_hours or modify the execution journal.
    """
    if plan.get('projectId')!=package['projectId'] or plan.get('source_sha256')!=package['source_sha256']:
        raise ConnectionFailure('A prévia não corresponde ao Excel e ao projeto selecionados.')
    session.binding(package)
    existing=session.rows('assignment/project/'+str(package['projectId']))
    codes=defaultdict(list);pairs=defaultdict(list)
    for row in existing:
        codes[row.get('assignmentCode')].append(row)
        pairs[(row.get('activityId'),row.get('resourceId'))].append(row)
    identity={k:plan[k] for k in ('projectId','source_sha256','mapping','payloads')}
    sha=hashlib.sha256(json.dumps(identity,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
    record_ok=bool(record and record.get('servidor')==SERVER and record.get('projectId')==plan['projectId']
        and record.get('source_sha256')==plan['source_sha256'] and record.get('plan_sha256')==sha)
    pending=(record.get('pendente') or {}) if record_ok else {}
    pending_codes=set(pending.get('codigos',[])) if pending.get('tipo')=='atribuicoes' else set()
    counts={'compativeis':0,'nao_encontradas':0,'divergentes':0};details=[]
    keep=('assignmentCode','assignmentId','projectId','activityId','resourceId','resourceClass','plannedUnits','remainingUnits','actualUnits')
    def minimal(row):
        return {k:(v if v is None or type(v) in (str,int,float,bool) else 'Formato não reconhecido') for k in keep if (v:=row.get(k)) is not None}
    for expected in plan['payloads']:
        code=expected['assignmentCode'];pair=(expected['activityId'],expected['resourceId'])
        related=list(codes.get(code,[]))
        related.extend(row for row in pairs.get(pair,[]) if row not in related)
        problem=None
        try:
            missing,found=partition_hours(dict(plan,payloads=[expected]),related)
            status='nao_encontradas' if missing else 'compativeis'
        except (ConnectionFailure,ValueError,TypeError,KeyError) as exc:
            status='divergentes';problem=str(exc) if isinstance(exc,ConnectionFailure) else 'Formato da resposta não reconhecido.'
        counts[status]+=1
        if status=='divergentes' or code in pending_codes:
            details.append({'codigo':code,'situacao':status,'lote_interrompido':code in pending_codes,
                'esperado':expected,'encontrados':[minimal(row) for row in related],'motivo':problem})
    global_problem=None
    try:partition_hours(plan,existing)
    except (ConnectionFailure,ValueError,TypeError,KeyError) as exc:
        global_problem=str(exc) if isinstance(exc,ConnectionFailure) else 'Formato de resposta não reconhecido.'
    assigned=session.rows('resource/projectId/'+str(package['projectId']))
    role_ids={r.get('resourceId') for r in assigned if r.get('resourceClass')=='ROLE'}
    return {'tipo':'diagnostico_horas_somente_leitura','consultado_em_utc':datetime.now(timezone.utc).isoformat(),'servidor':SERVER,'projectId':plan['projectId'],
        'source_sha256':plan['source_sha256'],'plan_sha256':sha,'atribuicoes_previstas':len(plan['payloads']),
        'hh_previstas':plan['hh_planejadas'],'atribuicoes_retornadas_oracle':len(existing),'resumo':counts,
        'funcoes_selecionadas_associadas':len(set(plan['mapping'].values())&role_ids),
        'funcoes_selecionadas_nao_associadas':sorted(set(plan['mapping'].values())-role_ids),
        'registro_compativel':record_ok,'estado_registro':record.get('estado') if record_ok else None,
        'erro_ultimo_envio':record.get('erro') if record_ok else None,'solicitacao_pendente':pending,
        'problema_conferencia_global':global_problem,'detalhes':details,
        'aviso':'Somente consulta. Não confirma a causa de uma falha passada sem resposta registrada e não autoriza repetir um lote incerto.'}
