"""Atualização: pergunta ao GitHub se há versão nova, baixa conferindo a impressão digital e instala.

Só a pergunta sai do computador (qual é a versão mais nova); nada da pessoa vai junto.
- Windows: baixa o instalador, confere o SHA-256 que o GitHub publica, instala sem janelas e o Papory reabre
  sozinho (o instalador é por usuário: não pede permissão de administrador).
- Mac: baixa o .dmg certo (Apple Silicon ou Intel), confere e abre; a troca do app é manual, porque sem a
  assinatura paga da Apple trocar o app sozinho faria perder as permissões.
"""
import hashlib
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import requests

from . import __version__

API = "https://api.github.com/repos/junioralbino28/papory/releases/latest"
PASTA = Path(tempfile.gettempdir()) / "Papory-atualizacao"
INTERVALO_S = 6 * 3600   # de quanto em quanto tempo pergunta de novo, com o Papory aberto


def versao_tupla(texto):
    """'v0.1.10' -> (0, 1, 10). Comparar texto direto erraria: '0.1.10' < '0.1.9'."""
    return tuple(int(n) for n in re.findall(r"\d+", texto or "")[:3])


def _mac_apple_silicon():
    if platform.machine() == "arm64":
        return True
    try:  # o Papory Intel rodando no Rosetta se vê como x86_64; o sistema sabe a verdade
        saida = subprocess.run(["sysctl", "-n", "hw.optional.arm64"], capture_output=True, text=True, timeout=3)
        return saida.stdout.strip() == "1"
    except (OSError, subprocess.SubprocessError):
        return False


def arquivo_deste_sistema(nomes):
    """Qual dos arquivos da versão serve aqui (None se nenhum)."""
    if sys.platform == "win32":
        quer = re.compile(r"^Papory-Setup-[\d.]+\.exe$")
    elif sys.platform == "darwin":
        quer = re.compile(rf"^Papory-[\d.]+-Mac-{'Apple-Silicon' if _mac_apple_silicon() else 'Intel'}\.dmg$")
    else:
        return None
    return next((n for n in nomes if quer.match(n)), None)


def procurar(atual=__version__, prazo_s=10):
    """Versão mais nova que a atual, ou None. Devolve {versao, notas, pagina, nome, url, tamanho, sha256}."""
    r = requests.get(API, timeout=prazo_s, headers={"Accept": "application/vnd.github+json",
                                                   "User-Agent": f"Papory/{__version__}"})
    r.raise_for_status()
    dados = r.json()
    versao = dados.get("tag_name", "").lstrip("v")
    if versao_tupla(versao) <= versao_tupla(atual):
        return None
    arquivos = {a["name"]: a for a in dados.get("assets", [])}
    nome = arquivo_deste_sistema(arquivos)
    if not nome:
        return None
    a = arquivos[nome]
    sha = (a.get("digest") or "").removeprefix("sha256:")
    if not re.fullmatch(r"[0-9a-f]{64}", sha):
        return None  # sem impressão digital não dá para conferir o que baixou: não oferece
    return {"versao": versao, "notas": (dados.get("body") or "").strip(), "pagina": dados.get("html_url"),
            "nome": nome, "url": a["browser_download_url"], "tamanho": a.get("size") or 0, "sha256": sha}


def baixar(nova, progresso=lambda feito, total: None, parar=lambda: False):
    """Baixa para uma pasta temporária e confere o SHA-256. Devolve o caminho; se não bater, apaga e dá erro."""
    shutil.rmtree(PASTA, ignore_errors=True)  # sobras de uma atualização anterior
    PASTA.mkdir(parents=True, exist_ok=True)
    destino = PASTA / nova["nome"]
    soma, feito = hashlib.sha256(), 0
    with requests.get(nova["url"], stream=True, timeout=(10, 60),
                      headers={"User-Agent": f"Papory/{__version__}"}) as r:
        r.raise_for_status()
        with open(destino, "wb") as f:
            for pedaco in r.iter_content(1 << 20):
                if parar():
                    raise InterruptedError("cancelado")
                f.write(pedaco)
                soma.update(pedaco)
                feito += len(pedaco)
                progresso(feito, nova["tamanho"])
    if soma.hexdigest() != nova["sha256"]:
        destino.unlink(missing_ok=True)
        raise ValueError("o arquivo baixado não confere com a impressão digital publicada no GitHub")
    return destino


def instalar(caminho):
    """Windows: roda o instalador sem janelas e separado do Papory (que precisa fechar para os arquivos serem
    trocados); o instalador reabre o Papory no fim. Mac: abre o .dmg para a pessoa arrastar o app."""
    if sys.platform == "win32":
        separado = 0x00000008 | 0x00000200  # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP
        # o Papory que o instalador reabre herda este ambiente: sem as variáveis de teste e com o aviso do
        # PyInstaller de que é um programa novo, não um filho deste
        ambiente = {k: v for k, v in os.environ.items() if not k.upper().startswith(("PAPORY_", "_PYI_"))}
        ambiente["PYINSTALLER_RESET_ENVIRONMENT"] = "1"
        subprocess.Popen([str(caminho), "/SILENT", "/SUPPRESSMSGBOXES", "/NORESTART", "/CLOSEAPPLICATIONS"],
                         creationflags=separado, close_fds=True, cwd=str(PASTA), env=ambiente)
    else:
        from . import plataforma
        plataforma.abrir(caminho)
    return sys.platform == "win32"  # True: o Papory deve fechar agora


def pode_procurar():
    """Rodando pelo código (git clone) a pessoa atualiza com git pull; o aviso é só para o app instalado."""
    return getattr(sys, "frozen", False) or os.environ.get("PAPORY_TESTAR_ATUALIZACAO") == "1"
