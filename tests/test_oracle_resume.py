import copy
import hashlib
import json
import pytest
from blossom.oracle.draft import field_equal, reconcile_wbs, upload_draft
from blossom.oracle.client import ConnectionFailure
from test_oracle_draft import plan, DraftOracle, connect


def interrupted(tmp_path):
    data=plan();data['wbs'][1]['payload']['wbsName']='Disciplina '
    data['wbs'].append({'local_id':'w3','local_parent':'w2','payload':{'projectId':7,'wbsCode':'1.1.1','wbsName':'Mais um'}})
    digest=hashlib.sha256(json.dumps(data,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
    record={'servidor':data['servidor'],'projectId':7,'origem':data['origem'],'plan_sha256':digest,
        'estado':'interrompido_conferir_oracle_antes_de_repetir','wbs':{'w1':101},'atividades':{},'relacionamentos':[],
        'solicitacao_pendente':{'rota':'wbs','chaves':['w2']}}
    path=tmp_path/'journal.json';path.write_text(json.dumps(record))
    oracle=DraftOracle();oracle.groups.extend([
        {'wbsId':101,'parentId':100,'projectId':7,'wbsCode':'1','wbsName':'Fase'},
        {'wbsId':102,'parentId':101,'projectId':7,'wbsCode':'1.1','wbsName':'Disciplina'}])
    return data,path,oracle


def test_name_normalization_does_not_hide_meaningful_differences():
    assert field_equal('wbsName','ENGENHARIA DIGITAL','ENGENHARIA DIGITAL ')
    assert field_equal('activityName',' Atividade ','Atividade')
    assert not field_equal('wbsName','Nome  interno','Nome interno')
    assert not field_equal('wbsName','Ação','Acao')
    assert not field_equal('wbsName','NOME','Nome')
    assert not field_equal('wbsCode','1.4','1.4 ')


def test_reconciliation_is_readonly_and_adopts_only_created_pending_group(tmp_path):
    data,path,oracle=interrupted(tmp_path);session=connect(oracle);before=path.read_bytes()
    root,record=reconcile_wbs(session,data,path)
    assert root==100 and record['wbs']=={'w1':101,'w2':102}
    assert path.read_bytes()==before
    assert [r.get_method() for r in oracle.calls].count('POST')==1


def test_resume_skips_existing_groups_keeps_backup_and_finishes_readback(tmp_path):
    data,path,oracle=interrupted(tmp_path);session=connect(oracle);before=json.loads(path.read_text())
    result=upload_draft(session,data,100,path,lambda _:None,resume=True)
    assert result['estado']=='estrutura_conferida_prazos_e_hh_pendentes'
    creates=[r for r in oracle.calls if r.full_url.endswith('/wbs') and r.get_method()=='POST']
    assert len(creates)==1 and json.loads(creates[0].data)['wbsCode']=='1.1.1'
    assert result['wbs']=={'w1':101,'w2':102,'w3':103}
    assert len(oracle.groups)==4 and len(oracle.activities)==2
    backups=list(tmp_path.glob('journal.backup_*.json'))
    assert len(backups)==1 and json.loads(backups[0].read_text())==before


@pytest.mark.parametrize('fault',['name','parent','extra','activity','missing','plan','phase','recorded_id'])
def test_resume_refuses_other_changes_without_any_writes(tmp_path,fault):
    data,path,oracle=interrupted(tmp_path)
    if fault=='name':oracle.groups[-1]['wbsName']='Outra disciplina'
    elif fault=='parent':oracle.groups[-1]['parentId']=100
    elif fault=='extra':oracle.groups.append({'wbsId':999,'projectId':7,'parentId':100,'wbsCode':'EXTRA','wbsName':'Fora do plano'})
    elif fault=='activity':oracle.activities.append({'activityId':999})
    elif fault=='missing':oracle.groups.pop()
    elif fault=='plan':data['wbs'][0]['payload']['wbsName']='Mudou'
    else:
        journal=json.loads(path.read_text())
        if fault=='phase':journal['solicitacao_pendente']['rota']='activity/batch'
        else:journal['wbs']['w1']=999
        path.write_text(json.dumps(journal))
    session=connect(oracle);before=path.read_bytes()
    with pytest.raises(ConnectionFailure):upload_draft(session,data,100,path,lambda _:None,resume=True)
    assert path.read_bytes()==before
    assert [r.get_method() for r in oracle.calls].count('POST')==1


def test_trimmed_response_also_works_in_fresh_upload(tmp_path):
    data=plan();data['wbs'][1]['payload']['wbsName']='Disciplina '
    data['activities'][0]['payload']['activityName']='Primeira '
    oracle=DraftOracle();session=connect(oracle)
    root=session.inspect_empty_project(data['projeto'])
    result=upload_draft(session,data,root,tmp_path/'journal.json',lambda _:None)
    assert result['estado']=='estrutura_conferida_prazos_e_hh_pendentes'
    assert oracle.groups[-1]['wbsName']=='Disciplina'
    assert oracle.activities[0]['activityName']=='Primeira'
    assert data['wbs'][1]['payload']['wbsName']=='Disciplina '

@pytest.mark.parametrize('confirmation',['','ENVIAR 7'])
def test_resume_cli_preserves_original_plan_and_requires_confirmation(tmp_path,monkeypatch,confirmation):
    import blossom.oracle.draft_cli as cli
    data,path,oracle=interrupted(tmp_path)
    output=tmp_path/'output';output.mkdir()
    journal=output/'envio_rascunho_7.json';path.rename(journal)
    original=journal.read_bytes()
    saved_plan=output/'plano_rascunho_primavera.json';saved_plan.write_text(json.dumps(data))
    original_plan=saved_plan.read_bytes()
    session=connect(oracle);session.test_connection=lambda:True
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(cli,'build_draft',lambda *_:data)
    monkeypatch.setattr(cli,'DraftSession',lambda *_:session)
    monkeypatch.setattr(cli,'getpass',lambda _:'password')
    answers=iter(['schedule.xlsx','test',confirmation])
    monkeypatch.setattr('builtins.input',lambda _:next(answers))
    assert cli.send_draft(resume=True)==0
    assert saved_plan.read_bytes()==original_plan
    if confirmation:assert json.loads(journal.read_text())['estado']=='estrutura_conferida_prazos_e_hh_pendentes'
    else:
        assert journal.read_bytes()==original
        assert [r.get_method() for r in oracle.calls].count('POST')==1

@pytest.mark.parametrize('actual,expected',[
    ('CIVIL &#x2F; CONCRETO','CIVIL / CONCRETO'),
    ('A &amp; B','A & B'),
    ('&lt;Documento&gt;','<Documento>'),
    ('Cliente&#39;s &quot;Documento&quot;', '''Cliente's "Documento"'''),
    ('Literal &amp;amp;','Literal &amp;'),
])
def test_response_html_encoding_is_decoded_once_for_names(actual,expected):
    for field in ('wbsName','activityName'):assert field_equal(field,actual,expected)
    assert not field_equal('wbsCode',actual,expected)


def test_source_literal_entities_are_preserved_and_not_recursively_decoded():
    assert not field_equal('wbsName','A &amp; B','A &amp;amp; B')
    assert not field_equal('wbsName','A &amp;amp; B','A & B')
    assert not field_equal('wbsName','CIVIL &#x2F; AÇO','CIVIL / CONCRETO')


def test_encoded_response_in_creation_and_readback(tmp_path):
    import html
    from test_oracle import Response
    class EncodedOracle(DraftOracle):
        def open(self,request,timeout):
            response=super().open(request,timeout)
            if '/primediscovery/' in request.full_url or request.full_url.endswith('util/testConnection'):
                return response
            data=json.loads(response.getvalue())
            def encode(value):
                if isinstance(value,list):return [encode(item) for item in value]
                if isinstance(value,dict):return {k:(html.escape(v,quote=True).replace('/','&#x2F;') if k in ('wbsName','activityName') and isinstance(v,str) else encode(v)) for k,v in value.items()}
                return value
            return Response(json.dumps(encode(data)).encode(),status=response.status)
    data=plan();data['wbs'][1]['payload']['wbsName']='CIVIL / CONCRETO '
    data['activities'][0]['payload']['activityName']='Documento / Cliente & Fornecedor'
    oracle=EncodedOracle();session=connect(oracle)
    root=session.inspect_empty_project(data['projeto'])
    result=upload_draft(session,data,root,tmp_path/'journal.json',lambda _:None)
    assert result['estado']=='estrutura_conferida_prazos_e_hh_pendentes'
    assert oracle.groups[-1]['wbsName']=='CIVIL / CONCRETO'


def test_resume_accepts_encoded_name_of_pending_created_group(tmp_path):
    data,path,oracle=interrupted(tmp_path)
    data['wbs'][1]['payload']['wbsName']='CIVIL / CONCRETO'
    record=json.loads(path.read_text())
    record['plan_sha256']=hashlib.sha256(json.dumps(data,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
    path.write_text(json.dumps(record))
    oracle.groups[-1]['wbsName']='CIVIL &#x2F; CONCRETO'
    session=connect(oracle)
    root,journal=reconcile_wbs(session,data,path)
    assert root==100 and journal['wbs']['w2']==102
