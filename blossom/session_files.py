"""Temporary files belong to one Streamlit session, never a shared project folder."""
from pathlib import Path
from tempfile import TemporaryDirectory


def workspace(state,base=None):
    if '_session_files' not in state:
        state['_session_files']=TemporaryDirectory(prefix='blossom-session-',dir=base)
    return Path(state['_session_files'].name)


def project_files(state,project_id,source_sha,base=None):
    if type(project_id) is not int or project_id<=0 or not isinstance(source_sha,str) or len(source_sha)!=64 or set(source_sha)-set('0123456789abcdef'):
        raise ValueError('Projeto ou origem inválida para esta sessão.')
    path=workspace(state,base)/str(project_id)/source_sha
    path.mkdir(parents=True,exist_ok=True)
    return path


def clear_session(state):
    session=state.get('oracle_session')
    if session:session.close()
    temporary=state.get('_session_files')
    if temporary:temporary.cleanup()
    for key in list(state):state.pop(key,None)
