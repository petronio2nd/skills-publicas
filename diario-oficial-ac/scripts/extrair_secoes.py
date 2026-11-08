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
         [--registro DIR_REGISTRO]

Saidas em DIR:
  RESUMO.md            -> ler SEMPRE (intervalos + busca do nome + atos de pessoal)
  <SECAO>_atos.txt     -> so os atos de pessoal da secao  <- leitura normal
  <SECAO>_completo.txt -> secao inteira (consultar so em caso de duvida)
  secoes_recorte.pdf   -> PDF apenas com as paginas das secoes alvo
  mapa_secoes.json     -> intervalos de TODAS as secoes (auditoria)

Registro em DIR_REGISTRO (fixo, fora da pasta temporaria; --registro "" desliga):
  ULTIMO.md            -> a ultima edicao processada (sobrescrito a cada execucao)
  historico.csv        -> uma linha por execucao, a mais recente no fim
  ultimo/<ARQUIVO>.pdf -> copia do PDF original da ultima edicao
"""

import argparse
import contextlib
import csv
import datetime
import hashlib
import json
import os
import re
import shutil
import sys
import time
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


# ----------------------------------------------------------------- registro
# Pasta fixa, fora da saida temporaria: responde "qual foi o ultimo DOE?" depois
# que a sessao acabou e o PDF original (anexo da conversa) ja sumiu.
REGISTRO_PADRAO = os.environ.get("DOE_REGISTRO", "")
ACRE = datetime.timezone(datetime.timedelta(hours=-5))  # UTC-5, sem horario de verao
MESES = {m: i for i, m in enumerate(
    ["JANEIRO", "FEVEREIRO", "MARCO", "ABRIL", "MAIO", "JUNHO", "JULHO",
     "AGOSTO", "SETEMBRO", "OUTUBRO", "NOVEMBRO", "DEZEMBRO"], 1)}
CAMPOS = ["processado_em", "edicao", "data_edicao", "paginas", "arquivo", "sha256",
          "secoes", "atos_pessoal", "alerta_nome", "situacao", "original", "saida"]


def ler_edicao(caminho):
    """Numero e data da edicao, lidos do cabecalho da pag. 1.

    Ed. 14.370: 'Sexta-feira, 09 de Outubro de 2026 ... Ano LIX - n� 14.370
    154 Paginas'. Edicao extra traz letra no numero (14.320-A).
    """
    try:
        with pdfplumber.open(caminho) as pdf:
            ws = [w for w in pdf.pages[0].extract_words() if w["top"] < 160]
    except Exception:
        return {}
    ws.sort(key=lambda w: (round(w["top"]), w["x0"]))
    txt = norm(" ".join(limpar(w["text"]) for w in ws))
    out = {}
    m = re.search(r"\bANO\s+[IVXLC]+\s*-\s*N[O\W]{0,3}\s*(\d{1,2}\.\d{3}(?:\s*-\s*[A-Z]\b)?)", txt)
    if m:
        out["edicao"] = re.sub(r"\s+", "", m.group(1))
    m = re.search(r"(?:FEIRA|SABADO|DOMINGO),?\s+(\d{1,2})\s+DE\s+([A-Z]+)\s+DE\s+(\d{4})", txt)
    if m and m.group(2) in MESES:
        out["data_edicao"] = f"{int(m.group(1)):02d}/{MESES[m.group(2)]:02d}/{m.group(3)}"
    return out


def sha256(caminho):
    h = hashlib.sha256()
    with open(caminho, "rb") as f:
        for bloco in iter(lambda: f.read(1 << 20), b""):
            h.update(bloco)
    return h.hexdigest()


def numero(edicao):
    """'14.370' -> (14370, ''); '14.320-A' -> (14320, 'A'); ilegivel -> None."""
    m = re.match(r"(\d{1,2})\.(\d{3})(?:-([A-Z]))?$", edicao or "")
    return (int(m.group(1) + m.group(2)), m.group(3) or "") if m else None


def fmt_num(n):
    return f"{n // 1000}.{n % 1000:03d}"


def fmt_hora(iso):
    try:
        return f"{datetime.datetime.fromisoformat(iso):%d/%m/%Y %H:%M}"
    except (TypeError, ValueError):
        return iso or "?"


def ler_historico(registro):
    hist = os.path.join(registro, "historico.csv")
    if not os.path.exists(hist):
        return []
    with open(hist, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f, delimiter=";"))


def ordenar(linhas_hist):
    """(com_num, sem_num): uma linha por edicao, a de maior numero primeiro.

    Reprocessar a mesma edicao vale a ultima execucao, sem duplicar.
    """
    por_ed = {}
    for r in linhas_hist:
        k = r.get("edicao") or "sha:" + (r.get("sha256") or "")
        por_ed.pop(k, None)
        por_ed[k] = r
    com_num = sorted((r for r in por_ed.values() if numero(r.get("edicao"))),
                     key=lambda r: numero(r["edicao"]), reverse=True)
    sem_num = [r for r in por_ed.values() if not numero(r.get("edicao"))]
    return com_num, sem_num


def atraso_de(reg, recente):
    """'' se reg e a edicao mais recente; senao, o motivo (texto do ULTIMO.md)."""
    if recente is None or recente.get("edicao") == reg.get("edicao"):
        return ""
    if not numero(reg.get("edicao")):
        return " — numero da edicao nao lido; a copia do PDF nao foi trocada"
    return f" — **ATRASADA**: anterior a mais recente, n. {recente['edicao']}"


def refazer_ultimo(registro):
    """Refaz o ULTIMO.md a partir do historico.csv (a ultima linha e o ultimo
    processamento). Devolve o texto de atraso da ultima linha."""
    linhas_hist = ler_historico(registro)
    if not linhas_hist:
        return ""
    reg = linhas_hist[-1]
    com_num, sem_num = ordenar(linhas_hist)
    recente = com_num[0] if com_num else None
    atraso = atraso_de(reg, recente)

    pasta = os.path.join(registro, "ultimo")
    copias = sorted(n for n in os.listdir(pasta) if n.lower().endswith(".pdf")) \
        if os.path.isdir(pasta) else []

    # so as regulares: uma extra (14.305-A) nao pode esconder a falta da 14.305
    nums = {n for n, letra in (numero(r["edicao"]) for r in com_num) if not letra}
    faltam = [n for n in range(max(nums) - 1, min(nums), -1) if n not in nums] if nums else []
    txt_faltam = ", ".join(fmt_num(n) for n in faltam[:15]) or "nenhuma"
    if len(faltam) > 15:
        txt_faltam += f" e mais {len(faltam) - 15} anteriores"

    def ed(r):
        return (f"n. {r.get('edicao') or '?'}, de {r.get('data_edicao') or '?'}"
                f" ({r.get('paginas') or '?'} paginas)")

    md = ["# Ultimo DOE-AC", ""]
    if recente:
        md.append(f"- **Edicao mais recente recebida:** {ed(recente)}, processada em "
                  f"{fmt_hora(recente.get('processado_em'))}. Alerta do nome: "
                  f"{recente.get('alerta_nome') or '?'}.")
    # de que edicao e cada copia (pelo nome do arquivo, na ultima execucao que o citou)
    ed_do_arq = {os.path.normcase(r.get("arquivo") or ""): r.get("edicao") or "?"
                 for r in linhas_hist}
    txt_copia = ", ".join(f"`ultimo/{n}` (ed. {ed_do_arq.get(os.path.normcase(n), '?')})"
                          for n in copias) or "nenhuma"
    if recente and not any(os.path.normcase(n) == os.path.normcase(recente.get("arquivo") or "")
                           for n in copias):
        txt_copia += (f" — **a da edicao mais recente (n. {recente['edicao']}) nao esta na "
                      f"pasta**: a copia falhou ou o original nao estava disponivel")
    md += [f"- **Ultimo processamento:** {ed(reg)}, em {fmt_hora(reg.get('processado_em'))}"
           f"{atraso}. Situacao: {reg.get('situacao') or '?'}.",
           f"- **Faltam entre as recebidas:** {txt_faltam}",
           f"- **Copia do PDF:** {txt_copia}",
           "", "Horarios no fuso do Acre (UTC-5).", "",
           "## Edicoes recebidas (mais recente primeiro, ate 15)", "",
           "| Edicao | Data | Processada em | Alerta do nome | Atos de pessoal | Arquivo |",
           "|---|---|---|---|---|---|"]
    for r in com_num[:15]:
        md.append(f"| {r['edicao']} | {r.get('data_edicao') or '?'} | "
                  f"{fmt_hora(r.get('processado_em'))} | {r.get('alerta_nome') or '?'} | "
                  f"{r.get('atos_pessoal') or '?'} | `{r.get('arquivo')}` |")
    if sem_num:
        md += ["", "Sem numero lido no cabecalho (conferir no PDF):", ""]
        md += [f"- `{r.get('arquivo')}`, processado em {fmt_hora(r.get('processado_em'))}, "
               f"sha256 `{(r.get('sha256') or '')[:16]}`" for r in sem_num]
    md += ["", f"Historico completo, com secoes, situacao e caminho do original de cada "
               f"execucao: `historico.csv` ({len(linhas_hist)} execucao(oes)).", ""]
    destino = os.path.join(registro, "ULTIMO.md")
    with open(destino + ".tmp", "w", encoding="utf-8") as f:
        f.write("\n".join(md))
    os.replace(destino + ".tmp", destino)
    return atraso


@contextlib.contextmanager
def travar(registro, espera=120, velha=600):
    """Trava por pasta de registro: duas execucoes ao mesmo tempo (duas edicoes
    de uma vez, ou duas sessoes) nao intercalam CSV, copia e ULTIMO.md. Trava
    com mais de 'velha' segundos e de processo que morreu no meio: sai."""
    arq = os.path.join(registro, ".registro.lock")
    fim = time.time() + espera
    while True:
        try:
            fd = os.open(arq, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(fd, str(os.getpid()).encode())
            os.close(fd)
            break
        except FileExistsError:
            try:
                if time.time() - os.path.getmtime(arq) > velha:
                    os.remove(arq)
                    continue
            except OSError:
                pass
            if time.time() > fim:
                raise TimeoutError(f"trava ocupada ha mais de {espera}s: {arq}")
            time.sleep(0.5)
    try:
        yield
    finally:
        with contextlib.suppress(OSError):
            os.remove(arq)


def guardar_copia(orig, pasta, nome):
    """Copia o PDF para pasta/nome e so depois apaga a copia anterior."""
    os.makedirs(pasta, exist_ok=True)
    copia = os.path.join(pasta, nome)
    if os.path.normcase(orig) == os.path.normcase(os.path.abspath(copia)):
        return
    shutil.copy2(orig, copia + ".tmp")
    os.replace(copia + ".tmp", copia)
    for n in os.listdir(pasta):
        if os.path.normcase(n) != os.path.normcase(nome) and n.lower().endswith((".pdf", ".tmp")):
            os.remove(os.path.join(pasta, n))


def registrar(a, reg):
    """Grava uma linha no historico.csv, guarda a copia do PDF e refaz o ULTIMO.md.

    O usuario pode mandar edicoes atrasadas, uma depois da outra ou fora de
    ordem. Por isso "ultimo" e a edicao de maior numero ja recebida, nao a
    ultima processada; uma edicao atrasada entra no historico e nao troca a copia.
    Falha aqui so gera AVISO: o registro nunca derruba a extracao.
    """
    if not a.registro:
        return
    try:
        orig = os.path.abspath(a.pdf)
        reg = dict(reg, processado_em=datetime.datetime.now(ACRE).isoformat(timespec="seconds"),
                   arquivo=os.path.basename(orig), sha256=sha256(orig),
                   original=orig, saida=os.path.abspath(a.out))

        os.makedirs(a.registro, exist_ok=True)
        with travar(a.registro):
            hist = os.path.join(a.registro, "historico.csv")
            novo = not os.path.exists(hist) or os.path.getsize(hist) == 0
            with open(hist, "a", encoding="utf-8-sig", newline="") as f:
                w = csv.DictWriter(f, fieldnames=CAMPOS, delimiter=";")
                if novo:
                    w.writeheader()
                w.writerow({k: reg.get(k, "") for k in CAMPOS})

            # copia do original: so a da edicao mais recente fica na pasta. Falha
            # aqui nao impede o ULTIMO.md, que diz de que edicao e a copia que ficou.
            erro_copia = ""
            com_num, _ = ordenar(ler_historico(a.registro))
            if not atraso_de(reg, com_num[0] if com_num else None):
                try:
                    guardar_copia(orig, os.path.join(a.registro, "ultimo"), reg["arquivo"])
                except Exception as e:
                    erro_copia = f"; AVISO: copia do PDF nao gravada ({e})"

            atraso = refazer_ultimo(a.registro)
        print(f"Registro: ed. {reg.get('edicao') or '?'} de {reg.get('data_edicao') or '?'}"
              + atraso.replace("**", "").replace("—", "-") + erro_copia
              + f"; ULTIMO.md em {a.registro}")
    except Exception as e:
        print(f"AVISO: registro do ultimo DOE nao gravado ({e}).")


# --------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf")
    ap.add_argument("--out", default=".")
    ap.add_argument("--secoes", default="GABINETE DA GOVERNADORA,SEICT")
    ap.add_argument("--nome", default=os.environ.get("DOE_NOME", "Fulano de Tal"))
    ap.add_argument("--registro", default=REGISTRO_PADRAO)
    a = ap.parse_args()

    os.makedirs(a.out, exist_ok=True)
    alvos = [norm(s) for s in a.secoes.split(",") if s.strip()]

    reader = pypdf.PdfReader(a.pdf)
    reg = dict(ler_edicao(a.pdf), paginas=len(reader.pages))
    marcadores = ler_marcadores(reader)
    if not marcadores:
        registrar(a, dict(reg, situacao="sem marcadores (extracao abortada)"))
        sys.exit("ERRO: PDF sem marcadores. Delimitacao automatica nao e confiavel.")

    resumo = []
    paginas = set()
    reg_secoes, reg_atos, avisos = [], [], []

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
            registrar(a, dict(reg, situacao="nada a extrair (sem marcador das secoes alvo)"))
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

            reg_secoes.append(f"{m['secao']} {m['inicio']}-{m['fim']}")
            reg_atos.append(f"{m['secao']} {len(pes)}")
            if m.get("aviso"):
                avisos.append(m["aviso"])
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

    alerta = f"SIM: {len(todos_hits)} ocorrencia(s)" if todos_hits else "nao"
    if parciais:
        alerta += f"; {len(parciais)} so do primeiro nome (conferir)"
    sem = [f"sem marcador: {t}" for t in faltando]
    registrar(a, dict(reg, secoes="; ".join(reg_secoes + sem),
                      atos_pessoal="; ".join(reg_atos), alerta_nome=alerta,
                      situacao="; ".join(["ok"] + [f"AVISO: {x}" for x in avisos])))


if __name__ == "__main__":
    main()
