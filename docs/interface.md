# Interface web — primeira entrega

Streamlit 1.50.0, identidade rosa em tema exclusivamente escuro, descrita em `visual_blossom.md`, envio somente da LD, manual fixo em `resources/manual_engenharia.xlsx`, configuração de jornada, capacidade por função e prazos independentes do cliente. Resultado com indicadores, quatro tabelas para revisão e downloads do Excel, pendências e matriz preliminar. O motor e as oito abas são preservados.

Validação em Linux: **21 testes passaram**, nenhum skip, incluindo AppTest da tela inicial/campos vazios, bloqueio de geração sem arquivos, adaptador com as planilhas reais e todos os testes anteriores. Página e health check HTTP 200. `pip check` sem inconsistências. A dependência packaging foi ajustada para 25.0 por compatibilidade com Streamlit.

O iniciador `Abrir_Blossom.bat` não foi executado em Windows neste ambiente. Ele usa ambiente em LocalAppData para evitar os caminhos longos/OneDrive observados na configuração local do usuário. A interface processa cada envio em pasta temporária e não altera os arquivos originais. Resultados não são compartilhados por cache global; downloads são mantidos na sessão e removidos da tela quando as entradas mudam.

Nenhuma URL pública foi publicada. Não há login, controle de acesso ou histórico persistente. Antes de hospedar para a equipe, é necessário definir essas condições. A análise integral das regras do manual continua pendente; a interface não a substitui.

O logotipo oficial pode ser incluído em `assets/logo.png`; a referência anexada na conversa foi usada para cores e composição, sem reconstruir a imagem original.

## Manual fixo

O visitante não envia nem escolhe um manual. A revisão 02 fornecida acompanha o aplicativo e sua integridade é conferida antes de cada geração. O hash continua registrado em Parametros e na matriz de regras. As regras preliminares e suas pendências não mudam. A interface solicita somente a LD. Isso também vale para o pacote Docker.
