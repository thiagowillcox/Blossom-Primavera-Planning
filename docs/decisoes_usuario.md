# Decisões do usuário durante a geração

Na página Configuração, a LD é conferida antes da geração. Quando há códigos
WBS repetidos, o site mostra os nomes e as posições dos grupos envolvidos.
O usuário define códigos exclusivos e confirma em **Confirmar códigos e continuar**.
Depois, **Gerar pré-cronograma** fica disponível.

Nenhuma opção é aplicada automaticamente. Pode-se manter o código de um grupo
e mudar o outro, ou alterar ambos. O novo código precisa ter um pai existente
e não pode repetir outro código da LD. O sistema não deduz alterações nos filhos:
se uma mudança exigir outros ajustes hierárquicos, ela é bloqueada com uma mensagem.
Esta versão não oferece fusão/exclusão de grupos, pois isso pode mudar o escopo.

A planilha original não é modificada. As decisões são vinculadas ao SHA-256
do arquivo da LD e permanecem na sessão ao navegar. Outra LD ou revisão não
herda as escolhas. Para guardar as escolhas fora da sessão, use **Salvar decisões
desta LD**; esse JSON pode ser colocado em `ajustes_wbs` no arquivo de parâmetros
da execução pela linha de comando. A importação desse JSON pela interface ainda
não está disponível.

No Excel gerado:

- `WBS` apresenta o código aplicado e, para grupos alterados, `codigo_original`
  e `decisao_usuario`.
- `Parametros` preserva `ajustes_wbs`, incluindo o hash e os códigos por origem.
- `Pendencias` registra `DECISAO_WBS_APLICADA` com origem e código antes/depois.
- Documentos e atividades seguem a WBS escolhida, preservando as horas por função.

Exemplo de configuração (o hash deve ser o do arquivo efetivamente utilizado):

```json
{
  "ajustes_wbs": {
    "ld_sha256": "SHA-256 da LD",
    "codigos_por_origem": {
      "LD!B633:D633": "4.5"
    }
  }
}
```

Este fluxo resolve a ambiguidade de códigos WBS duplicados por escolha explícita.
Outros tipos de pendência continuam com as regras de segurança existentes;
não são preenchidos com valores presumidos. As regras do manual ainda exigem
revisão técnica e essa escolha não equivale à aprovação dessas regras.
