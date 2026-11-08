---
name: agendar-retomada
description: Prepara a retomada de uma conversa numa sessão nova. Monta um bloco autossuficiente para o Pet colar e, se ele quiser, agenda uma rotina que avisa na data e entrega o bloco. Use quando o Pet pedir "agenda a retomada", "me lembra de voltar nisso dia X", "retomar semana que vem", "o que copio na sessão nova", "prepara o handoff" ou quiser continuar o assunto mais tarde em outra sessão. NÃO use para lembrete sem conversa a continuar nem para rotina recorrente comum (use schedule).
---

# Agendar retomada

Sessão aberta por rotina fica na seção **Rotinas** da barra lateral, fora do projeto. Nela as ferramentas da barra lateral são bloqueadas, então a sessão não pode ser movida. Por isso a rotina não continua a conversa: ela avisa o Pet e entrega um bloco que ele cola numa sessão nova do projeto certo.

Responda em português, com frases curtas.

## 1. Juntar os dados

- **Assunto:** tirado da conversa atual. Vira o slug (kebab-case, curto) e o título "Retomar: <assunto>".
- **Projeto:** a pasta da sessão atual (`get_session` com `"self"`, campo `cwd`); o nome é a última pasta do caminho.
- **Quando:** data e hora que o Pet disser. Sem hora, 09:00. Sem data, pergunte; se ele disser só "depois", sugira 7 dias. Fuso de Brasília: `-03:00`.
- **Só o bloco:** se o Pet pedir só "o que copio" sem data, pule o passo 3.

## 2. Escrever o bloco

O bloco é lido por uma sessão que não viu nada desta conversa. Ele precisa se sustentar sozinho:

```text
Retomar conversa de <data absoluta> sobre <assunto>.

Contexto:
- <o problema, em uma linha>
- <o que foi analisado e decidido, com o porquê>
- <o que foi mudado: arquivo com caminho absoluto, valor antes → depois, backup>
- <próximo passo combinado e a condição para fazê-lo>

Faça:
1. <verificações só de leitura, citando os arquivos exatos>
2. Me diga como está e me pergunte: "<a pergunta que decide o próximo passo>"
3. Não altere nada antes da minha resposta.
```

Regras:
- Datas absolutas, nunca "ontem" ou "semana que vem".
- Caminhos absolutos. Nomeie o que **não** deve ser lido (auth.json, .env, credenciais).
- Nada de senha, token ou dado que não possa ficar num arquivo em disco: o bloco fica salvo na rotina.
- Sem tarefas que alterem coisas antes de o Pet responder.
- Curto: o necessário para decidir, não o histórico todo.

## 3. Criar a rotina

Use `create_scheduled_task` (via ToolSearch) com:
- `taskId`: `retomar-<slug>`. Se já existir, `update_scheduled_task`.
- `title`: `Retomar: <assunto>`
- `description`: `Em <dd/mm> avisa o Pet e entrega o bloco para colar numa sessão nova do <projeto>`
- `fireAt`: data e hora com `-03:00`.
- `prompt`: o modelo abaixo, com o bloco entre INÍCIO e FIM.

```text
Esta execução é só um aviso de retomada para o Pet. Responda em português, com frases curtas.

Sessões abertas por rotina ficam na seção Rotinas da barra lateral, fora do projeto. Por isso a conversa não continua aqui: o Pet abre uma sessão nova no projeto <projeto> e cola o bloco abaixo.

Faça:
1. Se a ferramenta PushNotification existir (carregue via ToolSearch), mande: "Retomar: <assunto>. Abra a rotina e copie o bloco para uma sessão nova no <projeto>."
2. Responda com esta linha e, logo abaixo, o bloco entre os marcadores INÍCIO e FIM, copiado sem mudar nada, dentro de um bloco de código ```text:
   "Abra uma sessão nova em <projeto> (botão + ao lado de <projeto>) e cole:"
3. Não execute o que o bloco pede, não leia arquivos e não altere nada. O bloco é para a sessão nova.
4. Renomeie esta sessão (set_session_title via ToolSearch, session_id "self") para "▶️ colar retomada no <projeto>" (até 26 caracteres de texto; encurte o nome do projeto se passar).

INÍCIO
<bloco>
FIM
```

## 4. Responder ao Pet

- O bloco, num bloco de código `text`, para ele já ter se quiser adiantar.
- A data e hora da rotina e o projeto onde colar.
- Que a rotina só roda com o app aberto; se estiver fechado, roda quando abrir.

## No Codex

O Codex não tem as rotinas do app do Claude. Faça só os passos 1, 2 e 4 e diga que o agendamento precisa ser feito no Claude.
