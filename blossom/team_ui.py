"""Streamlit team forecast, separate from immutable LD/export results."""
import hashlib
import io
import json
from datetime import date
from decimal import Decimal
import openpyxl
from .team import forecast,bh_holidays


def plain(value):
    if isinstance(value,Decimal):return str(value)
    if isinstance(value,(date,)):return value.isoformat()
    raise TypeError(type(value).__name__)


def hh_label(value):
    from .oracle.preview import amount
    value=format(amount(value),',.6f').rstrip('0').rstrip('.')
    return value.replace(',','X').replace('.',',').replace('X','.')


def workbook_bytes(report):
    book=openpyxl.Workbook();book.remove(book.active)
    for title,key in [('Atividades','atividades'),('Carga_diaria','carga_diaria'),('Carga_semanal','carga_semanal')]:
        sheet=book.create_sheet(title);rows=report[key];keys=list(dict.fromkeys(k for r in rows for k in r))
        sheet.append(keys or ['status'])
        for row in rows:
            values=[float(row[k]) if isinstance(row.get(k),Decimal) else json.dumps(row.get(k),ensure_ascii=False) if isinstance(row.get(k),(list,dict)) else row.get(k) for k in keys]
            sheet.append(values)
            for cell in sheet[sheet.max_row]:
                if isinstance(cell.value,str):cell.data_type='s'
        sheet.freeze_panes='A2'
    sheet=book.create_sheet('Premissas')
    for k,v in report.get('premissas',{}).items():
        sheet.append([k,json.dumps(v,ensure_ascii=False,default=plain)])
        sheet.cell(sheet.max_row,2).data_type='s'
    output=io.BytesIO();book.save(output);book.close();return output.getvalue()


def render(st,config):
    from .ui import heading
    heading('04 · EQUIPE E PRAZOS','Horas, equipe e datas em uma visão só.',
        'Preencha o que já sabe. O que depender de decisão técnica, equipe ou cliente continuará pendente.')
    sources={}
    if st.session_state.get('result'):sources['Pré-cronograma desta sessão']=st.session_state.result[0]
    if st.session_state.get('oracle_package'):sources['Excel vinculado ao projeto Oracle']=st.session_state.oracle_package['tables']
    if not sources:
        st.info('Gere um pré-cronograma ou importe o Excel e seu registro na seção Primavera.');return
    source=st.selectbox('Base da previsão',list(sources));tables=sources[source]
    key=hashlib.sha256(json.dumps(tables,default=plain,sort_keys=True).encode()).hexdigest()
    saved=st.session_state.setdefault('workforce_inputs',{})
    def remember(name,key):saved[name]=st.session_state[key]
    def options(name,key,default):
        return {'key':key,'value':saved.get(name,default),'on_change':remember,'args':(name,key)}
    a,b=st.columns(2)
    with a:
        start=st.date_input('Data de início',format='DD/MM/YYYY',**options('start','team_start',None))
        daily=st.number_input('Horas por profissional por dia',min_value=0.5,max_value=24.0,step=0.5,**options('daily','team_daily',float(config['jornada_hh_dia'])))
        names=['Segunda','Terça','Quarta','Quinta','Sexta','Sábado','Domingo']
        weekdays=st.multiselect('Dias úteis',range(7),default=saved.get('weekdays',list(range(5))),format_func=lambda i:names[i],key='team_weekdays',on_change=remember,args=('weekdays','team_weekdays'))
    with b:
        client={}
        for stage,label in [('2','Comentários do cliente (dias úteis)'),('4','Aprovação do cliente (dias úteis)')]:
            client[stage]=st.number_input(label,min_value=0.0,step=1.0,**options('client'+stage,'team_client_'+stage,config['duracao_cliente_dias'].get(stage)))
        level=st.checkbox('Ajustar a previsão local à capacidade total da equipe',**options('level','team_level',False))
        st.caption('Sem essa opção, atividades podem disputar a mesma equipe; a sobrecarga aparece no relatório. O ajuste usa uma heurística e não garante o menor prazo possível.')
    roles=sorted({a['funcao'] for a in tables['Atribuicoes_Funcoes']})
    caps={};columns=st.columns(3)
    for i,role in enumerate(roles):
        with columns[i%3]:
            value=st.number_input('Profissionais — '+role,min_value=0.01,step=0.5,**options('cap_'+role,'team_cap_'+role,config['capacidade_profissionais'].get(role)))
            if value is not None:caps[role]=value
    with st.expander('Calendário de Belo Horizonte e feriados',expanded=False):
        year=start.year if start else date.today().year
        suggestions=[r for y in range(year,year+3) for r in bh_holidays(y)]
        st.caption('Lista sugerida para três anos, editável. Confira o calendário oficial e os acordos da empresa. Carnaval e pontos facultativos não são incluídos automaticamente.')
        st.dataframe(suggestions,hide_index=True)
        text=st.text_area('Feriados e outras paralisações (uma data AAAA-MM-DD por linha)',
            height=150,**options('holidays_'+str(year),'team_holidays_'+str(year),'\n'.join(r['data'] for r in suggestions)))
        cal_key=hashlib.sha256(json.dumps([start.isoformat() if start else None,daily,weekdays,text]).encode()).hexdigest()
        reviewed=st.checkbox('Conferi os dias úteis e a lista de feriados',**options('review_'+cal_key,'team_calendar_reviewed_'+cal_key,False))
    decisions_key='team_decisions_'+key
    decisions=st.session_state.setdefault(decisions_key,{})
    technical=[a for a in tables['Atividades'] if a.get('prerequisitos_tecnicos_pendentes')]
    if technical:
        with st.expander('Registrar validações das entradas técnicas'):
            st.caption('Registre apenas entradas efetivamente disponíveis desde o início. Essa decisão é sua e não altera a LD nem apaga a pendência original.')
            by_id={a['id']:a for a in technical}
            aid=st.selectbox('Atividade para conferir',list(by_id),format_func=lambda value:by_id[value]['nome'],key='team_decision_choice_'+key)
            st.write(by_id[aid]['prerequisitos_tecnicos_pendentes'])
            reason=st.text_area('Justificativa e referência da confirmação',value=decisions.get(aid,{}).get('justificativa',''),key='team_reason_'+key+'_'+aid)
            confirmed=st.checkbox('Confirmo que essas entradas estão disponíveis desde o início previsto',value=aid in decisions,key='team_released_'+key+'_'+aid)
            if st.button('Registrar decisão desta atividade'):
                if confirmed and not reason.strip():st.error('Informe a referência ou justificativa da confirmação.')
                else:
                    if confirmed:decisions[aid]={'disponivel_desde_inicio':True,'justificativa':reason.strip()}
                    else:decisions.pop(aid,None)
                    st.success('Decisão registrada nesta sessão. Gere novamente a previsão e baixe o relatório para guardar.')
    params=dict(config,jornada_hh_dia=daily,capacidade_profissionais=caps,duracao_cliente_dias=client)
    specification={'source':key,'config':params,'start':start.isoformat() if start else None,'weekdays':weekdays,
        'holidays':text,'level':level,'reviewed':reviewed,'decisoes_tecnicas':decisions}
    signature=hashlib.sha256(json.dumps(specification,sort_keys=True,default=plain).encode()).hexdigest()
    if st.session_state.get('team_signature')!=signature:
        st.session_state.pop('team_report',None);st.session_state.pop('timing_plan',None)
    if st.button('Preparar visão de equipe e prazos',type='primary'):
        try:
            holidays=sorted({date.fromisoformat(line.strip()).isoformat() for line in text.splitlines() if line.strip()})
            with st.spinner('Distribuindo horas e conferindo a equipe…'):
                report=forecast(tables,params,start=start,weekdays=weekdays,holidays=holidays,level=level,technical_decisions=decisions)
            report['premissas']=dict(specification,holidays=holidays)
            st.session_state.team_report=report;st.session_state.team_signature=signature
        except (ValueError,KeyError,TypeError) as exc:st.error('Não foi possível preparar a visão: '+str(exc))
    report=st.session_state.get('team_report')
    if report:
        pending=sum(bool(r['pendencias']) for r in report['atividades'])
        for col,label,value in zip(st.columns(3),['HH totais','HH sem previsão','Atividades pendentes'],[hh_label(report['hh_totais']),hh_label(report['hh_sem_previsao']),pending]):col.metric(label,value)
        if not start:st.info('Preencha a data de início para ver datas no calendário. As horas continuam disponíveis.')
        if not reviewed:st.info('O calendário ainda precisa da sua conferência antes de enviar prazos ao Oracle.')
        if any(r['sobrecarga'] for r in report['carga_diaria']):st.warning('Há dias com carga acima da equipe informada. Confira a tabela ou ative o ajuste à capacidade.')
        if any(r.get('fim') and int(r['fim'][:4])>year+2 for r in report['atividades']):st.warning('A previsão ultrapassa os três anos sugeridos. Acrescente e confira os feriados dos anos seguintes.')
        if report['carga_semanal']:
            st.subheader('Carga da equipe ao longo das semanas')
            selected_role=st.selectbox('Função para analisar',sorted({r['funcao'] for r in report['carga_semanal']}),key='team_chart_role')
            chart=[{'Semana':r['semana'],'Horas planejadas':float(r['hh']),'Horas disponíveis':float(r['capacidade_hh']) if r['capacidade_hh'] is not None else None} for r in report['carga_semanal'] if r['funcao']==selected_role]
            st.line_chart(chart,x='Semana',y=['Horas planejadas','Horas disponíveis'])
        displays=[('Atividades e prazos','atividades',[('nome','Atividade / etapa'),('duracao_dias','Duração em dias úteis'),('inicio','Início previsto'),('fim','Término previsto'),('pendencias','O que falta')]),
            ('Carga diária por função','carga_diaria',[('dia_util','Dia útil'),('data','Data'),('funcao','Função'),('hh','HH planejadas'),('capacidade_hh','HH disponíveis'),('ocupacao','Ocupação'),('sobrecarga','Sobrecarga')]),
            ('Carga semanal por função','carga_semanal',[('semana','Semana a partir de'),('funcao','Função'),('hh','HH planejadas'),('capacidade_hh','HH disponíveis')])]
        for title,field,columns in displays:
            with st.expander(title):
                def show(k,v):
                    if k=='ocupacao' and v is not None:return f'{v*100:.1f}%'
                    if k=='sobrecarga':return 'Sim' if v else 'Não' if v is not None else 'Equipe não informada'
                    if isinstance(v,Decimal):return hh_label(v)
                    if isinstance(v,list):return '; '.join(v)
                    return v
                shown=[{label:show(k,row.get(k)) for k,label in columns} for row in report[field]]
                st.dataframe(shown,hide_index=True)
        st.download_button('Baixar previsão da equipe — Excel',workbook_bytes(report),'previsao_equipe.xlsx','application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        st.download_button('Baixar premissas e previsão — JSON',json.dumps(report,ensure_ascii=False,default=plain,indent=2),'previsao_equipe.json','application/json')
        st.caption(report['aviso'])
