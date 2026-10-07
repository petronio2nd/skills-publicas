#!/usr/bin/env python3
"""
extrair_secoes.py — DOE-AC (Diario Oficial do Estado do Acre)

Etapa 1 — DELIMITAR pelos MARCADORES (bookmarks) do PDF o intervalo exato de
paginas de cada secao alvo (padrao: GABINETE DA GOVERNADORA e SEICT).

  Regra de fronteira:
    fim = pagina inicial do marcador seguinte, e:
      - cabecalho da proxima secao no TOPO da pagina  -> fim = proxima - 1
        (ex.: GABINETE 1..7, porque POLICIA CIVIL comeca no topo da pag. 8)
      - cabecalho no MEIO da pagina -> fim = proxima (pagina compartilhada)
        (ex.: SEICT 26..29, porque SEJUSP comeca no meio da pag. 29)
      - cabecalho no topo de uma coluna que nao a primeira, com texto da
        secao antes dele -> tambem pagina compartilhada
        (ex.: SEICT 51..53, SEJUSP no topo da coluna direita da pag. 53)
    Se o cabecalho da propria secao alvo nao aparece na pagina do marcador,
    sai um AVISO (secao provavelmente vazia).

Etapa 2 — RECORTAR e FILTRAR. Reconstroi a ordem de leitura (coluna a coluna),
descarta o que pertence a secoes vizinhas nas paginas compartilhadas, quebra o
texto em atos (LEI / DECRETO / PORTARIA / ...) e separa apenas os atos de
PESSOAL. Tambem faz a busca por nome direto aqui, sem custo de leitura.

Uso:
  python3 extrair_secoes.py ARQUIVO.pdf --out DIR
         [--secoes "GABINETE DA GOVERNADORA,SEICT"] [--nome "Seu Nome"]

Saidas em DIR:
  RESUMO.md            -> ler SEMPRE (intervalos + busca do nome + atos de pessoal)
  <SECAO>_atos.txt     -> so os atos de pessoal da secao  <- leitura normal
  <SECAO>_completo.txt -> secao inteira (consultar so em caso de duvida)
  secoes_recorte.pdf   -> PDF apenas com as paginas das secoes alvo
  mapa_secoes.json     -> intervalos de TODAS as secoes (auditoria)
"""

import argparse
import json
import os
import re
import sys
import unicodedata

import pdfplumber
import pypdf

TOPO_MAX = 100.0   # y (top) abaixo disso = cabecalho no topo da pagina
GUTTER_MIN = 8     # largura minima de calha entre colunas

# inicio de um ato dentro da secao (so vale como titulo se tiver "Nº" ou for CAIXA ALTA)
CABECALHO_ATO = re.compile(
    r"^(LEI|DECRETO|PORTARIA|RESOLU[CÇ][AÃ]O|INSTRU[CÇ][AÃ]O NORMATIVA|ATO|"
    r"EXTRATO|EDITAL|AVISO|TERMO|ERRATA|DESPACHO|CONVITE|RESULTADO|"
    r"CHAMAMENTO|CONTRATO|ORDEM DE SERVI[CÇ]O)\b", re.I)
TEM_NUMERO = re.compile(r"N[ºo°]\s*\.?\s*\d")

# Decreto de pessoal no Acre tem sufixo "-P" no numero (ex.: DECRETO Nº 15.667-P).
# Exige CAIXA ALTA de proposito: titulo publicado vem sempre assim, enquanto
# "Decreto Nº 13.353-P, de 10 de abril de 2026" e citacao dentro do texto.
DECRETO_P = re.compile(r"^DECRETO\s+N[ºo°]\s*\.?\s*[\d.]+\s*-\s*P\b")

# Verbo dispositivo do ato que interessa (estilo do DOE: "Art. 1º Exonerar FULANO").
# Aceita lixo de codificacao entre "Art" e o verbo: ha PDFs em que o ponto vem
# como caractere invalido ("Art� 1º Exonerar ...").
# Decretos "-P" de outra natureza (alterar lotacao, reformar, designar, ceder,
# revogar, agregar) NAO entram: so exoneracao, nomeacao e "sem efeito".
PESSOAL = re.compile(
    r"(?:^|art[^a-zà-ÿ]{0,14})\s*"
    r"(exonerar|nomear|tornar\s+sem\s+efeito|exonera|nomeia|torna\s+sem\s+efeito)\b",
    re.I | re.M)

# linhas de formula, iguais em todo decreto: nao carregam dado de tabela
BOILERPLATE = [
    re.compile(r"^\s*A GOVERNADORA DO ESTADO DO ACRE, no uso", re.I),
    re.compile(r"^\s*(confere|atribui[cç][aã]o|Constitui[cç][aã]o|e tendo em vista)\b.*"
               r"(Acre|Estado|Lei|inciso)", re.I),
    re.compile(r"^\s*RESOLVE:?\s*$", re.I),
    re.compile(r"^\s*art[^a-zà-ÿ]{0,14}\s*Este (Decreto|Ato|Portaria).*vigor", re.I),
    re.compile(r"^\s*Rio Branco\s*[-–/]?\s*Acre,", re.I),
    re.compile(r"Petr[oó]polis e \d+[ºo°]? do Estado", re.I),
    re.compile(r"^\s*\d+[ºo°] da Rep[uú]blica", re.I),
    re.compile(r"^\s*(Mailza Assis Cameli|Governadora do Estado do Acre)\s*$", re.I),
    re.compile(r"^\s*(Registre-se|Publique-se|Cumpra-se)[,.;]?\s*$", re.I),
    # citacao de fundamento legal no preambulo ("art. 52 da Lei Complementar...").
    # Dispositivo real vem com "Art." maiusculo seguido de verbo, entao nao casa.
    re.compile(r"^\s*art\.?\s*\d+[^A-ZÀ-Ý]{0,20}d[ao]s?\s+(Lei|Constitui)", ),
    # fragmentos do cabecalho do jornal que caem no meio do texto
    re.compile(r"^\s*(ESTADO DO ACRE|DO ESTADO|DO ACRE|GOVERNADORA|Oficial|"
               r"Di[aá]rio|Ano [IVXLC]+.*|N[ºo°]\s*[\d.]+\s*\d* P[aá]ginas?)\s*$"),
]


def enxugar(ls):
    """Remove as linhas de formula do ato, preservando o dispositivo."""
    return [l for l in ls if not any(b.search(l) for b in BOILERPLATE)]

# tipos de ato que nunca sao de pessoal
NAO_PESSOAL = re.compile(r"^(LEI|EDITAL|CONVITE|CHAMAMENTO|CONTRATO|"
                         r"TERMO|EXTRATO|AVISO|RESULTADO)\b", re.I)


def limpar(s):
    """Corrige glifos que o PDF nao mapeia (U+FFFD). Em varias edicoes do DOE
    o ponto final vem assim: 'Art� 1º', 'Decreto nº 14�809-P'."""
    s = re.sub("�{3,}", " ", s)   # sequencias longas = ornamento ilegivel
    return s.replace("�", ".")


def norm(s):
    s = unicodedata.normalize("NFKD", str(s))
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", s).strip().upper()


# ---------------------------------------------------------------- marcadores
def ler_marcadores(reader):
    """Lista plana de marcadores: [{title, page(1-based), nivel}] na ordem do sumario."""
    itens = []

    def walk(node, nivel=0):
        for it in node:
            if isinstance(it, list):
                walk(it, nivel + 1)
            else:
                try:
                    pg = reader.get_destination_page_number(it) + 1
                except Exception:
                    continue
                itens.append({"title": str(it.title).strip(), "page": pg, "nivel": nivel})

    walk(reader.outline)
    return itens


# ------------------------------------------------------------------- colunas
def ordem_de_leitura(page):
    """Palavras da pagina na ordem de leitura (coluna esquerda inteira, depois direita)."""
    palavras = [w for w in page.extract_words(extra_attrs=["size", "fontname"])
                if w["top"] > 35]  # ignora numero da pagina / linha de cabecalho
    page.flush_cache()  # sem isso o consumo de memoria explode em edicoes grandes
    if not palavras:
        return [], []

    W = int(page.width) + 1
    cov = [0] * W
    for w in palavras:
        for x in range(max(0, int(w["x0"])), min(W, int(w["x1"]) + 1)):
            cov[x] = 1

    calhas, ini = [], None
    for x in range(15, W - 15):
        if not cov[x]:
            if ini is None:
                ini = x
        else:
            if ini is not None and x - ini >= GUTTER_MIN:
                calhas.append((ini + x) / 2.0)
            ini = None

    if not calhas:
        calhas = [page.width / 2.0]  # DOE-AC e sempre 2 colunas

    limites = [0.0] + calhas + [page.width]

    def col(w):
        centro = (w["x0"] + w["x1"]) / 2.0
        for i in range(len(limites) - 1):
            if limites[i] <= centro < limites[i + 1]:
                # elemento que atravessa a calha = faixa cheia (banner)
                if w["x0"] < limites[i] - 5 or w["x1"] > limites[i + 1] + 5:
                    return -1
                return i
        return len(limites) - 2

    for w in palavras:
        w["_col"] = col(w)
        w["text"] = limpar(w["text"])

    ordenadas = sorted(palavras, key=lambda w: (w["_col"], round(w["top"], 1), w["x0"]))
    # ordem bruta (visual) guardada para localizar cabecalhos centralizados,
    # que podem ficar partidos entre duas colunas
    bruta = sorted(palavras, key=lambda w: (round(w["top"], 1), w["x0"]))
    for i, w in enumerate(ordenadas):
        w["_i"] = i
    return ordenadas, bruta


def linhas(palavras):
    """Agrupa palavras (ja ordenadas) em linhas de texto."""
    out, buf, ref, colr = [], [], None, None
    for w in palavras:
        if ref is None or w["_col"] != colr or abs(w["top"] - ref) > 3:
            if buf:
                out.append(" ".join(buf))
            buf, ref, colr = [], w["top"], w["_col"]
        buf.append(w["text"])
    if buf:
        out.append(" ".join(buf))
    return juntar_hifens(out)


def juntar_hifens(ls):
    """Reune palavras quebradas por hifenizacao no fim da linha ('atra -' + 'ves')."""
    out = []
    for ln in ls:
        ln = ln.rstrip()
        if out and re.search(r"[A-Za-zÀ-ÿ]\s?-$", out[-1]) and re.match(r"^[a-zà-ÿ]", ln):
            out[-1] = re.sub(r"\s?-$", "", out[-1]) + ln
        else:
            out.append(ln)
    return out


def _casar(seq, alvo):
    """Primeira palavra de 'seq' que inicia a sequencia 'alvo' (fonte de titulo)."""
    n = len(alvo)
    for i in range(len(seq) - n + 1):
        if [norm(seq[i + k]["text"]) for k in range(n)] == alvo:
            # cabecalhos do DOE sao Arial ~9.9pt; o corpo e ~6.5pt
            if seq[i]["size"] > 8.5:
                return seq[i]
    return None


def achar_cabecalho(pag, titulo):
    """Palavra inicial do cabecalho da secao. 'pag' = (ordenadas, bruta).

    Tenta primeiro na ordem de leitura; se falhar, tenta na ordem visual —
    cabecalhos centralizados atravessam a calha e ficam partidos entre colunas.
    """
    ordenadas, bruta = pag
    alvo = norm(titulo).split()
    return _casar(ordenadas, alvo) or _casar(bruta, alvo)


def texto_antes(pag, w):
    """Ha texto de coluna antes do cabecalho 'w' na ordem de leitura?

    Faixas cheias (banners, _col = -1) nao contam: abrem a pagina antes de
    qualquer coluna. Tolera umas poucas palavras soltas (numero, rodape).
    """
    antes = [x for x in pag[0][:w["_i"]] if x["_col"] >= 0]
    return len(antes) > 5


# ------------------------------------------------------------------ intervalos
def mapear_secoes(pdf, marcadores, alvos=None):
    """Calcula inicio/fim de cada marcador aplicando a regra de fronteira.

    So abre paginas do PDF para as secoes em 'alvos' (as demais entram no mapa
    com o fim estimado, para auditoria).
    """
    mapa = []
    for i, m in enumerate(marcadores):
        prox = marcadores[i + 1] if i + 1 < len(marcadores) else None
        interessa = alvos is None or norm(m["title"]) in alvos
        if prox is None:
            fim, motivo = len(pdf.pages), "ultima secao do documento"
        elif prox["page"] <= m["page"]:
            fim, motivo = m["page"], "proxima secao comeca na mesma pagina"
        elif not interessa:
            fim, motivo = prox["page"], "estimado (secao fora do escopo)"
        else:
            pag = ordem_de_leitura(pdf.pages[prox["page"] - 1])
            w = achar_cabecalho(pag, prox["title"])
            y = w["top"] if w is not None else None
            if y is None:
                # nao localizado: incluir a pagina inteira e deixar o filtro de
                # atos descartar o que for da secao vizinha (perder ato e pior
                # do que carregar texto a mais)
                fim = prox["page"]
                motivo = (f"cabecalho de '{prox['title']}' nao localizado na pag. "
                          f"{prox['page']}; pagina incluida por precaucao")
            elif y > TOPO_MAX:
                fim = prox["page"]
                motivo = (f"'{prox['title']}' comeca no MEIO da pag. {prox['page']} "
                          f"(y={y:.0f}) -> pagina compartilhada")
            elif texto_antes(pag, w):
                # topo de uma coluna que nao e a primeira: as colunas anteriores
                # ainda sao da secao alvo (ex.: SEJUSP no topo da coluna direita
                # da pag. 53 da ed. 14.367, com a SEICT na esquerda)
                fim = prox["page"]
                motivo = (f"'{prox['title']}' comeca no TOPO da coluna {w['_col'] + 1} "
                          f"da pag. {prox['page']} (y={y:.0f}), com texto da secao "
                          f"antes dele -> pagina compartilhada")
            else:
                fim = prox["page"] - 1
                motivo = (f"'{prox['title']}' comeca no TOPO da pag. "
                          f"{prox['page']} (y={y:.0f})")
        item = {"secao": m["title"], "nivel": m["nivel"],
                "inicio": m["page"], "fim": fim, "criterio": motivo}
        if interessa:
            aviso = conferir_cabecalho(pdf, m)
            if aviso:
                item["aviso"] = aviso
        mapa.append(item)
    return mapa


def conferir_cabecalho(pdf, m):
    """Aviso se o cabecalho da secao nao aparece na pagina do marcador.

    Ed. 14.366: o marcador do Gabinete apontava para a pag. 1, que so tinha
    sumario e Policia Civil; sem o aviso, a saida vinha com atos de outros
    orgaos como se fossem do Gabinete.
    """
    if achar_cabecalho(ordem_de_leitura(pdf.pages[m["page"] - 1]), m["title"]):
        return None
    aviso = (f"marcador de '{m['title']}' (pag. {m['page']}) sem cabecalho "
             f"correspondente; secao provavelmente vazia")
    if m["page"] > 1 and achar_cabecalho(ordem_de_leitura(pdf.pages[m["page"] - 2]),
                                         m["title"]):
        aviso = (f"marcador de '{m['title']}' (pag. {m['page']}) sem cabecalho "
                 f"correspondente, mas o cabecalho esta na pag. {m['page'] - 1}; "
                 f"marcador provavelmente uma pagina adiante -> conferir a pag. "
                 f"{m['page'] - 1}")
    return aviso


def linhas_da_secao(pdf, info, prox_titulo):
    """[(pagina, linha)] da secao, ja sem o conteudo das vizinhas."""
    out = []
    for p in range(info["inicio"], info["fim"] + 1):
        pag = ordem_de_leitura(pdf.pages[p - 1])
        ordenadas = pag[0]
        ini = 0
        if p == info["inicio"]:
            w = achar_cabecalho(pag, info["secao"])
            if w is not None:
                ini = w["_i"]
        fim = len(ordenadas)
        if prox_titulo and p == info["fim"]:
            w = achar_cabecalho(pag, prox_titulo)
            if w is not None and w["_i"] > ini:
                fim = w["_i"]
        for ln in linhas(ordenadas[ini:fim]):
            out.append((p, ln))
    return out


# --------------------------------------------------------------------- atos
def separar_atos(lp):
    """Quebra [(pag, linha)] em atos: [{pag, titulo, linhas[]}]."""
    atos, atual = [], None
    for pag, ln in lp:
        t = ln.strip()
        alfa = [c for c in t if c.isalpha()]
        caixa_alta = bool(alfa) and sum(c.isupper() for c in alfa) / len(alfa) > 0.7
        m = CABECALHO_ATO.match(t)
        # "Decreto Nº X-P, de ..." em caixa mista e citacao dentro do texto,
        # nao um decreto novo. Titulo publicado vem sempre em CAIXA ALTA.
        citacao = bool(m) and m.group(1).upper() == "DECRETO" and not m.group(1).isupper()
        eh_cab = (bool(m) and not citacao and len(t) < 130
                  and (bool(TEM_NUMERO.search(t)) or caixa_alta))
        if eh_cab:
            if atual:
                atos.append(atual)
            atual = {"pag": pag, "titulo": t, "linhas": []}
        elif atual:
            atual["linhas"].append(ln)
        else:
            atual = {"pag": pag, "titulo": "(preambulo da secao)", "linhas": [ln]}
    if atual:
        atos.append(atual)

    # titulo sem corpo = citacao de outro ato dentro do texto corrido, nao um ato novo
    juntos = []
    for x in atos:
        if not x["linhas"] and juntos:
            juntos[-1]["linhas"].append(x["titulo"])
        else:
            juntos.append(x)
    return juntos


def eh_pessoal(ato):
    """Interessa o ato cujo dispositivo exonera, nomeia ou torna sem efeito."""
    tit = ato["titulo"].strip()
    if NAO_PESSOAL.match(tit) and not DECRETO_P.match(tit):
        return False
    return bool(PESSOAL.search("\n".join(ato["linhas"])))


def padrao_tolerante(nome):
    """Regex do nome que aguenta acento nao mapeado pelo PDF.

    Ha edicoes em que o PDF nao mapeia um glifo e ele chega como U+FFFD, que
    limpar() converte em ponto. Se isso acontecer com uma vogal acentuada,
    'JOSÉ' vira 'JOS.' e a busca literal falha justamente no dia em
    que o alerta precisava disparar. Aqui cada letra passivel de acento
    tambem casa com um caractere solto.
    """
    p = []
    for ch in norm(nome):
        if ch == " ":
            p.append(r"[\s.]+")
        elif ch in "AEIOUCN":
            p.append(f"[{ch}.�]")
        else:
            p.append(re.escape(ch))
    return re.compile(r"\b" + "".join(p) + r"\b")


def buscar_nome(lp, nome, tolerante=False):
    """Ocorrencias do nome, com 2 linhas de contexto.

    A busca roda sobre o texto emendado (nao linha a linha): o nome pode estar
    partido pela quebra de linha, e aqui um falso negativo e o erro caro.
    Ignora acento, caixa e a quantidade de espacos.
    """
    if not lp:
        return []
    alvo = norm(nome)
    partes = [norm(ln) for _, ln in lp]
    # posicao inicial de cada linha dentro do texto emendado
    texto, inicios = "", []
    for s in partes:
        inicios.append(len(texto))
        texto += s + " "

    def linha_de(pos):
        i = 0
        for k, ini in enumerate(inicios):
            if ini <= pos:
                i = k
            else:
                break
        return i

    rx = padrao_tolerante(nome) if tolerante else re.compile(re.escape(alvo))
    hits, vistos = [], set()
    for m in rx.finditer(texto):
        i = linha_de(m.start())
        if i in vistos:
            continue
        vistos.add(i)
        ctx = lp[max(0, i - 2):i + 3]
        hits.append({"pagina": lp[i][0],
                     "contexto": "\n".join(f"   {t}" for _, t in ctx)})
    return hits


# --------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf")
    ap.add_argument("--out", default=".")
    ap.add_argument("--secoes", default="GABINETE DA GOVERNADORA,SEICT")
    ap.add_argument("--nome", default=os.environ.get("DOE_NOME", "Fulano de Tal"))
    a = ap.parse_args()

    os.makedirs(a.out, exist_ok=True)
    alvos = [norm(s) for s in a.secoes.split(",") if s.strip()]

    reader = pypdf.PdfReader(a.pdf)
    marcadores = ler_marcadores(reader)
    if not marcadores:
        sys.exit("ERRO: PDF sem marcadores. Delimitacao automatica nao e confiavel.")

    resumo = []
    paginas = set()

    with pdfplumber.open(a.pdf) as pdf:
        mapa = mapear_secoes(pdf, marcadores, alvos)
        with open(os.path.join(a.out, "mapa_secoes.json"), "w", encoding="utf-8") as f:
            json.dump(mapa, f, ensure_ascii=False, indent=2)

        sel = [m for m in mapa if norm(m["secao"]) in alvos]
        faltando = [t for t in alvos if not any(norm(m["secao"]) == t for m in sel)]
        for t in faltando:
            print(f"AVISO: sem marcador para '{t}' -> secao ignorada.")
        if not sel:
            msg = ("NADA A EXTRAIR: esta edicao nao possui marcador de nenhuma das "
                   "secoes alvo. Nenhum arquivo foi gerado.")
            print(msg)
            with open(os.path.join(a.out, "RESUMO.md"), "w", encoding="utf-8") as f:
                f.write("# DOE-AC\n\n" + msg + "\n")
            return

        resumo.append(f"# DOE-AC — {os.path.basename(a.pdf)}\n")
        resumo.append("## Secoes extraidas\n")
        todos_hits, parciais = [], []

        for m in sel:
            idx = mapa.index(m)
            prox = mapa[idx + 1]["secao"] if idx + 1 < len(mapa) else None
            lp = linhas_da_secao(pdf, m, prox)
            paginas.update(range(m["inicio"], m["fim"] + 1))

            atos = separar_atos(lp)
            pes = [x for x in atos if eh_pessoal(x)]
            nome_arq = re.sub(r"[^A-Za-z0-9]+", "_", norm(m["secao"])).strip("_")

            with open(os.path.join(a.out, f"{nome_arq}_completo.txt"), "w",
                      encoding="utf-8") as f:
                f.write(f"# {m['secao']} — paginas {m['inicio']}-{m['fim']}\n")
                pag = None
                for p, ln in lp:
                    if p != pag:
                        f.write(f"\n===== [pag. {p}] =====\n")
                        pag = p
                    f.write(ln + "\n")

            with open(os.path.join(a.out, f"{nome_arq}_atos.txt"), "w",
                      encoding="utf-8") as f:
                f.write(f"# {m['secao']} — atos de pessoal "
                        f"({len(pes)} de {len(atos)} atos; pags. {m['inicio']}-{m['fim']})\n")
                for x in pes:
                    f.write(f"\n----- [pag. {x['pag']}] {x['titulo']}\n")
                    f.write("\n".join(enxugar(x["linhas"])) + "\n")

            hits = buscar_nome(lp, a.nome)
            todos_hits += [dict(h, secao=m["secao"]) for h in hits]
            # rede de seguranca: so o primeiro nome, caso o sobrenome venha
            # escrito de outro jeito ou haja nome do meio entre os dois
            pags = {h["pagina"] for h in hits}
            # variacao de codificacao (acento que o PDF nao mapeou)
            for h in buscar_nome(lp, a.nome, tolerante=True):
                if h["pagina"] not in pags:
                    pags.add(h["pagina"])
                    todos_hits.append(dict(h, secao=m["secao"], obs="grafia alterada"))
            # rede de seguranca: so o primeiro nome, caso o sobrenome venha
            # escrito de outro jeito ou haja nome do meio entre os dois
            prim = norm(a.nome).split()[0]
            if len(prim) >= 6:
                parciais += [dict(h, secao=m["secao"])
                             for h in buscar_nome(lp, prim, tolerante=True)
                             if h["pagina"] not in pags]

            if m.get("aviso"):
                print(f"AVISO: {m['aviso']}.")
            print(f"  {m['secao']}: paginas {m['inicio']}-{m['fim']}  ({m['criterio']})")
            print(f"    atos: {len(pes)} de pessoal, de {len(atos)} no total")
            aviso = f"  **AVISO: {m['aviso']}.**  \n" if m.get("aviso") else ""
            resumo.append(f"- **{m['secao']}** — paginas {m['inicio']}-{m['fim']}  \n"
                          f"{aviso}"
                          f"  criterio: {m['criterio']}  \n"
                          f"  atos de pessoal: {len(pes)} de {len(atos)}  \n"
                          f"  arquivo: `{nome_arq}_atos.txt`")

        resumo.append(f"\nPaginas mantidas: {len(paginas)} de {len(reader.pages)} "
                      f"({len(reader.pages) - len(paginas)} descartadas)\n")

        resumo.append(f"## Alerta — \"{a.nome}\"\n")
        if todos_hits:
            resumo.append(f"**ATENCAO: NOME ENCONTRADO em {len(todos_hits)} ponto(s) "
                          f"desta edicao.** Leia cada trecho e diga do que se trata.\n")
            for h in todos_hits:
                obs = f" [{h['obs']}]" if h.get("obs") else ""
                resumo.append(f"- {h['secao']}, pag. {h['pagina']}{obs}:\n"
                              f"```\n{h['contexto']}\n```")
        else:
            resumo.append(f"SEM ALERTA: \"{a.nome}\" nao aparece nesta edicao "
                          f"(busca sobre o texto emendado, imune a quebra de linha).")
        if parciais:
            resumo.append(f"\nOcorrencias apenas do primeiro nome ({len(parciais)}) — "
                          f"conferir se e a mesma pessoa:\n")
            for h in parciais:
                resumo.append(f"- {h['secao']}, pag. {h['pagina']}:\n"
                              f"```\n{h['contexto']}\n```")
        print(f"  alerta '{a.nome}': {len(todos_hits)} ocorrencia(s), "
              f"{len(parciais)} parcial(is)")

    w = pypdf.PdfWriter()
    for p in sorted(paginas):
        w.add_page(reader.pages[p - 1])
    with open(os.path.join(a.out, "secoes_recorte.pdf"), "wb") as f:
        w.write(f)

    with open(os.path.join(a.out, "RESUMO.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(resumo) + "\n")
    print(f"Gerado em {a.out}: RESUMO.md, *_atos.txt, *_completo.txt, secoes_recorte.pdf")


if __name__ == "__main__":
    main()
