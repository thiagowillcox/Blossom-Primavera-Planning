"""Explicit duration update and native CPM job, after all prerequisites are known."""
import hashlib
import html
import json
import urllib.request
from datetime import date,datetime,time,timedelta,timezone
from decimal import Decimal
from .client import ConnectionFailure,_exchange,_json
from .draft import positive_id,durable_write
from .effort import partition_hours,amount,TOL
from ..team import WorkCalendar

FIELDS=['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday']


def calendar_work(calendar,day,holidays,exceptions):
    if day in exceptions:pattern=exceptions[day]
    elif day in holidays:pattern='0'*48
    else:pattern=calendar.get('workTime'+FIELDS[day.weekday()])
    if not isinstance(pattern,str) or len(pattern)!=48 or set(pattern)-{'0','1'}:
        raise ConnectionFailure('Calendário Oracle com turnos não reconhecidos. Confira o calendário antes de enviar prazos.')
    return pattern


def timing_preview(session,package,hours_plan,report):
    from ..team_ui import plain
    if package.get('aviso_versao_tecnica'):
        raise ConnectionFailure('A marcação de entradas técnicas desta versão do Excel não foi confirmada. Revise a base antes de agendar.')
    p=report.get('premissas',{})
    digest=hashlib.sha256(json.dumps(package['tables'],default=plain,sort_keys=True).encode()).hexdigest()
    if p.get('source')!=digest or not p.get('reviewed') or not p.get('start'):
        raise ConnectionFailure('Prepare a previsão usando o Excel vinculado ao Oracle, preencha a data e confira os feriados.')
    rows=report['atividades']
    if any(r['pendencias'] or r['duracao_dias'] is None or not r['inicio'] or not r['fim'] for r in rows):
        raise ConnectionFailure('Há atividades sem prazo, capacidade ou validação técnica. Resolva as pendências antes de agendar.')
    if {r['id'] for r in rows}!=set(package['journal']['atividades']):raise ConnectionFailure('As atividades da previsão diferem do registro Oracle.')
    project=session.binding(package);pid=package['projectId']
    missing,_=partition_hours(hours_plan,session.rows('assignment/project/'+str(pid)))
    if missing:raise ConnectionFailure('Envie e confira todas as horas antes de agendar o projeto.')
    from urllib.parse import urlencode
    relation_rows=session.rows('relationship/projectRelationshipCode?'+urlencode({'workspaceCode':project['workspaceCode'],'projectCode':project['projectCode']}))
    expected_relations=set()
    for relation in package['tables']['Relacionamentos']:
        if relation.get('tipo')!='FS' or amount(relation['defasagem_dias'])!=0:
            raise ConnectionFailure('O agendamento inicial aceita somente relações FS sem defasagem.')
        expected_relations.add((package['journal']['atividades'][relation['predecessora']],package['journal']['atividades'][relation['sucessora']]))
    actual_pairs=set()
    for relation in relation_rows:
        pair=(relation.get('predActivityId'),relation.get('succActivityId'))
        if (relation.get('predProjectId')!=pid or relation.get('succProjectId')!=pid
            or relation.get('relationshipType')!='FINISH_TO_START' or amount(relation.get('lagHours'))!=0 or pair in actual_pairs):
            raise ConnectionFailure('As ligações Oracle diferem da base conferida.')
        actual_pairs.add(pair)
    if actual_pairs!=expected_relations:raise ConnectionFailure('As ligações foram alteradas ou a consulta está incompleta.')
    calendar_id=positive_id(project.get('calendarId'))
    calendar=session.read('calendar/'+str(calendar_id))
    if not isinstance(calendar,dict) or calendar.get('calendarId')!=calendar_id:raise ConnectionFailure('Calendário do projeto não reconhecido.')
    if calendar.get('holidayMoveType') not in (None,'NONE'):
        raise ConnectionFailure('O calendário Oracle desloca feriados. Confira essa regra no calendário antes de agendar.')
    holiday_rows=[]
    if calendar.get('holiday'):
        group=session.read('holidayList/'+str(positive_id(calendar['holiday'])))
        if not isinstance(group,dict) or not isinstance(group.get('holidays'),list):raise ConnectionFailure('Lista de feriados Oracle não reconhecida.')
        holiday_rows=group['holidays']
    first=date.fromisoformat(p['start']);last=max(date.fromisoformat(r['fim']) for r in rows)
    if (last-first).days>12000:raise ConnectionFailure('Horizonte do calendário acima do limite de conferência.')
    oracle_holidays=set()
    for holiday in holiday_rows:
        if holiday.get('holidayDate'):oracle_holidays.add(date.fromisoformat(holiday['holidayDate'][:10]))
        elif holiday.get('month') and holiday.get('dayOfMonth'):
            for year in range(first.year,last.year+1):
                try:oracle_holidays.add(date(year,int(holiday['month']),int(holiday['dayOfMonth'])))
                except ValueError:raise ConnectionFailure('Feriado Oracle com data não reconhecida.') from None
        else:raise ConnectionFailure('A lista Oracle possui feriado recorrente sem data fixa; confira esse calendário antes de agendar.')
    exception_rows=session.rows('calendar/exception/'+str(calendar_id))
    exceptions={}
    for item in exception_rows:
        if not item.get('exceptionDate') or not isinstance(item.get('workTime'),str):raise ConnectionFailure('Exceção de calendário Oracle não reconhecida.')
        day=date.fromisoformat(item['exceptionDate'][:10])
        if day in exceptions:raise ConnectionFailure('Exceções repetidas no calendário Oracle.')
        exceptions[day]=item['workTime']
    daily=amount(p['config']['jornada_hh_dia']);local_holidays={date.fromisoformat(v) for v in p['holidays']}
    weekdays=set(p['weekdays']);current=first
    while current<=last:
        actual=Decimal(calendar_work(calendar,current,oracle_holidays,exceptions).count('1'))/2
        expected=daily if current.weekday() in weekdays and current not in local_holidays else Decimal(0)
        if actual!=expected:
            raise ConnectionFailure('Calendário Oracle difere do site em '+current.strftime('%d/%m/%Y')+'. Ajuste e confira o calendário; o programa não o alterará automaticamente.')
        current+=timedelta(days=1)
    start=WorkCalendar(first,weekdays,local_holidays).day(0)
    pattern=calendar_work(calendar,start,oracle_holidays,exceptions);slot=pattern.index('1')
    stamp=datetime.combine(start,time(slot//2,(slot%2)*30),tzinfo=timezone(timedelta(hours=-3))).isoformat()
    actual_activities=session.rows('activity/project/'+str(pid))
    for a in actual_activities:
        if a.get('calendar')!=calendar_id or a.get('constraintType') not in (None,'NONE') or a.get('secondaryConstraintType') not in (None,'NONE'):
            raise ConnectionFailure('Há atividade com outro calendário ou restrição. Confira no Oracle antes de agendar.')
    updates=[]
    for row in rows:
        hours=amount(row['duracao_dias'])*daily
        if hours>10000000:raise ConnectionFailure('Duração acima do limite Oracle.')
        updates.append({'activityId':package['journal']['atividades'][row['id']],'projectId':pid,
            'plannedDuration':float(hours),'remainingDuration':float(hours),'durationType':'FIXED_DURATION_AND_UNITS'})
    return {'projectId':pid,'source_sha256':package['source_sha256'],'calendarId':calendar_id,
        'dataDate':stamp,'project_update':{'projectId':pid,'planStartDate':stamp,'dataDate':stamp,
            'projectCode':html.unescape(project['projectCode']),'projectName':html.unescape(project['projectName']),
            'workspaceId':positive_id(project['workspaceId'])},'updates':updates,
        'aviso':'Agendamento nativo CPM. Não envia restrições para reproduzir o nivelamento local, não altera feriados nem capacidades globais.'}


def timing_mutation(session,method,route,payload,expected):
    if (method,route) not in [('PUT','activity/batch'),('PUT','project'),('POST','action/scheduleProject')]:
        raise ConnectionFailure('Operação de prazos não permitida.')
    if not session._token:raise ConnectionFailure('Sessão encerrada.')
    request=urllib.request.Request('https://primavera-us2.oraclecloud.com/api/restapi/'+route,method=method,
        data=json.dumps(payload,allow_nan=False).encode(),headers={'Authorization':'Bearer '+session._token,'Content-Type':'application/json','Accept':'application/json'})
    raw=_exchange(session._opener,request,'Envio de prazos e agendamento',limit=33554432,expected=expected)
    return _json(raw,'Envio de prazos e agendamento') if raw else None


def send_timing(session,package,hours_plan,report,plan,journal_path):
    path=journal_path
    if path.exists():raise ConnectionFailure('Já existe registro de agendamento. Consulte o andamento; não repita a solicitação.')
    current=timing_preview(session,package,hours_plan,report)
    if current!=plan:raise ConnectionFailure('A prévia de prazos mudou; confira novamente.')
    state={'projectId':plan['projectId'],'source_sha256':package['source_sha256'],'estado':'em_andamento','pendente':None,'jobId':None}
    durable_write(path,state,exclusive=True)
    try:
        for start in range(0,len(plan['updates']),50):
            rows=plan['updates'][start:start+50];state['pendente']='duracoes';durable_write(path,state)
            result=timing_mutation(session,'PUT','activity/batch',rows,(200,))
            if not isinstance(result,dict) or result.get('warnings'):raise ConnectionFailure('Oracle retornou avisos ou resposta inesperada na atualização. Confira o registro antes de continuar.')
            state['pendente']=None;durable_write(path,state)
        actual={r['activityId']:r for r in session.rows('activity/project/'+str(plan['projectId']))}
        for row in plan['updates']:
            a=actual.get(row['activityId'])
            if not a or any(abs(amount(a.get(k))-amount(row[k]))>TOL for k in ('plannedDuration','remainingDuration')):
                raise ConnectionFailure('As durações não foram confirmadas pela nova leitura.')
        missing,_=partition_hours(hours_plan,session.rows('assignment/project/'+str(plan['projectId'])))
        if missing:raise ConnectionFailure('As horas não foram preservadas após atualizar durações. Confira o Oracle.')
        state['pendente']='data_inicio';durable_write(path,state)
        timing_mutation(session,'PUT','project',plan['project_update'],(204,))
        project=session.read('project/'+str(plan['projectId']))
        expected=datetime.fromisoformat(plan['project_update']['planStartDate'])
        value=project.get('planStartDate') if isinstance(project,dict) else None
        if not value or datetime.fromisoformat(value.replace('Z','+00:00'))!=expected:raise ConnectionFailure('Data inicial não confirmada no Oracle.')
        state['pendente']='agendamento';durable_write(path,state)
        job=timing_mutation(session,'POST','action/scheduleProject',{'projectId':plan['projectId'],'dataDate':plan['dataDate']},(201,))
        if not isinstance(job,dict):raise ConnectionFailure('Resposta de agendamento não reconhecida.')
        state['jobId']=positive_id(job.get('jobId'));state['estado']='job_solicitado';state['pendente']=None
        durable_write(path,state);return state
    except BaseException:
        state['estado']='interrompido_conferir_oracle';durable_write(path,state);raise
