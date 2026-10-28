import json
from pathlib import Path
import pytest
from streamlit.testing.v1 import AppTest
from blossom.web import generate

ROOT = Path(__file__).resolve().parents[1]


def test_app_starts_and_requires_uploads():
    app = AppTest.from_file(str(ROOT/'app.py')).run(timeout=30)
    assert not app.exception
    assert app.button[0].disabled
    assert not app.toggle[0].value
    app.radio[0].set_value('Configuração').run()
    assert not app.exception
    assert app.number_input[0].value == 8.0
    assert app.number_input[1].value is None
    assert app.number_input[2].value is None
    app.text_input[0].set_value('Projeto de teste').run()
    app.number_input[0].set_value(6.0).run()
    app.radio[0].set_value('Arquivos').run()
    app.toggle[0].set_value(True).run()
    app.radio[0].set_value('Configuração').run()
    assert app.text_input[0].value == 'Projeto de teste'
    assert app.number_input[0].value == 6.0
    assert app.toggle[0].value
    assert app.button[0].disabled
    assert not app.exception



def test_web_requires_inputs():
    with pytest.raises(ValueError, match='Envie'):
        generate(b'', b'', {})


def test_web_real_uploads():
    if not (ROOT/'input/LD.xlsm').exists():
        pytest.skip('Planilhas comerciais locais indisponíveis')
    config=json.loads((ROOT/'config/parametros.json').read_text(encoding='utf-8'))
    tables, files=generate((ROOT/'input/LD.xlsm').read_bytes(),(ROOT/'input/Manual.xlsx').read_bytes(),config)
    assert len(tables['WBS'])==56
    assert len(tables['Atividades'])==952
    assert files['pre_cronograma.xlsx'].startswith(b'PK')
    assert len(json.loads(files['pendencias.json']))>0
    assert all(r['diferenca']==0 for r in tables['Auditoria_HH'])

    app = AppTest.from_file(str(ROOT/'app.py'))
    app.session_state['result'] = (tables, files)
    app.session_state['navigation'] = 'Resultados'
    app.run(timeout=30)
    assert not app.exception
    assert len(app.expander) == 5
    assert len(app.metric) == 4
    app.toggle[0].set_value(True).run()
    assert not app.exception
    assert len(app.metric) == 4
    assert any('1 - Emissão Inicial' in item.value for item in app.markdown)
    app.radio[0].set_value('Arquivos').run()
    app.radio[0].set_value('Resultados').run()
    assert len(app.metric) == 4
    assert not app.exception
