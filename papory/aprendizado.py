"""Aprender com as correções: o que você conserta no histórico vira vocabulário e, se repetir, regra de troca.

Regras:
- marcou "guardar no vocabulário" ao corrigir: a palavra entra na hora;
- a mesma troca corrigida 2 vezes: a palavra entra sozinha e a troca vira regra automática (em todos os apps).
Tudo fica só no computador, em %APPDATA%\\Papory\\correcoes.json.
"""
import difflib
import json
import re
import unicodedata
from datetime import datetime

from .config import PASTA

ARQUIVO = PASTA / "correcoes.json"
VEZES_PARA_APRENDER = 2
PONTUACAO = ".,!?;:…\"'“”()[]"


def sem_acento(texto):
    return "".join(c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn")


def _limpa(palavra):
    return palavra.strip(PONTUACAO)


def diferencas(antes, depois):
    """Trocas palavra a palavra entre o texto do Papory e o corrigido: [(de, para), ...] (só substituições)."""
    a, b = antes.split(), depois.split()
    ca, cb = [_limpa(p).lower() for p in a], [_limpa(p).lower() for p in b]
    trocas = []
    for op, i1, i2, j1, j2 in difflib.SequenceMatcher(None, ca, cb, autojunk=False).get_opcodes():
        if op != "replace":
            continue
        de = " ".join(_limpa(p) for p in a[i1:i2]).strip()
        para = " ".join(_limpa(p) for p in b[j1:j2]).strip()
        if de and para and de != para:
            trocas.append((de, para))
    return trocas


def _ler():
    try:
        return json.loads(ARQUIVO.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"trocas": {}}


def _gravar(dados):
    PASTA.mkdir(parents=True, exist_ok=True)
    ARQUIVO.write_bytes(json.dumps(dados, ensure_ascii=False, indent=1).encode("utf-8"))


def _no_vocabulario(cfg, palavra):
    alvo = sem_acento(palavra.lower())
    return any(sem_acento(v.lower()) == alvo for v in cfg["vocabulario"])


def registrar(cfg, trocas, guardar=()):
    """Conta as trocas e aplica as regras. guardar: palavras que a pessoa mandou pôr no vocabulário já.

    Mexe em cfg (a lista do vocabulário é alterada no lugar, porque o polimento guarda a mesma lista).
    Devolve {"vocabulario": [...], "regras": [...]} com o que foi aprendido agora.
    """
    dados = _ler()
    agora = datetime.now().isoformat(timespec="seconds")
    novas_palavras, novas_regras = [], []
    for de, para in trocas:
        chave = f"{de.lower()}→{para}"
        t = dados["trocas"].setdefault(chave, {"de": de, "para": para, "vezes": 0})
        t["vezes"] += 1
        t["ultima"] = agora
        if (para in guardar or t["vezes"] >= VEZES_PARA_APRENDER) and not _no_vocabulario(cfg, para):
            cfg["vocabulario"].append(para)
            novas_palavras.append(para)
        if t["vezes"] >= VEZES_PARA_APRENDER and len(de) >= 4 and de.lower() != para.lower():
            existe = any(s.get("de", "").lower() == de.lower() for s in cfg["substituicoes"])
            if not existe:
                cfg["substituicoes"].append({"de": de, "para": para, "aprendida": True})
                novas_regras.append((de, para))
    for palavra in guardar:  # marcou para guardar mesmo sem troca detectada (ex.: palavra nova)
        if palavra and not _no_vocabulario(cfg, palavra):
            cfg["vocabulario"].append(palavra)
            novas_palavras.append(palavra)
    _gravar(dados)
    return {"vocabulario": novas_palavras, "regras": novas_regras}


def sugestoes(cfg):
    """Palavras corrigidas que ainda não estão no vocabulário (e que a pessoa não mandou ignorar)."""
    ignoradas = {p.lower() for p in cfg["interface"].get("sugestoes_ignoradas", [])}
    saida = {}
    for t in _ler()["trocas"].values():
        p = t["para"]
        if _no_vocabulario(cfg, p) or p.lower() in ignoradas or not re.search(r"\w", p):
            continue
        atual = saida.get(p.lower())
        if atual is None or t.get("ultima", "") > atual.get("ultima", ""):
            saida[p.lower()] = t
    return sorted(saida.values(), key=lambda t: t.get("ultima", ""), reverse=True)


def ignorar(cfg, palavra):
    lista = cfg["interface"].setdefault("sugestoes_ignoradas", [])
    if palavra not in lista:
        lista.append(palavra)
