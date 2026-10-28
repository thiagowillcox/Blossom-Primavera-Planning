import hashlib
import json
import logging
from decimal import Decimal
from pathlib import Path
import streamlit as st
from blossom.web import generate, ROLES
from blossom.hierarchy import activity_hierarchy
from blossom.ui import apply_theme, heading, table

ROOT=Path(__file__).resolve().parent
st.set_page_config(page_title='Blossom Planning',page_icon='🌸',layout='wide')
ss=st.session_state
if 'settings' not in ss:
    ss.settings={'project':'','daily':8.0,'comments':None,'approval':None,
                 **{'cap_'+role:None for role in ROLES}}
if ss.get('workflow_version') != 'ld-manual-v2':
    previous_profile=ss.settings.pop('profile',None)
    if previous_profile and previous_profile!='Capacidade por função':
        ss.settings={'project':'','daily':8.0,'comments':None,'approval':None,
                     **{'cap_'+role:None for role in ROLES}}
        for key in list(ss):
            if key.startswith('field_'):ss.pop(key,None)
    for legacy in ('result','result_key','reference_result','reference_file','field_profile','field_project','field_daily','field_comments','field_approval'):
        ss.pop(legacy,None)
    ss.workflow_version='ld-manual-v2'
if '_go' in ss:
    ss.navigation=ss.pop('_go')


def go(page):
    ss._go=page


def save_setting(name):
    ss.settings[name]=ss['field_'+name]


def upload_changed(kind):
    upload=ss.get('upload_'+kind)
    ss[kind+'_file']=(upload.name,upload.getvalue()) if upload is not None else None


with st.sidebar:
    apply_theme()
    logo=ROOT/'assets/logo-dark.png'
    if logo.exists():st.image(str(logo),width=205)
    else:st.markdown('### Blossom')
    st.markdown('<div class="side-title">Blossom Planning</div><div class="side-sub">ENGENHARIA & PLANEJAMENTO</div>',unsafe_allow_html=True)
    page=st.radio('Seu planejamento',['Arquivos','Configuração','Resultados'],key='navigation')
    st.divider()
    st.caption('Do escopo ao próximo passo.')
    st.caption('Pré-cronograma para revisão da equipe. As precedências do manual ainda são preliminares.')
    st.caption('Processamento local · sem envio ao Oracle')

settings=ss.settings
config=json.loads((ROOT/'config/parametros.json').read_text(encoding='utf-8'))
config.update(projeto=settings['project'].strip() or 'Projeto não identificado',
              jornada_hh_dia=settings['daily'],
              capacidade_profissionais={role:settings['cap_'+role] for role in ROLES if settings['cap_'+role] is not None},
              duracao_cliente_dias={'2':settings['comments'],'4':settings['approval']})
fingerprint=hashlib.sha256(json.dumps(config,sort_keys=True).encode())
for kind in ('ld','manual'):
    if ss.get(kind+'_file'):fingerprint.update(ss[kind+'_file'][1])
key=fingerprint.hexdigest()
if ss.get('result_key') is not None and ss.result_key!=key:
    ss.pop('result',None);ss.pop('result_key',None)
ready=bool(ss.get('ld_file') and ss.get('manual_file'))

if page=='Arquivos':
    heading('01 · ARQUIVOS','Seu planejamento começa aqui.',
            'Envie a lista de documentos e o manual de engenharia. Nós organizamos a estrutura para você revisar com a equipe.')
    c1,c2=st.columns(2,gap='large')
    for col,kind,title,description,types in (
        (c1,'ld','Lista de Documentos','A LD comercial com entregáveis e horas por função.',['xlsm','xlsx']),
        (c2,'manual','Manual de Engenharia','A versão do manual usada como referência técnica.',['xlsx'])):
        with col,st.container(border=True,key="card_"+kind):
            st.subheader(title)
            st.caption(description)
            st.file_uploader('Selecionar '+title,type=types,key='upload_'+kind,
                             on_change=upload_changed,args=(kind,),label_visibility='collapsed')
            if ss.get(kind+'_file'):
                name,data=ss[kind+'_file']
                st.success('Arquivo selecionado: '+name)
                st.caption(f'{len(data)/1024/1024:.2f} MB · mantido nesta sessão ao navegar')
    st.markdown('<div class="notice"><strong>Seus arquivos, preservados.</strong><br>As planilhas originais não são alteradas. O Excel gerado fica disponível para download nesta sessão.</div>',unsafe_allow_html=True)
    st.button('Configurar projeto →',type='primary',disabled=not ready,on_click=go,args=('Configuração',))

elif page=='Configuração':
    heading('02 · CONFIGURAÇÃO','Cada projeto tem seu ritmo.',
            'Ajuste as premissas do planejamento. O que ainda não estiver definido pode ficar em branco para validação posterior.')
    if not ready:st.info('Envie as duas planilhas na seção Arquivos para liberar a geração.')
    a,b=st.columns([1.1,1],gap='large')
    with a,st.container(border=True,key="project_card"):
        st.subheader('Dados do projeto')
        st.text_input('Nome do projeto',value=settings['project'],placeholder='Ex.: Forno III',
                      key='field_project',on_change=save_setting,args=('project',))
        st.number_input('Jornada (HH por profissional/dia)',min_value=0.1,max_value=24.0,
                        value=settings['daily'],step=0.5,key='field_daily',on_change=save_setting,args=('daily',))
    with b,st.container(border=True,key="client_card"):
        st.subheader('Prazos do cliente')
        st.caption('Independentes das horas de acompanhamento. Deixe vazio se ainda não houver definição.')
        for name,label in [('comments','Comentários do cliente (dias)'),('approval','Aprovação final (dias)')]:
            st.number_input(label,min_value=0.0,value=settings[name],step=1.0,
                            key='field_'+name,on_change=save_setting,args=(name,))
    with st.expander('Capacidade disponível por função',expanded=False):
        st.caption('Quantidade equivalente de profissionais por atividade. Campos vazios mantêm a duração pendente; não há nivelamento entre atividades simultâneas.')
        columns=st.columns(3)
        for index,role in enumerate(ROLES):
            name='cap_'+role
            with columns[index%3]:
                st.number_input(role,min_value=0.01,value=settings[name],step=0.5,
                                key='field_'+name,on_change=save_setting,args=(name,))
    st.markdown('<div class="notice"><strong>Distribuição por documento</strong><br>80% emissão inicial · 10% comentários · 20% atendimento · 10% aprovação.<br>Atividades auxiliares preservam 100% das HH originais.</div>',unsafe_allow_html=True)
    if st.button('Gerar pré-cronograma →',type='primary',disabled=not ready):
        ss.pop('result',None)
        try:
            with st.spinner('Preparando seu planejamento e conferindo as horas…'):
                ss.result=generate(ss.ld_file[1],ss.manual_file[1],config)
                ss.result_key=key
            go('Resultados');st.rerun()
        except ValueError as exc:st.error('Não foi possível gerar: '+str(exc))
        except Exception:
            logging.exception('Falha na geração do pré-cronograma')
            st.error('Não foi possível processar as planilhas. Confira o formato e a integridade dos arquivos.')

else:
    heading('03 · RESULTADOS','Pronto para o próximo passo.',
            'Consulte o resumo, revise as pendências e baixe o pré-cronograma para compartilhar com a equipe.')
    if 'result' not in ss:
        st.markdown('<div class="empty"><h3>Seu planejamento aparecerá aqui</h3><p>Envie os arquivos e configure o projeto para gerar o primeiro resultado.</p></div>',unsafe_allow_html=True)
        st.button('Ir para '+('Configuração' if ready else 'Arquivos'),type='primary',
                  on_click=go,args=('Configuração' if ready else 'Arquivos',))
    else:
        tables,files=ss.result
        original=sum((r['hh_original'] for r in tables['Auditoria_HH']),Decimal(0))
        planned=sum((r['hh_planejada'] for r in tables['Auditoria_HH']),Decimal(0))
        def br(value):return f'{value:,.2f}'.replace(',','X').replace('.',',').replace('X','.')
        for col,label,value in zip(st.columns(4),['Atividades','HH originais','HH planejadas','Pendências'],
                                   [len(tables['Atividades']),br(original),br(planned),len(tables['Pendencias'])]):
            col.metric(label,value)
        st.markdown('<div class="notice"><strong>Uma base para revisar em equipe.</strong><br>Este resultado é preliminar. Confira as pendências e as relações técnicas antes de aprovar o planejamento.</div>',unsafe_allow_html=True)
        st.download_button('↓ Baixar pré-cronograma Excel',files['pre_cronograma.xlsx'],'pre_cronograma.xlsx',
                           'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',type='primary')
        sections=[('Estrutura WBS','WBS',[('codigo','Código'),('nome','Nome'),('origem','Origem')]),
                  ('Atividades e etapas','Atividades',[('nome','Nome'),('tipo_linha','Tipo'),('codigo_wbs','WBS'),('hh','HH'),('duracao_dias','Duração (dias)')]),
                  ('Pendências para revisão','Pendencias',[('codigo','Categoria'),('origem','Origem'),('descricao','Descrição')]),
                  ('Auditoria de horas','Auditoria_HH',[('nome','Documento / auxiliar'),('funcao','Função'),('hh_original','HH originais da função'),('hh_planejada','HH planejadas'),('diferenca','Diferença do planejamento'),('hh_total_ld','Total do registro na LD'),('hh_total_lido','Total do registro lido'),('diferenca_total_ld','Diferença com a LD'),('conferencia_total_ld','Conferência LD')])]
        for title,name,columns in sections:
            with st.expander(title,expanded=False):
                rows=activity_hierarchy(tables) if name=='Atividades' else tables[name]
                if name=='Auditoria_HH':st.caption('Os totais do documento aparecem em cada função. Não some esses totais entre as linhas; o relatório de conferência traz uma linha por registro da LD.')
                if name=='Atividades':st.caption('Fase → disciplina → documento → etapas. O Excel inclui grupos recolhíveis.')
                table(rows,columns,name)
        with st.expander('Relatórios complementares'):
            if 'conferencia_ld.json' in files:
                st.download_button('↓ Conferência das horas com a LD',files['conferencia_ld.json'],'conferencia_ld.json','application/json')
            st.download_button('↓ Relatório de pendências',files['pendencias.json'],'pendencias.json','application/json')
            st.download_button('↓ Matriz preliminar',files['matriz_regras.json'],'matriz_regras.json','application/json')
