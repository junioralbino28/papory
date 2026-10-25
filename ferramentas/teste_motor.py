"""Testa o motor de ponta a ponta SEM teclado, SEM colar e SEM placa de vídeo.

O áudio vem de um WAV; os eventos "apertou/soltou" entram direto na fila do motor (nenhuma tecla é simulada);
o texto final volta por motor.entregar (nada vai para a área de transferência). Usa uma cópia temporária da
configuração e do histórico, e o reconhecimento no processador (não disputa a placa com outro app aberto).

uso:  python ferramentas/teste_motor.py <arquivo.wav> [--com-reforco]
"""
import os
import shutil
import sys
import tempfile
import threading
import time
from pathlib import Path

wav = Path(sys.argv[1]).resolve()
original = Path(os.environ["APPDATA"])
temp = Path(tempfile.mkdtemp(prefix="papory-motor-"))
for nome in ("Papory", "Ditado"):
    if (original / nome).exists():
        shutil.copytree(original / nome, temp / nome, ignore=shutil.ignore_patterns("historico"))
        break
os.environ["APPDATA"] = str(temp)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)

from papory import config  # noqa: E402
from papory.motor import Motor  # noqa: E402

cfg = config.carregar()
cfg["asr"]["dispositivo"] = "cpu"
cfg["reforco_nuvem"]["ativo"] = "--com-reforco" in sys.argv
cfg["sons"] = False
eventos, chegou, textos = [], threading.Event(), []


def avisar(evento, dados=None):
    eventos.append(evento)
    if evento in ("carregando", "erro", "aviso", "silencio"):
        print(f"  [{evento}] {dados}")
    if evento in ("entregue", "silencio", "erro"):
        chegou.set()


motor = Motor(cfg, avisar, arquivo_teste=str(wav))
motor._ligar_atalho = lambda: None  # sem gancho de teclado no teste
t0 = time.perf_counter()
motor.carregar()
print(f"carregou em {time.perf_counter() - t0:.1f} s: {motor.descricao()}")
motor.entregar = textos.append


def ditar():
    chegou.clear()
    motor._eventos.put("apertou")
    time.sleep(0.3)
    motor._eventos.put("soltou")
    t = time.perf_counter()
    chegou.wait(120)
    return time.perf_counter() - t


s = ditar()
print(f"\n1) polimento ligado ({s:.1f} s): {textos[-1] if textos else '(nada)'}")
cfg["polimento"]["ativo"] = False
motor.aplicar_config()
s = ditar()
print(f"\n2) polimento desligado na hora ({s:.1f} s): {textos[-1] if textos else '(nada)'}")
print("\neventos:", eventos)
print("histórico gravado no teste:", (temp / "Papory" / "historico").exists())
motor.parar()
shutil.rmtree(temp, ignore_errors=True)
