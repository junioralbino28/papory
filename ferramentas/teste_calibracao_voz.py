"""Calibração de ponta a ponta com voz sintética: lê as frases, aprende e dita de novo (só Windows).

Gera cada frase com a voz pt-BR do Windows, passa pelo motor de verdade (Parakeet + polimento local, sem nuvem,
sem teclado e sem colar), aplica o que a calibração aprendeu (as trocas que já vêm marcadas) e repete as mesmas
leituras. Passa quando todo termo que saiu errado na 1ª rodada sai certo na 2ª, a não ser que a troca dele mexa em
palavra comum (essa espera a pessoa marcar), e quando frases comuns de controle continuam intactas.
Usa uma cópia temporária da configuração.

uso:  python ferramentas/teste_calibracao_voz.py
"""
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from papory import plataforma  # noqa: E402

temp = Path(tempfile.mkdtemp(prefix="papory-calib-voz-"))
dados = temp / "Papory"
if plataforma.pasta_dados().exists():
    shutil.copytree(plataforma.pasta_dados(), dados, ignore=shutil.ignore_patterns("historico", "*.log*"))
os.environ["PAPORY_DADOS"] = str(dados)

from papory import calibracao as cal  # noqa: E402
from papory import config  # noqa: E402
from papory.audio import GravadorDeArquivo  # noqa: E402
from papory.motor import Motor  # noqa: E402

TERMOS = ["Zaptalk", "Lumora"]  # nomes inventados: o reconhecimento não tem como conhecer
CONTROLE = ["Daqui a uma hora eu te ligo.", "Foi um bom papo com a equipe hoje."]  # não podem mudar
VOZ = r"""
Add-Type -AssemblyName System.Speech
$s = New-Object System.Speech.Synthesis.SpeechSynthesizer
$v = $s.GetInstalledVoices() | Where-Object { $_.VoiceInfo.Culture.Name -eq 'pt-BR' } | Select-Object -First 1
if (-not $v) { Write-Error 'sem voz pt-BR instalada'; exit 2 }
$s.SelectVoice($v.VoiceInfo.Name)
$s.Rate = 0
$fmt = New-Object System.Speech.AudioFormat.SpeechAudioFormatInfo(16000, 16, 1)
$s.SetOutputToWaveFile($env:PAPORY_WAV, $fmt)
$s.Speak($env:PAPORY_TEXTO)
$s.Dispose()
"""


def falar(texto, destino):
    env = dict(os.environ, PAPORY_WAV=str(destino), PAPORY_TEXTO=texto)
    subprocess.run(["powershell", "-NoProfile", "-Command", VOZ], env=env, check=True, capture_output=True)


cfg = config.carregar()
cfg["asr"]["dispositivo"] = "cpu"
cfg["reforco_nuvem"]["ativo"] = False  # nada sai do computador no teste
cfg["sons"] = False
cfg["historico"] = False
frases = cal.montar_frases(TERMOS)
wavs = []
for n, f in enumerate(frases):
    wavs.append(temp / f"frase{n}.wav")
    falar(f["texto"], wavs[-1])
controle = []
for n, texto in enumerate(CONTROLE):
    controle.append(temp / f"controle{n}.wav")
    falar(texto, controle[-1])
print(f"{len(frases)} frases e {len(CONTROLE)} de controle geradas com a voz do Windows")

registros, chegou = [], threading.Event()


def avisar(evento, d=None):
    if evento == "ditado":
        registros.append(d)
        chegou.set()
    elif evento in ("silencio", "erro"):
        registros.append(None)
        chegou.set()


motor = Motor(cfg, avisar, arquivo_teste=str(wavs[0]))
motor._ligar_atalho = lambda: None
motor.carregar()
motor.entregar = lambda texto: None
print("motor:", motor.descricao())


def ditar(lista):
    registros.clear()
    for wav in lista:
        motor.gravador = GravadorDeArquivo(str(wav))
        chegou.clear()
        motor._eventos.put("apertou")
        time.sleep(0.05)
        motor._eventos.put("soltou")
        chegou.wait(120)
    return list(registros)


def rodada():
    t0 = time.perf_counter()
    regs = ditar(wavs)
    return [cal.avaliar(f, r["cru"], r["final"]) if r else None for f, r in zip(frases, regs)], \
        [r and r.get("volume") for r in regs], time.perf_counter() - t0


antes, volumes, s1 = rodada()
controle_antes = [r and r["final"] for r in ditar(controle)]
proposta = cal.propor(cfg, [r for r in antes if r], TERMOS)
aprendido = cal.aplicar(cfg, proposta)
depois, _, s2 = rodada()
controle_depois = [r and r["final"] for r in ditar(controle)]
motor.parar()

falhas = 0
desmarcadas = {de for de, _ in proposta["regras"] if (de, _) not in proposta["marcadas"]}
print(f"\n1ª rodada: {s1:.1f} s de processamento para {len(frases)} frases; volume: {cal.veredito_volume(volumes)}")
for n, (a, d) in enumerate(zip(antes, depois)):
    print(f"\n[{n + 1}] {frases[n]['texto']}")
    print(f"    antes : {a['final'] if a else '(nada)'}   ({a['acertos'] if a else 0}/{a['total'] if a else '?'})")
    print(f"    depois: {d['final'] if d else '(nada)'}   ({d['acertos'] if d else 0}/{d['total'] if d else '?'})")
    if a and a["erros_alvo"]:
        print(f"    errou : {a['erros_alvo']}")
    for de, alvo in (a["erros_alvo"] if a else []):
        if d is None or alvo in d["faltou_no_final"] or alvo not in d["final"]:
            if de in desmarcadas:
                print(f"    -- “{de}” é palavra comum: a troca para “{alvo}” espera a pessoa marcar")
            else:
                falhas += 1
                print(f"    !! “{alvo}” continua errado depois da calibração")
for texto, a, d in zip(CONTROLE, controle_antes, controle_depois):
    mudou = a != d
    falhas += mudou
    print(f"\n[controle] {texto}\n    antes : {a}\n    depois: {d}{'   !! MUDOU' if mudou else ''}")
print(f"\nregras aprendidas: {aprendido['regras']}")
print(f"esperando a pessoa marcar: {sorted(desmarcadas)}")
print(f"vocabulário novo : {aprendido['vocabulario']}")
print(f"2ª rodada: {s2:.1f} s")
print("\nPASSOU: o que errou na leitura saiu certo no ditado seguinte (troca de palavra comum espera a pessoa "
      "marcar) e as frases de controle não mudaram" if not falhas
      else f"\n{falhas} termo(s) continuam errados")
shutil.rmtree(temp, ignore_errors=True)
sys.exit(1 if falhas else 0)
