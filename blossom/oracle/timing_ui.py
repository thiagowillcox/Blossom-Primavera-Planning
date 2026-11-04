import json
from .client import ConnectionFailure
from .draft import positive_id,durable_write
from .timing import timing_preview,send_timing
from .effort import partition_hours


def render(st,session,package,report,storage):
    st.divider();st.subheader('Prazos e agendamento no Oracle')
    st.caption('Primeiro, prepare a visão em Equipe e prazos usando a base Excel vinculado ao projeto Oracle. Datas e capacidades vazias permanecem pendentes.')
    ss=st.session_state;hours_plan=ss.get('oracle_hours_plan')
    if not hours_plan:return
    journal=storage/'registro_agendamento.json'
    uploaded=st.file_uploader('Registro de agendamento anterior, para consultar uma tentativa (opcional)',type=['json'],key='timing_record_upload')
    if uploaded and not journal.exists():
        try:
            restored=json.loads(uploaded.getvalue())
            if restored.get('projectId')!=package['projectId'] or restored.get('source_sha256')!=package['source_sha256']:raise ValueError()
            if restored.get('jobId') is not None:positive_id(restored['jobId'])
            durable_write(journal,restored,exclusive=True)
        except (ValueError,ConnectionFailure,OSError):st.error('Registro de agendamento incompatível.');return
    if st.button('Conferir calendário e preparar agendamento',disabled=not report):
        ss.pop('timing_plan',None)
        try:
            with st.spinner('Conferindo calendário, feriados e horas…'):
                ss.timing_plan=timing_preview(session,package,hours_plan,report)
        except (ConnectionFailure,ValueError,KeyError,TypeError) as exc:
            st.error(str(exc) if isinstance(exc,ConnectionFailure) else 'Não foi possível conferir os prazos.')
    plan=ss.get('timing_plan');journal=storage/'registro_agendamento.json'
    if plan and plan.get('source_sha256')==package['source_sha256']:
        st.write('Projeto: '+str(plan['projectId'])+' · Calendário Oracle: '+str(plan['calendarId'])+' · Início: '+plan['dataDate'])
        st.caption(plan['aviso'])
        st.download_button('Baixar prévia de agendamento',json.dumps(plan,ensure_ascii=False,indent=2),'previa_agendamento.json','application/json')
        consent=st.checkbox('Conferi a prévia e entendo que o Oracle recalculará datas pelo CPM, sem reproduzir automaticamente o nivelamento local',key='timing_consent')
        text=st.text_input('Para atualizar durações, início e solicitar o cálculo, digite AGENDAR '+str(plan['projectId']),key='timing_confirm')
        if st.button('Atualizar durações e solicitar agendamento',disabled=not consent or text.strip()!=f"AGENDAR {plan['projectId']}"):
            lock=storage.parent/'envio.lock'
            try:lock.mkdir()
            except FileExistsError:st.error('Já há uma operação em andamento para esse projeto neste servidor. Aguarde.');return
            try:
                with st.spinner('Atualizando prazos e solicitando o cálculo no Oracle…'):
                    state=send_timing(session,package,hours_plan,report,plan,journal)
                st.success('Solicitação registrada. Job '+str(state['jobId'])+'. Consulte o andamento abaixo.')
            except (ConnectionFailure,ValueError,KeyError,TypeError,OSError) as exc:
                st.error(str(exc) if isinstance(exc,ConnectionFailure) else 'Operação interrompida. Guarde o registro; não repita antes de conferir.')
            finally:lock.rmdir()
    if journal.exists():
        try:state=json.loads(journal.read_text())
        except (ValueError,OSError):st.error('O registro de agendamento não pôde ser lido. Preserve o arquivo para conferência.');return
        st.download_button('Baixar registro do agendamento',journal.read_bytes(),'registro_agendamento_'+str(package['projectId'])+'.json','application/json')
        if state.get('jobId') and st.button('Consultar andamento do cálculo'):
            try:
                result=session.read('action/jobStatus/'+str(positive_id(state['jobId'])))
                if not isinstance(result,dict) or not result.get('jobStatus'):raise ConnectionFailure('Status do job não reconhecido.')
                status=result['jobStatus'];st.write('Estado informado pelo Oracle: '+str(status))
                if status=='COMPLETED':
                    missing,_=partition_hours(hours_plan,session.rows('assignment/project/'+str(package['projectId'])))
                    if missing:raise ConnectionFailure('O cálculo terminou, mas a conferência das horas está incompleta.')
                    st.success('O cálculo terminou e as horas foram conferidas novamente. Confira as datas e a distribuição nas telas do projeto.')
                elif status in ('FAILED','COMPLETED_WITH_ERRORS','REJECTED','COMPLETED_WITH_WARNINGS'):st.warning('O cálculo precisa de conferência no Oracle. Veja os avisos do projeto.')
            except ConnectionFailure as exc:st.error(str(exc))
