"""Gravação do microfone enquanto o atalho está apertado.

O microfone abre ao apertar e fecha ao soltar (o indicador de "microfone em uso" do Windows só acende
enquanto você fala). GravadorDeArquivo troca o microfone por um WAV, para testar sem falar.
"""
import threading
import time

import numpy as np
import sounddevice as sd
import soundfile as sf


def listar_microfones():
    """Nomes dos microfones do sistema, sem repetir (o Windows lista o mesmo aparelho em várias APIs de áudio)."""
    padrao_api = sd.default.hostapi
    nomes = []
    for d in sd.query_devices():
        if d["max_input_channels"] > 0 and d["hostapi"] == padrao_api and d["name"] not in nomes:
            nomes.append(d["name"])
    return nomes


def microfone_padrao():
    try:
        return sd.query_devices(None, "input")["name"]
    except Exception:  # noqa: BLE001 — nenhum microfone ligado
        return None


def escolher_dispositivo(nome):
    if nome is None:
        return None
    for i, d in enumerate(sd.query_devices()):
        if d["max_input_channels"] > 0 and str(nome).lower() in d["name"].lower():
            return i
    raise ValueError(f"microfone não encontrado: {nome!r}")


class Gravador:
    def __init__(self, nome_microfone=None):
        self.dispositivo = escolher_dispositivo(nome_microfone)
        info = sd.query_devices(self.dispositivo, "input")
        self.taxa = 16000
        try:
            sd.check_input_settings(device=self.dispositivo, samplerate=self.taxa, channels=1)
        except Exception:  # noqa: BLE001 — dispositivo que não aceita 16 kHz grava na taxa dele
            self.taxa = int(info["default_samplerate"])
        self.nome = info["name"]
        self._blocos, self._fluxo, self._trava = [], None, threading.Lock()
        self.abriu_em_s = 0.0
        self.nivel = 0.0  # volume do último bloco (RMS), para as barras da pílula

    def _cb(self, dados, quadros, tempo, status):
        with self._trava:
            self._blocos.append(dados[:, 0].copy())
        self.nivel = float(np.sqrt(np.mean(dados[:, 0] ** 2))) if len(dados) else 0.0

    def iniciar(self):
        t0 = time.perf_counter()
        self._blocos = []
        self._fluxo = sd.InputStream(device=self.dispositivo, samplerate=self.taxa, channels=1,
                                     dtype="float32", callback=self._cb, blocksize=0, latency="low")
        self._fluxo.start()
        self.abriu_em_s = time.perf_counter() - t0

    def parar(self):
        if self._fluxo is None:
            return np.zeros(0, dtype=np.float32), self.taxa
        self._fluxo.stop()
        self._fluxo.close()
        self._fluxo = None
        self.nivel = 0.0
        with self._trava:
            audio = np.concatenate(self._blocos) if self._blocos else np.zeros(0, dtype=np.float32)
        return audio, self.taxa


class GravadorDeArquivo:
    """Para teste: ignora o microfone e devolve o áudio de um WAV quando o atalho é solto."""

    def __init__(self, caminho):
        self.audio, self.taxa = sf.read(str(caminho), dtype="float32")
        if self.audio.ndim > 1:
            self.audio = self.audio.mean(axis=1)
        self.nome = f"arquivo {caminho}"
        self.abriu_em_s = 0.0
        self.nivel = 0.0

    def iniciar(self):
        pass

    def parar(self):
        return self.audio.copy(), self.taxa
