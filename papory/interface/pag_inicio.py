"""Tela Início: números do seu uso, dica e o histórico (copiar, ouvir, corrigir e ensinar)."""
from datetime import date, datetime, timedelta

from PySide6.QtCore import QSize, Qt, QTimer
from PySide6.QtWidgets import (QApplication, QCheckBox, QFrame, QHBoxLayout, QLineEdit, QPlainTextEdit, QVBoxLayout,
                               QWidget)

from .. import aprendizado, contexto, historico
from . import tema
from .widgets import (botao, botao_icone, cartao, icone, limpar_layout, linha, linha_h, pagina_rolavel, rotulo,
                      teclas)

DIAS = ["segunda-feira", "terça-feira", "quarta-feira", "quinta-feira", "sexta-feira", "sábado", "domingo"]
MESES = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto", "setembro", "outubro",
         "novembro", "dezembro"]
POR_VEZ = 30


def _numero(n):
    return f"{n:,}".replace(",", ".")


def _decimal(x, casas=1):
    return f"{x:.{casas}f}".replace(".", ",")


def _minutos(m):
    m = round(m)
    return f"{m // 60} h {m % 60:02d} min" if m >= 60 else f"{m} min"


def _duracao(s):
    s = float(s or 0)
    return f"{int(s // 60)} min {int(s % 60)} s" if s >= 60 else f"{_decimal(s)} s"


def _dia(d):
    hoje = date.today()
    if d == hoje:
        return "Hoje"
    if d == hoje - timedelta(days=1):
        return "Ontem"
    return f"{DIAS[d.weekday()]}, {d.day} de {MESES[d.month - 1]}".capitalize()


class _Tocador:
    """Um áudio por vez: tocar outro para o anterior."""
    atual = None


class ItemHistorico(QFrame):
    def __init__(self, registro, pagina):
        super().__init__()
        self.r, self.pagina = registro, pagina
        self.setProperty("papel", "cartao")
        v = QVBoxLayout(self)
        v.setContentsMargins(18, 14, 14, 14)
        v.setSpacing(10)

        topo = QHBoxLayout()
        topo.setSpacing(16)
        col = QVBoxLayout()
        col.setSpacing(6)
        meta = [rotulo(registro["_quando"].strftime("%H:%M"), "rotulo"), rotulo("·", "meta"),
                rotulo(contexto.nome_do_app(registro.get("app")), "meta"), rotulo("·", "meta"),
                rotulo(_duracao(registro.get("duracao_s")), "meta")]
        onde = registro.get("polimento")
        if onde in ("local", "nuvem"):
            meta.append(rotulo(onde, "tag_local" if onde == "local" else "tag_nuvem"))
        if registro.get("correcao"):
            meta.append(rotulo("corrigido", "tag_neutra"))
        col.addWidget(linha_h(*meta, espaco=8))
        self.texto = rotulo(registro["final"], "texto", quebra=True, selecionavel=True)
        col.addWidget(self.texto)
        topo.addLayout(col, 1)

        botoes = QHBoxLayout()
        botoes.setSpacing(2)
        self.b_copiar = botao_icone("copiar", "Copiar")
        self.b_copiar.clicked.connect(self._copiar)
        self.b_ouvir = botao_icone("ouvir", "Ouvir o áudio")
        self.b_ouvir.clicked.connect(self._ouvir)
        self.b_ouvir.setEnabled(registro.get("_audio") is not None)
        self.b_corrigir = botao_icone("corrigir", "Corrigir")
        self.b_corrigir.setCheckable(True)
        self.b_corrigir.toggled.connect(self._abrir_editor)
        for b in (self.b_copiar, self.b_ouvir, self.b_corrigir):
            botoes.addWidget(b)
        topo.addLayout(botoes)
        topo.setAlignment(botoes, Qt.AlignmentFlag.AlignTop)
        v.addLayout(topo)

        self.editor = None
        self.aviso = rotulo("", "verde", quebra=True)
        self.aviso.hide()
        v.addWidget(self.aviso)

    # --------------------------------------------------------- ações
    def _copiar(self):
        QApplication.clipboard().setText(self.r["final"])
        self.b_copiar.setIcon(icone("visto", tema.VERDE, 19, 2.2))
        self.b_copiar.setToolTip("Copiado")
        QTimer.singleShot(1400, lambda: (self.b_copiar.setIcon(icone("copiar", "#3D4935", 19)),
                                         self.b_copiar.setToolTip("Copiar")))

    def _ouvir(self):
        import sounddevice as sd
        import soundfile as sf
        if _Tocador.atual is self:
            sd.stop()
            self._fim_audio()
            return
        if _Tocador.atual is not None:
            _Tocador.atual._fim_audio()
        dados, taxa = sf.read(str(self.r["_audio"]), dtype="float32")
        sd.play(dados, taxa)
        _Tocador.atual = self
        self.b_ouvir.setIcon(icone("parar", "#3D4935", 19))
        self.b_ouvir.setToolTip("Parar")
        QTimer.singleShot(int(len(dados) / taxa * 1000) + 300, self._fim_audio)

    def _fim_audio(self):
        if _Tocador.atual is self:
            _Tocador.atual = None
        self.b_ouvir.setIcon(icone("ouvir", "#3D4935", 19))
        self.b_ouvir.setToolTip("Ouvir o áudio")

    def _abrir_editor(self, abrir):
        self.setProperty("papel", "cartao_destaque" if abrir else "cartao")
        self.style().unpolish(self)
        self.style().polish(self)
        if not abrir:
            if self.editor:
                self.editor.hide()
            return
        if self.editor is None:
            self._criar_editor()
        self.campo.setPlainText(self.r["final"])
        self.editor.show()
        self.campo.setFocus()

    def _criar_editor(self):
        self.editor = QWidget()
        v = QVBoxLayout(self.editor)
        v.setContentsMargins(0, 4, 0, 4)
        v.setSpacing(12)
        v.addWidget(linha())
        v.addWidget(rotulo("Corrigir este ditado", "h3"))
        self.campo = QPlainTextEdit()
        self.campo.setMinimumHeight(84)
        self.campo.setMaximumHeight(160)
        self.campo.setAccessibleName("Texto corrigido")
        v.addWidget(self.campo)
        self.caixa_trocas = QVBoxLayout()
        self.caixa_trocas.setSpacing(10)
        v.addLayout(self.caixa_trocas)
        salvar, cancelar = botao("Salvar correção", "primario"), botao("Cancelar")
        acoes = linha_h(salvar, cancelar, 6,
                        linha_h(_icone_rotulo("cadeado"), rotulo("Fica só no seu computador.", "pequeno"), espaco=6))
        salvar.clicked.connect(self._salvar)
        cancelar.clicked.connect(lambda: self.b_corrigir.setChecked(False))
        v.addWidget(acoes)
        self.layout().insertWidget(1, self.editor)
        self.atraso = QTimer(self, singleShot=True, interval=300, timeout=self._mostrar_trocas)
        self.campo.textChanged.connect(self.atraso.start)
        self.marcas = []

    def _mostrar_trocas(self):
        limpar_layout(self.caixa_trocas)
        self.marcas = []
        trocas = aprendizado.diferencas(self.r["final"], self.campo.toPlainText())
        if not trocas:
            return
        for de, para in trocas[:4]:
            seta = _icone_rotulo("seta", tema.TEXTO_2)
            self.caixa_trocas.addWidget(linha_h(rotulo(de, "troca_de"), seta, rotulo(para, "troca_para"), espaco=10))
        vistos = []
        for _, para in trocas[:4]:
            if para.lower() in vistos or aprendizado._no_vocabulario(self.pagina.janela.cfg, para):
                continue
            vistos.append(para.lower())
            c = QCheckBox(f"Guardar “{para}” no vocabulário. Assim ele acerta da próxima vez.")
            c.setChecked(para[:1].isupper())  # nome próprio costuma ser o que vale guardar
            c.setProperty("palavra", para)
            self.marcas.append(c)
            self.caixa_trocas.addWidget(c)
        if self.marcas:
            self.caixa_trocas.addWidget(rotulo("Uma palavra corrigida duas vezes entra sozinha, mesmo sem marcar.",
                                               "pequeno"))

    def _salvar(self):
        novo = self.campo.toPlainText().strip()
        antigo = self.r["final"]
        if not novo or novo == antigo:
            self.b_corrigir.setChecked(False)
            return
        cfg = self.pagina.janela.cfg
        trocas = aprendizado.diferencas(antigo, novo)
        historico.corrigir(self.r["_arquivo"], novo, trocas)
        guardar = {c.property("palavra") for c in self.marcas if c.isChecked()}
        aprendeu = aprendizado.registrar(cfg, trocas, guardar=guardar)
        self.pagina.janela.salvar_config()
        self.r["final"] = novo
        self.r["correcao"] = {"trocas": trocas}
        self.texto.setText(novo)
        self.b_corrigir.setChecked(False)
        partes = ["Correção salva."]
        if aprendeu["vocabulario"]:
            partes.append("No vocabulário agora: " + ", ".join(aprendeu["vocabulario"]) + ".")
        if aprendeu["regras"]:
            partes.append("Troca automática nova: " + ", ".join(f"{de} → {para}" for de, para in aprendeu["regras"]) + ".")
        self.aviso.setText(" ".join(partes))
        self.aviso.show()
        QTimer.singleShot(6000, self.aviso.hide)
        self.pagina.janela.vocabulario_mudou()


def _icone_rotulo(nome, cor=tema.TEXTO_3):
    r = rotulo("")
    r.setPixmap(icone(nome, cor, 16).pixmap(QSize(16, 16)))
    return r


class PaginaInicio:
    def __init__(self, janela):
        self.janela = janela
        self.area, v = pagina_rolavel()
        self.limite = POR_VEZ

        cab = QVBoxLayout()
        cab.setSpacing(8)
        self.saudacao = rotulo("", "titulo")
        cab.addWidget(self.saudacao)
        self.linha_atalho = QHBoxLayout()
        self.linha_atalho.setSpacing(6)
        cab.addLayout(self.linha_atalho)
        v.addLayout(cab)

        numeros = QHBoxLayout()
        numeros.setSpacing(16)
        self.n_palavras = self._numero(numeros, "Palavras ditadas")
        self.n_ditados = self._numero(numeros, "Ditados")
        self.n_poupado = self._numero(numeros, "Tempo poupado", verde=True)
        v.addLayout(numeros)

        self.dica, dl = cartao("dica", (18, 12, 12, 12), 14, horizontal=True)
        dl.addWidget(_icone_rotulo("brilho", "#B35A00"))
        self.dica_texto = rotulo("", "laranja", quebra=True)
        dl.addWidget(self.dica_texto, 1)
        ver = botao("Ver atalhos de texto", "link")
        ver.clicked.connect(lambda: self.janela.ir("atalhos"))
        dl.addWidget(ver)
        fechar = botao_icone("fechar", "Fechar dica", tema.LARANJA_TEXTO)
        fechar.clicked.connect(self._fechar_dica)
        dl.addWidget(fechar)
        v.addWidget(self.dica)

        hist = QVBoxLayout()
        hist.setSpacing(14)
        topo = QHBoxLayout()
        topo.addWidget(rotulo("Histórico", "h2"))
        topo.addStretch(1)
        self.busca = QLineEdit()
        self.busca.setPlaceholderText("Buscar no que você ditou")
        self.busca.setAccessibleName("Buscar no histórico")
        self.busca.addAction(icone("buscar", tema.TEXTO_3, 18), QLineEdit.ActionPosition.LeadingPosition)
        self.busca.setFixedWidth(340)
        self.atraso_busca = QTimer(singleShot=True, interval=250, timeout=self.recarregar_lista)
        self.busca.textChanged.connect(self.atraso_busca.start)
        topo.addWidget(self.busca)
        hist.addLayout(topo)
        self.lista = QVBoxLayout()
        self.lista.setSpacing(12)
        hist.addLayout(self.lista)
        self.mais = botao("Mostrar mais")
        self.mais.clicked.connect(self._mostrar_mais)
        hist.addWidget(self.mais, 0, Qt.AlignmentFlag.AlignHCenter)
        v.addLayout(hist)
        v.addStretch(1)

    def _numero(self, linha_layout, titulo, verde=False):
        c, lay = cartao(margens=(22, 20, 22, 20), espaco=8)
        lay.addWidget(rotulo(titulo, "meta"))
        n = rotulo("—", "numero_verde" if verde else "numero")
        legenda = rotulo("", "pequeno", quebra=True)
        lay.addWidget(n)
        lay.addWidget(legenda)
        linha_layout.addWidget(c, 1)
        return n, legenda

    def _fechar_dica(self):
        self.janela.cfg["interface"]["dicas_fechadas"].append("atalhos")
        self.janela.salvar_config()
        self.dica.hide()

    def _mostrar_mais(self):
        self.limite += POR_VEZ
        self.recarregar_lista()

    def recarregar(self):
        cfg = self.janela.cfg
        h = datetime.now().hour
        self.saudacao.setText("Bom dia" if 5 <= h < 12 else "Boa tarde" if 12 <= h < 18 else "Boa noite")
        limpar_layout(self.linha_atalho)
        self.linha_atalho.addWidget(rotulo("Segure", "sub"))
        self.linha_atalho.addWidget(teclas(cfg["atalho"]))
        self.linha_atalho.addWidget(rotulo(", fale e solte. O texto aparece onde o cursor está.", "sub"))
        self.linha_atalho.addStretch(1)

        e = historico.estatisticas()
        self.n_palavras[0].setText(_numero(e["palavras"]))
        self.n_palavras[1].setText(f"desde {e['desde'].day} de {MESES[e['desde'].month - 1]}" if e["desde"]
                                   else "comece segurando o atalho")
        self.n_ditados[0].setText(_numero(e["ditados"]))
        self.n_ditados[1].setText(f"{_decimal(e['falando_min'])} min falando")
        self.n_poupado[0].setText(_minutos(e["poupado_min"]))  # sem "≈": as fontes embutidas não têm o símbolo
        self.n_poupado[1].setText("aproximado, contra digitar a 40 palavras por minuto")

        atalhos = cfg["atalhos_de_texto"]
        if "atalhos" in cfg["interface"]["dicas_fechadas"]:
            self.dica.hide()
        else:
            if atalhos:
                frase = next(iter(atalhos))
                self.dica_texto.setText(f"Diga “{frase}” e o Papory escreve o texto inteiro no lugar.")
            else:
                self.dica_texto.setText("Crie atalhos de texto: diga uma frase curta e o Papory escreve um texto "
                                        "inteiro, como seu e-mail ou sua assinatura.")
            self.dica.show()
        self.recarregar_lista()

    def recarregar_lista(self):
        limpar_layout(self.lista)
        busca = self.busca.text()
        itens = historico.listar(limite=self.limite + 1, busca=busca)
        self.mais.setVisible(len(itens) > self.limite)
        itens = itens[:self.limite]
        if not itens:
            c, lay = cartao()
            lay.addWidget(rotulo("Nada encontrado para essa busca." if busca.strip() else
                                 "Nenhum ditado ainda. Clique num campo de texto em qualquer programa, segure o "
                                 "atalho, fale e solte.", "sub", quebra=True))
            self.lista.addWidget(c)
            return
        dia = None
        for r in itens:
            d = r["_quando"].date()
            if d != dia:
                dia = d
                self.lista.addWidget(rotulo(_dia(d), "rotulo"))
            self.lista.addWidget(ItemHistorico(r, self))
