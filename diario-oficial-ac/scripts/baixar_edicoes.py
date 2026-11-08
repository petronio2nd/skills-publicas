#!/usr/bin/env python3
"""
baixar_edicoes.py — baixa edicoes do DOE-AC do site oficial (diario.ac.gov.br).

Uso:
  python baixar_edicoes.py 14371 14372 [--out DIR]   edicoes pelo numero
  python baixar_edicoes.py --faltam [--out DIR]      o que ainda nao passou pelo
         registro, nas ultimas --janela edicoes do site (padrao 20), sem descer
         abaixo da edicao mais antiga do registro: lacunas, edicoes publicadas
         depois da mais recente recebida e cadernos extras (14372-A, 14372-B);
         com o registro vazio, so a ultima edicao do site
  [--listar]   so mostra, nao baixa
  [--registro DIR_REGISTRO]   o mesmo do extrair_secoes.py

Uma edicao pode ter mais de um arquivo (Caderno Principal, 14372-A, 14372-B):
vem tudo, em DIR/<numero>/. No fim sai uma linha "PDF: <caminho>" por arquivo,
na ordem certa para rodar o extrair_secoes.py (mais antiga primeiro).

O site: a busca por numero e um POST "numero=<n>" na pagina inicial, que
devolve uma tabela (data, descricao, link download.php?arquivo=<base64>,
tamanho). O base64 e "(D1@r7#!)" + nome do PDF (DO<carimbo>.pdf), o mesmo
nome que o extrair_secoes.py grava no historico.csv. A pagina inicial traz
"Diario Oficial n. <ultima>" e o link dela (a.edhoje). A busca por numero leva
algumas horas para indexar a edicao do dia: enquanto vem vazia, a ultima
edicao sai pelo link a.edhoje (so o caderno que ele aponta).
"""

import argparse
import base64
import html
import os
import re
import shutil
import sys
import unicodedata
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from extrair_secoes import REGISTRO_PADRAO, ler_historico, numero  # noqa: E402

SITE = "https://diario.ac.gov.br/"
CABECALHOS = {"User-Agent": "Mozilla/5.0 (diario-oficial-ac)"}
LINHA = re.compile(
    r"<tr[^>]*>\s*<td>\s*([\d/]+)\s*</td>\s*<td>\s*"
    r"<a href=\"([^\"]*download\.php\?arquivo=[^\"]+)\"[^>]*>(.*?)</a>\s*</td>\s*"
    r"<td[^>]*>([^<]*)</td>", re.S)


def pedir(dados=None, timeout=60):
    corpo = urllib.parse.urlencode(dados).encode() if dados else None
    req = urllib.request.Request(SITE, data=corpo, headers=CABECALHOS)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("iso-8859-1")


def ultima_no_site():
    """(numero, url do link "Ultima edicao", data) da pagina inicial; numero None se nao achou."""
    t = pedir()
    m = re.search(r"Diario Oficial n\S*\s*(\d{4,6})", t, re.I)
    if not m:
        return None, None, ""
    u = re.search(r"<a href=\"([^\"]*download\.php\?arquivo=[^\"]+)\"[^>]*class=\"edhoje\"", t)
    d = re.search(r"(\d{1,2}) de (\w+) de (\d{4})", t[m.end():m.end() + 400])
    return int(m.group(1)), html.unescape(u.group(1)) if u else None, d.group(0) if d else "?"


def pelo_link_da_ultima(n, url, data):
    """A edicao do dia antes de a busca indexar: o caderno do link a.edhoje.

    letra None: nao se sabe o caderno, entao so o nome do arquivo decide se ja esta no registro."""
    nome = nome_do_arquivo(url)
    if not nome:
        return []
    return [{"data": data, "descricao": f"Diario Oficial n. {n} (link Ultima edicao; a busca ainda nao indexou)",
             "url": url, "tamanho": "?", "nome": nome, "letra": None}]


def nome_do_arquivo(url):
    """'download.php?arquivo=KEQx...' -> 'DO17918950062237.pdf' (ou None)."""
    b64 = urllib.parse.parse_qs(urllib.parse.urlparse(url).query).get("arquivo", [""])[0]
    try:
        nome = base64.b64decode(b64 + "=" * (-len(b64) % 4)).decode("latin-1")
    except ValueError:
        return None
    nome = re.sub(r"^\(.*?\)", "", nome)
    return nome if re.fullmatch(r"[A-Za-z0-9._-]+\.pdf", nome, re.I) else None


def arquivos_da_edicao(n):
    """[{data, descricao, url, tamanho, nome, letra}] da busca por numero; [] se nao ha.

    letra: '' no caderno principal (ou unico), 'A' em '14372-A' etc."""
    t = pedir({"numero": str(n)})
    i = t.find('class="resultados_busca"')
    if i < 0:
        return []
    out = []
    for data, url, desc, tam in LINHA.findall(t[i:]):
        desc = " ".join(html.unescape(re.sub(r"<[^>]+>", " ", desc)).split())
        desc = unicodedata.normalize("NFKD", desc).encode("ascii", "ignore").decode()
        if not re.search(rf"\bN\S*\s*{n}\b", desc):  # so desta edicao
            continue
        url = html.unescape(url)
        letra = re.search(rf"\b{n}\s*-\s*([A-Z])\b", desc)
        out.append({"data": data, "descricao": desc, "url": url, "tamanho": tam.strip(),
                    "nome": nome_do_arquivo(url) or f"{n}-{len(out) + 1}.pdf",
                    "letra": letra.group(1) if letra else ""})
    return out


def pdf_inteiro(caminho):
    """Comeca com %PDF- e tem %%EOF no fim (download cortado no meio nao tem)."""
    try:
        with open(caminho, "rb") as f:
            if f.read(5) != b"%PDF-":
                return False
            f.seek(0, os.SEEK_END)
            f.seek(max(0, f.tell() - 4096))
            return b"%%EOF" in f.read()
    except OSError:
        return False


def baixar(url, destino):
    part = destino + ".part"
    try:
        req = urllib.request.Request(url, headers=CABECALHOS)
        with urllib.request.urlopen(req, timeout=300) as r, open(part, "wb") as f:
            esperado = r.headers.get("Content-Length", "")
            shutil.copyfileobj(r, f)
            recebido = f.tell()
        # a conexao pode cair sem excecao antes do Content-Length
        if esperado.isdigit() and int(esperado) != recebido:
            raise ValueError(f"download incompleto ({recebido} de {esperado} bytes)")
        if not pdf_inteiro(part):
            raise ValueError("o site nao devolveu um PDF inteiro")
        os.replace(part, destino)
    finally:
        if os.path.exists(part):
            os.remove(part)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("numeros", nargs="*", help="numeros das edicoes (14371 ou 14.371)")
    ap.add_argument("--faltam", action="store_true")
    ap.add_argument("--janela", type=int, default=20)
    ap.add_argument("--listar", action="store_true")
    ap.add_argument("--out", default=os.path.join(os.environ.get("TEMP", "."), "doe-baixar"))
    ap.add_argument("--registro", default=REGISTRO_PADRAO)
    a = ap.parse_args()
    sys.stdout.reconfigure(errors="replace")  # console cp1252 e descricoes com acento

    hist = ler_historico(a.registro) if a.registro else []
    ja = {os.path.normcase(r.get("arquivo") or "") for r in hist}
    ja_ed = {numero(r.get("edicao")) for r in hist} - {None}  # {(14372, ''), (14372, 'A')}

    ultima, url_ultima, data_ultima = None, None, ""
    if a.numeros:
        alvo = sorted({int(re.sub(r"\D", "", x)) for x in a.numeros})
    elif a.faltam:
        ultima, url_ultima, data_ultima = ultima_no_site()
        if ultima is None:
            sys.exit("ERRO: nao achei o numero da ultima edicao na pagina inicial do site.")
        recebidas = [numero(r.get("edicao"))[0] for r in hist if numero(r.get("edicao"))]
        # registro vazio: so a ultima, para nao baixar 20 PDFs de 13 a 47 MB
        ini = max(ultima - a.janela + 1, min(recebidas)) if recebidas else ultima
        alvo = list(range(ini, ultima + 1))
        print(f"Ultima edicao no site: {ultima}. Conferindo {ini} a {ultima} contra o registro.")
    else:
        sys.exit("ERRO: diga os numeros das edicoes ou use --faltam.")

    pdfs, sem, listados, falhas = [], [], 0, 0
    for n in alvo:
        try:
            arqs = arquivos_da_edicao(n)
        except Exception as e:
            print(f"  {n}: ERRO na busca ({e})")
            falhas += 1
            continue
        if not arqs and a.numeros:
            try:  # pedida pelo numero: pode ser a do dia, ainda fora da busca
                u, url_ultima, data_ultima = ultima_no_site()
                ultima = u
            except Exception:
                pass
        if not arqs and n == ultima and url_ultima:
            arqs = pelo_link_da_ultima(n, url_ultima, data_ultima)
        if not arqs:
            sem.append(n)
            continue
        for x in arqs:
            novo = os.path.normcase(x["nome"]) not in ja and (n, x["letra"]) not in ja_ed
            if a.faltam and not novo:
                continue
            marca = "" if novo else " (ja no registro)"
            destino = os.path.join(a.out, str(n), x["nome"])
            if a.listar:
                print(f"  {n}: {x['descricao']} | {x['data']} | {x['tamanho']}{marca}")
                listados += 1
                continue
            if pdf_inteiro(destino):
                print(f"  {n}: {x['descricao']} -> ja baixado{marca}")
            else:
                if os.path.exists(destino):
                    print(f"  {n}: {x['descricao']} -> o baixado antes esta incompleto; baixando de novo")
                os.makedirs(os.path.dirname(destino), exist_ok=True)
                try:
                    baixar(x["url"], destino)
                except Exception as e:
                    print(f"  {n}: {x['descricao']} -> ERRO no download ({e})")
                    falhas += 1
                    continue
                print(f"  {n}: {x['descricao']} | {x['tamanho']} -> baixado{marca}")
            pdfs.append(destino)

    if sem:
        # a numeracao e corrida: no --faltam, edicao sem arquivo e anomalia (ou o site mudou)
        print("Sem arquivo no site: " + ", ".join(map(str, sem))
              + (" (a numeracao e corrida: confira no site)" if a.faltam else ""))
    problemas = falhas + (len(sem) if a.faltam else 0)
    if problemas:
        print(f"ATENCAO: {problemas} problema(s) acima; a conferencia nao foi completa.")
    elif a.faltam and not pdfs and not listados:
        print("Nada falta: todas as edicoes conferidas ja passaram pelo registro.")
    for p in pdfs:
        print(f"PDF: {p}")
    if problemas:
        sys.exit(1)


if __name__ == "__main__":
    main()
