"""Reconhecimento de fala: Parakeet v3 em fp32, na placa de vídeo (DirectML) ou no processador.

Medido com 34 ditados reais em PT-BR: fp32 erra 13% das palavras; o int8 perde trechos inteiros
na mesma voz. Por isso não há opção de int8 aqui.
"""
import time

import numpy as np
import onnx_asr
import onnxruntime as ort

TAXA = 16000
MAX_TRECHO_S = 90      # acima disso, corta nos silêncios (o modelo enxerga o áudio inteiro de uma vez)
ALVO_TRECHO_S = 60


def _reamostrar(audio, taxa):
    if taxa == TAXA or len(audio) == 0:
        return audio.astype(np.float32)
    n = int(round(len(audio) * TAXA / taxa))
    return np.interp(np.linspace(0, len(audio) - 1, n), np.arange(len(audio)), audio).astype(np.float32)


def _cortes(audio):
    """Divide áudio longo nos pontos mais silenciosos perto de cada ALVO_TRECHO_S."""
    if len(audio) <= MAX_TRECHO_S * TAXA:
        return [audio]
    janela = int(0.03 * TAXA)
    energia = np.sqrt(np.convolve(audio ** 2, np.ones(janela) / janela, mode="same"))
    pedacos, ini = [], 0
    while len(audio) - ini > MAX_TRECHO_S * TAXA:
        a, b = ini + int((ALVO_TRECHO_S - 15) * TAXA), ini + int((ALVO_TRECHO_S + 15) * TAXA)
        corte = a + int(np.argmin(energia[a:b]))
        pedacos.append(audio[ini:corte])
        ini = corte
    pedacos.append(audio[ini:])
    return pedacos


class Reconhecedor:
    def __init__(self, modelo="nemo-parakeet-tdt-0.6b-v3", dispositivo="auto"):
        gpu = dispositivo in ("auto", "gpu") and "DmlExecutionProvider" in ort.get_available_providers()
        provedores = ["DmlExecutionProvider", "CPUExecutionProvider"] if gpu else ["CPUExecutionProvider"]
        t0 = time.perf_counter()
        self.modelo = onnx_asr.load_model(modelo, quantization=None, providers=provedores)
        self.onde = "placa de vídeo (DirectML)" if gpu else "processador"
        self.transcrever(np.random.default_rng(0).normal(0, 0.01, TAXA).astype(np.float32), TAXA)  # aquece
        self.carregou_em_s = time.perf_counter() - t0

    def transcrever(self, audio, taxa):
        audio = _reamostrar(np.asarray(audio, dtype=np.float32), taxa)
        if len(audio) < 0.3 * TAXA:
            return ""
        partes = [str(self.modelo.recognize(p, sample_rate=TAXA)).strip() for p in _cortes(audio)]
        return " ".join(p for p in partes if p)
