"""Primeira abertura em 3 passos: baixar o modelo de voz, testar o microfone, conhecer o atalho."""

from PySide6.QtCore import QObject, Qt, QTimer, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (QApplication, QComboBox, QFrame, QHBoxLayout, QPlainTextEdit, QProgressBar,
                               QStackedWidget, QVBoxLayout, QWidget)

from .. import audio, config, modelo, plataforma
from . import tema
from .calibracao import Calibracao
from .pag_config import DialogoAtalho, StatusPolimento, _gb, _icone_rotulo
from .widgets import Medidor, botao, cartao, limpar_layout, rotulo, teclas


class _Ponte(QObject):
    progresso = Signal(object, object)
    terminou = Signal(object)
    ouviu = Signal(str)


class PrimeiraAbertura(QWidget):
    concluiu = Signal()

    def __init__(self, cfg, motor, carregar_motor):
        super().__init__()
        self.cfg, self.motor, self.carregar_motor = cfg, motor, carregar_motor
        self.motor_iniciado = False
        self.ponte = _Ponte()
        self.ponte.progresso.connect(self._progresso)
        self.ponte.terminou.connect(self._baixou)
        self.ponte.ouviu.connect(self._ouviu)
        self.setWindowTitle("Bem-vindo ao Papory")
        self.setWindowIcon(QIcon(str(tema.IMAGENS / "papory.ico")))
        self.setObjectName("fundo")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground)
        self.setFixedSize(520, 740)
        v = QVBoxLayout(self)
        v.setContentsMargins(24, 24, 24, 24)
        self.pilha = QStackedWidget()
        v.addWidget(self.pilha)
        self.pilha.addWidget(self._passo1())
        self.pilha.addWidget(self._passo2())
        self.pilha.addWidget(self._passo3())
        self.relogio = QTimer(self, interval=50, timeout=self._quadro)
        self.relogio.start()
        QTimer.singleShot(0, self._conferir_modelo)

    # --------------------------------------------------------------- moldura
    def _moldura(self, numero):
        f = QFrame()
        f.setProperty("papel", "passo")
        lay = QVBoxLayout(f)
        lay.setContentsMargins(28, 26, 28, 26)
        lay.setSpacing(16)
        topo = QHBoxLayout()
        topo.addWidget(rotulo(f"Passo {numero} de 3", "meta"))
        topo.addStretch(1)
        for i in range(3):
            barra = QFrame()
            barra.setFixedSize(28, 6)
            barra.setStyleSheet(f"background: {tema.VERDE if i < numero else '#DCE4D2'}; border-radius: 3px;")
            topo.addWidget(barra)
        lay.addLayout(topo)
        return f, lay

    def _passo1(self):
        f, lay = self._moldura(1)
        circulo = QFrame()
        circulo.setObjectName("circulo")
        circulo.setFixedSize(190, 190)
        circulo.setStyleSheet("QFrame#circulo { background: #E9F5DF; border-radius: 95px; }")
        cl = QVBoxLayout(circulo)
        cl.setContentsMargins(5, 5, 5, 5)
        img = rotulo("")
        img.setPixmap(tema.papagaio("papory-microfone-512.png").scaled(
            180, 180, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        img.setAccessibleName("O papagaio do Papory falando num microfone")
        cl.addWidget(img, 0, Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(circulo, 0, Qt.AlignmentFlag.AlignHCenter)
        t = rotulo("Oi! Eu sou o Papory.", "titulo")
        t.setStyleSheet("font-size: 24px;")
        t.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(t)
        s = rotulo("Segure um atalho, fale e solte. O texto aparece onde o cursor está, em qualquer programa.",
                   "sub", quebra=True)
        s.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(s)
        priv = QHBoxLayout()
        priv.addStretch(1)
        priv.addWidget(_icone_rotulo("cadeado", tema.VERDE))
        priv.addWidget(rotulo("Roda no seu computador. A sua voz não sai daqui.", "verde"))
        priv.addStretch(1)
        lay.addLayout(priv)
        lay.addStretch(1)
        self.caixa_baixar, bl = cartao("suave", (16, 14, 16, 14), 8)
        topo = QHBoxLayout()
        self.rot_baixar = rotulo("Modelo de voz", "rotulo", quebra=True)
        self.rot_tamanho = rotulo("", "meta")
        topo.addWidget(self.rot_baixar, 1)
        topo.addWidget(self.rot_tamanho, 0, Qt.AlignmentFlag.AlignTop)
        bl.addLayout(topo)
        self.barra = QProgressBar()
        self.barra.setTextVisible(False)
        self.barra.setRange(0, 1000)
        bl.addWidget(self.barra)
        self.rot_baixar_obs = rotulo("Só desta vez. Depois funciona sem internet.", "pequeno", quebra=True)
        bl.addWidget(self.rot_baixar_obs)
        lay.addWidget(self.caixa_baixar)
        self.b_passo1 = botao("Conferindo…", "primario")
        self.b_passo1.setEnabled(False)
        self.b_passo1.clicked.connect(self._passo1_clicou)
        lay.addWidget(self.b_passo1)
        return f

    def _passo2(self):
        f, lay = self._moldura(2)
        lay.addWidget(rotulo("Teste o microfone", "titulo"))
        lay.itemAt(lay.count() - 1).widget().setStyleSheet("font-size: 24px;")
        lay.addWidget(rotulo("Microfone", "rotulo"))
        self.mic = QComboBox()
        self.mic.setAccessibleName("Microfone")
        padrao = audio.microfone_padrao()
        self.mic.addItem(f"Padrão do {plataforma.NOME}{f' ({padrao})' if padrao else ''}", None)
        for n in audio.listar_microfones():
            self.mic.addItem(n, n)
        i = self.mic.findData(self.cfg["microfone"])
        self.mic.setCurrentIndex(i if i >= 0 else 0)
        self.mic.activated.connect(self._trocar_mic)
        lay.addWidget(self.mic)
        linha_at = QHBoxLayout()
        linha_at.setSpacing(6)
        linha_at.addWidget(rotulo("Segure", "sub"))
        self.teclas2 = QHBoxLayout()
        linha_at.addLayout(self.teclas2)
        linha_at.addWidget(rotulo("e leia em voz alta:", "sub"))
        linha_at.addStretch(1)
        lay.addLayout(linha_at)
        frase, fl = cartao("dica", (18, 16, 18, 16))
        r = rotulo("“Testando o Papory, um, dois, três.”")
        r.setStyleSheet("font-size: 18px; font-weight: 700; color: #4A2A00;")
        r.setWordWrap(True)
        fl.addWidget(r)
        lay.addWidget(frase)
        vol = QHBoxLayout()
        vol.setSpacing(12)
        vol.addWidget(rotulo("Volume", "meta"))
        self.medidor = Medidor(10)
        vol.addWidget(self.medidor, 1)
        lay.addLayout(vol)
        self.resultado, self.res_lay = cartao("ok", (16, 14, 16, 14), 12, horizontal=True)
        lay.addWidget(self.resultado)
        caixa_cal, cl = cartao(margens=(16, 14, 16, 14), espaco=6)
        topo = QHBoxLayout()
        topo.setSpacing(8)
        topo.addWidget(_icone_rotulo("microfone", tema.VERDE, 18))
        topo.addWidget(rotulo("Ensine seu jeito de falar", "h3"))
        topo.addStretch(1)
        self.b_calibrar = botao("Começar")
        self.b_calibrar.clicked.connect(self._calibrar)
        topo.addWidget(self.b_calibrar)
        cl.addLayout(topo)
        self.rot_calibrar = rotulo("Opcional, uns 2 minutos: leia algumas frases e o Papory aprende os nomes que "
                                   "você mais usa.", "meta", quebra=True)
        cl.addWidget(self.rot_calibrar)
        lay.addWidget(caixa_cal)
        lay.addStretch(1)
        botoes = QHBoxLayout()
        voltar, seguir = botao("Voltar"), botao("Continuar", "primario")
        voltar.clicked.connect(lambda: self._ir(0))
        seguir.clicked.connect(lambda: self._ir(2))
        botoes.addWidget(voltar, 1)
        botoes.addWidget(seguir, 2)
        lay.addLayout(botoes)
        return f

    def _passo3(self):
        f, lay = self._moldura(3)
        t = rotulo("Pronto para usar", "titulo")
        t.setStyleSheet("font-size: 24px;")
        lay.addWidget(t)
        at = QHBoxLayout()
        at.setSpacing(8)
        at.addWidget(rotulo("Seu atalho", "sub"))
        self.teclas3 = QHBoxLayout()
        at.addLayout(self.teclas3)
        at.addStretch(1)
        trocar = botao("Trocar")
        trocar.clicked.connect(self._trocar_atalho)
        at.addWidget(trocar)
        lay.addLayout(at)
        lay.addWidget(rotulo("Experimente: clique aqui, segure o atalho e fale", "rotulo"))
        self.experimente = QPlainTextEdit()
        self.experimente.setPlaceholderText("O texto vai aparecer aqui")
        self.experimente.setFixedHeight(90)
        lay.addWidget(self.experimente)
        pol, pl = cartao(margens=(16, 14, 16, 14), espaco=10)
        topo = QHBoxLayout()
        topo.setSpacing(8)
        topo.addWidget(_icone_rotulo("brilho", tema.VERDE, 18))
        topo.addWidget(rotulo("Polimento local", "h3"))
        topo.addWidget(rotulo("opcional", "tag_neutra"))
        topo.addStretch(1)
        pl.addLayout(topo)
        pl.addWidget(rotulo("Corrige palavras que soam parecido com uma IA pequena no seu computador.", "meta",
                            quebra=True))
        self.status_pol = StatusPolimento(self.cfg)
        self.status_pol.mudou.connect(self.motor.aplicar_config)
        pl.addWidget(self.status_pol)
        lay.addWidget(pol)
        lay.addWidget(rotulo("O reforço na nuvem começa desligado. Dá para ligar depois, nas Configurações.",
                             "pequeno", quebra=True))
        lay.addStretch(1)
        concluir = botao("Concluir", "primario")
        concluir.clicked.connect(self._concluir)
        lay.addWidget(concluir)
        return f

    # ------------------------------------------------------------- lógica
    def _conferir_modelo(self):
        if modelo.baixado():
            self.rot_baixar.setText("O modelo de voz já está no computador")
            self.rot_tamanho.setText(_gb(modelo.tamanho_no_disco()))
            self.barra.setValue(1000)
            self.rot_baixar_obs.setText("Pronto. Funciona sem internet.")
            self.b_passo1.setText("Continuar")
            self.b_passo1.setEnabled(True)
            self._iniciar_motor()
        else:
            self.rot_tamanho.setText("cerca de 2,5 GB")
            self.b_passo1.setText("Baixar e continuar")
            self.b_passo1.setEnabled(True)

    def _passo1_clicou(self):
        if self.motor_iniciado:
            self._ir(1)
            return
        self.b_passo1.setEnabled(False)
        self.b_passo1.setText("Baixando…")
        self.rot_baixar.setText("Baixando o modelo de voz")
        modelo.baixar(lambda feito, total: self.ponte.progresso.emit(feito, total),
                      lambda erro: self.ponte.terminou.emit(erro))

    def _progresso(self, feito, total):
        if total:
            self.barra.setValue(int(1000 * min(feito / total, 1.0)))
            self.rot_tamanho.setText(f"{_gb(feito)} de {_gb(total)}")
        else:
            self.barra.setRange(0, 0)  # sem saber o total: barra "andando"
            self.rot_tamanho.setText(_gb(feito))

    def _baixou(self, erro):
        self.barra.setRange(0, 1000)
        if erro:
            self.rot_baixar.setText("Não consegui baixar")
            self.rot_baixar_obs.setText("Confira a internet e tente de novo.")
            self.b_passo1.setText("Tentar de novo")
            self.b_passo1.setEnabled(True)
            return
        self.barra.setValue(1000)
        self.rot_baixar.setText("Modelo de voz baixado")
        self.rot_baixar_obs.setText("Pronto. Funciona sem internet.")
        self.b_passo1.setText("Continuar")
        self.b_passo1.setEnabled(True)
        self._iniciar_motor()

    def _iniciar_motor(self):
        if not self.motor_iniciado:
            self.motor_iniciado = True
            self.carregar_motor()

    def _ir(self, i):
        self.pilha.setCurrentIndex(i)
        for caixa in (self.teclas2, self.teclas3):
            limpar_layout(caixa)
            caixa.addWidget(teclas(self.cfg["atalho"]))
        if i == 1:
            self.motor.entregar = lambda texto: self.ponte.ouviu.emit(texto)
            self._mostrar_resultado(None)
        else:
            self.motor.entregar = None
        if i == 2:
            self.experimente.setFocus()

    def _mostrar_resultado(self, texto, ok=True):
        limpar_layout(self.res_lay)
        if texto is None:
            msg = ("Pronto: segure o atalho e leia a frase." if self.motor.pronto else
                   "Preparando o reconhecimento… leva alguns segundos.")
            self.resultado.setProperty("papel", "suave")
            self.res_lay.addWidget(rotulo(msg, "meta", quebra=True), 1)
        else:
            self.resultado.setProperty("papel", "ok" if ok else "aviso")
            self.res_lay.addWidget(_icone_rotulo("visto" if ok else "alerta", tema.VERDE if ok else "#B35A00", 20),
                                   0, Qt.AlignmentFlag.AlignTop)
            col = QVBoxLayout()
            col.setSpacing(4)
            col.addWidget(rotulo("Ficou ótimo." if ok else "Não ouvi nada.", "h3"))
            col.addWidget(rotulo(f"Ouvi: “{texto}”" if ok else "Fale um pouco mais perto do microfone, segurando o "
                                 "atalho enquanto fala.", "meta", quebra=True))
            self.res_lay.addLayout(col, 1)
        self.resultado.style().unpolish(self.resultado)
        self.resultado.style().polish(self.resultado)

    def _ouviu(self, texto):
        self._mostrar_resultado(texto)

    def ao_evento(self, evento, dados):
        if self.pilha.currentIndex() != 1:
            return
        if evento == "pronto":
            self._mostrar_resultado(None)
        elif evento == "silencio":
            self._mostrar_resultado("", ok=False)

    def _quadro(self):
        if self.pilha.currentIndex() == 1:
            self.medidor.definir(self.motor.nivel())

    def _trocar_mic(self, _):
        self.cfg["microfone"] = self.mic.currentData()
        config.salvar(self.cfg)
        self.motor.aplicar_config()

    def _trocar_atalho(self):
        estava = self.motor.pausado
        self.motor.pausar(True)
        d = DialogoAtalho(self, self.cfg["atalho"])
        if d.exec() and d.combinacao:
            self.cfg["atalho"] = list(d.combinacao)
            config.salvar(self.cfg)
            self.motor.aplicar_config()
            self._ir(2)
        self.motor.pausar(estava)

    def _calibrar(self):
        d = Calibracao(self, self.cfg, self.motor, lambda: (config.salvar(self.cfg), self.motor.aplicar_config()))
        d.terminou.connect(self._calibrou)
        d.exec()

    def _calibrou(self, aprendido):
        n = len(aprendido["regras"]) + len(aprendido["vocabulario"])
        self.rot_calibrar.setText(f"Feito. Aprendi {n} {'coisa nova' if n == 1 else 'coisas novas'} sobre o seu "
                                  "jeito de falar." if n else "Feito. O Papory já entende bem o seu jeito de falar.")
        self.b_calibrar.setText("Fazer de novo")

    def _concluir(self):
        self.motor.entregar = None
        self.cfg["interface"]["primeira_abertura_feita"] = True
        config.salvar(self.cfg)
        self.relogio.stop()
        self.hide()
        self.concluiu.emit()

    def closeEvent(self, ev):
        if not self.motor_iniciado:  # sem o modelo de voz o Papory não funciona
            QApplication.quit()
            return
        ev.ignore()
        self._concluir()
