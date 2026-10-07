---
name: cpa
description: Commit, push e arquivar a sessão, em um passo, conferindo antes se nada ficou pendente. Use quando o Pet digitar "cpa" ou "/cpa", ou pedir "commit, push e arquiva". NÃO use para só commitar sem arquivar, nem para arquivar sem versionar.
---

# cpa: conferir, commit, push e arquivar

"cpa" já é o pedido do Pet para versionar. Não pergunte de novo se pode commitar.

## 1. Conferir pendências (obrigatório, antes de tudo)

Releia a sessão e monte a lista do que ainda está aberto. Confira cada ponto:

- **Com o Pet:** a última resposta tem **Sua vez**? Há pergunta sem resposta, escolha, comando para ele
  rodar, link para revisar ou prazo? O título atual começa com 🔥 👍 ▶️ 📖 🧠?
- **Com outra pessoa (🤝):** algo espera resposta ou ação de alguém de fora?
- **Com você (⚙️):** agente, comando em segundo plano, workflow ou monitor ainda rodando; algo que você
  disse que ia fazer e não fez; `HANDOFF.md` do projeto a atualizar.
- **Para versionar:** mudança desta sessão em qualquer repositório tocado, não só no diretório da
  sessão (a pasta `diversos`, por exemplo, não é repositório; as edições podem estar em `skills`, `mds-sistema` etc.).

Botão de `spawn_task` não usado não é pendência: o trabalho seguinte já está em outra sessão.

Mostre o resultado em uma linha: "nada pendente" ou o que ficou. O commit e o push dos passos 2 e 3
acontecem de qualquer jeito; a lista decide só o passo 4.

## 2. Commit

Para cada repositório tocado nesta sessão, rode `git status`. Inclua só o que esta sessão mudou;
arquivo alheio à sessão fica de fora, e você avisa. Respeite as regras do projeto sobre o que pode ir
ao repositório (lista branca, segredos, pastas travadas, validação antes do commit). Mensagem no estilo
do `git log` recente, com a linha de coautoria. Direto no `main`, sem branch nem PR (regra global de
Git). Se não houver nada a commitar, diga isso e siga.

## 3. Push

`git push` para o remoto de sempre. Se falhar, pare e mostre o erro. Não arquive.

## 4. Título e arquivamento

Sempre deixe o título certo no fim (`set_session_title`, `"self"`), com as regras de emoji do
`CLAUDE.md` global:

- **Nada pendente:** renomeie para `🗄️ <o que foi feito>`, mesmo que já esteja com ✅ (sessão
  arquivada leva 🗄️). Se a sessão estiver fixada (era 🔥), desafixe com `set_pinned` antes:
  `archive_session` recusa sessão fixada. Mande a mensagem final (🗄️, hash de cada commit e o que foi
  versionado) **antes** de chamar `archive_session` com `"self"`, porque a conversa termina com ele.
- **Pendente com o Pet:** não arquive. Título com o emoji da primeira pendência (🔥 👍 ▶️ 📖 🧠) e
  mensagem final com **Sua vez**.
- **Pendente com outra pessoa:** não arquive. Título `🤝 <nome>: <o quê>`.
- **Trabalho seu ainda rodando:** não arquive. Título com ⚙️; rode o `cpa` de novo quando terminar.

As ferramentas (`set_session_title`, `set_pinned`, `archive_session`) vêm via ToolSearch.

**No Codex:** faça a mesma conferência e renomeie a conversa com a ferramenta de título dele. Se não
houver ferramenta para arquivar, não arquive: termine com 🗄️ e diga ao Pet que a conversa pode ser
arquivada.
