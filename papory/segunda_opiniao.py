"""Segunda transcrição na nuvem (Whisper large-v3 na Groq), em paralelo com o Parakeet local.

O polimento recebe as duas e escolhe, palavra a palavra, a que faz sentido. Medido no roteiro lido
(gabarito exato): erro do texto final 8,8% só com o Parakeet → 6,1% com a fusão. Desligada por padrão,
porque com ela o ÁUDIO sai do PC.
"""
import io
import threading

import requests
import soundfile as sf

from .asr import TAXA, _reamostrar


class SegundaOpiniao:
    def __init__(self, cfg, chave_api):
        f = cfg["reforco_nuvem"]
        self.ligada = bool(f["ativo"]) and bool(chave_api)
        self.modelo, self.prazo = f["modelo_audio"], float(f["prazo_audio_s"])
        self.vocabulario = cfg["vocabulario"]
        self.chave = chave_api
        self.sessao = requests.Session()

    def pedir(self, audio, taxa):
        """Dispara em segundo plano; devolve uma função que espera (até o prazo) e dá o texto ou None."""
        if not self.ligada or len(audio) < 0.5 * taxa:
            return lambda: None
        resultado = {}

        def trabalho():
            try:
                buf = io.BytesIO()
                sf.write(buf, _reamostrar(audio, taxa), TAXA, format="WAV", subtype="PCM_16")
                r = self.sessao.post(
                    "https://api.groq.com/openai/v1/audio/transcriptions",
                    headers={"Authorization": f"Bearer {self.chave}"},
                    files={"file": ("ditado.wav", buf.getvalue(), "audio/wav")},
                    data={"model": self.modelo, "language": "pt", "temperature": "0", "response_format": "json",
                          "prompt": ", ".join(self.vocabulario)[:800]},
                    timeout=self.prazo)
                r.raise_for_status()
                resultado["texto"] = r.json()["text"].strip()
            except Exception as e:  # noqa: BLE001 — sem a segunda opinião, segue só com o Parakeet
                resultado["erro"] = type(e).__name__

        t = threading.Thread(target=trabalho, daemon=True)
        t.start()

        def esperar():
            t.join(self.prazo + 0.5)
            return resultado.get("texto")

        return esperar
