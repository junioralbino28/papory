"""Gera os sons do Papory (assobio de papagaio), sintetizados aqui: nada de som de terceiros.

    comecou.wav   dois assobios subindo: o microfone já está ouvindo, pode falar
    terminou.wav  um assobio descendo: soltou, o texto vai ser escrito
    copiou.wav    dois assobios graves: o texto ficou só copiado (use Ctrl+V)

uso:  python ferramentas/gerar_sons.py        (grava em papory/sons/)
"""
from pathlib import Path

import numpy as np
import soundfile as sf

TAXA = 48000
PASTA = Path(__file__).resolve().parent.parent / "papory" / "sons"


def assobio(f0, f1, seg, vibrato=0.0):
    """Tom que desliza de f0 para f1, com um tremido leve, abrindo e fechando suave (sem estalo)."""
    x = np.arange(int(TAXA * seg)) / TAXA
    f = f0 * (f1 / f0) ** (x / seg) * (1 + vibrato * np.sin(2 * np.pi * 38 * x))
    fase = 2 * np.pi * np.cumsum(f) / TAXA
    return (np.sin(fase) + 0.2 * np.sin(2 * fase)) * np.sin(np.pi * x / seg) ** 1.5


def juntar(*partes):
    """partes: (início em segundos, som)."""
    saida = np.zeros(max(int(i * TAXA) + len(s) for i, s in partes))
    for i, s in partes:
        saida[int(i * TAXA):int(i * TAXA) + len(s)] += s
    return saida


SONS = {
    "comecou": juntar((0, assobio(1400, 2600, 0.07)), (0.085, assobio(1700, 3000, 0.09, vibrato=0.02))),
    "terminou": assobio(2700, 1500, 0.12, vibrato=0.015),
    "copiou": juntar((0, assobio(1100, 900, 0.08)), (0.13, assobio(1100, 900, 0.08))),
}

if __name__ == "__main__":
    PASTA.mkdir(parents=True, exist_ok=True)
    for nome, som in SONS.items():
        som = som / np.abs(som).max() * 10 ** (-4 / 20)  # pico em −4 dB
        sf.write(PASTA / f"{nome}.wav", som.astype(np.float32), TAXA, subtype="PCM_16")
        print(f"{nome}.wav  {len(som) / TAXA * 1000:.0f} ms")
