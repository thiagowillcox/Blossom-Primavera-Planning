"""Create a project in an explicitly selected workspace; no implicit structure import."""
import hashlib
import html
import json
import urllib.request
from datetime import date,datetime,time,timedelta,timezone
from pathlib import Path
from .client import SERVER,ConnectionFailure,_exchange,_json
from .draft import positive_id,text,durable_write


def wire_equal(actual,expected):
    return actual==expected or (isinstance(actual,str) and html.unescape(actual)==expected)


def workspace_snapshot(row):
    if not isinstance(row,dict):raise ConnectionFailure('Workspace não reconhecido.')
    positive_id(row.get('workspaceId'));text(row.get('workspaceName'),255)
    if row.get('parentId') not in (None,0):positive_id(row['parentId'])
    return {k:row.get(k) for k in ('workspaceId','workspaceName','workspaceCode','parentId')}


def list_workspaces(session):
    rows=session.rows('workspace');seen=set();result=[]
    for row in rows:
        item=workspace_snapshot(row);wid=item['workspaceId']
        if wid in seen:raise ConnectionFailure('A consulta repetiu um workspace.')
        seen.add(wid);result.append(item)
    by_id={r['workspaceId']:r for r in result}
    for row in result:
        current=row;path=[];visited=set()
        while current:
            wid=current['workspaceId']
            if wid in visited:raise ConnectionFailure('Hierarquia circular de workspaces.')
            visited.add(wid);path.append(html.unescape(current['workspaceName']))
            parent=current.get('parentId')
            if parent not in (None,0) and parent not in by_id:path.append('…')
            current=by_id.get(parent)
        row['caminho']=' / '.join(reversed(path))
    return sorted(result,key=lambda row:(row['caminho'].casefold(),row['workspaceId']))


def verify_workspace(session,selected):
    expected=workspace_snapshot(selected)
    actual=workspace_snapshot(session.read('workspace/'+str(expected['workspaceId'])))
    if any(not wire_equal(actual.get(k),expected.get(k)) for k in expected):
        raise ConnectionFailure('O workspace mudou desde a seleção. Consulte a lista novamente.')
    return actual


def calendars_for_workspace(session,workspace_id):
    wid=positive_id(workspace_id);visited=set();result={}
    for _ in range(20):
        if wid in visited:raise ConnectionFailure('Hierarquia de workspaces circular.')
        visited.add(wid)
        for row in session.rows('calendar/workspace/'+str(wid)):
            if row.get('projectId') not in (None,0) or row.get('isAssignableToProject') is False:continue
            cid=positive_id(row.get('calendarId'))
            if row.get('workspaceId')!=wid:raise ConnectionFailure('Calendário retornado fora do workspace consultado.')
            selected={k:row.get(k) for k in ('calendarId','calendarName','workspaceId','isAssignableToProject')}
            if cid in result and result[cid]!=selected:raise ConnectionFailure('Calendário inconsistente entre consultas.')
            result[cid]=selected
        workspace=workspace_snapshot(session.read('workspace/'+str(wid)))
        parent=workspace.get('parentId')
        if parent in (None,0):break
        wid=positive_id(parent)
    else:raise ConnectionFailure('A hierarquia de calendários excedeu o limite de conferência.')
    return sorted(result.values(),key=lambda r:(str(r['calendarName']).casefold(),r['calendarId']))


def projects_in_workspace(session,wid):
    rows=session.rows('project/workspace/'+str(positive_id(wid)))
    for row in rows:
        if row.get('workspaceId')!=wid or not isinstance(row.get('projectCode'),str):
            raise ConnectionFailure('A consulta de projetos não confirmou o workspace escolhido.')
        positive_id(row.get('projectId'))
    return rows


def matching_code(rows,code):
    return [r for r in rows if html.unescape(r['projectCode']).strip().casefold()==code.strip().casefold()]


def prepare_project(session,workspace,code,name,start,clock=time(8),calendar_id=None):
    if not isinstance(code,str) or not isinstance(name,str):raise ConnectionFailure('Preencha código e nome do projeto.')
    code=text(code.strip(),60);name=text(name.strip(),255)
    if not name.upper().startswith('TESTE'):raise ConnectionFailure('Nesta versão, o nome do novo projeto precisa começar com TESTE.')
    if type(start) is not date or not isinstance(clock,time) or clock.tzinfo is not None:
        raise ConnectionFailure('Preencha a data e o horário de início do novo projeto.')
    selected=verify_workspace(session,workspace)
    stamp=datetime.combine(start,clock,tzinfo=timezone(timedelta(hours=-3))).isoformat()
    payload={'workspaceId':selected['workspaceId'],'projectCode':code,'projectName':name,
        'planStartDate':stamp,'dataDate':stamp,'status':'PLANNED'}
    calendar_name=None
    if calendar_id is not None:
        cid=positive_id(calendar_id)
        calendars=calendars_for_workspace(session,selected['workspaceId'])
        match=next((r for r in calendars if r['calendarId']==cid),None)
        if match is None:raise ConnectionFailure('O calendário não está disponível para o workspace escolhido.')
        payload['calendarId']=cid;calendar_name=match['calendarName']
    if matching_code(projects_in_workspace(session,selected['workspaceId']),code):
        raise ConnectionFailure('Já existe um projeto com esse código nesse workspace. Escolha outro código ou use o projeto existente.')
    return {'servidor':SERVER,'workspace':selected,'payload':payload,'calendarName':calendar_name,
        'aviso':'Cria somente o projeto. Estrutura, horas e agendamento continuam em etapas separadas.'}


def project_signature(plan):
    return hashlib.sha256(json.dumps(plan,sort_keys=True,ensure_ascii=False).encode()).hexdigest()


def verify_project(session,pid,payload):
    row=session.read('project/'+str(positive_id(pid)))
    if (not isinstance(row,dict) or row.get('projectId')!=pid or row.get('workspaceId')!=payload['workspaceId']
        or not wire_equal(row.get('projectCode'),payload['projectCode'])
        or not wire_equal(row.get('projectName'),payload['projectName'])):
        raise ConnectionFailure('O projeto retornado não corresponde ao nome, código e workspace confirmados. Não repita a criação.')
    if 'calendarId' in payload and row.get('calendarId')!=payload['calendarId']:
        raise ConnectionFailure('O calendário do projeto criado difere da prévia. Confira antes de continuar.')
    return {k:row.get(k) for k in ('projectId','projectName','projectCode','workspaceId')}


def create_project(session,plan,journal_path):
    if plan.get('servidor')!=SERVER:raise ConnectionFailure('Ambiente do projeto inválido.')
    payload=plan['payload'];workspace=plan['workspace']
    if not isinstance(payload.get('projectName'),str) or not payload['projectName'].upper().startswith('TESTE'):
        raise ConnectionFailure('O nome do novo projeto precisa começar com TESTE.')
    # Recheck the same plan, never accept caller-defined extra write fields.
    permitted={'workspaceId','projectCode','projectName','planStartDate','dataDate','status','calendarId'}
    if set(payload)-permitted or payload.get('workspaceId')!=workspace.get('workspaceId') or payload.get('status')!='PLANNED':
        raise ConnectionFailure('A prévia de criação contém campos não permitidos.')
    stamp=datetime.fromisoformat(payload['planStartDate'])
    if stamp.utcoffset()!=timedelta(hours=-3) or payload.get('dataDate')!=payload['planStartDate']:
        raise ConnectionFailure('As datas da prévia não foram confirmadas.')
    path=Path(journal_path);signature=project_signature(plan)
    if path.exists():
        old=json.loads(path.read_text())
        if old.get('plan_sha256')!=signature:raise ConnectionFailure('Há registro de outra prévia. Preserve-o antes de continuar.')
        verify_workspace(session,workspace)
        pid=old.get('projectId')
        if pid is None:
            candidates=matching_code(projects_in_workspace(session,payload['workspaceId']),payload['projectCode'])
            if len(candidates)!=1:
                raise ConnectionFailure('Uma criação anterior ainda tem resultado incerto. Ela não será repetida automaticamente.')
            pid=positive_id(candidates[0].get('projectId'))
        project=verify_project(session,pid,payload)
        old.update(estado='projeto_criado_conferido',projectId=pid,projeto=project,pendente=False)
        durable_write(path,old);return project
    checked=prepare_project(session,workspace,payload['projectCode'],payload['projectName'],stamp.date(),stamp.timetz().replace(tzinfo=None),payload.get('calendarId'))
    if checked!=plan:raise ConnectionFailure('A prévia mudou antes da criação. Confira novamente.')
    if not session._token:raise ConnectionFailure('Conexão encerrada.')
    state={'servidor':SERVER,'plan_sha256':signature,'workspaceId':payload['workspaceId'],'projectCode':payload['projectCode'],
        'estado':'criacao_pendente','projectId':None,'pendente':True}
    durable_write(path,state,exclusive=True)
    try:
        request=urllib.request.Request(SERVER+'/api/restapi/project',method='POST',
            data=json.dumps(payload,ensure_ascii=False,allow_nan=False).encode(),
            headers={'Authorization':'Bearer '+session._token,'Accept':'application/json','Content-Type':'application/json'})
        result=_json(_exchange(session._opener,request,'Criação do projeto',limit=4194304,expected=(201,)),'Criação do projeto')
        if not isinstance(result,dict):raise ConnectionFailure('Resposta de criação do projeto não reconhecida. Consulte antes de repetir.')
        pid=positive_id(result.get('projectId'));state['projectId']=pid;durable_write(path,state)
        project=verify_project(session,pid,payload)
        state.update(estado='projeto_criado_conferido',pendente=False,projeto=project)
        durable_write(path,state);return project
    except BaseException as exc:
        state['estado']='interrompido_conferir_oracle'
        state['erro']=str(exc) if isinstance(exc,ConnectionFailure) else 'Operação interrompida. Confira o Oracle antes de repetir.'
        durable_write(path,state);raise
