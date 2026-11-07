---
name: iniciar-analise
description: Inicia, retoma ou migra análises documentais longas pelo molde de checkpoints e evidências. Use para novo caso, análise aprofundada de processo ou pasta de documentos, retomada e migração metodológica. Não use para leitura pontual nem conversão de arquivo.
---

# Iniciar análise documental

Esta skill é o procedimento de entrada. O método vive nos arquivos do caso e do molde;
se houver divergência, esses arquivos vencem.

- Molde mestre: `D:\20-VIDAIA\00-REPOS\modelo-atual`
- Script: `<molde>\bin\novo-caso.py`

## Antes de agir

Identifique o ambiente e leia **somente uma** referência:

- Codex Desktop ou CLI: [references/codex.md](references/codex.md)
- Claude Code ou Cowork: [references/claude-code.md](references/claude-code.md)

Em outro ambiente, siga o fluxo comum abaixo sem inventar comandos de barra.

## Escolher o cenário

| Sinal | Ação |
|---|---|
| A pasta do caso não existe ou não contém `AI-CONTEXT/` | Criar um caso. |
| A pasta já contém `AI-CONTEXT/` | Retomar em tarefa/sessão nova. |
| O usuário pede o método novo em caso antigo | Simular a migração; aplicar somente após aprovação. |

### Retomar

1. Leia `AI-CONTEXT/handoff/CURRENT.md` e depois o `CURRENT.md` do projeto ativo.
2. Leia adiante apenas os arquivos que esses dois apontarem por nome.
3. Não abra o `MANIFEST.md`, o plano ou as fontes brutas para “se situar”. Consulte
   primeiro `SOURCE_MAP.md`, `FACTS/`, `FINDINGS.md` e `HYPOTHESES.md` quando forem
   indicados.
4. Se os dois checkpoints não bastarem, corrija o contrato de retomada antes de ampliar
   a leitura. Não recrie a estrutura.

## Criar um caso

Colete de uma vez apenas o que faltar: identificador, pasta do caso, objetivo, pergunta
central, produto final, pasta das fontes e prazo, se houver. Aceite campos incompletos;
o script registra `[nao informado - preencher]`. Nunca invente identificador, objetivo,
documento ou conclusão.

Execute sem continuação específica de shell:

```text
python "D:\20-VIDAIA\00-REPOS\modelo-atual\bin\novo-caso.py" novo --destino "<pasta>" --id "<id>" --objetivo "<objetivo>" --pergunta "<pergunta>" --produto "<produto>" --fontes "<fontes>" --prazo "<prazo opcional>"
```

O script cria a cópia autossuficiente, instancia `_TEMPLATE-SEI`, configura o handoff,
registra proveniência e preserva arquivos que já existam. Não replique esses passos à
mão. Se o script recusar, leia a mensagem e escolha criação, retomada ou migração.

### Inventário inicial — somente em caso recém-criado

1. Trabalhe dentro da pasta do caso, nunca no molde.
2. Leia `START-HERE.md` e `AI-CONTEXT/OPERATING_RULES.md` uma única vez para o primeiro
   inventário; não os releia em retomadas.
3. Liste as fontes sem leitura integral indiscriminada e registre um `SRC-NNN` por
   arquivo no `MANIFEST.md`.
4. Marque duplicidades, ilegíveis, PDFs sem texto pesquisável e lacunas.
5. Complete o plano, registre a cobertura e reescreva o `CURRENT.md`.
6. Entregue resumo curto: objetivo, fontes, etapas, riscos e dados faltantes.

Mantenha saídas volumosas fora da conversa principal. Delegue varredura, OCR, extração,
hashes ou logs a subagente somente quando ele estiver disponível e autorizado; caso
contrário, processe em streaming ou salve a saída bruta em arquivo e traga apenas o
veredito rastreável.

## Migrar um caso antigo

Nunca atualize automaticamente. Primeiro execute apenas a simulação:

```text
python "D:\20-VIDAIA\00-REPOS\modelo-atual\bin\novo-caso.py" migrar --caso "<pasta do caso>"
```

Mostre as diferenças e aguarde aprovação expressa. Só então repita com `--aplicar`.
A migração faz backup, registra a proveniência e não deve sobrescrever dados do projeto.
Revise separadamente `AGENTS.md` e `CLAUDE.md` quando o caso contiver regras próprias.

## Contrato de retomada

Reescreva o `CURRENT.md`; não empilhe entradas. Teto rígido: 2 KB.

Ele contém somente: objetivo da fatia em uma frase; estado em 3 a 5 bullets; próximo
passo único; critério de aceite; e no máximo seis referências relevantes agora. Trechos,
citações, tentativas, raciocínio e histórico ficam nos arquivos próprios e checkpoints.

Antes de pausar, compactar, trocar de ambiente ou encerrar:

1. reescreva o `CURRENT.md`;
2. registre cobertura em `STATUS.md` e decisões travadas em `DECISIONS.md`;
3. encerre ou compacte conforme a referência do ambiente.

## Limites

- Preserve documentos originais e não use links simbólicos para fontes.
- Diferencie fato, hipótese, achado, decisão e pendência.
- Não apague hipótese rejeitada nem esconda evidência contrária.
- Não releia fonte já representada por evidência suficiente.
- Não instale MCP para instrumentar o próprio consumo; use script local sob demanda.
- Durante uma análise, não altere o molde mestre.
