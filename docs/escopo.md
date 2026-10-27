# Conferência com o pedido original

Esta versão corrige a organização da entrega; não altera os arquivos Excel de entrada nem cria novas premissas comerciais.

| Pedido | Implementação e limite |
|---|---|
| Ler LD e distinguir documentos/auxiliares | Leitura do layout recebido, códigos comerciais e unidades; HH desconhecidas ou inconsistentes ficam pendentes. |
| WBS hierárquica | Somente os 56 nós de fases e disciplinas; termina na linha 57 do Excel recebido, incluindo o cabeçalho. Não é um corte arbitrário por número de linha: outras LDs podem ter outra quantidade de nós. |
| Documentos em quatro etapas | 80/10/20/10 por função, conforme instrução expressa do usuário. 213 documentos com HH utilizáveis. |
| Auxiliares sem acréscimo automático | Uma atividade com 100% das HH por auxiliar calculável; 100 auxiliares. |
| Jornada/capacidade e prazos editáveis | JSON; jornada 8. Capacidade e prazos não fornecidos permanecem vazios. Não se deduz prazo do cliente pelas suas HH. |
| Manual e regras versionadas | Extração parcial: figuras preservadas com hash/origem e quatro observações visuais. A interpretação completa das três matrizes FEL e o mapeamento técnico ainda não foram concluídos. Evidências catalogadas não são regras interpretadas. |
| Predecessoras/sucessoras | Encadeamento das etapas configurável; vínculos técnicos obrigatórios exigem aprovação explícita e referência existente na matriz. Nenhuma relação técnica obrigatória foi inferida das figuras. |
| Oito abas e dados originais | Oito abas mantidas. Auditoria e pendências preservam os registros originais/cache e vínculos por ID. JSON completo inclui também os registros sem atividades. |
| Identificadores estáveis | Identidade semântica, sem número da linha como chave única; mudanças de nome podem exigir associação explícita. |
| Validações | Testes de HH, percentuais por função/etapa, auxiliares, IDs, integridade, ciclos, dados vazios, regra inexistente e reprodução dos arquivos reais. |
| Sem Oracle/BMS | Nenhuma escrita na API e nenhum acoplamento BMS. |
| Pré-cronograma do Forno III | Resultado produzido a partir da LD enviada. Ainda é necessária confirmação de que essa LD corresponde ao Forno III. |

## O que ainda impede declarar a primeira fase concluída

A matriz técnica completa do manual não foi extraída/interpretada e validada. Faltam capacidades e prazos para preencher as durações, além de resolver os casos comerciais sinalizados. O resultado pode ser conferido como protótipo de cálculo e estrutura; não é um cronograma tecnicamente integrado aprovado.
