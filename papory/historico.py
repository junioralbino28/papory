"""Guarda cada ditado (áudio + textos + tempos) na sua máquina, para rever, corrigir e medir depois."""
import json
import shutil
import time
from datetime import datetime
from pathlib import Path

import soundfile as sf

from .config import PASTA

PALAVRAS_POR_MINUTO_DIGITANDO = 40  # base do "tempo poupado"


def pasta():
    return PASTA / "historico"


def salvar(audio, taxa, registro):
    """Grava AAAA-MM-DD/HHMMSS.wav + .json; devolve o caminho do .json."""
    agora = time.localtime()
    dia = pasta() / time.strftime("%Y-%m-%d", agora)
    dia.mkdir(parents=True, exist_ok=True)
    base = dia / time.strftime("%H%M%S", agora)
    n = 2
    while base.with_suffix(".json").exists():  # dois ditados no mesmo segundo
        base = dia / f"{time.strftime('%H%M%S', agora)}-{n}"
        n += 1
    if len(audio):
        sf.write(str(base.with_suffix(".wav")), audio, taxa, subtype="PCM_16")
    base.with_suffix(".json").write_bytes(json.dumps(registro, ensure_ascii=False, indent=1).encode("utf-8"))
    return base.with_suffix(".json")


def _arquivos():
    p = pasta()
    if not p.exists():
        return []
    return sorted(p.glob("*/*.json"), key=lambda f: (f.parent.name, f.stem), reverse=True)


def _ler(arquivo):
    try:
        r = json.loads(arquivo.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    hora = arquivo.stem.split("-")[0]
    try:
        r["_quando"] = datetime.strptime(f"{arquivo.parent.name} {hora}", "%Y-%m-%d %H%M%S")
    except ValueError:
        r["_quando"] = datetime.fromtimestamp(arquivo.stat().st_mtime)
    r["_arquivo"] = arquivo
    wav = arquivo.with_suffix(".wav")
    r["_audio"] = wav if wav.exists() else None
    return r


def listar(limite=None, busca=None):
    """Ditados do mais novo para o mais antigo. busca: trecho do texto (sem diferenciar maiúsculas e acentos)."""
    from .aprendizado import sem_acento
    alvo = sem_acento(busca.strip().lower()) if busca and busca.strip() else None
    saida = []
    for f in _arquivos():
        r = _ler(f)
        if r is None or not r.get("final"):
            continue
        if alvo and alvo not in sem_acento(r["final"].lower()):
            continue
        saida.append(r)
        if limite and len(saida) >= limite:
            break
    return saida


def contar():
    return len(_arquivos())


def estatisticas():
    ditados = palavras = 0
    segundos = 0.0
    primeiro = None
    for f in _arquivos():
        r = _ler(f)
        if r is None or not r.get("final"):
            continue
        ditados += 1
        palavras += len(r["final"].split())
        segundos += float(r.get("duracao_s") or 0)
        primeiro = r["_quando"]
    digitando_min = palavras / PALAVRAS_POR_MINUTO_DIGITANDO
    return {"ditados": ditados, "palavras": palavras, "falando_min": segundos / 60,
            "poupado_min": max(0.0, digitando_min - segundos / 60), "desde": primeiro}


def corrigir(arquivo, texto_novo, trocas):
    """Troca o texto final de um ditado pelo corrigido (o original fica guardado em "final_antes_da_correcao")."""
    arquivo = Path(arquivo)
    r = json.loads(arquivo.read_text(encoding="utf-8"))
    r.setdefault("final_antes_da_correcao", r.get("final"))
    r["final"] = texto_novo
    r["correcao"] = {"quando": datetime.now().isoformat(timespec="seconds"), "trocas": trocas}
    arquivo.write_bytes(json.dumps(r, ensure_ascii=False, indent=1).encode("utf-8"))


def apagar_tudo():
    p = pasta()
    if p.exists():
        shutil.rmtree(p)
