---
name: cpa
description: Commit, push e arquivar a sessão, em um passo. Use quando o Pet digitar "cpa" ou "/cpa", ou pedir "commit, push e arquiva". NÃO use para só commitar sem arquivar, nem para arquivar sem versionar.
---

# cpa: commit, push e arquivar

"cpa" já é o pedido do Pet para versionar. Não pergunte de novo se pode commitar.

1. **Commit.** Rode `git status`. Inclua só o que esta sessão mudou; arquivo alheio à sessão fica de
   fora, e você avisa. Respeite as regras do projeto sobre o que pode ir ao repositório (lista branca,
   segredos, pastas travadas). Mensagem no estilo do `git log` recente, com a linha de coautoria.
   Direto no `main`, sem branch nem PR (regra global de Git). Se não houver nada a commitar, diga isso
   e siga.
2. **Push.** `git push` para o remoto de sempre. Se falhar, pare e mostre o erro. Não arquive.
3. **Arquivar, se for o caso.** Arquive só se nada nesta sessão ainda depender do Pet (pergunta
   aberta, escolha, comando para ele rodar, peça para revisar). Se algo depender, não arquive e diga
   o quê em uma linha.
   - Antes de arquivar, renomeie a sessão para `🗄️ <o que foi feito>` (`set_session_title`,
     `"self"`). Renomeie mesmo que o nome já esteja com ✅: sessão arquivada leva 🗄️, não ✅.
   - Mande a mensagem final (🗄️, hash do commit e o que foi versionado) **antes** de chamar
     `archive_session` com `"self"`, porque a conversa termina com ele. As duas ferramentas vêm via
     ToolSearch.
   - **No Codex:** renomeie a conversa para `🗄️ <o que foi feito>` com a ferramenta de título dele.
     Se não houver ferramenta para arquivar, não arquive: termine com 🗄️ e diga ao Pet que a conversa
     pode ser arquivada.
