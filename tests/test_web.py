import json
from pathlib import Path
import pytest
from streamlit.testing.v1 import AppTest
from blossom.web import generate
from blossom.fixed_manual import get_fixed_manual, MANUAL_SHA256

ROOT = Path(__file__).resolve().parents[1]


def test_app_starts_and_requires_uploads():
    app = AppTest.from_file(str(ROOT/'app.py')).run(timeout=30)
    assert not app.exception
    assert app.button[0].disabled
    assert len(app.get('file_uploader'))==1
    assert len(app.toggle)==0
    app.radio[0].set_value('Configuração').run()
    assert not app.exception
    assert len(app.selectbox)==1
    assert app.selectbox[0].value==1
    assert app.number_input[0].value == 8.0
    assert app.number_input[1].value is None
    assert app.number_input[2].value is None
    app.text_input[0].set_value('Projeto de teste').run()
    app.number_input[0].set_value(6.0).run()
    app.radio[0].set_value('Arquivos').run()
    app.radio[0].set_value('Configuração').run()
    assert app.text_input[0].value == 'Projeto de teste'
    assert app.number_input[0].value == 6.0
    assert len(app.toggle)==0
    assert app.button[0].disabled
    assert not app.exception



def test_web_requires_inputs():
    with pytest.raises(ValueError, match='Envie'):
        generate(b'', {})


def test_web_real_uploads():
    if not (ROOT/'input/LD.xlsm').exists():
        pytest.skip('Planilhas comerciais locais indisponíveis')
    config=json.loads((ROOT/'config/parametros.json').read_text(encoding='utf-8'))
    tables, files=generate((ROOT/'input/LD.xlsm').read_bytes(),config)
    assert len(tables['WBS'])==56
    assert len(tables['Atividades'])==952
    assert files['pre_cronograma.xlsx'].startswith(b'PK')
    assert len(json.loads(files['pendencias.json']))>0
    assert all(r['diferenca']==0 for r in tables['Auditoria_HH'])
    assert next(r['valor'] for r in tables['Parametros'] if r['parametro']=='manual_sha256')==MANUAL_SHA256

    app = AppTest.from_file(str(ROOT/'app.py'))
    app.session_state['workflow_version'] = 'ld-relacoes-v4'
    app.session_state['result'] = (tables, files)
    app.session_state['navigation'] = 'Resultados'
    app.run(timeout=30)
    assert not app.exception

    assert len(app.expander) == 7
    assert len(app.metric) == 4
    assert not app.exception
    assert len(app.metric) == 4
    assert any('1 - Emissão Inicial' in item.value for item in app.markdown)
    app.radio[0].set_value('Arquivos').run()
    app.radio[0].set_value('Resultados').run()
    assert len(app.metric) == 4
    assert not app.exception

    # A single LD upload enables generation; no manual upload/session is needed.
    app.session_state['ld_file']=('LD.xlsm',(ROOT/'input/LD.xlsm').read_bytes())
    app.radio[0].set_value('Configuração').run(timeout=30)
    assert not app.exception
    assert not next(b for b in app.button if b.label.startswith('Gerar')).disabled
    assert 'manual_file' not in app.session_state


def test_upgrade_removes_legacy_reference_settings():
    app=AppTest.from_file(str(ROOT/'app.py'))
    app.session_state['settings']={'profile':'Reprocessar referência Wardi','project':'Humberto',
        'daily':8.0,'comments':3.0,'approval':3.0}
    app.session_state['reference_result']=(b'old',{})
    app.session_state['navigation']='Configuração'
    app.run(timeout=30)
    assert not app.exception
    assert app.text_input[0].value==''
    assert app.number_input[1].value is None
    assert app.number_input[2].value is None
    assert len(app.toggle)==0
    assert len(app.selectbox)==1
    assert 'reference_result' not in app.session_state


@pytest.mark.parametrize('present', [False,True])
def test_missing_or_modified_fixed_manual_blocks_generation(tmp_path,monkeypatch,present):
    import blossom.fixed_manual as fixed
    path=tmp_path/'manual.xlsx'
    if present:path.write_bytes(b'wrong-version')
    monkeypatch.setattr(fixed,'FIXED_MANUAL',path)
    with pytest.raises(ValueError,match='manual fixo'):
        generate(b'LD',{})


def test_fixed_manual_version_is_packaged():
    assert get_fixed_manual().is_file()


def test_upgrade_discards_uploaded_manual_and_previous_result():
    app=AppTest.from_file(str(ROOT/'app.py'))
    app.session_state['workflow_version']='ld-manual-v2'
    app.session_state['manual_file']=('Outra.xlsx',b'old')
    app.session_state['result']=('stale',{})
    app.run(timeout=30)
    assert not app.exception
    assert 'manual_file' not in app.session_state
    assert 'result' not in app.session_state
    assert len(app.get('file_uploader'))==1
