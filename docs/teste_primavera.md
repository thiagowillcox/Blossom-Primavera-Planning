# Teste local de conexão ao Primavera Cloud

O teste usa as instruções oficiais mostradas pelo usuário:

- Basic → token: https://docs.oracle.com/en/industries/construction-engineering/primavera-cloud/opcap/D175778.html
- Bearer → teste: https://docs.oracle.com/en/industries/construction-engineering/primavera-cloud/opcap/D175775.html

Há somente uma solicitação POST para gerar o token e uma GET para
`/api/restapi/util/testConnection`. Nenhum projeto é listado, criado ou alterado.
Não há envio de WBS, atividades, atribuições ou relacionamentos.

## Windows

Baixe a versão atual da main e extraia o ZIP. Com Python 3.12 instalado, abra
`Testar_Primavera.bat`. Digite usuário e senha somente no console local que abrir.
A senha não aparece durante a digitação. O teste usa somente a biblioteca padrão
do Python; não exige instalação adicional de pacotes ou hospedagem.

Não envie a senha, o token ou a codificação Base64 ao chat e não use sites
externos para codificar suas credenciais. Base64 é reversível, não criptografia.
O programa faz essa codificação em memória e envia apenas ao endereço HTTPS
do Primavera `primavera-us2.oraclecloud.com`. O `http` do parâmetro `scope`
é o identificador exigido pela documentação; a conexão de rede continua HTTPS.

## Resultados

Compartilhe apenas a mensagem final de sucesso/erro. Não é necessário mostrar
a tela com seu email. Um HTTP 401/403 pode exigir configuração adicional da
autenticação/permissões; não prova, isoladamente, que a senha está errada.
Não tente repetidamente em caso de recusa.

O parser reconhece os campos `access_token` e `accessToken`. Se o seu ambiente
responder com outro formato, ele interrompe o teste sem imprimir o conteúdo.
Confira então o exemplo de resposta da documentação, sem expor um token real.

Não salva credenciais, não cria arquivo de token e não segue redirecionamentos.
Não desativa a verificação dos certificados TLS. Foi testado com respostas
simuladas; a autenticação real depende da execução pelo titular da conta.
O iniciador Windows ainda precisa ser validado no computador do usuário.
