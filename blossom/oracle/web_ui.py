"""Session-isolated Oracle role-hours UI. Never cache tokens or credentials."""
import hashlib
import html
import json
from pathlib import Path
from tempfile import gettempdir
import time
from .client import ConnectionFailure
from .effort import EffortSession,load_package,plan_hours,partition_hours,sync_hours,ROLE_CODES
from .draft import durable_write


def disconnect(ss):
    session=ss.get('oracle_session')
    if session:session.close()
    for key in list(ss):
        if key.startswith('oracle_') and key not in ('oracle_package','oracle_package_key'):ss.pop(key,None)


def render(st):
    from ..ui import heading
    from ..team_ui import hh_label
    heading('05 · PRIMAVERA','As horas de cada função na atividade certa.',
        'Importe o cronograma já enviado, confira as funções e revise a prévia antes de gravar no Oracle.')
    st.caption('Esta etapa complementa a estrutura existente. Não recria grupos, atividades ou ligações.')
    excel=st.file_uploader('Excel original usado no envio concluído',type=['xlsx'],key='hours_excel_upload')
    record=st.file_uploader('Registro estrutural concluído — envio_rascunho_<ID>.json',type=['json'],key='hours_structure_upload')
    if not excel or not record:
        st.info('O registro está na pasta output do programa usado no seu computador. Precisamos dele para reconhecer os IDs já criados.');return
    digest=hashlib.sha256(excel.getvalue()+record.getvalue()).hexdigest()
    ss=st.session_state
    if ss.get('oracle_package_key')!=digest:
        for key in ('oracle_package','oracle_package_key','oracle_catalog','oracle_project','oracle_hours_plan','oracle_hours_result'):ss.pop(key,None)
        try:
            ss.oracle_package=load_package(excel.getvalue(),record.getvalue());ss.oracle_package_key=digest
        except (ConnectionFailure,ValueError,KeyError,TypeError,OSError):
            st.error('O Excel e o registro não correspondem a um envio estrutural concluído. Use os mesmos arquivos originais.');return
    package=ss.oracle_package;pid=package['projectId']
    st.write('Projeto do registro: **'+str(pid)+'**')
    summary=[{'Função da LD':role,'HH planejadas':hh_label(value)} for role,value in package['hh_por_funcao'].items()]
    st.dataframe(summary,hide_index=True)
    st.metric('Total de HH planejadas',hh_label(package['hh_planejadas']))
    with st.expander('Horas por atividade e função'):
        names={a['id']:a['nome'] for a in package['tables']['Atividades']}
        st.dataframe([{'Atividade':names[a['atividade_id']],'Função':a['funcao'],'HH':hh_label(a['hh'])} for a in package['tables']['Atribuicoes_Funcoes']],hide_index=True)
    def connect():
        username=ss.get('oracle_login','');password=ss.get('oracle_password','')
        ss.oracle_password=''
        try:
            old=ss.pop('oracle_session',None)
            if old:old.close()
            session=EffortSession(username,password);session.test_connection()
            ss.oracle_session=session;ss.oracle_connected_at=time.time();ss.pop('oracle_message',None)
            for key in ('oracle_catalog','oracle_project','oracle_hours_plan'):ss.pop(key,None)
        except ConnectionFailure as exc:
            if 'session' in locals():session.close()
            ss.oracle_message=str(exc)
    session=ss.get('oracle_session')
    if session and time.time()-ss.get('oracle_connected_at',0)>1200:
        disconnect(ss);session=None;st.info('A sessão de integração expirou. Entre novamente para continuar.')
    with st.expander('Conexão Oracle',expanded=session is None):
        st.caption('A senha é descartada após a autenticação. A conexão fica apenas nesta sessão e expira na próxima interação após 20 minutos. Não entra nos relatórios.')
        with st.form('oracle_connection'):
            st.text_input('Usuário / e-mail Oracle',key='oracle_login')
            st.text_input('Senha Oracle',type='password',key='oracle_password')
            st.form_submit_button('Conectar ao Oracle',on_click=connect)
        if ss.get('oracle_message'):st.error(ss.oracle_message)
        if session:st.button('Desconectar',on_click=disconnect,args=(ss,))
    session=ss.get('oracle_session')
    if not session:return
    if st.button('Consultar projeto e funções disponíveis'):
        try:
            with st.spinner('Conferindo atividades e consultando funções…'):
                project,catalog=session.catalog(package)
            ss.oracle_project=project;ss.oracle_catalog=catalog;ss.pop('oracle_hours_plan',None)
        except ConnectionFailure as exc:st.error(str(exc))
    if not ss.get('oracle_catalog'):return
    catalog=ss.oracle_catalog;project=ss.oracle_project
    st.subheader(html.unescape(project['projectName']))
    st.caption('Usamos apenas funções de mão de obra ativas já cadastradas. Cadastros globais e taxas não serão alterados.')
    role_by_id={r['resourceId']:r for r in catalog};mapping={}
    for role in package['hh_por_funcao']:
        candidates=[r['resourceId'] for r in catalog if r['resourceCode']==ROLE_CODES.get(role)]
        options=[None]+sorted(role_by_id)
        suggested=ss.get('oracle_hours_plan',{}).get('mapping',{}).get(role,candidates[0] if len(candidates)==1 else None)
        if suggested not in options:suggested=None
        selected=st.selectbox('Função Oracle para '+role,options,index=options.index(suggested),
            format_func=lambda rid:'Selecione…' if rid is None else html.unescape(str(role_by_id[rid]['resourceName']))+' · '+str(role_by_id[rid]['resourceCode'])+' · ID '+str(rid),key='role_map_'+digest+'_'+role)
        if selected is not None:mapping[role]=selected
    if ss.get('oracle_hours_plan') and ss.oracle_hours_plan['mapping']!=mapping:ss.pop('oracle_hours_plan',None)
    approved=st.checkbox('Conferi a correspondência de todas as funções',key='oracle_mapping_approved_'+digest)
    if st.button('Preparar prévia das horas',disabled=not approved):
        try:
            session.binding(package)
            plan=plan_hours(package,mapping,catalog)
            missing,found=partition_hours(plan,session.rows('assignment/project/'+str(pid)))
            ss.oracle_hours_plan=plan
            st.success(f"Prévia: {len(missing)} atribuições para criar e {len(found)} já conferidas no Oracle.")
        except (ConnectionFailure,ValueError,KeyError,TypeError) as exc:st.error(str(exc) if isinstance(exc,ConnectionFailure) else 'Não foi possível conferir a prévia de horas.')
    plan=ss.get('oracle_hours_plan')
    if not plan:return
    st.subheader('Confira antes de enviar')
    st.write(f"Projeto {pid} · {len(plan['payloads'])} atribuições · {plan['hh_planejadas']} HH")
    st.dataframe([{'Função LD':role,'Função Oracle':html.unescape(str(role_by_id[rid]['resourceName'])),'Código Oracle':role_by_id[rid]['resourceCode'],'HH':hh_label(package['hh_por_funcao'][role])} for role,rid in mapping.items()],hide_index=True)
    if plan['associar_funcoes']:st.info(str(len(plan['associar_funcoes']))+' funções existentes também serão associadas a este projeto.')
    st.caption('O envio não define prazos nem avanço. Custos eventualmente calculados pelo Oracle usam os cadastros existentes; não enviamos taxas.')
    st.download_button('Baixar prévia de horas',json.dumps(plan,ensure_ascii=False,indent=2),'previa_horas_oracle.json','application/json')
    storage=Path(gettempdir())/'blossom-effort'/str(pid)/package['source_sha256']
    storage.mkdir(parents=True,exist_ok=True)
    journal=storage/'registro_horas.json'
    previous=st.file_uploader('Registro de horas anterior, se precisar recuperar uma tentativa (opcional)',type=['json'],key='hours_previous_upload')
    if previous and not journal.exists():
        try:
            restored=json.loads(previous.getvalue())
            if restored.get('servidor')!=plan['servidor'] or restored.get('projectId')!=pid or restored.get('source_sha256')!=package['source_sha256']:raise ValueError()
            durable_write(journal,restored,exclusive=True)
        except (ValueError,KeyError,OSError):st.error('Registro de horas incompatível.');return
    text=st.text_input('Para gravar no projeto, digite ENVIAR HORAS '+str(pid),key='oracle_confirm_'+digest)
    if st.button('Enviar e conferir horas no Oracle',type='primary',disabled=not approved or text.strip()!=f'ENVIAR HORAS {pid}'):
        lock=storage.parent/'envio.lock'
        try:
            lock.mkdir()
        except FileExistsError:
            st.error('Já há um envio em andamento para esse projeto neste servidor. Aguarde.');return
        try:
            with st.spinner('Enviando e conferindo horas…'):
                progress=st.empty()
                result=sync_hours(session,package,plan,journal,progress.info)
                ss.oracle_hours_result=result
            st.success('Horas enviadas e conferidas por nova consulta: '+hh_label(result['hh_conferidas'])+' HH.')
        except (ConnectionFailure,ValueError,KeyError,TypeError,OSError) as exc:
            st.error(str(exc) if isinstance(exc,ConnectionFailure) else 'Envio interrompido. Preserve o registro e consulte o Oracle antes de repetir.')
        finally:lock.rmdir()
    if journal.exists():
        st.download_button('Baixar registro do envio de horas',journal.read_bytes(),'registro_horas_'+str(pid)+'.json','application/json')
        st.caption('Guarde esse registro. O disco do Streamlit pode ser reiniciado e ainda não há histórico persistente neste programa.')
    from .timing_ui import render as timing
    timing(st,session,package,ss.get('team_report'),storage)
