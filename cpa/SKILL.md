---
name: cpa
description: Commit, push e arquivar a sessão, em um passo, conferindo antes o que ficou pendente e cuidando do TickTick com inteligência (procurar antes de criar; atualizar, criar, adiar ou concluir tarefas e hábitos que a sessão tocou). Use quando o Pet digitar "cpa" ou "/cpa" (ou ainda "cpa backlog", que vale como "cpa"), ou pedir "commit, push e arquiva". Também roda só a gestão do TickTick (sem commit, push nem arquivar) quando o Pet disser "tik", "atu tik", "atualiza o tik" (sem a palavra "cpa"). NÃO use para só commitar sem arquivar, nem para arquivar sem versionar, nem para preparar retomada por outro agente (isso é a handoff-tik, que o cpa chama quando cabe).
---

# cpa: conferir, commit, push e arquivar

"cpa" já é o pedido do Pet para versionar. Não pergunte de novo se pode commitar.

## Modo só-tik

Se o Pet pedir "tik", "atu tik" ou "atualiza o tik": rode só o passo 1b (e o 4b, se a sessão
cumpriu hábito ou tarefa) sobre o que a sessão fez e o que rolou nela, incluindo o título da tarefa
quando mudou. Sem commit, push, mudança de título da sessão nem arquivamento. Mesmas regras e limites
do 1b; relate uma linha por tarefa. Se o Pet citar a tarefa, use essa; senão, procure pela sessão.

Desambiguação: a palavra "cpa" na mensagem é sempre o `cpa` completo (commit, push e arquivar), mesmo
com "tik" junto. Sem "cpa", é só-tik. Na dúvida real, não arquive: faça só o tik e pergunte se é para
fechar a sessão (arquivar é o passo que mais custa desfazer).

## 1. Conferir pendências (obrigatório, antes de tudo)

Releia a sessão e monte a lista do que ainda está aberto. Confira cada ponto:

- **Com o Pet:** releia a conversa e julgue se algo ainda depende dele: pergunta sem resposta, escolha,
  comando para ele rodar, mensagem para ele mandar, link para revisar, prazo. O título e a **Sua vez** são só pistas: podem estar
  velhos, e o próprio "cpa" pode ter respondido o que pediam (o OK do commit, por exemplo). Na dúvida,
  não arquive e diga o que viu.
- **Com outra pessoa (🤝):** algo espera resposta ou ação de alguém de fora?
- **Com você (⚙️):** agente, comando em segundo plano, workflow ou monitor ainda rodando; algo que você
  disse que ia fazer e não fez; `HANDOFF.md` do projeto a atualizar.
- **Para versionar:** mudança desta sessão em qualquer repositório tocado, não só no diretório da
  sessão (a pasta `diversos`, por exemplo, não é repositório; as edições podem estar em `skills`, `mds-sistema` etc.).

Botão de `spawn_task` não usado não é pendência: o trabalho seguinte já está em outra sessão.

Mostre o resultado em uma linha: "nada pendente" ou o que ficou. O commit e o push dos passos 2 e 3
acontecem de qualquer jeito; a lista decide só o passo 4.

## 1b. Gestão do TickTick

"cpa" é o único comando. Se o Pet digitar "cpa backlog" (ou "cpa e joga X no backlog"), trate como "cpa".
Para cada pendência da sessão e cada tarefa que ela tocou, **procure antes de criar** (`search_task`,
`filter_tasks`; nas listas 🎯 PRINCIPAL, 📅 COMPROMISSOS, 💡 BACKLOG, 👩 OUTRA PESSOA) e decida. A tarefa que a
sessão adotou ou criou na abertura (`CLAUDE.md` global, "TickTick como gerenciador de sessão") é a primeira candidata:

- **Atualizar** a tarefa existente (título, descrição, data, tag), quando for o mesmo assunto.
- **Criar** se não houver nenhuma.
- **Adiar** (mudar a data) quando a sessão mostrar que o prazo mudou.
- **Concluir** só se a sessão mostrar que foi cumprida (hábitos e tarefas do passo 4b).

Lista: com data → 🎯 PRINCIPAL; compromisso com hora marcada → 📅 COMPROMISSOS; sem prazo → 💡 BACKLOG;
de outra pessoa → 👩 OUTRA PESSOA. Valem as regras de "Backlog no TickTick" do `CLAUDE.md` global: tag de tema,
título no infinitivo com o objeto, fuso de Brasília (`America/Sao_Paulo`, `-0300`) e descrição que se
sustenta sozinha (onde, o quê, caminhos e números, conferências, quando está pronto).

Limites:
- **Nunca apague** tarefa.
- Duas tarefas parecidas e sem como saber qual é a certa: não adivinhe, não mexa e deixe a dúvida no relato.
- Pendência com outra pessoa (🤝) ou que o Pet vai fazer hoje não vira tarefa sem necessidade; o que vira
  tarefa deixa de prender a sessão (pode virar 🗄️).
- Se a pendência é **trabalho a retomar por outro agente** (precisa de histórico, modelo e esforço),
  chame a skill `handoff-tik` em vez de duplicar a lógica. As duas skills continuam separadas.
- Relate **uma linha por tarefa**: `criada|atualizada|adiada|concluída|sem mexer — <título> (<lista>)`.

## 2. Commit

Antes, se o diff a commitar tem código que ainda não passou pelo `/code-review` nesta sessão (ou mudou
depois dele), rode-o no diff, com o nível pelo risco e sem `--fix` (`dupla`, seção 0b). Corrija o que
se confirmar e rode os testes de novo. Achado que só o Pet decide segura o arquivamento (passo 4), não o
commit do resto. No OpenCode, o `/code-review` é a ponte do plugin gêmeo (`dupla`, seção 0b): roda igual.

Para cada repositório tocado nesta sessão, rode `git status`. Inclua só o que esta sessão mudou;
arquivo alheio à sessão fica de fora, e você avisa. Respeite as regras do projeto sobre o que pode ir
ao repositório (lista branca, segredos, pastas travadas, validação antes do commit). Mensagem no estilo
do `git log` recente, com a linha de coautoria. Direto no `main`, sem branch nem PR (regra global de
Git). **Exceção: `origin` em `github.com/<ORG>/*`:** o commit vai na branch de trabalho, nunca em `main`
ou `develop`; sem branch, crie uma a partir da base do repositório. PR só com pedido do Pet, e `cpa` não é
esse pedido. Se não houver nada a commitar, diga isso e siga.

**Arquivo sem dono:** no mesmo `git status`, veja o que está alterado ou novo, fora desta sessão e com
data de modificação de mais de 7 dias. Crie ou atualize uma tarefa em 💡 BACKLOG por repositório, com os
caminhos e as datas (procure antes de criar, como no passo 1b). Não commite, não apague nem restaure esses
arquivos. Isso não prende a sessão.

## 3. Push

`git push` para o remoto de sempre; nesse caso, só da branch de trabalho. Se falhar, pare e mostre o erro.
Não arquive.

## 4. Título e arquivamento

Sempre deixe o título certo no fim (`set_session_title`, `"self"`), com as regras de emoji do
`CLAUDE.md` global:

- **Nada pendente:** renomeie para `🗄️ <o que foi feito>`, mesmo que já esteja com ✅ (sessão
  arquivada leva 🗄️). Se a sessão estiver fixada (era 🔥), desafixe com `set_pinned` antes:
  `archive_session` recusa sessão fixada. Marque no TickTick o que a sessão concluiu (passo 4b). Mande
  a mensagem final (🗄️, hash de cada commit, o que foi versionado e o que foi marcado no TickTick)
  **antes** de chamar `archive_session` com `"self"`, porque a conversa termina com ele.
- **Pendente com o Pet:** não arquive. Título com o emoji da primeira pendência, pelas regras do
  `CLAUDE.md` global, e mensagem final com **Sua vez**.
- **Pendente com outra pessoa:** não arquive. Título `🤝 <nome> <dd/mm>: <o quê>`, com o dia em que
  passou para ela, se for conhecido.
- **Trabalho seu ainda rodando:** não arquive. Título com ⚙️; rode o `cpa` de novo quando terminar.

As ferramentas (`set_session_title`, `set_pinned`, `archive_session`) vêm via ToolSearch. No OpenCode,
`/cpa` é um comando do plugin gêmeo que chama esta skill, e as três ferramentas existem com os mesmos
nomes pelo plugin: arquivar é o mesmo `archive_session("self")`.

## 4b. Marcar como concluído no TickTick

Só no caso **nada pendente**: o `cpa` do Pet diz que ele fez a parte dele (leu, conferiu). O que a
sessão concluiu fica concluído **hoje** no TickTick, sem perguntar (Pet, 22/10/2026).

**Hábitos.** Se a sessão cumpriu um hábito da tabela, faça o check-in do dia:

| Sessão | Hábito | id |
|---|---|---|
| <tarefa que o usuário cumpre> | <nome do hábito> | `<id do hábito>` |

- Dia = hoje em Brasília (`AAAAMMDD`), `client_timezone: "America/Sao_Paulo"`, como as tarefas do
  TickTick (regra do `CLAUDE.md` global), mesmo em projeto que usa o horário do Acre.
- Confira antes com `get_habit_checkins` (de hoje a hoje); se já tem `status: 2`, não mexa.
- Marque com `upsert_habit_checkins`: `stamp` de hoje, `status: 2`, `value: 1`, `goal: 1`.
- Fora de dia do hábito (DOE AC no sábado, por exemplo), não marque.
- Hábito que é ação do próprio Pet fica fora da tabela e nunca é marcado: os hábitos pessoais do usuário. Linha nova na tabela só
  quando o Pet pedir.

**Tarefas.** Se a sessão nasceu de uma tarefa do TickTick (o prompt traz o link ou o id) ou fez
exatamente o que o título de uma tarefa aberta diz, conclua-a com `complete_task` (`project_id` sai
do link, `#p/<project_id>/tasks/<task_id>`). Tarefa parecida mas não idêntica, ou feita só em parte,
não conclua: a mensagem final oferece "👍 concluir <título> no TickTick?". Tarefa recorrente
(DOE, ponto) não se conclui por aqui.

Diga na mensagem final, em uma linha, o que foi marcado (hábito e dia, ou título da tarefa), ou
"nada a marcar no TickTick". Ferramentas do conector TickTick via ToolSearch
(`get_habit_checkins`, `upsert_habit_checkins`, `search_task`, `complete_task`); no OpenCode, as mesmas
pelo MCP `ticktick`. Sem o conector, diga o que o Pet deve marcar.

**Sem ferramenta de arquivar** (harness ou cliente sem o plugin gêmeo): faça a mesma conferência e
renomeie a conversa com a ferramenta de título que houver. Não arquive: termine com 🗄️ e diga ao Pet
que a conversa pode ser arquivada.
