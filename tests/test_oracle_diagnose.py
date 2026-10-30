import hashlib,json
import pytest
from blossom.oracle.diagnose import diagnose_groups
from blossom.oracle.client import ConnectionFailure
from test_oracle_draft import plan,DraftOracle,connect,PROJECT


def files(tmp_path):
    data=plan();digest=hashlib.sha256(json.dumps(data,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
    journal={'servidor':data['servidor'],'projectId':7,'plan_sha256':digest,'wbs':{'w1':101},
        'solicitacao_pendente':{'rota':'wbs','chaves':['w2']},'estado':'interrompido'}
    p=tmp_path/'plan.json';p.write_text(json.dumps(data))
    j=tmp_path/'journal.json';j.write_text(json.dumps(journal))
    return p,j,tmp_path/'diagnosis.json'


def test_diagnosis_finds_changed_name_without_any_entity_writes(tmp_path):
    paths=files(tmp_path);oracle=DraftOracle()
    oracle.groups.extend([{'projectId':7,'wbsId':101,'parentId':100,'wbsCode':'1','wbsName':'Fase'},
        {'projectId':7,'wbsId':102,'parentId':101,'wbsCode':'1.1','wbsName':'Changed'}])
    session=connect(oracle)
    result=diagnose_groups(session,*paths)
    pending=next(r for r in result['comparacoes'] if r['solicitacao_pendente'])
    assert pending['encontrados'][0]['wbsId']==102
    assert pending['diferencas']==[{'wbsName':{'esperado':'Disciplina','oracle':'Changed'}}]
    assert [r.get_method() for r in oracle.calls]==['POST','GET','GET','GET','GET']
    assert 'password' not in paths[-1].read_text()


def test_mismatched_plan_stops_before_queries(tmp_path):
    p,j,target=files(tmp_path)
    data=json.loads(p.read_text());data['wbs'][0]['payload']['wbsName']='Changed';p.write_text(json.dumps(data))
    oracle=DraftOracle();session=connect(oracle);before=len(oracle.calls)
    with pytest.raises(ConnectionFailure,match='não correspondem'):diagnose_groups(session,p,j,target)
    assert len(oracle.calls)==before and not target.exists()
