"""Peças reaproveitadas pelas telas: ícones, interruptor, teclas, chips em fluxo, medidor de volume."""
from PySide6.QtCore import QByteArray, QPoint, QRect, QRectF, QSize, Qt, Signal
from PySide6.QtGui import QColor, QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import (QAbstractButton, QFrame, QHBoxLayout, QLabel, QLayout, QPushButton, QScrollArea,
                               QSizePolicy, QToolButton, QVBoxLayout, QWidget)

from .. import plataforma
from . import tema

# traços dos ícones (24×24, linha), os mesmos do esboço
ICONES = {
    "inicio": '<path d="M3 10.5 12 3l9 7.5"/><path d="M5 9.5V21h14V9.5"/><path d="M9.5 21v-6h5v6"/>',
    "vocabulario": '<path d="M4 19.5V5a2 2 0 0 1 2-2h14v16H6a2 2 0 0 0-2 2z"/><path d="M8 7h8"/><path d="M8 11h5"/>',
    "atalhos": '<path d="M4 7V5h12v2"/><path d="M10 5v14"/><path d="M7 19h6"/>'
               '<path d="M18 11l1 2 2 1-2 1-1 2-1-2-2-1 2-1z"/>',
    "config": '<path d="M4 6h10"/><path d="M18 6h2"/><path d="M4 12h4"/><path d="M12 12h8"/><path d="M4 18h12"/>'
              '<circle cx="16" cy="6" r="2"/><circle cx="10" cy="12" r="2"/><circle cx="18" cy="18" r="2"/>',
    "copiar": '<rect x="8" y="8" width="12" height="12" rx="2"/>'
              '<path d="M16 8V6a2 2 0 0 0-2-2H6a2 2 0 0 0-2 2v8a2 2 0 0 0 2 2h2"/>',
    "ouvir": '<path d="M8 5v14l11-7z"/>',
    "parar": '<rect x="6" y="6" width="12" height="12" rx="2"/>',
    "corrigir": '<path d="M4 20h4L19 9a2.8 2.8 0 0 0-4-4L4 16z"/><path d="M13.5 6.5l4 4"/>',
    "buscar": '<circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/>',
    "visto": '<path d="m5 12.5 4.5 4.5L19 7.5"/>',
    "fechar": '<path d="M6 6l12 12M18 6 6 18"/>',
    "mais": '<path d="M12 5v14M5 12h14"/>',
    "seta": '<path d="M5 12h14M13 6l6 6-6 6"/>',
    "brilho": '<path d="M12 3l1.8 4.7L18.5 9.5l-4.7 1.8L12 16l-1.8-4.7L5.5 9.5l4.7-1.8z"/>',
    "cadeado": '<rect x="5" y="11" width="14" height="10" rx="2"/><path d="M8 11V7a4 4 0 0 1 8 0v4"/>',
    "lixeira": '<path d="M4 7h16M9 7V4h6v3M6 7l1 13h10l1-13"/>',
    "chip": '<rect x="6" y="6" width="12" height="12" rx="2"/><path d="M10 10h4v4h-4z"/>'
            '<path d="M9 2v4M15 2v4M9 18v4M15 18v4M2 9h4M2 15h4M18 9h4M18 15h4"/>',
    "nuvem": '<path d="M7 18h10a4 4 0 0 0 .5-8 6 6 0 0 0-11.5 1.5A3.3 3.3 0 0 0 7 18z"/>',
    "microfone": '<rect x="9" y="3" width="6" height="11" rx="3"/><path d="M5 11a7 7 0 0 0 14 0"/><path d="M12 18v3"/>',
    "microfone_mudo": '<rect x="9" y="3" width="6" height="11" rx="3"/><path d="M5 11a7 7 0 0 0 14 0"/>'
                      '<path d="M12 18v3"/><path d="M4 4l16 16"/>',
    "alerta": '<path d="M12 3 2 20h20z"/><path d="M12 10v4M12 17h.01"/>',
}


def icone(nome, cor=tema.TEXTO, tamanho=20, espessura=1.8):
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="{cor}" '
           f'stroke-width="{espessura}" stroke-linecap="round" stroke-linejoin="round">{ICONES[nome]}</svg>')
    render = QSvgRenderer(QByteArray(svg.encode()))
    escala = 3  # desenha maior para ficar nítido em tela com zoom
    pm = QPixmap(tamanho * escala, tamanho * escala)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    render.render(p)
    p.end()
    pm.setDevicePixelRatio(escala)
    return QIcon(pm)


def rotulo(texto, papel=None, quebra=False, selecionavel=False):
    r = QLabel(texto)
    if papel:
        r.setProperty("papel", papel)
    if quebra:
        r.setWordWrap(True)
    if selecionavel:
        r.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
    return r


def botao(texto, papel="secundario", nome_icone=None, cor_icone=None):
    b = QPushButton(texto)
    b.setProperty("papel", papel)
    b.setCursor(Qt.CursorShape.PointingHandCursor)
    if nome_icone:
        b.setIcon(icone(nome_icone, cor_icone or ("#FFFFFF" if papel == "primario" else tema.TEXTO), 18, 2))
        b.setIconSize(QSize(18, 18))
    return b


def botao_icone(nome, dica, cor="#3D4935"):
    b = QToolButton()
    b.setProperty("papel", "icone")
    b.setIcon(icone(nome, cor, 19))
    b.setIconSize(QSize(19, 19))
    b.setToolTip(dica)
    b.setAccessibleName(dica)
    b.setCursor(Qt.CursorShape.PointingHandCursor)
    b.setFixedSize(42, 42)
    return b


def cartao(papel="cartao", margens=(22, 20, 22, 20), espaco=14, horizontal=False):
    c = QFrame()
    c.setProperty("papel", papel)
    lay = QHBoxLayout(c) if horizontal else QVBoxLayout(c)
    lay.setContentsMargins(*margens)
    lay.setSpacing(espaco)
    return c, lay


def linha():
    f = QFrame()
    f.setProperty("papel", "linha")
    return f


def linha_h(*itens, espaco=10, esticar_fim=True):
    w = QWidget()
    lay = QHBoxLayout(w)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.setSpacing(espaco)
    for i in itens:
        if isinstance(i, int):
            lay.addSpacing(i)
        elif i is None:
            lay.addStretch(1)
        else:
            lay.addWidget(i)
    if esticar_fim:
        lay.addStretch(1)
    return w


def teclas(nomes, grande=False):
    """Linha com as teclas do atalho: [Ctrl] + [Win]."""
    w = QWidget()
    lay = QHBoxLayout(w)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.setSpacing(6)
    for i, n in enumerate(nomes):
        if i:
            lay.addWidget(rotulo("+", "meta"))
        lay.addWidget(rotulo(nome_tecla(n), "tecla_grande" if grande else "tecla"))
    return w


def nome_tecla(n):
    return plataforma.TECLAS.get(n, n.upper())


def pagina_rolavel(largura_max=960):
    """Página com rolagem e conteúdo centralizado até largura_max. Devolve (scroll, layout_do_conteudo)."""
    area = QScrollArea()
    area.setWidgetResizable(True)
    area.setFrameShape(QFrame.Shape.NoFrame)
    area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    externo = QWidget()
    externo.setObjectName("pagina")
    h = QHBoxLayout(externo)
    h.setContentsMargins(40, 36, 40, 56)
    conteudo = QWidget()
    conteudo.setMaximumWidth(largura_max)
    v = QVBoxLayout(conteudo)
    v.setContentsMargins(0, 0, 0, 0)
    v.setSpacing(28)
    h.addStretch(1)
    h.addWidget(conteudo, 100)
    h.addStretch(1)
    area.setWidget(externo)
    return area, v


class Interruptor(QAbstractButton):
    """Chave liga/desliga (46×26), verde quando ligada."""

    def __init__(self, ligado=False, nome=""):
        super().__init__()
        self.setCheckable(True)
        self.setChecked(ligado)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(50, 30)
        self.setAccessibleName(nome)

    def sizeHint(self):
        return QSize(50, 30)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        trilho = QRectF(2, 2, 46, 26)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(tema.VERDE if self.isChecked() else "#8A9580"))
        p.drawRoundedRect(trilho, 13, 13)
        x = 25 if self.isChecked() else 5
        p.setBrush(QColor("#FFFFFF"))
        p.drawEllipse(QRectF(x, 5, 20, 20))
        if self.hasFocus():
            p.setPen(QColor(tema.VERDE_PAPAGAIO))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRoundedRect(QRectF(0.5, 0.5, 49, 29), 15, 15)


class Medidor(QWidget):
    """Volume do microfone em segmentos (verde até o meio, verde-claro depois)."""

    def __init__(self, segmentos=14):
        super().__init__()
        self.segmentos, self.valor = segmentos, 0.0
        self.setFixedHeight(14)
        self.setMinimumWidth(120)

    def definir(self, nivel_rms):
        self.valor = min(1.0, (max(0.0, nivel_rms) / 0.12) ** 0.5)
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(Qt.PenStyle.NoPen)
        n, esp = self.segmentos, 4
        larg = (self.width() - esp * (n - 1)) / n
        acesos = round(self.valor * n)
        for i in range(n):
            if i < acesos:
                cor = tema.VERDE_VIVO if i < n * 0.6 else tema.VERDE_PAPAGAIO
            else:
                cor = "#DCE4D2"
            p.setBrush(QColor(cor))
            p.drawRoundedRect(QRectF(i * (larg + esp), 0, larg, 14), 3, 3)


class FluxoLayout(QLayout):
    """Itens lado a lado que descem para a linha de baixo quando não cabem (chips de palavras)."""

    def __init__(self, espaco=8):
        super().__init__()
        self.itens, self.espaco = [], espaco
        self.setContentsMargins(0, 0, 0, 0)

    def addItem(self, item):
        self.itens.append(item)

    def count(self):
        return len(self.itens)

    def itemAt(self, i):
        return self.itens[i] if 0 <= i < len(self.itens) else None

    def takeAt(self, i):
        return self.itens.pop(i) if 0 <= i < len(self.itens) else None

    def expandingDirections(self):
        return Qt.Orientation(0)

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, largura):
        return self._arrumar(QRect(0, 0, largura, 0), so_medir=True)

    def setGeometry(self, rect):
        super().setGeometry(rect)
        self._arrumar(rect, so_medir=False)

    def sizeHint(self):
        return self.minimumSize()

    def minimumSize(self):
        s = QSize()
        for it in self.itens:
            s = s.expandedTo(it.minimumSize())
        return s

    def _arrumar(self, rect, so_medir):
        x, y, altura_linha = rect.x(), rect.y(), 0
        for it in self.itens:
            dica = it.sizeHint()
            if x + dica.width() > rect.right() + 1 and altura_linha > 0:
                x, y = rect.x(), y + altura_linha + self.espaco
                altura_linha = 0
            if not so_medir:
                it.setGeometry(QRect(QPoint(x, y), dica))
            x += dica.width() + self.espaco
            altura_linha = max(altura_linha, dica.height())
        return y + altura_linha - rect.y()


def limpar_layout(lay):
    while lay.count():
        it = lay.takeAt(0)
        w = it.widget()
        if w is not None:
            w.setParent(None)
            w.deleteLater()
        elif it.layout() is not None:
            limpar_layout(it.layout())


def politica_expandir(w):
    w.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
    return w


class Sinal(QWidget):
    """Só para carregar um sinal sem widget visível."""
    disparou = Signal(object)
