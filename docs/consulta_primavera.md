# Consulta local e prévia — integração Oracle

A autenticação e o endpoint `util/testConnection` foram confirmados pelo usuário
no Oracle Primavera Cloud. A consulta de projetos também foi confirmada pelo
usuário. O envio completo de cronogramas continua pendente; há um iniciador
separado para [rascunhos estruturais](envio_rascunho_primavera.md), sem HH e prazos.

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
O usuário executou a consulta corrigida com sucesso e selecionou o destino.
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
`pronto_para_envio` e `envio_implementado` permanecem falsos para o envio
completo com HH, recursos e prazos. O campo `envio_estrutural_disponivel` informa
que existe um iniciador separado de rascunho. Sua execução exige uma nova
conferência do destino e confirmação explícita do resumo exibido.

## 3. Criar o rascunho estrutural

Veja [Enviar uma estrutura de teste ao Oracle](envio_rascunho_primavera.md).
Essa operação pode criar dados reais no projeto vazio selecionado; a prévia e a
consulta, isoladamente, continuam sem gravar entidades no Oracle.

## Situação da validação

O usuário executou autenticação, consulta por nome, seleção e prévia offline.
O contrato de criação foi conferido no OpenAPI oficial fornecido pelo usuário.
Os testes de escrita são simulados; ainda não houve criação real confirmada.
O motor de planejamento e as regras da LD/manual não foram alterados por essa
integração. As atribuições de recursos/HH e os prazos permanecem para outra etapa.
