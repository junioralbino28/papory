"""Fotografa as telas do Papory sem mostrar nada na sua tela (Qt "offscreen") e sem carregar a voz.

Usa uma CÓPIA da pasta de dados (histórico, config) numa pasta temporária, para não mexer na sua.

uso:  python ferramentas/foto_interface.py <pasta_de_saida>
"""
import os
import shutil
import sys
import tempfile
from pathlib import Path

saida = Path(sys.argv[1]).resolve()
saida.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from papory import plataforma  # noqa: E402

original = plataforma.pasta_dados()
temp = Path(tempfile.mkdtemp(prefix="papory-foto-")) / "Papory"
for pasta in (original, original.with_name("Ditado")):
    if pasta.exists():
        shutil.copytree(pasta, temp)
        break
os.environ["PAPORY_DADOS"] = str(temp)
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtWidgets import QApplication  # noqa: E402

from papory import config  # noqa: E402
from papory.interface import tema  # noqa: E402
from papory.interface.app import MotorFalso  # noqa: E402
from papory.interface.bandeja import Bandeja  # noqa: E402
from papory.interface.janela import Janela  # noqa: E402
from papory.interface.pilula import Pilula  # noqa: E402
from papory.interface.primeira import PrimeiraAbertura  # noqa: E402

app = QApplication(sys.argv)
tema.aplicar(app)
cfg = config.carregar()
eventos = []
motor = MotorFalso(cfg, lambda e, d=None: eventos.append(e))

janela = Janela(cfg, motor)
janela.estado = "pronto"
janela.atualizar_status()
janela.resize(1180, 820)
janela.show()
for chave in ("inicio", "vocabulario", "atalhos", "config"):
    janela.ir(chave)
    for _ in range(4):
        app.processEvents()
    janela.grab().save(str(saida / f"janela-{chave}.png"))
    pagina = janela.pags[chave].area.widget()
    pagina.resize(janela.pags[chave].area.viewport().width(), pagina.sizeHint().height())
    for _ in range(4):
        app.processEvents()
    pagina.grab().save(str(saida / f"pagina-{chave}.png"))

pilula = Pilula(cfg, motor)
estados = [("ouvindo", "0:07"), ("escrevendo", "escrevendo"), ("colado", "Colado no VS Code"),
           ("copiado", f"Copiado: use {plataforma.COLAR}"),("silencio", "Não ouvi nada"), ("sem_microfone", "Sem microfone")]
for estado, texto in estados:
    motor.gravando = estado == "ouvindo"
    pilula._mostrar(estado, texto)
    if estado == "ouvindo":
        for _ in range(10):
            pilula._quadro()
        pilula.texto = texto
    for _ in range(4):
        app.processEvents()
    pilula.grab().save(str(saida / f"pilula-{estado}.png"))
motor.gravando = False

bandeja = Bandeja(cfg, motor)
bandeja.definir("pronto")
bandeja.sincronizar()
bandeja.menu.adjustSize()
bandeja.menu.grab().save(str(saida / "bandeja-menu.png"))

bem_vindo = PrimeiraAbertura(cfg, motor, lambda: None)
bem_vindo.show()
for i in range(3):
    bem_vindo._ir(i)
    for _ in range(4):
        app.processEvents()
    bem_vindo.grab().save(str(saida / f"primeira-{i + 1}.png"))
    if i == 1:
        bem_vindo._mostrar_resultado("Testando o Papory, um, dois, três.")
        for _ in range(4):
            app.processEvents()
        bem_vindo.grab().save(str(saida / "primeira-2-ouviu.png"))

from papory.interface.calibracao import Calibracao  # noqa: E402

calib = Calibracao(None, cfg, motor, lambda: None)
calib.resize(560, 640)
calib.show()


def foto_calib(nome):
    for _ in range(4):
        app.processEvents()
    calib.grab().save(str(saida / f"calibracao-{nome}.png"))


foto_calib("1-inicio")
calib.campo_termos.setText("Lumora, Zaptalk")
calib._comecar()
foto_calib("2-frase")
voz = {"fala": 0.004, "saturado": 0.0}  # baixinha: para fotografar o aviso do microfone
calib.ao_evento("ouvindo", None)
errado = "Oi, aqui é o papore, o ditado por voz que roda no meu computador."
calib.ao_evento("ditado", {"cru": errado, "final": errado, "volume": voz})
foto_calib("3-diferente")
calib._mostrar_frase(1)
calib.ao_evento("ouvindo", None)
certo = calib.frases[1]["texto"]
calib.ao_evento("ditado", {"cru": certo, "final": certo, "volume": voz})
foto_calib("4-certinho")
calib._mostrar_frase(6)  # "Hoje eu falei sobre Lumora na reunião." ouvida como "uma hora": troca vem desmarcada
calib.ao_evento("ouvindo", None)
comum = "Hoje eu falei sobre uma hora na reunião."
calib.ao_evento("ditado", {"cru": comum, "final": comum, "volume": voz})
calib._ver_resultado()
foto_calib("5-resultado")
calib.done(0)

print("fotos em", saida)
print("eventos do motor falso:", eventos)
shutil.rmtree(temp.parent, ignore_errors=True)
