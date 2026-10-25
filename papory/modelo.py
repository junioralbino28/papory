"""Modelo de voz (Parakeet, ~2,5 GB): saber se já está no computador e baixar com progresso na 1ª abertura.

Baixa exatamente os arquivos que o onnx-asr pede para o fp32 (mesmos padrões do resolver dele), para que o
carregamento depois funcione sem internet.
"""
import fnmatch
import threading
import time
from pathlib import Path

NOME = "nemo-parakeet-tdt-0.6b-v3"


def _repo():
    from onnx_asr.resolver import model_repos
    return model_repos[NOME]


def _padroes():
    from onnx_asr.models.nemo import NemoConformerTdt
    arquivos = list(NemoConformerTdt._get_model_files(None).values())
    extras = [str(Path(a).with_suffix(".onnx?data")) for a in arquivos if a.endswith(".onnx")]
    return ["config.json", "config.yaml", *arquivos, *extras]


def _pasta_cache():
    from huggingface_hub import constants
    return Path(constants.HF_HUB_CACHE) / ("models--" + _repo().replace("/", "--"))


def baixado():
    from huggingface_hub import snapshot_download
    try:
        snapshot_download(_repo(), allow_patterns=_padroes(), local_files_only=True)
        return True
    except Exception:  # noqa: BLE001 — falta algum arquivo
        return False


def tamanho_no_disco():
    """Bytes dos arquivos do modelo já baixados (0 se não houver)."""
    snaps = _pasta_cache() / "snapshots"
    if not snaps.exists():
        return 0
    padroes = _padroes()
    total = 0
    for f in snaps.glob("*/*"):
        if f.is_file() and any(fnmatch.fnmatch(f.name, p) for p in padroes):
            total += f.stat().st_size
    return total


def tamanho_total():
    """Bytes a baixar (pergunta ao Hugging Face); None sem internet."""
    from huggingface_hub import HfApi
    try:
        info = HfApi().model_info(_repo(), files_metadata=True)
    except Exception:  # noqa: BLE001
        return None
    padroes = _padroes()
    return sum(s.size or 0 for s in info.siblings if any(fnmatch.fnmatch(s.rfilename, p) for p in padroes))


def _bytes_no_cache():
    p = _pasta_cache() / "blobs"
    if not p.exists():
        return 0
    return sum(f.stat().st_size for f in p.iterdir() if f.is_file())


def baixar(ao_progresso, ao_terminar):
    """Baixa em segundo plano. ao_progresso(baixados, total) a cada ~0,5 s; ao_terminar(erro_ou_None)."""
    def trabalho():
        from huggingface_hub import snapshot_download
        total = tamanho_total()
        inicio = _bytes_no_cache()
        resultado = {}

        def baixa():
            try:
                snapshot_download(_repo(), allow_patterns=_padroes())
            except Exception as e:  # noqa: BLE001
                resultado["erro"] = e

        t = threading.Thread(target=baixa, daemon=True)
        t.start()
        while t.is_alive():
            ao_progresso(max(0, _bytes_no_cache() - inicio), total)
            time.sleep(0.5)
        erro = resultado.get("erro")
        if not erro and total:
            ao_progresso(total, total)
        ao_terminar(erro)

    threading.Thread(target=trabalho, daemon=True).start()
