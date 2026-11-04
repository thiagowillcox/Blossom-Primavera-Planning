import hashlib,json
from pathlib import Path
import urllib.error
import openpyxl
import pytest
from blossom.oracle.client import SERVER,ConnectionFailure
from blossom.oracle.effort import EffortSession,load_package,plan_hours,sync_hours,partition_hours
from test_oracle import FakeOracle,Response
from test_oracle_preview import make_files


ROLE={'resourceId':888,'resourceCode':'BL-ENG-PL','resourceName':'Engenheiro Pleno','resourceClass':'ROLE','resourceType':'LABOR','resourceStatus':'ACTIVE','workspaceId':2}
PROJECT={'projectId':7,'projectName':'TESTE HH','projectCode':'LAB','workspaceId':2,'workspaceCode':'WS','calendarId':4}


def files(tmp_path):
 path,_,_=make_files(tmp_path)
 book=openpyxl.load_workbook(path)
 for sheet,fields in [('WBS',{'codigo':'1','nome':'Fase'}),('Atividades',{'nome':'Atividade'}),('Atribuicoes_Funcoes',{'id':'AF-1','funcao':'EPleno'})]:
  target=book[sheet]
  for field,value in fields.items():
   col=target.max_column+1;target.cell(1,col,field);target.cell(2,col,value)
 book['Parametros'].append(['versao_motor','0.5.0'])
 book.save(path);book.close()
 record={'servidor':SERVER,'projectId':7,'estado':'estrutura_conferida_prazos_e_hh_pendentes','solicitacao_pendente':None,
   'origem':{'xlsx_sha256':hashlib.sha256(path.read_bytes()).hexdigest()},'atividades':{'a':201},'wbs':{'w':101}}
 return path.read_bytes(),json.dumps(record).encode()


class EffortOracle(FakeOracle):
 def __init__(self,fail=False):
  super().__init__();self.assigned=False;self.assignments=[];self.fail=fail
  self.activity={'activityId':201,'projectId':7,'activityCode':'a','activityName':'Atividade','wbsId':101,'activityStatus':'NOT_STARTED','calendar':4,'plannedDuration':8,'remainingDuration':8}
 def open(self,request,timeout):
  if len(self.calls)<2:return super().open(request,timeout)
  self.calls.append(request);route=request.full_url.split('/api/restapi/')[1]
  if request.get_method()=='GET':
   if route=='project/7':result=PROJECT
   elif route=='activity/project/7':result=[self.activity]
   elif route=='wbs/project/7':result=[{'wbsId':100,'projectId':7,'parentId':None},{'wbsId':101,'projectId':7,'parentId':100,'wbsCode':'1','wbsName':'Fase'}]
   elif route=='resource/projectId/7':result=[ROLE] if self.assigned else []
   elif route=='resource/workspace/2':result=[ROLE]
   elif route=='workspace/2':result={'workspaceId':2,'parentId':None}
   elif route=='assignment/project/7':result=self.assignments
   else:raise AssertionError(route)
   return Response(json.dumps(result).encode())
  assert request.get_method()=='POST'
  if route=='resource/888/assign/project/7':self.assigned=True;return Response(b'',status=204)
  assert route=='assignment/batch'
  payload=json.loads(request.data)
  rows=[dict(p,assignmentId=900+len(self.assignments)+i,actualUnits=0) for i,p in enumerate(payload)]
  self.assignments.extend(rows)
  if self.fail:raise urllib.error.URLError('unknown after creation')
  return Response(json.dumps(list(reversed(rows))).encode(),status=201)


def session(oracle):
 s=EffortSession('test','fictional-password',opener=oracle);s.test_connection();return s


def test_package_must_match_exact_completed_structural_upload(tmp_path):
 excel,record=files(tmp_path);p=load_package(excel,record)
 assert p['hh_planejadas']=='10' and p['hh_por_funcao']=={'EPleno':'10'}
 with pytest.raises(ConnectionFailure):load_package(excel+b'changed',record)
 r=json.loads(record);r['estado']='interrompido'
 with pytest.raises(ConnectionFailure):load_package(excel,json.dumps(r).encode())


def test_hours_create_role_assignments_without_dates_or_duration_and_retry_is_idempotent(tmp_path):
 package=load_package(*files(tmp_path));oracle=EffortOracle();s=session(oracle)
 _,catalog=s.catalog(package);plan=plan_hours(package,{'EPleno':888},catalog)
 payload=plan['payloads'][0]
 assert payload['plannedUnits']==10 and payload['remainingUnits']==10
 assert payload['resourceClass']=='ROLE' and payload['driveActivityDates'] is False
 assert not {'plannedDuration','plannedStart','actualUnits','pricePerUnit'}&set(payload)
 path=tmp_path/'hours.json';result=sync_hours(s,package,plan,path)
 assert result['hh_conferidas']=='10.0' and result['estado']=='horas_conferidas'
 assert len(oracle.assignments)==1 and oracle.assigned
 # A refreshed catalog marks the role already assigned; that does not change operation identity.
 _,catalog=s.catalog(package);plan=plan_hours(package,{'EPleno':888},catalog)
 sync_hours(s,package,plan,path)
 assert len(oracle.assignments)==1
 assert 'fictional-password' not in path.read_text()


def test_partial_uncertain_batch_is_adopted_after_readback_without_duplicate_post(tmp_path):
 p=load_package(*files(tmp_path));oracle=EffortOracle(fail=True);s=session(oracle)
 _,catalog=s.catalog(p);plan=plan_hours(p,{'EPleno':888},catalog);path=tmp_path/'hours.json'
 with pytest.raises(ConnectionFailure):sync_hours(s,p,plan,path)
 assert json.loads(path.read_text())['pendente']['tipo']=='atribuicoes'
 assert len(oracle.assignments)==1
 oracle.fail=False
 sync_hours(s,p,plan,path)
 assert len(oracle.assignments)==1
 assert sum(r.full_url.endswith('/assignment/batch') for r in oracle.calls)==1


def test_unknown_unseen_previous_batch_is_not_repeated(tmp_path):
 p=load_package(*files(tmp_path));oracle=EffortOracle(fail=True);s=session(oracle)
 _,catalog=s.catalog(p);plan=plan_hours(p,{'EPleno':888},catalog);path=tmp_path/'hours.json'
 with pytest.raises(ConnectionFailure):sync_hours(s,p,plan,path)
 oracle.assignments.clear();oracle.fail=False
 before=len(oracle.calls)
 with pytest.raises(ConnectionFailure,match='incerto'):sync_hours(s,p,plan,path)
 assert all(r.get_method()=='GET' for r in oracle.calls[before:])


@pytest.mark.parametrize('change',[{'plannedUnits':99},{'actualUnits':1},{'assignmentCode':'OUTRO'},{'resourceClass':'RESOURCE'}])
def test_existing_conflicting_work_is_never_overwritten_or_added(tmp_path,change):
 p=load_package(*files(tmp_path));oracle=EffortOracle();s=session(oracle)
 _,catalog=s.catalog(p);plan=plan_hours(p,{'EPleno':888},catalog)
 oracle.assignments=[dict(dict(plan['payloads'][0],assignmentId=900,actualUnits=0),**change)]
 before=len(oracle.calls)
 with pytest.raises(ConnectionFailure):sync_hours(s,p,plan,tmp_path/'hours.json')
 assert all(r.get_method()=='GET' for r in oracle.calls[before:])


def test_modified_or_started_activity_blocks_binding(tmp_path):
 p=load_package(*files(tmp_path));oracle=EffortOracle();s=session(oracle)
 oracle.activity['activityStatus']='IN_PROGRESS'
 with pytest.raises(ConnectionFailure):s.catalog(p)


def test_labor_role_mapping_requires_explicit_complete_selection(tmp_path):
 p=load_package(*files(tmp_path));oracle=EffortOracle();s=session(oracle);_,catalog=s.catalog(p)
 with pytest.raises(ConnectionFailure):plan_hours(p,{},catalog)
 with pytest.raises(ConnectionFailure):plan_hours(p,{'EPleno':999},catalog)
 assert all(r.get_method()=='GET' for r in oracle.calls[2:])
