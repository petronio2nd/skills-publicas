# Formato do editor SEI/AC — guia de referência

## O que descobri testando no editor

O editor do SEI é um **CKEditor** dividido em regiões independentes:

| Região | Conteúdo | Editável |
|---|---|---|
| Cabeçalho | Brasão + ESTADO DO ACRE + endereço | não (automático) |
| Título | `Despacho nº 1/2026/SIGLA - UNIDADE` | **número gerado automaticamente** |
| Destinatário | `Ao(À) Sr(a). ...` | sim |
| **Corpo** | o texto do documento | **sim — é aqui que se cola** |
| Rodapé | `Referência: Processo nº ...` + `SEI nº ...` | não (automático) |

## Por que colar de DOCX/PDF quebra

O DOCX traz fonte, tamanho, espaçamento e recuo como **estilo embutido** (Arial, Calibri, margens em cm).
O SEI ignora ou distorce isso porque toda a formatação dele vem de **classes CSS nomeadas**.
A solução é colar **HTML puro usando as classes do SEI**, sem nenhum `style=` de fonte.

## Fonte padrão

- **Times New Roman**
- Corpo: **11 pt**, justificado, recuo de primeira linha de **2,5 cm**
- Bloco de assinatura: **10 pt**, centralizado

Não é preciso declarar nada disso: a classe já aplica.

## Classes disponíveis (vocabulário completo)

### Parágrafos de texto
| Classe | Efeito |
|---|---|
| `Texto_Justificado_Recuo_Primeira_Linha` | **padrão do corpo** — justificado, recuo 2,5 cm |
| `Texto_Justificado_Recuo_Primeira_Linha_Esp_Simples` | idem, espaçamento simples |
| `Texto_Justificado` | justificado, sem recuo |
| `Texto_Justificado_Maiusculas` | justificado, maiúsculas |
| `Texto_Alinhado_Esquerda` | à esquerda |
| `Texto_Alinhado_Esquerda_Espacamento_Simples` | à esquerda, espaçamento simples |
| `Texto_Alinhado_Esquerda_Espacamento_Simples_Maiusc` | idem, maiúsculas |
| `Texto_Alinhado_Direita` | à direita — usar na data |
| `Texto_Centralizado` | centralizado — **bloco de assinatura** |
| `Texto_Centralizado_Maiusculas` | centralizado, maiúsculas |
| `Texto_Centralizado_Maiusculas_Negrito` | centralizado, maiúsculas, negrito |
| `Texto_Centralizado_Maiusculas_Negrito_titulo` | título |
| `Texto_Centralizado_Maiusculas_Negrito_cabecalho` | cabeçalho |
| `Texto_Espaco_Duplo_Recuo_Primeira_Linha` | espaço duplo |
| `Texto_Fundo_Cinza_Negrito` | fundo cinza, negrito |
| `Texto_Fundo_Cinza_Maiusculas_Negrito` | fundo cinza, maiúsculas, negrito |
| `Citacao` | citação recuada |

### Numeração AUTOMÁTICA — não digitar o rótulo
| Classe | Gera sozinho |
|---|---|
| `Paragrafo_Numerado_Nivel1` a `...Nivel7` | `1.` `2.` `3.` |
| `Item_Inciso_Romano` | `I -` `II -` `III -` |
| `Item_Alinea_Letra` | `a)` `b)` `c)` |
| `Item_Nivel1` a `Item_Nivel8` | numeração + MAIÚSCULAS/NEGRITO/fundo cinza (serve de seção) |

**ARMADILHA CONFIRMADA NO TESTE:** se você escrever `<p class="Item_Inciso_Romano">I – primeiro...</p>`
o resultado sai **`I -   I – primeiro...`** (duplicado). Escreva só o texto.

### Tabelas
| Classe (dentro da célula) | Efeito |
|---|---|
| `Tabela_Texto_Centralizado` | centralizado |
| `Tabela_Texto_Alinhado_Esquerda` | à esquerda |
| `Tabela_Texto_Alinhado_Direita` | à direita — usar em valores R$ |
| `Tabela_Texto_Justificado_Simples` | justificado |
| `Tabela_Texto_8` | corpo 8 pt (tabelas densas) |

Tabelas funcionam perfeitamente, inclusive com cor de fundo no cabeçalho.

## Modelo pronto (esqueleto)

```html
<p class="Texto_Justificado_Recuo_Primeira_Linha">Senhor(a) Diretor(a),</p>
<p class="Texto_Justificado_Recuo_Primeira_Linha">Primeiro parágrafo do texto.</p>

<p class="Texto_Fundo_Cinza_Maiusculas_Negrito">1. DO OBJETO</p>
<p class="Texto_Justificado_Recuo_Primeira_Linha">Texto da seção.</p>

<p class="Item_Inciso_Romano">texto do primeiro inciso;</p>
<p class="Item_Inciso_Romano">texto do segundo inciso; e</p>
<p class="Item_Alinea_Letra">texto da alínea.</p>

<table border="1" cellpadding="4" cellspacing="0" style="width:100%">
<tbody>
  <tr>
    <td style="background-color:#d9e2f3;width:10%"><p class="Tabela_Texto_Centralizado"><strong>Item</strong></p></td>
    <td style="background-color:#d9e2f3;width:60%"><p class="Tabela_Texto_Centralizado"><strong>Descrição</strong></p></td>
    <td style="background-color:#d9e2f3;width:30%"><p class="Tabela_Texto_Centralizado"><strong>Valor</strong></p></td>
  </tr>
  <tr>
    <td><p class="Tabela_Texto_Centralizado">1</p></td>
    <td><p class="Tabela_Texto_Justificado_Simples">Descrição do item.</p></td>
    <td><p class="Tabela_Texto_Alinhado_Direita">R$ 171.400,00</p></td>
  </tr>
</tbody>
</table>

<p class="Texto_Justificado_Recuo_Primeira_Linha">&nbsp;</p>
<p class="Texto_Justificado_Recuo_Primeira_Linha">Atenciosamente,</p>
<p class="Texto_Centralizado">&nbsp;</p>
<p class="Texto_Centralizado"><strong>Nome</strong><br />Cargo<br />Portaria/Decreto nº ___</p>
```

## Regras de redação oficial (Manual da Presidência, 3ª ed.)

- Sem "Prezado(a)" no despacho interno: vocativo é `Senhor(a) Diretor(a),`
- Fecho: **Atenciosamente** (mesma hierarquia ou inferior) / **Respeitosamente** (autoridade superior)
- Não repetir o número do despacho no corpo — o SEI já gera no título
- Citar documentos por **nome + número SEI**: `Despacho nº 1/2026/SIGLA-UNIDADE (0012345671)`
- Impessoalidade: 1ª pessoa do singular quando o signatário fala por si (`informo`, `encaminho`, `submeto`)
- Data por extenso, à direita, só quando o documento exigir (o SEI já registra a data da assinatura)

## O que NÃO fazer

- não colar de Word/PDF direto
- não usar `<h1>`, `<h2>`, `<div>`, `<span style=...>`
- não declarar `font-family` nem `font-size`
- não digitar os rótulos de incisos, alíneas e itens numerados
- não escrever "Despacho nº ___" no corpo
