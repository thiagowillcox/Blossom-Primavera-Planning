# Enviar uma estrutura de teste ao Oracle

O iniciador `Enviar_Rascunho_Primavera.bat` cria WBS, atividades e ligações FS
sem defasagem em um projeto **vazio**, cujo nome comece com `TESTE`. Ele não cria
nem substitui projetos, não altera entidades existentes e não executa agendamento.
O gerador do site continua independente desta operação local.

## Preparação e execução

1. Atualize os arquivos do programa. Preserve a pasta `output` da instalação em
   uso: nela ficam a seleção, a prévia e os registros de envio. Não apague registros
   de tentativas anteriores para tentar novamente.
2. Selecione o projeto com `Listar_Projetos_Primavera.bat` e prepare o Excel com
   `Preparar_Envio_Primavera.bat`, caso ainda não tenha feito essas etapas.
3. Abra `Enviar_Rascunho_Primavera.bat` e arraste **o mesmo Excel** usado na prévia.
   O iniciador usa o ambiente Python instalado por `Abrir_Blossom.bat`.
4. Confira o resumo exibido. O arquivo completo de solicitações estruturais,
   ainda com referências locais, fica em `output/plano_rascunho_primavera.json`.
5. Informe usuário e senha no console. O programa consulta o projeto selecionado,
   confere nome/código/workspace, ausência de atividades e presença de apenas
   uma WBS raiz. Um projeto preenchido bloqueia o envio.
6. Somente após conferir esse resumo, digite `ENVIAR` seguido do ID mostrado.
   Enter cancela sem gravar nada no Oracle.
7. Aguarde a criação e a leitura de conferência. Não edite o mesmo projeto durante
   a operação. Ao final, confira também a estrutura na interface do Primavera.

A seleção e a prévia antigas continuam compatíveis: o nome do arquivo, seu hash
e o destino precisam coincidir. O plano é reconstruído do Excel e validado; o
JSON da prévia não é utilizado como solicitação de criação.

## O que é enviado

- WBS na ordem dos pais antes dos filhos, abaixo da raiz existente. Os códigos
  e nomes vêm da planilha; IDs gerados pelo Oracle determinam as associações.
- Atividades como `ACTIVITY`, `NOT_STARTED`, com nome completo e ID estável
  Blossom como `activityCode`, dentro da WBS correta.
- Ligações `FINISH_TO_START`, com `lagHours: 0`, usando os IDs Oracle retornados.
  Outras modalidades e defasagens são bloqueadas antes da primeira gravação.

Não são enviados HH, atribuições de funções, recursos, custos, durações,
calendários, restrições, datas ou marcações de avanço. As pendências técnicas
permanecem no Excel e no plano local; não são criadas como campos Oracle.
**O Oracle poderá aplicar durações/datas/calendário padrão ao criar atividades.**
Esses valores não representam prazos validados pelo Blossom. A estrutura é um
rascunho; ainda não constitui o cronograma final.

## Registro, interrupções e conferência

WBS são criadas individualmente; atividades e ligações, em lotes de até 50.
As respostas precisam corresponder às chaves solicitadas; a ordem do lote não
é usada para associar IDs. A conclusão exige uma nova consulta de WBS,
atividades e ligações, comparando IDs, nomes, pais, tipos e referências.

Antes de cada solicitação de criação, o programa grava e sincroniza em disco
`output/envio_rascunho_<ID>.json`. Esse registro guarda os IDs confirmados e a
solicitação em andamento. Não guarda senha, token ou respostas completas.

Não há transação única: uma falha de rede, permissão ou validação pode ocorrer
**depois de criar parte da estrutura**. Não há repetição automática, exclusão,
rollback ou continuação automática. Um registro existente bloqueia outra
execução, mesmo após sucesso, para impedir duplicação. Em caso de falha, preserve
esse arquivo e confira o Oracle antes de qualquer nova tentativa. Uma resposta
incompleta/paginada na conferência também impede declarar o envio concluído.

## Documentação e limites da validação

O contrato foi extraído do `openapi.json` oficial enviado pelo usuário, versão
`2026.10.02`, SHA-256
`27d1ea55a6e16b554533ca8ae1713500e230d8290fb9260dd7e8e0c3cb8584ca`.
O recorte de campos, limites e endpoints está em
`config/oracle_structural_contract.json`.

As criações usam `POST /wbs`, `POST /activity/batch` e
`POST /relationship/batch`, com resposta documentada HTTP 201. A conferência usa
`GET /project/{projectId}`, `GET /wbs/project/{projectId}`,
`GET /activity/project/{projectId}` e
`GET /relationship/projectRelationshipCode?workspaceCode=...&projectCode=...`.

A autenticação, a busca por nome e a prévia offline foram executadas com sucesso
pelo usuário. **As gravações ainda não foram executadas na conta real.** Os
ensaios de criação usam um servidor simulado, incluindo falha após criação,
resposta fora de ordem, lotes, conferência e cancelamento antes do envio.
A API real poderá exigir permissões adicionais ou configurações do projeto;
esses casos interrompem o envio e precisam de diagnóstico antes de repetir.

Validação local: 139 testes passaram na suíte completa; o módulo de envio
passou em 13 cenários após acrescentar a confirmação positiva no console.
As quatro saídas comerciais disponíveis também foram processadas em simulação
de criação e conferência, sem chamadas à conta real e sem publicar essas saídas.

## Diagnosticar uma interrupção na criação de WBS

Se aparecer `Resposta da WBS diferente do esperado`, preserve o registro e o
plano locais. A solicitação pode ter criado a WBS antes da divergência.
Atualize os arquivos do programa preservando `output` e abra
`Diagnosticar_Envio_Primavera.bat`. O diagnóstico usa somente autenticação e GET
para consultar o projeto, suas WBS e atividades. Ele não chama os endpoints de
criação, atualização ou exclusão.

O relatório `output/diagnostico_rascunho_primavera.json` compara os campos
esperados com os encontrados no Oracle, incluindo o grupo da solicitação
interrompida. O relatório também contém os nomes/IDs das WBS desse projeto de
teste: compartilhe-o apenas com quem está tratando a integração, não em um
repositório público. Não inclui credenciais ou respostas completas da API.
O plano precisa ter o mesmo hash registrado no envio para autorizar a consulta.
A ferramenta não retoma nem repete gravações. A causa da divergência depende
desse relatório; não deve ser presumida apenas pela mensagem de erro.

## Continuar após o Oracle remover espaços no fim de um nome

A criação real revelou que o Oracle remove espaços ASCII no começo/fim dos
nomes. A comparação de `wbsName` e `activityName` agora aceita apenas essa
normalização. Códigos, IDs, hierarquia, acentos, caixa e espaços internos continuam
sendo conferidos. Os nomes das solicitações são aparados, sem alterar o Excel,
o plano original ou seu hash.

`Retomar_Envio_Primavera.bat` permite uma continuação restrita à fase de WBS:

- O mesmo Excel, seleção e plano originais precisam coincidir com o hash
  registrado antes da interrupção.
- Nenhuma atividade ou ligação pode ter sido registrada/criada.
- Os grupos confirmados precisam formar o início exato da sequência do plano.
- A solicitação pendente precisa ser a próxima WBS e essa WBS precisa existir
  uma única vez no Oracle, com código, nome e pai corretos.
- A consulta precisa conter somente a raiz, os grupos confirmados e esse grupo
  pendente. Qualquer grupo extra ou diferença real bloqueia a continuação.

A ferramenta consulta o projeto antes da confirmação e novamente antes de
continuar. Ela mostra quantos grupos serão preservados e quantos faltam.
Somente após `ENVIAR <ID>` salva uma cópia do registro anterior como
`output/envio_rascunho_<ID>.backup_<hash>.json`, registra o ID do grupo reconciliado
e cria o restante, sem repetir os grupos existentes. O plano original é preservado.
Não há exclusões ou atualizações de grupos. Interrupções em lotes de atividades
ou ligações continuam bloqueadas para conferência separada.
