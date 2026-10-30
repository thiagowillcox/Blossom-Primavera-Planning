# Blossom Primavera Planning

Para localizar um projeto Oracle e revisar um Excel, veja
[Consulta de projetos e prévia local](docs/consulta_primavera.md). Para criar uma
estrutura em um projeto de teste vazio, veja
[Envio de rascunho estrutural](docs/envio_rascunho_primavera.md), sem HH e prazos.

Versão preliminar de um motor Python de pré-cronogramas de engenharia a partir da LD comercial e do Manual de Engenharia. O motor de planejamento é independente de Oracle Primavera Cloud e BMS e não escreve na API Oracle. Há um teste local de autenticação e conexão, separado do gerador: [Testar Primavera](docs/teste_primavera.md).

Para hospedar em servidor próprio, fora do Streamlit Community Cloud, consulte
[Hospedagem própria](docs/hospedagem_propria.md). Inclui Docker, HTTPS e uma
primeira proteção por usuário/senha, com os limites descritos no guia.

No site, códigos WBS repetidos agora abrem uma etapa de decisão em **Configuração**:
defina códigos exclusivos, confirme e gere o resultado. As escolhas ficam
registradas no Excel sem modificar a LD. Veja [Decisões do usuário](docs/decisoes_usuario.md).

## Executar

Python 3.12 (validado), com `openpyxl` e `pytest`:

```bash
python -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m blossom
.venv/bin/python -m pytest -q
```

Execute na raiz do repositório. Entradas locais, preservadas sem modificação:

- `input/LD.xlsm`: cópia de `BL1120-0011_R03 - LD (2).xlsm`.
- `resources/manual_engenharia.xlsx`: manual fixo (revisão 02) já incluído na distribuição.

Para outros caminhos:

```bash
.venv/bin/python -m blossom --ld '/caminho/LD.xlsm' --config config/parametros.json --output output
```

As LDs comerciais, o ambiente virtual e as novas saídas são locais e ignorados pelo Git. Em outra máquina, forneça apenas a LD; o manual fixo acompanha o código. A leitura não executa macros; `openpyxl` não recalcula Excel. O motor reproduz somente a conversão A4/A3/A2/A1/A0 da fórmula conhecida, confronta A1 e totais com os valores em cache, e sinaliza inconsistências. Fórmulas não reconhecidas dependem de cache e são sinalizadas. Registros sem HH não recebem atividades com esforço inventado.

## Parâmetros editáveis

Edite `config/parametros.json` sem alterar Python:

- `jornada_hh_dia`: 8 por padrão.
- `capacidade_profissionais`: número de profissionais equivalentes disponíveis por função, usando os rótulos exatos da LD: `Gerente`, `Especialista`, `ESênior`, `EPleno`, `EJúnior`, `PSênior`, `PPleno`, `PJúnior`, `Desenh.`. O padrão vazio deixa durações pendentes. Por exemplo, `{"EPleno": 2, "PSênior": 1}` atribui duas pessoas equivalentes à primeira função e uma à segunda; preencher todas as funções com HH para calcular uma atividade.
- `duracao_cliente_dias`: prazos independentes para etapas `2` e `4`. O padrão `null` é pendente, não zero.
- `encadeamento`: pares de etapas com relação FS e defasagem zero, padrão `[[1,2],[2,3],[3,4]]`. Ciclos são rejeitados.
- `relacionamentos_aprovados`: vínculos entre IDs de atividades, revisados pela equipe. Exemplo de estrutura: `{"predecessora":"ATV-...","sucessora":"ATV-...","regra_id":"OBS-...","classe":"obrigatoria","aprovada":true,"tipo":"FS","defasagem_dias":0}`. Somente classe obrigatória aprovada cria vínculo, e `regra_id` deve existir na matriz carregada do manual; referências inventadas são rejeitadas. Demais classes permanecem informativas.
- `identidades`: associação de identidade semântica a ID persistente, para preservar um identificador após correção de nome/EAP. A chave exata está em `WBS.identidade_semantica` e em `resultado.json`.

A distribuição obrigatória de documentos é 80% / 10% / 20% / 10% por função (120% das HH originais). Atividades auxiliares têm uma atividade única e 100% das HH. As HH de acompanhamento do cliente não determinam seus prazos. As colunas de ajuste de mix são preservadas e não substituem as HH originais de H:P multiplicadas por G para formatos A, ou diretas para unidade HH.

A duração calculável é `max(HH_funcao / (jornada × capacidade_funcao))`: funções paralelas por atividade. É uma estimativa, sem nivelamento entre atividades concorrentes. Início/fim são dias relativos ao início do projeto, sem calendário nem datas civis. Uma predecessora sem fim calculável mantém o início da sucessora pendente. Atividades sem dependências conhecidas começam no dia relativo zero, o que não comprova independência técnica.

## Saídas e rastreabilidade

`output/pre_cronograma.xlsx` contém exatamente as oito abas:

1. `WBS`: somente fases e disciplinas extraídas da hierarquia da LD. No arquivo recebido são 56 nós, com cabeçalho na linha 1 e último nó na linha 57. Documentos e auxiliares não são acrescentados como níveis WBS.
2. `Atividades`: etapas, esforço e durações/dias relativos quando calculáveis.
3. `Atribuicoes_Funcoes`: HH por atividade e função.
4. `Relacionamentos`: encadeamento documental e vínculos obrigatórios aprovados.
5. `Matriz_Regras`: 26 regras textuais revisadas, quatro observações visuais preliminares e 317 evidências de figuras; mostra aplicação e candidatos por LD.
6. `Parametros`: configuração e hashes dos insumos.
7. `Pendencias`: HH ausentes, durações, evidências em imagem e outras decisões necessárias. Pendências dos registros da LD carregam seu ID, dados originais e cache, inclusive quando não há HH calculáveis.
8. `Auditoria_HH`: original, planejado, esperado e diferença por registro/função, com código, descrição, WBS, quantidade, unidade, A1 e dados originais/cache para rastreabilidade.

Também são gerados `resultado.json`, `matriz_regras.json`, `pendencias.json` e a pasta `manual_figuras/`. O XLSX é normalizado para reprodutibilidade binária. Os JSONs têm ordenação determinística e decimais representados sem perda em strings. A tabela `registros` de `resultado.json` preserva todos os 652 registros nomeados da LD. IDs usam a identidade semântica (WBS/código/EAP/nome), sem depender apenas da linha. Duplicidades são rejeitadas; alterações de nome exigem a associação explícita em `identidades` para conservar o ID.

## Manual e limites desta versão

Leia [a inspeção dos arquivos](docs/inspecao.md). Os fluxogramas SIPOC e as orientações são majoritariamente figuras rasterizadas. O motor extrai e cataloga as figuras com hash e posição; isso não equivale a interpretar automaticamente suas setas.

`config/regras_manual.json` contém 26 regras derivadas de trechos textuais verificáveis, separando obrigação, referência, condição e informação externa. Veja [a revisão das ligações](docs/revisao_relacionamentos.md). A premissa editável `marco_informacao_consolidada` começa em 1 (Emissão Inicial), conforme definição do usuário. Exigências explícitas de aprovação prevalecem.

`config/observacoes_manual.json` contém quatro observações extraídas visualmente de dois fluxos da Engenharia Detalhada, separando informação externa, referência técnica e condição. O campo `natureza` separa `observacao_preliminar` de `evidencia_nao_interpretada`; nas evidências os campos de predecessora/sucessora ficam vazios. Essas observações só são aceitas para o hash exato do manual inspecionado. Nenhuma foi aprovada como dependência temporal obrigatória. As demais figuras ficam explicitamente `a_validar`. Não há tradução automática de fornecedor/entrada SIPOC para relação FS.

**A primeira fase ainda não está integralmente concluída:** falta a interpretação completa das matrizes do manual e seu mapeamento validado à LD. Os testes de software não substituem essa análise técnica. Veja [a conferência do escopo](docs/escopo.md).

A equipe deve revisar as figuras, completar a matriz, mapear documentos do manual aos IDs da LD e aprovar relações antes de considerar o pré-cronograma tecnicamente integrado. Reemissões/atualizações também são sinalizadas para confirmar aplicação das quatro etapas. A identificação da LD como Forno III ainda precisa ser confirmada pelo responsável.

## Arquitetura

- `ld.py`: leitura e normalização da LD.
- `manual.py`: extração de imagens/evidências e matriz preliminar.
- `wbs.py`: estrutura hierárquica.
- `hours.py`: distribuição e auditoria de HH.
- `duration.py`: estimativas por capacidade e prazos externos.
- `relationships.py` e `schedule.py`: vínculos aprovados e estimativa relativa.
- `validation.py`: parâmetros, integridade, IDs e ciclos.
- `export.py`: Excel/JSON determinísticos.
- `oracle/`: teste local de autenticação e conexão, sem envio de cronogramas.

Os testes cobrem distribuição por função/etapa, auxiliares, paralelismo, prazos do cliente, IDs, vínculos inválidos/cíclicos, registros vazios, parâmetros inválidos e reprodução dos resultados dos arquivos reais. O teste de integração fica explicitamente `skipped` se os arquivos comerciais não estiverem disponíveis; uma execução sem esse teste não comprova validação da LD real.

## Atualizar uma cópia baixada no Windows

Feche o Excel antes de gerar novamente. Em uma nova extração do ZIP da branch, coloque a LD em `input/LD.xlsm`; o manual fixo já acompanha o projeto. Na pasta que contém `requirements.txt`, execute no PowerShell:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m blossom
```

Os arquivos de exemplo em `output` podem corresponder a versões anteriores. Gere novamente sua LD para obter a versão atual. As LDs comerciais de entrada não estão versionadas; o manual fixo está em `resources`. Não extraia uma nova entrega por cima de alterações locais sem preservá-las.

## Interface web Blossom

A interface em `app.py` permite enviar somente a LD, usar automaticamente o manual fixo, preencher jornada/capacidades/prazos, gerar e baixar o Excel e consultar WBS, atividades, pendências e auditoria no navegador. Campos vazios continuam pendentes. A interface não possui login, histórico persistente ou envio ao Oracle. A integração de rascunho estrutural usa um iniciador local separado.

### Windows: abrir sem digitar comandos

Com Python 3.12 instalado, abra a pasta que contém `app.py` e dê dois cliques em **`Abrir_Blossom.bat`**. Na primeira execução o arquivo instala as dependências pela internet no ambiente curto `%LOCALAPPDATA%\BlossomPlanning\venv`. Depois inicia o site local e solicita ao navegador que o abra. Mantenha a janela do servidor aberta durante o uso. Se o navegador não abrir automaticamente, use `http://localhost:8501` no seu computador. Fechar a janela encerra o servidor.

O iniciador Windows foi preparado, mas não foi executado em Windows neste ambiente Linux.

### Iniciar manualmente

```powershell
& "$env:LOCALAPPDATA\BlossomPlanning\venv\Scripts\python.exe" -m pip install -r requirements.txt
& "$env:LOCALAPPDATA\BlossomPlanning\venv\Scripts\python.exe" -m streamlit run app.py
```

Abra o endereço indicado no terminal. A interface aceita os nomes originais dos arquivos; não é necessário renomear ou copiar planilhas para `input`. O processamento usa diretórios temporários curtos e isolados por geração. Os downloads ficam em memória na sessão; não há histórico durável. Ao alterar entradas ou parâmetros, gere novamente para obter novos downloads.

O Blossom Planning usa somente tema escuro, com fundo quase preto, cartões em rosa profundo, botões pink e logo de letras claras em `assets/logo-dark.png`. Não há alternância de tema na interface.

Esta é uma aplicação local. Para disponibilizá-la por uma URL à equipe, ainda é necessário escolher hospedagem e definir autenticação, acesso aos documentos e limites de processamento. Não exponha o servidor local como se já fosse um serviço publicado.

## Hierarquia visual do pré-cronograma

A aba `Atividades` apresenta **fase → disciplina → documento → quatro etapas**. As atividades auxiliares aparecem diretamente sob sua disciplina, com suas HH originais. Os títulos de fase, disciplina e documento são linhas de apresentação: não são novas atividades, não recebem esforço e não entram na matriz de relacionamentos. A coluna `nome` recebe indentação real no Excel; os controles de agrupamento permitem recolher/expandir os níveis. `nivel`, `pai_id`, `codigo_wbs` e `caminho_wbs` tornam a estrutura explícita.

A aba WBS permanece separada, com apenas os nós hierárquicos originais (56 na LD recebida). O JSON mantém as atividades executáveis em `tabelas.Atividades` e a visão completa em `linhas_cronograma`. Os indicadores do site e a auditoria contam somente atividades com HH, sem duplicar esforços nos agrupadores.

No site, a aba Atividades usa a mesma ordem hierárquica, com recuo visual e classificação da linha. O agrupamento recolhível está no Excel. Não ordene isoladamente as linhas do cronograma exportado: isso separa filhos dos pais; a tabela exportada não aplica filtro automático para preservar a sequência.

## Novo visual e navegação do Blossom Planning

- **Arquivos:** envie somente a LD pelo cartão rosado; o manual de referência já está configurado.
- **Configuração:** informe projeto, jornada, capacidade e prazos; campos sem definição continuam vazios.
- **Resultados:** veja primeiro o resumo, baixe o Excel e abra somente as tabelas desejadas. Tabelas grandes são paginadas com 100 linhas por página, preservando a sequência hierárquica.
- O site abre diretamente no tema escuro; não há seletor de tema.
- Arquivos e premissas permanecem durante a navegação entre seções. Alterar entradas ou parâmetros invalida o resultado anterior; navegar entre as seções não invalida a geração.
- Fonte Nunito Sans incluída localmente, com licença em `assets/OFL.txt`. Não há busca de fontes durante o uso.
- Os arquivos permanecem somente durante a sessão: não é um histórico persistente nem há contas/login nesta entrega.

Para atualizar, feche o servidor anterior, extraia a nova versão em pasta curta fora do OneDrive e abra `Abrir_Blossom.bat` novamente. Recarregar só o navegador não substitui arquivos antigos do projeto.

## Conferência das horas pela LD

A fonte de cálculo é a LD comercial enviada. O Excel do Wardi é apenas referência visual e não é usado para impor horas, prazos ou vínculos. Os modos de reprocessamento, perfil de compatibilidade e bloqueio por hash foram removidos. Hashes continuam registrados somente para rastrear os arquivos lidos.

A aba `Auditoria_HH` mostra, para cada registro planejado, o total original R da LD, o total lido, a diferença e o status de conferência, além das horas por função. Totais de registro se repetem nas linhas de função: não devem ser somados entre linhas. O download **Conferência das horas com a LD**, em Relatórios complementares, contém uma linha por registro, incluindo registros sem HH planejadas. A mesma conferência está em `resultado.json` e em `output/conferencia_ld.json`.

A duração usa a capacidade das funções em paralelo. Prazos do cliente permanecem vazios até serem informados; não há prazo fixo herdado de outro projeto. O nome do projeto também começa vazio na interface.

Leia [a revisão do diagnóstico](docs/diagnostico_wardi.md). A extração completa das precedências do manual continua pendente. O novo relatório confere esforço; não comprova a validação técnica de todos os relacionamentos.
