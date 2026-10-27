"""Janela principal: menu lateral (Início, Vocabulário, Atalhos de texto, Configurações) + estado do Papory."""
import webbrowser

from PySide6.QtCore import QSize, Qt, QTimer, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (QButtonGroup, QFrame, QHBoxLayout, QMainWindow, QPushButton, QStackedWidget,
                               QVBoxLayout, QWidget)

from .. import config
from . import tema
from .atualizar import CartaoAtualizacao
from .pag_atalhos import PaginaAtalhos
from .pag_config import REPO, PaginaConfig, link_issue
from .pag_inicio import PaginaInicio
from .pag_vocabulario import PaginaVocabulario
from .widgets import cartao, icone, limpar_layout, linha, rotulo, teclas

PAGINAS = [("inicio", "Início", "inicio"), ("vocabulario", "Vocabulário", "vocabulario"),
           ("atalhos", "Atalhos de texto", "atalhos"), ("config", "Configurações", "config")]
ESTADOS = {"pronto": ("Pronto para ouvir", tema.VERDE_VIVO), "carregando": ("Carregando a voz…", "#C9A227"),
           "pausado": ("Pausado", "#8A9580"), "atencao": ("Precisa de atenção", "#D92D20")}


class Janela(QMainWindow):
    fechou_primeira_vez = Signal()

    def __init__(self, cfg, motor):
        super().__init__()
        self.cfg, self.motor = cfg, motor
        self.estado = "carregando"
        self.setWindowTitle("Papory")
        self.setWindowIcon(QIcon(str(tema.IMAGENS / "papory.ico")))
        self.resize(1120, 800)
        self.setMinimumSize(880, 600)

        central = QWidget()
        central.setObjectName("fundo")
        h = QHBoxLayout(central)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(0)

        self.menu = menu = QFrame()
        menu.setObjectName("menu")
        menu.setFixedWidth(248)
        mv = QVBoxLayout(menu)
        mv.setContentsMargins(16, 24, 16, 20)
        mv.setSpacing(28)
        logo = QHBoxLayout()
        logo.setContentsMargins(8, 0, 0, 0)
        logo.setSpacing(10)
        img = rotulo("")
        img.setPixmap(tema.papagaio().scaled(44, 44, Qt.AspectRatioMode.KeepAspectRatio,
                                             Qt.TransformationMode.SmoothTransformation))
        logo.addWidget(img)
        logo.addWidget(rotulo("Papory", "marca"))
        logo.addStretch(1)
        mv.addLayout(logo)

        nav = QVBoxLayout()
        nav.setSpacing(4)
        self.grupo = QButtonGroup(self)
        self.botoes = {}
        for chave, texto, nome_icone in PAGINAS:
            b = QPushButton(texto)
            b.setProperty("papel", "nav")
            b.setCheckable(True)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setIcon(icone(nome_icone, "#2E3A27", 20))
            b.setIconSize(QSize(20, 20))
            b.clicked.connect(lambda _=False, c=chave: self.ir(c))
            self.grupo.addButton(b)
            self.botoes[chave] = b
            nav.addWidget(b)
        mv.addLayout(nav)
        self.cartao_atualizacao = CartaoAtualizacao()  # só aparece quando há versão nova
        # mede no próximo giro: logo depois de trocar o texto, a altura que o Qt informa ainda é a antiga
        self.cartao_atualizacao.mudou.connect(lambda: QTimer.singleShot(0, self._ajustar_lateral))
        mv.addWidget(self.cartao_atualizacao)
        mv.addStretch(1)

        self.ajuda = QWidget()  # sempre à vista: estrela, erro e sugestão no GitHub
        ajuda = QVBoxLayout(self.ajuda)
        ajuda.setContentsMargins(0, 0, 0, 0)
        ajuda.setSpacing(2)
        titulo = rotulo("Gostou do Papory?", "pequeno")
        titulo.setContentsMargins(12, 0, 0, 4)
        ajuda.addWidget(titulo)
        atalhos = (("Dar uma estrela", "brilho", REPO), ("Relatar um erro", "alerta", link_issue("erro")),
                   ("Mandar sugestão", "mais", link_issue("sugestao")))
        for texto, nome_icone, link in atalhos:
            b = QPushButton(texto)
            b.setProperty("papel", "nav_ajuda")
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setIcon(icone(nome_icone, tema.TEXTO_2, 16))
            b.setIconSize(QSize(16, 16))
            b.setToolTip("Abre no navegador")
            b.clicked.connect(lambda _=False, u=link: webbrowser.open(u))
            ajuda.addWidget(b)
        mv.addWidget(self.ajuda)

        self.status, self.status_lay = cartao(margens=(16, 16, 16, 16), espaco=10)
        mv.addWidget(self.status)
        h.addWidget(menu)

        self.pilha = QStackedWidget()
        h.addWidget(self.pilha, 1)
        self.setCentralWidget(central)

        self.pags = {"inicio": PaginaInicio(self), "vocabulario": PaginaVocabulario(self),
                     "atalhos": PaginaAtalhos(self), "config": PaginaConfig(self)}
        for p in self.pags.values():
            self.pilha.addWidget(p.area)
        self.atual = None
        self.atraso_inicio = QTimer(self, singleShot=True, interval=200,
                                    timeout=lambda: self.atual == "inicio" and self.pags["inicio"].recarregar())
        self.ja_fechou = False
        self.ir("inicio")
        self.atualizar_status()

    def resizeEvent(self, ev):
        super().resizeEvent(ev)
        self._ajustar_lateral()

    def _ajustar_lateral(self):
        """Janela baixa: o cartão de estado não pode apertar. Sai primeiro o "Gostou do Papory?" (o aviso de
        versão nova passa na frente dele) e depois a explicação do aviso; o botão Atualizar fica sempre."""
        if not hasattr(self, "ajuda"):
            return
        lay, c = self.menu.layout(), self.cartao_atualizacao

        def cabe():
            precisa = lay.totalHeightForWidth(self.menu.width()) if lay.hasHeightForWidth() else -1
            # folga de 8 px: a conta do Qt para o texto que quebra em duas linhas sai um pouco curta
            return (precisa if precisa > 0 else lay.totalSizeHint().height()) + 8 <= self.menu.height()

        lay.setSpacing(28)
        c.compactar(False)
        self.ajuda.show()
        if cabe():
            return
        self.ajuda.hide()
        if c.isHidden() or cabe():
            return
        c.compactar(True)
        if not cabe():  # perto da altura mínima: aproxima os blocos
            lay.setSpacing(8)

    # ------------------------------------------------------------ navegação
    def ir(self, chave):
        self.atual = chave
        self.botoes[chave].setChecked(True)
        for c, b in self.botoes.items():
            b.setIcon(icone(dict((k, n) for k, _, n in PAGINAS)[c], "#17410C" if c == chave else "#2E3A27", 20))
        self.pags[chave].recarregar()
        self.pilha.setCurrentWidget(self.pags[chave].area)

    def mostrar(self, chave="inicio"):
        self.ir(chave)
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def closeEvent(self, ev):
        ev.ignore()  # fechar a janela não fecha o Papory: ele continua na bandeja
        self.hide()
        if not self.ja_fechou:
            self.ja_fechou = True
            self.fechou_primeira_vez.emit()

    # ------------------------------------------------------- configuração
    def salvar_config(self):
        config.salvar(self.cfg)
        self.motor.aplicar_config()
        self.atualizar_status()

    def vocabulario_mudou(self):
        if self.atual == "vocabulario":
            self.pags["vocabulario"].recarregar()

    def historico_mudou(self):
        self.pags["inicio"].recarregar()

    def config_mudou_fora(self):
        """A bandeja mudou algo: redesenha o que está na tela."""
        self.atualizar_status()
        if self.isVisible() and self.atual in ("config", "inicio"):
            self.pags[self.atual].recarregar()

    # ---------------------------------------------------------------- estado
    def ao_evento(self, evento, dados):
        if evento == "carregando":
            self.estado = "carregando"
        elif evento == "pronto":
            self.estado = "pausado" if self.motor.pausado else "pronto"
        elif evento == "pausado":
            self.estado = "pausado" if dados else "pronto"
        elif evento in ("erro", "sem_microfone"):
            self.estado = "atencao"
            QTimer.singleShot(6000, lambda: self.estado == "atencao" and self._voltar_pronto())
        elif evento == "ditado" and self.isVisible():
            self.atraso_inicio.start()
        self.atualizar_status()

    def _voltar_pronto(self):
        self.estado = "pausado" if self.motor.pausado else "pronto"
        self.atualizar_status()

    def atualizar_status(self):
        lay = self.status_lay
        limpar_layout(lay)
        texto, cor = ESTADOS[self.estado]
        topo = QHBoxLayout()
        topo.setSpacing(8)
        ponto = QFrame()
        ponto.setFixedSize(10, 10)
        ponto.setStyleSheet(f"background: {cor}; border-radius: 5px;")
        topo.addWidget(ponto)
        t = rotulo(texto)
        t.setStyleSheet("font-weight: 700; font-size: 14px;")
        topo.addWidget(t)
        topo.addStretch(1)
        lay.addLayout(topo)
        at = QHBoxLayout()
        at.setSpacing(6)
        at.addWidget(rotulo("Segure", "meta"))
        at.addWidget(teclas(self.cfg["atalho"]))
        at.addStretch(1)
        lay.addLayout(at)
        lay.addWidget(linha())
        m, c = self.motor, self.cfg
        rec = getattr(m, "rec", None)
        voz = ("na placa de vídeo" if "placa" in rec.onde else "no processador") if rec else "carregando"
        polidor = getattr(m, "polidor", None)
        if not c["polimento"]["ativo"]:
            pol = "desligado"
        elif polidor is None:
            pol = "no seu PC"
        else:
            pol = "no seu PC" if polidor.local_ok else "indisponível"
        nuvem = c["reforco_nuvem"]["ativo"] and bool(config.chave("GROQ_API_KEY", c))
        for nome_icone, texto_linha, cor_linha in (("chip", f"Voz: {voz}", "#3D4935"),
                                                   ("brilho", f"Polimento: {pol}", "#3D4935"),
                                                   ("nuvem", f"Reforço na nuvem: {'ligado' if nuvem else 'desligado'}",
                                                    tema.LARANJA_TEXTO if nuvem else "#3D4935")):
            ln = QHBoxLayout()
            ln.setSpacing(8)
            ic = rotulo("")
            ic.setPixmap(icone(nome_icone, cor_linha, 16).pixmap(16, 16))
            ln.addWidget(ic)
            r = rotulo(texto_linha, quebra=True)
            r.setStyleSheet(f"font-size: 13px; color: {cor_linha};")
            ln.addWidget(r, 1)
            lay.addLayout(ln)
