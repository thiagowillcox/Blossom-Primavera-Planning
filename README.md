# Blossom Primavera Planning

Motor Python de pré-cronogramas de engenharia a partir da LD comercial e do Manual de Engenharia. Primeira versão independente de Oracle Primavera Cloud e BMS; não faz chamadas de rede nem escreve na API Oracle.

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
- `input/Manual.xlsx`: cópia de `Mnaual de Engenharia Blossom.xlsx` (revisão 02).

Para outros caminhos:

```bash
.venv/bin/python -m blossom --ld '/caminho/LD.xlsm' --manual '/caminho/manual.xlsx' --config config/parametros.json --output output
```

Os arquivos comerciais, o ambiente virtual e as saídas são locais e ignorados pelo Git. Copie os arquivos comerciais para os caminhos acima em outra máquina. A leitura não executa macros; `openpyxl` não recalcula Excel. O motor reproduz somente a conversão A4/A3/A2/A1/A0 da fórmula conhecida, confronta A1 e totais com os valores em cache, e sinaliza inconsistências. Fórmulas não reconhecidas dependem de cache e são sinalizadas. Registros sem HH não recebem atividades com esforço inventado.

## Parâmetros editáveis

Edite `config/parametros.json` sem alterar Python:

- `jornada_hh_dia`: 8 por padrão.
- `capacidade_profissionais`: número de profissionais equivalentes disponíveis por função, usando os rótulos exatos da LD: `Gerente`, `Especialista`, `ESênior`, `EPleno`, `EJúnior`, `PSênior`, `PPleno`, `PJúnior`, `Desenh.`. O padrão vazio deixa durações pendentes. Por exemplo, `{"EPleno": 2, "PSênior": 1}` atribui duas pessoas equivalentes à primeira função e uma à segunda; preencher todas as funções com HH para calcular uma atividade.
- `duracao_cliente_dias`: prazos independentes para etapas `2` e `4`. O padrão `null` é pendente, não zero.
- `encadeamento`: pares de etapas com relação FS e defasagem zero, padrão `[[1,2],[2,3],[3,4]]`. Ciclos são rejeitados.
- `relacionamentos_aprovados`: vínculos entre IDs de atividades, revisados pela equipe. Exemplo de estrutura: `{"predecessora":"ATV-...","sucessora":"ATV-...","regra_id":"OBS-...","classe":"obrigatoria","aprovada":true,"tipo":"FS","defasagem_dias":0}`. Somente classe obrigatória aprovada cria vínculo. Demais classes permanecem informativas.
- `identidades`: associação de identidade semântica a ID persistente, para preservar um identificador após correção de nome/EAP. A chave exata está em `WBS.identidade_semantica` e em `resultado.json`.

A distribuição obrigatória de documentos é 80% / 10% / 20% / 10% por função (120% das HH originais). Atividades auxiliares têm uma atividade única e 100% das HH. As HH de acompanhamento do cliente não determinam seus prazos. As colunas de ajuste de mix são preservadas e não substituem as HH originais de H:P multiplicadas por G para formatos A, ou diretas para unidade HH.

A duração calculável é `max(HH_funcao / (jornada × capacidade_funcao))`: funções paralelas por atividade. É uma estimativa, sem nivelamento entre atividades concorrentes. Início/fim são dias relativos ao início do projeto, sem calendário nem datas civis. Uma predecessora sem fim calculável mantém o início da sucessora pendente. Atividades sem dependências conhecidas começam no dia relativo zero, o que não comprova independência técnica.

## Saídas e rastreabilidade

`output/pre_cronograma.xlsx` contém exatamente as oito abas:

1. `WBS`: fases, disciplinas e todos os registros, inclusive sem HH, com fórmulas originais e cache em JSON inerte.
2. `Atividades`: etapas, esforço e durações/dias relativos quando calculáveis.
3. `Atribuicoes_Funcoes`: HH por atividade e função.
4. `Relacionamentos`: encadeamento documental e vínculos obrigatórios aprovados.
5. `Matriz_Regras`: inventário das figuras FEL e observações visuais preliminares.
6. `Parametros`: configuração e hashes dos insumos.
7. `Pendencias`: HH ausentes, durações, regras em imagem e outras decisões necessárias.
8. `Auditoria_HH`: original, planejado, esperado e diferença por registro/função.

Também são gerados `resultado.json`, `matriz_regras.json`, `pendencias.json` e a pasta `manual_figuras/`. O XLSX é normalizado para reprodutibilidade binária. Os JSONs têm ordenação determinística e decimais representados sem perda em strings. IDs usam a identidade semântica (WBS/código/EAP/nome), sem depender apenas da linha. Duplicidades são rejeitadas; alterações de nome exigem a associação explícita em `identidades` para conservar o ID.

## Manual e limites desta versão

Leia [a inspeção dos arquivos](docs/inspecao.md). Os fluxogramas SIPOC e as orientações são majoritariamente figuras rasterizadas. O motor extrai e cataloga as figuras com hash e posição; isso não equivale a interpretar automaticamente suas setas.

`config/observacoes_manual.json` contém quatro observações extraídas visualmente de dois fluxos da Engenharia Detalhada, separando informação externa, referência técnica e condição. Essas observações só são aceitas para o hash exato do manual inspecionado. Nenhuma foi aprovada como dependência temporal obrigatória. As demais figuras ficam explicitamente `a_validar`. Não há tradução automática de fornecedor/entrada SIPOC para relação FS.

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
- `oracle/`: namespace reservado, sem implementação de integração.

Os testes cobrem distribuição por função/etapa, auxiliares, paralelismo, prazos do cliente, IDs, vínculos inválidos/cíclicos, registros vazios, parâmetros inválidos e reprodução dos resultados dos arquivos reais. O teste de integração fica explicitamente `skipped` se os arquivos comerciais não estiverem disponíveis; uma execução sem esse teste não comprova validação da LD real.
