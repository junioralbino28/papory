"""Tela Configurações: atalho, microfone, reconhecimento, polimento local, reforço na nuvem e geral."""
import json
import threading
import webbrowser
from pathlib import Path

import requests
from PySide6.QtCore import QObject, Qt, QTimer, Signal
from PySide6.QtWidgets import (QComboBox, QDialog, QHBoxLayout, QLineEdit, QMessageBox, QVBoxLayout, QWidget)

from .. import __version__, audio, config, historico, modelo, plataforma
from ..teclado import GRUPOS
from . import tema
from .calibracao import Calibracao
from .widgets import (Interruptor, Medidor, botao, cartao, icone, limpar_layout, linha, nome_tecla,
                      pagina_rolavel, rotulo, teclas)

OLLAMA = "http://127.0.0.1:11434"
ORDEM_TECLAS = ["ctrl", "win", "shift", "alt", "alt_gr", *[f"f{n}" for n in range(1, 13)]]


def _gb(n):
    return f"{n / 1e9:.1f} GB".replace(".", ",")


def _ollama_app():
    return plataforma.ollama_app()


def _icone_rotulo(nome, cor, tam=16):
    r = rotulo("")
    r.setPixmap(icone(nome, cor, tam, 2).pixmap(tam, tam))
    return r


class _Ponte(QObject):
    resultado = Signal(str, object)


class StatusPolimento(QWidget):
    """Mostra se o polimento local está pronto e oferece o próximo passo (instalar, abrir, baixar)."""
    mudou = Signal()

    def __init__(self, cfg):
        super().__init__()
        self.cfg = cfg
        self.ponte = _Ponte()
        self.ponte.resultado.connect(self._mostrar)
        self.lay = QVBoxLayout(self)
        self.lay.setContentsMargins(0, 0, 0, 0)
        self.lay.setSpacing(10)
        self.verificar()

    def verificar(self):
        limpar_layout(self.lay)
        self.lay.addWidget(rotulo("Verificando o polimento local…", "meta"))
        threading.Thread(target=self._checar, daemon=True).start()

    def _checar(self):
        nome = self.cfg["polimento"]["modelo_local"]
        try:
            tags = requests.get(f"{OLLAMA}/api/tags", timeout=2).json()
            achado = next((m for m in tags.get("models", []) if m["name"] == nome), None)
            self.ponte.resultado.emit("instalado" if achado else "falta_modelo", achado)
        except Exception:  # noqa: BLE001
            app = _ollama_app()
            self.ponte.resultado.emit("fechado" if app else "sem_ollama", app)

    def _mostrar(self, estado, info):
        limpar_layout(self.lay)
        nome = self.cfg["polimento"]["modelo_local"]
        if estado == "instalado":
            linha_ok = QHBoxLayout()
            linha_ok.setSpacing(8)
            linha_ok.addWidget(_icone_rotulo("visto", tema.VERDE))
            linha_ok.addWidget(rotulo("Instalado", "verde"))
            linha_ok.addWidget(rotulo(f"{nome} pelo Ollama · {_gb(info.get('size', 0))} · se passar de 3 s, cola o "
                                      "texto sem polir", "meta", quebra=True), 1)
            self.lay.addLayout(linha_ok)
            self.mudou.emit()
            return
        textos = {"falta_modelo": f"Falta baixar o modelo {nome} (cerca de 3,3 GB). Depois funciona sem internet.",
                  "fechado": "O Ollama está instalado, mas fechado. Ele precisa estar aberto para polir o texto.",
                  "sem_ollama": "Precisa do Ollama, um programa grátis que roda IAs pequenas no seu computador."}
        self.lay.addWidget(rotulo(textos[estado], "meta", quebra=True))
        botoes = QHBoxLayout()
        botoes.setSpacing(8)
        if estado == "falta_modelo":
            b = botao("Instalar o modelo", "contorno")
            b.clicked.connect(lambda: self._baixar_modelo(b))
        elif estado == "fechado":
            b = botao("Abrir o Ollama", "contorno")
            b.clicked.connect(lambda: self._abrir_ollama(info))
        else:
            b = botao("Baixar o Ollama", "contorno")
            b.clicked.connect(lambda: webbrowser.open("https://ollama.com/download"))
        botoes.addWidget(b)
        de_novo = botao("Verificar de novo", "texto")
        de_novo.clicked.connect(self.verificar)
        botoes.addWidget(de_novo)
        self.progresso = rotulo("", "meta")
        botoes.addWidget(self.progresso)
        botoes.addStretch(1)
        self.lay.addLayout(botoes)

    def _abrir_ollama(self, app):
        try:
            plataforma.abrir_programa(app)
        except OSError:
            pass
        QTimer.singleShot(4000, self.verificar)

    def _baixar_modelo(self, b):
        b.setEnabled(False)
        nome = self.cfg["polimento"]["modelo_local"]

        def trabalho():
            try:
                with requests.post(f"{OLLAMA}/api/pull", json={"model": nome, "stream": True}, stream=True,
                                   timeout=(5, 600)) as r:
                    for linha_bruta in r.iter_lines():
                        if not linha_bruta:
                            continue
                        d = json.loads(linha_bruta)
                        if d.get("total") and d.get("completed"):
                            self.ponte.resultado.emit("progresso", d["completed"] / d["total"])
                        if d.get("status") == "success":
                            break
                self._checar()
            except Exception as e:  # noqa: BLE001
                self.ponte.resultado.emit("progresso", f"falhou: {type(e).__name__}")

        self.ponte.resultado.disconnect()
        self.ponte.resultado.connect(self._progresso)
        threading.Thread(target=trabalho, daemon=True).start()

    def _progresso(self, estado, info):
        if estado != "progresso":
            self.ponte.resultado.disconnect()
            self.ponte.resultado.connect(self._mostrar)
            self._mostrar(estado, info)
            return
        if isinstance(info, float):
            self.progresso.setText(f"Baixando… {info * 100:.0f}%")
        else:
            self.progresso.setText(str(info))


class DialogoAtalho(QDialog):
    """Captura o novo atalho: a maior combinação apertada ao mesmo tempo."""

    def __init__(self, pai, atual):
        super().__init__(pai)
        self.setWindowTitle("Trocar atalho")
        self.setMinimumWidth(460)
        self.setStyleSheet(f"QDialog {{ background: {tema.BRANCO}; }}")
        self.apertadas, self.combinacao = set(), list(atual)
        v = QVBoxLayout(self)
        v.setContentsMargins(24, 22, 24, 22)
        v.setSpacing(14)
        v.addWidget(rotulo("Trocar atalho", "h3"))
        v.addWidget(rotulo("Aperte e segure as teclas do novo atalho, depois solte.", "meta", quebra=True))
        self.mostra = QHBoxLayout()
        v.addLayout(self.mostra)
        self.dica = rotulo(f"Use duas teclas ou mais (ex.: {nome_tecla('ctrl')} + {nome_tecla('win')}, "
                           f"{nome_tecla('ctrl')} + Shift) ou uma tecla F (F8, F9…).",
                           "pequeno", quebra=True)
        v.addWidget(self.dica)
        linha_b = QHBoxLayout()
        linha_b.addStretch(1)
        cancelar, self.ok = botao("Cancelar"), botao("Salvar atalho", "primario")
        cancelar.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.ok.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        cancelar.clicked.connect(self.reject)
        self.ok.clicked.connect(self.accept)
        linha_b.addWidget(cancelar)
        linha_b.addWidget(self.ok)
        v.addLayout(linha_b)
        self._atualizar()

    @staticmethod
    def _nome(ev):
        k = ev.key()
        mapa = {Qt.Key.Key_Control: "ctrl", Qt.Key.Key_Meta: "win", Qt.Key.Key_Super_L: "win",
                Qt.Key.Key_Super_R: "win", Qt.Key.Key_Shift: "shift", Qt.Key.Key_Alt: "alt",
                Qt.Key.Key_AltGr: "alt_gr"}
        if k in mapa:
            return mapa[k]
        if Qt.Key.Key_F1 <= k <= Qt.Key.Key_F12:
            return f"f{k - Qt.Key.Key_F1 + 1}"
        return None

    def keyPressEvent(self, ev):
        nome = self._nome(ev)
        if nome is None or ev.isAutoRepeat():
            return
        if not self.apertadas:
            self.combinacao = []
        self.apertadas.add(nome)
        if len(self.apertadas) >= len(self.combinacao):
            self.combinacao = sorted(self.apertadas, key=ORDEM_TECLAS.index)
        self._atualizar()

    def keyReleaseEvent(self, ev):
        nome = self._nome(ev)
        if nome and not ev.isAutoRepeat():
            self.apertadas.discard(nome)

    def _valido(self):
        c = self.combinacao
        return all(t in GRUPOS for t in c) and (len(c) >= 2 or (len(c) == 1 and c[0].startswith("f")))

    def _atualizar(self):
        limpar_layout(self.mostra)
        self.mostra.addWidget(teclas(self.combinacao, grande=True) if self.combinacao else rotulo("…", "sub"))
        self.mostra.addStretch(1)
        self.ok.setEnabled(self._valido())


class PaginaConfig:
    def __init__(self, janela):
        self.janela = janela
        cfg = janela.cfg
        self.area, v = pagina_rolavel(880)
        v.setSpacing(20)

        cab = QVBoxLayout()
        cab.setSpacing(8)
        cab.addWidget(rotulo("Configurações", "titulo"))
        cab.addWidget(rotulo("Tudo que vem ligado roda no seu computador, sem internet e sem pagar nada.", "sub",
                             quebra=True))
        v.addLayout(cab)
        v.addSpacing(8)

        # ---- atalho
        c, l = cartao()
        l.addWidget(rotulo("Atalho para falar", "h3"))
        linha_at = QHBoxLayout()
        linha_at.setSpacing(10)
        linha_at.addWidget(rotulo("Segure", "sub"))
        self.caixa_teclas = QHBoxLayout()
        linha_at.addLayout(self.caixa_teclas)
        linha_at.addWidget(rotulo(", fale e solte", "sub"))
        linha_at.addStretch(1)
        trocar = botao("Trocar atalho")
        trocar.clicked.connect(self._trocar_atalho)
        linha_at.addWidget(trocar)
        l.addLayout(linha_at)
        l.addWidget(rotulo(f"Se outro app de ditado usar o mesmo atalho ({plataforma.OUTRO_APP_ATALHO}), o texto sai "
                           "duas vezes. Feche o outro ou troque aqui.", "pequeno", quebra=True))
        v.addWidget(c)

        # ---- microfone
        c, l = cartao()
        l.addWidget(rotulo("Microfone", "h3"))
        l.addWidget(rotulo("Usar", "rotulo"))
        linha_mic = QHBoxLayout()
        linha_mic.setSpacing(12)
        self.mic = QComboBox()
        self.mic.setAccessibleName("Microfone")
        self.mic.activated.connect(self._trocar_mic)
        linha_mic.addWidget(self.mic, 1)
        self.b_testar = botao("Testar", "secundario", "microfone")
        self.b_testar.clicked.connect(self._testar_mic)
        linha_mic.addWidget(self.b_testar)
        l.addLayout(linha_mic)
        linha_vol = QHBoxLayout()
        linha_vol.setSpacing(12)
        linha_vol.addWidget(rotulo("Volume", "meta"))
        self.medidor = Medidor()
        linha_vol.addWidget(self.medidor, 1)
        l.addLayout(linha_vol)
        v.addWidget(c)

        # ---- calibração
        c, l = cartao()
        l.addWidget(rotulo("Seu jeito de falar", "h3"))
        linha_cal = QHBoxLayout()
        linha_cal.setSpacing(12)
        linha_cal.addWidget(rotulo("Leia algumas frases curtas e o Papory aprende os nomes e termos que você mais "
                                   "usa. Também confere o volume do microfone.", "meta", quebra=True), 1)
        b_calibrar = botao("Ler as frases", "secundario", "microfone")
        b_calibrar.clicked.connect(self._calibrar)
        linha_cal.addWidget(b_calibrar, 0, Qt.AlignmentFlag.AlignVCenter)
        l.addLayout(linha_cal)
        v.addWidget(c)

        # ---- reconhecimento
        c, l = cartao()
        l.addWidget(rotulo("Reconhecimento de voz", "h3"))
        linha_rec = QHBoxLayout()
        linha_rec.setSpacing(14)
        col1, col2 = QVBoxLayout(), QVBoxLayout()
        col1.setSpacing(6)
        col2.setSpacing(6)
        col1.addWidget(rotulo("Onde roda", "rotulo"))
        self.onde = QComboBox()
        self.onde.addItem("Automático: placa de vídeo, se houver", "auto")
        self.onde.addItem("Só o processador (mais lento)", "cpu")
        self.onde.setAccessibleName("Onde o reconhecimento roda")
        self.onde.activated.connect(self._trocar_onde)
        col1.addWidget(self.onde)
        col2.addWidget(rotulo("Idioma", "rotulo"))
        idioma = rotulo("Português", "texto")
        idioma.setStyleSheet(f"background: {tema.FUNDO}; border-radius: 12px; padding: 12px 14px; font-weight: 600;")
        col2.addWidget(idioma)
        linha_rec.addLayout(col1, 3)
        linha_rec.addLayout(col2, 2)
        l.addLayout(linha_rec)
        self.status_voz = QHBoxLayout()
        self.status_voz.setSpacing(8)
        l.addLayout(self.status_voz)
        v.addWidget(c)

        # ---- polimento
        c, l = cartao(espaco=12)
        topo, self.sw_polimento = self._linha_chave("Polimento local",
                                                    "Uma IA pequena, no seu computador, corrige palavras que soam "
                                                    "parecido e tira “é…”, “tipo”, “né” sobrando. Não manda nada para "
                                                    "a internet.", cfg["polimento"]["ativo"], grande=True)
        self.sw_polimento.toggled.connect(self._mudar_polimento)
        l.addWidget(topo)
        self.status_polimento = StatusPolimento(cfg)
        self.status_polimento.mudou.connect(self.janela.motor.aplicar_config)
        l.addWidget(self.status_polimento)
        v.addWidget(c)

        # ---- reforço na nuvem
        c, l = cartao(espaco=14)
        topo, self.sw_reforco = self._linha_chave("Reforço na nuvem",
                                                  "Uma segunda transcrição e uma revisão pela Groq, no plano grátis. "
                                                  "Erra menos, mas não é preciso para usar.",
                                                  cfg["reforco_nuvem"]["ativo"], grande=True, etiqueta="opcional")
        self.sw_reforco.toggled.connect(self._mudar_reforco)
        l.addWidget(topo)
        self.corpo_reforco = QWidget()
        cr = QVBoxLayout(self.corpo_reforco)
        cr.setContentsMargins(0, 0, 0, 0)
        cr.setSpacing(14)
        aviso, al = cartao("aviso", (14, 12, 14, 12), 12, horizontal=True)
        al.addWidget(_icone_rotulo("cadeado", "#B35A00", 20), 0, Qt.AlignmentFlag.AlignTop)
        al.addWidget(rotulo("<b>Ligado, o áudio e o texto de cada ditado vão para a Groq.</b> Se a Groq falhar, "
                            "demorar ou a cota grátis acabar, o Papory segue só com o local, sem você perceber.",
                            "laranja", quebra=True), 1)
        cr.addWidget(aviso)
        cr.addWidget(rotulo("Chave da Groq", "rotulo"))
        linha_ch = QHBoxLayout()
        linha_ch.setSpacing(10)
        self.campo_chave = QLineEdit()
        self.campo_chave.setEchoMode(QLineEdit.EchoMode.Password)
        self.campo_chave.setPlaceholderText("Cole aqui a sua chave")
        self.campo_chave.setAccessibleName("Chave da Groq")
        salvar_ch = botao("Salvar chave")
        salvar_ch.clicked.connect(self._salvar_chave)
        linha_ch.addWidget(self.campo_chave, 1)
        linha_ch.addWidget(salvar_ch)
        cr.addLayout(linha_ch)
        self.status_chave = QHBoxLayout()
        self.status_chave.setSpacing(8)
        cr.addLayout(self.status_chave)
        link = rotulo(f'<a href="https://console.groq.com/keys" style="color: {tema.VERDE};">'
                      'Como pegar uma chave grátis</a>')
        link.setOpenExternalLinks(True)
        link.setStyleSheet("font-size: 13px; font-weight: 700;")
        cr.addWidget(link)
        l.addWidget(self.corpo_reforco)
        v.addWidget(c)

        # ---- geral
        c, l = cartao(margens=(22, 10, 22, 16), espaco=0)
        t = rotulo("Geral", "h3")
        t.setContentsMargins(0, 12, 0, 4)
        l.addWidget(t)
        itens = [("Bipes ao começar e ao terminar", "Um bipe grave avisa quando o texto ficou só copiado.",
                  cfg["sons"], self._mudar_bipes),
                 ("Mostrar a pílula enquanto ouve", f"Fica no rodapé da tela, {plataforma.ONDE_PILULA}.",
                  cfg["interface"]["pilula"], self._mudar_pilula),
                 (f"Iniciar com o {plataforma.NOME}", plataforma.ICONE_FICA, plataforma.inicio_ligado(),
                  self._mudar_iniciar),
                 ("Guardar o histórico", "Áudio e texto de cada ditado, só neste computador.", cfg["historico"],
                  self._mudar_historico)]
        self.sw_geral = []
        for i, (titulo, desc, valor, acao) in enumerate(itens):
            if i:
                l.addWidget(linha())
            w, sw = self._linha_chave(titulo, desc, valor)
            w.setContentsMargins(0, 10, 0, 10)
            sw.toggled.connect(acao)
            self.sw_geral.append(sw)
            l.addWidget(w)
        botoes = QHBoxLayout()
        botoes.setSpacing(10)
        botoes.setContentsMargins(0, 8, 0, 0)
        abrir = botao("Abrir a pasta do histórico")
        abrir.clicked.connect(self._abrir_pasta)
        apagar = botao("Apagar o histórico", "perigo")
        apagar.clicked.connect(self._apagar_historico)
        botoes.addWidget(abrir)
        botoes.addWidget(apagar)
        botoes.addStretch(1)
        l.addLayout(botoes)
        v.addWidget(c)

        rod = QHBoxLayout()
        rod.setSpacing(10)
        img = rotulo("")
        img.setPixmap(tema.papagaio().scaled(28, 28, Qt.AspectRatioMode.KeepAspectRatio,
                                             Qt.TransformationMode.SmoothTransformation))
        rod.addWidget(img)
        rod.addWidget(rotulo(f"Papory {__version__} · roda no seu computador", "meta"))
        rod.addStretch(1)
        v.addLayout(rod)
        v.addStretch(1)

        self.teste = None
        self.relogio_teste = QTimer(interval=50, timeout=self._quadro_teste)

    # ------------------------------------------------------------ montagem
    @staticmethod
    def _linha_chave(texto, descricao, valor, grande=False, etiqueta=None):
        w = QWidget()
        lay = QHBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(16)
        col = QVBoxLayout()
        col.setSpacing(4)
        linha_t = QHBoxLayout()
        linha_t.setSpacing(8)
        t = rotulo(texto, "h3")
        if not grande:
            t.setStyleSheet("font-size: 15px; font-weight: 700;")
        linha_t.addWidget(t)
        if etiqueta:
            linha_t.addWidget(rotulo(etiqueta, "tag_neutra"))
        linha_t.addStretch(1)
        col.addLayout(linha_t)
        col.addWidget(rotulo(descricao, "meta", quebra=True))
        lay.addLayout(col, 1)
        sw = Interruptor(valor, texto)
        lay.addWidget(sw, 0, Qt.AlignmentFlag.AlignVCenter)
        return w, sw

    # ------------------------------------------------------------- dados
    def recarregar(self):
        cfg, motor = self.janela.cfg, self.janela.motor
        limpar_layout(self.caixa_teclas)
        self.caixa_teclas.addWidget(teclas(cfg["atalho"], grande=True))

        self.mic.clear()
        padrao = audio.microfone_padrao()
        self.mic.addItem(f"Padrão do {plataforma.NOME}{f' ({padrao})' if padrao else ''}", None)
        for nome in audio.listar_microfones():
            self.mic.addItem(nome, nome)
        i = self.mic.findData(cfg["microfone"])
        self.mic.setCurrentIndex(i if i >= 0 else 0)

        self.onde.setCurrentIndex(max(0, self.onde.findData(cfg["asr"]["dispositivo"])))
        limpar_layout(self.status_voz)
        tam = modelo.tamanho_no_disco()
        if tam:
            self.status_voz.addWidget(_icone_rotulo("visto", tema.VERDE))
            self.status_voz.addWidget(rotulo("Instalado", "verde"))
        agora = f" · agora na {motor.rec.onde}" if getattr(motor, "pronto", False) and motor.rec else ""
        self.status_voz.addWidget(rotulo(f"Modelo Parakeet TDT 0.6B v3 · {_gb(tam)} no disco{agora}" if tam else
                                         "O modelo de voz ainda não foi baixado.", "meta", quebra=True), 1)

        for sw, valor in ((self.sw_polimento, cfg["polimento"]["ativo"]),
                          (self.sw_reforco, cfg["reforco_nuvem"]["ativo"]),
                          (self.sw_geral[0], cfg["sons"]), (self.sw_geral[1], cfg["interface"]["pilula"]),
                          (self.sw_geral[2], plataforma.inicio_ligado()), (self.sw_geral[3], cfg["historico"])):
            sw.blockSignals(True)
            sw.setChecked(bool(valor))
            sw.blockSignals(False)
        self.status_polimento.setVisible(cfg["polimento"]["ativo"])
        self.corpo_reforco.setVisible(cfg["reforco_nuvem"]["ativo"])
        self._mostrar_status_chave()

    def _mostrar_status_chave(self):
        cfg = self.janela.cfg
        limpar_layout(self.status_chave)
        caminho = cfg.get("arquivo_de_chaves")
        do_arquivo = False
        if caminho and Path(caminho).exists():
            do_arquivo = any(l.strip().removeprefix("export ").startswith("GROQ_API_KEY=")
                             for l in Path(caminho).read_text(encoding="utf-8", errors="replace").splitlines())
        if do_arquivo:
            self.status_chave.addWidget(_icone_rotulo("visto", tema.VERDE))
            self.status_chave.addWidget(rotulo("Chave lida do seu arquivo de chaves", "verde"))
        elif config.chave("GROQ_API_KEY", cfg):
            self.status_chave.addWidget(_icone_rotulo("visto", tema.VERDE))
            self.status_chave.addWidget(rotulo("Chave salva neste computador", "verde"))
        else:
            self.status_chave.addWidget(rotulo("Sem chave: o reforço fica parado até você colar uma.", "erro"))
        self.status_chave.addStretch(1)

    def _salvar(self):
        self.janela.salvar_config()
        self.recarregar()

    # ----------------------------------------------------------- ações
    def _trocar_atalho(self):
        motor = self.janela.motor
        estava = motor.pausado
        motor.pausar(True)  # senão apertar o atalho atual aqui começaria um ditado
        d = DialogoAtalho(self.area, self.janela.cfg["atalho"])
        if d.exec() and d.combinacao:
            self.janela.cfg["atalho"] = list(d.combinacao)
            self._salvar()
        motor.pausar(estava)

    def _trocar_mic(self, _):
        self.janela.cfg["microfone"] = self.mic.currentData()
        self._salvar()

    def _calibrar(self):
        if self.teste is not None:
            self._parar_teste()
        d = Calibracao(self.area, self.janela.cfg, self.janela.motor, self.janela.salvar_config)
        d.terminou.connect(lambda _: self.janela.vocabulario_mudou())
        d.exec()

    def _testar_mic(self):
        if self.teste is not None or self.janela.motor.gravando:
            return
        nome = self.mic.currentData()
        try:
            self.nivel_teste = 0.0

            def cb(dados, *_):
                import numpy as np
                self.nivel_teste = float(np.sqrt(np.mean(dados[:, 0] ** 2)))

            self.teste = audio.abrir_medidor(nome, cb)
        except Exception:  # noqa: BLE001
            self.b_testar.setText("Microfone não encontrado")
            QTimer.singleShot(2500, lambda: self.b_testar.setText("Testar"))
            self.teste = None
            return
        self.b_testar.setText("Fale algo…")
        self.relogio_teste.start()
        QTimer.singleShot(6000, self._parar_teste)

    def _quadro_teste(self):
        self.medidor.definir(getattr(self, "nivel_teste", 0.0))

    def _parar_teste(self):
        if self.teste is not None:
            audio.fechar_medidor(self.teste)
            self.teste = None
        self.relogio_teste.stop()
        self.medidor.definir(0)
        self.b_testar.setText("Testar")

    def _trocar_onde(self, _):
        self.janela.cfg["asr"]["dispositivo"] = self.onde.currentData()
        self._salvar()

    def _mudar_polimento(self, ligado):
        self.janela.cfg["polimento"]["ativo"] = ligado
        self._salvar()
        if ligado:
            self.status_polimento.verificar()

    def _mudar_reforco(self, ligado):
        self.janela.cfg["reforco_nuvem"]["ativo"] = ligado
        self._salvar()

    def _salvar_chave(self):
        valor = self.campo_chave.text().strip()
        if not valor:
            return
        config.guardar_chave("GROQ_API_KEY", valor)
        self.campo_chave.clear()
        self._salvar()

    def _mudar_bipes(self, v):
        self.janela.cfg["sons"] = v
        self._salvar()

    def _mudar_pilula(self, v):
        self.janela.cfg["interface"]["pilula"] = v
        self._salvar()

    def _mudar_iniciar(self, v):
        plataforma.ligar_inicio(v)
        self.recarregar()

    def _mudar_historico(self, v):
        self.janela.cfg["historico"] = v
        self._salvar()

    def _abrir_pasta(self):
        historico.pasta().mkdir(parents=True, exist_ok=True)
        plataforma.abrir(historico.pasta())

    def _apagar_historico(self):
        n = historico.contar()
        if not n:
            return
        r = QMessageBox.question(self.area, "Apagar o histórico",
                                 f"Apagar os {n} ditados guardados (áudio e texto)? Isso não pode ser desfeito.\n\n"
                                 "O vocabulário e os atalhos continuam.",
                                 QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                 QMessageBox.StandardButton.No)
        if r == QMessageBox.StandardButton.Yes:
            historico.apagar_tudo()
            self.janela.historico_mudou()
