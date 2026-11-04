from decimal import Decimal as D
from blossom.team import forecast,bh_holidays,WorkCalendar


def data():
 return {'Atividades':[{'id':k,'nome':k,'etapa':0,'hh':8} for k in ['a','b']],
 'Atribuicoes_Funcoes':[{'atividade_id':k,'funcao':'EPleno','hh':8} for k in ['a','b']], 'Relacionamentos':[]}


def config():return {'jornada_hh_dia':8,'capacidade_profissionais':{'EPleno':1},'duracao_cliente_dias':{'2':None,'4':None}}


def test_hours_are_conserved_and_overload_is_visible():
 r=forecast(data(),config(),start='2026-10-13')
 assert r['hh_totais']==16 and r['hh_sem_previsao']==0
 assert r['carga_diaria'][0]['hh']==16 and r['carga_diaria'][0]['sobrecarga']
 assert r['carga_diaria'][0]['ocupacao']==2


def test_leveling_preserves_hours_and_respects_capacity():
 r=forecast(data(),config(),start='2026-10-13',level=True)
 assert [a['inicio'] for a in r['atividades']]==['2026-10-13','2026-10-14']
 assert sum(a['hh'] for a in r['carga_diaria'])==16
 assert all(not row['sobrecarga'] for row in r['carga_diaria'])


def test_missing_capacity_leaves_hours_pending_instead_of_inventing_dates():
 c=config();c['capacidade_profissionais']={}
 r=forecast(data(),c,start='2026-10-13')
 assert r['hh_sem_previsao']==16 and r['carga_diaria']==[]
 assert all(a['inicio'] is None for a in r['atividades'])


def test_technical_pending_propagates_and_explicit_decision_is_traceable():
 t=data();t['Atividades'][0]['prerequisitos_tecnicos_pendentes']='DF'
 t['Relacionamentos']=[{'predecessora':'a','sucessora':'b','tipo':'FS','defasagem_dias':0}]
 assert forecast(t,config())['hh_sem_previsao']==16
 assert forecast(t,config(),technical_decisions={'a':{'disponivel_desde_inicio':True,'justificativa':''}})['hh_sem_previsao']==16
 assert forecast(t,config(),technical_decisions={'a':{'disponivel_desde_inicio':True,'justificativa':'DF recebido e conferido'}})['hh_sem_previsao']==0
 assert t['Atividades'][0]['prerequisitos_tecnicos_pendentes']=='DF'


def test_calendar_skips_bh_holiday_and_weekend():
 holidays=[r['data'] for r in bh_holidays(2026)]
 c=WorkCalendar('2026-10-12',[0,1,2,3,4],holidays)
 assert c.day(0).isoformat()=='2026-10-13'
 assert '2026-08-15' in holidays and '2026-12-08' in holidays and '2026-11-20' in holidays
 assert '2026-02-17' not in holidays # carnival is not automatically a work closure


def test_client_effort_and_duration_are_independent():
 t=data();t['Atividades'][0]['etapa']=2;c=config();c['duracao_cliente_dias']['2']=3
 r=forecast(t,c,start='2026-10-13')
 assert r['atividades'][0]['duracao_dias']==3 and r['hh_totais']==16


def test_zero_client_deadline_does_not_discard_nonzero_effort():
 t=data();t['Atividades'][0]['etapa']=2;c=config();c['duracao_cliente_dias']['2']=0
 r=forecast(t,c)
 assert r['hh_sem_previsao']==8


def test_fractional_hours_and_weekly_capacity_are_not_rounded_to_days():
 t=data();t['Atribuicoes_Funcoes'][0]['hh']=D('.25')
 r=forecast(t,config(),start='2026-10-16',level=True)
 assert r['hh_totais']==D('8.25')
 assert sum(row['hh'] for row in r['carga_semanal'])==D('8.25')
 assert not any(row['sobrecarga'] for row in r['carga_diaria'])
