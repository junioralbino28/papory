"""Reconhecimento de fala: Parakeet v3 em fp32, na placa de vídeo (DirectML) ou no processador.

Medido com 34 ditados reais em PT-BR: fp32 erra 13% das palavras; o int8 perde trechos inteiros
na mesma voz. Por isso não há opção de int8 aqui.

O Parakeet v3 escolhe o idioma sozinho (não dá para travar) e às vezes "vira" inglês no meio de uma fala longa
(dois ditados de 42 e 45 s: inglês sem sentido, e no segundo sumiram 2/3 da fala). O mesmo áudio em trechos de
~15 s sai em português certo. Cortar SEMPRE custa caro (34 ditados: 13,0% de erro inteiro, 15,4% em trechos de
~15 s), então só refaz em trechos quando o texto vem com cara de inglês.
"""
import re
import time

import numpy as np
import onnx_asr
import onnxruntime as ort

TAXA = 16000
MAX_TRECHO_S = 90      # acima disso, corta nos silêncios (o modelo enxerga o áudio inteiro de uma vez)
ALVO_TRECHO_S = 60
REFAZER_S = 15         # texto com cara de inglês: refaz em trechos deste tamanho...
REFAZER_TRECHO_S = 8   # ...e o trecho que ainda sair em inglês, em pedaços menores
# palavras de inglês que não existem em português ("do" fica de fora: "do Claude"); termo técnico solto não conta
INGLES = re.compile(r"(?<!\w)(the|and|you|with|that|this|for|is|are|have|will|would|i|i'm|i'll|don't|what|know|"
                    r"because|think|how|about|it's|can't|not|or|was|were|there|they|just|like|get|make|if|my|your|"
                    r"which|when|where|who|why|does|did|be|been|being|has|had|of|to|in|on|at|it|we|he|she)(?!\w)",
                    re.I)


def parece_ingles(texto):
    """Inglês em 10% ou mais das palavras. Medido em ditados reais: normais até 7% (num curto), os ruins 29% e 48%."""
    n = len(INGLES.findall(texto))
    return n >= 4 and n >= 0.10 * len(texto.split())


def _quanto_ingles(texto):
    return len(INGLES.findall(texto)) / max(1, len(texto.split()))


def _reamostrar(audio, taxa):
    if taxa == TAXA or len(audio) == 0:
        return audio.astype(np.float32)
    n = int(round(len(audio) * TAXA / taxa))
    return np.interp(np.linspace(0, len(audio) - 1, n), np.arange(len(audio)), audio).astype(np.float32)


def _cortes(audio, maximo=MAX_TRECHO_S, alvo=ALVO_TRECHO_S, folga=15):
    """Divide áudio longo nos pontos mais silenciosos perto de cada `alvo` segundos (± folga)."""
    if len(audio) <= maximo * TAXA:
        return [audio]
    janela = int(0.03 * TAXA)
    energia = np.sqrt(np.convolve(audio ** 2, np.ones(janela) / janela, mode="same"))
    pedacos, ini = [], 0
    while len(audio) - ini > maximo * TAXA:
        a, b = ini + int((alvo - folga) * TAXA), ini + int((alvo + folga) * TAXA)
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
        texto = self._reconhecer(_cortes(audio))
        if not parece_ingles(texto) or len(audio) <= (REFAZER_TRECHO_S + 2) * TAXA:
            return texto
        partes = []
        for trecho in _cortes(audio, maximo=REFAZER_S + 5, alvo=REFAZER_S, folga=5):
            parte = self._reconhecer([trecho])
            if parece_ingles(parte) and len(trecho) > (REFAZER_TRECHO_S + 2) * TAXA:
                menor = self._reconhecer(_cortes(trecho, maximo=REFAZER_TRECHO_S + 2, alvo=REFAZER_TRECHO_S, folga=2))
                parte = menor if _quanto_ingles(menor) < _quanto_ingles(parte) else parte
            partes.append(parte)
        outro = " ".join(p for p in partes if p)
        if _quanto_ingles(outro) < _quanto_ingles(texto):
            print(f"reconhecimento: saiu com cara de inglês; refeito em trechos de ~{REFAZER_S} s")
            return outro
        return texto

    def _reconhecer(self, partes):
        partes = [str(self.modelo.recognize(p, sample_rate=TAXA)).strip() for p in partes]
        return " ".join(p for p in partes if p)
