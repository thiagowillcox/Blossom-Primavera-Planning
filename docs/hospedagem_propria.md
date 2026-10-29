# Hospedar fora do Streamlit Community Cloud

O aplicativo continua usando Streamlit como ferramenta Python. A hospedagem
passa a ser um servidor Linux contratado na conta escolhida pelo responsável.
O projeto fornece Docker para executar o programa e Caddy para HTTPS e login.
Nenhum servidor é contratado ou publicado por esses arquivos.

## O que providenciar primeiro

1. Uma conta em um provedor de servidores virtuais (VPS). DigitalOcean, Azure,
   AWS e Oracle Cloud são exemplos; compare preço e condições antes de contratar.
2. Um servidor Ubuntu 24.04 LTS. Como ponto de partida, considere 2 vCPU e
   4 GB de RAM. Essa é uma referência inicial, não uma capacidade medida para
   vários usuários simultâneos. Confira o custo exibido pelo provedor.
3. Um domínio/subdomínio sob seu controle, por exemplo `planning.seudominio.com.br`.
   O domínio do exemplo não existe para este projeto: substitua pelo seu.
4. Acesso ao servidor por chave SSH. No firewall do provedor, permita 80 e 443
   para o site e limite a porta SSH ao seu endereço IP. Não abra 8501.

Este caminho envolve cobrança do servidor/domínio. Não é necessário contratar
nada para ler o guia ou revisar os arquivos. Para dados da empresa, use uma
conta e condições de hospedagem autorizadas para esse uso.

## Como as partes se conectam

```text
Navegador → HTTPS e login (Caddy) → Blossom Planning (Streamlit)
```

O aplicativo não tem porta publicada no servidor. Apenas o proxy recebe
conexões externas. Ele também encaminha o WebSocket usado pelo Streamlit.
As LDs dos usuários não são incluídas na imagem Docker. O manual de referência fixo é incluído em `resources/manual_engenharia.xlsx`.

## 1. Preparar o servidor

Conecte-se por SSH conforme as instruções do provedor. Instale Docker Engine
e o plugin Docker Compose seguindo o guia oficial para Ubuntu:

https://docs.docker.com/engine/install/ubuntu/

Confira a instalação:

```bash
sudo docker version
sudo docker compose version
```

Instale Git e baixe o projeto:

```bash
sudo apt update
sudo apt install -y git
git clone --branch main https://github.com/thiagowillcox/Blossom-Primavera-Planning.git
cd Blossom-Primavera-Planning
```

## 2. Apontar o domínio

No painel do domínio, crie um registro DNS tipo A para o subdomínio desejado,
apontando para o IP público do servidor. Se houver registro AAAA, ele também
precisa apontar para o servidor correto. Aguarde o DNS propagar.

As portas 80 e 443 devem alcançar o servidor. O Caddy solicitará e renovará
o certificado HTTPS automaticamente. Sem DNS correto ou com portas bloqueadas,
a publicação não fica pronta.

## 3. Configurar o acesso

Gere o hash de uma senha forte. O comando pede a senha de forma interativa:

```bash
sudo docker run --rm -it caddy:2 caddy hash-password
```

Copie o hash exibido, não a senha. Em seguida:

```bash
cp deploy/env.example .env
chmod 600 .env
nano .env
```

Preencha domínio, email, usuário e hash. Mantenha o hash entre aspas simples
para preservar os caracteres `$`. Não envie `.env` ao GitHub nem compartilhe
senhas no chat. O arquivo já é ignorado pelo Git e pelo build Docker.

Essa primeira proteção usa uma conta de acesso compartilhada, criada por você.
Ela restringe o site, mas ainda não oferece contas individuais, SSO, MFA ou
auditoria por pessoa. O login aparece numa janela do navegador. Revise essa
limitação antes de uso definitivo com a equipe.

## 4. Iniciar

```bash
sudo docker compose config --quiet
sudo docker compose up -d --build
sudo docker compose ps
sudo docker compose logs --tail=60 proxy
```

Não publique a saída completa de `docker compose config` sem `--quiet`, pois
ela pode mostrar a configuração de acesso. O primeiro build precisa baixar
as imagens e dependências.

Abra `https://SEU_DOMINIO`. O navegador deve pedir usuário e senha. Se o
certificado não estiver válido, confira o DNS e os logs antes de enviar arquivos.

## 5. Conferir antes de compartilhar

- Abra em janela anônima e confirme que o login é exigido.
- Confira que `http://SEU_DOMINIO` redireciona para HTTPS.
- Confira que `http://IP_DO_SERVIDOR:8501` não está acessível externamente.
- Teste uma LD sem informações confidenciais, gere e baixe o Excel. O manual fixo já está configurado.
- Abra uma segunda sessão e confirme que os resultados da primeira não aparecem.
- Depois de testar, retire ou restrinja a publicação antiga no Community Cloud;
  migrar o código não desliga automaticamente o site anterior.

## Atualizar e acompanhar

Execute na pasta do projeto:

```bash
git pull --ff-only origin main
sudo docker compose up -d --build
sudo docker compose ps
```

Para acompanhar uma falha:

```bash
sudo docker compose logs --tail=100 app
sudo docker compose logs --tail=100 proxy
```

Não remova os volumes `caddy_data` e `caddy_config` nas atualizações: eles
guardam certificados/configuração do proxy. Atualizações do sistema operacional,
imagens e revisão de acessos continuam sendo responsabilidade da operação.

## O que ainda não é feito

- Não há histórico persistente de pré-cronogramas nem banco de dados.
- Uploads são processados temporariamente, sem volume persistente de documentos.
  O resultado fica na sessão e deve ser baixado. Sessões consomem memória e
  podem ser perdidas ao reiniciar. Isso não é garantia de apagamento forense.
- O servidor precisa ser dimensionado/testado para a quantidade de usuários.
- Não há integração Oracle nem aprovação automática das regras do manual.
- HTTPS e senha são uma primeira proteção; não representam uma auditoria ou
  certificação de segurança da aplicação.

## Validação do pacote

Foram conferidos o Compose, o build da imagem, a configuração do Caddy,
o início do aplicativo sem root e com filesystem somente leitura, a interface,
o bloqueio HTTP 401 sem senha e o acesso HTTP 200 com senha fictícia em rede
interna de teste. A geração de Excel também foi testada com entradas sintéticas.
Nenhuma porta foi publicada nesses testes. O certificado HTTPS público e o
acesso por domínio ainda dependem de um servidor e DNS reais e não foram testados.

Neste ambiente de desenvolvimento, o build precisou de uma CA adicional para
validar o acesso ao índice Python. O Dockerfile aceita opcionalmente o segredo
de build `build_ca` para redes com CA própria, sem desabilitar a verificação TLS
nem incorporar o certificado na imagem. Em um servidor com confiança padrão,
o comando normal de build não precisa desse segredo.
