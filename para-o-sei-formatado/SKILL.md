---
name: para-o-sei-formatado
description: "Monta documentos no editor do SEI/AC: converte texto em HTML com as classes CSS oficiais do sistema, injeta direto no documento via Claude in Chrome e cria os links internos entre documentos do processo. Use sempre que o Pet pedir 'joga no SEI', 'formata pro SEI', 'cola no SEI', 'converte pro SEI', 'HTML do SEI', 'põe no despacho', 'monta o documento no SEI', 'linka os documentos', enviar um link app.sei.ac.gov.br/sei/controlador.php?acao=editor_montar, ou pedir despacho/ofício/memorando/termo de referência/mapa de risco/declaração para tramitar no SEI. NÃO use para gerar DOCX ou PDF (use as skills docx/pdf)."
---

# Para o SEI — Formatado

Monta e injeta documentos no editor do SEI/AC (CKEditor 4), com links internos funcionais.

## Regra de ouro

O SEI **ignora formatação embutida**. Toda a aparência vem de **classes CSS nomeadas**.
Colar de Word/PDF quebra. Injetar HTML com as classes certas funciona.

- **NUNCA** usar `style="font-family..."`, `font-size`, `<h1>`, `<h2>`, `<div>`, `<span>`
- **SEMPRE** usar `<p class="...">` com as classes da tabela abaixo
- `style=` só é permitido em tabela: `width`, `background-color`, `vertical-align`
- Acentos em UTF-8 puro funcionam; entidades HTML também. Prefira entidades em textos longos injetados por JS.

## Fonte (não declarar — a classe aplica)

Times New Roman · corpo 11 pt justificado com recuo de primeira linha de 2,5 cm · assinatura 10 pt centralizada.

## Estrutura do editor

Regiões independentes, cada uma um editor CKEditor separado:

| Região | Editável | Observação |
|---|---|---|
| Cabeçalho (brasão, órgão, endereço) | não | automático |
| Título (`Despacho nº 1/2026/SIGLA - UNIDADE`) | não | **número gerado pelo sistema** |
| Destinatário (`Ao(À) Sr(a). ...`) | **sim** | editor próprio; pode ser substituído por injeção |
| **Corpo** | **sim** | é aqui que vai o conteúdo |
| Rodapé (`Referência:` / `SEI nº`) | não | automático |

**Nunca** escrever "Despacho nº ___" no corpo.

### Identificar o editor do corpo

```js
const C=window.CKEDITOR; let r=[];
for(const k in C.instances){let n=0,t='';try{const b=C.instances[k].document.getBody().$;
 n=b.innerHTML.length;t=(b.textContent||'').trim().replace(/\s+/g,' ').slice(0,60)}catch(e){}
 r.push(k+' | '+n+' | '+t)}
r.join('\n')
```

**Não escolher pelo tamanho.** O cabeçalho tem ~35 000 caracteres e engana heurísticas de "maior". Identifique pelo **texto**: o corpo é o que está vazio (documento novo) ou contém o conteúdo. Alguns tipos (Termo de Referência, Declaração) já trazem modelo preenchido no corpo — confirme antes de sobrescrever.

## Classes

### Parágrafos
| Classe | Uso |
|---|---|
| `Texto_Justificado_Recuo_Primeira_Linha` | **padrão do corpo** |
| `Texto_Justificado_Recuo_Primeira_Linha_Esp_Simples` | idem, espaçamento simples |
| `Texto_Justificado` | justificado sem recuo (bom para destinatário) |
| `Texto_Justificado_Maiusculas` | justificado maiúsculas |
| `Texto_Alinhado_Esquerda` | à esquerda |
| `Texto_Alinhado_Esquerda_Espacamento_Simples` | à esquerda, esp. simples |
| `Texto_Alinhado_Esquerda_Espacamento_Simples_Maiusc` | idem, maiúsculas |
| `Texto_Alinhado_Direita` | data, local |
| `Texto_Centralizado` | **bloco de assinatura** |
| `Texto_Centralizado_Maiusculas` | centralizado maiúsculas |
| `Texto_Centralizado_Maiusculas_Negrito` | centralizado maiúsculas negrito |
| `Texto_Centralizado_Maiusculas_Negrito_titulo` | título |
| `Texto_Centralizado_Maiusculas_Negrito_cabecalho` | cabeçalho |
| `Texto_Espaco_Duplo_Recuo_Primeira_Linha` | espaço duplo |
| `Texto_Fundo_Cinza_Negrito` | destaque |
| `Texto_Fundo_Cinza_Maiusculas_Negrito` | **título de seção** (o mais usado) |
| `Citacao` | citação recuada |

### Numeração AUTOMÁTICA — escrever só o texto
| Classe | Gera sozinho |
|---|---|
| `Paragrafo_Numerado_Nivel1` … `Nivel7` | `1.` `2.` `3.` |
| `Item_Inciso_Romano` | `I -` `II -` `III -` |
| `Item_Alinea_Letra` | `a)` `b)` `c)` |
| `Item_Nivel1` … `Item_Nivel8` | número + MAIÚSCULAS + negrito + fundo cinza |

**ARMADILHA:** `<p class="Item_Inciso_Romano">I – texto</p>` produz `I -   I – texto`. Escrever apenas o texto.

### Células de tabela
| Classe | Uso |
|---|---|
| `Tabela_Texto_Centralizado` | cabeçalho, números curtos |
| `Tabela_Texto_Alinhado_Esquerda` | texto curto |
| `Tabela_Texto_Alinhado_Direita` | **valores em R$** |
| `Tabela_Texto_Justificado_Simples` | texto longo |
| `Tabela_Texto_8` | **tabelas densas (8 pt)** |

Tabela padrão:
```html
<table border="1" cellpadding="4" cellspacing="0" style="width:100%">
<tbody>
<tr>
 <td style="background-color:#d9e2f3;width:10%"><p class="Tabela_Texto_Centralizado"><strong>Item</strong></p></td>
 <td style="background-color:#d9e2f3;width:60%"><p class="Tabela_Texto_Centralizado"><strong>Descrição</strong></p></td>
 <td style="background-color:#d9e2f3;width:30%"><p class="Tabela_Texto_Centralizado"><strong>Valor</strong></p></td>
</tr>
<tr>
 <td style="vertical-align:top"><p class="Tabela_Texto_Centralizado">1</p></td>
 <td style="vertical-align:top"><p class="Tabela_Texto_Justificado_Simples">Descrição.</p></td>
 <td style="vertical-align:top"><p class="Tabela_Texto_Alinhado_Direita">R$ 171.400,00</p></td>
</tr>
</tbody>
</table>
```

**A página do SEI é sempre retrato e não vira.** Máximo confortável: **6 colunas**. Tabelas de risco com 8 colunas (ID, risco, P, I, Nível, preventiva, contingência, responsável) devem virar 6, fundindo P/I/Nível numa coluna "Avaliação" com `<br />`. Use `Tabela_Texto_8` nessas.

## Injeção

Conteúdo longo excede o limite de uma chamada. Acumule em `window.__H` e aplique no fim:

```js
window.__H = '<p class="...">...</p>';          // 1ª chamada
window.__H += '<p class="...">...</p>';         // chamadas seguintes
window.CKEDITOR.instances['<idDoCorpo>'].setData(window.__H);   // última
```

Trocar o destinatário:
```js
window.CKEDITOR.instances['<idDestinatario>']
  .setData('<p class="Texto_Justificado">Ao Gabinete do Secretário ...</p>');
```
`setData` é assíncrono — aguarde ~600 ms antes de reler para conferir.

## Links internos entre documentos (âncora SEI)

O link do SEI **não tem `href`**. É `<a id="lnkSei<ID_INTERNO>" class="ancora_sei" style="text-indent:0px;">0012345678</a>`, onde `<ID_INTERNO>` é o id do banco — **não** o número de protocolo. **Jamais fabricar**: link errado parece correto no editor e quebra no documento assinado.

O plugin resolve o protocolo por consulta assíncrona ao servidor e grava o resultado em `window._protocoloFormatado`. Por isso **o primeiro clique no OK falha** e o segundo confirma.

Função que funciona:

```js
window.__linkar = function(editorKey, protocolo){
 return new Promise(async (resolve)=>{
  const ed = window.CKEDITOR.instances[editorKey];
  const doc = ed.document.$, body = ed.document.getBody().$;
  const w = doc.createTreeWalker(body, NodeFilter.SHOW_TEXT, null);
  let node=null, idx=-1;
  while(w.nextNode()){ const n=w.currentNode;
    if(n.parentElement && n.parentElement.closest('a')) continue;   // pula já linkados
    const i=n.nodeValue.indexOf(protocolo); if(i>=0){ node=n; idx=i; break; } }
  if(!node) return resolve('NAO_ENCONTRADO');
  const rg = new window.CKEDITOR.dom.range(ed.document);
  rg.setStart(new window.CKEDITOR.dom.node(node), idx);
  rg.setEnd(new window.CKEDITOR.dom.node(node), idx+protocolo.length);
  ed.focus(); ed.getSelection().selectRanges([rg]);
  ed.execCommand('linkseiDialog');
  await new Promise(r=>setTimeout(r,700));
  let d = window.CKEDITOR.dialog.getCurrent();
  if(!d) return resolve('SEM_DIALOGO');
  d.setValueOf('general','protocolo', protocolo);
  window._protocoloFormatado = undefined;
  d.getButton('ok').click();                                        // 1º: dispara consulta
  for(let i=0;i<25;i++){ await new Promise(r=>setTimeout(r,200));
    if(window._protocoloFormatado) break; }
  d = window.CKEDITOR.dialog.getCurrent();
  if(d){ d.getButton('ok').click(); await new Promise(r=>setTimeout(r,500)); }  // 2º: confirma
  const ab = !!window.CKEDITOR.dialog.getCurrent();
  if(ab){ try{ window.CKEDITOR.dialog.getCurrent().hide(); }catch(e){} }
  resolve(ab?'FALHOU':'OK');
 });
};
for(const p of ['0000.000000.00001/2026-00','0012345679','0012345678']){
  await window.__linkar('<idDoCorpo>', p);
}
```

Funciona também com o número do processo formatado. Linkar a **primeira ocorrência** de cada documento; repetições ficam como texto.

### Linkar tudo o que estiver disponível

Depois de injetar o corpo, linke **todos** os processos e documentos citados, não só alguns. O Pet pede isso sempre.

1. Monte a lista com cada número de processo (`0000.000000.00002/2026-00`) e cada número SEI de documento (`0012345670`) citados no corpo.
2. Veja o que **já veio linkado**. Ao receber o texto por `setData`, o SEI às vezes converte sozinho protocolos a que a unidade tem acesso. Conte `body.querySelectorAll('a.ancora_sei')` e tire os já ancorados da lista.
3. Antes do laço, **capture os alertas**. Um alerta nativo trava a extensão:
   ```js
   window.__alertas=[]; window.alert=m=>window.__alertas.push(String(m));
   ```
4. Rode `__linkar` em cada item e guarde o resultado por protocolo.
5. **Protocolo restrito.** `FALHOU` acompanhado do alerta "Unidade atual não possui acesso ao protocolo restrito" significa que a unidade não enxerga o processo, que costuma ser o da contratação, aberto em outra diretoria. Não há contorno: o protocolo fica como texto, com o número SEI e a página, e continua rastreável. Só uma unidade com acesso consegue criar esse link.
6. Informe ao Pet, numa tabela, cada protocolo com ✅ (automático ou pelo diálogo) ou ❌ (restrito).

### Ajustes depois dos links

Depois de linkar, **não** use `setData` com o HTML original, porque isso apaga as âncoras. Para acrescentar no fim (assinatura, parágrafo esquecido), anexe no DOM do corpo e registre a mudança no editor:

```js
const ed=CKEDITOR.instances['<idDoCorpo>'], b=ed.document.getBody().$;
ed.fire('saveSnapshot');
const t=ed.document.$.createElement('div'); t.innerHTML='<p class="...">...</p>';
while(t.firstChild) b.appendChild(t.firstChild);
ed.fire('saveSnapshot'); ed.fire('change');   // checkDirty() deve voltar true
```

Em seguida, confira se a contagem de `a.ancora_sei` continua a mesma.

**Falso positivo:** varrer o texto com `/00\d{8}/` capta números inexistentes formados pela junção de células (ex.: `171.400,00` + `44905200` = `0044905200`). Conferir a lista contra a árvore do processo antes de linkar.

## Cuidados operacionais

- **Salvar primeiro, ajustar depois.** Injete, peça para salvar, só então faça ajustes finos.
- **Sessão expira.** O sintoma é `Erro desconhecido salvando documento`, alerta genérico do navegador. Alerta do navegador **trava a extensão** — só o usuário pode fechar. Depois: relogar e reabrir o documento com hash novo.
- URLs do SEI exigem `infra_hash` de sessão. Não adianta montar URL à mão: retorna "Link sem assinatura". Sempre pedir o link ao usuário.
- `javascript_tool` bloqueia respostas que contenham URLs, tokens ou ids longos. Devolva apenas contagens, prefixos, moldes (`id.replace(/[a-z]/g,'l')`) ou booleanos.
- Nunca clicar em **Assinar**. Salvar só com autorização expressa.
- Navegar para outro documento com alterações não salvas dispara "Leave site?" — abrir aba nova em vez de descartar.
- **Navegador interno do app.** A edição abre em popup, e essa aba não pode ser controlada. Peça ao Pet o link do popup (`acao=editor_montar...`) e abra-o numa aba comum com `preview_start` e `url`. Não reutilize nem registre esse link, porque ele carrega o hash da sessão.

## Bloco de assinatura do Pet (padrão)

Todo documento do Pet **termina com o bloco de assinatura**, logo depois do fecho. Não o esqueça:

```html
<p class="Texto_Justificado_Recuo_Primeira_Linha">Respeitosamente,</p>
<p class="Texto_Centralizado">&nbsp;</p>
<p class="Texto_Centralizado"><strong>NOME COMPLETO</strong><br />Cargo<br />Unidade &ndash; SIGLA<br />Matr&iacute;cula n&ordm; 0000000-0<br />Decreto n&ordm; 0.000-P, de DD de m&ecirc;s de AAAA</p>
```

Se o documento sair em nome de outra pessoa, por exemplo de uma diretora, pergunte o bloco a ela e não reaproveite este.

## Visibilidade de minutas — importante para o fluxo

Documento **não assinado é minuta e só é visível para a unidade que o criou**. Outra unidade vê o documento na árvore mas não consegue abrir, mesmo com o processo tramitado.

Consequência: para outra unidade **ler e assinar**, é obrigatório disponibilizar **bloco de assinatura** para ela. Um bloco por unidade signatária. Disponibilizar na ordem hierárquica do fluxo (diretoria antes do gabinete).

## Redação oficial (Manual de Redação da Presidência, 3ª ed.)

- Vocativo do despacho interno: `Senhor Secretário,` / `Senhora Diretora,` — não usar "Prezado(a)"
- Fecho: **Atenciosamente** (mesma hierarquia ou inferior) · **Respeitosamente** (autoridade superior)
- Citar documento por nome + número SEI: `Despacho nº 1/2026/SIGLA-UNIDADE (0012345671)`
- 1ª pessoa do singular quando o signatário fala por si: `informo`, `encaminho`, `submeto`
- Concisão, clareza, impessoalidade
- Não repetir o número do próprio documento no corpo
- Evitar data por extenso no corpo: o SEI já registra a data da assinatura, e datas divergentes viram achado

## Checklist antes de injetar

- [ ] editor de destino confirmado pelo **conteúdo**, não pelo tamanho
- [ ] nenhum `style=` de fonte, nenhum `<h1>`/`<div>`/`<span>`
- [ ] rótulos de inciso/alínea/número **não** digitados manualmente
- [ ] tabelas com no máximo 6 colunas; densas com `Tabela_Texto_8`
- [ ] documentos citados com número SEI, para linkar depois
- [ ] fecho e **bloco de assinatura presentes** no fim do corpo, com cargo e portaria ou decreto (padrão do Pet acima)
- [ ] nenhuma data redundante no corpo
- [ ] depois de injetar: todos os protocolos citados linkados, e os restritos reportados
