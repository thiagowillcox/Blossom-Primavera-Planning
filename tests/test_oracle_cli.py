import json
from pathlib import Path
import pytest
import blossom.oracle.__main__ as cli


@pytest.mark.parametrize('choice',['7','999'])
def test_project_selection_is_explicit_local_and_has_no_credentials(tmp_path,monkeypatch,capsys,choice):
    monkeypatch.chdir(tmp_path)
    old=Path('output/consulta_primavera_local.json');old.parent.mkdir()
    old.write_text(json.dumps({'projeto_selecionado':{'projectId':99}}))
    values=iter(['test@example.org','Laboratório',choice])
    monkeypatch.setattr('sys.argv',['oracle','--listar-projetos'])
    monkeypatch.setattr('builtins.input',lambda _:next(values))
    monkeypatch.setattr(cli,'getpass',lambda _:'fictional-password')
    monkeypatch.setattr(cli,'list_projects',lambda *_:[{'projectId':7,'projectName':'Laboratório','projectCode':'LAB','workspaceId':2}])
    assert cli.main()==0
    assert 'fictional-password' not in capsys.readouterr().out
    if choice=='7':
        data=json.loads(old.read_text())
        assert data['projeto_selecionado']['projectId']==7
        assert 'fictional-password' not in old.read_text()
    else:assert not old.exists()
