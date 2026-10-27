# Inspeção anterior à implementação

## LD comercial

Arquivo recebido: `BL1120-0011_R03 - LD (2).xlsm`. Uma aba `LD`, 936 linhas e 23 colunas. Linha 3: ITEM, EAP, especificação, folhas, unidade e A1 equivalente. Linha 4: nove funções em H:P, HH/A1 em Q, total original em R, fator em T e valores ajustados em U:V.

B contém códigos hierárquicos como `1.0`, `1.1`, `2.0`, `3.0`, `4.0`. A hierarquia cobre engenharia conceitual, básica, detalhada e atividades complementares. Dentro das fases aparecem disciplinas/coordenação e seções “Desenhos / Documentos” e “Atividades”. Os códigos DC/DB/DD e AC/AB/AD distinguem registros de documentos e de atividades auxiliares por fase.

Registros com descrição: 73 DC, 122 DB, 218 DD; 61 AC, 69 AB e 109 AD (652 no total). Há HH positivas em 213 DD e 97 AD. As fases conceitual/básica estão sem HH positivas. Não se deve preencher essas lacunas a partir do manual ou das descrições.

As células G convertem folhas em A1: A4/8, A3/4, A2/2, A1, A0×2. Para unidade HH as funções têm esforço direto. As fórmulas R somam as funções, multiplicando por G apenas quando a unidade não é HH. T/U/V são ajustes comerciais adicionais, preservados para consulta e separados da base original.

Exemplo real: linha 519 “Abrigo Compressores - SPCI”: uma folha A1, mix 1/1/4/4/8 nas funções preenchidas, total original 18 HH. Linha 548 “Memória de Cálculo de Dimensionamento de Processo - Forno (Reemissão)”: 24 folhas A4 = 3 A1, soma unitária 5 HH/A1, total original 15 HH. As linhas de totais e cabeçalhos não são novas atividades e não entram duas vezes no esforço.

## Manual

Arquivo recebido: `Mnaual de Engenharia Blossom.xlsx`. O histórico identifica BL0000-GE-MAN-0001, revisão 02 de 21/01/2026. Sete abas:

- Histórico de Revisões: 14 linhas.
- Sumário: 23 linhas.
- 1. Objetivo e 2. Definições: 111 linhas.
- 2.3.1 Eng. Conceitual - FEL 2: 2178 linhas.
- 2.3.2 Eng. Básica - FEL 3: 3235 linhas.
- 2.3.3 Eng. Detalhada - FEL 4: 3033 linhas.
- Engenharia Digital - BIM: 31 linhas.

Há 314 arquivos de mídia no XLSX. Nas três abas FEL há figuras ancoradas aos blocos de disciplinas/documentos. Texto em células identifica títulos e localização; os detalhes de SIPOC e das orientações estão em imagens. Existem erros `#VALUE!` em células de cabeçalho, sem evidência de que representem regras de relacionamento.

Dois exemplos visualmente inspecionados na Engenharia Detalhada:

- Fluxo geral de coordenação, imagem original `image206.png`, ancorada na linha 60: disciplinas alimentam entregáveis e cliente recebe saídas; há seta de Planilha de Quantidades a CAPEX/OPEX. Isso não define por si só relação temporal FS.
- Planilha de Quantidades Multidisciplinar, imagem `image89.png`, linha 140: cliente fornece normas, disciplinas fornecem informações, e uma decisão verifica consistência/suficiência. O retorno “NÃO” é um ciclo de obtenção de informação, não um ciclo válido de cronograma.

Esses exemplos originam quatro observações versionadas com hash do arquivo. A matriz completa de relações aprovadas ainda requer análise humana das demais figuras e correspondência com os entregáveis da LD.

## Ambiguidades registradas

- A LD não apresenta um identificador único preenchido para cada entregável. Usar chave semântica estável e rejeitar colisões.
- A denominação Forno III não está inequivocamente identificada no arquivo; confirmar com o responsável.
- Reemissões e atualizações podem não exigir o mesmo ciclo de uma emissão nova. Aplicar a distribuição solicitada e marcar a aplicação para revisão.
- Recursos disponíveis, prazos do cliente, calendário e data-base não foram fornecidos. Não inventar durações nem datas.
- Entradas SIPOC podem ser referência, informação externa ou condição; não gerar dependência obrigatória automaticamente.
- Valores em cache podem estar desatualizados. Reproduzir somente fórmulas conhecidas e confrontar os totais; bloquear HH inconsistentes.
- Tipos documentais específicos estão frequentemente embutidos no nome, não em uma coluna padronizada. Preservar a descrição; não inventar classificação semântica.

## Achados adicionais da execução

As fórmulas em HH das linhas 508, 509, 512 e 530 têm cache disponível; três auxiliares adicionais passam a ser planejáveis além dos 97 com constantes positivas. Foram planejados 213 documentos e 100 auxiliares. A linha 790, “Consultoria NR12 - R$ 40.000,00”, tem unidade VB e valores em funções, mas não tem A1 nem total calculável. Ela permanece bloqueada; os valores não são convertidos em HH por suposição. As linhas 757 e 875 também são verbas VB, sem HH planejáveis.
