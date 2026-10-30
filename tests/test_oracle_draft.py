import json
import urllib.error
from pathlib import Path
import pytest
from blossom.oracle.client import SERVER, ConnectionFailure
from blossom.oracle.draft import build_draft, DraftSession, upload_draft
from test_oracle import FakeOracle, Response
from test_oracle_preview import make_files


PROJECT={'projectId':7,'projectName':'TESTE Laboratório','projectCode':'LAB','workspaceId':2,'workspaceCode':'WORKSPACE'}


def plan():
    return {'tipo':'rascunho_estrutural_oracle_v1','servidor':SERVER,'projeto':PROJECT.copy(),'origem':{'xlsx_sha256':'test'},
        'wbs':[{'local_id':'w1','local_parent':None,'payload':{'projectId':7,'wbsCode':'1','wbsName':'Fase'}},
               {'local_id':'w2','local_parent':'w1','payload':{'projectId':7,'wbsCode':'1.1','wbsName':'Disciplina'}}],
        'activities':[{'local_id':'a','local_wbs':'w2','payload':{'projectId':7,'activityCode':'a','activityName':'Primeira','activityType':'ACTIVITY','activityStatus':'NOT_STARTED'}},
                      {'local_id':'b','local_wbs':'w2','payload':{'projectId':7,'activityCode':'b','activityName':'Segunda','activityType':'ACTIVITY','activityStatus':'NOT_STARTED'}}],
        'relationships':[{'predecessor':'a','successor':'b','payload':{'predProjectId':7,'succProjectId':7,'relationshipType':'FINISH_TO_START','lagHours':0}}]}


class CreatedResponse(Response):
    def __init__(self,data):super().__init__(data,status=201)


class DraftOracle(FakeOracle):
    def __init__(self,fail=None,existing=False):
        super().__init__();self.fail=fail;self.existing=existing
        self.groups=[{'wbsId':100,'parentId':None,'projectId':7}]
        self.activities=[];self.relations=[]

    def open(self,request,timeout):
        if len(self.calls)<2:return super().open(request,timeout)
        self.calls.append(request)
        route=request.full_url.split('/api/restapi/')[1]
        if request.get_method()=='GET':
            if route=='project/7':result=PROJECT
            elif route=='wbs/project/7':result=self.groups
            elif route=='activity/project/7':result=self.activities or ([{'activityId':1}] if self.existing else [])
            elif route.startswith('relationship/projectRelationshipCode?'):result=self.relations
            else:raise AssertionError(route)
            return Response(json.dumps(result).encode())
        assert request.get_method()=='POST' and route in ('wbs','activity/batch','relationship/batch')
        payload=json.loads(request.data)
        if route=='wbs':
            result=dict(payload,wbsId=100+len(self.groups));self.groups.append(result)
        elif route=='activity/batch':
            result=[dict(row,activityId=200+len(self.activities)+i) for i,row in enumerate(payload)]
            self.activities.extend(result)
        else:
            result=[dict(row,relationshipId=300+len(self.relations)+i) for i,row in enumerate(payload)]
            self.relations.extend(result)
        if self.fail==route:raise urllib.error.URLError('uncertain outcome; secret response never exposed')
        # Batches deliberately arrive out of order: IDs must map by codes/pairs.
        return CreatedResponse(json.dumps(list(reversed(result)) if isinstance(result,list) else result).encode())


def connect(oracle):
    session=DraftSession('test','password',opener=oracle);session.test_connection();return session


def test_draft_uses_returned_ids_keeps_hierarchy_and_reads_back(tmp_path):
    oracle=DraftOracle();session=connect(oracle)
    root=session.inspect_empty_project(PROJECT)
    result=upload_draft(session,plan(),root,tmp_path/'journal.json',lambda _:None)
    assert result['estado']=='estrutura_conferida_prazos_e_hh_pendentes'
    assert oracle.groups[1]['parentId']==100 and oracle.groups[2]['parentId']==101
    assert all(a['wbsId']==102 for a in oracle.activities)
    assert oracle.relations[0]['predActivityId']==result['atividades']['a']
    assert oracle.relations[0]['succActivityId']==result['atividades']['b']
    assert len(result['relacionamentos'])==1
    assert [r.get_method() for r in oracle.calls].count('POST')==5 # token + 2 WBS + 2 batches
    assert all(r.get_method() in ('GET','POST') for r in oracle.calls)
    assert 'password' not in (tmp_path/'journal.json').read_text()
    assert oracle.calls[-1].full_url.endswith('workspaceCode=WORKSPACE&projectCode=LAB')


def test_nonempty_project_is_rejected_without_scheduling_writes():
    oracle=DraftOracle(existing=True);session=connect(oracle)
    with pytest.raises(ConnectionFailure,match='já possui atividades'):session.inspect_empty_project(PROJECT)
    assert [r.get_method() for r in oracle.calls].count('POST')==1


def test_ambiguous_partial_failure_keeps_journal_and_blocks_retry(tmp_path):
    oracle=DraftOracle(fail='activity/batch');session=connect(oracle);root=session.inspect_empty_project(PROJECT)
    path=tmp_path/'journal.json'
    with pytest.raises(ConnectionFailure):upload_draft(session,plan(),root,path,lambda _:None)
    record=json.loads(path.read_text())
    assert record['estado'].startswith('interrompido')
    assert record['solicitacao_pendente']['rota']=='activity/batch'
    assert len(record['wbs'])==2 and len(oracle.activities)==2
    calls=len(oracle.calls)
    with pytest.raises(ConnectionFailure,match='Já existe'):upload_draft(session,plan(),root,path,lambda _:None)
    assert len(oracle.calls)==calls


def test_create_route_allowlist_cannot_update_or_delete():
    oracle=DraftOracle();session=connect(oracle);calls=len(oracle.calls)
    for route in ('project','activity','wbs/100','action/schedule'):
        with pytest.raises(ConnectionFailure):session.create(route,{})
    assert len(oracle.calls)==calls


def test_readback_detects_foreign_or_missing_entities(tmp_path):
    oracle=DraftOracle();session=connect(oracle);root=session.inspect_empty_project(PROJECT)
    original=session.verify_created
    def verify(*args):
        oracle.activities.append({'activityId':999})
        return original(*args)
    session.verify_created=verify
    path=tmp_path/'journal.json'
    with pytest.raises(ConnectionFailure,match='incompleta'):upload_draft(session,plan(),root,path,lambda _:None)
    assert json.loads(path.read_text())['estado'].startswith('interrompido')


def draft_files(tmp_path):
    import openpyxl
    from blossom.oracle.preview import prepare_preview
    path,selection,preview=make_files(tmp_path)
    workbook=openpyxl.load_workbook(path)
    workbook['WBS'].append([]) # retain existing columns; extend real metadata below
    workbook['WBS']['C1']='codigo';workbook['WBS']['C2']='1'
    workbook['WBS']['D1']='nome';workbook['WBS']['D2']='Fase'
    workbook['Atividades']['J1']='nome';workbook['Atividades']['J2']='Atividade'
    workbook.save(path);workbook.close()
    prepare_preview(path,selection,preview)
    return path,selection,preview


def test_workbook_build_omits_all_dates_durations_and_resource_fields(tmp_path):
    path,selection,preview=draft_files(tmp_path)
    result=build_draft(path,selection,preview)
    activity=result['activities'][0]['payload']
    assert set(activity)=={'projectId','activityCode','activityName','activityType','activityStatus'}
    assert result['hh_nao_enviadas']=='10'
    assert result['duracoes_nao_enviadas'] is True


def test_changed_workbook_cannot_reuse_old_review(tmp_path):
    path,selection,preview=draft_files(tmp_path)
    path.write_bytes(path.read_bytes()+b'changed')
    with pytest.raises(ConnectionFailure,match='mudou'):build_draft(path,selection,preview)


def test_generated_fields_match_uploaded_openapi_contract(tmp_path):
    contract=json.loads((Path(__file__).parents[1]/'config/oracle_structural_contract.json').read_text())
    oracle=DraftOracle();session=connect(oracle);root=session.inspect_empty_project(PROJECT)
    upload_draft(session,plan(),root,tmp_path/'journal.json',lambda _:None)
    schemas={'wbs':'ApiEntityWBSInput','activity/batch':'ApiEntityActivityInput','relationship/batch':'ApiEntityRelationshipInput'}
    for request in oracle.calls:
        if request.get_method()!='POST' or '/primediscovery/' in request.full_url:continue
        route=request.full_url.split('/api/restapi/')[1]
        schema=contract['schemas'][schemas[route]]
        payload=json.loads(request.data)
        for row in payload if isinstance(payload,list) else [payload]:
            assert set(schema['required'])<=set(row)
            for key,value in row.items():
                spec=schema['properties'][key]
                if spec.get('type')=='integer':assert type(value) is int
                if spec.get('type')=='string':assert isinstance(value,str) and len(value)<=spec.get('maxLength',100000)
                if 'enum' in spec:assert value in spec['enum']


@pytest.mark.parametrize('confirmation',['','ENVIAR 7'])
def test_cli_only_creates_after_explicit_confirmation(tmp_path,monkeypatch,confirmation):
    import blossom.oracle.draft_cli as cli
    monkeypatch.chdir(tmp_path)
    oracle=DraftOracle();session=connect(oracle)
    monkeypatch.setattr(cli,'DraftSession',lambda *_:session)
    monkeypatch.setattr(cli,'build_draft',lambda *_:plan())
    monkeypatch.setattr(cli,'getpass',lambda _:'password')
    answers=iter(['schedule.xlsx','test',confirmation])
    monkeypatch.setattr('builtins.input',lambda _:next(answers))
    # cli probes again; fake handles a repeated read-only connection test.
    original=oracle.open
    def open_request(request,timeout):
        if request.full_url.endswith('util/testConnection') and len(oracle.calls)>=2:
            oracle.calls.append(request);return Response(b'{}')
        return original(request,timeout)
    oracle.open=open_request
    assert cli.send_draft()==0
    assert [r.get_method() for r in oracle.calls].count('POST')==(5 if confirmation else 1)
    assert (tmp_path/'output/envio_rascunho_7.json').exists()==bool(confirmation)


def test_large_activity_batches_are_bounded_and_ids_are_unique(tmp_path):
    data=plan();sample=data['activities'][0]
    data['activities']=[dict(sample,local_id=f'a{i}',payload=dict(sample['payload'],activityCode=f'a{i}')) for i in range(103)]
    data['relationships']=[]
    oracle=DraftOracle();session=connect(oracle);root=session.inspect_empty_project(PROJECT)
    report=upload_draft(session,data,root,tmp_path/'journal.json',lambda _:None)
    batches=[json.loads(r.data) for r in oracle.calls if r.full_url.endswith('/activity/batch')]
    assert list(map(len,batches))==[50,50,3]
    assert len(set(report['atividades'].values()))==103


def test_production_named_project_is_blocked_before_data_reads():
    oracle=DraftOracle();session=connect(oracle);calls=len(oracle.calls)
    with pytest.raises(ConnectionFailure,match='comece com TESTE'):
        session.inspect_empty_project(dict(PROJECT,projectName='Produção'))
    assert len(oracle.calls)==calls


def test_empty_activity_204_is_handled_as_empty():
    oracle=DraftOracle();session=connect(oracle);original=oracle.open
    def open_request(request,timeout):
        if request.full_url.endswith('activity/project/7'):
            oracle.calls.append(request);return Response(b'',status=204)
        return original(request,timeout)
    oracle.open=open_request
    assert session.inspect_empty_project(PROJECT)==100
