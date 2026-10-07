---
name: diario-oficial-ac
description: >
  Analisa PDFs do Diário Oficial do Estado do Acre (DOE-AC) extraindo apenas as seções
  GABINETE DA GOVERNADORA e SEICT, delimitadas pelos marcadores (bookmarks) do PDF, e
  descartando todo o restante. Busca o nome configurado em DOE_NOME, monta tabelas de
  exonerações e nomeações e resume os demais atos das duas seções (leis sancionadas,
  decretos -P de outra natureza, créditos adicionais, portarias e extratos da SEICT).
  Use quando o usuário enviar um PDF do Diário Oficial do Acre, mencionar "DOE Acre",
  "diário oficial do Acre", "atos de pessoal", "exoneração", "nomeação", "gabinete da
  governadora", "SEICT", "decreto de nomeação", "decreto de exoneração", "CAS", "DAE",
  cargos comissionados no governo do Acre, ou pedir o resumo dos atos e leis publicados
  na edição.
---

# Atos do DOE-AC — Gabinete da Governadora e SEICT

Extraia do DOE-AC as duas seções que interessam: **GABINETE DA GOVERNADORA** e **SEICT**. O resto do PDF é descartado antes de qualquer leitura.

A saída tem duas partes, ambas obrigatórias:

1. **Atos de pessoal** — tabelas de exonerações e nomeações (o núcleo).
2. **Demais atos** — leis sancionadas, decretos `-P` de outra natureza, créditos adicionais e os atos da SEICT.

## Fluxo

1. Rode o script de extração.
2. Leia `RESUMO.md` (sempre), os `*_atos.txt` (pessoal) e os `*_completo.txt` (demais atos, com a poda da seção 5).
3. Monte as tabelas de pessoal.
4. Monte o bloco de demais atos.
5. Apresente no formato da seção "Saída".

## 1. Extração

O script fica em `D:\20-VIDAIA\00-CODIGOS\skills\diario-oficial-ac\scripts\extrair_secoes.py`. Use sempre o Python do Windows pelo caminho completo; nunca `python` nem `python3` soltos. A saída vai para uma pasta temporária (`<SAIDA>`): no Claude Code, `doe` dentro da pasta de trabalho da sessão (o scratch workspace, `--out "./doe"`); no Codex, `%TEMP%\doe`. Nunca grave a saída ao lado do PDF nem em pasta de projeto.

Não use a pasta de rascunho (scratchpad) do Claude Code: o caminho dela já passa de 250 caracteres e, com os nomes dos arquivos, estoura o limite de 260 do Windows (`WinError 206` no `os.makedirs`).

```text
"C:\Users\petro\AppData\Local\Programs\Python\Python313\python.exe" "D:\20-VIDAIA\00-CODIGOS\skills\diario-oficial-ac\scripts\extrair_secoes.py" "CAMINHO_DO_PDF" --out "<SAIDA>"
```

Dependências: `pdfplumber` e `pypdf`, já instaladas nesse Python. Se faltar alguma, instale com o mesmo Python: `-m pip install pdfplumber pypdf`.

Parâmetros: `--secoes "GABINETE DA GOVERNADORA,SEICT"` e `--nome "Seu Nome"` (as seções já são o padrão; sem `--nome`, vale a variável de ambiente `DOE_NOME`).

Saídas em `<SAIDA>`:

| Arquivo | Uso |
|---|---|
| `RESUMO.md` | ler sempre — intervalos, contagem de atos e busca por nome |
| `<SECAO>_atos.txt` | ler sempre — só os atos de pessoal, sem as fórmulas repetidas |
| `<SECAO>_completo.txt` | ler sempre — base dos demais atos (aplicar a poda da seção 5) |
| `secoes_recorte.pdf` | PDF com as páginas das seções; útil para pegar valores por regex |
| `mapa_secoes.json` | intervalos de todas as seções, para auditoria |

### Como o script delimita as seções

Pelos marcadores do PDF. O intervalo vai da página do marcador da seção até o marcador seguinte, com uma ressalva decisiva:

> **Seções compartilham páginas.** O DOE é diagramado em duas colunas e corrido: uma seção nova costuma começar no meio da página em que a anterior termina.

| Cabeçalho da próxima seção | Fim da seção alvo |
|---|---|
| no **topo** da página (y < 100), sem texto de coluna antes dele | página anterior |
| no **topo** de uma coluna que não a primeira, com texto antes dele | aquela mesma página (compartilhada) |
| no **meio** da página | aquela mesma página (compartilhada) |

Exemplos reais: ed. 14.315 (24/07/2026) — Gabinete = 1–7, porque Polícia Civil começa no topo da pág. 8; SEICT = 26–29, porque SEJUSP começa no meio da pág. 29. Ed. de 14/08/2026 — Gabinete = 1–74 (CGE no topo da 75), SEICT = 111–116 (SEJUSP no meio da 116).

Nas páginas compartilhadas o script ainda corta o conteúdo alheio no nível da palavra, seguindo a ordem de leitura das colunas.

Sempre reporte ao usuário os intervalos detectados e quantas páginas foram descartadas.

### Armadilhas de marcador (já ocorreram)

- **Seção sem marcador** — é ignorada em silêncio pelo script, e o `AVISO:` sai no stdout. Leia o stdout. Em 30/07/2026 o Gabinete não tinha marcador e a seção inteira sumiu. Avise o usuário explicitamente quando isso acontecer.
- **Marcador uma página adiante do conteúdo** — em 31/07/2026 (ed. 14.320-A) o marcador apontava o Gabinete para a pág. 2, mas os atos começavam na pág. 1; incluir a pág. 1 recuperou 6 decretos. Se a seção começa na pág. 2 ou 3, confira a página anterior antes de aceitar o intervalo.
- **Marcador sem cabeçalho da seção** — o script confere se o cabeçalho da seção alvo aparece na página do marcador; se não aparece, sai `AVISO: marcador ... sem cabecalho correspondente; secao provavelmente vazia` no stdout e no `RESUMO.md`. Em 05/10/2026 (ed. 14.366) o marcador do Gabinete apontava para a pág. 1, que só tinha sumário e Polícia Civil; o `_completo.txt` saiu com portarias da PCAC e do CBMAC. Com esse aviso, confira o texto: se não houver ato do Gabinete, diga ao usuário que a seção está vazia nesta edição e não resuma o conteúdo alheio. Se o cabeçalho estiver na página anterior, o aviso diz isso (é o caso do marcador uma página adiante, acima).
- **Cabeçalho da próxima seção no topo da coluna direita** — o y sozinho não basta. Em 06/10/2026 (ed. 14.367) o cabeçalho SEJUSP estava em y=49 da pág. 53, mas na coluna direita; a esquerda ainda era SEICT (fim da Portaria nº 121 e a Portaria nº 158). A regra antiga cortou a SEICT em 51–52 e perdeu as duas portarias. Agora o topo só leva o fim para a página anterior se não houver texto de coluna antes do cabeçalho na ordem de leitura; havendo, a página é compartilhada e o corte é feito no nível da palavra (SEICT = 51–53).
- **Sem marcador algum no PDF** — o script aborta. Avise que a delimitação automática não é confiável.
- **Faltando as duas seções** — o script imprime `NADA A EXTRAIR`. Responda apenas que a edição não traz atos do Gabinete nem da SEICT e encerre. **Não** varra o PDF por conta própria e **não** analise outras seções.

## 2. Alerta de nome

Isto é um alarme, não uma busca neutra: para quem ocupa cargo em comissão, o nome só aparece no DOE quando a pessoa é exonerada ou nomeada. **Ausência é a notícia boa; presença é urgente.**

O script faz a busca em três camadas e escreve o resultado em `RESUMO.md`:

1. **Estrita** — sobre o texto emendado, imune a quebra de linha, acento, caixa e espaço duplo.
2. **Tolerante a codificação** — há PDFs do DOE em que um glifo não mapeia e chega como caractere inválido; se isso atingir uma vogal acentuada, "JOSÉ" vira "JOS." e a busca literal falharia justamente no dia que importa. Essas ocorrências vêm marcadas `[grafia alterada]` e valem alarme igual.
3. **Só o primeiro nome** — listada à parte, para conferir se é a mesma pessoa.

- **Sem ocorrência:** comece a resposta com uma linha só, direta: "Nada sobre você nesta edição." Não elabore.
- **Com ocorrência:** abra a resposta com o alerta em destaque, antes de qualquer tabela — o trecho exato, a página, o número do decreto e o que o ato faz (exoneração, nomeação, sem efeito). Se for exoneração, diga isso na primeira linha, sem rodeio.
- **Ocorrência só do primeiro nome:** verifique no trecho se é a mesma pessoa antes de alarmar; se for homônimo, diga que não é ele.

Cuidado com "Petrópolis", que aparece no fecho de todo decreto e não tem relação com o nome.

## 3. Atos de pessoal — interpretação

Tipos que entram nas tabelas: **exonerações**, **decretos tornados sem efeito** e **nomeações**. Decretos de pessoal no Acre têm sufixo `-P` no número (ex.: `DECRETO Nº 15.667-P`) e vêm sempre em CAIXA ALTA — em caixa mista é citação dentro do texto, não ato novo.

Os demais decretos `-P` (vacância, reforma militar, designação, cessão, colocação à disposição, agregação, revogação, alteração de lotação) **não** entram nas tabelas — vão para o bloco de demais atos (seção 5).

**Mês/Ano de Referência** — campo crítico:

- Exonerações e "sem efeito": mês/ano do **decreto original de nomeação** que está sendo revogado. Procure "nomeado através do Decreto nº X, de DD de MMMM de AAAA" no corpo do ato.
- Nomeações: mês/ano do **decreto atual**.

Formato `MM/AAAA`.

## 4. Tabelas de pessoal

Colunas concisas — as tabelas devem caber em meia tela 4K (~960px).

**TABELA 1 — EXONERAÇÕES** (inclui os "sem efeito"), ordenada alfabeticamente por Nome:

| Nome | CAS/DAE | Mês/Ano Ref. |
|------|---------|--------------|

**TABELA 2 — NOMEAÇÕES**, ordenada por Órgão (A→Z) e, dentro do órgão, por Nome (A→Z):

| Órgão | Nome | CAS/DAE | Mês/Ano Ref. |
|-------|------|---------|--------------|

**Regra especial — SEICT:** os nomeados para a SEICT saem do fluxo geral e vão no **final** da tabela, em ordem alfabética entre si, precedidos de uma linha separadora.

Regras gerais: nomes em Title Case (vêm em CAIXA ALTA no PDF); sem código CAS/DAE, registre o que houver (FG-3, CC-2) ou `—`; abrevie órgãos longos mantendo a sigla oficial.

Se a mesma pessoa for exonerada e nomeada na mesma edição, aponte isso em nota — é troca de vínculo, não duas movimentações independentes.

## 5. Demais atos

Base: os `*_completo.txt`. Para enumerar os atos da seção, reaproveite as funções do próprio script:

```python
import re, sys
sys.path.insert(0, "DIR_DO_SCRIPT")
from extrair_secoes import separar_atos, eh_pessoal, enxugar

lp, pag = [], None
for ln in open("GABINETE_DA_GOVERNADORA_completo.txt", encoding="utf-8"):
    ln = ln.rstrip("\n")
    m = re.match(r"^===== \[pag\. (\d+)\] =====$", ln)
    if m: pag = int(m.group(1)); continue
    if ln.startswith("# "): continue
    if pag: lp.append((pag, ln))

for i, a in enumerate(separar_atos(lp)):
    flag = "PESSOAL" if eh_pessoal(a) else "       "
    print(f"[{i:02d}] {flag} p.{a['pag']:>3} linhas={len(a['linhas']):>4} | {a['titulo'][:110]}")
```

Isso dá o índice da seção. A partir dele, leia o corpo só dos atos que interessam.

### Poda obrigatória — decretos de crédito adicional

Os decretos de crédito adicional (suplementar/especial, numeração **sem** `-P`) carregam anexos de dotação orçamentária que respondem por até 92% do volume da seção e não têm informação nenhuma de interesse — é o paredão de `3 3 90 39 00 00 - OUTROS SERVIÇOS DE TERCEIROS`.

**Nunca leia o corpo desses decretos.** Extraia só:

- número, data e tipo (suplementar ou especial);
- o valor, por regex na primeira página do ato sobre o `secoes_recorte.pdf` (`R\$ ?[\d]{1,3}(?:\.\d{3})*,\d{2}` — o primeiro casamento da página é o do `Art. 1º`);
- as fontes de compensação citadas no `Art. 2º` (superávit financeiro, excesso de arrecadação, anulação de dotações, transferência especial da União);
- os órgãos beneficiados que aparecem em CAIXA ALTA no anexo, se forem poucos.

Cada decreto vira **uma linha de tabela**. Feche com o total somado.

Atenção: o número por extenso e o valor em algarismos ficam em colunas diferentes e a ordem de leitura os separa — confira se o extenso bate com o número antes de reportar. Quando duas páginas de decreto se encontram, o regex pode devolver valores de dois atos; o do ato novo é o que casa com o extenso.

### O que reportar de cada tipo

**Leis sancionadas** — separe em dois grupos:

- *Com efeito prático*: jornada, tributos, criação de órgão, doação de imóvel, PCCR. Diga o que muda, para quem, a partir de quando, e a autoria (Poder Executivo, deputado, Mesa Diretora).
- *Simbólicas*: utilidade pública, datas comemorativas, títulos honoríficos. Uma linha corrida com todas, sem detalhar.

**Decretos `-P` de outra natureza** — um item por ato, dizendo o que faz e o efeito prático: vacância (por falecimento, posse em cargo inacumulável, aposentadoria), cessão (com ou sem ônus, prazo), designação para responder por pasta (quem, qual, período), reforma militar, revogação por decisão judicial. Marque `REPUBLICADO POR INCORREÇÃO` quando constar.

**SEICT** — costuma ser portaria de gestão/fiscalização de contrato, aviso de cotação e extrato de aditivo:

- *Portarias de gestor/fiscal*: tabela com portaria, contrato/objeto, empresa e os designados (gestor titular e substituto, fiscal titular e substituto). Registre a portaria revogada.
- *Avisos e convites*: objeto, prazo de resposta, e-mail de envio, quantitativos principais.
- *Extratos de aditivo*: instrumento, contratada, efeito (prorrogação com período, acréscimo com percentual e valor).

Cruze os atos entre si: quando a mesma contratação aparece em dois atos da edição (uma portaria redesignando fiscal e um aditivo prorrogando o mesmo contrato), diga isso.

### Contaminação de fronteira

Nas páginas compartilhadas sobra conteúdo das seções vizinhas — extratos de outra secretaria no topo da primeira página, avisos de licença ambiental do IMAC no rodapé da última. Reconheça pelo órgão citado, deixe fora do resumo e registre em nota de rodapé o que foi descartado e por quê.

Pela mesma razão, a contagem de atos do script infla: um ato que atravessa a quebra de página pode ser contado duas vezes. Reporte a contagem que você apurou, não a do script.

## 6. Saída

```
[Alerta de nome — em destaque, se encontrado. Se não, uma linha: "Nada sobre você nesta edição."]

Seções extraídas: Gabinete da Governadora (págs. X–Y), SEICT (págs. W–Z) — N páginas descartadas.

## Atos do Gabinete da Governadora e SEICT — DOE-AC [data da edição]

### Exonerações
[Tabela 1]
Total: X servidores

### Nomeações
[Tabela 2]
Total: Y servidores (Z na SEICT)

---

## Demais atos — o que passa a valer

### Gabinete: leis sancionadas
[com efeito prático, depois as simbólicas em uma linha]

### Gabinete: créditos adicionais
[tabela: decreto | data | tipo | valor] + total + fontes + beneficiários recorrentes

### Gabinete: decretos -P de outra natureza
[lista]

### SEICT
[tabela de portarias, avisos, tabela de extratos]

[Nota de qualidade da extração, se houve contaminação ou campo ambíguo]
```

Informação ambígua ou ilegível: marque `[?]` no campo e explique em nota ao final.

## Observações

- Decretos referenciam decretos anteriores — é neles que está o Mês/Ano de Referência das exonerações.
- O script remove do `_atos.txt` as fórmulas de praxe (preâmbulo da Governadora, artigo de vigência, fecho, assinatura). Se algum campo parecer faltar, confira o ato no `_completo.txt` antes de marcar `[?]`.
- Palavras hifenizadas na quebra de linha já são reunidas pelo script, mas confira nomes próprios.
- A ordem de leitura por coluna às vezes intercala trechos de atos vizinhos dentro do `_atos.txt`. Quando um ato curto parecer conter texto alheio (tabela de dotação no meio de uma exoneração), vá ao `secoes_recorte.pdf` e leia a página com `extract_text()` — lá o ato sai íntegro.
- Nunca infira onde a seção acaba pelo conteúdo: use os marcadores e a regra de fronteira.
- Nomear membros de conselho colegiado (CACS-FUNDEB, Conselho Superior da AGEAC) não é nomeação para cargo em comissão — fica fora da Tabela 2 e entra nos demais atos.

## Calibração

Validado em 25 edições do DOE-AC (jun–ago/2026, 121 a 513 páginas), 817 atos de pessoal identificados, dos quais 734 entram nas tabelas. Nenhum ato dispositivo perdido e nenhuma contaminação de seção vizinha. Casos cobertos: seção iniciando na pág. 1, 2 ou 3; edição sem marcador de SEICT; edição sem marcador de Gabinete; edição sem nenhum dos dois; seções que começam e terminam em página compartilhada; PDFs em que o ponto final vem como caractere inválido; duas edições no mesmo dia (regular e extra).

**Tamanho esperado das seções** — serve para desconfiar do resultado:

| | Típico | Ocasional | Excepcional |
|---|---|---|---|
| Gabinete | 1–3 págs. | ~20 págs. (lote grande de nomeações) | 74 págs. (créditos adicionais atrasados) |
| SEICT | 1–6 págs. | — | — |

Volume medido: 28/07 = 21 págs. (93 nomeados); 31/07 = 1 e 9 págs.; 04/08 = 3 págs.; 05/08 = 2 págs.; 10/08 = 3 págs.; 14/08 = 74 págs. (7 decretos de crédito adicional, 63 delas de anexo orçamentário). Um Gabinete acima de 30 páginas quase sempre significa crédito adicional acumulado — aplique a poda e o custo volta ao normal.
