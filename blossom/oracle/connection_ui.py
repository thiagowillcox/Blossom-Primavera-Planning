"""Oracle authentication in the current browser session only."""
import time
from .client import ConnectionFailure
from .effort import EffortSession


def disconnect(state):
    session=state.get('oracle_session')
    if session:session.close()
    for key in list(state):
        if key.startswith('oracle_') and key not in ('oracle_package','oracle_package_key'):state.pop(key,None)


def render(st,session_class=EffortSession):
    state=st.session_state;session=state.get('oracle_session')
    if session and time.time()-state.get('oracle_connected_at',0)>1200:
        disconnect(state);session=None;st.info('A conexão expirou. Entre novamente para continuar.')
    def connect():
        username=state.get('oracle_login','');password=state.get('oracle_password','');state.oracle_password=''
        old=state.pop('oracle_session',None)
        if old:old.close()
        try:
            new=session_class(username,password);new.test_connection()
            state.oracle_session=new;state.oracle_connected_at=time.time();state.pop('oracle_message',None)
            for key in ('oracle_catalog','oracle_project','oracle_hours_plan','oracle_hours_ready'):state.pop(key,None)
        except ConnectionFailure as exc:
            if 'new' in locals():new.close()
            state.oracle_message=str(exc)
    with st.expander('Conexão Oracle',expanded=session is None):
        st.caption('Sua senha é descartada após entrar. A conexão pertence apenas a esta sessão e expira na próxima interação após 20 minutos.')
        with st.form('oracle_connection'):
            st.text_input('Usuário / e-mail Oracle',key='oracle_login')
            st.text_input('Senha Oracle',type='password',key='oracle_password')
            st.form_submit_button('Conectar ao Oracle',on_click=connect)
        if state.get('oracle_message'):st.error(state.oracle_message)
        if session:st.button('Desconectar',on_click=disconnect,args=(state,))
    return state.get('oracle_session')
