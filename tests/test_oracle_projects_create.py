import json
import urllib.error
from datetime import date,time
import pytest
from blossom.oracle.client import ConnectionFailure
from blossom.oracle.projects import list_workspaces,prepare_project,create_project,calendars_for_workspace
from blossom.oracle.structure import IntegrationSession
from test_oracle import FakeOracle,Response


WORKSPACE={'workspaceId':2,'workspaceName':'Engenharia','workspaceCode':'ENG','parentId':None}


class ProjectOracle(FakeOracle):
 def __init__(self):
  super().__init__();self.projects=[];self.workspaces=[WORKSPACE,{'workspaceId':3,'workspaceName':'BH','workspaceCode':'BH','parentId':2}]
  self.fail_after=False;self.wrong_workspace=False
 def open(self,request,timeout):
  if len(self.calls)<2:return super().open(request,timeout)
  self.calls.append(request);route=request.full_url.split('/api/restapi/')[1]
  if request.get_method()=='GET':
   if route=='workspace':rows=self.workspaces
   elif route.startswith('workspace/'):
    wid=int(route.split('/')[-1]);rows=next(w for w in self.workspaces if w['workspaceId']==wid)
   elif route.startswith('project/workspace/'):
    wid=int(route.split('/')[-1]);rows=[p for p in self.projects if p['workspaceId']==wid]
   elif route.startswith('project/'):
    pid=int(route.split('/')[-1]);rows=next(p for p in self.projects if p['projectId']==pid)
   elif route=='calendar/workspace/2':rows=[{'calendarId':4,'calendarName':'BH 8h','workspaceId':2,'projectId':None,'isAssignableToProject':True}]
   elif route=='calendar/workspace/3':rows=[]
   else:raise AssertionError(route)
   return Response(json.dumps(rows).encode())
  assert request.get_method()=='POST' and route=='project'
  payload=json.loads(request.data);row=dict(payload,projectId=100+len(self.projects))
  if self.wrong_workspace:row['workspaceId']=3
  self.projects.append(row)
  if self.fail_after:raise urllib.error.URLError('ambiguous server response not exported')
  return Response(json.dumps(row).encode(),status=201)


def session(oracle):
 s=IntegrationSession('test','fictional-password',opener=oracle);s.test_connection();return s


def test_workspace_hierarchy_and_inherited_calendars_are_readonly():
 oracle=ProjectOracle();s=session(oracle)
 rows=list_workspaces(s)
 assert next(r for r in rows if r['workspaceId']==3)['caminho']=='Engenharia / BH'
 assert calendars_for_workspace(s,3)[0]['calendarId']==4
 assert [r.get_method() for r in oracle.calls].count('POST')==1


def test_preview_does_not_create_and_actual_project_is_verified_in_selected_workspace(tmp_path):
 oracle=ProjectOracle();s=session(oracle)
 plan=prepare_project(s,WORKSPACE,'NEW','TESTE Novo',date(2026,10,13),time(8),4)
 assert not oracle.projects
 assert plan['payload']['workspaceId']==2
 assert plan['payload']['dataDate']=='2026-10-13T08:00:00-03:00'
 result=create_project(s,plan,tmp_path/'project.json')
 assert result['projectId']==100 and result['workspaceId']==2
 assert oracle.projects[0]['status']=='PLANNED'
 create_project(s,plan,tmp_path/'project.json')
 assert len(oracle.projects)==1
 assert [r.get_method() for r in oracle.calls].count('POST')==2 # authentication + create
 assert 'fictional-password' not in (tmp_path/'project.json').read_text()


def test_existing_project_code_is_not_reused_or_overwritten(tmp_path):
 oracle=ProjectOracle();s=session(oracle)
 oracle.projects=[{'projectId':99,'workspaceId':2,'projectCode':'NEW','projectName':'TESTE Existing'}]
 before=len(oracle.calls)
 with pytest.raises(ConnectionFailure,match='Já existe'):prepare_project(s,WORKSPACE,'new','TESTE Another',date(2026,10,13))
 assert all(r.get_method()=='GET' for r in oracle.calls[before:])
 assert len(oracle.projects)==1


def test_duplicate_appearing_after_preview_prevents_creation(tmp_path):
 oracle=ProjectOracle();s=session(oracle)
 plan=prepare_project(s,WORKSPACE,'NEW','TESTE Novo',date(2026,10,13))
 oracle.projects=[{'projectId':99,'workspaceId':2,'projectCode':'NEW','projectName':'TESTE Existing'}]
 before=len(oracle.calls)
 with pytest.raises(ConnectionFailure,match='Já existe'):create_project(s,plan,tmp_path/'project.json')
 assert all(r.get_method()=='GET' for r in oracle.calls[before:])
 assert not (tmp_path/'project.json').exists()


def test_lost_response_is_recovered_by_readback_without_a_second_create(tmp_path):
 oracle=ProjectOracle();s=session(oracle);plan=prepare_project(s,WORKSPACE,'NEW','TESTE Novo',date(2026,10,13))
 oracle.fail_after=True;path=tmp_path/'project.json'
 with pytest.raises(ConnectionFailure):create_project(s,plan,path)
 assert json.loads(path.read_text())['pendente']
 oracle.fail_after=False
 result=create_project(s,plan,path)
 assert result['projectId']==100 and len(oracle.projects)==1
 assert [r.get_method() for r in oracle.calls].count('POST')==2


def test_uncertain_unseen_creation_is_not_repeated(tmp_path):
 oracle=ProjectOracle();s=session(oracle);plan=prepare_project(s,WORKSPACE,'NEW','TESTE Novo',date(2026,10,13))
 oracle.fail_after=True;path=tmp_path/'project.json'
 with pytest.raises(ConnectionFailure):create_project(s,plan,path)
 oracle.projects.clear();oracle.fail_after=False;before=len(oracle.calls)
 with pytest.raises(ConnectionFailure,match='incerto'):create_project(s,plan,path)
 assert all(r.get_method()=='GET' for r in oracle.calls[before:])


def test_wrong_workspace_in_created_response_blocks_selection(tmp_path):
 oracle=ProjectOracle();s=session(oracle);plan=prepare_project(s,WORKSPACE,'NEW','TESTE Novo',date(2026,10,13))
 oracle.wrong_workspace=True
 with pytest.raises(ConnectionFailure,match='workspace'):create_project(s,plan,tmp_path/'project.json')
 assert len(oracle.projects)==1 # may exist; no retry or deletion
 assert json.loads((tmp_path/'project.json').read_text())['projectId']==100


@pytest.mark.parametrize('name,start',[('Produção',date(2026,10,13)),('TESTE Novo',None),('TESTE Novo','2026-10-13')])
def test_invalid_or_missing_fields_do_not_mutate(name,start):
 oracle=ProjectOracle();s=session(oracle);before=len(oracle.calls)
 with pytest.raises(ConnectionFailure):prepare_project(s,WORKSPACE,'NEW',name,start)
 assert len(oracle.calls)==before


def test_workspace_changed_since_preview_is_detected(tmp_path):
 oracle=ProjectOracle();s=session(oracle);original=dict(WORKSPACE)
 plan=prepare_project(s,original,'NEW','TESTE Novo',date(2026,10,13))
 oracle.workspaces=[dict(w,workspaceName='Changed') if w['workspaceId']==2 else w for w in oracle.workspaces]
 with pytest.raises(ConnectionFailure,match='mudou'):create_project(s,plan,tmp_path/'project.json')
 assert not oracle.projects


def test_project_creation_ui_requires_workspace_preview_and_explicit_confirmation(tmp_path,monkeypatch):
 from pathlib import Path
 from streamlit.testing.v1 import AppTest
 import blossom.oracle.workflow_ui as workflow
 from blossom.oracle.effort import load_package
 from test_oracle_effort import files
 excel,record=files(tmp_path);package=load_package(excel,record);oracle=ProjectOracle()
 monkeypatch.setattr(workflow,'IntegrationSession',lambda username,password:IntegrationSession(username,password,opener=oracle))
 root=Path(__file__).resolve().parents[1]
 app=AppTest.from_file(str(root/'app.py'))
 app.session_state['workflow_version']='ld-relacoes-v4';app.session_state['navigation']='Primavera'
 app.session_state['result']=(package['tables'],{'pre_cronograma.xlsx':excel})
 app.run(timeout=30)
 next(t for t in app.text_input if t.label=='Usuário / e-mail Oracle').set_value('test')
 next(t for t in app.text_input if t.label=='Senha Oracle').set_value('fictional-password')
 next(b for b in app.button if b.label=='Conectar ao Oracle').click().run()
 next(s for s in app.selectbox if s.label=='Como deseja escolher o projeto?').set_value('Criar projeto novo em um workspace').run()
 next(b for b in app.button if b.label=='Consultar workspaces disponíveis').click().run()
 next(s for s in app.selectbox if s.label=='Workspace onde criar o projeto').set_value(3).run()
 next(t for t in app.text_input if t.label=='Nome do novo projeto').set_value('TESTE Novo')
 next(t for t in app.text_input if t.label=='Código do novo projeto').set_value('NEW')
 app.date_input[0].set_value('2026-10-13').run()
 next(b for b in app.button if b.label=='Consultar calendários desse workspace').click().run()
 next(s for s in app.selectbox if s.label=='Calendário do novo projeto').set_value(4).run()
 next(b for b in app.button if b.label=='Preparar criação do projeto').click().run()
 assert not app.exception and not oracle.projects
 assert next(b for b in app.button if b.label=='Criar projeto no Oracle').disabled
 next(t for t in app.text_input if t.label.startswith('Para criar neste workspace')).set_value('CRIAR NEW').run()
 next(b for b in app.button if b.label=='Criar projeto no Oracle').click().run(timeout=30)
 assert not app.exception
 assert app.session_state['flow_project']['projectId']==100
 assert app.session_state['flow_project']['workspaceId']==3
 assert oracle.projects[0]['calendarId']==4
 assert [r.get_method() for r in oracle.calls].count('POST')==2
 assert any(b.label=='Conferir estrutura no Oracle (sem enviar)' for b in app.button)
 # Changing the form does not silently keep the old project's import controls active.
 next(t for t in app.text_input if t.label=='Código do novo projeto').set_value('OTHER').run()
 assert not any(b.label=='Conferir estrutura no Oracle (sem enviar)' for b in app.button)
 assert len(oracle.projects)==1


def test_creation_request_matches_the_uploaded_oracle_contract(tmp_path):
 from pathlib import Path
 oracle=ProjectOracle();s=session(oracle)
 plan=prepare_project(s,WORKSPACE,'NEW','TESTE Novo',date(2026,10,13),calendar_id=4)
 create_project(s,plan,tmp_path/'project.json')
 contract=json.loads((Path(__file__).parents[1]/'config/oracle_project_contract.json').read_text())['schema']
 request=next(r for r in oracle.calls if r.get_method()=='POST' and r.full_url.endswith('/api/restapi/project'))
 payload=json.loads(request.data)
 assert set(contract['required'])<=set(payload)
 for key,value in payload.items():
  spec=contract['properties'][key]
  if spec['type']=='integer':assert type(value) is int
  if spec['type']=='string':assert isinstance(value,str)
  if 'maxLength' in spec:assert len(value)<=spec['maxLength']
  if 'enum' in spec:assert value in spec['enum']
