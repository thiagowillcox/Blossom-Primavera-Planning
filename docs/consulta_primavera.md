# Consulta local e prévia — integração Oracle

A autenticação e o endpoint `util/testConnection` foram confirmados pelo usuário
no Oracle Primavera Cloud. A gravação de cronogramas ainda não está implementada.

## 1. Consultar o destino

No Windows com Python 3.12, extraia a main atual e abra
`Listar_Projetos_Primavera.bat`. Informe login/senha no console local, como no
teste anterior. Informe também o nome completo do projeto. O programa autentica,
testa a conexão e consulta `GET /api/restapi/project/name/{projectName}`, com o
nome codificado como um único segmento do endereço.

A rota foi confirmada na documentação oficial **Project REST Endpoints → View
all Projects by Name**, fornecida pelo usuário em 30/10/2026:
https://docs.oracle.com/en/industries/construction-engineering/primavera-cloud/opcap/api-project.html
A tentativa anterior de `GET /api/restapi/project` retornou HTTP 405 no ambiente
real e foi substituída. Não há tentativa de escrita nem criação como alternativa.
O formato da resposta e a consulta corrigida ainda precisam de validação real.
A consulta mostra somente os resultados recebidos; não afirma que todas
as páginas ou todos os projetos foram lidos.

Confira o nome retornado e escolha
o ID exibido. A seleção é salva somente em
`output/consulta_primavera_local.json`. O programa retém apenas projectId,
projectCode, projectName e workspaceId. Não salva token/senha ou o corpo
completo da resposta Oracle. A pasta output ignora novos arquivos no Git.

Se mais de um projeto corresponder ao nome, o usuário precisa escolher o ID;
nenhum primeiro resultado é escolhido automaticamente. Sem correspondência,
nenhum projeto é inventado e nenhum destino é selecionado.

Compartilhe somente o nome/ID do projeto escolhido ou a mensagem final de erro.
Não envie a lista completa, tokens, senhas ou codificação Base64.

## 2. Preparar a prévia offline

Gere um novo pré-cronograma pelo site, com as regras e premissas atuais.
Depois abra `Preparar_Envio_Primavera.bat` e arraste o Excel gerado para a janela.
O iniciador usa o ambiente local instalado por `Abrir_Blossom.bat`.

Essa etapa não pede senha, não acessa a rede e não envia dados. Ela lê o Excel
e a seleção local do projeto, verifica IDs/grafo/somas de atribuições e auditoria,
conta durações/entradas técnicas pendentes e registra o resumo em
`output/previa_envio_primavera.json`.

O JSON é uma prévia interna, **não é um payload válido da API Oracle**.
`pronto_para_envio` e `envio_implementado` permanecem falsos. Mesmo que todas
as durações estejam preenchidas, ainda é necessário confirmar os endpoints,
os campos, as unidades, o calendário/data-base e o mapeamento de funções para
recursos/papéis do Oracle antes de implementar a escrita.

## Situação da validação

Testes automatizados usam respostas simuladas; a autenticação/teste de conexão
real foram executados pelo usuário. A consulta de projetos ainda precisa ser
executada no ambiente real, e os iniciadores Windows precisam ser conferidos
no computador do usuário. Nenhum projeto, WBS, atividade, recurso ou
relacionamento é criado ou alterado por essas ferramentas.

A documentação oficial completa da API (especialmente projetos, WBS,
atividades, atribuições e relacionamentos) é necessária para a próxima etapa.

Validação do código após corrigir a consulta por nome: 127 testes passaram. A prévia offline também foi executada
nas quatro saídas comerciais disponíveis, usando um destino simulado e sem
nenhuma chamada de rede. Isso não valida o endpoint de projetos no tenant real
nem os campos de uma futura solicitação de criação no Oracle.
