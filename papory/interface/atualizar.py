"""Aviso de versão nova na lateral e na bandeja; baixa, confere e instala quando a pessoa clica em Atualizar."""
import os
import sys
import threading

from PySide6.QtCore import QObject, QTimer, Signal
from PySide6.QtWidgets import QFrame, QProgressBar, QVBoxLayout

from .. import __version__, atualizacao
from .widgets import botao, rotulo

PRIMEIRA_S = 15  # espera o Papory abrir e carregar a voz antes de perguntar


class Atualizador(QObject):
    """Pergunta ao GitHub ao abrir e a cada 6 horas; baixa em segundo plano. Os sinais chegam na thread da tela."""
    achou = Signal(object)              # {versao, notas, pagina, nome, url, tamanho, sha256}
    progresso = Signal(object, object)  # bytes baixados, total
    baixou = Signal(object)             # caminho do arquivo conferido, ou a exceção

    def __init__(self, cfg):
        super().__init__()
        self.cfg, self.nova, self.baixando = cfg, None, False
        # PAPORY_FINGIR_VERSAO: só para testar a atualização no app instalado sem esperar uma versão nova
        self.atual = os.environ.get("PAPORY_FINGIR_VERSAO") or __version__
        self.relogio = QTimer(self, interval=atualizacao.INTERVALO_S * 1000, timeout=self.procurar)

    def iniciar(self):
        if atualizacao.pode_procurar():
            QTimer.singleShot(PRIMEIRA_S * 1000, self.procurar)
            self.relogio.start()

    def procurar(self):
        if self.cfg.get("atualizacoes", True) and not self.baixando:
            threading.Thread(target=self._procurar, daemon=True, name="atualizacao").start()

    def _procurar(self):
        try:
            nova = atualizacao.procurar(self.atual)
        except Exception as e:  # noqa: BLE001 — sem internet ou GitHub fora: tenta de novo na próxima
            print(f"atualização: não deu para perguntar ao GitHub ({type(e).__name__})")
            return
        if nova:
            self.achou.emit(nova)

    def baixar(self):
        if self.nova and not self.baixando:
            self.baixando = True
            threading.Thread(target=self._baixar, daemon=True, name="atualizacao").start()

    def _baixar(self):
        try:
            caminho = atualizacao.baixar(self.nova, lambda feito, total: self.progresso.emit(feito, total))
        except Exception as e:  # noqa: BLE001 — a tela mostra o motivo e deixa tentar de novo
            self.baixando = False
            print(f"atualização: falhou ao baixar ({type(e).__name__}: {e})")
            self.baixou.emit(e)
            return
        self.baixou.emit(caminho)


class CartaoAtualizacao(QFrame):
    """Faixa na lateral: aparece só quando há versão nova."""
    pediu = Signal()
    mudou = Signal()  # a altura mudou: a janela decide se o "Gostou do Papory?" ainda cabe

    def __init__(self):
        super().__init__()
        self.setProperty("papel", "dica")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(14, 12, 14, 12)
        lay.setSpacing(6)
        self.titulo = rotulo("", "h3")
        self.titulo.setStyleSheet("font-size: 14px;")
        self.texto = rotulo("", "pequeno", quebra=True)
        self.barra = QProgressBar()
        self.barra.setTextVisible(False)
        self.barra.setRange(0, 1000)
        self.barra.hide()
        self.botao = botao("Atualizar", "primario")
        self.botao.clicked.connect(self.pediu.emit)
        self.notas = rotulo("", "pequeno")
        self.notas.setOpenExternalLinks(True)
        for w in (self.titulo, self.texto, self.barra, self.botao, self.notas):
            lay.addWidget(w)
        self.compacto = self.explicacao_dispensavel = False
        self.hide()

    def compactar(self, sim):
        """Janela baixa: sai o link "O que mudou" e, quando o botão já diz o que fazer, a explicação."""
        self.compacto = sim
        self.texto.setVisible(not (sim and self.explicacao_dispensavel))
        self.notas.setVisible(not sim)

    def _avisar(self):
        self.compactar(self.compacto)
        self.mudou.emit()

    def mostrar(self, nova):
        self.explicacao_dispensavel = True
        self.titulo.setText(f"Versão {nova['versao']} disponível")
        self.texto.setText("Baixa, instala e abre de novo sozinho." if sys.platform == "win32" else
                           "Baixa o Papory novo para você arrastar para Aplicativos.")
        self.notas.setText(f'<a href="{nova["pagina"]}" style="color:#8A4600;">O que mudou</a>')
        self.botao.setText("Atualizar" if sys.platform == "win32" else "Baixar")
        self.botao.setToolTip("")
        self.botao.setEnabled(True)
        self.botao.show()
        self.barra.hide()
        self.show()
        self._avisar()

    def baixando(self, feito, total):
        self.barra.show()
        if total:
            self.barra.setValue(int(1000 * min(1.0, feito / total)))
        self.botao.setEnabled(False)
        self.botao.setText(f"Baixando… {int(100 * feito / total)}%" if total else "Baixando…")
        self._avisar()

    def esperando_ditado(self):
        self.explicacao_dispensavel = False
        self.barra.hide()  # já baixou: falta só o ditado acabar
        self.botao.hide()
        self.texto.setText("Termine o ditado: a atualização começa logo depois.")
        self._avisar()

    def instalando(self):
        self.explicacao_dispensavel = False
        self.barra.hide()
        self.botao.hide()
        self.texto.setText("Instalando… o Papory fecha e abre de novo sozinho em menos de um minuto.")
        self._avisar()

    def mac_pronto(self):
        self.explicacao_dispensavel = False
        self.barra.hide()
        self.botao.hide()
        self.texto.setText("Pronto: abri o arquivo. Feche o Papory, arraste o Papory novo para Aplicativos e "
                           "confirme Substituir.")
        self._avisar()

    def erro(self, motivo):
        self.explicacao_dispensavel = True  # na janela baixa o motivo fica na dica do botão
        self.barra.hide()
        self.botao.setEnabled(True)
        self.botao.setText("Tentar de novo")
        self.botao.show()
        self.texto.setText(f"Não deu para atualizar ({motivo}).")
        self.botao.setToolTip(self.texto.text())
        self._avisar()
