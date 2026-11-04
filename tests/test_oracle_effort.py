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


class DefaultUnitsOracle(EffortOracle):
 """Reproduce the tenant's observed POST defaults, then apply documented PUT units."""
 def open(self,request,timeout):
  if request.get_method()=='PUT':
   assert request.full_url.endswith('/assignment/batch')
   self.calls.append(request)
   for payload in json.loads(request.data):
    assert set(payload)=={'assignmentId','activityId','resourceId','plannedUnits','remainingUnits'}
    target=next(r for r in self.assignments if r['assignmentId']==payload['assignmentId'])
    target.update(payload)
   return Response(b'{"links":{}}',status=200)
  if request.full_url.endswith('/assignment/batch'):
   result=super().open(request,timeout)
   for row in self.assignments:row.update(plannedUnits=40,remainingUnits=40)
   return Response(json.dumps(self.assignments).encode(),status=201)
  return super().open(request,timeout)


def test_creation_default_units_are_initialized_and_read_back_without_duplicate(tmp_path):
 package=load_package(*files(tmp_path));oracle=DefaultUnitsOracle();s=session(oracle)
 _,catalog=s.catalog(package);plan=plan_hours(package,{'EPleno':888},catalog)
 path=tmp_path/'hours.json'
 result=sync_hours(s,package,plan,path)
 assert result['estado']=='horas_conferidas'
 assert len(oracle.assignments)==1 and oracle.assignments[0]['plannedUnits']==10
 assert len(result['inicializacoes_horas'])==1
 assert result['inicializacoes_horas'][0]['antes'][0]['plannedUnits']==40
 before=len(oracle.calls);sync_hours(s,package,plan,path)
 assert all(r.get_method()=='GET' for r in oracle.calls[before:])


def interrupted_default_batch(tmp_path):
 from blossom.oracle.effort import diagnose_hours
 package=load_package(*files(tmp_path));oracle=DefaultUnitsOracle();s=session(oracle)
 _,catalog=s.catalog(package);plan=plan_hours(package,{'EPleno':888},catalog)
 # Old version created the batch and stopped when it returned default units.
 import blossom.oracle.effort as effort
 original=effort.initialize_hours
 try:
  effort.initialize_hours=lambda *a:(_ for _ in ()).throw(ConnectionFailure('old check'))
  with pytest.raises(ConnectionFailure):sync_hours(s,package,plan,tmp_path/'hours.json')
 finally:effort.initialize_hours=original
 record=json.loads((tmp_path/'hours.json').read_text())
 diagnostic=diagnose_hours(s,package,plan,record)
 assert diagnostic['resumo']['divergentes']==1
 return package,oracle,s,plan,diagnostic


def test_repair_requires_review_and_only_updates_pending_batch(tmp_path):
 package,oracle,s,plan,diagnostic=interrupted_default_batch(tmp_path)
 path=tmp_path/'hours.json';before=len(oracle.calls)
 with pytest.raises(ConnectionFailure):sync_hours(s,package,plan,path)
 assert all(r.get_method()=='GET' for r in oracle.calls[before:])
 result=sync_hours(s,package,plan,path,repair_snapshot=diagnostic)
 assert result['estado']=='horas_conferidas' and len(oracle.assignments)==1
 assert oracle.assignments[0]['plannedUnits']==10


@pytest.mark.parametrize('change',[{'actualUnits':1},{'plannedUnits':41},{'assignmentId':901}])
def test_reviewed_batch_changed_since_diagnostic_cannot_be_repaired(tmp_path,change):
 package,oracle,s,plan,diagnostic=interrupted_default_batch(tmp_path)
 oracle.assignments[0].update(change);before=len(oracle.calls)
 with pytest.raises(ConnectionFailure):sync_hours(s,package,plan,tmp_path/'hours.json',repair_snapshot=diagnostic)
 assert all(r.get_method()=='GET' for r in oracle.calls[before:])


def test_reviewed_batch_with_actual_progress_is_never_repaired(tmp_path):
 from blossom.oracle.effort import diagnose_hours
 package,oracle,s,plan,_=interrupted_default_batch(tmp_path)
 oracle.assignments[0]['actualUnits']=1
 path=tmp_path/'hours.json';diagnostic=diagnose_hours(s,package,plan,json.loads(path.read_text()))
 before=len(oracle.calls)
 with pytest.raises(ConnectionFailure):sync_hours(s,package,plan,path,repair_snapshot=diagnostic)
 assert all(r.get_method()=='GET' for r in oracle.calls[before:])


def test_regenerated_excel_can_restore_only_identical_original_hours_payload(tmp_path):
 from blossom.oracle.effort import restore_hours_record
 package,oracle,s,plan,diagnostic=interrupted_default_batch(tmp_path)
 original=json.loads((tmp_path/'hours.json').read_text())
 current=dict(plan,source_sha256='a'*64)
 restored=restore_hours_record(original,current)
 assert restored['source_sha256']=='a'*64
 assert restored['pendente']==original['pendente']
 assert restored['origens_equivalentes'][0]['plan_sha256']==original['plan_sha256']
 assert original['source_sha256']!=restored['source_sha256']
 assert restore_hours_record(restored,current)==restored


@pytest.mark.parametrize('field,value',[('plannedUnits',11),('remainingUnits',11),('activityId',999),('resourceId',999),('assignmentCode','changed')])
def test_regenerated_excel_with_changed_hours_or_identity_rejects_restore(tmp_path,field,value):
 from blossom.oracle.effort import restore_hours_record
 package,oracle,s,plan,diagnostic=interrupted_default_batch(tmp_path)
 original=json.loads((tmp_path/'hours.json').read_text())
 current=json.loads(json.dumps(plan));current['source_sha256']='a'*64;current['payloads'][0][field]=value
 with pytest.raises(ConnectionFailure,match='diferem'):restore_hours_record(original,current)


def test_record_from_another_project_cannot_be_rebound(tmp_path):
 from blossom.oracle.effort import restore_hours_record
 package,oracle,s,plan,diagnostic=interrupted_default_batch(tmp_path)
 original=json.loads((tmp_path/'hours.json').read_text());original['projectId']=8
 with pytest.raises(ConnectionFailure,match='outro projeto'):restore_hours_record(original,plan)
