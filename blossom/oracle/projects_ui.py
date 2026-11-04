"""Explicit existing-project selection or reviewed creation in a workspace."""
import hashlib
import html
import json
from datetime import time
from .client import ConnectionFailure
from .projects import list_workspaces,calendars_for_workspace,prepare_project,create_project,project_signature
from ..session_files import workspace as session_workspace


def render(st,session,preferences):
    ss=st.session_state
    st.subheader('Destino no Primavera')
    modes=['Usar projeto existente','Criar projeto novo em um workspace']
    def switch_mode():
        preferences['target_mode']=ss.flow_project_mode
        for key in ('flow_project','flow_scope','flow_snapshot','oracle_package','oracle_package_key','oracle_hours_plan','timing_plan'):ss.pop(key,None)
    mode=st.selectbox('Como deseja escolher o projeto?',modes,index=modes.index(preferences.get('target_mode',modes[0])),key='flow_project_mode',on_change=switch_mode)
    if mode==modes[0]:
        def remember_search():preferences['name']=ss.flow_search_name
        name=st.text_input('Nome completo do projeto no Oracle',value=preferences.get('name',''),placeholder='Ex.: TESTE - Projeto',key='flow_search_name',on_change=remember_search)
        if st.button('Buscar projeto no Oracle'):
            try:
                rows=session.projects_by_name(name)
                ss.flow_candidates={p['projectId']:p for p in rows if p['projectName'].strip().casefold()==name.strip().casefold()}
                ss.flow_search_message='Projetos correspondentes: '+str(len(ss.flow_candidates))
            except ConnectionFailure as exc:ss.flow_candidates={};ss.flow_search_message=str(exc)
        if ss.get('flow_search_message'):st.info(ss.flow_search_message)
        candidates=ss.get('flow_candidates',{})
        if candidates:
            options=[None]+sorted(candidates)
            chosen=st.selectbox('Projeto que receberá o planejamento',options,index=0,
                format_func=lambda pid:'Selecione…' if pid is None else html.unescape(candidates[pid]['projectName'])+' · ID '+str(pid),key='flow_choice')
            if st.button('Usar este projeto',disabled=chosen is None):ss.flow_project=candidates[chosen]
        return ss.get('flow_project')
    return new_project(st,session)


def new_project(st,session):
    ss=st.session_state;saved=ss.setdefault('new_project_inputs',{})
    st.caption('Workspace é a pasta do Primavera onde o projeto ficará. Nesta versão, os nomes de novos projetos devem começar com TESTE.')
    st.caption('A criação depende das permissões da sua conta no workspace selecionado.')
    if st.button('Consultar workspaces disponíveis'):
        try:
            ss.oracle_workspaces=list_workspaces(session)
            ss.new_project_message=('info','Workspaces retornados: '+str(len(ss.oracle_workspaces)))
        except ConnectionFailure as exc:ss.new_project_message=('error',str(exc))
    candidates=ss.get('oracle_workspaces',[])
    if not candidates:
        if ss.get('new_project_message'):
            level,message=ss.new_project_message;getattr(st,level)(message)
        return None
    by_id={r['workspaceId']:r for r in candidates};options=[None]+list(by_id)
    def remember(key,widget):saved[key]=ss[widget]
    def settings(key,widget,default):return {'value':saved.get(key,default),'key':widget,'on_change':remember,'args':(key,widget)}
    selected=saved.get('workspaceId')
    if selected not in by_id:selected=None
    def change_workspace():
        saved['workspaceId']=ss.new_project_workspace;saved['calendarId']=None
        ss.pop('new_project_calendar_context',None);ss.pop('new_project_calendars',None)
    wid=st.selectbox('Workspace onde criar o projeto',options,index=options.index(selected),
        format_func=lambda value:'Selecione…' if value is None else by_id[value]['caminho']+' · ID '+str(value),
        key='new_project_workspace',on_change=change_workspace)
    if wid is None:return None
    target=by_id[wid]
    default_name=str(ss.get('settings',{}).get('project','')).strip()
    if default_name and not default_name.upper().startswith('TESTE'):default_name='TESTE - '+default_name
    name=st.text_input('Nome do novo projeto',placeholder='TESTE - Nome do projeto',**settings('name','new_project_name',default_name))
    code=st.text_input('Código do novo projeto',placeholder='Ex.: BL1120-0011-T2',**settings('code','new_project_code',''))
    st.caption('O código identifica o projeto no Oracle e não pode repetir um código existente no workspace. O ID numérico será gerado pelo Oracle.')
    a,b=st.columns(2)
    with a:start=st.date_input('Data de início do novo projeto',format='DD/MM/YYYY',**settings('start','new_project_start',ss.get('workforce_inputs',{}).get('start')))
    with b:clock=st.time_input('Horário de início (Brasília)',**settings('clock','new_project_clock',time(8)))
    st.caption('A data também será a referência inicial dos dados do projeto. O status inicial será Planejado.')
    if st.button('Consultar calendários desse workspace'):
        try:
            ss.new_project_calendars=calendars_for_workspace(session,wid);ss.new_project_calendar_context=wid
            ss.new_project_calendar_message=None
        except ConnectionFailure as exc:ss.new_project_calendar_message=str(exc)
    if ss.get('new_project_calendar_message'):st.info(ss.new_project_calendar_message)
    calendars=ss.get('new_project_calendars',[]) if ss.get('new_project_calendar_context')==wid else []
    calendar_by_id={r['calendarId']:r for r in calendars};calendar_options=[None]+list(calendar_by_id)
    selected_calendar=saved.get('calendarId')
    if selected_calendar not in calendar_by_id:selected_calendar=None
    cid=st.selectbox('Calendário do novo projeto',calendar_options,index=calendar_options.index(selected_calendar),
        format_func=lambda value:'Usar o padrão definido pelo Oracle' if value is None else html.unescape(str(calendar_by_id[value]['calendarName']))+' · ID '+str(value),
        key='new_project_calendar',on_change=remember,args=('calendarId','new_project_calendar'))
    signature=hashlib.sha256(json.dumps({'workspace':target,'name':name,'code':code,'start':start.isoformat() if start else None,
        'clock':clock.isoformat(),'calendarId':cid},sort_keys=True).encode()).hexdigest()
    if ss.get('new_project_preview_input')!=signature:
        ss.pop('new_project_plan',None);ss.pop('new_project_message',None)
    if st.button('Preparar criação do projeto'):
        ss.new_project_preview_input=signature
        ss.pop('new_project_plan',None)
        try:
            with st.spinner('Conferindo workspace, calendário e código…'):
                ss.new_project_plan=prepare_project(session,target,code,name,start,clock,cid)
            ss.new_project_preview_input=signature;ss.new_project_message=('success','Prévia conferida. Nenhum projeto foi criado ainda.')
        except (ConnectionFailure,ValueError,KeyError,TypeError,OSError) as exc:
            ss.new_project_message=('error',str(exc) if isinstance(exc,ConnectionFailure) else 'Confira os campos do novo projeto.')
    plan=ss.get('new_project_plan')
    if plan:
        p=plan['payload']
        st.subheader('Confira o novo projeto')
        st.dataframe([{'Campo':'Workspace','Valor':target['caminho']+' · ID '+str(wid)},
            {'Campo':'Nome','Valor':p['projectName']},{'Campo':'Código','Valor':p['projectCode']},
            {'Campo':'Início / referência inicial','Valor':p['planStartDate']},
            {'Campo':'Calendário','Valor':str(plan['calendarName'] or 'Padrão definido pelo Oracle')},
            {'Campo':'Status inicial','Valor':'Planejado'}],hide_index=True)
        st.caption(plan['aviso'])
        confirmation=st.text_input('Para criar neste workspace, digite CRIAR '+p['projectCode'],key='new_project_confirmation_'+signature)
        if st.button('Criar projeto no Oracle',type='primary',disabled=confirmation.strip()!='CRIAR '+p['projectCode']):
            path=session_workspace(ss)/'project_creation'/(project_signature(plan)+'.json')
            try:
                with st.spinner('Criando e conferindo o projeto…'):
                    result=create_project(session,plan,path)
                ss.new_project_result=result;ss.new_project_result_input=signature;ss.flow_project=result
                workforce=ss.setdefault('workforce_inputs',{})
                if not workforce.get('start'):workforce['start']=start
                ss.new_project_message=('success','Projeto criado e conferido: '+html.unescape(result['projectName'])+' · ID '+str(result['projectId'])+'. Continue pela estrutura abaixo.')
            except (ConnectionFailure,ValueError,KeyError,TypeError,OSError) as exc:
                ss.new_project_message=('error',str(exc) if isinstance(exc,ConnectionFailure) else 'Criação interrompida. Confira antes de repetir.')
    if ss.get('new_project_message'):
        level,message=ss.new_project_message;getattr(st,level)(message)
    if ss.get('new_project_result_input')==signature:return ss.get('new_project_result')
    return None
