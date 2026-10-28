# Compatibilidade e conferência de LDs

O leitor aceita a aba LD isolada ou dentro do orçamento. Continua usando o layout
Blossom: cabeçalho de nove funções em H:P na linha 4, quantidade E, unidade F,
A1 equivalente G e total de HH R. Uma estrutura diferente exige adaptação;
não se presume que qualquer planilha seja compatível.

Variações tratadas:

- Nome da aba LD, códigos e unidades com espaços ou diferenças de maiúsculas.
- Células em branco, espaços Unicode/invisíveis e o marcador literal `\xa0`.
- Números em texto inequívocos, como `12`, `12,50`, `12.50`, `1.234,50`
  e `1,234.50`. `1.234` e `1,234` em texto são ambíguos e exigem revisão;
  células numéricas do Excel não têm essa ambiguidade.

Não se transforma texto desconhecido em zero. Números negativos/não finitos,
fórmulas sem resultado salvo, total com mix de funções ausente e divergências
com o total original continuam bloqueados ou sinalizados. Não se inventam
quantidades, horas, capacidades ou dependências. Aba ausente/vazia, cabeçalho
incompatível e ausência de registros reconhecidos produzem mensagens explícitas.
As células originais permanecem preservadas na rastreabilidade, inclusive os nomes.

## Conferência com arquivos recebidos

Comparação direta com o leitor anterior para as duas entradas já aprovadas:
registros completos, WBS e pendências permaneceram iguais, incluindo IDs e HH.

| Entrada | Atividades | HH originais | HH planejadas |
| --- | ---: | ---: | ---: |
| BL1120-0011_R03 — LD original | 952 | 13.442,25 | 15.199,65 |
| BL1120-0011_R03 — Orcamento_JSF (5) | 952 | 13.204,25 | 14.907,50 |
| BL1120-0012_R00 — LD | 95 | 574,8125 | 650,2625 |

Na terceira entrada, 14 documentos antes bloqueados pelo marcador `\xa0`
passam a ser incluídos. São 21 documentos em quatro etapas e 11 auxiliares.
A soma por função confere com R em todos os registros planejados. Permanecem
461 registros sem HH, quatro avisos de fórmulas e sete de ciclo a confirmar,
além das pendências de duração e manual. Nenhum desses avisos é resolvido
por simples normalização de células.

Os testes cobrem marcadores vazios, números em texto, rejeição de ambiguidades,
layouts incompatíveis e preservação das horas. Isso reduz falhas conhecidas;
novos layouts ou casos não reconhecidos ainda podem exigir ajustes.
