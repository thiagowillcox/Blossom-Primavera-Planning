# Horas por função, equipe e integração Oracle

O fluxo principal agora está no [guia de uso por link](uso_por_link.md), sem
exigir download/importação de registros. As instruções de arquivos abaixo
continuam disponíveis na opção Importar registros antigos.

A geração da LD e as oito abas originais permanecem preservadas. Esta entrega
acrescenta duas áreas ao site: **Equipe e prazos** e **Primavera**. O envio inicial da estrutura também está no site, com os iniciadores locais
como alternativa.

## Começar pelas horas no projeto já criado

1. Abra **Primavera** no menu do site.
2. Carregue o **mesmo Excel original** que foi enviado ao Oracle e o registro
   `output/envio_rascunho_<ID>.json` daquela operação concluída. O registro é
   necessário para reconhecer os IDs Oracle sem recriar atividades.
3. Entre com seu usuário Oracle e senha. A senha é descartada após autenticação;
   o token fica apenas na memória dessa sessão. Não há cache global da conexão.
   A conexão é encerrada ao desconectar ou na próxima interação após 20 minutos.
4. Consulte o projeto e as funções. O programa confere todas as atividades e WBS,
   seus nomes/códigos/pais e o estado não iniciado das atividades. Consultas
   incompletas ou alterações relevantes bloqueiam o envio.
5. Escolha um cadastro Oracle distinto para cada função com horas na LD.
   Os códigos conhecidos podem aparecer sugeridos, mas a confirmação é sua.
6. Confira a prévia. Ela mostra o projeto, as funções, as horas e as associações
   de funções existentes que ainda precisam ser adicionadas ao projeto.
7. Digite `ENVIAR HORAS <ID>` e confirme o envio. Ao terminar, baixe o registro.

São utilizados cadastros existentes da classe `ROLE`, tipo `LABOR`, ativos,
visíveis no projeto ou em seus workspaces ancestrais. O programa não cria nem
renomeia funções globais, não substitui um recurso material por mão de obra e
não presume que a função Especialista equivale a outra senioridade. Sem uma
correspondência válida, a prévia não avança.

As horas são enviadas em `plannedUnits` e `remainingUnits`, para atribuições
não iniciadas. Não são convertidas em dias. `driveActivityDates` fica falso:
este envio não define a duração da atividade. Custos e taxas não são enviados;
o Oracle poderá aplicar os cadastros de custo que já existam.

Cada atribuição usa um código estável derivado do ID original do Blossom.
Antes de gravar, o programa lê as atribuições existentes. Uma atribuição já
compatível é preservada. Horas diferentes, avanço real, código divergente para
a mesma atividade/função ou IDs repetidos bloqueiam a operação, em vez de
sobrescrever ou somar esforço. A confirmação final usa uma nova consulta e
reconcilia as horas com tolerância de 0,000001 HH, considerando a representação
numérica da API. Na tela, HH têm apresentação legível; os dados de auditoria
mantêm os valores recebidos.

Os lotes contêm até 50 atribuições. Um registro é sincronizado em disco antes
de cada chamada. Se uma resposta se perder após a criação, a nova consulta
pode reconhecer o lote completo e continuar. Um lote com resultado ainda
incerto e não encontrado na leitura não é repetido automaticamente. Guarde o
registro; ele pode ser importado na seção Primavera para recuperar a operação.

## Equipe, calendário e previsão

A tela **Equipe e prazos** aceita o resultado desta sessão ou o Excel vinculado
ao Oracle. Data inicial, jornada, dias úteis, capacidade de cada função e prazos
do cliente são preenchíveis. Uma equipe desconhecida ou um prazo do cliente
em branco mantém as durações dependentes como pendentes.

A lista de feriados de Belo Horizonte é uma **sugestão editável para três anos**,
com feriados nacionais e religiosos/municipais usuais. Confira a lista vigente
e as regras da empresa antes de confirmar. Carnaval e pontos facultativos não
são tratados automaticamente como feriados. Acrescente paralisações específicas
ou anos seguintes quando necessário. Uma alteração nos parâmetros do calendário
exige nova confirmação. O calendário Oracle é conferido separadamente antes do
agendamento; nenhuma lista global de feriados é alterada pelo programa.

A previsão usa as horas de cada função, a equipe informada, funções paralelas
por atividade e prazos independentes do cliente. A distribuição de esforço é
uniforme durante o prazo da atividade. Ela mostra:

- início/fim previstos, quando calculáveis;
- horas por dia e por semana, por função;
- capacidade informada e sobrecarga;
- gráfico semanal de demanda e disponibilidade;
- horas que continuam sem previsão e seus motivos.

O ajuste opcional à equipe usa uma heurística de alocação seriada que preserva
as ligações FS e evita ultrapassar a capacidade informada. Não garante o menor
prazo possível nem modela particularidades de produtividade de cada documento.
As capacidades são premissas locais da previsão, não alterações em cadastros
globais de disponibilidade do Oracle.

Entradas técnicas pendentes bloqueiam a previsão e propagam a falta de início
às sucessoras. Quando uma entrada estiver efetivamente disponível desde o
início previsto, é possível registrar a confirmação e sua justificativa para a
atividade. Essas decisões ficam vinculadas à base e entram no relatório;
a LD e a pendência original não são apagadas. Não há aprovação técnica automática.

Baixe o Excel e o JSON da previsão para guardar dados e decisões. Esse relatório
é separado do pré-cronograma original, preservando a rastreabilidade do envio.

## Atualizar prazos e solicitar o cálculo do Oracle

Depois de preencher os parâmetros, conferir as entradas técnicas e enviar as
horas, volte à seção Primavera e prepare a prévia do agendamento. Para esta
etapa, a previsão deve usar o **Excel vinculado ao projeto Oracle**.

O programa verifica todas as atividades, relações e horas, o calendário de cada
atividade, os turnos de 30 minutos do calendário do projeto, feriados e exceções
durante o período da previsão. Calendários diferentes, restrições existentes,
feriados recorrentes não reconhecidos ou diferença entre dias/horas úteis do
site e do Oracle bloqueiam a atualização. O programa não substitui o calendário
por uma suposição de oito horas.

Após `AGENDAR <ID>`, a operação atualiza as durações em **horas**, define o tipo
`FIXED_DURATION_AND_UNITS` para preservar o esforço, confere durações e horas
por nova leitura e atualiza a data inicial/data dos dados do projeto de teste.
Em seguida, solicita `action/scheduleProject`, guarda o ID do job e permite
consultar o andamento. Uma solicitação de job não significa que o cálculo
terminou; somente o status do Oracle informa a conclusão. As HH são conferidas
novamente quando o job termina.

Esse cálculo é o **CPM nativo do Oracle**. A operação não envia restrições para
impor as datas da heurística local e não declara que houve nivelamento global
no Oracle. Confira as datas calculadas e a carga nas telas do projeto.
Um registro de agendamento existente impede repetir automaticamente uma
solicitação cujo resultado pode ser incerto.

## Segurança, armazenamento e limites atuais

As novas gravações estão limitadas a projetos cujo nome começa com `TESTE`.
Todas usam HTTPS verificado no tenant já utilizado. Não há redirecionamento de
credenciais, senha/token em relatórios ou rotas livres fornecidas pelo usuário.

Não existe transação única entre lotes. Uma falha pode deixar parte dos dados
criada/atualizada. Preserve os registros e confira o Oracle antes de repetir.
A exclusão de dados não faz parte deste fluxo.

Os arquivos de execução são temporários e isolados por sessão, não um histórico.
O fluxo integrado reconhece a estrutura compatível no Oracle sem exigir os JSONs
locais. Downloads são opcionais para quem quiser guardar cópias. Não há banco
de histórico; o login utilizado na integração é o da própria conta Oracle.

A documentação foi conferida no `openapi.json` fornecido, versão 2026.10.02.
O recorte do contrato está em `config/oracle_effort_contract.json`. Os testes de
criação de horas e de agendamento usam respostas simuladas. O envio estrutural
anterior foi validado pelo usuário na conta real; **estas novas gravações ainda
precisam do primeiro teste real**. Nenhuma senha foi recebida ou utilizada pelo
assistente nesta implementação.

## Verificação desta entrega

A suíte de regressão passou com **194 testes**, incluindo conexão por sessão,
prévia sem gravação, confirmação explícita no site, descarte da senha,
conservação de HH, bloqueio de conflitos e recuperação por leitura após falha.
Também foram simulados criação, conferência e repetição sem duplicação das
atribuições nas quatro saídas de LD já disponíveis. A previsão com ajuste à
equipe conservou as horas e manteve as entradas técnicas pendentes separadas.
Nenhum desses ensaios usou credenciais reais ou gravou no tenant Oracle.

## Mensagens e diagnóstico de um envio interrompido

As mensagens de prévia e erro são mantidas na sessão após atualizar campos ou
baixar arquivos. Novas interrupções também guardam no registro uma mensagem
sanitizada, sem senha, token ou corpo bruto da resposta Oracle. Registros antigos
podem não conter o motivo da falha.

Para conferir uma tentativa sem gravar, prepare a prévia e clique em
**Conferir situação das horas (sem enviar)**. Essa ação usa apenas GET depois
da autenticação. Ela consulta os dados atuais, compara as horas/funções com a
prévia e permite baixar `diagnostico_horas_<ID>.json`. O relatório diferencia
atribuições compatíveis, não encontradas e divergentes, e inclui os campos
mínimos para conferir o lote interrompido quando o registro for compatível.
Não há repetição de lotes ou alteração do registro de execução nessa consulta.

O diagnóstico é diferente de `previa_horas_oracle.json`: a prévia contém as
solicitações preparadas, enquanto o diagnóstico inclui a comparação com a
leitura atual do Oracle. Uma consulta sem resultados não esclarece, sozinha,
o motivo de uma falha passada nem libera automaticamente um lote incerto.
