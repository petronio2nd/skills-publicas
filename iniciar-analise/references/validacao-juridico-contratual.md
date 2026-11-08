# Validação do roteiro jurídico/contratual — 01/11/2026

## O que foi exercitado

Dois cenários fictícios em `../evals/`, uma execução por cenário com a versão
anterior da skill e outra com a referência nova: quatro respostas no total.

| Cenário | Critério principal | Com roteiro | Versão anterior |
|---|---|---|---|
| Atos judiciais distintos | Sentença modificada, envio sem cumprimento, recurso separado, pedido sem julgamento e prazo não calculável | Passou | Passou |
| Contrato/anexo ausente | Instrumento/aditivo/minuta distintos, aceite não demonstrado e cláusula de prazo condicionada | Passou | Passou |

Resultados avaliados pela autora, lendo as quatro respostas e seus limites.
O roteiro novo detalhou cobertura e contrapontos, mas os critérios objetivos
também passaram na versão anterior: **nenhum ganho de qualidade foi demonstrado**.
Enunciados pequenos e explícitos; não testam busca, recuperação, arquivos extensos
ou comportamento com material hostil. Uma execução não estima variabilidade.
Tokens e duração não foram retornados pelo harness; não foram inventados.

## Revisão e correções

L1 de outra família (Claude Fable xhigh solicitado, modelo real não informado;
reserva após Gemini indisponível) aprovada com correções. Tratados:
- Regra específica de uma plataforma substituída por remissão às regras do caso.
- Espaços em prompts/critérios restaurados.
- Referência de ambiente diferenciada da referência de domínio.
- Configuração dos testes restrita a leitura, sem criação de caso.
- Inferências vedadas e pares conceituais explicitados.
- Termo indefinido trocado por exemplo concreto de PDF com várias peças.

As quatro execuções comportamentais antecedem essas correções pontuais. Depois,
frontmatter, schema dos casos/graders, ferramentas de leitura, referência e nome
da skill foram conferidos; `git diff --check` passou. Não houve nova execução
comportamental nem revisão independente das quatro saídas. Não apresentar os
testes como comprovação empírica de cada instrução da versão final.

## Limites e próximo uso

O piloto processual orienta os controles de leitura, mas não valida qualidade
universal nem substitui revisão jurídica profissional. A modalidade contratual
foi exercitada apenas com material fictício: validar no contrato concreto antes
de alegar utilidade prática. Manter sem automação de prazos, protocolos ou envio.

Ao avaliar novo caso, priorizar tarefas menos guiadas, fonte contrária, aditivo
parcial, condição ausente e procedimentos relacionados; não repetir estes dois
cenários para prometer ganho que a comparação não mostrou.
