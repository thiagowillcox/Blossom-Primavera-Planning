# Revisão das ligações — 30/10/2026

## O que foi verificado

O manual BL0000-GE-MAN-0001 Rev.02 foi inspecionado nas três abas FEL. Foram
identificados 277 blocos de documentos (123 com texto em células), 317 evidências
de imagens e dez trechos textuais com exigências temporais explícitas. Esses
dez trechos foram separados em 26 regras versionadas em
`config/regras_manual.json`, com citação integral e endereço da célula. O motor
confere a citação e o hash do manual antes de aplicar a regra.

Isso é uma revisão textual e uma inspeção visual focalizada, não uma declaração
de que todos os fluxos gráficos foram integralmente interpretados. Permanecem
317 evidências catalogadas e quatro observações visuais preliminares. A matriz
agora tem 347 registros, sem confundir evidência com relação de cronograma.

## Premissas confirmadas pelo usuário

- Normalmente, informação consolidada/finalizada fica disponível após a
  Emissão Inicial. Essa é uma premissa editável de projeto, não texto atribuído
  ao manual: `marco_informacao_consolidada: 1`. Pode ser alterada para outra
  etapa ou `null` para deixar cada ligação em revisão.
- Não há datas de recebimento de documentos de fornecedor. Eles continuam
  como pendências externas, sem duração ou data presumida.
- Se o manual exige aprovação do cliente expressamente, essa exigência prevalece
  sobre a premissa de Emissão Inicial.

## Regras que podem gerar vínculos

A regra de Mecânica em `FEL 2!B541` diz que o cliente deve comentar e aprovar
os critérios antes da elaboração dos demais documentos da disciplina, e declara
aplicação em todas as fases. Ela gera FS entre aprovação final dos critérios
(etapa 4) e início dos demais documentos (etapa 1), somente na mesma fase e no
mesmo ramo Mecânica. O predecessor precisa existir com atividade planejada.

Outras exigências textuais obrigatórias podem usar o marco configurado pelo
usuário, mas apenas com correspondência exata e única dos documentos. Plurais,
acentos e pontuação são normalizados; correspondências por família/área apenas
geram candidatos para revisão. Uma data de disponibilidade não resolve, por si,
a dúvida sobre qual documento representa a entrada.

Nada é criado automaticamente quando faltam HH, há múltiplos candidatos, o
escopo da regra é ambíguo ou a aplicabilidade é condicional. Entradas de outras
fases são mostradas para revisão; nenhum vínculo entre fases é inferido.

## Correções no motor e na apresentação

- Fluxos gerais no começo de uma disciplina deixam de herdar o título do
  último documento da disciplina anterior. Exemplo: a figura em FEL 4 R227
  pertence ao fluxo de Processo Mineral, não ao HAZOP anterior.
- O retorno SIM/NÃO do SIPOC não é convertido em ciclo de atividades.
- Entradas obrigatórias, externas ou condicionais ainda não resolvidas deixam o início/fim pendente, mesmo que a duração seja calculável. Isso impede apresentar dia zero como liberação técnica; não cria vínculo FS nem presume que a condição se aplica.
- “Em paralelo” e “em conjunto” não viram FS automaticamente.
- Uma referência técnica não pode ser forçada a obrigatória apenas mudando
  o campo `classe` de um relacionamento aprovado. Os documentos e etapas
  também precisam corresponder à regra revisada.
- Excel e site mostram os nomes das predecessoras/sucessoras, a fonte, as
  candidatas identificadas na LD e a aplicação de cada regra.
- O hash da matriz versionada é incluído em Parametros; a aplicação das
  regras e a premissa de disponibilidade são editáveis em Configuração.

## Pontos que ainda precisam de validação

- Interpretar os demais fluxos gráficos e confirmar sua aplicabilidade ao projeto.
- Mapear documentos equivalentes por área, revisão e disciplina, inclusive
  documentos que venham de uma fase anterior.
- Resolver a referência genérica a “memória de cálculo finalizada” em FEL 3
  K946: o trecho não especifica de forma suficiente qual memória usar.
- O cabeçalho de FEL 4 R195 diz HAZOP, mas a orientação em R217 diz HAZID:
  não são tratados como sinônimos automaticamente.
- Definir capacidades e prazos do cliente para calcular durações. O programa
  continua sem nivelamento global de recursos e sem calendário/data-base.

Não é correto declarar o cronograma completo para envio definitivo ao Oracle
com essas pendências. O teste de conexão à API permanece separado e não envia
cronogramas.

## Matriz textual revisada

| Fase da evidência | Entrada | Documento | Classe | Célula |
| --- | --- | --- | --- | --- |
| FEL 2 | CRITÉRIOS DE PROJETO | DEMAIS DOCUMENTOS DA DISCIPLINA MECÂNICA | obrigatoria | B541 |
| FEL 2 | DIMENSIONAMENTO DE EQUIPAMENTOS DE PROCESSO | ARRANJO MECÂNICO / MODELO BIM | obrigatoria | K594 |
| FEL 2 | DIMENSIONAMENTO DE EQUIPAMENTOS MECÂNICOS | ARRANJO MECÂNICO / MODELO BIM | referencia_tecnica | K594 |
| FEL 3 | FLUXOGRAMA DE ENGENHARIA | LISTA DE EQUIPAMENTOS | obrigatoria | K946 |
| FEL 3 | MEMÓRIA DE CÁLCULO FINALIZADA | LISTA DE EQUIPAMENTOS | obrigatoria | K946 |
| FEL 3 | LISTA DE INSTRUMENTOS | LISTA DE ENTRADAS / SAÍDAS | obrigatoria | K3019 |
| FEL 3 | LISTA DE EQUIPAMENTOS MECÂNICOS | LISTA DE ENTRADAS / SAÍDAS | obrigatoria | K3019 |
| FEL 3 | ARQUITETURA DO SISTEMA DE AUTOMAÇÃO E CONTROLE | LISTA DE ENTRADAS / SAÍDAS | referencia_tecnica | K3019 |
| FEL 3 | CRITÉRIOS DE PROJETO DE AUTOMAÇÃO INDUSTRIAL | LISTA DE INSTRUMENTOS | obrigatoria | K3046 |
| FEL 3 | FLUXOGRAMAS DE ENGENHARIA | LISTA DE INSTRUMENTOS | referencia_tecnica | K3046 |
| FEL 3 | CRITÉRIOS DE PROJETO DE AUTOMAÇÃO INDUSTRIAL | MEMORIAL DESCRITIVO DO PROJETO | obrigatoria | K3235 |
| FEL 3 | CRITÉRIOS DE PROJETO DE AUTOMAÇÃO E INSTRUMENTAÇÃO | MEMORIAL DESCRITIVO DO PROJETO | obrigatoria | K3235 |
| FEL 3 | FLUXOGRAMAS DE PROCESSO PFD | MEMORIAL DESCRITIVO DO PROJETO | obrigatoria | K3235 |
| FEL 4 | ARRANJOS GERAIS MECÂNICOS | MEMÓRIA DE CÁLCULO | condicional | L2012 |
| FEL 4 | PLANO DE BASES DE ESTRUTURAS METÁLICAS | MEMÓRIA DE CÁLCULO | condicional | L2012 |
| FEL 4 | DFs DE EQUIPAMENTOS COM PLANOS DE CARGAS | MEMÓRIA DE CÁLCULO | informacao_externa | L2012 |
| FEL 4 | DIAGRAMAS UNIFILARES | DIAGRAMA DE INTERLIGAÇÃO | referencia_tecnica | K2817 |
| FEL 4 | P&IDs | DIAGRAMA DE INTERLIGAÇÃO | referencia_tecnica | K2817 |
| FEL 4 | LISTA DE INSTRUMENTOS | DIAGRAMA DE INTERLIGAÇÃO | obrigatoria | K2817 |
| FEL 4 | RELAÇÕES DE ENTRADAS E SAÍDAS | DIAGRAMA DE INTERLIGAÇÃO | obrigatoria | K2817 |
| FEL 4 | DOCUMENTAÇÃO DE FORNECEDOR DOS EQUIPAMENTOS E INSTRUMENTOS | DETALHES TÍPICOS DE MONTAGEM | informacao_externa | K2871 |
| FEL 4 | ARRANJO GERAL DE EQUIPAMENTOS — MECÂNICA | PLANTA DE LOCAÇÃO DE INSTRUMENTOS / EQUIPAMENTOS | obrigatoria | K2898 |
| FEL 4 | ARRANJO GERAL DE EQUIPAMENTOS — TUBULAÇÃO | PLANTA DE LOCAÇÃO DE INSTRUMENTOS / EQUIPAMENTOS | obrigatoria | K2898 |
| FEL 4 | ARRANJO GERAL DE EQUIPAMENTOS — ELÉTRICA | PLANTA DE LOCAÇÃO DE INSTRUMENTOS / EQUIPAMENTOS | obrigatoria | K2898 |
| FEL 4 | DOCUMENTOS DE FORNECEDOR | PLANTA DE LOCAÇÃO DE INSTRUMENTOS / EQUIPAMENTOS | informacao_externa | K2898 |
| FEL 4 | FLUXOGRAMA DE ENGENHARIA | PLANTA DE LOCAÇÃO DE INSTRUMENTOS / EQUIPAMENTOS | obrigatoria | K2898 |

## Validação desta rodada

103 testes automatizados passaram. Uma auditoria separada leu diretamente
os valores das quatro LDs e os Excel gerados, conferindo HH por função e etapa,
hierarquia, pares esperados de ligações, ausência de ciclos, IDs e rastreabilidade.
As quantidades de atividades, as HH e o mix comercial foram preservados.

Os resultados comerciais detalhados e as planilhas geradas não acompanham esta
atualização pública. As saídas de exemplo já presentes no repositório pertencem
a versões anteriores: gere novamente sua LD pelo site para obter a revisão atual.
As pendências podem aumentar porque agora as correspondências e entradas
ausentes ficam explícitas, sem que sejam inventadas horas ou atividades.
