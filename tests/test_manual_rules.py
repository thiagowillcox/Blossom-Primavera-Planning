import copy
import json
from decimal import Decimal
from pathlib import Path
import openpyxl
import pytest
from blossom.fixed_manual import get_fixed_manual, MANUAL_SHA256
from blossom.hours import distribute
from blossom.manual_rules import RULES_PATH, load_text_rules, map_manual_rules, confirm_applied_rules, mark_pending_inputs
from blossom.schedule import estimate
from blossom.relationships import build_links
from blossom.validation import topology

ROOT=Path(__file__).resolve().parents[1]


def source_rule():
    return copy.deepcopy(json.loads(RULES_PATH.read_text(encoding='utf-8'))['regras'][0])


def setup_records():
    nodes=[{'id':'phase','nome':'DETALHADA','pai':None},
           {'id':'mechanical','nome':'MECÂNICA','pai':'phase'},
           {'id':'electric','nome':'ELÉTRICA','pai':'phase'}]
    def record(identifier,name,code='DD',wbs='mechanical'):
        return {'id':identifier,'nome':name,'tipo':'documento','codigo':code,'wbs_id':wbs,
                'origem':'LD!'+identifier,'hh':{'EPleno':Decimal(10)},'total_original':Decimal(10)}
    records=[record('criteria','Critérios de Projeto'),record('drawing','Arranjo Geral'),
             record('electric_drawing','Diagrama Unifilar',wbs='electric'),
             record('basic_drawing','Arranjo Básico',code='DB')]
    return records,nodes


def test_reviewed_quotes_match_exact_manual():
    workbook=openpyxl.load_workbook(get_fixed_manual(),data_only=True,read_only=True)
    rules,issues=load_text_rules(workbook,MANUAL_SHA256)
    workbook.close()
    assert len(rules)==26 and not issues
    assert sum(bool(r.get('automatica')) for r in rules)==1
    assert {r['classe'] for r in rules}=={'obrigatoria','condicional','referencia_tecnica','informacao_externa'}


def test_approval_gate_applies_only_to_same_discipline_and_phase():
    records,nodes=setup_records();config=json.loads((ROOT/'config/parametros.json').read_text())
    activities,assignments,audit,_=distribute(records,config)
    mapped,automatic,issues=map_manual_rules([source_rule()],records,nodes,activities,config)
    assert len(automatic)==1
    byid={a['id']:a for a in activities};link=automatic[0]
    assert byid[link['predecessora']]['registro_id']=='criteria'
    assert byid[link['predecessora']]['etapa']==4
    assert byid[link['sucessora']]['registro_id']=='drawing'
    assert byid[link['sucessora']]['etapa']==1
    assert sum(a['hh'] for a in assignments)==Decimal(48)
    assert all(r['diferenca']==0 for r in audit)
    links=build_links(activities,config,mapped,automatic)
    topology(activities,links)


@pytest.mark.parametrize('kind',['reference','conditional','external','disabled','unplanned','ambiguous','unspecified_stage','scope_ambiguous'])
def test_uncertain_rules_never_invent_dependencies(kind):
    records,nodes=setup_records();config=json.loads((ROOT/'config/parametros.json').read_text())
    rule=source_rule()
    if kind=='reference':rule['classe']='referencia_tecnica'
    elif kind=='conditional':rule['classe']='condicional'
    elif kind=='external':rule['classe']='informacao_externa'
    elif kind=='disabled':config['aplicar_regras_explicitas']=False
    elif kind=='unplanned':records[0]['hh']={};records[0]['total_original']=None
    elif kind=='ambiguous':
        duplicate=copy.deepcopy(records[0]);duplicate['id']='other_criteria';records.append(duplicate)
    elif kind=='unspecified_stage':rule['automatica']=False;rule['etapa_predecessora']=None
    elif kind=='scope_ambiguous':rule['requer_validacao_mapeamento']=True
    activities,_,_,_=distribute(records,config)
    _,automatic,issues=map_manual_rules([rule],records,nodes,activities,config)
    assert automatic==[]
    assert any(i['codigo']=='REVISAO_RELACIONAMENTO' for i in issues)


def test_reference_rule_cannot_be_used_as_mandatory_by_config():
    config=json.loads((ROOT/'config/parametros.json').read_text())
    config['relacionamentos_aprovados']=[{'classe':'obrigatoria','aprovada':True,
                                         'regra_id':'reference','predecessora':'a','sucessora':'b'}]
    with pytest.raises(ValueError,match='Referência técnica'):
        build_links([],config,[{'id':'reference','classe':'referencia_tecnica'}])


def test_reviewed_quote_mismatch_is_blocked(tmp_path,monkeypatch):
    import blossom.manual_rules as module
    workbook=openpyxl.Workbook();workbook.active.title=source_rule()['fase']
    data={'regras':[source_rule()]};p=tmp_path/'rules.json';p.write_text(json.dumps(data))
    monkeypatch.setattr(module,'RULES_PATH',p)
    with pytest.raises(ValueError,match='Evidência textual'):
        load_text_rules(workbook,MANUAL_SHA256)
    workbook.close()


def test_unplanned_documents_do_not_gain_hours_or_activities():
    records,nodes=setup_records();config=json.loads((ROOT/'config/parametros.json').read_text())
    for rec in records:rec['hh']={};rec['total_original']=None
    activities,assignments,audit,_=distribute(records,config)
    _,automatic,_=map_manual_rules([source_rule()],records,nodes,activities,config)
    assert activities==assignments==audit==automatic==[]


@pytest.mark.parametrize('stage',[None,1,4])
def test_project_premise_is_used_only_for_unique_exact_matches(stage):
    records,nodes=setup_records();records=records[:2]
    rule=source_rule();rule['automatica']=False;rule['etapa_predecessora']=None
    rule['seletor_sucessora']={'documentos':['Arranjo Geral'],'disciplinas':['MECÂNICA']}
    config=json.loads((ROOT/'config/parametros.json').read_text());config['marco_informacao_consolidada']=stage
    activities,_,_,_=distribute(records,config)
    _,links,_=map_manual_rules([rule],records,nodes,activities,config)
    if stage is None:assert links==[]
    else:
        assert len(links)==1
        assert next(a for a in activities if a['id']==links[0]['predecessora'])['etapa']==stage
        assert links[0]['base_etapas']=='parametro:marco_informacao_consolidada'


def test_project_premise_does_not_override_explicit_client_approval():
    records,nodes=setup_records();config=json.loads((ROOT/'config/parametros.json').read_text())
    config['marco_informacao_consolidada']=1
    activities,_,_,_=distribute(records,config)
    _,links,_=map_manual_rules([source_rule()],records,nodes,activities,config)
    assert next(a for a in activities if a['id']==links[0]['predecessora'])['etapa']==4


def test_family_candidate_is_not_automatic_even_if_only_one_document_matches():
    records,nodes=setup_records();records=records[:2];records[0]['nome']='Critérios de Projeto - Área X'
    rule=source_rule();rule['automatica']=False;rule['etapa_predecessora']=None
    rule['seletor_predecessora']['familias']=['Critérios de Projeto']
    rule['seletor_sucessora']={'documentos':['Arranjo Geral'],'disciplinas':['MECÂNICA']}
    config=json.loads((ROOT/'config/parametros.json').read_text());activities,_,_,_=distribute(records,config)
    mapped,links,issues=map_manual_rules([rule],records,nodes,activities,config)
    assert mapped[0]['predecessoras_ld']==['criteria']
    assert links==[] and issues


@pytest.mark.parametrize('case',['wrong_document','wrong_stage','valid'])
def test_explicit_review_cannot_approve_unrelated_documents_or_override_manual(case):
    records,nodes=setup_records();config=json.loads((ROOT/'config/parametros.json').read_text())
    activities,_,_,_=distribute(records,config)
    mapped,_,_=map_manual_rules([source_rule()],records,nodes,activities,config)
    index={(a['registro_id'],a['etapa']):a['id'] for a in activities}
    config['relacionamentos_aprovados']=[{'regra_id':mapped[0]['id'],'classe':'obrigatoria','aprovada':True,
        'predecessora':index['criteria',1 if case=='wrong_stage' else 4],
        'sucessora':index['electric_drawing' if case=='wrong_document' else 'drawing',1]}]
    if case=='valid':
        assert len(build_links(activities,config,mapped))==13
    else:
        with pytest.raises(ValueError,match='correspondem|etapa'):
            build_links(activities,config,mapped)


def test_explicit_project_confirmation_is_reported_in_matrix_and_pending_list():
    records,nodes=setup_records();records=records[:2]
    rule=source_rule();rule['automatica']=False;rule['etapa_predecessora']=None
    rule['seletor_sucessora']={'documentos':['Arranjo Geral'],'disciplinas':['MECÂNICA']}
    config=json.loads((ROOT/'config/parametros.json').read_text());config['marco_informacao_consolidada']=None
    activities,_,_,_=distribute(records,config)
    mapped,automatic,issues=map_manual_rules([rule],records,nodes,activities,config)
    index={(a['registro_id'],a['etapa']):a['id'] for a in activities}
    config['relacionamentos_aprovados']=[{'regra_id':rule['id'],'classe':'obrigatoria','aprovada':True,
                                         'predecessora':index['criteria',1],'sucessora':index['drawing',1]}]
    links=build_links(activities,config,mapped,automatic)
    issues=confirm_applied_rules(mapped,links,activities,issues,config)
    assert mapped[0]['quantidade_ligacoes_aplicadas']==1
    assert mapped[0]['status_mapeamento']=='confirmada_pelo_usuario'
    assert issues==[]


@pytest.mark.parametrize('classification',['informacao_externa','condicional','referencia_tecnica'])
def test_pending_inputs_do_not_invent_dates_or_fs_links(classification):
    records,nodes=setup_records();records=records[:2]
    config=json.loads((ROOT/'config/parametros.json').read_text())
    config['capacidade_profissionais']={'EPleno':1};config['duracao_cliente_dias']={'2':1,'4':1}
    rule=source_rule();rule['classe']=classification
    activities,_,_,_=distribute(records,config)
    mapped,automatic,_=map_manual_rules([rule],records,nodes,activities,config)
    links=build_links(activities,config,mapped,automatic)
    assert len(links)==6
    mark_pending_inputs(mapped,links,activities);estimate(activities,links)
    target=[a for a in activities if a['registro_id']=='drawing']
    assert all(a['duracao_dias'] is not None for a in target)
    if classification=='referencia_tecnica':assert target[0]['inicio_dia']==0
    else:assert all(a['inicio_dia'] is None and a['fim_dia'] is None for a in target)
