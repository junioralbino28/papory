"""Testa a pasta montada pelo PyInstaller SEM mexer na sua tela, no seu teclado nem na sua configuração.

1. Papory.exe com a interface invisível (Qt offscreen) e sem motor: abre, fica 15 s e é encerrado; o log não
   pode ter erro.
2. papory-terminal.exe em autoteste: WAV no lugar do microfone, reconhecimento no processador, sem colar.

Os dois usam uma pasta de dados temporária (APPDATA falso), apagada no fim.
uso:  python empacotar/testar_pacote.py <pasta Papory montada> <arquivo.wav>
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

pasta, wav = Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve()
sys.stdout.reconfigure(encoding="utf-8")
temp = Path(tempfile.mkdtemp(prefix="papory-pacote-"))
cfg = {"asr": {"modelo": "nemo-parakeet-tdt-0.6b-v3", "dispositivo": "cpu"}, "reforco_nuvem": {"ativo": False},
       "sons": False, "historico": False, "interface": {"primeira_abertura_feita": True}}
(temp / "Papory").mkdir()
(temp / "Papory" / "config.json").write_text(json.dumps(cfg), encoding="utf-8")
env = dict(os.environ, APPDATA=str(temp), QT_QPA_PLATFORM="offscreen", PAPORY_INSTANCIA="papory-teste-pacote")

print("1) interface (Papory.exe --sem-motor, invisível)")
p = subprocess.Popen([str(pasta / "Papory.exe"), "--sem-motor"], env=env)
time.sleep(15)
vivo = p.poll() is None
p.kill()
p.wait()
log = temp / "Papory" / "papory.log"
texto = log.read_text(encoding="utf-8", errors="replace") if log.exists() else ""
print(f"   continuava aberto depois de 15 s: {vivo} | erro no log: {'Traceback' in texto}")
if "Traceback" in texto:
    print(texto[-3000:])

print("2) motor (papory-terminal.exe, autoteste no processador)")
t = time.perf_counter()
r = subprocess.run([str(pasta / "papory-terminal.exe"), "--arquivo-teste", str(wav), "--uma-vez", "--sem-colar"],
                   env=env, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=600)
linhas = [l for l in r.stdout.splitlines() if l.startswith("RESULTADO ")]
print(f"   código {r.returncode} em {time.perf_counter() - t:.0f} s")
if linhas:
    res = json.loads(linhas[-1][len("RESULTADO "):])
    print(f"   texto: {res['final']}\n   polimento: {res['polimento']} | motivo: {res['motivo_cru']}")
else:
    print(r.stdout[-2500:], r.stderr[-2500:])
shutil.rmtree(temp, ignore_errors=True)
