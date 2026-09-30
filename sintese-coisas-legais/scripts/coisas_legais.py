#!/usr/bin/env python3
"""
coisas_legais.py: apoio da skill sintese-coisas-legais.

Comandos:
  listar            um JSON por item da raiz de coisas-legais, com o estado
                    (novo, repetido, falta_mover, incompleto), do mais antigo
                    para o mais novo, e no fim uma linha de resumo
  lidos             um JSON por item de _lido, com o título da sintese.md
  legenda ARQUIVO   texto de um .srt ou .vtt, sem números, tempos, marcas nem
                    repetição, com um marcador [mm:00] a cada minuto e, no fim,
                    [fim mm:ss] com o tempo da última fala
  arquivar ITEM     move o item para _lido, só se a sintese.md já existir e o
                    destino ainda não existir

Só o `arquivar` mexe em disco, e só dentro de coisas-legais. Nada é apagado.
Ignora _lido e tudo o que começa com "_".

Uso:
  python coisas_legais.py listar
  python coisas_legais.py legenda "D:\\00-ENTRADA\\coisas-legais\\<pasta>\\video.pt.srt"
  python coisas_legais.py arquivar "<nome da pasta ou do arquivo>"
"""

import argparse
import json
import os
import re
import sys
import time

BASE = r"D:\00-ENTRADA\coisas-legais"
LIDO = "_lido"
SINTESE = "sintese.md"
FICHAS = ("post.json", "video.json")
RECENTE = 3 * 3600  # a D:\00-ENTRADA entra no Pepita a cada 3 h

TIPOS = {
    "texto": {".md", ".txt"},
    "legenda": {".srt", ".vtt"},
    "imagem": {".jpg", ".jpeg", ".png", ".gif", ".webp"},
    "midia": {".mp4", ".webm", ".mkv", ".mov", ".mp3", ".m4a", ".wav", ".ogg", ".opus"},
    "pepita": {".pdf", ".docx", ".doc", ".xlsx", ".xls", ".pptx", ".ppt", ".odt"},
}
PARCIAL = (".crdownload", ".part", ".tmp", ".ytdl")
IGNORAR = {"desktop.ini", "thumbs.db"}


def emitir(obj):
    print(json.dumps(obj, ensure_ascii=False))


def tipo_de(nome):
    if nome.lower() in FICHAS:
        return "ficha"
    ext = os.path.splitext(nome)[1].lower()
    for tipo, exts in TIPOS.items():
        if ext in exts:
            return tipo
    return "outro"


def ler_ficha(pasta):
    for nome in FICHAS:
        caminho = os.path.join(pasta, nome)
        if os.path.isfile(caminho):
            try:
                with open(caminho, encoding="utf-8") as f:
                    return json.load(f)
            except (OSError, ValueError):
                return None
    return None


def link_de(ficha):
    link = ficha.get("webpage_url") or ficha.get("url") or ficha.get("paginaDoPost") or ""
    return link.rstrip("/")


def duracao(segundos):
    if not isinstance(segundos, (int, float)):
        return None
    s = int(segundos)
    h, m, s = s // 3600, s % 3600 // 60, s % 60
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def resumo_ficha(ficha):
    """O que interessa da ficha para a síntese e para achar repetidos."""
    if not ficha:
        return {}
    autor = ficha.get("autor")
    data = str(ficha.get("upload_date") or "")
    r = {
        "id": str(ficha.get("id") or "") or None,
        "link": link_de(ficha) or None,
        "autor": autor.get("nome") if isinstance(autor, dict) else (ficha.get("channel") or ficha.get("uploader")),
        "titulo": ficha.get("title"),
        "publicado": f"{data[:4]}-{data[4:6]}-{data[6:]}" if len(data) == 8 else None,
        "duracao": duracao(ficha.get("duration")),
        "salvo_em": ficha.get("salvoEm"),
    }
    return {k: v for k, v in r.items() if v}


def indice_lido(base):
    """id e link de cada item já lido, para não reprocessar o que as extensões regravaram."""
    ids, links = {}, {}
    lido = os.path.join(base, LIDO)
    if not os.path.isdir(lido):
        return ids, links
    for nome in os.listdir(lido):
        f = resumo_ficha(ler_ficha(os.path.join(lido, nome)))
        if f.get("id"):
            ids[f["id"]] = nome
        if f.get("link"):
            links[f["link"]] = nome
    return ids, links


def descrever(base, nome, ids, links):
    caminho = os.path.join(base, nome)
    lido = os.path.join(base, LIDO)
    if os.path.isdir(caminho):
        arquivos, pastas, mtimes = [], [], []
        for n in sorted(os.listdir(caminho)):
            c = os.path.join(caminho, n)
            if os.path.isdir(c):
                pastas.append(n)
            elif n.lower() not in IGNORAR:
                arquivos.append({"nome": n, "tipo": tipo_de(n), "bytes": os.path.getsize(c)})
                mtimes.append(os.path.getmtime(c))
        item = {"item": nome, "forma": "pasta", "arquivos": arquivos}
        if pastas:
            item["subpastas"] = pastas
        item.update(resumo_ficha(ler_ficha(caminho)))
        mtime = max(mtimes) if mtimes else os.path.getmtime(caminho)
        ja_lido = ids.get(item.get("id")) or links.get(item.get("link"))
        if any(a["nome"].lower().endswith(PARCIAL) for a in arquivos):
            estado = "incompleto"
        elif ja_lido or os.path.exists(os.path.join(lido, nome)):
            estado, item["em_lido"] = "repetido", ja_lido or nome
        elif os.path.isfile(os.path.join(caminho, SINTESE)):
            estado = "falta_mover"
        else:
            estado = "novo"
    else:
        radical = os.path.splitext(nome)[0]
        destino = os.path.join(lido, radical)
        item = {"item": nome, "forma": "arquivo", "tipo": tipo_de(nome), "bytes": os.path.getsize(caminho)}
        mtime = os.path.getmtime(caminho)
        if nome.lower().endswith(PARCIAL):
            estado = "incompleto"
        elif os.path.exists(os.path.join(destino, nome)):
            estado, item["em_lido"] = "repetido", radical
        elif os.path.isfile(os.path.join(destino, SINTESE)):
            estado = "falta_mover"
        elif os.path.exists(destino):
            estado, item["em_lido"] = "repetido", radical
        else:
            estado = "novo"
    item["estado"] = estado
    item["modificado"] = time.strftime("%Y-%m-%d %H:%M", time.localtime(mtime))
    if time.time() - mtime < RECENTE:
        item["recente"] = True  # pode ainda não estar no Pepita
    item["_ordem"] = item.get("salvo_em") or time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(mtime))
    return item


def cmd_listar(base):
    ids, links = indice_lido(base)
    itens = [descrever(base, n, ids, links) for n in os.listdir(base)
             if not n.startswith("_") and n.lower() not in IGNORAR]
    itens.sort(key=lambda i: i.pop("_ordem"))
    contagem = {}
    for item in itens:
        emitir(item)
        contagem[item["estado"]] = contagem.get(item["estado"], 0) + 1
    emitir({"resumo": contagem, "base": base})


def cmd_lidos(base):
    lido = os.path.join(base, LIDO)
    if not os.path.isdir(lido):
        return
    for nome in sorted(os.listdir(lido)):
        titulo = None
        caminho = os.path.join(lido, nome, SINTESE)
        if os.path.isfile(caminho):
            with open(caminho, encoding="utf-8", errors="replace") as f:
                for linha in f:
                    if linha.startswith("# "):
                        titulo = linha[2:].strip()
                        break
        emitir({"pasta": nome, "titulo": titulo})


TEMPO = re.compile(r"^\s*(?:(\d+):)?(\d{1,2}):(\d{2})[.,]\d{3}\s*-->")
FIM = re.compile(r"-->\s*(?:(\d+):)?(\d{1,2}):(\d{2})[.,]\d{3}")


def cmd_legenda(caminho):
    with open(caminho, encoding="utf-8-sig", errors="replace") as f:
        linhas = [l.strip() for l in f.read().splitlines()]
    partes, anterior, minuto, fim, i = [], None, -1, None, 0
    while i < len(linhas):
        s = linhas[i]
        seguinte = linhas[i + 1] if i + 1 < len(linhas) else ""
        i += 1
        if not s or s.startswith("WEBVTT") or TEMPO.match(seguinte):
            continue  # linha vazia, cabeçalho ou número/identificador da fala
        if re.match(r"^(NOTE|STYLE|REGION)\b", s):
            while i < len(linhas) and linhas[i]:
                i += 1  # bloco de comentário do VTT vai até a linha em branco
            continue
        tempo = TEMPO.match(s)
        if tempo:
            h, m, _ = (int(g or 0) for g in tempo.groups())
            if h * 60 + m > minuto:
                minuto = h * 60 + m
                partes.append(f"\n[{minuto:02d}:00]")
            ate = FIM.search(s)
            if ate:
                h, m, seg = (int(g or 0) for g in ate.groups())
                fim = max(fim or 0, h * 3600 + m * 60 + seg)
            continue
        s = re.sub(r"<[^>]+>|\{\\[^}]*\}", "", s)  # <c>, <i>, <00:00:01.000>, {\an8}
        s = re.sub(r"\s+", " ", s).strip()
        if s and s != anterior:
            partes.append(s)
            anterior = s
    if fim is not None:
        partes.append(f"\n[fim {duracao(fim)}]")  # o vídeo do LinkedIn não traz duração na ficha
    print(" ".join(partes).strip())


def cmd_arquivar(base, nome):
    def recusar(motivo):
        emitir({"recusado": nome, "motivo": motivo})
        sys.exit(1)

    if not nome or nome != os.path.basename(nome) or nome.startswith((".", "_")):
        recusar("nome inválido: passe só o nome do item na raiz de coisas-legais")
    origem = os.path.join(base, nome)
    lido = os.path.join(base, LIDO)
    if os.path.isdir(origem):
        sintese = os.path.join(origem, SINTESE)
        destino = os.path.join(lido, nome)
    elif os.path.isfile(origem):
        pasta = os.path.join(lido, os.path.splitext(nome)[0])
        sintese = os.path.join(pasta, SINTESE)
        destino = os.path.join(pasta, nome)
    else:
        recusar("não existe na raiz de coisas-legais")
    if not os.path.isfile(sintese) or os.path.getsize(sintese) == 0:
        recusar(f"falta a síntese: grave antes {sintese}")
    if os.path.exists(destino):
        recusar(f"já existe {destino}; não sobrescrevo")
    os.makedirs(os.path.dirname(destino), exist_ok=True)
    os.rename(origem, destino)  # mesmo disco: só muda de lugar, nunca copia e apaga
    emitir({"movido": nome, "para": destino})


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--base", default=BASE, help=argparse.SUPPRESS)
    sub = p.add_subparsers(dest="comando", required=True)
    sub.add_parser("listar")
    sub.add_parser("lidos")
    sub.add_parser("legenda").add_argument("arquivo")
    sub.add_parser("arquivar").add_argument("item")
    a = p.parse_args()
    base = os.path.abspath(a.base)
    if a.comando == "listar":
        cmd_listar(base)
    elif a.comando == "lidos":
        cmd_lidos(base)
    elif a.comando == "legenda":
        cmd_legenda(a.arquivo)
    else:
        cmd_arquivar(base, a.item)


if __name__ == "__main__":
    main()
