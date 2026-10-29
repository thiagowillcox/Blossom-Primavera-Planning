"""Presentation helpers; no changes to engineering calculations."""
import base64
from pathlib import Path
from html import escape
import streamlit as st


def apply_theme():
    colors = {'bg':'#121014','side':'#19151b','card':'#241b23','text':'#f8edf3',
              'muted':'#bfaab7','border':'#49303e','input':'#201920','soft':'#321c2a','pink':'#ff348d'}
    variables = ';'.join('--'+k+':'+v for k,v in colors.items())
    css = '''
    .stApp,.stApp p,.stApp label,.stApp button,.stApp input,.stApp h1,.stApp h2,.stApp h3 {font-family:"Nunito Sans","Segoe UI",Arial,sans-serif!important}
    [data-testid="stAppDeployButton"] {display:none}
    .stApp {background:var(--bg);color:var(--text);color-scheme:SCHEME}
    [data-testid="stHeader"] {background:var(--bg)}
    .block-container {max-width:1140px;padding:2.8rem 2.7rem 4rem}
    h1,h2,h3,p,label,li {color:var(--text)}
    h1 {font-size:2.1rem!important;letter-spacing:-.8px;font-weight:750!important}
    h2 {font-size:1.45rem!important;letter-spacing:-.4px}
    h3 {font-size:1.05rem!important}
    [data-testid="stCaptionContainer"] {opacity:1!important}
    [data-testid="stCaptionContainer"] p {color:var(--muted)!important;opacity:1}
    [data-testid="stSidebar"] {background:var(--side);border-right:1px solid var(--border)}
    [data-testid="stSidebar"] .stImage {margin:1rem auto .6rem;max-width:210px}
    [data-testid="stSidebar"] hr {border-color:var(--border)}
    [data-testid="stSidebar"] [role="radiogroup"] {gap:8px}
    [data-testid="stSidebar"] [role="radiogroup"] label {
      padding:12px 14px;border-radius:12px;border:1px solid transparent;transition:.18s ease}
    [data-testid="stSidebar"] [role="radiogroup"] label:hover {background:var(--soft)}
    [data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) {
      background:var(--soft);border-color:var(--border)}
    [data-testid="stVerticalBlockBorderWrapper"]>div {border-color:var(--border)!important;border-radius:18px!important}
    .st-key-card_ld,.st-key-card_manual,.st-key-project_card,.st-key-client_card {background:var(--card);border-radius:18px;border-color:var(--border)!important}
    [data-testid="stFileUploaderDropzone"] {background:var(--input);border:1px dashed var(--border);border-radius:14px}
    [data-testid="stFileUploaderDropzone"] *,[data-testid="stFileUploaderFile"] * {color:var(--text)}
    [data-baseweb="input"],[data-baseweb="base-input"],[data-baseweb="select"]>div {
      background:var(--input)!important;color:var(--text)!important;border-color:var(--border)!important;border-radius:10px}
    input {color:var(--text)!important;-webkit-text-fill-color:var(--text)!important}
    input::placeholder {-webkit-text-fill-color:var(--muted)!important}
    [data-testid="stNumberInputContainer"] {background:var(--input);border-color:var(--border)}
    [data-testid="stNumberInputContainer"] button {color:var(--text);background:var(--card)}
    button[kind="primary"] {background:#e90071!important;color:white!important;border:0!important}
    button[kind="primary"] p {color:white!important}
    button:disabled {opacity:.45!important;cursor:not-allowed!important}
    button[kind="secondary"] {background:var(--input);border:1px solid var(--border);color:var(--text)}
    .stButton button,.stDownloadButton button {border-radius:11px;min-height:44px;transition:transform .16s ease,box-shadow .16s ease}
    .stButton button:hover:not(:disabled),.stDownloadButton button:hover:not(:disabled) {
      transform:translateY(-1px);box-shadow:0 5px 14px #e900711c;border-color:#e90071}
    button:focus-visible,a:focus-visible {outline:3px solid var(--pink);outline-offset:3px}
    [data-testid="stMetric"] {padding:20px;background:var(--card);border:1px solid var(--border);border-radius:16px}
    [data-testid="stMetricValue"] {font-size:1.8rem;color:var(--text)}
    [data-testid="stExpander"] {background:var(--input);border:1px solid var(--border);border-radius:14px}
    [data-testid="stExpander"] summary {color:var(--text);padding:13px}
    .eyebrow {font-size:.72rem;color:var(--pink);font-weight:750;letter-spacing:1.7px;margin-bottom:10px}
    .intro {color:var(--muted);font-size:1rem;line-height:1.7;max-width:760px;margin-bottom:26px}
    .notice {background:var(--card);border:1px solid var(--border);border-radius:16px;padding:20px 24px;
      color:var(--text);line-height:1.65;margin:18px 0}
    .notice strong {color:var(--pink)}
    .side-title {font-weight:750;color:var(--text);font-size:1.2rem;text-align:center}
    .side-sub {color:var(--muted);font-size:.7rem;letter-spacing:1.6px;text-align:center;margin-bottom:28px}
    .empty {padding:50px 28px;text-align:center;background:var(--card);border:1px solid var(--border);border-radius:18px;margin-bottom:20px}
    .empty p {color:var(--muted)}
    .table-wrap {overflow:auto;max-height:470px;border:1px solid var(--border);border-radius:12px}
    .blossom-table {border-collapse:collapse;width:100%;font-size:.86rem;color:var(--text)}
    .blossom-table th {background:var(--card);position:sticky;top:0;text-align:left;padding:13px 16px;white-space:nowrap}
    .blossom-table td {padding:12px 16px;border-top:1px solid var(--border);vertical-align:top;white-space:pre-wrap;min-width:100px}
    .blossom-table tr:hover td {background:var(--soft)}
    .blossom-table .summary td {background:var(--card);font-weight:650}
    @media(prefers-reduced-motion:reduce) {* {transition:none!important;animation:none!important}}
    @media(max-width:700px) {.block-container {padding:1.5rem 1rem 3rem} h1 {font-size:1.7rem!important}}
    '''.replace('SCHEME', 'dark')
    font = base64.b64encode((Path(__file__).resolve().parents[1]/'assets/NunitoSans.ttf').read_bytes()).decode()
    css = '@font-face{font-family:"Nunito Sans";src:url(data:font/ttf;base64,'+font+');font-weight:200 1000;font-style:normal;font-display:swap}'+css
    st.markdown('<style>:root{'+variables+'}'+css+'</style>', unsafe_allow_html=True)


def heading(step, title, description):
    st.markdown('<div class="eyebrow">BLOSSOM PLANNING / '+escape(step)+'</div>', unsafe_allow_html=True)
    st.title(title)
    st.markdown('<div class="intro">'+escape(description)+'</div>', unsafe_allow_html=True)


def table(rows, columns, key):
    if not rows:
        st.caption('Nenhum registro para exibir.')
        return
    size=100
    pages=(len(rows)+size-1)//size
    page=st.selectbox('Página',range(1,pages+1),key='table_'+key,
                      format_func=lambda p:f'{p} de {pages}') if pages>1 else 1
    visible=rows[(page-1)*size:page*size]
    html='<div class="table-wrap"><table class="blossom-table"><thead><tr>'
    html+=''.join('<th scope="col">'+escape(label)+'</th>' for field,label in columns)
    html+='</tr></thead><tbody>'
    for row in visible:
        html+='<tr class="summary">' if row.get('tipo_linha') in ('fase','agrupador','documento') else '<tr>'
        for field,label in columns:
            value=row.get(field)
            text='' if value is None else str(value)
            indent=min(row.get('nivel',0),7)*18 if field=='nome' else 0
            html+=f'<td style="padding-left:{16+indent}px">'+escape(text)+'</td>'
        html+='</tr>'
    st.markdown(html+'</tbody></table></div>',unsafe_allow_html=True)
    st.caption(f'{len(rows)} registros · exibindo {(page-1)*size+1}–{min(page*size,len(rows))}')
