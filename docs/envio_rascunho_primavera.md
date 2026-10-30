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
