"""Janela "Ensine seu jeito de falar": ler frases curtas para o Papory aprender como a pessoa fala."""

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (QCheckBox, QDialog, QHBoxLayout, QLineEdit, QProgressBar, QStackedWidget,
                               QVBoxLayout, QWidget)

from .. import calibracao as cal
from .. import plataforma
from . import tema
from .widgets import Medidor, botao, cartao, icone, limpar_layout, rotulo, teclas

_aberta = None
ESPERA_PROXIMA_MS = 1200  # leitura sem erro: passa sozinho para a próxima frase


def _icone_rotulo(nome, cor, tam=16):
    r = rotulo("")
    r.setPixmap(icone(nome, cor, tam, 2).pixmap(tam, tam))
    return r


def repassar(evento, dados):
    """O app liga os eventos do motor aqui; eles chegam na janela de calibração aberta, se houver."""
    if _aberta is not None:
        _aberta.ao_evento(evento, dados)


def _pagina():
    w = QWidget()
    lay = QVBoxLayout(w)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.setSpacing(14)
    return w, lay


class Calibracao(QDialog):
    terminou = Signal(object)  # o que foi aprendido: {"regras", "vocabulario"}

    def __init__(self, pai, cfg, motor, salvar):
        global _aberta
        super().__init__(pai)
        self.cfg, self.motor, self.salvar = cfg, motor, salvar
        self.setWindowTitle("Ensine seu jeito de falar")
        self.setStyleSheet(f"QDialog {{ background: {tema.BRANCO}; }}")
        self.setMinimumSize(560, 600)
        self.frases, self.termos, self.leituras, self.volumes = [], [], [], []
        self.i, self.fala_da_frase, self.proposta, self.salvo = 0, None, None, False
        self.marcas = []

        v = QVBoxLayout(self)
        v.setContentsMargins(28, 26, 28, 24)
        self.pilha = QStackedWidget()
        v.addWidget(self.pilha)
        self.pilha.addWidget(self._pag_inicio())
        self.pilha.addWidget(self._pag_leitura())
        self.pilha.addWidget(self._pag_fim())

        self.entregar_antes, self.pausado_antes = motor.entregar, motor.pausado
        motor.entregar = lambda texto: None  # o texto lido não é colado em lugar nenhum
        if motor.pausado:
            motor.pausar(False)
        self.relogio = QTimer(self, interval=50, timeout=self._quadro)
        self.proxima_sozinho = QTimer(self, singleShot=True, interval=ESPERA_PROXIMA_MS, timeout=self._proxima)
        _aberta = self

    # ------------------------------------------------------------ páginas
    def _pag_inicio(self):
        w, lay = _pagina()
        t = rotulo("Ensine seu jeito de falar", "titulo")
        t.setStyleSheet("font-size: 24px;")
        lay.addWidget(t)
        lay.addWidget(rotulo("Você lê algumas frases curtas segurando o atalho. O Papory compara o que ouviu com o "
                             "texto, aprende as palavras que errou e confere o volume do microfone. Leva uns 2 "
                             "minutos.", "sub", quebra=True))
        lay.addSpacing(6)
        topo = QHBoxLayout()
        topo.setSpacing(8)
        topo.addWidget(rotulo("Nomes e termos que você mais fala", "rotulo"))
        topo.addWidget(rotulo("opcional", "tag_neutra"))
        topo.addStretch(1)
        lay.addLayout(topo)
        self.campo_termos = QLineEdit()
        self.campo_termos.setPlaceholderText("Ex.: o nome da sua empresa, de clientes, de ferramentas")
        self.campo_termos.setAccessibleName("Nomes e termos que você mais fala")
        lay.addWidget(self.campo_termos)
        lay.addWidget(rotulo("Separe por vírgula. Eles entram nas frases e vão para o seu vocabulário.", "pequeno",
                             quebra=True))
        lay.addStretch(1)
        botoes = QHBoxLayout()
        cancelar, comecar = botao("Cancelar"), botao("Começar", "primario")
        cancelar.clicked.connect(self.reject)
        comecar.clicked.connect(self._comecar)
        botoes.addWidget(cancelar, 1)
        botoes.addWidget(comecar, 2)
        lay.addLayout(botoes)
        return w

    def _pag_leitura(self):
        w, lay = _pagina()
        topo = QHBoxLayout()
        self.rot_contagem = rotulo("", "meta")
        topo.addWidget(self.rot_contagem)
        topo.addStretch(1)
        self.barra = QProgressBar()
        self.barra.setTextVisible(False)
        self.barra.setFixedWidth(180)
        topo.addWidget(self.barra)
        lay.addLayout(topo)
        linha_at = QHBoxLayout()
        linha_at.setSpacing(6)
        linha_at.addWidget(rotulo("Segure", "sub"))
        self.caixa_teclas = QHBoxLayout()
        linha_at.addLayout(self.caixa_teclas)
        linha_at.addWidget(rotulo("e leia em voz alta:", "sub"))
        linha_at.addStretch(1)
        lay.addLayout(linha_at)
        frase, fl = cartao("dica", (20, 18, 20, 18))
        self.rot_frase = rotulo("")
        self.rot_frase.setStyleSheet("font-size: 20px; font-weight: 700; color: #4A2A00;")
        self.rot_frase.setWordWrap(True)
        self.rot_frase.setMinimumHeight(64)
        fl.addWidget(self.rot_frase)
        lay.addWidget(frase)
        vol = QHBoxLayout()
        vol.setSpacing(12)
        vol.addWidget(rotulo("Volume", "meta"))
        self.medidor = Medidor(12)
        vol.addWidget(self.medidor, 1)
        lay.addLayout(vol)
        self.resultado, self.res_lay = cartao("suave", (16, 14, 16, 14), 12, horizontal=True)
        lay.addWidget(self.resultado)
        lay.addStretch(1)
        botoes = QHBoxLayout()
        self.b_repetir, self.b_proxima = botao("Repetir"), botao("Pular", "primario")
        self.b_repetir.clicked.connect(self._repetir)
        self.b_proxima.clicked.connect(self._proxima)
        botoes.addWidget(self.b_repetir, 1)
        botoes.addWidget(self.b_proxima, 2)
        lay.addLayout(botoes)
        return w

    def _pag_fim(self):
        w, lay = _pagina()
        t = rotulo("Pronto", "titulo")
        t.setStyleSheet("font-size: 24px;")
        lay.addWidget(t)
        self.fim_lay = QVBoxLayout()
        self.fim_lay.setSpacing(14)
        lay.addLayout(self.fim_lay)
        lay.addStretch(1)
        self.b_salvar = botao("Salvar e fechar", "primario")
        self.b_salvar.clicked.connect(self._salvar)
        lay.addWidget(self.b_salvar)
        return w

    # ------------------------------------------------------------ leitura
    def _comecar(self):
        self.termos = cal.separar_termos(self.campo_termos.text())
        self.frases = cal.montar_frases(self.termos)
        self.leituras = [None] * len(self.frases)
        self.volumes = [None] * len(self.frases)
        self.barra.setRange(0, len(self.frases))
        limpar_layout(self.caixa_teclas)
        self.caixa_teclas.addWidget(teclas(self.cfg["atalho"]))
        self.pilha.setCurrentIndex(1)
        self.relogio.start()
        self._mostrar_frase(0)

    def _mostrar_frase(self, i):
        self.i = i
        self.proxima_sozinho.stop()
        self.rot_contagem.setText(f"Frase {i + 1} de {len(self.frases)}")
        self.barra.setValue(i + 1)
        self.rot_frase.setText(f"“{self.frases[i]['texto']}”")
        self._atualizar_botoes()
        r = self.leituras[i]
        if r is None:
            self._cartao("suave", None, "Pronto: segure o atalho e leia a frase." if self.motor.pronto else
                         "Preparando o reconhecimento… leva alguns segundos.")
        else:
            self._mostrar_leitura(r)

    def _atualizar_botoes(self):
        ultima = self.i == len(self.frases) - 1
        lida = self.leituras[self.i] is not None
        self.b_proxima.setText("Ver resultado" if ultima and lida else "Próxima" if lida else "Pular")
        self.b_repetir.setEnabled(lida)

    def _cartao(self, papel, icone, titulo, texto=None):
        limpar_layout(self.res_lay)
        self.resultado.setProperty("papel", papel)
        if icone:
            cor = tema.VERDE if icone == "visto" else "#B35A00"
            self.res_lay.addWidget(_icone_rotulo(icone, cor, 20), 0, Qt.AlignmentFlag.AlignTop)
        col = QVBoxLayout()
        col.setSpacing(4)
        col.addWidget(rotulo(titulo, "h3" if texto else "meta", quebra=True))
        if texto:
            col.addWidget(rotulo(texto, "meta", quebra=True))
        self.res_lay.addLayout(col, 1)
        self.resultado.style().unpolish(self.resultado)
        self.resultado.style().polish(self.resultado)

    def _mostrar_leitura(self, r):
        ouvi = f"Ouvi: “{r['final']}”"
        if r["acertos"] == r["total"] and not r["diferencas"]:
            self._cartao("ok", "visto", "Certinho.", ouvi)
            return
        trocas = "; ".join(f"“{de}” no lugar de “{para}”" for de, para in r["diferencas"])
        detalhe = f"Escrevi {trocas}." if trocas else "Faltou ou sobrou alguma palavra."
        self._cartao("aviso", "alerta", "Saiu diferente em alguma parte.",
                     f"{ouvi}\n\n{detalhe} Se você leu certo, siga: é com isso que eu aprendo. Se leu diferente, "
                     "repita.")

    def _repetir(self):
        self.leituras[self.i] = self.volumes[self.i] = None
        self._mostrar_frase(self.i)

    def _proxima(self):
        if self.i < len(self.frases) - 1:
            self._mostrar_frase(self.i + 1)
        else:
            self._ver_resultado()

    def ao_evento(self, evento, dados):
        if self.pilha.currentIndex() != 1:
            return
        if evento == "pronto" and self.leituras[self.i] is None:
            self._mostrar_frase(self.i)
        elif evento == "ouvindo":
            self.proxima_sozinho.stop()
            self.fala_da_frase = self.i  # a fala é da frase que estava na tela quando apertou
            self._cartao("suave", None, "Ouvindo…")
        elif evento == "escrevendo":
            self._cartao("suave", None, "Escrevendo…")
        elif evento == "ditado" and self.fala_da_frase is not None:
            i, self.fala_da_frase = self.fala_da_frase, None
            self.leituras[i] = cal.avaliar(self.frases[i], dados["cru"], dados["final"])
            self.volumes[i] = dados.get("volume")
            if i == self.i:
                self._mostrar_leitura(self.leituras[i])
                self._atualizar_botoes()
                r = self.leituras[i]
                if r["acertos"] == r["total"] and not r["diferencas"]:
                    self.proxima_sozinho.start()
        elif evento == "silencio":
            self.fala_da_frase = None
            self._cartao("aviso", "alerta", "Não ouvi nada.", "Segure o atalho enquanto fala, com o microfone um "
                         "pouco mais perto.")
        elif evento in ("erro", "sem_microfone"):
            self.fala_da_frase = None
            self._cartao("aviso", "alerta", "Sem microfone." if evento == "sem_microfone" else "Algo deu errado.",
                         "Confira o microfone e tente de novo.")

    def _quadro(self):
        self.medidor.definir(self.motor.nivel())

    # ----------------------------------------------------------- resultado
    def _ver_resultado(self):
        self.relogio.stop()
        self.proxima_sozinho.stop()
        self.medidor.definir(0)
        lidas = [r for r in self.leituras if r]
        self.proposta = cal.propor(self.cfg, lidas, self.termos)
        limpar_layout(self.fim_lay)
        self.marcas = []
        lay = self.fim_lay
        if not lidas:
            lay.addWidget(rotulo("Você não leu nenhuma frase, então não tenho o que aprender desta vez.", "sub",
                                 quebra=True))
        else:
            acertos, total = sum(r["acertos"] for r in lidas), sum(r["total"] for r in lidas)
            lay.addWidget(rotulo(f"Acertei {acertos} de {total} palavras em {len(lidas)} "
                                 f"{'frase' if len(lidas) == 1 else 'frases'}.", "sub", quebra=True))
        p = self.proposta
        if p["regras"]:
            c, cl = cartao(margens=(18, 16, 18, 16), espaco=10)
            cl.addWidget(rotulo("Trocas automáticas", "h3"))
            cl.addWidget(rotulo("Quando o Papory ouvir a palavra da esquerda, escreve a da direita. Desmarque se "
                                "for uma palavra que você também usa no dia a dia.", "meta", quebra=True))
            for de, para in p["regras"]:
                caixa = QCheckBox(f"“{de}” vira “{para}”")
                caixa.setChecked((de, para) in p["marcadas"])
                cl.addWidget(caixa)
                if not caixa.isChecked():
                    nota = rotulo(f"“{de}” é comum no português. Só marque se o Papory sempre escreve isso no lugar "
                                  f"de “{para}”.", "pequeno", quebra=True)
                    nota.setContentsMargins(30, 0, 0, 0)
                    cl.addWidget(nota)
                self.marcas.append(((de, para), caixa))
            lay.addWidget(c)
        if p["vocabulario"]:
            c, cl = cartao(margens=(18, 16, 18, 16), espaco=8)
            cl.addWidget(rotulo("Entram no seu vocabulário", "h3"))
            cl.addWidget(rotulo(", ".join(p["vocabulario"]), "texto", quebra=True))
            lay.addWidget(c)
        if lidas and not p["regras"] and not p["vocabulario"]:
            lay.addWidget(rotulo("Nenhum nome para corrigir: o Papory já entende bem o seu jeito de falar.", "meta",
                                 quebra=True))
        veredito = cal.veredito_volume(self.volumes)
        if veredito:
            textos = {
                "bom": ("O volume do microfone está bom.", None),
                "baixo": ("Sua voz chegou baixinha.", "Chegue o microfone mais perto da boca ou aumente o volume "
                          f"de entrada nos ajustes de som do {plataforma.NOME}."),
                "alto": ("O som está estourando.", "Afaste um pouco o microfone ou diminua o volume de entrada "
                         f"nos ajustes de som do {plataforma.NOME}."),
            }
            titulo, texto = textos[veredito]
            c, cl = cartao("ok" if veredito == "bom" else "aviso", (16, 14, 16, 14), 12, horizontal=True)
            cl.addWidget(_icone_rotulo("visto" if veredito == "bom" else "alerta",
                                       tema.VERDE if veredito == "bom" else "#B35A00", 20), 0,
                         Qt.AlignmentFlag.AlignTop)
            col = QVBoxLayout()
            col.setSpacing(4)
            col.addWidget(rotulo(titulo, "h3"))
            if texto:
                col.addWidget(rotulo(texto, "meta", quebra=True))
            cl.addLayout(col, 1)
            lay.addWidget(c)
        self.b_salvar.setText("Salvar e fechar" if p["regras"] or p["vocabulario"] or p["comuns"] else "Fechar")
        self.pilha.setCurrentIndex(2)

    def _salvar(self):
        if not self.salvo and self.proposta is not None:
            self.salvo = True
            aceitas = [regra for regra, caixa in self.marcas if caixa.isChecked()]
            aprendido = cal.aplicar(self.cfg, self.proposta, aceitas)
            self.salvar()
            self.terminou.emit(aprendido)
        self.accept()

    # --------------------------------------------------------------- fim
    def done(self, codigo):
        global _aberta
        if self.pilha.currentIndex() == 2 and not self.salvo:  # fechou no X depois de ler: guarda o que aprendeu
            self._salvar()
            return
        self.relogio.stop()
        self.proxima_sozinho.stop()
        self.motor.entregar = self.entregar_antes
        if self.pausado_antes and not self.motor.pausado:
            self.motor.pausar(True)
        if _aberta is self:
            _aberta = None
        super().done(codigo)
