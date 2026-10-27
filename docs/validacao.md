# Validação da versão corrigida 0.2.0

Execução local em Python 3.12, openpyxl 3.1.5 e pytest 8.3.5. Arquivos de entrada originais preservados.

- `python -m pytest -q`: **18 passed**, nenhum skipped nesta execução.
- `python -m blossom`: execução bem-sucedida nos dois arquivos enviados.
- `pip check`: sem dependências quebradas.
- Reprodutibilidade: duas execuções independentes produziram Excel e três JSONs idênticos byte a byte.
- Excel reaberto com as oito abas esperadas. WBS conferida com 57 linhas: cabeçalho + 56 nós, sem documentos/auxiliares.
- Todos os 652 registros preservam rastreabilidade em `Auditoria_HH` ou `Pendencias`, além do JSON completo.
- Teste rejeita troca de horas entre etapas, mesmo mantendo o total do documento.
- Teste rejeita regra inexistente em relacionamento obrigatório.

## Resultado real

| Medida | Quantidade |
|---|---:|
| Registros originais nomeados | 652 |
| Nós hierárquicos | 56 |
| Documentos com HH planejadas | 213 |
| Auxiliares com HH planejadas | 100 |
| Atividades geradas | 952 |
| Atribuições por função | 3888 |
| Relacionamentos FS entre etapas | 639 |
| Linhas de auditoria por registro/função | 1158 |
| HH originais calculáveis | 13442,25 |
| HH planejadas | 15199,65 |
| Diferenças de auditoria | 0 |

O total original coincide com o cache de R5 da LD, dentro de tolerância 0,000001 HH para resíduos numéricos do Excel. As somas por função e as etapas são calculadas com Decimal. Documentos totalizam 8787 HH originais e auxiliares 4655,25 HH; somente os documentos recebem o acréscimo de 1757,4 HH.

## Pendências e limites

1627 linhas de pendências, com categorias distintas; uma pendência não é necessariamente um erro de execução:

- 952 durações pendentes: nenhuma capacidade ou prazo foi presumido.
- 338 registros sem HH positivas.
- 317 evidências de figuras para revisão (figuras repetidas no mesmo contexto são consolidadas).
- 6 reemissões/atualizações para validar o ciclo.
- 4 funções com fórmulas, calculadas a partir do cache Excel.
- 4 observações visuais preliminares sem mapeamento aprovado.
- 3 registros de unidade/fórmula A1 não padrão, incluindo verbas VB.
- 1 registro bloqueado por unidade VB com HH sem multiplicador/total utilizável (LD!790).
- 1 confirmação de identificação como Forno III.
- 1 aviso de ausência de nivelamento global de recursos/calendário.

A matriz contém 321 linhas: 317 evidências catalogadas e quatro observações visuais. Não são 321 dependências interpretadas/aprovadas. A interpretação integral das figuras não foi concluída; esta versão evita criar relações obrigatórias sem fundamento.

O resultado é um pré-cronograma estrutural com esforço auditável, não um cronograma integrado aprovado para emissão. As durações serão calculadas quando os parâmetros forem preenchidos. É necessário completar/revisar as relações técnicas e resolver as pendências com a equipe.

Código e saídas de referência versionados na branch `codex/planejamento-fase1`. As duas planilhas comerciais de entrada não são versionadas. A versão anterior foi enviada ao GitHub; esta correção deve ser consultada no commit correspondente da mesma branch. Os campos `install_script` e `start_skill` foram salvos no rascunho; publicação e restauração em nova tarefa não foram realizadas nem validadas.

## Correção de escopo

A versão anterior misturava os 652 registros comerciais com a WBS. A versão 0.2.0 mantém somente os 56 nós hierárquicos nessa aba. Os registros não foram excluídos do processamento: os 313 com esforço utilizável continuam gerando atividades; os 339 restantes permanecem sem HH inventadas e rastreáveis nas pendências.

As 317 figuras catalogadas são evidências, não regras interpretadas. Não recebem predecessora/sucessora inferidas. As quatro observações continuam preliminares. A interpretação completa do manual continua incompleta e não se declara a primeira fase encerrada.
