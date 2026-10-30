"""Regressão da pílula: pausa e saída clicáveis sem roubar o foco."""
import os
import sys
from pathlib import Path

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from papory.interface import tema  # noqa: E402
from papory.interface.pilula import Pilula  # noqa: E402


class MotorFalso:
    gravando = False
    pausado = False

    @staticmethod
    def nivel():
        return 0.0


app = QApplication.instance() or QApplication(sys.argv)
tema.aplicar(app)
motor = MotorFalso()
pilula = Pilula({"interface": {"pilula": True}}, motor)
pausas, saidas = [], []


def pausar(valor):
    motor.pausado = valor
    pausas.append(valor)


pilula.pedir_pausa.connect(pausar)
pilula.pedir_sair.connect(lambda: saidas.append(True))
pilula._mostrar("escrevendo", "escrevendo")
app.processEvents()

assert pilula.windowFlags() & Qt.WindowType.WindowDoesNotAcceptFocus
ret_pausa, ret_sair = pilula._retangulos_controle()
assert ret_pausa.width() >= 26 and ret_sair.width() >= 26

QTest.mouseClick(pilula, Qt.MouseButton.LeftButton, pos=ret_pausa.center().toPoint())
assert pausas == [True]

QTest.mouseClick(pilula, Qt.MouseButton.LeftButton, pos=ret_pausa.center().toPoint())
assert pausas == [True, False]

QTest.mouseClick(pilula, Qt.MouseButton.LeftButton, pos=ret_sair.center().toPoint())
assert saidas == [True]

pilula._mostrar("ouvindo", "0:00")
app.processEvents()
ret_pausa_ouvindo, ret_sair_ouvindo = pilula._retangulos_controle()
assert ret_pausa_ouvindo.width() >= 26 and ret_sair_ouvindo.width() >= 26

if len(sys.argv) > 1:
    destino = Path(sys.argv[1])
    destino.mkdir(parents=True, exist_ok=True)
    pilula._mostrar("escrevendo", "escrevendo")
    app.processEvents()
    pilula.grab().save(str(destino / "pilula-controles.png"))

pilula.close()
print("TUDO CERTO")
