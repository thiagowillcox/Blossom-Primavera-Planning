import hashlib,json
from decimal import Decimal as D
import pytest
from blossom.oracle.client import ConnectionFailure
from blossom.oracle.effort import load_package,plan_hours,sync_hours
from blossom.oracle.timing import timing_preview,send_timing
from blossom.team import forecast
from blossom.team_ui import plain
from test_oracle_effort import files,EffortOracle,session,PROJECT
from test_oracle import Response


class TimingOracle(EffortOracle):
 def __init__(self):
  super().__init__();self.project=dict(PROJECT);self.job_count=0
  self.pattern='0'*16+'1'*16+'0'*16
 def open(self,request,timeout):
  route=request.full_url.split('/api/restapi/')[-1]
  if len(self.calls)>=2 and request.get_method()=='GET':
   if route=='project/7':self.calls.append(request);return Response(json.dumps(self.project).encode())
   if route=='calendar/4':
    self.calls.append(request);return Response(json.dumps(dict(calendarId=4,holiday=None,**{'workTime'+n:self.pattern if i<5 else '0'*48 for i,n in enumerate(['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday'])})).encode())
   if route=='calendar/exception/4' or route.startswith('relationship/projectRelationshipCode?'):
    self.calls.append(request);return Response(b'[]')
  if request.get_method()=='PUT':
   self.calls.append(request);body=json.loads(request.data)
   if route=='project':self.project.update(body);return Response(b'',status=204)
   assert route=='activity/batch';self.activity.update(body[0]);return Response(b'{"links":{"201":"test"}}')
  if request.get_method()=='POST' and route=='action/scheduleProject':
   self.calls.append(request);self.job_count+=1;return Response(b'{"jobId":555,"jobStatus":"QUEUED"}',status=201)
  return super().open(request,timeout)


def prepared(tmp_path):
 p=load_package(*files(tmp_path));oracle=TimingOracle();s=session(oracle)
 _,catalog=s.catalog(p);hp=plan_hours(p,{'EPleno':888},catalog)
 sync_hours(s,p,hp,tmp_path/'hours.json')
 config={'jornada_hh_dia':8,'capacidade_profissionais':{'EPleno':1},'duracao_cliente_dias':{'2':None,'4':None}}
 r=forecast(p['tables'],config,start='2026-10-13')
 r['premissas']={'source':hashlib.sha256(json.dumps(p['tables'],sort_keys=True,default=plain).encode()).hexdigest(),
  'reviewed':True,'start':'2026-10-13','weekdays':[0,1,2,3,4],'holidays':[],'config':config}
 return p,oracle,s,hp,r


def test_native_schedule_requires_known_parameters_and_verified_calendar(tmp_path):
 p,oracle,s,hp,r=prepared(tmp_path)
 plan=timing_preview(s,p,hp,r)
 assert plan['updates'][0]['plannedDuration']==10
 assert plan['dataDate']=='2026-10-13T08:00:00-03:00'
 state=send_timing(s,p,hp,r,plan,tmp_path/'timing.json')
 assert state['jobId']==555 and state['estado']=='job_solicitado'
 assert oracle.activity['plannedDuration']==10
 assert oracle.project['planStartDate']==plan['dataDate'] and oracle.job_count==1
 with pytest.raises(ConnectionFailure,match='registro'):send_timing(s,p,hp,r,plan,tmp_path/'timing.json')
 assert oracle.job_count==1


def test_calendar_mismatch_prevents_mutation(tmp_path):
 p,oracle,s,hp,r=prepared(tmp_path);oracle.pattern='1'*12+'0'*36
 before=len(oracle.calls)
 with pytest.raises(ConnectionFailure,match='Calendário Oracle difere'):timing_preview(s,p,hp,r)
 assert all(req.get_method()=='GET' for req in oracle.calls[before:])


@pytest.mark.parametrize('missing',['start','reviewed','technical','hours'])
def test_unknown_or_unreviewed_inputs_block_scheduling(tmp_path,missing):
 p,oracle,s,hp,r=prepared(tmp_path)
 if missing=='technical':r['atividades'][0]['pendencias']=['DF pendente']
 elif missing=='hours':oracle.assignments=[]
 else:r['premissas'][missing]=None
 before=len(oracle.calls)
 with pytest.raises(ConnectionFailure):timing_preview(s,p,hp,r)
 assert all(req.get_method()=='GET' for req in oracle.calls[before:])


def test_unknown_job_result_is_registered_and_never_resubmitted(tmp_path):
 import urllib.error
 p,oracle,s,hp,r=prepared(tmp_path);plan=timing_preview(s,p,hp,r)
 original=oracle.open
 def fail_after_job(request,timeout):
  result=original(request,timeout)
  if request.full_url.endswith('action/scheduleProject'):raise urllib.error.URLError('ambiguous response')
  return result
 oracle.open=fail_after_job;path=tmp_path/'timing.json'
 with pytest.raises(ConnectionFailure):send_timing(s,p,hp,r,plan,path)
 assert json.loads(path.read_text())['pendente']=='agendamento' and oracle.job_count==1
 with pytest.raises(ConnectionFailure):send_timing(s,p,hp,r,plan,path)
 assert oracle.job_count==1


def test_requests_use_the_fields_and_required_values_in_uploaded_contract(tmp_path):
 from pathlib import Path
 p,oracle,s,hp,r=prepared(tmp_path);plan=timing_preview(s,p,hp,r)
 send_timing(s,p,hp,r,plan,tmp_path/'timing.json')
 contract=json.loads((Path(__file__).parents[1]/'config/oracle_effort_contract.json').read_text())
 names={'assignment/batch':'ApiEntityAssignmentInput','activity/batch':'ApiEntityActivityInput','project':'ApiEntityProjectInput','action/scheduleProject':'ApiEntityProjectScheduleInput'}
 for req in oracle.calls:
  route=req.full_url.split('/api/restapi/')[-1]
  if req.get_method() not in ('PUT','POST') or route not in names:continue
  schema=contract['schemas'][names[route]];payload=json.loads(req.data)
  for row in payload if isinstance(payload,list) else [payload]:
   assert set(schema['required'])<=set(row)
   for key,value in row.items():
    spec=schema['properties'][key]
    if 'enum' in spec:assert value in spec['enum']
    if spec['type']=='integer':assert type(value) is int
