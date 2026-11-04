from pathlib import Path
from streamlit.testing.v1 import AppTest
from blossom.oracle.effort import load_package
from test_oracle_effort import files
ROOT=Path(__file__).resolve().parents[1]


def test_new_pages_start_without_credentials_or_source_files():
 app=AppTest.from_file(str(ROOT/'app.py')).run(timeout=30)
 app.radio[0].set_value('Equipe e prazos').run()
 assert not app.exception and app.info
 app.radio[0].set_value('Primavera').run()
 assert not app.exception
 assert len(app.get('file_uploader'))==0
 assert not app.text_input # no password requested before a verified package


def test_team_form_keeps_unfilled_capacities_pending_and_exports_preview(tmp_path):
 package=load_package(*files(tmp_path))
 app=AppTest.from_file(str(ROOT/'app.py'))
 app.session_state['workflow_version']='ld-relacoes-v4'
 app.session_state['oracle_package']=package
 app.session_state['navigation']='Equipe e prazos'
 app.run(timeout=30)
 assert not app.exception
 assert app.date_input[0].value is None
 assert next(w for w in app.number_input if w.label=='Profissionais — EPleno').value is None
 next(b for b in app.button if b.label=='Preparar visão de equipe e prazos').click().run(timeout=30)
 assert not app.exception
 assert app.session_state['team_report']['hh_sem_previsao']==10
 app.date_input[0].set_value('2026-10-13').run()
 next(w for w in app.number_input if w.label=='Profissionais — EPleno').set_value(1).run()
 next(b for b in app.button if b.label=='Preparar visão de equipe e prazos').click().run(timeout=30)
 assert not app.exception
 assert app.session_state['team_report']['hh_sem_previsao']==0
 assert app.session_state['team_report']['atividades'][0]['inicio']=='2026-10-13'


def test_oracle_web_login_preview_and_confirmed_hours_upload(tmp_path,monkeypatch):
 import io
 import streamlit as st
 import blossom.oracle.web_ui as ui
 from blossom.oracle.effort import EffortSession
 from test_oracle_effort import EffortOracle
 excel_bytes,record_bytes=files(tmp_path)
 class Uploaded(io.BytesIO):
  def __init__(self,data,name):super().__init__(data);self.name=name
 excel=Uploaded(excel_bytes,'schedule.xlsx');record=Uploaded(record_bytes,'record.json')
 def uploader(label,**kwargs):
  if label.startswith('Excel original'):return excel
  if label.startswith('Registro estrutural'):return record
  return None
 monkeypatch.setattr(st,'file_uploader',uploader)
 monkeypatch.setattr(ui,'gettempdir',lambda:str(tmp_path))
 oracle=EffortOracle()
 monkeypatch.setattr(ui,'EffortSession',lambda username,password:EffortSession(username,password,opener=oracle))
 app=AppTest.from_file(str(ROOT/'app.py'))
 app.session_state['workflow_version']='ld-relacoes-v4';app.session_state['navigation']='Primavera'
 app.run(timeout=30)
 next(w for w in app.selectbox if w.label=='Base para integração').set_value('Importar registros antigos (opcional)').run(timeout=30)
 assert not app.exception
 app.text_input[0].set_value('test');app.text_input[1].set_value('fictional-password')
 next(b for b in app.button if b.label=='Conectar ao Oracle').click().run(timeout=30)
 assert not app.exception
 assert app.session_state['oracle_password']==''
 next(b for b in app.button if b.label=='Consultar projeto e funções disponíveis').click().run(timeout=30)
 assert not app.exception
 next(c for c in app.checkbox if c.label.startswith('Conferi a correspondência')).check().run()
 next(b for b in app.button if b.label=='Preparar prévia das horas').click().run(timeout=30)
 assert not app.exception
 assert not oracle.assignments
 next(b for b in app.button if b.label=='Conferir situação das horas (sem enviar)').click().run(timeout=30)
 assert not app.exception and not oracle.assignments
 assert app.session_state['oracle_hours_diagnostic']['resumo']['nao_encontradas']==1
 assert next(b for b in app.button if b.label=='Enviar e conferir horas no Oracle').disabled
 next(t for t in app.text_input if t.label.startswith('Para gravar no projeto')).set_value('ENVIAR HORAS 7').run()
 assert any('Prévia:' in item.value for item in app.success)
 next(b for b in app.button if b.label=='Enviar e conferir horas no Oracle').click().run(timeout=30)
 assert not app.exception and len(oracle.assignments)==1
 assert app.session_state['oracle_hours_result']['estado']=='horas_conferidas'
 assert app.session_state['oracle_password']==''
 next(b for b in app.button if b.label=='Desconectar').click().run(timeout=30)
 assert not app.exception
 assert 'oracle_session' not in app.session_state


def test_team_inputs_and_report_survive_navigation(tmp_path):
 package=load_package(*files(tmp_path));app=AppTest.from_file(str(ROOT/'app.py'))
 app.session_state['workflow_version']='ld-relacoes-v4';app.session_state['oracle_package']=package;app.session_state['navigation']='Equipe e prazos'
 app.run(timeout=30)
 app.date_input[0].set_value('2026-10-13').run()
 next(w for w in app.number_input if w.label=='Profissionais — EPleno').set_value(2).run()
 next(b for b in app.button if b.label=='Preparar visão de equipe e prazos').click().run()
 app.radio[0].set_value('Resultados').run()
 app.radio[0].set_value('Equipe e prazos').run()
 assert not app.exception
 assert app.date_input[0].value.isoformat()=='2026-10-13'
 assert next(w for w in app.number_input if w.label=='Profissionais — EPleno').value==2
 assert app.session_state['team_report']['hh_sem_previsao']==0


def test_recovery_can_be_confirmed_after_preview_blocks_existing_default_hours(tmp_path,monkeypatch):
 import blossom.oracle.web_ui as ui
 from test_oracle_effort import interrupted_default_batch
 package,oracle,session,plan,_=interrupted_default_batch(tmp_path)
 (tmp_path/'hours.json').rename(tmp_path/'registro_horas.json')
 monkeypatch.setattr(ui,'project_files',lambda *args:tmp_path)
 app=AppTest.from_string('import streamlit as st\nfrom blossom.oracle.web_ui import render\nrender(st,package=st.session_state.test_package)')
 app.session_state['test_package']=package;app.session_state['oracle_session']=session
 app.run(timeout=30)
 next(b for b in app.button if b.label=='Consultar projeto e funções disponíveis').click().run()
 next(c for c in app.checkbox if c.label.startswith('Conferi a correspondência')).check().run()
 next(b for b in app.button if b.label=='Preparar prévia das horas').click().run()
 assert not app.session_state['oracle_hours_ready']
 next(b for b in app.button if b.label=='Conferir situação das horas (sem enviar)').click().run()
 next(t for t in app.text_input if t.label.startswith('Para gravar no projeto')).set_value('ENVIAR HORAS 7').run()
 assert next(b for b in app.button if b.label=='Enviar e conferir horas no Oracle').disabled
 next(c for c in app.checkbox if c.label.startswith('Corrigir as horas')).check().run()
 assert not next(b for b in app.button if b.label=='Enviar e conferir horas no Oracle').disabled
 next(b for b in app.button if b.label=='Enviar e conferir horas no Oracle').click().run(timeout=30)
 assert not app.exception
 assert app.session_state['oracle_hours_result']['estado']=='horas_conferidas'
 assert len(oracle.assignments)==1 and oracle.assignments[0]['plannedUnits']==10
