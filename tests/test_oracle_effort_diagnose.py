import hashlib,json
from pathlib import Path
from blossom.oracle.effort import diagnose_hours,load_package,plan_hours,sync_hours
from blossom.oracle.client import ConnectionFailure,SERVER
from test_oracle_effort import files,EffortOracle,session
import pytest


def prepared(tmp_path):
 p=load_package(*files(tmp_path));oracle=EffortOracle();s=session(oracle)
 _,catalog=s.catalog(p);plan=plan_hours(p,{'EPleno':888},catalog)
 sha=hashlib.sha256(json.dumps({k:plan[k] for k in ('projectId','source_sha256','mapping','payloads')},sort_keys=True,ensure_ascii=False).encode()).hexdigest()
 record={'servidor':SERVER,'projectId':7,'source_sha256':p['source_sha256'],'plan_sha256':sha,
  'estado':'interrompido_conferir_oracle','pendente':{'tipo':'atribuicoes','codigos':['BL-AF-1']}}
 return p,oracle,s,plan,record


def test_empty_oracle_is_reported_without_retry_or_journal_changes(tmp_path):
 p,oracle,s,plan,record=prepared(tmp_path);original=json.dumps(record);before=len(oracle.calls)
 report=diagnose_hours(s,p,plan,record)
 assert report['resumo']=={'compativeis':0,'nao_encontradas':1,'divergentes':0}
 assert report['registro_compativel'] and report['erro_ultimo_envio'] is None
 assert report['detalhes'][0]['encontrados']==[]
 assert json.dumps(record)==original
 assert all(r.get_method()=='GET' for r in oracle.calls[before:])


def test_changed_hours_are_exported_as_minimal_evidence_without_raw_responses(tmp_path):
 p,oracle,s,plan,record=prepared(tmp_path)
 oracle.assignments=[dict(plan['payloads'][0],assignmentId=900,actualUnits=0)]
 oracle.assignments[0].update(remainingUnits=0,extra_field='must not be exported')
 report=diagnose_hours(s,p,plan,record)
 assert report['resumo']['divergentes']==1
 assert report['detalhes'][0]['encontrados'][0]['remainingUnits']==0
 assert 'extra_field' not in json.dumps(report)
 assert 'fictional-password' not in json.dumps(report)


def test_compatible_created_batch_is_identified_readonly(tmp_path):
 p,oracle,s,plan,record=prepared(tmp_path)
 oracle.assignments=[dict(plan['payloads'][0],assignmentId=900,actualUnits=0)]
 oracle.assigned=True;before=len(oracle.calls)
 report=diagnose_hours(s,p,plan,record)
 assert report['resumo']['compativeis']==1
 assert report['funcoes_selecionadas_associadas']==1
 assert report['problema_conferencia_global'] is None
 assert all(r.get_method()=='GET' for r in oracle.calls[before:])


def test_future_failures_keep_sanitized_error_in_execution_record(tmp_path):
 p,oracle,s,plan,record=prepared(tmp_path);oracle.fail=True;path=tmp_path/'record.json'
 with pytest.raises(ConnectionFailure):sync_hours(s,p,plan,path)
 saved=json.loads(path.read_text())
 assert saved['erro'] and saved['estado']=='interrompido_conferir_oracle'
 assert 'unknown after creation' not in saved['erro']
 assert 'fictional-password' not in path.read_text()
