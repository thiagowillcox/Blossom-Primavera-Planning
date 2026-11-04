# Usar o Blossom Planning por um link

O aplicativo continua sendo Streamlit e pode usar o mesmo app já publicado no
Streamlit Community Cloud. A versão local e os iniciadores `.bat` permanecem
como alternativa; não são necessários para o fluxo principal hospedado.

## Um único fluxo no navegador

1. Abra o link hospedado do app, no domínio `streamlit.app`.
2. Em **Arquivos**, envie a LD. O manual fixo já acompanha o programa.
3. Em **Configuração**, preencha o que já souber, resolva eventuais códigos WBS
   repetidos e gere o pré-cronograma.
4. Em **Primavera**, mantenha **Pré-cronograma gerado no site**. O resultado entra
   automaticamente na integração: não é necessário baixar e reenviar Excel.
5. Entre com sua conta Oracle, busque o projeto pelo nome completo e selecione
   explicitamente o destino. As novas gravações continuam limitadas a `TESTE`.
6. Clique em **Conferir estrutura no Oracle (sem enviar)**. A tela mostra os itens
   já compatíveis e os que faltam. Uma estrutura completa pode ser utilizada
   diretamente, sem recriação ou registro JSON importado.
7. Se faltarem itens, revise o resumo e digite `ENVIAR ESTRUTURA <ID>` para criar
   somente os restantes. A conclusão exige nova leitura de conferência.
8. Siga para as funções e horas na mesma página. Consulte as funções, confira a
   correspondência, prepare a prévia e confirme `ENVIAR HORAS <ID>`.
9. Preencha **Equipe e prazos**. O Excel vinculado ao Oracle é selecionado como
   base preferencial. Volte a Primavera para a prévia e confirmação do agendamento.

Cada gravação tem prévia e confirmação próprias. Consultas e preparo de prévia
não enviam dados. Não são criados novos cadastros globais de funções ou
calendários, nem apagadas entidades existentes para fazer uma importação caber.

## Projeto que já recebeu uma estrutura

Se o pré-cronograma original só existir como arquivo, escolha **Excel de um
trabalho anterior**, carregue esse Excel e selecione o projeto Oracle. O programa
confere códigos, nomes, pais, IDs retornados, estados não iniciados e ligações.
Sem diferenças, reconhece a estrutura e monta as associações necessárias para
continuar com as horas. Esse caminho não exige o registro JSON antigo.

Há também **Importar registros antigos (opcional)** para diagnosticar e recuperar
uma tentativa da versão anterior. Os registros baixados são cópias opcionais;
o fluxo normal não depende de encontrá-los no computador.

## Sessão, interrupções e ausência de histórico

Não há banco de dados, cadastro Supabase, histórico persistente ou restauração
automática de trabalhos anteriores. Uma nova sessão não lista trabalhos antigos.
Arquivos temporários pertencem apenas à sessão, com diretório independente de
outros navegadores/usuários. **Novo planejamento / limpar sessão** encerra a
conexão Oracle, remove os arquivos temporários e limpa os dados da tela. Isso
não apaga dados no Oracle.

Durante a sessão, o aplicativo mantém os registros necessários para conferir
solicitações e não repetir automaticamente uma chamada de resultado incerto.
Uma resposta perdida depois de criar um lote de atividades ou ligações pode ser
reconciliada por leitura quando todos os itens forem encontrados corretamente.
Itens ausentes de um lote ainda incerto bloqueiam a repetição na mesma sessão.
Não se presume que uma consulta sem resultados prove que uma chamada anterior
não foi executada.

Ao voltar em outra sessão, gere ou carregue a base novamente e confira o projeto
no Oracle. O aplicativo compara os objetos existentes, preserva os compatíveis
e impede continuar quando houver entidades diferentes, adicionais, iniciadas,
IDs repetidos ou consulta incompleta. Não há garantia transacional entre lotes
ou bloqueio global entre sessões distintas: evite operar o mesmo projeto em duas
abas ao mesmo tempo. Uma situação ambígua exige conferência; não é resolvida
apagando entidades ou repetindo chamadas automaticamente.

Os downloads de Excel, prévias, diagnósticos e registros continuam disponíveis
caso você queira guardar uma cópia, mas não são uma etapa obrigatória.

## Atualizações do site

O app hospedado precisa apontar para este repositório, branch `main`, arquivo
principal `app.py`. O código, dependências, logo e manual fixo estão versionados.
Atualizações publicadas na `main` são disponibilizadas pelo mecanismo de deploy
do Streamlit; quem usa o link não precisa baixar novos ZIPs ou abrir `.bat`.

A configuração de hospedagem pertence à conta Streamlit do proprietário. Se o
link mostrar uma versão antiga, confira em Manage app o repositório, a branch e
o arquivo principal e reinicie o app. O endereço `127.0.0.1:8501` é a execução
local e não é o link hospedado para compartilhar.

O login Oracle usa a conta e as permissões de cada usuário. O fluxo não cria um
login corporativo separado para a página inicial. Restrições de quem pode abrir
o próprio link são configuradas pelo proprietário nas opções de compartilhamento
do Streamlit, se necessárias. Nenhuma senha deve ser colocada no repositório.

## Validação da implementação

A suíte de regressão passou com 210 testes. Os testes do navegador cobrem um
projeto vazio e uma estrutura já existente, do resultado gerado até a conferência
de horas, sem clicar em downloads ou importar registro JSON. Também cobrem a
limpeza da sessão e a separação dos arquivos entre sessões independentes.

As quatro saídas de LD disponíveis foram reconhecidas em consultas simuladas
e seguiram para o envio/conferência de horas no mesmo fluxo. Os testes de
interrupção cobrem resposta perdida depois da criação de atividades e ligações,
recuperação por leitura e bloqueio de repetição quando o lote está incompleto.
Esses ensaios não acessaram nem alteraram a conta Oracle real. O endereço
hospedado depende da configuração do app na conta Streamlit do proprietário;
a confirmação da interface publicada precisa ser feita no próprio link.

## Criar um projeto no workspace escolhido

O nome em **Configuração** identifica o pré-cronograma e serve como sugestão de
nome para um projeto novo. Gerar o Excel não cria um projeto automaticamente.

Depois de conectar ao Oracle, a seção Primavera oferece dois destinos:

- **Usar projeto existente:** busca o nome, pede a escolha do ID e utiliza o
  workspace ao qual aquele projeto já pertence.
- **Criar projeto novo em um workspace:** consulta os workspaces visíveis à conta,
  mostra o caminho na hierarquia e pede uma seleção explícita.

Para criar, preencha nome, código e data/horário inicial. O nome configurado na
geração aparece sugerido, com `TESTE -` quando necessário para a proteção atual.
O código é o identificador escolhido pelo usuário; o ID numérico é criado pelo
Oracle. Nomes e códigos podem ser editados antes de preparar a prévia.

É possível consultar os calendários do workspace e de seus ancestrais e escolher
um calendário existente. Sem seleção explícita, o programa deixa o Oracle usar
seu padrão. Não são criados nem modificados workspaces ou calendários.

**Preparar criação do projeto** somente consulta e valida. A prévia mostra o
workspace e seu ID, nome, código, início, calendário e status inicial Planejado.
A data inicial também é enviada como data dos dados nessa criação. Após digitar
`CRIAR <código>`, **Criar projeto no Oracle** chama o endpoint de criação uma vez
e consulta o ID retornado para conferir nome, código e workspace. Um calendário
explicitamente escolhido também precisa ser confirmado na leitura.

O projeto criado fica selecionado para seguir pelo fluxo de estrutura, horas e
prazos. A criação não envia a estrutura nem solicita agendamento automaticamente.
A data também preenche a previsão de equipe se ela ainda estiver em branco.

Um código já existente no workspace bloqueia uma nova criação; nenhum projeto
é substituído. Antes da gravação, workspace e código são conferidos novamente.
Se uma resposta se perder, o registro temporário da sessão permite consultar o
projeto correspondente e reconhecê-lo sem repetir o POST. Se a consulta não
confirmar o resultado, não há repetição automática. A criação depende das
permissões da conta Oracle no workspace selecionado.

A operação usa o OpenAPI oficial fornecido, com contrato resumido em
`config/oracle_project_contract.json`: `GET /workspace`, consultas do workspace,
projetos e calendários, `POST /project` e `GET /project/{projectId}`. O corpo de
criação inclui todos os campos obrigatórios do schema. Os testes são simulados;
a criação real precisa de validação na conta Oracle. As gravações continuam
limitadas a nomes que começam com `TESTE` nesta versão.
