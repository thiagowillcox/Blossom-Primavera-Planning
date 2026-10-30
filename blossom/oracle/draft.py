"""Create-only structural drafts in empty test projects. Never schedule or assign HH."""
import hashlib
import html
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import urllib.request
import urllib.parse
import openpyxl
from ..validation import topology
from .client import SERVER, ConnectionFailure, ReadSession, _exchange, _json
from .preview import prepare_preview, amount


def positive_id(value):
    if type(value) is not int or value <= 0:
        raise ConnectionFailure('Identificador Oracle inválido. O envio foi interrompido.')
    return value


def text(value, limit):
    if not isinstance(value,str) or not value.strip() or len(value)>limit or any(ord(c)<32 for c in value):
        raise ConnectionFailure('Nome ou código vazio/incompatível com o limite da API. Confira a planilha.')
    return value


def field_equal(key, actual, expected):
    # Oracle may HTML-escape response names and trim ASCII boundary spaces.
    # Decode a response at most once; never decode the source name or IDs/codes.
    # Keep case, accents, punctuation and internal whitespace significant.
    if key in ('wbsName','activityName') and isinstance(actual,str) and isinstance(expected,str):
        expected=expected.strip(' ')
        return actual.strip(' ')==expected or html.unescape(actual).strip(' ')==expected
    return actual==expected


def build_draft(workbook_path, selection_path, preview_path):
    """Revalidate workbook and bind to the exact offline preview already reviewed."""
    old=json.loads(Path(preview_path).read_text(encoding='utf-8'))
    with TemporaryDirectory() as directory:
        report=prepare_preview(workbook_path,selection_path,Path(directory)/'check.json')
    if (old.get('servidor')!=SERVER or old.get('origem',{}).get('xlsx_sha256')!=report['origem']['xlsx_sha256']
        or old.get('projeto_destino')!=report['projeto_destino']):
        raise ConnectionFailure('O Excel ou destino mudou desde a prévia. Execute Preparar_Envio_Primavera.bat novamente.')
    pid=positive_id(report['projeto_destino']['projectId'])
    workbook=openpyxl.load_workbook(workbook_path,read_only=True,data_only=True)
    try:
        tables={}
        for name in ('WBS','Atividades','Relacionamentos'):
            rows=workbook[name].values;header=next(rows)
            tables[name]=[dict(zip(header,row)) for row in rows if any(v is not None for v in row)]
    finally:workbook.close()
    ws=tables['WBS'];activities=[a for a in tables['Atividades'] if a.get('tipo_linha','atividade')=='atividade']
    # Codes retain stable Blossom IDs, not row positions or Oracle-generated IDs.
    wbs={w['id']:w for w in ws}
    order=topology(ws,[{'predecessora':w['pai'],'sucessora':w['id']} for w in ws if w.get('pai')])
    groups=[]
    for key in order:
        w=wbs[key]
        groups.append({'local_id':text(key,60),'local_parent':w.get('pai'),'payload':{
            'projectId':pid,'wbsCode':text(w['codigo'],60),'wbsName':text(w['nome'],255),
            'description':'RASCUNHO Blossom Planning: estrutura para revisão, sem validação de prazos.'}})
    activity_rows=[]
    for a in activities:
        activity_rows.append({'local_id':text(a['id'],60),'local_wbs':a['wbs_id'],'payload':{
            'projectId':pid,'activityCode':text(a['id'],60),'activityName':text(a['nome'],255),
            'activityType':'ACTIVITY','activityStatus':'NOT_STARTED'}})
    relations=[]
    for r in tables['Relacionamentos']:
        if r.get('tipo')!='FS' or amount(r.get('defasagem_dias',0))!=0:
            raise ConnectionFailure('O rascunho inicial aceita somente ligações FS sem defasagem. Nenhuma conversão de dias em horas será presumida.')
        relations.append({'predecessor':r['predecessora'],'successor':r['sucessora'],
            'payload':{'predProjectId':pid,'succProjectId':pid,'relationshipType':'FINISH_TO_START','lagHours':0}})
    plan={'tipo':'rascunho_estrutural_oracle_v1','servidor':SERVER,'projeto':report['projeto_destino'],
        'origem':report['origem'],'wbs':groups,'activities':activity_rows,'relationships':relations,
        'hh_nao_enviadas':report['hh_planejadas'],'duracoes_nao_enviadas':True,
        'pendencias_por_categoria':report['pendencias_por_categoria']}
    return plan


class DraftSession(ReadSession):
    """Only known read routes and three create routes, no PUT/DELETE/scheduler."""
    def _read_json(self,path):
        raw=self._get(path,'Conferência do projeto',limit=16777216,allow_empty=True)
        return _json(raw,'Conferência do projeto') if raw else []

    def inspect_empty_project(self, selected):
        pid=positive_id(selected['projectId'])
        if not str(selected.get('projectName','')).strip().upper().startswith('TESTE'):
            raise ConnectionFailure('Este iniciador aceita apenas projetos de teste cujo nome comece com TESTE.')
        project=self._read_json('project/'+str(pid))
        if not isinstance(project,dict) or project.get('projectId')!=pid or any(
            project.get(k)!=selected.get(k) for k in ('projectName','projectCode','workspaceId') if selected.get(k) is not None):
            raise ConnectionFailure('O projeto Oracle não corresponde ao destino selecionado. Consulte os projetos novamente.')
        activities=self._read_json('activity/project/'+str(pid))
        if not isinstance(activities,list) or activities:
            raise ConnectionFailure('O projeto já possui atividades ou a consulta não foi reconhecida. Use um projeto de teste vazio; nada foi alterado.')
        groups=self._read_json('wbs/project/'+str(pid))
        if (not isinstance(groups,list) or len(groups)!=1 or not isinstance(groups[0],dict)
            or groups[0].get('projectId')!=pid or groups[0].get('parentId') not in (None,0)):
            raise ConnectionFailure('Esperávamos apenas a WBS raiz do projeto vazio. Confira a estrutura antes de enviar; nada foi alterado.')
        text(project.get('projectCode'),60);text(project.get('workspaceCode'),60)
        self._project=project
        return positive_id(groups[0].get('wbsId'))

    def verify_created(self, plan, journal, root_id):
        pid=plan['projeto']['projectId']
        groups=self._read_json('wbs/project/'+str(pid))
        activities=self._read_json('activity/project/'+str(pid))
        query=urllib.parse.urlencode({'workspaceCode':self._project['workspaceCode'],
            'projectCode':self._project['projectCode']})
        relations=self._read_json('relationship/projectRelationshipCode?'+query)
        for rows,key,expected in (
            (groups,'wbsId',set(journal['wbs'].values())|{root_id}),
            (activities,'activityId',set(journal['atividades'].values())),
            (relations,'relationshipId',set(journal['relacionamentos']))):
            if not isinstance(rows,list) or len(rows)!=len(expected) or any(not isinstance(r,dict) for r in rows):
                raise ConnectionFailure('A leitura de conferência está incompleta ou o projeto mudou. Não repita o envio.')
            if {r.get(key) for r in rows}!=expected:
                raise ConnectionFailure('Os IDs lidos no Oracle diferem dos criados. Não repita o envio.')
        actual_groups={w['wbsId']:w for w in groups}
        for w in plan['wbs']:
            row=actual_groups[journal['wbs'][w['local_id']]]
            parent=journal['wbs'][w['local_parent']] if w['local_parent'] else root_id
            if row.get('parentId')!=parent or any(not field_equal(k,row.get(k),v) for k,v in w['payload'].items() if k!='description'):
                raise ConnectionFailure('Hierarquia ou nomes das WBS diferem na leitura de conferência.')
        actual_activities={a['activityId']:a for a in activities}
        for a in plan['activities']:
            row=actual_activities[journal['atividades'][a['local_id']]]
            if row.get('wbsId')!=journal['wbs'][a['local_wbs']] or any(not field_equal(k,row.get(k),v) for k,v in a['payload'].items()):
                raise ConnectionFailure('Uma atividade difere na leitura de conferência.')
        expected={(journal['atividades'][r['predecessor']],journal['atividades'][r['successor']]):r['payload'] for r in plan['relationships']}
        for row in relations:
            value=expected.get((row.get('predActivityId'),row.get('succActivityId')))
            if not value or any(row.get(k)!=v for k,v in value.items()):
                raise ConnectionFailure('Uma ligação difere na leitura de conferência.')

    def create(self, route, payload):
        if route not in ('wbs','activity/batch','relationship/batch'):
            raise ConnectionFailure('Operação de escrita não permitida por este iniciador.')
        if not self._token:raise ConnectionFailure('Sessão encerrada.')
        # Only request names are trimmed; the source workbook and plan remain intact.
        def clean(row):return {k:(v.strip(' ') if k in ('wbsName','activityName') and isinstance(v,str) else v) for k,v in row.items()}
        payload=[clean(row) for row in payload] if isinstance(payload,list) else clean(payload)
        request=urllib.request.Request(SERVER+'/api/restapi/'+route,method='POST',
            data=json.dumps(payload,ensure_ascii=False,allow_nan=False).encode('utf-8'),
            headers={'Authorization':'Bearer '+self._token,'Accept':'application/json','Content-Type':'application/json'})
        return _json(_exchange(self._opener,request,'Criação do rascunho',limit=16777216,expected=(201,)), 'Criação do rascunho')


def durable_write(path, data, *, exclusive=False):
    # Flush before requesting a mutation. An uncertain request must never be retried blindly.
    payload=json.dumps(data,ensure_ascii=False,indent=2,allow_nan=False)
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x' if exclusive else 'w',encoding='utf-8') as stream:
        stream.write(payload);stream.flush();os.fsync(stream.fileno())


def upload_draft(session, plan, root_id, journal_path, progress=print, *, resume=False):
    """Caller must display the plan and obtain explicit confirmation before calling."""
    path=Path(journal_path);path.parent.mkdir(parents=True,exist_ok=True)
    if resume:
        inspected_root,journal=reconcile_wbs(session,plan,path)
        if inspected_root!=root_id:raise ConnectionFailure('A raiz mudou antes da continuação.')
        before=json.loads(path.read_text(encoding='utf-8'))
        backup=path.with_name(path.stem+'.backup_'+hashlib.sha256(json.dumps(before,sort_keys=True).encode()).hexdigest()[:16]+'.json')
        if not backup.exists():durable_write(backup,before,exclusive=True)
        journal['estado']='em_andamento';journal['solicitacao_pendente']=None
        durable_write(path,journal)
    else:
        if path.exists():
            raise ConnectionFailure('Já existe um registro de envio para esse projeto. Não repita nem apague o registro: precisamos conferir o Oracle antes de continuar.')
        journal={'servidor':SERVER,'projectId':plan['projeto']['projectId'],'origem':plan['origem'],
            'plan_sha256':hashlib.sha256(json.dumps(plan,sort_keys=True,ensure_ascii=False).encode()).hexdigest(),
            'estado':'em_andamento','wbs':{},'atividades':{},'relacionamentos':[], 'solicitacao_pendente':None,
            'aviso':'Rascunho sem HH atribuídas e sem prazos validados. Não agendar automaticamente.'}
        durable_write(path,journal,exclusive=True)
    def request(route,payload,keys):
        journal['solicitacao_pendente']={'rota':route,'chaves':keys}
        durable_write(path,journal)
        # No automatic retry. Failure may mean the Oracle accepted part/all of this batch.
        return session.create(route,payload)
    def save():
        journal['solicitacao_pendente']=None;durable_write(path,journal)
    try:
        for i,w in enumerate(plan['wbs'],1):
            if w['local_id'] in journal['wbs']:
                progress(f"Grupo já conferido, preservado: {i}/{len(plan['wbs'])}");continue
            payload=dict(w['payload'],parentId=journal['wbs'][w['local_parent']] if w['local_parent'] else positive_id(root_id))
            result=request('wbs',payload,[w['local_id']])
            if not isinstance(result,dict) or any(not field_equal(k,result.get(k),payload[k]) for k in ('projectId','wbsCode','wbsName','parentId')):
                raise ConnectionFailure('Resposta da WBS diferente do esperado.')
            identifier=positive_id(result.get('wbsId'))
            if identifier in journal['wbs'].values():raise ConnectionFailure('ID de WBS repetido na resposta.')
            journal['wbs'][w['local_id']]=identifier;save()
            progress(f"Grupos criados: {i}/{len(plan['wbs'])}")
        for start in range(0,len(plan['activities']),50):
            rows=plan['activities'][start:start+50]
            payloads=[dict(a['payload'],wbsId=journal['wbs'][a['local_wbs']]) for a in rows]
            result=request('activity/batch',payloads,[a['local_id'] for a in rows])
            if not isinstance(result,list) or len(result)!=len(rows):raise ConnectionFailure('Lote de atividades com resposta incompleta.')
            expected={p['activityCode']:p for p in payloads};seen=set()
            for item in result:
                if not isinstance(item,dict):raise ConnectionFailure('Resposta de atividade não reconhecida.')
                key=item.get('activityCode');p=expected.get(key)
                if not p or key in seen or any(not field_equal(k,item.get(k),p[k]) for k in ('projectId','wbsId','activityName')):
                    raise ConnectionFailure('Lote de atividades não corresponde à solicitação.')
                identifier=positive_id(item.get('activityId'))
                if identifier in journal['atividades'].values():raise ConnectionFailure('ID de atividade repetido na resposta.')
                journal['atividades'][key]=identifier;seen.add(key)
            save();progress(f"Atividades criadas: {len(journal['atividades'])}/{len(plan['activities'])}")
        for start in range(0,len(plan['relationships']),50):
            rows=plan['relationships'][start:start+50]
            payloads=[dict(r['payload'],predActivityId=journal['atividades'][r['predecessor']],
                succActivityId=journal['atividades'][r['successor']]) for r in rows]
            result=request('relationship/batch',payloads,[[r['predecessor'],r['successor']] for r in rows])
            if not isinstance(result,list) or len(result)!=len(rows):raise ConnectionFailure('Lote de ligações com resposta incompleta.')
            expected={(p['predActivityId'],p['succActivityId']):p for p in payloads};seen=set()
            for item in result:
                if not isinstance(item,dict):raise ConnectionFailure('Resposta de ligação não reconhecida.')
                pair=(item.get('predActivityId'),item.get('succActivityId'));p=expected.get(pair)
                if not p or pair in seen or any(item.get(k)!=p[k] for k in p):
                    raise ConnectionFailure('Lote de ligações não corresponde à solicitação.')
                identifier=positive_id(item.get('relationshipId'))
                if identifier in journal['relacionamentos']:raise ConnectionFailure('ID de ligação repetido na resposta.')
                journal['relacionamentos'].append(identifier);seen.add(pair)
            save();progress(f"Ligações criadas: {len(journal['relacionamentos'])}/{len(plan['relationships'])}")
        progress('Conferindo os dados criados por nova leitura da API...')
        session.verify_created(plan,journal,root_id)
        journal['estado']='estrutura_conferida_prazos_e_hh_pendentes';save()
        return journal
    except BaseException:
        journal['estado']='interrompido_conferir_oracle_antes_de_repetir'
        durable_write(path,journal)
        raise


def reconcile_wbs(session, plan, journal_path):
    """Read-only reconciliation of a WBS-only prefix plus one uncertain created WBS.

    Never resume an activity batch or adopt unrelated entities by name alone.
    """
    journal=json.loads(Path(journal_path).read_text(encoding='utf-8'))
    digest=hashlib.sha256(json.dumps(plan,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
    pid=plan['projeto']['projectId']
    if (plan.get('servidor')!=SERVER or journal.get('servidor')!=SERVER or journal.get('projectId')!=pid
        or journal.get('plan_sha256')!=digest or not str(journal.get('estado','')).startswith('interrompido')
        or journal.get('atividades') or journal.get('relacionamentos')):
        raise ConnectionFailure('Esse registro não permite continuação automática de WBS. Preserve os arquivos para conferência.')
    project=plan['projeto']
    if not str(project.get('projectName','')).strip().upper().startswith('TESTE'):
        raise ConnectionFailure('A continuação exige projeto de teste.')
    actual=session._read_json('project/'+str(positive_id(pid)))
    if not isinstance(actual,dict) or any(actual.get(k)!=project.get(k) for k in ('projectId','projectName','projectCode','workspaceId') if project.get(k) is not None):
        raise ConnectionFailure('O destino da continuação difere do plano.')
    text(actual.get('projectCode'),60);text(actual.get('workspaceCode'),60)
    activities=session._read_json('activity/project/'+str(pid))
    if not isinstance(activities,list) or activities:
        raise ConnectionFailure('Já há atividades no projeto. A continuação de WBS foi bloqueada.')
    groups=session._read_json('wbs/project/'+str(pid))
    if not isinstance(groups,list) or any(not isinstance(w,dict) or w.get('projectId')!=pid for w in groups):
        raise ConnectionFailure('Consulta de WBS não reconhecida.')
    roots=[w for w in groups if w.get('parentId') in (None,0)]
    if len(roots)!=1:raise ConnectionFailure('Raiz do projeto não reconhecida.')
    root=positive_id(roots[0].get('wbsId'))
    recorded=journal.get('wbs',{})
    if not isinstance(recorded,dict):raise ConnectionFailure('Registro de WBS inválido.')
    rows=plan['wbs'];count=len(recorded)
    if count>=len(rows) or set(recorded)!={w['local_id'] for w in rows[:count]}:
        raise ConnectionFailure('O registro não corresponde à sequência original de WBS.')
    pending=journal.get('solicitacao_pendente') or {}
    if pending.get('rota')!='wbs' or pending.get('chaves')!=[rows[count]['local_id']]:
        raise ConnectionFailure('A solicitação interrompida não é a próxima WBS da sequência.')
    used={root};mapping={}
    for index,w in enumerate(rows[:count+1]):
        parent=mapping[w['local_parent']] if w['local_parent'] else root
        payload=dict(w['payload'],parentId=parent)
        if index<count:
            identifier=positive_id(recorded[w['local_id']])
            candidates=[g for g in groups if g.get('wbsId')==identifier]
        else:
            candidates=[g for g in groups if g.get('wbsCode')==payload['wbsCode'] and g.get('parentId')==parent]
        if len(candidates)!=1 or any(not field_equal(k,candidates[0].get(k),payload[k]) for k in ('projectId','wbsCode','wbsName','parentId')):
            raise ConnectionFailure('Uma WBS existente difere do plano ou não foi encontrada de forma única. Nada será repetido.')
        identifier=positive_id(candidates[0].get('wbsId'))
        if identifier in used:raise ConnectionFailure('ID de WBS duplicado na conferência.')
        used.add(identifier);mapping[w['local_id']]=identifier
    if len(groups)!=len(used) or {g.get('wbsId') for g in groups}!=used:
        raise ConnectionFailure('Existem outras WBS ou a consulta está incompleta. Continuação bloqueada.')
    journal['wbs']=mapping
    session._project=actual
    return root,journal
