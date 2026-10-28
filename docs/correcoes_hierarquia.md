# Correções da hierarquia de atividades

## O que mudou

1. A lista plana da aba Atividades foi substituída por uma visão hierárquica em profundidade: fase, disciplina, documento e etapas. A ordem das fases, disciplinas e documentos vem da LD original.
2. O documento aparece como título; suas quatro etapas ficam abaixo dele, em ordem, com seus nomes próprios. O nome completo e os IDs das atividades permanecem no modelo de cálculo/JSON.
3. Auxiliares aparecem sob a disciplina, com a mesma atividade única e sem acréscimo automático de HH.
4. A coluna nome recebe indentação de célula real. Foram adicionados grupos recolhíveis no Excel, com títulos acima dos filhos, cores e negrito nos agrupadores.
5. Foram incluídos nível, ID do pai, código e caminho WBS para conferir a estrutura sem depender apenas da aparência.
6. A visão do site acompanha a hierarquia. O contador de atividades continua contando somente atividades executáveis.
7. Linhas de apresentação não têm HH, durações ou relações próprias: não duplicam esforço nem criam regras de precedência.
8. A WBS continua somente com seus nós originais; documentos foram agrupados na apresentação do cronograma, sem serem acrescentados à aba WBS.
9. O JSON mantém a tabela técnica de atividades e acrescenta linhas_cronograma para representar a apresentação.
10. Testes específicos verificam parentesco, ordem, indentação, grupos Excel, preservação dos IDs/HH e ausência de pai inexistente.

## Conferência e limites

Validação com a LD original enviada e o manual original. O arquivo `BL1120-0011_R03 - Orcamento_JSF (4).xlsm` foi desconsiderado por solicitação do usuário; nenhuma mudança específica desse formato foi mantida e seu conteúdo não foi adicionado ao repositório.

O cronograma pronto mencionado ainda não foi recebido. Portanto, não houve comparação com datas, calendários ou predecessoras de um cronograma de referência. A interpretação completa das precedências do manual permanece pendente, assim como capacidades/prazos ainda não informados. Não se declara que todos os possíveis problemas do motor foram eliminados.

## Evidências desta execução

- **24 testes passaram**, nenhum skip.
- Excel reaberto: 1.222 linhas em Atividades (cabeçalho, 56 nós WBS, 213 títulos de documentos e 952 atividades executáveis), com níveis de agrupamento 0 a 3.
- WBS com 57 linhas, incluindo cabeçalho.
- Comparação direta dos dados JSON com o commit anterior: todas as tabelas técnicas e todos os registros originais permaneceram idênticos. Apenas a representação adicional do cronograma e sua formatação foram acrescentadas.
- Reprodutibilidade validada em duas gerações independentes.
