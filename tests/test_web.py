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
    assert app.number_input[0].value == 8.0
    assert app.number_input[1].value is None
    assert app.number_input[2].value is None
    app.text_input[0].set_value('Projeto de teste').run()
    assert not app.exception
    assert app.button[0].disabled


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
