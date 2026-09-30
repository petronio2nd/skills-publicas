---
name: "banco-inter-money"
description: "Converte e corrige extratos e faturas de QUALQUER banco (Banco Inter, Banco do Brasil, Caixa, Nubank etc.: OFX exportado, fatura PDF, CSV de cartão ou print do app) para OFX compatível com MS Money (última versão), já com o payee certo de cada transação (dicionário payees.csv, que casa com os payees e categorias do Money), e ajuda a diagnosticar/corrigir problemas de importação (saldo que não fecha, transações sumidas, duplicadas). Use sempre que o usuário enviar um .ofx, .csv ou PDF de extrato/fatura de qualquer banco, ou pedir para converter, corrigir, importar no Money, gerar OFX, acertar payee/categoria, ou resolver \"saldo não bate\"/\"transação sumiu\"/\"duplicou\" no MS Money. Use mesmo sem a palavra \"skill\" — basta haver um arquivo/print de banco e intenção de gerar/corrigir OFX ou acertar o registro do Money."
---

# Extratos de qualquer banco → MS Money

O nome da skill ficou `banco-inter-money` porque ela nasceu com o Inter, mas vale para todos os bancos. Converte e corrige arquivos/dados de banco (extrato OFX, fatura PDF, CSV de cartão, ou print do app) para OFX compatível com MS Money, põe o payee certo em cada transação (seção **Payees**) e ajuda a fechar o saldo depois da importação.

## Tipos de entrada

| Entrada | O que fazer | Por quê |
|---|---|---|
| **PDF de fatura de cartão** | Extrair transações do texto e montar OFX do zero (Caminho 2; o algoritmo foi escrito para o layout do Inter: em outro banco, adaptar a detecção de linha) | Inter não exporta OFX de fatura de cartão, só de conta corrente |
| **.ofx exportado pelo Inter (extrato conta corrente)** | Caminho 1: `aplicar_payees.py` corrige as datas e troca a `<NAME>` | O Money rejeita o OFX original por formatação |
| **.ofx de outro banco (BB, Caixa, Nubank…)** | Caminho 1, igual ao Inter (a checagem do cabeçalho está lá) | Cada banco erra num ponto diferente; o script só mexe no que precisa |
| **.ofx do Banco do Brasil (conta corrente)** | Não mexer em data nem cabeçalho; só aplicar os payees (seção **Payees**) | O OFX do BB já vem com fuso nas datas e sem `<NAME>`; o Money aceita como está, mas o payee sai do MEMO, com data e hora ("Pix - Enviado - 21/09 14:30 …"), e cada Pix vira um payee novo |
| **.csv de cartão ou conta (qualquer banco)** | Ler CSV (conferir as colunas do banco), ajustar sinal caso a caso (ver seção de sinal abaixo), montar OFX do zero | O Inter às vezes exporta CSV com convenção de sinal diferente da do OFX, e ISSO VARIA por exportação — não assumir sem checar |
| **Print/lista colada do app (sem arquivo)** | Extrair transações do texto/imagem, perguntar ACCTID e confirmar totais antes de gerar | Risco de erro de leitura; sempre validar soma contra o total informado pelo usuário antes de entregar o arquivo |

## Contexto do problema (por que o Money rejeita)

O MS Money rejeita OFX exportado diretamente pelo Inter por dois motivos:
1. Datas sem fuso horário (`20260415` em vez de `20260415120000[-3:BRT]`)
2. Tag `<NAME>` do Inter (por isso o Caminho 1 remove a original)

**`<NAME>` em si funciona**: em 29/09/2026 o Money aceitou um OFX do BB com `<NAME>` curto (até 32 caracteres, sem `&`, `<`, `>`) antes do `<MEMO>`, e usou como payee. O que o Money recusava no Inter provavelmente era o conteúdo da tag, não a tag (causa não isolada, as duas correções foram feitas juntas). Por isso: remover a `<NAME>` que vem do banco e pôr a nossa, do `payees.csv`.

## Caminho 1 — Corrigir extrato OFX existente (qualquer banco)

Quando o usuário envia um `.ofx` exportado pelo banco, **não reconstruir do zero**. Rodar `aplicar_payees.py` (seção **Payees**), que preserva o resto do arquivo e faz as correções pontuais:
- datas sem fuso (`<DTxxx>` com 8 dígitos, com ou sem tag de fechamento) ganham `120000[-3:BRT]`;
- a `<NAME>` do banco sai, e o texto dela vai para o começo do `<MEMO>` (ou vira o MEMO, se não houver);
- cada transação ganha a nossa `<NAME>` com o payee.

Antes de rodar, conferir no arquivo do banco novo:
- **Seção**: tem de ser `BANKMSGSRSV1`. Se vier `CREDITCARDMSGSRSV1` (fatura de cartão), o Money recusa: trocar por `BANKMSGSRSV1`/`STMTTRNRS`/`STMTRS`/`BANKACCTFROM` com `ACCTTYPE` `CREDITLINE`, como no modelo do Caminho 2.
- **Encoding**: o script lê e grava em `latin-1`. Se o arquivo vier em UTF-8 (acentos viram `Ã©` no Money), converter para latin-1 e ajustar `CHARSET:1252` no cabeçalho.
- **Sinal**: débito negativo, crédito positivo. Conferir uma compra e um crédito conhecidos.

Reportar ao usuário: quantas datas foram corrigidas, quantas transações, quantas ficaram sem payee (o script imprime).

**Atenção a períodos sobrepostos**: se o usuário já importou um extrato de um período e agora manda outro que se sobrepõe, avisar que pode haver duplicação.


## Payees — o nome certo em cada transação

O OFX **não tem campo de categoria**. O Money escolhe a categoria pelo payee: se o `<NAME>` for **exatamente** o nome de um payee que já existe no Money, a categoria padrão dele vem junto. Payee novo entra sem categoria, e o Pet escolhe uma vez no Money; depois o Money repete.

Tudo fica em `D:\20-VIDAIA\00-CODIGOS\ofx-money\`:
- `payees.csv` (UTF-8, `;`): `padrao;valor;payee;categoria;nota`. `padrao` é regex sobre o texto da `<NAME>` do banco + MEMO; `valor` (opcional) restringe pelo `TRNAMT` exato; `payee` é o nome como está no Money (até 32 caracteres); `categoria` é só referência, para dizer ao Pet o que escolher quando o payee é novo.
- `aplicar_payees.py entrada.ofx` gera `entrada-name.ofx` ao lado: corrige datas sem fuso, acrescenta `<NAME>` antes de cada `<MEMO>` (a `<NAME>` do banco vai para o começo do MEMO) e não toca no resto do arquivo. `--memo` gera `entrada-memo.ofx` com o payee no próprio MEMO: fallback se algum dia o Money recusar `<NAME>`. **Vale para toda entrada**: o último passo de qualquer caminho (OFX corrigido, PDF, CSV, print) é rodar `aplicar_payees.py` no OFX gerado, e o arquivo entregue é o `-name.ofx`.

Regras:
1. **Loja, assinatura, conta, tarifa**: tem que casar com um payee existente do Money, porque é daí que vem a categoria. Quando o banco manda `<NAME>` (Inter) e não há regra, o script usa essa `<NAME>` cortada em 32 caracteres, que é exatamente como o Money criou os payees nas importações antigas do Inter (`Mercado Exemplo       Cidade`, `Pagamento Fatura - FULANO DE TAL`): os payees antigos continuam casando, com a categoria. Na tabela, essas linhas saem marcadas `(nome do banco)`; entregar o arquivo e listar ao Pet as que parecem novas, com a categoria sugerida, para ele escolher na importação. Sem regra e sem `<NAME>`: **parar e perguntar** antes de entregar. Antes de perguntar, procurar no Gmail (boleto, recibo, e-mail do marketplace), como no Ebanx. Tudo que o Pet confirmar vira linha no `payees.csv` (regra mais específica em cima: o script usa a primeira que casar).
2. **Pix para pessoa**: payee = só o nome, sem CPF, hora nem cidade, com até 32 caracteres. Categoria **não é obrigatória**. O script faz isso sozinho pelos padrões da lista `PIX_PESSOA` (hoje só o BB: `Pix - Enviado/Recebido - DD/MM HH:MM [CPF] NOME`). **Banco novo**: olhar como ele escreve o Pix no MEMO/NAME e acrescentar um padrão em `PIX_PESSOA` (grupo 1 = nome), testando no arquivo. Se o Pet disser quem é (ex.: FULANO DE TAL = Barbeiro), gravar a regra no `payees.csv`.
3. **Ebanx** (Pix Automático): o Ebanx cobra por vários serviços (Canva, OpenAI…), e o MEMO não diz qual. Procurar no Gmail `from:payments@ebanx.com` perto da data: o assunto traz serviço e valor ("Seu pagamento Canva de R$ 35,00 foi confirmado!"). Gravar com a coluna `valor`. Valor sem regra fica sem payee de propósito.
4. **BB Rende Fácil**: payee `Movimentação`, que no Money é transferência para a conta "1. Rende Fácil".
5. **Pix de conta própria** (FULANO DE TA…): payee `Transferência`.
6. Ao entregar, listar a tabela valor → payee → categoria que o script imprime, e apontar os payees novos com a categoria a escolher.
7. **Os dois lados de uma transferência**: pagamento de fatura, Pix entre contas próprias, resgate de CDB. Cada lado aparece no extrato da sua conta (ex.: -43,30 no 2. Inter e +43,30 no 3. Inter CC 2). Se o Pet marcar um lado como transferência na importação, o Money cria o outro lado sozinho, e o outro extrato vai duplicar. Avisar sempre que o outro lado já tiver sido importado ou ainda for ser.
8. **Pix Marketplace** (Inter, CNPJ 10573521): é Mercado Pago/Mercado Livre. O item está nos e-mails do Mercado Livre ("Você comprou …") da mesma data; valor que casa com um payee específico vai com a coluna `valor` (ex.: -24,88 = Assinatura X).

O Money corta o payee em 32 caracteres; a lista de payees dele já tem sujeira de importações antigas (CPF grudado no nome, cidade junto, duplicados como "Claude" × "Anthropic Claude", "ChatGPT" × "OpenAI ChatGPT"). Nas regras, usar o nome que o Pet usa hoje; na dúvida entre dois, perguntar.

## Caminho 2 — Fatura PDF de cartão em OFX

### Formato OFX correto (MS Money)

O MS Money exige **BANKMSGSRSV1** (não CREDITCARDMSGSRSV1):

```
OFXHEADER:100
DATA:OFXSGML
VERSION:102
SECURITY:NONE
ENCODING:USASCII
CHARSET:1252
COMPRESSION:NONE
OLDFILEUID:NONE
NEWFILEUID:NONE

<OFX>
   <SIGNONMSGSRSV1>
      <SONRS>
         <STATUS><CODE>0</CODE><SEVERITY>INFO</SEVERITY></STATUS>
         <DTSERVER>YYYYMMDD120000[-3:BRT]</DTSERVER>
         <LANGUAGE>POR</LANGUAGE>
         <FI><ORG>Banco Inter</ORG><FID>77</FID></FI>
      </SONRS>
   </SIGNONMSGSRSV1>
   <BANKMSGSRSV1>
      <STMTTRNRS>
         <TRNUID>1</TRNUID>
         <STATUS><CODE>0</CODE><SEVERITY>INFO</SEVERITY></STATUS>
         <STMTRS>
            <CURDEF>BRL</CURDEF>
            <BANKACCTFROM>
               <BANKID>77</BANKID>
               <ACCTID>{numero_cartao}</ACCTID>
               <ACCTTYPE>CREDITLINE</ACCTTYPE>
            </BANKACCTFROM>
            <BANKTRANLIST>
               <DTSTART>...</DTSTART>
               <DTEND>...</DTEND>
               <STMTTRN>
                  <TRNTYPE>DEBIT</TRNTYPE>
                  <DTPOSTED>20260316120000[-3:BRT]</DTPOSTED>
                  <TRNAMT>-74.90</TRNAMT>
                  <FITID>INTER0001202603</FITID>
                  <MEMO>RESTAURANTE EXEMPLO [Cartao 1234****5678]</MEMO>
               </STMTTRN>
            </BANKTRANLIST>
            <LEDGERBAL>
               <BALAMT>-482.93</BALAMT>
               <DTASOF>20260402120000[-3:BRT]</DTASOF>
            </LEDGERBAL>
         </STMTRS>
      </STMTTRNRS>
   </BANKMSGSRSV1>
</OFX>
```

### Algoritmo de extração do PDF

**1. Extrair metadados** — procurar `DDDD****DDDD DD/MM/AAAA` para obter cartão e vencimento.

**2. Detectar cartão atual** (faturas podem ter mais de um cartão listado).

**3. Detectar linha de transação** — começam com dia seguido de "de mês ano".

**4. Extrair valor** — pode estar na mesma linha ou na linha seguinte (quando o pdfplumber quebra entre página/coluna).

`+` no valor = CREDIT (pagamento). Sem sinal = DEBIT (compra).

**5. Ignorar linhas de total**: `Total CARTÃO`.

**6. Valor final**: compra → negativo (`DEBIT`), pagamento → positivo (`CREDIT`).

## Caminho 3 — CSV de cartão em OFX

**Script pronto**: `python csv_cartao_para_ofx.py entrada.csv ACCTID PREFIXO_FITID [--desde DD/MM/AAAA] [--saldo X]` (em `ofx-money`) aplica a regra de sinal abaixo e grava `entrada.ofx`; depois rodar `aplicar_payees.py` nele e entregar o `-name.ofx`. `ACCTID` vem do `contas.csv`. `PREFIXO_FITID` precisa ser novo a cada arquivo (ex.: `ICC20260929`), para não colidir com FITIDs já aceitos. `--desde` corta o que a última importação já trouxe: a data "Last Updated" da conta no Money e a "Last Paid" dos payees ajudam a achar o corte; listar ao Pet o que ficou de fora. Sem `--saldo`, o `BALAMT` é só a soma do período, não o saldo da fatura: avisar.

Formato típico (UTF-8 com BOM):

```
"Data","Lançamento","Categoria","Tipo","Valor"
"05/08/2026","VIVO EASY*VIVO EASY","OUTROS","Compra à vista","R$ 45,00"
```

### ⚠️ Sinal: NÃO ASSUMIR — verificar caso a caso

Já apareceram **dois formatos diferentes** de CSV do Inter na prática:

- **Formato A** (com sinal misto): compras positivas, pagamentos negativos (`-R$ 874,36`). Nesse caso, inverter o sinal de tudo ao converter para OFX.
- **Formato B** (tudo positivo, inclusive "PAGAMENTO ON LINE"): não há como diferenciar pelo sinal. Nesse caso, **identificar pagamentos pela descrição** (`PAGAMENTO ON LINE`, `Transferência`, `Débito automático fatura` etc.) e tratá-los como **CREDIT positivo** no OFX (reduzem a dívida), tratando todo o resto como **DEBIT negativo** (compra).

**Regra prática**: antes de gerar o arquivo, escanear a coluna `Lançamento`/`Valor` procurando por linhas com "PAGAMENTO", "TRANSFERÊNCIA" ou "DÉBITO AUTOMÁTICO FATURA". Se o valor dessas linhas vier com o MESMO sinal das compras normais, é o Formato B — inverter o sinal só dessas linhas específicas (pagamento = CREDIT), mantendo o resto como está. Se vier com sinal oposto, é o Formato A — inverter tudo.

**Erro já cometido**: converter "PAGAMENTO ON LINE" como DEBIT igual às compras. Isso soma a dívida em vez de abatê-la, e gera conflito com lançamentos "Transferência" que o usuário já tinha no Money para o mesmo pagamento — o saldo final não fecha (fica exatamente errado pelo dobro do valor do pagamento).

```python
import csv, re

with open(caminho_csv, encoding='utf-8-sig') as f:
    linhas = list(csv.DictReader(f))

def parse_val(v):
    v = v.replace('R$','').strip()
    neg = v.startswith('-')
    v = v.replace('-','').replace('.','').replace(',','.').strip()
    val = float(v)
    return -val if neg else val

PAGAMENTO_RE = re.compile(r'PAGAMENTO|TRANSFER[ÊE]NCIA|D[ÉE]BITO AUTOM[ÁA]TICO', re.I)

for row in linhas:
    val_csv = parse_val(row['Valor'])
    is_pagamento = bool(PAGAMENTO_RE.search(row['Lançamento']))
    if is_pagamento:
        val_ofx = abs(val_csv)   # sempre CREDIT positivo
    else:
        val_ofx = -abs(val_csv)  # sempre DEBIT negativo (compra)
    memo = re.sub(r'\s{2,}', ' ', row['Lançamento']).strip()
    categoria = row['Categoria'].strip()
    # memo final: f"{memo} ({categoria})"
```

Ordenar as transações por data crescente antes de montar `DTSTART`/`DTEND`.

**ACCTID para CSV**: o CSV não traz o número do cartão. Perguntar ao usuário os últimos 4 dígitos ou o nome exato da conta no Money.

## Caminho 4 — Print do app / lista colada (sem arquivo)

Quando o usuário cola texto do app ou manda screenshots em vez de um arquivo:

1. Extrair todas as transações (data, descrição, valor, sinal).
2. **Somar e comparar com o total da fatura informado pelo usuário** antes de gerar qualquer arquivo. Se não bater, avisar a diferença e perguntar como proceder (gerar assim mesmo vs. pedir export mais confiável).
3. Perguntar o ACCTID (últimos dígitos do cartão) se não estiver visível.
4. Tratar pagamentos como CREDIT, compras como DEBIT (mesma lógica do Caminho 3).

## Regras de saída (Caminhos 2, 3 e 4 — montagem do zero)

- `FITID`: `INTER{N:04d}{YYYYMM}` (sequencial único por arquivo). Ao gerar um arquivo de correção/reenvio para o mesmo período, usar um sufixo diferente (ex.: `INTERC0001202608B`) para não colidir com FITIDs já aceitos no Money.
- `NAME`: não montar aqui; depois de gerar o OFX, rodar `aplicar_payees.py` nele (seção **Payees**)
- `MEMO`: `{descricao} [Cartao {cartao_numero}]` (fatura PDF) ou `{descricao} ({categoria})` (CSV/print) — sem `&`, `<`, `>`
- `BALAMT`: soma de todos os valores (negativo = devedor). Se o resultado esperado é fatura zerada (paga), usar `0.00`.
- `DTASOF`: data de vencimento da fatura, quando disponível; senão data de hoje
- Encoding do arquivo: `latin-1`
- Nome sugerido: `fatura-inter-AAAAMM.ofx` (PDF) ou `fatura-inter-AAAAMM-outra-conta.ofx` (CSV/print)

## ACCTID e conta errada no Money

**Registro**: `D:\20-VIDAIA\00-CODIGOS\ofx-money\contas.csv` guarda qual `ACCTID` já está mapeado para qual conta do Money. Em arquivo montado do zero (CSV, PDF, print), reusar o `ACCTID` de lá; se a conta não estiver, criar um (ex.: `CART1234`, prefixo + 4 últimos dígitos do cartão), avisar o Pet que o Money vai perguntar a conta, e gravar a linha depois que ele confirmar a importação. A lista de contas do Money mostra o número mascarado com o mesmo tamanho do `ACCTID` (`XXXX1234` = 8 caracteres).

O Money associa um `ACCTID` a uma conta na primeira importação e reusa esse mapeamento nas seguintes — **sem perguntar de novo**. Isso causa dois problemas:

1. **Importou na conta errada da primeira vez**: gerar o próximo arquivo com um `ACCTID` diferente (ex.: sufixo `NOVA`, `CC`, ou qualquer string nova) força o Money a tratar como conta desconhecida e perguntar de novo a qual conta associar.
2. **Reenviando um arquivo corrigido para o mesmo período**: se for usar o `ACCTID` original, o Money vai repetir o mesmo mapeamento (útil se a conta já estava certa) — mas se a primeira tentativa foi pra conta errada, **trocar o ACCTID de novo**, e não voltar ao original, senão cai na mesma conta errada de novo. Lembrar de qual foi o ACCTID já usado em cada tentativa dentro da conversa.

## Diagnóstico: saldo não fecha depois de importar

Quando o usuário disser "não bate", "sumiu", "duplicou" ou similar, seguir esta ordem:

1. **Pedir "Items to review" e o "Bank Balance" do topo, e o "Ending Balance" do rodapé do registro.** Se "Bank Balance" (vindo do `LEDGERBAL` do OFX) diverge do "Ending Balance" (soma real do registro), é sinal de que nem tudo foi aceito/importado — ver item 2.
2. **"Items to review (N)" com N alto e transações sumidas do registro**: geralmente é auto-match/auto-reconcile do Money mesclando as novas transações com lançamentos genéricos antigos (`Compras`, `IOF`, `Restaurantes e Lanches`, nomes de assinatura como `Claude`, `TICKTICK`, `Assinatura X`) que têm o mesmo valor na mesma data. Isso pode:
   - **Absorver silenciosamente** a transação nova sem criar linha nem atualizar o nome (o valor já estava certo, então o saldo não quebra — só o detalhe do payee não aparece). Não é necessariamente um problema.
   - **Falhar em casar** e criar uma pendência "?" duplicada ao lado do lançamento genérico antigo, inflando o saldo. Nesse caso, apagar o lançamento genérico antigo (sem "?") duplicado, mantendo o novo detalhado.
3. **Calcular manualmente a soma esperada** a partir da lista de transações que o usuário forneceu (whatsapp/print/CSV), começando do saldo que deveria ser zero antes da primeira transação. Comparar com o "Ending Balance" do Money. A diferença aponta exatamente para o valor duplicado ou faltante — procurar no registro uma linha (ou par de linhas) com esse valor exato.
4. **Duplicação clássica antiga**: um pagamento (`Transferência`/`PAGAMENTO ON LINE`, crédito positivo) que também aparece como `Compras` ou outro nome genérico de mesma data e valor, mas como débito. Isso soma o dobro do valor do pagamento à diferença. Apagar a linha extra (geralmente a mais antiga/genérica, sem "?").
5. Depois de qualquer correção, sempre pedir o print do registro completo do início ao fim (não só um trecho) antes de declarar resolvido — reconciliar com dados parciais já causou diagnóstico errado nesta conversa mais de uma vez.

## Erros comuns

| Sintoma | Causa | Solução |
|---|---|---|
| "invalid or corrupt data" no Money | CREDITCARDMSGSRSV1 | Usar BANKMSGSRSV1 |
| "invalid or corrupt data" no Money | Data sem fuso horário | Adicionar `120000[-3:BRT]` |
| Cada Pix vira um payee novo, com data e hora no nome | OFX sem `<NAME>`: o Money usa o MEMO como payee | Aplicar `payees.csv` com `aplicar_payees.py` |
| Payee entra sem categoria | Nome não é exatamente igual ao payee existente no Money (ou payee é novo) | Acertar o nome no `payees.csv`; payee novo: escolher a categoria uma vez no Money |
| Transação faltando (fatura PDF) | Valor na linha seguinte | Buscar valor em look-ahead |
| Nome genérico na conta | ACCTID hardcoded | Extrair do padrão `DDDD****DDDD` (PDF) ou perguntar ao usuário (CSV/print) |
| Saldo dobra o valor do pagamento a mais | Pagamento (`PAGAMENTO ON LINE`) convertido como DEBIT em vez de CREDIT | Detectar pagamento pela descrição, não só pelo sinal do CSV (ver Caminho 3) |
| Importou na conta certa da primeira vez, errado na segunda (ou vice-versa) | Money reusa o mapeamento ACCTID→conta da primeira importação | Trocar o ACCTID a cada tentativa até acertar; nunca reusar um ACCTID que já mapeou errado |
| Transações sumem do registro após importar, mas saldo do topo bate | Auto-match absorveu silenciosamente em lançamentos genéricos antigos | Não é erro se o saldo fechar; conferir "Items to review" e comparar Bank Balance vs Ending Balance |
| Saldo não fecha mesmo depois de tudo aceito | Duplicata antiga não relacionada ao import atual (ex.: pagamento antigo lançado duas vezes, uma como crédito outra como débito) | Somar manualmente a partir de um saldo inicial conhecido (0 ou o que o usuário confirmar) e comparar com o Ending Balance para achar a diferença exata |
| Card "fatura aberta" do app Inter não bate com soma do Money | O app às vezes exibe o valor da fatura anterior já paga em vez da fatura aberta atual | Conferir somando manualmente os lançamentos do período — costuma confirmar que a conversão está correta e o app é que exibe errado |

