"""Editable local calendar and resource forecast; preserves original LD effort."""
from collections import defaultdict
from datetime import date,timedelta
from decimal import Decimal, ROUND_CEILING
from .duration import duration
from .validation import topology

D=Decimal


def easter(year):
    a=year%19;b=year//100;c=year%100;d=b//4;e=b%4;f=(b+8)//25;g=(b-f+1)//3
    h=(19*a+b-d-g+15)%30;i=c//4;k=c%4;l=(32+2*e+2*i-h-k)%7;m=(a+11*h+22*l)//451
    month=(h+l-7*m+114)//31;day=(h+l-7*m+114)%31+1
    return date(year,month,day)


def bh_holidays(year):
    """Reviewable BH holiday suggestion; carnival/optional closures are not holidays here."""
    fixed=[(1,1,'Confraternização Universal'),(4,21,'Tiradentes'),(5,1,'Dia do Trabalho'),
        (8,15,'Assunção de Nossa Senhora — BH'),(9,7,'Independência'),(10,12,'Nossa Senhora Aparecida'),
        (11,2,'Finados'),(11,15,'Proclamação da República'),(12,8,'Imaculada Conceição — BH'),(12,25,'Natal')]
    if year>=2024:fixed.append((11,20,'Consciência Negra'))
    rows=[{'data':date(year,m,d).isoformat(),'nome':name} for m,d,name in fixed]
    rows.extend([{'data':(easter(year)-timedelta(days=2)).isoformat(),'nome':'Sexta-feira da Paixão'},
        {'data':(easter(year)+timedelta(days=60)).isoformat(),'nome':'Corpus Christi — BH'}])
    return sorted(rows,key=lambda r:r['data'])


class WorkCalendar:
    def __init__(self,start,weekdays,holidays):
        self.start=date.fromisoformat(start) if isinstance(start,str) else start
        if not isinstance(self.start,date):raise ValueError('Preencha a data de início.')
        self.weekdays=set(weekdays)
        if not self.weekdays or not self.weekdays<=set(range(7)):raise ValueError('Selecione os dias úteis da semana.')
        self.holidays={date.fromisoformat(v) if isinstance(v,str) else v for v in holidays}
        self.days=[];self.next_day=self.start

    def day(self,index):
        if index<0 or index>8000:raise ValueError('A previsão ultrapassa o horizonte de 8.000 dias úteis. Confira a capacidade da equipe.')
        while len(self.days)<=index:
            current=self.next_day;self.next_day+=timedelta(days=1)
            if (current-self.start).days>20000:raise ValueError('Calendário sem dias úteis suficientes.')
            if current.weekday() in self.weekdays and current not in self.holidays:self.days.append(current)
        return self.days[index]


def forecast(tables, config, *, start=None, weekdays=(0,1,2,3,4), holidays=(), level=False, technical_decisions=None):
    daily=D(str(config['jornada_hh_dia']))
    if not daily.is_finite() or not 0<daily<=24:raise ValueError('A jornada deve estar entre 0 e 24 horas por dia.')
    capacities={k:D(str(v)) for k,v in config['capacidade_profissionais'].items()}
    if any(not v.is_finite() or v<=0 for v in capacities.values()):raise ValueError('Informe uma capacidade positiva por função.')
    calendar=WorkCalendar(start,weekdays,holidays) if start else None
    hours=defaultdict(lambda:defaultdict(D));total=D(0)
    for row in tables['Atribuicoes_Funcoes']:
        hh=D(str(row['hh']))
        if not hh.is_finite() or hh<0:raise ValueError('Horas inválidas na atribuição.')
        hours[row['atividade_id']][row['funcao']]+=hh;total+=hh
    activities={r['id']:r for r in tables['Atividades'] if r.get('tipo_linha','atividade')=='atividade'}
    links=tables['Relacionamentos'];incoming=defaultdict(list)
    for r in links:
        if r.get('tipo')!='FS' or D(str(r['defasagem_dias']))<0:raise ValueError('A previsão aceita apenas FS com defasagem não negativa.')
        incoming[r['sucessora']].append(r)
    intervals=[];events=defaultdict(lambda:defaultdict(D));result={};daily_load=defaultdict(D);unplaced=defaultdict(D)
    for aid in topology(list(activities.values()),links):
        a=activities[aid];hh=hours[aid];pending=[]
        days=duration(hh,config,a['etapa'])
        if days is None:pending.append('Capacidade da função ou prazo do cliente não preenchido')
        elif not days.is_finite() or days<0:raise ValueError('Duração inválida.')
        decision=(technical_decisions or {}).get(aid,{})
        released=decision.get('disponivel_desde_inicio') is True and isinstance(decision.get('justificativa'),str) and bool(decision['justificativa'].strip())
        if a.get('prerequisitos_tecnicos_pendentes') and not released:pending.append('Entrada técnica pendente')
        if any(result[r['predecessora']]['fim_hora_util'] is None for r in incoming[aid]):pending.append('Predecessora sem previsão definida')
        work=days*daily if days is not None else None
        if work is not None and work==0 and sum(hh.values(),D(0))>0:pending.append('Prazo zero incompatível com horas de acompanhamento')
        if work is not None and work>daily*8000:raise ValueError('Duração acima do horizonte de previsão.')
        rates={k:v/work for k,v in hh.items()} if work else {}
        if level and any(k not in capacities or rate>capacities[k]+D('.000000001') for k,rate in rates.items()):
            pending.append('Horas não cabem na equipe durante o prazo informado')
        begin=end=None
        if not pending:
            begin=max((result[r['predecessora']]['fim_hora_util']+D(str(r['defasagem_dias']))*daily for r in incoming[aid]),default=D(0))
            if level and work:
                # Serial schedule-generation heuristic, not an optimal-schedule solver.
                for _ in range(len(intervals)*2+2):
                    stop=begin+work
                    points=sorted({begin,stop}|{t for t in events if begin<t<stop})
                    load={role:sum((rr.get(role,D(0)) for s,e,rr in intervals if s<=begin<e),D(0)) for role in rates}
                    clash=None
                    for left,right in zip(points,points[1:]):
                        if left!=begin:
                            for role in rates:load[role]+=events[left].get(role,D(0))
                        if any(rate+load[role]>capacities[role]+D('.000000001') for role,rate in rates.items()):
                            clash=min(e for s,e,_ in intervals if s<=left<e);break
                    if clash is None:break
                    begin=clash
                else:raise ValueError('Não foi possível encontrar uma janela de capacidade para a atividade.')
            end=begin+work
            if end>daily*8000:raise ValueError('A equipe informada leva o projeto além do horizonte de previsão.')
            if work:
                intervals.append((begin,end,rates))
                for role,rate in rates.items():events[begin][role]+=rate;events[end][role]-=rate
                for index in range(int(begin//daily),int((end/daily).to_integral_value(rounding=ROUND_CEILING))):
                    overlap=min(end,(index+1)*daily)-max(begin,index*daily)
                    for role,rate in rates.items():daily_load[(index,role)]+=overlap*rate
        else:
            for role,value in hh.items():unplaced[role]+=value
        finish_index=max(0,int((end/daily).to_integral_value(rounding=ROUND_CEILING))-1) if end is not None else None
        result[aid]={'id':aid,'nome':a['nome'],'duracao_dias':days,'inicio_hora_util':begin,'fim_hora_util':end,
            'inicio':calendar.day(int(begin//daily)).isoformat() if calendar and begin is not None else None,
            'fim':calendar.day(finish_index).isoformat() if calendar and end is not None else None,
            'pendencias':pending}
    load=[];weekly=defaultdict(D);weekly_capacity={}
    for (index,role),hh in sorted(daily_load.items()):
        when=calendar.day(index) if calendar else None;available=capacities.get(role)
        capacity=available*daily if available is not None else None
        load.append({'dia_util':index+1,'data':when.isoformat() if when else None,'funcao':role,'hh':hh,
            'capacidade_hh':capacity,'ocupacao':hh/capacity if capacity else None,'sobrecarga':hh>capacity+D('.000000001') if capacity else None})
        if when:
            monday=when-timedelta(days=when.weekday());weekly[(monday,role)]+=hh
    for (monday,role),hh in sorted(weekly.items()):
        count=sum(1 for i in range(7) if (monday+timedelta(days=i)).weekday() in calendar.weekdays
            and monday+timedelta(days=i) not in calendar.holidays and monday+timedelta(days=i)>=calendar.start)
        cap=capacities.get(role);weekly_capacity[(monday,role)]=cap*daily*count if cap is not None else None
    accounted=sum(daily_load.values(),D(0))+sum(unplaced.values(),D(0))
    if abs(accounted-total)>D('.000001'):raise ValueError('Falha na conservação das horas da previsão.')
    return {'atividades':list(result.values()),'carga_diaria':load,
        'carga_semanal':[{'semana':m.isoformat(),'funcao':r,'hh':hh,'capacidade_hh':weekly_capacity[(m,r)]} for (m,r),hh in sorted(weekly.items())],
        'hh_totais':total,'hh_sem_previsao':sum(unplaced.values(),D(0)),
        'hh_sem_previsao_por_funcao':dict(unplaced),'nivelamento':level,
        'aviso':'Previsão local para revisão; não é agendamento do Oracle. Pendências técnicas permanecem bloqueadas.'}
