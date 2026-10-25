"""Pílula de ditado: aparece no rodapé da tela enquanto você fala e some sozinha depois.

Ela NUNCA pode roubar o foco: o motor guarda qual janela estava na frente quando você apertou o atalho e cola
lá. Por isso a janela é "ferramenta, sem foco" para o Qt e, no Windows, WS_EX_NOACTIVATE.
"""
import math
import time
from collections import deque

from PySide6.QtCore import QRect, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QCursor, QFont, QFontMetrics, QGuiApplication, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QWidget

from .. import contexto, plataforma
from . import tema
from .widgets import icone

MARGEM = 14          # espaço em volta da pílula para a sombra
ALTURA = 48

# estado: (ícone, cor do círculo, cor do ícone, borda, quanto tempo fica na tela em ms)
MENSAGENS = {
    "colado": ("visto", tema.VERDE_VIVO, "#FFFFFF", None, 900),
    "entregue": ("visto", tema.VERDE_VIVO, "#FFFFFF", None, 900),
    "copiado": ("copiar", "#F7A23B", tema.PILULA, "#F7A23B", 2800),
    "silencio": ("microfone_mudo", "#2C3526", "#DDE6D4", None, 1600),
    "sem_microfone": ("alerta", "#F0857A", tema.PILULA, "#F0857A", 4500),
    "erro": ("alerta", "#F0857A", tema.PILULA, "#F0857A", 3500),
}


class Pilula(QWidget):
    pedir_config = Signal()

    def __init__(self, cfg, motor):
        flags = (Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint
                 | Qt.WindowType.WindowDoesNotAcceptFocus)
        super().__init__(None, flags)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WidgetAttribute.WA_MacAlwaysShowToolWindow)  # no Mac, senão some com outro app na frente
        self.setWindowTitle("Papory")
        self.cfg, self.motor = cfg, motor
        self.estado, self.texto, self.inicio = "oculto", "", 0.0
        self.niveis = deque([0.0] * 10, maxlen=10)
        self.cabeca = tema.papagaio().copy(QRect(130, 15, 280, 280))
        self.fonte = tema.fonte(14, QFont.Weight.Bold)
        self.fonte_leve = tema.fonte(14, QFont.Weight.DemiBold)
        self._estilo_aplicado = False
        self.relogio = QTimer(self, interval=33, timeout=self._quadro)
        self.sumir = QTimer(self, singleShot=True, timeout=self._esconder)

    # ------------------------------------------------------------- estados
    def ao_evento(self, evento, dados):
        if evento == "ouvindo":
            self.inicio = time.monotonic()
            self.niveis.extend([0.0] * 10)
            self._mostrar("ouvindo", "0:00")
        elif evento == "escrevendo" and not self.motor.gravando:
            self._mostrar("escrevendo", "escrevendo")
        elif evento in MENSAGENS and not self.motor.gravando:
            # só o "colado" traz o app; no "silencio" o dado é a duração em segundos
            texto = f"Colado no {contexto.nome_do_app(dados)}" if evento == "colado" else {
                "entregue": "Pronto", "copiado": f"Copiado: use {plataforma.COLAR}", "silencio": "Não ouvi nada",
                "sem_microfone": "Sem microfone", "erro": "Algo deu errado"}[evento]
            self._mostrar(evento, texto)
            self.sumir.start(MENSAGENS[evento][4])

    def _largura(self, estado, texto):
        fm = QFontMetrics(self.fonte)
        if estado == "ouvindo":
            return 7 + 34 + 12 + 67 + 12 + fm.horizontalAdvance("0:00") + 16
        if estado == "escrevendo":
            return 7 + 34 + 12 + 31 + 12 + QFontMetrics(self.fonte_leve).horizontalAdvance(texto) + 18
        return 8 + 32 + 10 + fm.horizontalAdvance(texto) + 18

    def _mostrar(self, estado, texto):
        self.sumir.stop()
        self.estado, self.texto = estado, texto
        if not self.cfg["interface"].get("pilula", True):
            return
        largura = self._largura(estado, texto) + 2 * MARGEM
        tela = QGuiApplication.screenAt(QCursor.pos()) or QGuiApplication.primaryScreen()
        area = tela.availableGeometry()
        self.setGeometry(area.center().x() - largura // 2, area.bottom() - ALTURA - 2 * MARGEM - 4,
                         largura, ALTURA + 2 * MARGEM)
        if not self.isVisible():
            self.show()
            self._sem_foco()
        self.relogio.start()
        self.update()

    def _esconder(self):
        self.estado = "oculto"
        self.relogio.stop()
        self.hide()

    def _sem_foco(self):
        if self._estilo_aplicado:
            return
        try:
            plataforma.ajustar_pilula(self)
            self._estilo_aplicado = True
        except Exception:  # noqa: BLE001 — sem janela nativa (testes)
            pass

    def _quadro(self):
        if self.estado == "ouvindo":
            self.niveis.append(min(1.0, (self.motor.nivel() / 0.12) ** 0.5))
            s = int(time.monotonic() - self.inicio)
            self.texto = f"{s // 60}:{s % 60:02d}"
        self.update()

    def mousePressEvent(self, ev):
        if self.estado in ("sem_microfone", "erro"):
            self.pedir_config.emit()
            self._esconder()

    # ------------------------------------------------------------- desenho
    def paintEvent(self, _):
        if self.estado == "oculto":
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        caixa = QRectF(MARGEM, MARGEM, self.width() - 2 * MARGEM, ALTURA)
        for i, a in enumerate((22, 14, 7)):  # sombra suave
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(0, 0, 0, a))
            p.drawRoundedRect(caixa.adjusted(-2 - i * 3, -1 - i * 2 + 4, 2 + i * 3, 3 + i * 3), 26 + i * 3, 26 + i * 3)
        borda = MENSAGENS.get(self.estado, (None, None, None, None))[3]
        p.setBrush(QColor(tema.PILULA))
        p.setPen(QPen(QColor(borda), 2) if borda else Qt.PenStyle.NoPen)
        p.drawRoundedRect(caixa.adjusted(1, 1, -1, -1) if borda else caixa, ALTURA / 2, ALTURA / 2)
        x, meio = caixa.x(), caixa.center().y()

        if self.estado in ("ouvindo", "escrevendo"):
            circ = QRectF(x + 7, meio - 17, 34, 34)
            caminho = QPainterPath()
            caminho.addEllipse(circ)
            p.save()
            p.setClipPath(caminho)
            p.fillRect(circ, QColor("#E9F5DF"))
            p.drawPixmap(circ.adjusted(-2, -1, 2, 3).toRect(), self.cabeca)
            p.restore()
            x += 7 + 34 + 12
            if self.estado == "ouvindo":
                t = time.monotonic()
                for i, v in enumerate(self.niveis):
                    mexe = 0.08 * math.sin(t * 9 + i * 1.7) if v > 0.05 else 0
                    h = 22 * max(0.22, min(1.0, 0.22 + 0.78 * v + mexe))
                    p.setPen(Qt.PenStyle.NoPen)
                    p.setBrush(QColor("#F7A23B" if i % 2 == 0 else "#7BD155"))
                    p.drawRoundedRect(QRectF(x + i * 7, meio - h / 2, 4, h), 2, 2)
                x += 67 + 12
                p.setFont(self.fonte)
                p.setPen(QColor("#FFFFFF"))
                p.drawText(QRectF(x, caixa.y(), 80, ALTURA), Qt.AlignmentFlag.AlignVCenter, self.texto)
            else:
                t = time.monotonic()
                for i in range(3):
                    fase = (t * 1.0 - i * 0.2) % 1.2
                    alfa = 255 if fase < 0.4 else 70
                    p.setPen(Qt.PenStyle.NoPen)
                    p.setBrush(QColor(123, 209, 85, alfa))
                    p.drawEllipse(QRectF(x + i * 12, meio - 3.5, 7, 7))
                x += 31 + 12
                p.setFont(self.fonte_leve)
                p.setPen(QColor("#DDE6D4"))
                p.drawText(QRectF(x, caixa.y(), 200, ALTURA), Qt.AlignmentFlag.AlignVCenter, self.texto)
            return

        nome, cor_circulo, cor_icone, _, _ = MENSAGENS[self.estado]
        circ = QRectF(x + 8, meio - 16, 32, 32)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(cor_circulo))
        p.drawEllipse(circ)
        icone(nome, cor_icone, 18, 2.4).paint(p, circ.adjusted(7, 7, -7, -7).toRect())
        p.setFont(self.fonte)
        p.setPen(QColor("#FFFFFF"))
        p.drawText(QRectF(x + 8 + 32 + 10, caixa.y(), 400, ALTURA), Qt.AlignmentFlag.AlignVCenter, self.texto)
