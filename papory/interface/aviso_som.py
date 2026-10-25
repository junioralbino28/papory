"""Aviso antes do primeiro ditado: esperar o assobio do papagaio para começar a falar (aparece uma vez só)."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QHBoxLayout, QVBoxLayout

from .. import config, plataforma
from . import tema
from .widgets import botao, rotulo


class AvisoSom(QDialog):
    def __init__(self, pai, cfg):
        super().__init__(pai)
        self.cfg = cfg
        self.setWindowTitle("Antes de falar")
        self.setStyleSheet(f"QDialog {{ background: {tema.BRANCO}; }}")
        self.setFixedWidth(460)
        v = QVBoxLayout(self)
        v.setContentsMargins(28, 26, 28, 24)
        v.setSpacing(14)
        img = rotulo("")
        img.setPixmap(tema.papagaio("papory-microfone-512.png").scaled(
            120, 120, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        img.setAccessibleName("O papagaio do Papory falando num microfone")
        v.addWidget(img, 0, Qt.AlignmentFlag.AlignHCenter)
        t = rotulo("Espere o assobio para falar", "titulo")
        t.setStyleSheet("font-size: 22px;")
        t.setAlignment(Qt.AlignmentFlag.AlignCenter)
        v.addWidget(t)
        v.addWidget(rotulo("Segure o atalho e espere o assobio do papagaio: ele avisa que o microfone já está "
                           "ouvindo.", "sub", quebra=True))
        v.addWidget(rotulo("Com o microfone do computador, o assobio vem na hora. Com fone Bluetooth pode levar uns 2 "
                           "segundos, o tempo de o fone ligar o microfone. O que você falar antes do assobio não é "
                           "gravado.", "meta", quebra=True))
        v.addSpacing(4)
        botoes = QHBoxLayout()
        ouvir, ok = botao("Ouvir o assobio", "secundario", "ouvir"), botao("Entendi", "primario")
        ouvir.clicked.connect(lambda: plataforma.tocar_som("comecou"))
        ok.clicked.connect(self.accept)
        botoes.addWidget(ouvir, 1)
        botoes.addWidget(ok, 1)
        v.addLayout(botoes)

    def done(self, codigo):
        self.cfg["interface"]["aviso_som_visto"] = True
        config.salvar(self.cfg)
        super().done(codigo)


def mostrar_se_precisa(pai, cfg):
    if not cfg["interface"].get("aviso_som_visto"):
        AvisoSom(pai, cfg).exec()
