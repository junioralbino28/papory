"""Liga tudo: motor + bandeja + pílula + janela (+ primeira abertura). Uma instância só por usuário."""
import getpass
import os
import random
import sys
import threading
import traceback

from PySide6.QtCore import QObject, QTimer, Signal
from PySide6.QtGui import QIcon
from PySide6.QtNetwork import QLocalServer, QLocalSocket
from PySide6.QtWidgets import QApplication

from .. import config, historico, modelo, plataforma
from ..motor import Motor
from . import aviso_som, calibracao, tema
from .bandeja import Bandeja
from .janela import Janela
from .pilula import Pilula
from .primeira import PrimeiraAbertura


class Ponte(QObject):
    """O motor avisa de threads de fundo; o sinal entrega na thread da tela."""
    evento = Signal(str, object)


class MotorFalso:
    """Para testar a interface sem carregar a voz (--sem-motor)."""

    def __init__(self, cfg, avisar):
        self.cfg, self.avisar = cfg, avisar
        self.pausado = self.gravando = False
        self.pronto = True
        self.entregar = self.rec = self.polidor = None

    def carregar(self):
        self.avisar("pronto", None)

    def pausar(self, v):
        self.pausado = v
        self.avisar("pausado", v)

    def nivel(self):
        return random.uniform(0.0, 0.08) if self.gravando else 0.0

    def aplicar_config(self):
        pass

    def copiar_ultimo(self):
        return None

    def parar(self):
        pass


def _redirecionar_log():
    """Sem terminal (pythonw ou .exe), print e erros vão para %APPDATA%\\Papory\\papory.log."""
    if sys.stdout is not None and sys.stdout.isatty():
        return
    config.PASTA.mkdir(parents=True, exist_ok=True)
    arq = config.PASTA / "papory.log"
    if arq.exists() and arq.stat().st_size > 2_000_000:
        arq.replace(arq.with_suffix(".log.1"))
    f = open(arq, "a", encoding="utf-8", buffering=1)  # noqa: SIM115 — fica aberto enquanto o app roda
    sys.stdout = sys.stderr = f
    threading.excepthook = lambda a: traceback.print_exception(a.exc_type, a.exc_value, a.exc_traceback)


def rodar(a):
    _redirecionar_log()
    try:  # identidade própria na barra de tarefas: sem isso o Windows mostra o ícone do Python (pythonw.exe)
        plataforma.identidade_app()
    except Exception:  # noqa: BLE001
        pass
    app = QApplication(sys.argv)
    app.setApplicationName("Papory")
    app.setWindowIcon(QIcon(str(tema.IMAGENS / "papory.ico")))
    app.setQuitOnLastWindowClosed(False)

    # PAPORY_INSTANCIA: só para testes rodarem ao lado do Papory de verdade sem chamar a janela dele
    nome = os.environ.get("PAPORY_INSTANCIA") or f"papory-{getpass.getuser()}"
    sock = QLocalSocket()
    sock.connectToServer(nome)
    if sock.waitForConnected(300):  # já está aberto: pede para mostrar a janela e sai
        sock.write(b"mostrar")
        sock.flush()
        sock.waitForBytesWritten(500)
        return 0
    QLocalServer.removeServer(nome)
    servidor = QLocalServer()
    servidor.listen(nome)

    tema.aplicar(app)
    cfg = config.carregar()
    ponte = Ponte()
    emitir = lambda evento, dados=None: ponte.evento.emit(evento, dados)  # noqa: E731
    motor = MotorFalso(cfg, emitir) if a.sem_motor else Motor(cfg, emitir)

    janela = Janela(cfg, motor)
    pilula = Pilula(cfg, motor)
    bandeja = Bandeja(cfg, motor)
    for receptor in (pilula.ao_evento, bandeja.ao_evento, janela.ao_evento, calibracao.repassar):
        ponte.evento.connect(receptor)
    ponte.evento.connect(lambda e, d: e == "aviso" and bandeja.avisar(str(d)))
    pilula.pedir_config.connect(lambda: janela.mostrar("config"))
    bandeja.abrir.connect(janela.mostrar)
    bandeja.config_mudou.connect(janela.config_mudou_fora)
    bandeja.sair.connect(app.quit)
    janela.fechou_primeira_vez.connect(
        lambda: bandeja.avisar(f"O Papory continua {plataforma.ONDE_ICONE}. Segure o atalho para falar."))

    def ler_pedido():
        c = servidor.nextPendingConnection()
        c.waitForReadyRead(300)
        janela.mostrar("inicio")

    servidor.newConnection.connect(ler_pedido)

    def carregar():
        threading.Thread(target=motor.carregar, daemon=True, name="carga").start()

    precisa_primeira = a.primeira_abertura or not modelo.baixado() or (
        not cfg["interface"]["primeira_abertura_feita"] and historico.contar() == 0)
    if precisa_primeira:
        bem_vindo = PrimeiraAbertura(cfg, motor, carregar)
        ponte.evento.connect(bem_vindo.ao_evento)
        bem_vindo.concluiu.connect(lambda: (janela.mostrar("inicio"), bandeja.avisar(
            "Tudo pronto. Segure o atalho em qualquer campo de texto, fale e solte.")))
        bem_vindo.show()
        janela.bem_vindo = bem_vindo  # mantém viva
    else:
        if not cfg["interface"]["primeira_abertura_feita"]:  # quem já usava antes da interface
            cfg["interface"]["primeira_abertura_feita"] = True
            config.salvar(cfg)
        carregar()
        if not a.escondido:
            janela.show()
        # quem já usava e atualizou: o aviso do assobio aparece uma vez, antes do próximo ditado
        QTimer.singleShot(800, lambda: aviso_som.mostrar_se_precisa(janela if janela.isVisible() else None, cfg))

    faltam = plataforma.pedir_permissoes()  # Mac: abre os pedidos do sistema (no Windows não falta nada)
    if faltam:
        bandeja.avisar(f"Para funcionar, ligue o Papory em {' e em '.join(faltam)}, na parte de Privacidade dos "
                       "ajustes do Mac. Depois feche e abra o Papory.")

    codigo = app.exec()
    motor.parar()
    bandeja.tray.hide()
    return codigo
