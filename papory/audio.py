"""Gravação do microfone enquanto o atalho está apertado.

O microfone abre ao apertar e fecha ao soltar (o indicador de "microfone em uso" do Windows só acende
enquanto você fala). GravadorDeArquivo troca o microfone por um WAV, para testar sem falar.
"""
import threading
import time

import numpy as np
import sounddevice as sd
import soundfile as sf


# O PortAudio lê a lista de aparelhos uma vez só, quando o programa abre: um fone Bluetooth ligado depois não
# aparecia, e o "padrão do sistema" ficava o da abertura. atualizar_aparelhos() relê a lista, mas nunca com um
# microfone aberto ou um som tocando (reler fecha tudo o que o PortAudio tem aberto).
_trava = threading.Lock()
_abertos = 0
_relida_em = 0.0


def _tocando():
    try:
        return sd.get_stream().active
    except RuntimeError:  # nada tocado ainda
        return False


def atualizar_aparelhos(minimo_s=2.0):
    """Relê a lista de microfones do sistema (leva de 25 a 200 ms). Devolve False se não deu para reler agora."""
    global _relida_em
    with _trava:
        if _abertos or _tocando() or time.monotonic() - _relida_em < minimo_s:
            return False
        sd._terminate()
        sd._initialize()
        _relida_em = time.monotonic()
        return True


def abrir_medidor(nome, callback):
    """Microfone aberto só para medir o volume (botão Testar). Fechar com fechar_medidor()."""
    global _abertos
    with _trava:
        fluxo = sd.InputStream(device=escolher_dispositivo(nome), channels=1, dtype="float32", callback=callback)
        fluxo.start()
        _abertos += 1
    return fluxo


def fechar_medidor(fluxo):
    global _abertos
    fluxo.stop()
    fluxo.close()
    with _trava:
        _abertos -= 1


def tocar(dados, taxa):
    """Toca um áudio (ouvir um ditado do histórico) sem cruzar com uma releitura da lista."""
    with _trava:
        sd.play(dados, taxa)


def parar_som():
    with _trava:
        sd.stop()


def listar_microfones():
    """Nomes dos microfones do sistema, sem repetir (o Windows lista o mesmo aparelho em várias APIs de áudio)."""
    atualizar_aparelhos()
    padrao_api = sd.default.hostapi
    nomes = []
    for d in sd.query_devices():
        if d["max_input_channels"] > 0 and d["hostapi"] == padrao_api and d["name"] not in nomes:
            nomes.append(d["name"])
    return nomes


def microfone_padrao():
    atualizar_aparelhos()
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


def medir_volume(audio, taxa):
    """fala: volume típico da voz (RMS em janelas de 20 ms, 90º percentil); saturado: fração de amostras no teto."""
    n = max(1, int(taxa * 0.02))
    if len(audio) < n:
        return {"fala": 0.0, "saturado": 0.0}
    janelas = audio[: len(audio) // n * n].reshape(-1, n)
    return {"fala": round(float(np.percentile(np.sqrt((janelas ** 2).mean(axis=1)), 90)), 4),
            "saturado": round(float((np.abs(audio) >= 0.98).mean()), 5)}


class Gravador:
    def __init__(self, nome_microfone=None):
        self.nome_microfone = nome_microfone
        self._preparar()  # já na criação: ValueError se o microfone escolhido não está ligado
        self._blocos, self._fluxo, self._trava = [], None, threading.Lock()
        self.abriu_em_s = 0.0
        self.nivel = 0.0  # volume do último bloco (RMS), para as barras da pílula
        # o 1º som de verdade chegou: fone Bluetooth no modo música leva ~1,5 s para ligar o microfone
        # (medido no Buds2 Pro), e o que se fala antes disso não chega
        self.ouviu = threading.Event()
        self.demorou_s = 0.0  # do abrir até o 1º som: perto de 0 num microfone com fio, 0,7 a 1,4 s no Buds
        self._t0 = 0.0

    def _preparar(self):
        """Acha o microfone pelo nome: o número dele muda quando a lista de aparelhos é relida."""
        self.dispositivo = escolher_dispositivo(self.nome_microfone)
        info = sd.query_devices(self.dispositivo, "input")
        self.taxa = 16000
        try:
            sd.check_input_settings(device=self.dispositivo, samplerate=self.taxa, channels=1)
        except Exception:  # noqa: BLE001 — dispositivo que não aceita 16 kHz grava na taxa dele
            self.taxa = int(info["default_samplerate"])
        self.nome = info["name"]

    def _cb(self, dados, quadros, tempo, status):
        with self._trava:
            self._blocos.append(dados[:, 0].copy())
        self.nivel = float(np.sqrt(np.mean(dados[:, 0] ** 2))) if len(dados) else 0.0
        if self.nivel > 0 and not self.ouviu.is_set():
            self.demorou_s = time.perf_counter() - self._t0
            self.ouviu.set()

    def iniciar(self):
        global _abertos
        t0 = self._t0 = time.perf_counter()
        self._blocos = []
        self.demorou_s = 0.0
        self.ouviu.clear()
        with _trava:  # espera uma releitura da lista que esteja no meio (no máximo uns 200 ms)
            self._preparar()
            self._fluxo = sd.InputStream(device=self.dispositivo, samplerate=self.taxa, channels=1,
                                         dtype="float32", callback=self._cb, blocksize=0, latency="low")
            self._fluxo.start()
            _abertos += 1
        self.abriu_em_s = time.perf_counter() - t0

    def parar(self, depois_s=0.0):
        """depois_s: segura o microfone aberto mais um pouco, sem guardar esse pedaço. Fone Bluetooth troca do modo
        ligação para o de música quando o microfone fecha, e o som que estiver tocando nessa troca some."""
        global _abertos
        if self._fluxo is None:
            return np.zeros(0, dtype=np.float32), self.taxa
        with self._trava:
            ate = sum(len(b) for b in self._blocos)
        if depois_s:
            time.sleep(depois_s)
        self._fluxo.stop()
        self._fluxo.close()
        self._fluxo = None
        with _trava:
            _abertos -= 1
        self.nivel = 0.0
        with self._trava:
            audio = np.concatenate(self._blocos)[:ate] if self._blocos else np.zeros(0, dtype=np.float32)
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
        self.ouviu = threading.Event()
        self.ouviu.set()
        self.demorou_s = 0.0

    def iniciar(self):
        pass

    def parar(self, depois_s=0.0):
        return self.audio.copy(), self.taxa
