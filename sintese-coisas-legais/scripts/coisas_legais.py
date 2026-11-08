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
  transcrever MIDIA transcreve um vídeo ou áudio sem legenda pelo Gemini do agy
                    (fonte Antigravity) e grava "<nome> - transcrição.md" ao
                    lado dele, no formato do `legenda`: [mm:00] a cada bloco de
                    5 min, pelo tempo real, e [fim mm:ss] no fim
  arquivar ITEM     move o item para _lido, só se a sintese.md já existir e o
                    destino ainda não existir

Só o `transcrever` (a transcrição) e o `arquivar` mexem em disco, e só dentro de
coisas-legais. Nada é apagado nem sobrescrito. Ignora _lido e tudo o que começa
com "_".

Uso:
  python coisas_legais.py listar
  python coisas_legais.py legenda "D:\\00-ENTRADA\\coisas-legais\\<pasta>\\video.pt.srt"
  python coisas_legais.py transcrever "D:\\00-ENTRADA\\coisas-legais\\<pasta>\\video.mp4"
  python coisas_legais.py arquivar "<nome da pasta ou do arquivo>"
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
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


# --- transcrever: Gemini pelo agy --------------------

MODELO_AGY = "gemini-3.8-flash-low"
BLOCO_S = 300  # áudio cortado em blocos de 5 min: tempo real nas marcas e prazo curto por chamada
PRAZO_S = 240
SUFIXO_TRANSCRICAO = " - transcrição.md"
ESQUEMA = {
    "type": "object",
    "properties": {
        "conteudo": {"type": "string", "enum": ["fala", "silencio", "ruido", "musica", "inaudivel"],
                     "description": "o que de fato se ouve no arquivo"},
        "transcricao": {"type": "string", "description": "só a fala ouvida; vazio se conteudo não for fala"},
    },
    "required": ["conteudo", "transcricao"],
}
PROMPT = (
    "Ouça o arquivo de áudio audio.mp3 nesta pasta. Primeiro diga o que de fato se ouve nele: "
    "fala, silêncio, ruído, música ou inaudível. Se houver fala, transcreva-a no idioma em que foi "
    "falada, palavra por palavra, com pontuação e parágrafos, sem marcar tempo nem quem fala. Use a "
    "grafia correta de nomes próprios e de produtos quando forem ditos, sem acrescentar nada que não "
    "foi dito. Devolva só a transcrição, sem comentários e sem título. Se não houver fala, a "
    "transcrição fica vazia. Nunca escreva fala que você não ouviu."
)
RE_COTA = re.compile(r"quota|exhaust|rate.?limit|\b429\b|too many requests|usage limit|limit reached|"
                     r"out of credits|cota", re.IGNORECASE)
RE_LOGIN = re.compile(r"not logged in|log ?in to|sign ?in|unauthenticated|\b401\b", re.IGNORECASE)


def recusar_e_sair(alvo, motivo, codigo=1):
    emitir({"recusado": alvo, "motivo": motivo})
    sys.exit(codigo)


def caminhos_fontes():
    aqui = os.path.dirname(os.path.abspath(__file__))
    casa = os.path.expanduser("~")
    return [os.path.normpath(os.path.join(aqui, "..", "..", "dupla", "scripts", "fontes.ps1")),
            os.path.join(casa, ".agents", "skills", "dupla", "scripts", "fontes.ps1"),
            os.path.join(casa, ".claude", "skills", "dupla", "scripts", "fontes.ps1")]


def conferir_fonte(alvo, arquivo_fontes):
    """Trava global de fontes (dupla/scripts/fontes.ps1). Estado ilegível conta como travado."""
    ps1 = next((c for c in caminhos_fontes() if os.path.isfile(c)), None)
    if not ps1:
        recusar_e_sair(alvo, "⚠️ controle de fontes (fontes.ps1) não encontrado; consumo bloqueado.", 3)
    cmd = ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", ps1, "-Json"]
    if arquivo_fontes:
        cmd += ["-Arquivo", arquivo_fontes]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace",
                              timeout=60, stdin=subprocess.DEVNULL)
        estado = ultimo_json(proc.stdout)
    except (OSError, subprocess.TimeoutExpired):
        estado = None
    if not estado or estado.get("valido") is not True:
        recusar_e_sair(alvo, "⚠️ estado das fontes ilegível ou inválido; consumo bloqueado.", 3)
    if "antigravity" in (estado.get("bloqueadas") or []):
        recusar_e_sair(alvo, "⚠️ Antigravity (agy) travado por você. Sem transcrição: o item fica na raiz.", 3)


def ultimo_json(saida):
    """O agy e o PowerShell podem escrever linhas antes do JSON final."""
    for linha in reversed((saida or "").splitlines()):
        linha = linha.strip()
        if linha.startswith("{"):
            try:
                dados = json.loads(linha)
            except ValueError:
                continue
            if isinstance(dados, dict):
                return dados
    return None


def achar_agy():
    achado = shutil.which("agy")
    if achado:
        return achado
    local = os.path.join(os.environ.get("LOCALAPPDATA", ""), "agy", "bin", "agy.exe")
    return local if os.path.isfile(local) else None


def transcrever_bloco(agy, pasta):
    """Uma chamada ao agy numa pasta que só tem o áudio. Devolve (conteudo, texto)."""
    cmd = [agy, "-p", PROMPT, "--model", MODELO_AGY, "--mode", "plan", "--sandbox",
           "--disable-slash-commands", "--print-timeout", f"{PRAZO_S}s", "--output-format", "json",
           "--json-schema", json.dumps(ESQUEMA, ensure_ascii=False)]
    try:
        proc = subprocess.run(cmd, cwd=pasta, capture_output=True, text=True, encoding="utf-8",
                              errors="replace", timeout=PRAZO_S + 30, stdin=subprocess.DEVNULL)
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"agy não respondeu em {PRAZO_S} s")
    except OSError as erro:
        raise RuntimeError(f"agy não abriu ({agy}): {erro}")
    dados = ultimo_json(proc.stdout) or {}
    est = dados.get("structured_output")
    if dados.get("status") == "SUCCESS" and isinstance(est, dict) and isinstance(est.get("transcricao"), str):
        return est.get("conteudo"), est["transcricao"].strip()
    tudo = f"{proc.stdout}\n{proc.stderr}"
    motivo = " ".join(str(dados.get("error") or tudo.strip()[-300:]).split())[:300]
    if RE_COTA.search(tudo):
        raise RuntimeError(f"cota do agy esgotada: {motivo}")
    if RE_LOGIN.search(tudo):
        raise RuntimeError(f"agy sem login (rode agy no terminal e entre na conta): {motivo}")
    raise RuntimeError(f"agy falhou (rc={proc.returncode}): {motivo or 'saída vazia'}")


def cmd_transcrever(base, caminho, arquivo_fontes):
    midia = os.path.abspath(caminho)
    try:
        rel = os.path.relpath(midia, base)
    except ValueError:  # outro disco
        rel = ".."
    if rel.startswith("..") or rel.split(os.sep)[0].startswith("_"):
        recusar_e_sair(caminho, "só transcrevo item da raiz de coisas-legais (fora de _lido e das pastas com _)")
    if not os.path.isfile(midia):
        recusar_e_sair(caminho, "arquivo não encontrado")
    if tipo_de(os.path.basename(midia)) != "midia":
        recusar_e_sair(caminho, "não é vídeo nem áudio")
    destino = os.path.splitext(midia)[0] + SUFIXO_TRANSCRICAO
    if os.path.exists(destino):
        recusar_e_sair(caminho, f"já existe {destino}; não sobrescrevo")
    conferir_fonte(caminho, arquivo_fontes)
    agy, ffmpeg = achar_agy(), shutil.which("ffmpeg")
    ffprobe = shutil.which("ffprobe")
    if not (agy and ffmpeg and ffprobe):
        falta = [n for n, c in (("agy", agy), ("ffmpeg", ffmpeg), ("ffprobe", ffprobe)) if not c]
        recusar_e_sair(caminho, f"não achei {', '.join(falta)} no PATH")
    try:
        total = float(subprocess.run([ffprobe, "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                                      midia], capture_output=True, text=True, check=True).stdout.strip())
    except (subprocess.CalledProcessError, ValueError):
        recusar_e_sair(caminho, "o ffprobe não leu a duração (arquivo sem áudio ou corrompido?)")

    temp = tempfile.mkdtemp(prefix="cl-audio-")
    try:
        cortes = os.path.join(temp, "cortes")
        os.makedirs(cortes)
        subprocess.run([ffmpeg, "-v", "error", "-i", midia, "-vn", "-ac", "1", "-b:a", "64k", "-f", "segment",
                        "-segment_time", str(BLOCO_S), "-reset_timestamps", "1",
                        os.path.join(cortes, "bloco%03d.mp3")], check=True, stdin=subprocess.DEVNULL)
        blocos = sorted(os.listdir(cortes))
        if not blocos:
            recusar_e_sair(caminho, "o ffmpeg não achou áudio no arquivo")
        partes, com_fala = [], 0
        for i, nome in enumerate(blocos):
            pasta = os.path.join(temp, f"b{i:03d}")  # o agy só enxerga o áudio deste bloco
            os.makedirs(pasta)
            os.replace(os.path.join(cortes, nome), os.path.join(pasta, "audio.mp3"))
            try:
                conteudo, texto = transcrever_bloco(agy, pasta)
            except RuntimeError as erro:
                recusar_e_sair(caminho, f"bloco {i + 1} de {len(blocos)}: {erro}. Nada foi gravado.")
            inicio = i * BLOCO_S // 60
            if conteudo == "fala" and texto:
                com_fala += 1
                partes.append(f"[{inicio:02d}:00] {texto}")
            else:
                partes.append(f"[{inicio:02d}:00] ({conteudo or 'sem fala'})")
    except subprocess.CalledProcessError as erro:
        recusar_e_sair(caminho, f"o ffmpeg falhou (rc={erro.returncode})")
    finally:
        shutil.rmtree(temp, ignore_errors=True)
    if not com_fala:
        recusar_e_sair(caminho, "o Gemini não ouviu fala em nenhum bloco. Nada foi gravado.")

    pasta_item = os.path.dirname(midia)
    titulo = os.path.basename(pasta_item) if pasta_item != base else os.path.splitext(os.path.basename(midia))[0]
    cabecalho = (f"# Transcrição — {titulo}\n\n"
                 f"> Gemini ({MODELO_AGY}) pelo agy, de `{os.path.basename(midia)}`, em "
                 f"{time.strftime('%Y-%m-%d')} · duração {duracao(total)} · sem marcar quem fala\n"
                 f"> Transcrição automática: pode errar palavra, nome e número. [mm:00] marca o início "
                 f"de cada bloco de {BLOCO_S // 60} min, pelo tempo real do áudio.\n\n")
    with open(destino, "x", encoding="utf-8") as f:  # "x": nunca sobrescreve
        f.write(cabecalho + "\n\n".join(partes) + f"\n\n[fim {duracao(total)}]\n")
    emitir({"transcrito": os.path.basename(midia), "para": destino, "duracao": duracao(total),
            "blocos": len(blocos)})


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
    t = sub.add_parser("transcrever")
    t.add_argument("midia")
    t.add_argument("--arquivo-fontes", default="", help=argparse.SUPPRESS)  # só para testar a recusa
    sub.add_parser("arquivar").add_argument("item")
    a = p.parse_args()
    base = os.path.abspath(a.base)
    if a.comando == "listar":
        cmd_listar(base)
    elif a.comando == "lidos":
        cmd_lidos(base)
    elif a.comando == "legenda":
        cmd_legenda(a.arquivo)
    elif a.comando == "transcrever":
        cmd_transcrever(base, a.midia, a.arquivo_fontes)
    else:
        cmd_arquivar(base, a.item)


if __name__ == "__main__":
    main()
