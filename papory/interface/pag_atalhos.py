"""Tela Atalhos de texto: diga uma frase curta e o Papory escreve um texto inteiro no lugar."""
from PySide6.QtWidgets import QHBoxLayout, QLineEdit, QPlainTextEdit, QVBoxLayout

from . import tema
from .widgets import botao, botao_icone, cartao, icone, limpar_layout, pagina_rolavel, rotulo

IDEIAS = ["minha assinatura", "meu endereço", "minha chave Pix", "link da agenda", "resposta de boas-vindas"]


def _grupos(atalhos):
    """Frases que escrevem o mesmo texto viram um cartão só ("meu e-mail" e "meu email")."""
    grupos = {}
    for frase, texto in atalhos.items():
        grupos.setdefault(texto, []).append(frase)
    return [(frases, texto) for texto, frases in grupos.items()]


class PaginaAtalhos:
    def __init__(self, janela):
        self.janela = janela
        self.editando = None  # frases do cartão em edição
        self.area, v = pagina_rolavel()

        cab = QVBoxLayout()
        cab.setSpacing(8)
        cab.addWidget(rotulo("Atalhos de texto", "titulo"))
        cab.addWidget(rotulo("Diga a frase e o Papory escreve o texto inteiro no lugar dela, mesmo no meio do "
                             "ditado: “me manda no meu e-mail” sai com o endereço completo.", "sub", quebra=True))
        v.addLayout(cab)

        form, fl = cartao(margens=(22, 22, 22, 22), espaco=16)
        self.titulo_form = rotulo("Novo atalho", "h3")
        fl.addWidget(self.titulo_form)
        campos = QHBoxLayout()
        campos.setSpacing(14)
        c1, c2 = QVBoxLayout(), QVBoxLayout()
        c1.setSpacing(6)
        c2.setSpacing(6)
        c1.addWidget(rotulo("Quando eu disser", "rotulo"))
        self.frase = QLineEdit()
        self.frase.setPlaceholderText("Ex.: minha assinatura")
        self.frase.setAccessibleName("Quando eu disser")
        c1.addWidget(self.frase)
        c1.addStretch(1)
        c2.addWidget(rotulo("Escrever isto", "rotulo"))
        self.texto = QPlainTextEdit()
        self.texto.setPlaceholderText("O texto completo que vai aparecer")
        self.texto.setAccessibleName("Escrever isto")
        self.texto.setFixedHeight(78)
        c2.addWidget(self.texto)
        campos.addLayout(c1, 2)
        campos.addLayout(c2, 3)
        fl.addLayout(campos)
        acoes = QHBoxLayout()
        acoes.setSpacing(10)
        self.b_salvar = botao("Adicionar atalho", "primario", "mais")
        self.b_salvar.clicked.connect(self._salvar)
        self.b_cancelar = botao("Cancelar")
        self.b_cancelar.clicked.connect(self._limpar_form)
        self.b_cancelar.hide()
        self.erro = rotulo("", "erro")
        acoes.addWidget(self.b_salvar)
        acoes.addWidget(self.b_cancelar)
        acoes.addWidget(rotulo("Maiúsculas e minúsculas não importam.", "pequeno"))
        acoes.addWidget(self.erro)
        acoes.addStretch(1)
        fl.addLayout(acoes)
        ideias = QHBoxLayout()
        ideias.setSpacing(8)
        ideias.addWidget(rotulo("Ideias:", "meta"))
        for ideia in IDEIAS:
            b = botao(ideia, "ideia")
            b.clicked.connect(lambda _=False, t=ideia: (self.frase.setText(t), self.texto.setFocus()))
            ideias.addWidget(b)
        ideias.addStretch(1)
        fl.addLayout(ideias)
        v.addWidget(form)

        seus = QVBoxLayout()
        seus.setSpacing(12)
        t = QHBoxLayout()
        t.setSpacing(10)
        t.addWidget(rotulo("Seus atalhos", "h2"))
        self.total = rotulo("", "meta")
        t.addWidget(self.total)
        t.addStretch(1)
        seus.addLayout(t)
        self.lista = QVBoxLayout()
        self.lista.setSpacing(12)
        seus.addLayout(self.lista)
        v.addLayout(seus)
        v.addStretch(1)

    def recarregar(self):
        atalhos = self.janela.cfg["atalhos_de_texto"]
        grupos = _grupos(atalhos)
        self.total.setText(f"{len(grupos)} {'atalho' if len(grupos) == 1 else 'atalhos'}")
        limpar_layout(self.lista)
        if not grupos:
            self.lista.addWidget(rotulo("Nenhum atalho ainda. Use o formulário acima.", "meta"))
        for frases, texto in grupos:
            c, lay = cartao(margens=(18, 14, 12, 14), espaco=18, horizontal=True)
            esq = QVBoxLayout()
            esq.setSpacing(6)
            esq.addWidget(rotulo("Quando disser", "rotulo"))
            principal = rotulo(f"“{frases[0]}”")
            principal.setStyleSheet("font-size: 16px; font-weight: 800;")
            esq.addWidget(principal)
            if len(frases) > 1:
                esq.addWidget(rotulo("também vale: " + ", ".join(frases[1:]), "meta", quebra=True))
            lay.addLayout(esq, 2)
            seta = rotulo("")
            seta.setPixmap(icone("seta", tema.TEXTO_3, 20).pixmap(20, 20))
            lay.addWidget(seta)
            dir_ = QVBoxLayout()
            dir_.setSpacing(6)
            dir_.addWidget(rotulo("Escreve", "rotulo"))
            dir_.addWidget(rotulo(texto, "texto_atalho", quebra=True, selecionavel=True))
            lay.addLayout(dir_, 3)
            editar = botao_icone("corrigir", f"Editar o atalho {frases[0]}")
            apagar = botao_icone("lixeira", f"Apagar o atalho {frases[0]}")
            editar.clicked.connect(lambda _=False, f=frases, t=texto: self._editar(f, t))
            apagar.clicked.connect(lambda _=False, f=frases: self._apagar(f))
            lay.addWidget(editar)
            lay.addWidget(apagar)
            self.lista.addWidget(c)

    def _editar(self, frases, texto):
        self.editando = frases
        self.titulo_form.setText("Editar atalho")
        self.frase.setText(frases[0])
        self.texto.setPlainText(texto)
        self.b_salvar.setText("Salvar alterações")
        self.b_cancelar.show()
        self.frase.setFocus()
        self.area.verticalScrollBar().setValue(0)

    def _limpar_form(self):
        self.editando = None
        self.titulo_form.setText("Novo atalho")
        self.frase.clear()
        self.texto.clear()
        self.erro.clear()
        self.b_salvar.setText("Adicionar atalho")
        self.b_cancelar.hide()

    def _salvar(self):
        frase, texto = self.frase.text().strip(), self.texto.toPlainText().strip()
        if not frase or not texto:
            self.erro.setText("Preencha a frase e o texto.")
            return
        atalhos = self.janela.cfg["atalhos_de_texto"]
        if self.editando:
            for f in self.editando:
                atalhos.pop(f, None)
            for f in self.editando[1:]:
                atalhos[f] = texto  # as outras formas de dizer continuam valendo
        atalhos[frase] = texto
        self._limpar_form()
        self.janela.salvar_config()
        self.recarregar()

    def _apagar(self, frases):
        atalhos = self.janela.cfg["atalhos_de_texto"]
        for f in frases:
            atalhos.pop(f, None)
        self.janela.salvar_config()
        self.recarregar()
