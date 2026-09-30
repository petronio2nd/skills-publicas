---
name: notas-fiscais-cpf
description: "Levanta as notas fiscais (NF-e e NFC-e) emitidas no CPF do Pet nos programas estaduais de nota fiscal cidadã e salva um CSV por estado, com a chave de acesso de cada nota. Estados: Goiás (Nota Fiscal Goiana), Acre (Nota Premiada Acreana) e Mato Grosso (Nota MT, extração ainda não mapeada). Usa o Claude in Chrome: o Pet faz o login, e a skill coleta e baixa. Use quando o Pet pedir 'minhas notas fiscais', 'notas no meu CPF', 'baixa as notas da Nota Goiana / Acreana / Nota MT', 'atualiza o CSV das notas', 'quanto gastei no ano', 'acha a nota da compra X' ou quiser a chave de acesso de uma compra. NÃO use para gerar DANFE/PDF sem o Pet pedir, nem para NF-e de outros estados (essas só saem pelo NFeDistribuicaoDFe, com certificado digital)."
---

# Notas fiscais no CPF

Cada estado só mostra as notas **emitidas lá** e **com o CPF informado na compra**. Não existe consulta nacional por CPF. A Receita e o e-CAC não listam notas; o Portal Nacional da NF-e só consulta uma nota por vez, pela chave. A lista completa de NF-e de todos os estados só sai pelo **NFeDistribuicaoDFe** da SEFAZ, com certificado digital do Pet. Isso fica fora desta skill.

Responda em português, com frases curtas.

## Regras

- **Login é sempre do Pet.** Abra a página e peça que ele entre. Nunca digite CPF nem senha, nem clique em "Entrar" com dados que ele digitou.
- **Não imprima** token, cookie nem o CPF. Os scripts leem o que precisam dentro da página e devolvem só o resumo.
- **Baixar o CSV é download.** Se o pedido do Pet já foi "baixa/salva o CSV", siga. Se ele pediu só para ver as notas, mostre o resumo e pergunte antes de baixar.
- A pasta de downloads do Chrome do Pet é **`D:\00-ENTRADA`**. Confira o arquivo lá depois de baixar.
- DANFE (PDF) só quando o Pet pedir.

## Passo a passo

1. **Carregar as ferramentas** do Claude in Chrome em uma chamada só: `tabs_context_mcp`, `tabs_create_mcp`, `navigate`, `javascript_tool`, `get_page_text`, `find`, `computer`, `read_network_requests`.
2. **Abrir** uma aba nova por estado pedido (tabela abaixo) e pedir o login: `▶️ entrar na aba X`. Espere o Pet avisar.
3. **Confirmar o login** com `get_page_text` (aparece o nome dele ou "Minhas Notas").
4. **Coletar:** leia o script do estado em `scripts\` com `Read` e passe o conteúdo, sem mudar nada, para o `javascript_tool` na aba do estado. O script guarda o CSV em `window.__notasCsv` na página e devolve o resumo.
5. **Baixar:** rode `scripts\baixar-csv.js` na mesma aba e confira o arquivo em `D:\00-ENTRADA`: `Get-Content <arquivo> -Encoding UTF8 -TotalCount 2`.
6. **Responder** com: arquivo salvo, quantidade de notas, tabela por ano (quantidade e valor) e as empresas de maior valor, se o Pet quiser.
7. **Fechar** as abas que você abriu, a menos que o Pet queira continuar nelas.

## Estados

| UF | Programa | Onde abrir | Script | Arquivo |
|---|---|---|---|---|
| GO | Nota Fiscal Goiana | `https://nfgoiana.economia.go.gov.br/nfg/cidadao/telaCidadao` → botão **Entrar** | `goias-coletar.js` | `notas-go-AAAA-MM-DD.csv` |
| AC | Nota Premiada Acreana | `https://notapremiadaacreana.ac.gov.br/login` → **Pessoa Física** | `acre-coletar.js` | `notas-ac-AAAA-MM-DD.csv` |
| MT | Nota MT | `https://www.sefaz.mt.gov.br/notamt/` → **Entrar** | ainda não existe | `notas-mt-AAAA-MM-DD.csv` |

### Goiás

- Sem API: o script abre o modal **"Consultar Minhas Notas em Detalhe"** e percorre as páginas (10 notas cada) clicando em "»".
- São ~50 páginas e o `javascript_tool` corta em 45 s. Por isso a coleta **roda em segundo plano** na página. O script só a inicia. Depois consulte `JSON.stringify(window.__coleta)` a cada ~20 s até `fase` ser `"pronto"` (o resumo vem em `resumo`) ou `"erro"` (motivo em `erro`). Não rode outra coisa na aba enquanto isso.
- Colunas: Data, Tipo, Número, CNPJ, Empresa, Nome fantasia, Valor, Pontos, Sorteio, Chave de acesso.
- Notas de 2015 a 2017 sem chave são cupons fiscais antigos (ECF). Não têm documento para baixar.
- A nota entra no portal até o último dia do mês seguinte ao da compra.
- DANFE: link `/nfg/cidadao/downloadNota/<chave>` em cada linha (não testado).

### Acre

- O portal tem API. O script usa o token da sessão (`localStorage.AccessToken`, um JWT) e o CPF do campo `sub` do token, e chama `https://notapremiadaacreanaapi.ac.gov.br/api/v1/user/historic-documents?page=N&per_page=100&cpfCnpjDestinatario=<cpf>`.
- A resposta traz `historicDocuments` com `chaveAcesso`, `cnpjCpfEmitente`, `nomeFantasia`, `dataEmissao`, `status` (AUTORIZADA ou CANCELADA), `valorTotal` e `tipoDocumento` (NFE ou NFCE).
- Colunas: Data, Tipo, Número (tirado da chave), CNPJ, Empresa, Valor, Status, Chave de acesso. Os totais do resumo não contam as canceladas.
- Se a API responder 401 ou 403, o login expirou: peça ao Pet para entrar de novo.
- DANFE: botão **"Baixar DANFE"** em cada linha de **Minhas Notas** (não testado).

### Mato Grosso (a mapear)

Em 30/09/2026 o login falhou três vezes no teste, e o mapeamento parou aí. O que já se sabe:

- O site é Angular 7. O login é `POST /notamt/api/autenticacao/login` (form-urlencoded `usuario=<cpf>&senha=<senha>`, **sem codificar**). Senha com `+`, `&`, `%`, `=` ou `#` chega errada ao servidor.
- A resposta `400` com "Não foi possível efetuar o login do usuário" é tratada pelo próprio site como **falha temporária** do servidor, não como senha errada.
- O endereço `www.nota.mt.gov.br` deu erro de certificado no Chrome. Use `www.sefaz.mt.gov.br/notamt/`.
- Alternativa quando o site falha: app **Nota MT** no celular (mostra as notas, mas não exporta).

**Quando o login funcionar:** ligue `read_network_requests` na aba, abra a tela de notas do usuário e veja qual chamada `/notamt/api/...` traz a lista. O token deve estar no `localStorage` ou no `sessionStorage` (veja só os **nomes** das chaves, não os valores). Escreva `scripts\mt-coletar.js` no mesmo molde do `acre-coletar.js`: grava `window.__notasCsv` e devolve só o resumo. Teste, atualize esta seção e a tabela de estados.

## Duplicadas

Antes de somar gastos, confira (com Python, lendo os CSVs com `encoding='utf-8-sig'` e `delimiter=';'`):

- **Mesma chave nos dois estados:** nota emitida em GO para entrega no AC aparece nos dois programas. Some uma vez só.
- **Mesma linha repetida** (CNPJ, número, data e valor iguais): importação dobrada do portal. Já apareceu em GO, num cupom sem chave.
- **Mesma empresa, data e valor, com números diferentes:**
  - NFC-e + NF-e: a loja emitiu o cupom e depois a nota da mesma compra. Provável gasto contado duas vezes; confirme com o Pet.
  - Uma autorizada + uma cancelada (AC): nota reemitida. Não é duplicada; os totais já ignoram as canceladas.

## Limites da ferramenta

- A saída do `javascript_tool` corta em ~1.000 caracteres. Por isso os scripts não devolvem o CSV: ele sai pelo download.
- A extensão bloqueia saída que pareça cookie, query string ou base64. Não tente contornar; resuma dentro da página.
