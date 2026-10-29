# Revisão do diagnóstico após esclarecimento do Wardi

O Wardi informou que o Excel apresentado havia sido solicitado para formatação e pediu validação com as LDs. A aplicação deve gerar e conferir dados a partir da LD comercial e do manual, usando o Excel como referência visual, sem forçar igualdade com seus resultados numéricos.

## Conclusões corrigidas

- Hash diferente prova diferença nos bytes do arquivo, não prova por si só diferença nos dados de engenharia. Metadados e formatação também mudam o hash. Um teste cobre alteração apenas em metadados, preservando as horas calculadas.
- As diferenças observadas nas saídas existem, mas o Excel formatado não é um gabarito independente de cálculos validados. Não há fundamento para substituir os valores da LD pelo que aparece nesse Excel.
- Reprocessar uma saída pronta não valida a automação LD + manual. O modo de reprocessamento foi um desvio de escopo e foi retirado.
- O método HH/jornada inferido da referência não substitui duração decorrida com capacidade profissional. Ele e o perfil de prazos fixos de três dias foram retirados.

## O que foi removido

- Upload, modo e código de reprocessamento do cronograma Wardi.
- Perfil parcial e configuração exclusiva da referência.
- Bloqueio de LD/manual por hashes de outro resultado.
- Nome Humberto e prazos fixos inseridos pela seleção do perfil.
- Testes que tratavam reprodução do resultado do Wardi como critério de correção do gerador.
- Alternância de tema: o site agora é exclusivamente escuro, conforme pedido do usuário.

Na atualização de uma sessão antiga, resultados e configurações herdados dos perfis de referência são descartados. Configurações legítimas da geração normal continuam preservadas entre páginas.

## Correções gerais mantidas

- Resolução dos cabeçalhos de função e identificadores que usam referências a células locais ou cache, sem executar macros/fórmulas arbitrárias.
- Separação entre valores financeiros e campos de ajuste de HH.
- Parentesco de hierarquias com mais níveis.
- Agrupamento visual de fase, disciplina, documento e etapas.
- Método de duração por capacidade, com funções trabalhando em paralelo.

## Nova conferência contra a própria LD

Cada registro planejado tem conferência do total original da coluna R com a soma das horas originais lidas por função. São exportados `hh_total_ld`, `hh_total_lido`, `diferenca_total_ld` e `conferencia_total_ld` na Auditoria_HH. Registros não planejáveis permanecem nas pendências e no relatório de conferência; não recebem esforço inventado.

`conferencia_ld.json` contém uma linha por registro e pode ser baixado na interface. Os totais de registro repetidos por função na aba de auditoria não devem ser somados. O motor rejeita divergência acima de 0,000001 HH em um registro planejado.

Com a LD disponível: 652 registros nomeados; 313 planejados com total conferido contra R; 339 sem HH planejáveis. Soma original 13.442,25 HH, documentos com 8.787 HH originais; total planejado 15.199,65 HH após distribuição por função. Esses números são resultados dessa entrada, não metas fixadas no código.

## Limites atuais

A interpretação completa das precedências do manual e a revisão técnica do cronograma permanecem pendentes. A nova conferência valida esforço lido e distribuição, não toda a lógica de engenharia. A segunda LD não foi validada como amostra adicional: o orçamento enviado por engano continua desconsiderado, conforme instrução anterior do usuário. Não se declara validado o funcionamento em todas as LDs.

## Validação desta revisão

32 testes passaram, sem skips nesta sessão. Incluem leitura de cabeçalhos, distinção de custos, hierarquia, esforço por função, duração paralela, comparação direta com o total R, mudança somente de metadados sem alteração de HH, remoção de perfis legados e ausência de seletor de tema. A redução em relação aos 37 testes da versão anterior decorre da retirada dos testes dos recursos de reprocessamento que saíram do produto; não foram desativados testes do cálculo pela LD.

Fluxo também conferido no Chromium: apenas dois uploads, fundo escuro, projeto/prazos vazios, geração pela LD e download de conferencia_ld.json. Resultado: 313 registros conferidos e 339 sem HH planejadas. A nova prévia do site está em visual_blossom.md.
