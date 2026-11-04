import json
import urllib.error
import pytest
from blossom.oracle.structure import inspect_structure,sync_structure
from blossom.oracle.client import ConnectionFailure
from test_oracle_draft import DraftOracle,connect,plan


def test_fresh_structure_then_readonly_recognition_without_recreation(tmp_path):
 oracle=DraftOracle();s=connect(oracle);p=plan();path=tmp_path/'journal.json'
 result=sync_structure(s,p,path)
 assert result['estado']=='estrutura_conferida_prazos_e_hh_pendentes'
 assert len(oracle.groups)==3 and len(oracle.activities)==2 and len(oracle.relations)==1
 before=len(oracle.calls)
 root,state=inspect_structure(s,p)
 assert root==100 and state['atividades']==result['atividades']
 assert all(r.get_method()=='GET' for r in oracle.calls[before:])
 sync_structure(s,p,path)
 assert len(oracle.activities)==2 and len(oracle.relations)==1


def test_matching_partial_structure_without_local_journal_creates_only_missing_objects(tmp_path):
 oracle=DraftOracle();oracle.groups.append({'wbsId':101,'projectId':7,'parentId':100,'wbsCode':'1','wbsName':'Fase'})
 s=connect(oracle);result=sync_structure(s,plan(),tmp_path/'journal.json')
 assert result['estado']=='estrutura_conferida_prazos_e_hh_pendentes'
 assert len([r for r in oracle.calls if r.full_url.endswith('/wbs') and r.get_method()=='POST'])==1
 assert len(oracle.groups)==3


@pytest.mark.parametrize('route',['activity/batch','relationship/batch'])
def test_response_lost_after_creation_is_adopted_on_readback_without_repeating_batch(tmp_path,route):
 oracle=DraftOracle(fail=route);s=connect(oracle);p=plan();path=tmp_path/'journal.json'
 with pytest.raises(ConnectionFailure):sync_structure(s,p,path)
 assert json.loads(path.read_text())['solicitacao_pendente']['rota']==route
 oracle.fail=None
 result=sync_structure(s,p,path)
 assert result['estado']=='estrutura_conferida_prazos_e_hh_pendentes'
 assert sum(r.get_method()=='POST' and r.full_url.endswith('/'+route) for r in oracle.calls)==1
 assert len(oracle.activities)==2 and len(oracle.relations)==1


def test_uncertain_partially_visible_batch_is_not_repeated(tmp_path):
 oracle=DraftOracle(fail='activity/batch');s=connect(oracle);path=tmp_path/'journal.json';p=plan()
 with pytest.raises(ConnectionFailure):sync_structure(s,p,path)
 oracle.activities.pop();oracle.fail=None;before=len(oracle.calls)
 with pytest.raises(ConnectionFailure,match='incerto'):sync_structure(s,p,path)
 assert all(r.get_method()=='GET' for r in oracle.calls[before:])


@pytest.mark.parametrize('change',['extra_group','extra_activity','wrong_name','started'])
def test_nonmatching_project_is_never_modified(tmp_path,change):
 oracle=DraftOracle();s=connect(oracle);p=plan()
 if change=='extra_group':oracle.groups.append({'wbsId':99,'projectId':7,'parentId':100,'wbsCode':'FOREIGN','wbsName':'Outro'})
 elif change=='extra_activity':oracle.activities.append({'activityId':99,'activityCode':'FOREIGN'})
 else:
  sync_structure(s,p,tmp_path/'initial.json')
  if change=='wrong_name':oracle.activities[0]['activityName']='Outra atividade'
  else:oracle.activities[0]['activityStatus']='IN_PROGRESS'
 before=len(oracle.calls)
 with pytest.raises(ConnectionFailure):sync_structure(s,p,tmp_path/'different.json')
 assert all(r.get_method()=='GET' for r in oracle.calls[before:])
