import json
from pathlib import Path
from decimal import Decimal as D
import pytest
import openpyxl
from blossom.ld import read_ld
from blossom.duration import duration
from blossom.provenance import verify_sources
from blossom.common import digest
from blossom.validation import validate_config
from blossom.wbs import node

ROLES=['Gerente','Especialista','ESênior','EPleno','EJúnior','PSênior','PPleno','PJúnior','Desenh.']


def workbook(path, unresolved=False):
    w=openpyxl.Workbook();s=w.active;s.title='LD';cpu=w.create_sheet('CPU ')
    for i,role in enumerate(ROLES):
        col=openpyxl.utils.get_column_letter(5+i)
        cpu.cell(2,5+i,role)
        s.cell(4,8+i,f"='CPU '!{col}2")
    if unresolved:s['H4']="='Ausente'!E2"
    s['B7']='3.0';s['D7']='DETALHADA';s['B8']='3.1';s['D8']='MECÂNICA'
    s['B9']='DD';s['D9']='Documento A';s['E9']=2;s['F9']='A1';s['G9']=2;s['K9']=8;s['R9']=16
    s['T9']=2000;s['V9']=3000;s['V4']='Especialista'
    w.save(path)


def test_local_formula_headers_and_costs(tmp_path):
    p=tmp_path/'budget.xlsx';workbook(p)
    records,wbs,issues=read_ld(p)
    assert records[0]['hh']=={'EPleno':D(16)}
    assert records[0]['total_original']==16
    assert records[0]['total_ajustado_cache'] is None
    assert records[0]['fator_ajuste_original'] is None
    assert '3000' in records[0]['cache']


def test_unresolved_role_header_is_rejected(tmp_path):
    p=tmp_path/'budget.xlsx';workbook(p,True)
    with pytest.raises(ValueError,match='identificação sem valor'):
        read_ld(p)


def test_nested_wbs_parent():
    assert node('3.1.2','Grupo',10)['pai']==node('3.1','Disciplina',9)['id']
    assert node('3.1.0','Grupo',10)['pai']==node('3.1','Disciplina',9)['id']


def test_reference_requires_exact_sources(tmp_path):
    ld=tmp_path/'LD';manual=tmp_path/'manual';ld.write_bytes(b'LD');manual.write_bytes(b'manual')
    c={'fontes_esperadas':{'ld':digest(ld),'manual':digest(manual)}}
    verify_sources(ld,manual,c)
    ld.write_bytes(b'outra LD')
    with pytest.raises(ValueError,match='LD diferente da referência'):verify_sources(ld,manual,c)


def test_equivalent_effort_is_distinct_from_parallel_capacity():
    c={'jornada_hh_dia':8,'capacidade_profissionais':{'EPleno':1,'PSênior':1},'duracao_cliente_dias':{'2':3,'4':3}}
    hours={'EPleno':D(8),'PSênior':D(8)}
    assert duration(hours,c,1)==1
    c['metodo_duracao']='equivalente_hh'
    assert duration(hours,c,1)==2
    assert duration(hours,c,2)==3


def test_bad_duration_mode_is_rejected():
    c=json.loads(Path('config/parametros.json').read_text(encoding='utf-8'));c['metodo_duracao']='desconhecido'
    with pytest.raises(ValueError,match='Método'):validate_config(c)


def test_all_wardi_production_durations_follow_effort():
    p=Path(__file__).resolve().parents[1]/'input/pre_cronograma_v0001.xlsx'
    if not p.exists():pytest.skip('Referência comercial não está no checkout')
    w=openpyxl.load_workbook(p,read_only=True,data_only=False);rows=list(w['Atividades'].values)
    records=[dict(zip(rows[0],r)) for r in rows[1:]];c={'jornada_hh_dia':8,'metodo_duracao':'equivalente_hh','duracao_cliente_dias':{'2':3,'4':3}}
    for r in records:
        stage=0 if r['tipo']=='auxiliar' else r['etapa']
        actual=duration({'total':D(str(r['hh']))},c,stage)
        assert abs(actual-D(str(r['duracao_dias'])))<D('0.00000001')
    assert len(records)==952
    w.close()


def test_web_reference_profile_rejects_old_sources():
    from streamlit.testing.v1 import AppTest
    root=Path(__file__).resolve().parents[1]
    if not (root/'input/LD.xlsm').exists():pytest.skip('LD antiga indisponível')
    app=AppTest.from_file(str(root/'app.py')).run(timeout=30)
    app.session_state['ld_file']=('LD.xlsm',(root/'input/LD.xlsm').read_bytes())
    app.session_state['manual_file']=('Manual.xlsx',(root/'input/Manual.xlsx').read_bytes())
    app.radio[0].set_value('Configuração').run()
    app.selectbox[0].set_value('Referência Wardi v0001 (parcial)').run()
    assert not app.exception
    assert app.number_input[1].value==3.0
    assert app.number_input[2].value==3.0
    assert app.text_input[0].value=='Humberto'
    app.button[0].click().run(timeout=30)
    assert not app.exception
    assert any('LD diferente da referência' in error.value for error in app.error)
    assert 'result' not in app.session_state
