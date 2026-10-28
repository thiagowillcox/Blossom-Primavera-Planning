# Diagnóstico e correções — referência Wardi v0001

## Causas comprovadas

1. **Entradas diferentes.** As duas planilhas reenviadas são idênticas às entradas antigas: LD SHA-256 `460cc1d3059c68d8e84f3a0e4f2abc009ad6ab5435160736b231c194d1cfd5e8`; manual `cbd1da49a5afb5f33baac8b32cb377f38ffaf6ff2d3deab5db4181515d1671ac`. O v0001 registra LD `e2937ed7362ee0edbad9d37bccf3bb1d0d188cd1483772517673106b67d80259` e manual `f403e6f9349a8a13ae1e1b74053da9968dc12ae7270fd38778abc91e73e431f6`. Não se pode corrigir a diferença de 292,15 HH simplesmente mudando percentuais: ambos já aplicam 80/10/20/10 aos seus próprios dados.
2. **Método de duração diferente.** Todas as 526 etapas produtivas/auxiliares do v0001 seguem HH/jornada; as 426 etapas do cliente usam três dias. O motor original usa máximo por função/capacidade, deixando campos pendentes na ausência de capacidade. Os métodos não são equivalentes; HH/jornada foi identificado explicitamente como equivalente homem-dia.
3. **Regras e rede diferentes.** O v0001 tem 219 relações obrigatórias adicionais, além de 52 condicionais e cinco referências inativas. O motor original não dispõe da extração/revisão de regras feita pelo Wardi. Não foi inventado um extrator equivalente nem copiados vínculos por nome aproximado para uma LD nova.
4. **O escalonador FS não explica a divergência por si só.** Alimentado com as durações e os 858 vínculos ativos do v0001, o escalonador existente reproduziu os 1.904 valores de início/fim das 952 atividades dentro de tolerância 1e-8. Não foi alterado um algoritmo que passou nessa conferência.
5. **Representação e dados da LD.** Há nomes e classificações alterados no próprio material de referência. Não foram renomeados ou redistribuídos documentos da LD antiga para simular outra entrada.

## Problemas corrigidos no código

- `ld.py`: cabeçalhos de funções com fórmulas agora usam o cache ou referências diretas a células locais. Fórmula sem valor disponível é rejeitada, não tratada como nome de profissão. Macros e fórmulas arbitrárias não são executadas.
- `ld.py`: identificação de código/EAP/nome/unidade por fórmulas usa valores resolvidos quando disponíveis.
- `ld.py`: colunas de valores financeiros deixam de ser tratadas como fator/total de ajuste de HH; o layout de ajustes é reconhecido pelo cabeçalho. Dados originais continuam preservados.
- `ld.py` e `wbs.py`: leitura e parentesco de códigos com mais de dois níveis; `3.1.2` e `3.1.0` ficam sob `3.1`.
- `duration.py`, `hours.py` e `validation.py`: método de duração explícito, validação dos métodos e campo `base_duracao`. Modo padrão por capacidade preservado; opção HH/jornada sinalizada como esforço equivalente.
- `provenance.py`: perfil de referência verifica hashes antes de processar e recusa arquivos diferentes.
- `reference.py`: novo modo de reprocessamento de uma exportação auditada. Recalcula esforços, durações, atribuições, auditoria e dias relativos a partir dos caches/parametrização/rede importados. Não usa os resultados HH/duração/data existentes como valores de cálculo.
- `app.py`: escolha explícita do modo, upload opcional do cronograma e download da referência reprocessada/relatório de diferenças. Mudança de fontes ou perfil invalida resultados anteriores.

## Como usar os recursos disponíveis

Na interface:

1. Em Arquivos, abra **Referência Wardi (opcional)** e envie `pre_cronograma_v0001.xlsx`.
2. Em Configuração, escolha **Reprocessar referência Wardi**.
3. Clique **Reprocessar referência** e baixe o Excel e a conferência em Resultados.

Este modo usa a referência como fonte de planejamento: importa sua estrutura, IDs, regras, restrições, metadados e rede; recalcula os resultados quantitativos a partir da auditoria preservada. Não é geração de uma LD nova, não substitui silenciosamente as horas da LD comercial e não demonstra reprodução do software do Wardi para outros projetos.

O perfil **Referência Wardi v0001 (parcial)** é diferente: configura HH/jornada e prazos conhecidos para geração pela LD, mas exige as entradas de hash correto. Como as entradas exatas não estão disponíveis, essa via é bloqueada. Ela não contém as regras completas do motor do Wardi.

## Evidências

- **37 testes passaram**, sem skips nesta sessão com os anexos disponíveis.
- A conferência completa do reprocessamento comparou valores de todas as células das nove abas com o v0001: nenhuma diferença textual ou numérica acima de 1e-8; formatação/bytes ZIP não são critério de igualdade de dados.
- Resultado recalculado: 952 atividades, 14.907,50 HH planejadas, 858 vínculos ativos e os 915 relacionamentos preservados no arquivo.
- Teste de não cópia: HH, duração, início e fim foram intencionalmente corrompidos no arquivo de entrada de teste; o reprocessador os refez corretamente a partir do cache e da rede.
- Rejeitados cache incompleto, vínculos órfãos, funções sem mapeamento, rateio fracionário e restrições de início sem política suportada. O programa não tenta adivinhar esses casos.
- Testes de navegação e reprocessamento pelo site aprovados.
- Com a LD antiga, os totais continuam os correspondentes àquela LD. Não foi feito ajuste artificial para chegar ao total do Wardi.

Os arquivos comerciais não foram adicionados ao Git. Para executar testes dependentes da referência em outra máquina, coloque o v0001 em `input/pre_cronograma_v0001.xlsx`; sem ele, esses testes ficam explicitamente skipped.

## O que permanece pendente

Reproduzir o motor de geração do Wardi para **novas LDs**, incluindo suas políticas de rateio, escopo por ativo, OCR/regras completas e escolha de vínculos, não foi demonstrado. Com os recursos disponíveis, o que está validado é o reprocessamento do cronograma de referência e as correções independentes do leitor. Igualdade neste exemplo não comprova equivalência geral dos dois sistemas.
