"""Tela Vocabulário: sugestões aprendidas com as correções, suas palavras e as trocas automáticas."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QComboBox, QDialog, QFrame, QGridLayout, QHBoxLayout, QLineEdit, QToolButton,
                               QVBoxLayout, QWidget)

from .. import aprendizado, contexto
from . import tema
from .widgets import (FluxoLayout, botao, botao_icone, cartao, icone, limpar_layout, pagina_rolavel, rotulo)

APPS_CODIGO = ["code", "windowsterminal", "cursor", "claude"]


def _apps(lista):
    if not lista:
        return "Todos os apps"
    return ", ".join(contexto.nome_do_app(a) for a in lista)


class Chip(QFrame):
    def __init__(self, texto, ao_remover):
        super().__init__()
        self.setProperty("papel", "chip")
        lay = QHBoxLayout(self)
        lay.setContentsMargins(14, 0, 2, 0)
        lay.setSpacing(2)
        r = rotulo(texto)
        r.setStyleSheet("font-size: 14px; font-weight: 600;")
        lay.addWidget(r)
        x = QToolButton()
        x.setProperty("papel", "icone")
        x.setIcon(icone("fechar", tema.TEXTO_3, 14, 2))
        x.setFixedSize(36, 38)
        x.setToolTip(f"Remover {texto}")
        x.setAccessibleName(f"Remover {texto}")
        x.setCursor(Qt.CursorShape.PointingHandCursor)
        x.clicked.connect(ao_remover)
        lay.addWidget(x)
        self.setFixedHeight(42)


class DialogoTroca(QDialog):
    def __init__(self, pai):
        super().__init__(pai)
        self.setWindowTitle("Nova troca automática")
        self.setMinimumWidth(460)
        self.setStyleSheet(f"QDialog {{ background: {tema.BRANCO}; }}")
        v = QVBoxLayout(self)
        v.setContentsMargins(24, 22, 24, 22)
        v.setSpacing(12)
        v.addWidget(rotulo("Nova troca automática", "h3"))
        v.addWidget(rotulo("Quando o Papory escrever a palavra da esquerda, ele troca pela da direita.", "meta",
                           quebra=True))
        self.de, self.para = QLineEdit(), QLineEdit()
        self.de.setPlaceholderText("Ex.: Cláudio")
        self.para.setPlaceholderText("Ex.: Claude")
        for texto, campo in (("Quando sair", self.de), ("Vira", self.para)):
            v.addWidget(rotulo(texto, "rotulo"))
            v.addWidget(campo)
        v.addWidget(rotulo("Em quais apps", "rotulo"))
        self.apps = QComboBox()
        self.apps.addItem("Em todos os apps", [])
        self.apps.addItem(f"Só em apps de código ({_apps(APPS_CODIGO)})", APPS_CODIGO)
        v.addWidget(self.apps)
        linha = QHBoxLayout()
        linha.addStretch(1)
        cancelar, ok = botao("Cancelar"), botao("Adicionar troca", "primario")
        cancelar.clicked.connect(self.reject)
        ok.clicked.connect(self._ok)
        linha.addWidget(cancelar)
        linha.addWidget(ok)
        v.addSpacing(6)
        v.addLayout(linha)

    def _ok(self):
        if self.de.text().strip() and self.para.text().strip():
            self.accept()

    def valor(self):
        troca = {"de": self.de.text().strip(), "para": self.para.text().strip()}
        if self.apps.currentData():
            troca["apps"] = self.apps.currentData()
        return troca


class PaginaVocabulario:
    def __init__(self, janela):
        self.janela = janela
        self.area, v = pagina_rolavel()
        v.setSpacing(32)

        cab = QVBoxLayout()
        cab.setSpacing(8)
        cab.addWidget(rotulo("Vocabulário", "titulo"))
        cab.addWidget(rotulo("Nomes e termos que você usa. Quando o Papory ouve algo parecido, ele dá preferência a "
                             "estas palavras.", "sub", quebra=True))
        v.addLayout(cab)

        nova = QVBoxLayout()
        nova.setSpacing(6)
        nova.addWidget(rotulo("Nova palavra ou nome", "rotulo"))
        linha = QHBoxLayout()
        linha.setSpacing(10)
        self.campo = QLineEdit()
        self.campo.setPlaceholderText("Ex.: o nome de um cliente, uma sigla, um produto")
        self.campo.setAccessibleName("Nova palavra ou nome")
        self.campo.returnPressed.connect(self._adicionar)
        adicionar = botao("Adicionar", "primario", "mais")
        adicionar.clicked.connect(self._adicionar)
        linha.addWidget(self.campo, 1)
        linha.addWidget(adicionar)
        nova.addLayout(linha)
        v.addLayout(nova)

        sug = QVBoxLayout()
        sug.setSpacing(12)
        t = QHBoxLayout()
        t.setSpacing(10)
        ic = rotulo("")
        ic.setPixmap(icone("brilho", "#B35A00", 20).pixmap(20, 20))
        t.addWidget(ic)
        t.addWidget(rotulo("Aprendidas com as suas correções", "h2"))
        t.addStretch(1)
        sug.addLayout(t)
        self.sugestoes = QVBoxLayout()
        self.sugestoes.setSpacing(10)
        sug.addLayout(self.sugestoes)
        v.addLayout(sug)

        pal = QVBoxLayout()
        pal.setSpacing(14)
        t = QHBoxLayout()
        t.setSpacing(10)
        t.addWidget(rotulo("Suas palavras", "h2"))
        self.total = rotulo("", "meta")
        t.addWidget(self.total)
        t.addStretch(1)
        pal.addLayout(t)
        self.caixa_chips = QWidget()
        self.chips = FluxoLayout(8)
        self.caixa_chips.setLayout(self.chips)
        pal.addWidget(self.caixa_chips)
        v.addLayout(pal)

        tro = QVBoxLayout()
        tro.setSpacing(14)
        t = QHBoxLayout()
        col = QVBoxLayout()
        col.setSpacing(6)
        col.addWidget(rotulo("Trocas automáticas", "h2"))
        col.addWidget(rotulo("Se o Papory escrever a palavra da esquerda, ele troca pela da direita. Só nos apps "
                             "marcados.", "meta", quebra=True))
        t.addLayout(col, 1)
        nova_troca = botao("Nova troca", "secundario", "mais")
        nova_troca.clicked.connect(self._nova_troca)
        t.addWidget(nova_troca, 0, Qt.AlignmentFlag.AlignBottom)
        tro.addLayout(t)
        self.cartao_trocas, cl = cartao(margens=(0, 4, 0, 4), espaco=0)
        self.grade = QGridLayout()
        self.grade.setContentsMargins(18, 6, 8, 6)
        self.grade.setHorizontalSpacing(16)
        self.grade.setVerticalSpacing(4)
        cl.addLayout(self.grade)
        tro.addWidget(self.cartao_trocas)
        v.addLayout(tro)
        v.addStretch(1)

    # -------------------------------------------------------------- dados
    def recarregar(self):
        cfg = self.janela.cfg
        limpar_layout(self.sugestoes)
        sugestoes = aprendizado.sugestoes(cfg)
        if not sugestoes:
            self.sugestoes.addWidget(rotulo("Nenhuma sugestão agora. Quando você corrigir um ditado no Início, a "
                                            "palavra aparece aqui.", "meta", quebra=True))
        for s in sugestoes[:6]:
            c, lay = cartao("cartao_laranja", margens=(18, 14, 18, 14), horizontal=True)
            col = QVBoxLayout()
            col.setSpacing(4)
            nome = rotulo(s["para"])
            nome.setStyleSheet("font-size: 18px; font-weight: 800;")
            vezes = "uma vez" if s["vezes"] == 1 else f"{s['vezes']} vezes"
            col.addWidget(nome)
            col.addWidget(rotulo(f"Você corrigiu “{s['de']}” para “{s['para']}” {vezes}. Na segunda correção igual "
                                 "ela entra sozinha.", "meta", quebra=True))
            lay.addLayout(col, 1)
            sim, nao = botao("Adicionar agora", "primario"), botao("Ignorar")
            sim.clicked.connect(lambda _=False, p=s["para"]: self._adicionar(p))
            nao.clicked.connect(lambda _=False, p=s["para"]: self._ignorar(p))
            lay.addWidget(sim)
            lay.addWidget(nao)
            self.sugestoes.addWidget(c)

        limpar_layout(self.chips)
        for palavra in cfg["vocabulario"]:
            self.chips.addWidget(Chip(palavra, lambda _=False, p=palavra: self._remover(p)))
        n = len(cfg["vocabulario"])
        self.total.setText(f"{n} {'palavra' if n == 1 else 'palavras'}")
        self.caixa_chips.updateGeometry()

        limpar_layout(self.grade)
        for col, texto in enumerate(("Quando sair", "Vira", "Em quais apps")):
            self.grade.addWidget(rotulo(texto, "rotulo"), 0, col)
        self.grade.setColumnStretch(0, 3)
        self.grade.setColumnStretch(1, 3)
        self.grade.setColumnStretch(2, 3)
        for i, s in enumerate(cfg["substituicoes"], start=1):
            de = s.get("descricao") or s.get("de") or "regra avançada"
            para = s.get("descricao_para") or s.get("para", "")
            esq = QVBoxLayout()
            esq.setSpacing(2)
            r = rotulo(de, quebra=True)
            r.setStyleSheet("font-size: 14px; font-weight: 600;")
            esq.addWidget(r)
            if s.get("nota"):
                esq.addWidget(rotulo(s["nota"], "pequeno", quebra=True))
            if s.get("aprendida"):
                esq.addWidget(rotulo("aprendida com suas correções", "pequeno"))
            caixa = QWidget()
            caixa.setLayout(esq)
            vira = rotulo(para, quebra=True)
            vira.setStyleSheet("font-size: 14px; font-weight: 700; color: #1E5C12;")
            apagar = botao_icone("lixeira", f"Apagar a troca {de}", tema.TEXTO_3)
            apagar.clicked.connect(lambda _=False, alvo=s: self._apagar_troca(alvo))
            self.grade.addWidget(caixa, i, 0)
            self.grade.addWidget(vira, i, 1)
            self.grade.addWidget(rotulo(_apps(s.get("apps")), "meta", quebra=True), i, 2)
            self.grade.addWidget(apagar, i, 3)
        self.cartao_trocas.setVisible(bool(cfg["substituicoes"]))

    def _salvar(self):
        self.janela.salvar_config()
        self.recarregar()

    def _adicionar(self, palavra=None):
        cfg = self.janela.cfg
        palavra = (palavra if isinstance(palavra, str) else self.campo.text()).strip()
        if not palavra:
            return
        if not aprendizado._no_vocabulario(cfg, palavra):
            cfg["vocabulario"].insert(0, palavra)  # no lugar: o polimento usa a mesma lista
        self.campo.clear()
        self._salvar()

    def _remover(self, palavra):
        cfg = self.janela.cfg
        if palavra in cfg["vocabulario"]:
            cfg["vocabulario"].remove(palavra)
        self._salvar()

    def _ignorar(self, palavra):
        aprendizado.ignorar(self.janela.cfg, palavra)
        self._salvar()

    def _nova_troca(self):
        d = DialogoTroca(self.area)
        if d.exec():
            self.janela.cfg["substituicoes"].append(d.valor())
            self._salvar()

    def _apagar_troca(self, alvo):
        lista = self.janela.cfg["substituicoes"]
        if alvo in lista:
            lista.remove(alvo)
        self._salvar()
