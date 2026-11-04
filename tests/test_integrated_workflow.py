import json
import pytest
from pathlib import Path
from streamlit.testing.v1 import AppTest
from blossom.oracle.effort import load_package
from blossom.oracle.structure import IntegrationSession
from blossom.session_files import project_files,clear_session
from test_oracle_effort import files,EffortOracle,PROJECT
from test_oracle import Response

ROOT=Path(__file__).resolve().parents[1]


class FlowOracle(EffortOracle):
 def __init__(self,fresh):
  super().__init__()
  self.groups=[{'wbsId':100,'projectId':7,'parentId':None}]
  self.activities=[]
  if not fresh:
   self.groups.append({'wbsId':101,'projectId':7,'parentId':100,'wbsCode':'1','wbsName':'Fase'})
   self.activities.append(dict(self.activity,activityType='ACTIVITY'))
 def open(self,req,timeout):
  route=req.full_url.split('/api/restapi/')[-1]
  if len(self.calls)>=2:
   if req.get_method()=='GET':
    if route.startswith('project/name/'):
     self.calls.append(req);return Response(json.dumps([PROJECT]).encode())
    if route=='wbs/project/7':
     self.calls.append(req);return Response(json.dumps(self.groups).encode())
    if route=='activity/project/7':
     self.calls.append(req);return Response(json.dumps(self.activities).encode())
    if route.startswith('relationship/projectRelationshipCode?'):
     self.calls.append(req);return Response(b'[]')
   if req.get_method()=='POST' and route=='wbs':
    self.calls.append(req);row=dict(json.loads(req.data),wbsId=100+len(self.groups));self.groups.append(row)
    return Response(json.dumps(row).encode(),status=201)
   if req.get_method()=='POST' and route=='activity/batch':
    self.calls.append(req);rows=[dict(r,activityId=201+i+len(self.activities)) for i,r in enumerate(json.loads(req.data))]
    self.activities.extend(rows);return Response(json.dumps(rows).encode(),status=201)
  return super().open(req,timeout)


@pytest.mark.parametrize('fresh',[False,True])
def test_generate_to_structure_and_hours_without_downloading_or_importing_json(tmp_path,monkeypatch,fresh):
 import blossom.oracle.workflow_ui as workflow
 excel,record=files(tmp_path);p=load_package(excel,record);oracle=FlowOracle(fresh)
 monkeypatch.setattr(workflow,'IntegrationSession',lambda username,password:IntegrationSession(username,password,opener=oracle))
 app=AppTest.from_file(str(ROOT/'app.py'))
 app.session_state['workflow_version']='ld-relacoes-v4';app.session_state['navigation']='Primavera'
 app.session_state['result']=(p['tables'],{'pre_cronograma.xlsx':excel})
 app.run(timeout=30)
 assert not app.exception
 assert not app.get('file_uploader')
 next(t for t in app.text_input if t.label=='Usuário / e-mail Oracle').set_value('test')
 next(t for t in app.text_input if t.label=='Senha Oracle').set_value('fictional-password')
 next(b for b in app.button if b.label=='Conectar ao Oracle').click().run(timeout=30)
 assert not app.exception
 next(t for t in app.text_input if t.label=='Nome completo do projeto no Oracle').set_value('TESTE HH')
 next(b for b in app.button if b.label=='Buscar projeto no Oracle').click().run()
 next(s for s in app.selectbox if s.label=='Projeto que receberá o planejamento').set_value(7).run()
 next(b for b in app.button if b.label=='Usar este projeto').click().run()
 next(b for b in app.button if b.label=='Conferir estrutura no Oracle (sem enviar)').click().run(timeout=30)
 assert not app.exception
 if fresh:
  assert next(b for b in app.button if b.label=='Enviar ou continuar estrutura').disabled
  next(t for t in app.text_input if t.label.startswith('Para criar os itens restantes')).set_value('ENVIAR ESTRUTURA 7').run()
  next(b for b in app.button if b.label=='Enviar ou continuar estrutura').click().run(timeout=30)
 else:
  assert [r.get_method() for r in oracle.calls].count('POST')==1 # only authentication
 assert not app.exception
 assert app.session_state['oracle_package']['projectId']==7
 assert len(oracle.groups)==2 and len(oracle.activities)==1
 assert not any('Registro estrutural' in w.label or 'Excel original' in w.label for w in app.get('file_uploader'))
 next(b for b in app.button if b.label=='Consultar projeto e funções disponíveis').click().run(timeout=30)
 next(c for c in app.checkbox if c.label.startswith('Conferi a correspondência')).check().run()
 next(b for b in app.button if b.label=='Preparar prévia das horas').click().run()
 assert not app.exception
 next(t for t in app.text_input if t.label.startswith('Para gravar no projeto')).set_value('ENVIAR HORAS 7').run()
 next(b for b in app.button if b.label=='Enviar e conferir horas no Oracle').click().run(timeout=30)
 assert not app.exception and len(oracle.assignments)==1
 assert app.session_state['oracle_hours_result']['estado']=='horas_conferidas'
 # Starting over removes session data/files, but not the Oracle project.
 path=Path(app.session_state['_session_files'].name)
 next(b for b in app.button if b.label=='Novo planejamento / limpar sessão').click().run()
 assert not app.exception and not path.exists()
 assert 'oracle_package' not in app.session_state and 'oracle_session' not in app.session_state
 assert len(oracle.activities)==1


def test_temporary_files_are_isolated_between_sessions_and_cleared():
 a={};b={};sha='a'*64
 first=project_files(a,7,sha);second=project_files(b,7,sha)
 assert first!=second
 (first/'registro_horas.json').write_text('private session state')
 assert not (second/'registro_horas.json').exists()
 clear_session(a)
 assert not first.exists() and second.exists()
 clear_session(b)
 assert not second.exists()
