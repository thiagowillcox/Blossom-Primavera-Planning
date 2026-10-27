import hashlib
import json
from decimal import Decimal
import logging
from pathlib import Path
import streamlit as st
from blossom.web import generate, ROLES

ROOT = Path(__file__).resolve().parent
st.set_page_config(page_title='Blossom | Planejamento', page_icon='🌸', layout='wide')
st.markdown('''<style>
.block-container {max-width:1200px;padding-top:2.2rem;padding-bottom:3rem}
[data-testid="stSidebar"] {background:#183c30}
[data-testid="stSidebar"] * {color:#fff}
.brand {font-size:2.7rem;font-weight:800;letter-spacing:-2px;line-height:1.2}
.eyebrow {color:#ae0056;letter-spacing:2.5px;font-size:.72rem;font-weight:700;margin-bottom:.7rem}
.hero {padding:1.5rem 0 2rem;border-bottom:1px solid #ddd9d2;margin-bottom:1.7rem}
.hero h1 {font-size:2.8rem;letter-spacing:-1.5px;max-width:750px;margin:0}
.hero p {color:#66766c;max-width:730px;font-size:1.05rem;line-height:1.7}
.step {color:#a70050;font-size:.8rem;letter-spacing:1px;font-weight:700}
[data-testid="stMetric"] {background:white;border:1px solid #e5dfd8;border-radius:12px;padding:18px}
.stButton>button {border-radius:8px;font-weight:600}
</style>''', unsafe_allow_html=True)
with st.sidebar:
    logo = ROOT/'assets/logo.png'
    if logo.exists(): st.image(str(logo), width=210)
    else:
        st.markdown('<div class="brand">Blossom<span style="color:#ff429b">.</span></div>', unsafe_allow_html=True)
    st.caption('ENGENHARIA • PLANEJAMENTO')
    st.divider()
    st.markdown('### Do escopo ao planejamento')
    st.write('01  Envie as planilhas')
    st.write('02  Configure o projeto')
    st.write('03  Gere e revise')
    st.divider()
    st.caption('Versão preliminar para revisão da equipe. A análise completa das precedências do manual está pendente.')
    st.caption('Nenhum dado é enviado ao Oracle Primavera Cloud. Sem histórico persistente de uploads nesta versão.')

st.markdown('''<div class="hero"><div class="eyebrow">BLOSSOM · PRÉ-CRONOGRAMA DE ENGENHARIA</div>
<h1>Planejamento que começa<br>com os seus documentos.</h1>
<p>Transforme a LD comercial em uma estrutura inicial de atividades, esforço por função e relacionamentos para revisão da equipe.</p></div>''', unsafe_allow_html=True)

left, right = st.columns([1.25, 1], gap='large')
with left:
    st.markdown('<div class="step">01 / DOCUMENTOS DO PROJETO</div>', unsafe_allow_html=True)
    st.subheader('Envie as planilhas')
    st.caption('Use o layout comercial Blossom. Os arquivos de entrada são preservados; macros não são executadas.')
    ld = st.file_uploader('Lista de Documentos comercial', type=['xlsm', 'xlsx'], key='ld')
    manual = st.file_uploader('Manual de Engenharia', type=['xlsx'], key='manual')
    st.info('O manual deve ser enviado nesta versão. As observações existentes só são reutilizadas quando a versão do arquivo coincide com a analisada.')
with right:
    st.markdown('<div class="step">02 / PREMISSAS DE PLANEJAMENTO</div>', unsafe_allow_html=True)
    st.subheader('Configure o projeto')
    project = st.text_input('Nome do projeto', placeholder='Ex.: Forno III')
    daily = st.number_input('Jornada (HH por profissional/dia)', min_value=0.1, max_value=24.0, value=8.0, step=0.5)
    st.caption('Deixe os campos abaixo vazios quando ainda não houver definição. Horas não serão convertidas em prazos por suposição.')
    a,b = st.columns(2)
    with a: comments = st.number_input('Comentários do cliente (dias)', min_value=0.0, value=None, step=1.0)
    with b: approval = st.number_input('Aprovação final (dias)', min_value=0.0, value=None, step=1.0)
    capacities = {}
    with st.expander('Capacidade disponível por função'):
        st.caption('Quantidade equivalente de profissionais por atividade. Esta estimativa não nivela recursos entre atividades simultâneas.')
        for role in ROLES:
            value = st.number_input(role, min_value=0.01, value=None, step=0.5, key='cap_'+role)
            if value is not None: capacities[role] = value

config = json.loads((ROOT/'config/parametros.json').read_text(encoding='utf-8'))
config.update(projeto=project.strip() or 'Projeto não identificado', jornada_hh_dia=daily,
              capacidade_profissionais=capacities, duracao_cliente_dias={'2':comments,'4':approval})
fingerprint = hashlib.sha256(json.dumps(config, sort_keys=True).encode())
for upload in (ld, manual):
    if upload is not None: fingerprint.update(upload.getvalue())
key = fingerprint.hexdigest()
if 'result_key' in st.session_state and st.session_state.result_key != key:
    st.session_state.pop('result', None)
    st.session_state.pop('result_key', None)

st.divider()
st.caption('Documentos: 80% emissão inicial · 10% comentários do cliente · 20% atendimento · 10% aprovação. Auxiliares: 100% das HH originais.')
if st.button('Gerar pré-cronograma →', type='primary', disabled=ld is None or manual is None, use_container_width=True):
    st.session_state.pop('result', None)
    try:
        with st.spinner('Lendo as planilhas e conferindo as horas…'):
            st.session_state.result = generate(ld.getvalue(), manual.getvalue(), config)
            st.session_state.result_key = key
    except ValueError as exc:
        st.error('Não foi possível gerar: '+str(exc))
    except Exception:
        logging.exception('Falha na geração do pré-cronograma')
        st.error('Não foi possível ler ou processar as planilhas. Confira o layout da LD, o formato Excel e se os arquivos estão íntegros. Nenhum resultado novo foi liberado.')

if 'result' in st.session_state:
    tables, files = st.session_state.result
    st.markdown('<div class="step">03 / RESULTADO PARA REVISÃO</div>', unsafe_allow_html=True)
    st.subheader('Seu pré-cronograma está disponível')
    st.warning('Resultado preliminar. Revise as pendências antes de usar no planejamento. Figuras do manual catalogadas não representam dependências aprovadas.')
    original = sum((r['hh_original'] for r in tables['Auditoria_HH']), Decimal(0))
    planned = sum((r['hh_planejada'] for r in tables['Auditoria_HH']), Decimal(0))
    cols = st.columns(4)
    for col, label, value in zip(cols, ['Atividades','HH originais','HH planejadas','Pendências'],
                                [len(tables['Atividades']),f'{original:,.2f}',f'{planned:,.2f}',len(tables['Pendencias'])]):
        col.metric(label, value)
    st.download_button('Baixar pré-cronograma Excel', files['pre_cronograma.xlsx'], 'pre_cronograma.xlsx',
                       'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', type='primary')
    tabs = st.tabs(['Estrutura WBS','Atividades','Pendências','Auditoria de horas'])
    for tab, name, columns in zip(tabs, ['WBS','Atividades','Pendencias','Auditoria_HH'],
        [['codigo','nome','origem'],['nome','etapa','hh','duracao_dias','origem'],
         ['codigo','origem','descricao'],['registro_id','funcao','hh_original','hh_planejada','diferenca']]):
        with tab:
            st.dataframe([{c:str(row.get(c)) if row.get(c) is not None else '' for c in columns}
                          for row in tables[name]], use_container_width=True, hide_index=True)
    c1,c2 = st.columns(2)
    with c1: st.download_button('Baixar relatório de pendências', files['pendencias.json'], 'pendencias.json','application/json')
    with c2: st.download_button('Baixar matriz preliminar', files['matriz_regras.json'], 'matriz_regras.json','application/json')
