"""Ícone perto do relógio (barra de menus, no Mac): mostra o estado (bolinha colorida) e tem o menu."""
from PySide6.QtCore import QObject, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import QAction, QActionGroup, QColor, QIcon, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QHBoxLayout, QLabel, QMenu, QSystemTrayIcon, QVBoxLayout, QWidget, QWidgetAction

from .. import audio, config, plataforma
from . import tema
from .widgets import nome_tecla, rotulo

CORES = {"pronto": tema.VERDE_VIVO, "ouvindo": tema.LARANJA, "carregando": "#C9A227", "atencao": "#D92D20",
         "pausado": None}
TEXTOS = {"pronto": "pronto", "ouvindo": "ouvindo", "carregando": "carregando a voz…",
          "atencao": "precisa de atenção", "pausado": "pausado"}


def _icone(cor):
    base = tema.papagaio().scaled(64, 64, Qt.AspectRatioMode.KeepAspectRatio,
                                  Qt.TransformationMode.SmoothTransformation)
    pm = QPixmap(64, 64)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    if cor is None:
        p.setOpacity(0.45)
    p.drawPixmap(0, 0, base)
    p.setOpacity(1)
    if cor:
        p.setPen(QPen(QColor("#FFFFFF"), 4))
        p.setBrush(QColor(cor))
        p.drawEllipse(QRectF(40, 40, 21, 21))
    p.end()
    return QIcon(pm)


class Bandeja(QObject):
    abrir = Signal(str)          # página a abrir ("inicio", "config"...)
    config_mudou = Signal()
    sair = Signal()

    def __init__(self, cfg, motor):
        super().__init__()
        self.cfg, self.motor = cfg, motor
        self.icones = {e: _icone(c) for e, c in CORES.items()}
        self.estado = "carregando"
        self.tray = QSystemTrayIcon(self.icones["carregando"])
        self.tray.activated.connect(self._clicou)
        self.voltar = QTimer(self, singleShot=True, timeout=lambda: self.definir("pronto"))
        self._montar_menu()
        self.definir("carregando")
        self.tray.show()

    def _montar_menu(self):
        m = QMenu()
        m.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        m.setWindowFlags(m.windowFlags() | Qt.WindowType.FramelessWindowHint | Qt.WindowType.NoDropShadowWindowHint)
        cab = QWidget()
        lay = QHBoxLayout(cab)
        lay.setContentsMargins(10, 8, 10, 10)
        lay.setSpacing(10)
        img = QLabel()
        img.setPixmap(tema.papagaio().scaled(34, 34, Qt.AspectRatioMode.KeepAspectRatio,
                                             Qt.TransformationMode.SmoothTransformation))
        col = QVBoxLayout()
        col.setSpacing(0)
        nome = rotulo("Papory")
        nome.setFont(tema.fonte(18, tema.QFont.Weight.DemiBold, marca=True))
        self.rotulo_estado = rotulo("", "pequeno")
        col.addWidget(nome)
        col.addWidget(self.rotulo_estado)
        lay.addWidget(img)
        lay.addLayout(col)
        lay.addStretch(1)
        acao_cab = QWidgetAction(m)
        acao_cab.setDefaultWidget(cab)
        m.addAction(acao_cab)
        m.addSeparator()
        abrir = m.addAction("Abrir o Papory", lambda: self.abrir.emit("inicio"))
        f = abrir.font()
        f.setBold(True)
        abrir.setFont(f)
        m.addAction("Copiar o último ditado", self._copiar_ultimo)
        self.menu_mic = m.addMenu("Microfone")
        self.menu_mic.aboutToShow.connect(self._montar_microfones)
        m.addSeparator()
        self.acao_polimento = self._marcavel(m, "Polimento local", self._polimento)
        self.acao_reforco = self._marcavel(m, "Reforço na nuvem (Groq)", self._reforco)
        self.acao_pausa = self._marcavel(m, "Pausar o atalho", lambda v: self.motor.pausar(v))
        m.addSeparator()
        self.acao_iniciar = self._marcavel(m, f"Iniciar com o {plataforma.NOME}", self._iniciar)
        m.addAction("Sair", self.sair.emit)
        m.aboutToShow.connect(self.sincronizar)
        self.menu = m
        self.tray.setContextMenu(m)

    @staticmethod
    def _marcavel(menu, texto, ao_mudar):
        a = menu.addAction(texto)
        a.setCheckable(True)
        a.toggled.connect(ao_mudar)
        return a

    def sincronizar(self):
        """Marca no menu o estado atual (pode ter mudado pela janela)."""
        for acao, valor in ((self.acao_polimento, self.cfg["polimento"]["ativo"]),
                            (self.acao_reforco, self.cfg["reforco_nuvem"]["ativo"]),
                            (self.acao_pausa, self.motor.pausado), (self.acao_iniciar, plataforma.inicio_ligado())):
            acao.blockSignals(True)
            acao.setChecked(bool(valor))
            acao.blockSignals(False)
        self.rotulo_estado.setText(self._texto_estado())

    def _texto_estado(self):
        atalho = " + ".join(nome_tecla(t) for t in self.cfg["atalho"])
        if self.estado == "pronto":
            return f"Pronto · segure {atalho}"
        return TEXTOS[self.estado].capitalize()

    def _montar_microfones(self):
        self.menu_mic.clear()
        grupo = QActionGroup(self.menu_mic)
        atual = self.cfg["microfone"]
        padrao = audio.microfone_padrao()
        opcoes = [(None, f"Padrão do {plataforma.NOME}{f' ({padrao})' if padrao else ''}")]
        opcoes += [(n, n) for n in audio.listar_microfones()]
        for valor, texto in opcoes:
            a = QAction(texto, grupo)
            a.setCheckable(True)
            a.setChecked(valor == atual)
            a.triggered.connect(lambda _=False, v=valor: self._trocar_microfone(v))
            self.menu_mic.addAction(a)

    def _salvar(self):
        config.salvar(self.cfg)
        self.motor.aplicar_config()
        self.config_mudou.emit()

    def _trocar_microfone(self, valor):
        self.cfg["microfone"] = valor
        self._salvar()

    def _polimento(self, ligado):
        self.cfg["polimento"]["ativo"] = ligado
        self._salvar()

    def _reforco(self, ligado):
        self.cfg["reforco_nuvem"]["ativo"] = ligado
        self._salvar()
        if ligado and not config.chave("GROQ_API_KEY", self.cfg):
            self.abrir.emit("config")  # falta a chave: abre onde ela é colada

    def _iniciar(self, ligado):
        plataforma.ligar_inicio(ligado)
        self.config_mudou.emit()

    def _copiar_ultimo(self):
        texto = self.motor.copiar_ultimo()
        if not texto:
            self.tray.showMessage("Papory", "Ainda não há ditado para copiar.", self.icones["pronto"], 2500)

    def _clicou(self, motivo):
        if motivo in (QSystemTrayIcon.ActivationReason.DoubleClick, QSystemTrayIcon.ActivationReason.Trigger):
            self.abrir.emit("inicio")

    def definir(self, estado):
        if self.motor.pausado and estado == "pronto":
            estado = "pausado"
        self.estado = estado
        self.tray.setIcon(self.icones[estado])
        self.tray.setToolTip(f"Papory — {self._texto_estado().lower()}")

    def ao_evento(self, evento, dados):
        self.voltar.stop()
        if evento == "carregando":
            self.definir("carregando")
        elif evento in ("ouvindo", "escrevendo"):
            self.definir("ouvindo")
        elif evento in ("pronto", "colado", "copiado", "silencio", "entregue", "ditado"):
            if not self.motor.gravando:
                self.definir("pronto")
        elif evento == "pausado":
            self.definir("pausado" if dados else "pronto")
        elif evento in ("erro", "sem_microfone"):
            self.definir("atencao")
            self.voltar.start(6000)
            if evento == "erro" and dados:
                self.tray.showMessage("Papory", str(dados), QSystemTrayIcon.MessageIcon.Warning, 5000)

    def avisar(self, texto):
        self.tray.showMessage("Papory", texto, self.icones["pronto"], 4000)
