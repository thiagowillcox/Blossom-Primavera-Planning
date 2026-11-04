"""Generate, choose, inspect, create/recover and assign hours in one browser session."""
import hashlib
import html
import json
from .client import ConnectionFailure
from .connection_ui import render as connection
from .structure import IntegrationSession,prepare_structure,inspect_structure,sync_structure,guard_previous
from .draft import durable_write
from .effort import load_package
from ..session_files import project_files


def render(st):
    from ..ui import heading
    ss=st.session_state
    heading('05 · PRIMAVERA','Do pré-cronograma ao Oracle, aqui no site.',
        'Escolha o projeto, confira o que já existe e avance pela estrutura, horas e prazos.')
    st.caption('Sem histórico permanente: os dados ficam nesta sessão. As consultas ao Oracle evitam recriar o que já está compatível.')
    preferences=ss.setdefault('flow_preferences',{})
    modes=['Pré-cronograma gerado no site','Excel de um trabalho anterior','Importar registros antigos (opcional)']
    def remember_mode():preferences['mode']=ss.flow_mode
    mode=st.selectbox('Base para integração',modes,index=modes.index(preferences.get('mode',modes[0])),key='flow_mode',on_change=remember_mode)
    if mode==modes[2]:
        from .web_ui import render as legacy
        legacy(st);return
    if mode==modes[0]:
        if not ss.get('result'):
            st.info('Envie a LD em Arquivos e gere o pré-cronograma. Ele aparecerá aqui automaticamente, sem baixar nem reenviar Excel ou JSON.')
            st.button('Ir para Arquivos',on_click=lambda:ss.update(_go='Arquivos'))
            return
        excel=ss.result[1]['pre_cronograma.xlsx']
        st.success('Pré-cronograma desta sessão pronto para integração.')
    else:
        def remember_excel():
            value=ss.get('flow_excel_upload')
            ss.flow_imported_excel=(value.name,value.getvalue()) if value else None
        st.file_uploader('Pré-cronograma Excel anterior',type=['xlsx'],key='flow_excel_upload',on_change=remember_excel)
        if not ss.get('flow_imported_excel'):
            st.info('Carregue somente o Excel anterior. Vamos reconhecer a estrutura diretamente no Oracle, sem exigir o arquivo de registro.');return
        filename,excel=ss.flow_imported_excel;st.caption('Arquivo desta sessão: '+filename)
    session=connection(st,IntegrationSession)
    if not session:return
    st.subheader('Escolha o projeto de teste')
    def remember_search():preferences['name']=ss.flow_search_name
    name=st.text_input('Nome completo do projeto no Oracle',value=preferences.get('name',''),placeholder='Ex.: TESTE - Projeto',key='flow_search_name',on_change=remember_search)
    if st.button('Buscar projeto no Oracle'):
        try:
            rows=session.projects_by_name(name)
            ss.flow_candidates={p['projectId']:p for p in rows if p['projectName'].strip().casefold()==name.strip().casefold()}
            ss.flow_search_message='Projetos correspondentes: '+str(len(ss.flow_candidates))
        except ConnectionFailure as exc:
            ss.flow_candidates={};ss.flow_search_message=str(exc)
    if ss.get('flow_search_message'):st.info(ss.flow_search_message)
    candidates=ss.get('flow_candidates',{})
    if candidates:
        options=[None]+sorted(candidates)
        chosen=st.selectbox('Projeto que receberá o planejamento',options,index=0,
            format_func=lambda pid:'Selecione…' if pid is None else html.unescape(candidates[pid]['projectName'])+' · ID '+str(pid),key='flow_choice')
        if st.button('Usar este projeto',disabled=chosen is None):ss.flow_project=candidates[chosen]
    project=ss.get('flow_project')
    if not project:return
    scope=hashlib.sha256(excel+json.dumps(project,sort_keys=True).encode()).hexdigest()
    if ss.get('flow_scope')!=scope:
        for key in ('flow_plan','flow_snapshot','flow_feedback','oracle_package','oracle_package_key','oracle_catalog','oracle_project',
            'oracle_hours_plan','oracle_hours_ready','oracle_hours_result','oracle_hours_feedback','oracle_hours_diagnostic','timing_plan'):
            ss.pop(key,None)
        try:
            plan,report=prepare_structure(excel,project)
            ss.flow_plan=plan;ss.flow_scope=scope
        except (ConnectionFailure,ValueError,KeyError,TypeError,OSError):
            st.error('Não foi possível conferir o pré-cronograma. Gere novamente pelo site ou confira o arquivo escolhido.');return
    plan=ss.flow_plan;pid=project['projectId'];source=plan['origem']['xlsx_sha256']
    storage=project_files(ss,pid,source);journal=storage/'registro_estrutura.json'
    st.subheader('Estrutura do projeto')
    st.write(html.unescape(project['projectName'])+' · ID '+str(pid))
    st.write(f"Prévia: {len(plan['wbs'])} grupos, {len(plan['activities'])} atividades e {len(plan['relationships'])} ligações.")
    st.caption('Só criamos itens ausentes e compatíveis com a prévia. Grupos, atividades e ligações diferentes bloqueiam a operação; não são apagados nem substituídos.')
    if st.button('Conferir estrutura no Oracle (sem enviar)'):
        ss.pop('flow_snapshot',None)
        try:
            with st.spinner('Consultando a estrutura existente…'):
                root,state=inspect_structure(session,plan)
                if journal.exists():guard_previous(json.loads(journal.read_text()),state)
            ss.flow_snapshot=state;ss.flow_feedback=('success','Estrutura consultada e comparada com a prévia.')
        except (ConnectionFailure,ValueError,KeyError,TypeError,OSError) as exc:
            ss.flow_feedback=('error',str(exc) if isinstance(exc,ConnectionFailure) else 'Não foi possível conferir a estrutura.')
    snapshot=ss.get('flow_snapshot')
    if snapshot:
        missing={'grupos':len(plan['wbs'])-len(snapshot['wbs']),'atividades':len(plan['activities'])-len(snapshot['atividades']),
            'ligações':len(plan['relationships'])-len(snapshot['relacionamentos'])}
        st.info(f"Já conferidos: {len(snapshot['wbs'])} grupos, {len(snapshot['atividades'])} atividades e {len(snapshot['relacionamentos'])} ligações.")
        if snapshot['estado']=='estrutura_conferida_prazos_e_hh_pendentes':
            st.success('A estrutura já está completa e compatível. Podemos seguir para as horas sem recriá-la.')
            durable_write(journal,snapshot)
            try:ss.oracle_package=load_package(excel,json.dumps(snapshot).encode())
            except (ConnectionFailure,ValueError,KeyError,TypeError):st.error('A estrutura corresponde, mas o pacote de horas precisa de conferência.');return
        else:
            st.write('Falta criar: '+', '.join(str(v)+' '+k for k,v in missing.items()))
            st.caption('Esta etapa cria somente a estrutura, ainda sem HH por função, taxas ou prazos definidos pelo programa.')
            text=st.text_input('Para criar os itens restantes, digite ENVIAR ESTRUTURA '+str(pid),key='flow_confirm_'+scope)
            if st.button('Enviar ou continuar estrutura',type='primary',disabled=text.strip()!=f'ENVIAR ESTRUTURA {pid}'):
                lock=storage.parent/'envio.lock'
                try:lock.mkdir()
                except FileExistsError:st.error('Já há uma operação neste projeto nesta sessão. Aguarde.');return
                try:
                    with st.spinner('Enviando e conferindo a estrutura…'):
                        progress=st.empty();state=sync_structure(session,plan,journal,progress.info)
                    ss.flow_snapshot=state;ss.oracle_package=load_package(excel,json.dumps(state).encode())
                    ss.flow_feedback=('success','Estrutura criada e conferida por nova consulta. Siga para as horas abaixo.')
                except (ConnectionFailure,ValueError,KeyError,TypeError,OSError) as exc:
                    ss.flow_feedback=('error',str(exc) if isinstance(exc,ConnectionFailure) else 'Operação interrompida. Consulte a estrutura antes de repetir.')
                    ss.pop('flow_snapshot',None)
                finally:lock.rmdir()
    if ss.get('flow_feedback'):
        level,message=ss.flow_feedback;getattr(st,level)(message)
    if journal.exists():
        with st.expander('Cópia opcional do registro desta sessão'):
            st.caption('Você não precisa baixar nem reenviar este arquivo para continuar aqui.')
            st.download_button('Baixar registro da estrutura',journal.read_bytes(),'envio_rascunho_'+str(pid)+'.json','application/json')
    package=ss.get('oracle_package')
    if package and package['projectId']==pid and package['source_sha256']==source:
        st.divider()
        from .web_ui import render as hours
        hours(st,package=package)
