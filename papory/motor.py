"""Motor do Papory: atalho, microfone, reconhecimento, polimento e colagem, sem interface.

O modo terminal e a interface (bandeja, pílula, janela) usam o mesmo motor. Ele conta o que está acontecendo
chamando avisar(evento, dados) a partir de threads de fundo; quem desenha na tela repassa para a thread dela.

Eventos: carregando (etapa), pronto, ouvindo (processo), escrevendo, colado (processo), copiado, silencio,
entregue (texto), sem_microfone, aviso (texto), erro (texto), ditado (registro), pausado (bool).

Três threads: o gancho de teclado só avisa (não pode demorar); o controle abre e fecha o microfone;
o trabalho transcreve, pole e cola, para você poder começar outro ditado enquanto o anterior é colado.
"""
import gc
import queue
import re
import threading
import time
import traceback

from . import colar, config, contexto, historico, plataforma
from .asr import Reconhecedor
from .audio import Gravador, GravadorDeArquivo, atualizar_aparelhos, medir_volume
from .polimento import Polidor
from .segunda_opiniao import SegundaOpiniao
from .teclado import Atalho


som = plataforma.tocar_som
ESPERA_MICROFONE_S = 3.0  # sem som nenhum do microfone nesse tempo, o assobio de começo toca assim mesmo


def aplicar_substituicoes(texto, cfg, processo):
    """Trocas fixas por app. "de" é palavra exata; "de_regex" é expressão regular (com grupos em "para")."""
    for s in cfg["substituicoes"]:
        if s.get("apps") and processo not in s["apps"]:
            continue
        padrao = s["de_regex"] if "de_regex" in s else rf"(?<!\w){re.escape(s['de'])}(?!\w)"
        texto = re.sub(padrao, s["para"], texto)
    return texto


def manter_pergunta(cru, final):
    """Se a fala terminou em pergunta, o texto final também termina com "?" (o polimento às vezes tira o "né?")."""
    if cru.rstrip().endswith("?") and not final.rstrip().endswith("?"):
        return final.rstrip().rstrip(".!…") + "?"
    return final


def aplicar_atalhos_de_texto(texto, cfg):
    for frase, troca in cfg["atalhos_de_texto"].items():
        texto = re.sub(rf"(?<!\w){re.escape(frase)}(?!\w)[.!?]?", troca, texto, flags=re.I)
    return texto


class Motor:
    def __init__(self, cfg, avisar=None, arquivo_teste=None, com_atalho=True):
        self.cfg = cfg
        self.avisar = avisar or (lambda evento, dados=None: None)
        self.arquivo_teste = arquivo_teste
        self.com_atalho = com_atalho  # False no autoteste: nenhum gancho de teclado
        self.pausado = False
        self.pronto = False
        self.gravando = False
        self._fala = 0              # conta os apertos: o assobio de começo atrasado não toca numa fala seguinte
        self.entregar = None        # se for uma função, recebe o texto final em vez de colar (teste do microfone)
        self.ultimo = None          # último registro, para "copiar o último ditado"
        self.ultima_restauracao = None
        self.rec = self.polidor = self.segunda = self.gravador = self.atalho = None
        self._eventos, self._trabalhos = queue.Queue(), queue.Queue()
        self._aplicado = {}

    # ------------------------------------------------------------------ carga
    def carregar(self):
        """Pesado (modelo de voz na placa de vídeo + aquecer o polimento): rode fora da thread da tela."""
        try:
            self.avisar("carregando", "microfone")
            self.gravador = self._novo_gravador()
            self.avisar("carregando", "voz")
            self.rec = Reconhecedor(self.cfg["asr"]["modelo"], self.cfg["asr"]["dispositivo"])
            self.avisar("carregando", "polimento")
            chave = config.chave("GROQ_API_KEY", self.cfg)
            self.polidor = Polidor(self.cfg, chave)
            self.segunda = SegundaOpiniao(self.cfg, chave)
            self._lembrar_aplicado()
            threading.Thread(target=self._controle, daemon=True, name="controle").start()
            threading.Thread(target=self._trabalho, daemon=True, name="trabalho").start()
            self._ligar_atalho()
            self.pronto = True
            self.avisar("pronto", None)
        except Exception as e:  # noqa: BLE001
            traceback.print_exc()
            self.avisar("erro", f"Não consegui iniciar: {e}")

    def descricao(self):
        if not self.pronto:
            return "carregando"
        return {"microfone": self.gravador.nome if self.gravador else "nenhum", "voz": self.rec.onde,
                "polimento": self.polidor.descricao(),
                "reforco": "ligado" if self.segunda.ligada else "desligado"}

    def _novo_gravador(self):
        if self.arquivo_teste:
            return GravadorDeArquivo(self.arquivo_teste)
        atualizar_aparelhos(minimo_s=0)  # um fone pode ter sido ligado depois que o Papory abriu
        try:
            return Gravador(self.cfg["microfone"])
        except ValueError:  # o microfone escolhido não está ligado: usa o padrão do sistema
            self.avisar("aviso", f"O microfone escolhido não está conectado. Usando o padrão do {plataforma.NOME}.")
        except Exception:  # noqa: BLE001
            pass
        try:
            return Gravador(None)
        except Exception:  # noqa: BLE001 — nenhum microfone no computador
            return None

    def _ligar_atalho(self):
        if not self.com_atalho:
            return
        if self.atalho:
            self.atalho.parar()
        self.atalho = Atalho(self.cfg["atalho"], lambda: self._eventos.put("apertou"),
                             lambda: self._eventos.put("soltou"))
        self.atalho.iniciar()

    # ------------------------------------------------------- comandos da tela
    def pausar(self, pausado):
        self.pausado = bool(pausado)
        self.avisar("pausado", self.pausado)

    def nivel(self):
        return getattr(self.gravador, "nivel", 0.0) if self.gravando else 0.0

    def _lembrar_aplicado(self):
        c = self.cfg
        self._aplicado = {"atalho": list(c["atalho"]), "microfone": c["microfone"],
                          "dispositivo": c["asr"]["dispositivo"]}

    def aplicar_config(self):
        """Depois que a tela muda a configuração: liga/desliga na hora o que dá, recarrega o que precisa."""
        if not self.pronto:
            return
        c = self.cfg
        chave = config.chave("GROQ_API_KEY", c)
        self.polidor.chave = self.segunda.chave = chave
        self.polidor.ligado = bool(c["polimento"]["ativo"])
        self.polidor.reforco = bool(c["reforco_nuvem"]["ativo"]) and bool(chave)
        self.segunda.ligada = bool(c["reforco_nuvem"]["ativo"]) and bool(chave)
        if self.polidor.ligado and not self.polidor.local_ok:  # talvez tenham aberto o Ollama ou baixado o modelo
            threading.Thread(target=self._preparar_polimento, daemon=True).start()
        antes = self._aplicado
        if list(c["atalho"]) != antes.get("atalho"):
            self._ligar_atalho()
        if c["microfone"] != antes.get("microfone") and not self.gravando:
            self.gravador = self._novo_gravador()
        if c["asr"]["dispositivo"] != antes.get("dispositivo"):
            threading.Thread(target=self._recarregar_voz, daemon=True).start()
        self._lembrar_aplicado()

    def _preparar_polimento(self):
        self.polidor.local_ok = self.polidor._preparar_local()
        self.avisar("pronto", None)

    def _recarregar_voz(self):
        self.pronto = False
        self.avisar("carregando", "voz")
        try:
            self.rec = None
            gc.collect()  # solta o modelo antigo da placa antes de carregar o novo
            self.rec = Reconhecedor(self.cfg["asr"]["modelo"], self.cfg["asr"]["dispositivo"])
            self.pronto = True
            self.avisar("pronto", None)
        except Exception as e:  # noqa: BLE001
            traceback.print_exc()
            self.avisar("erro", f"Não consegui carregar o reconhecimento: {e}")

    def copiar_ultimo(self):
        """Põe o último ditado na área de transferência; devolve o texto (ou None)."""
        texto = (self.ultimo or {}).get("final")
        if not texto:
            ultimos = historico.listar(limite=1)
            texto = ultimos[0]["final"] if ultimos else None
        if texto:
            plataforma.escrever_texto(texto)
        return texto

    def parar(self):
        if self.atalho:
            self.atalho.parar()
        self._eventos.put("parar")
        self._trabalhos.put(None)

    # ------------------------------------------------------------ as threads
    def _controle(self):
        estado = {}
        while True:
            ev = self._eventos.get()
            if ev == "parar":
                return
            if ev == "apertou":
                if self.pausado or not self.pronto:
                    continue
                if self.gravador is None:
                    self.gravador = self._novo_gravador()  # talvez tenham ligado um microfone
                ctx = contexto.app_ativo()
                try:
                    if self.gravador is None:
                        raise OSError("sem microfone")
                    self.gravador.iniciar()
                except Exception:  # noqa: BLE001 — microfone desligado no meio do caminho
                    self.gravador = None
                    self.avisar("sem_microfone", None)
                    continue
                estado = {"contexto": ctx}
                self.gravando = True
                self._fala += 1
                if self.cfg["sons"]:
                    threading.Thread(target=self._assobiar_quando_ouvir, args=(self.gravador, self._fala),
                                     daemon=True).start()
                self.avisar("ouvindo", ctx["processo"])
            elif ev == "soltou" and estado:
                audio, taxa = self.gravador.parar()
                self.gravando = False
                if self.cfg["sons"]:
                    som("terminou")
                self._trabalhos.put((audio, taxa, estado["contexto"], time.perf_counter()))
                self.avisar("escrevendo", None)
                estado = {}
                if not self.arquivo_teste:  # relê a lista enquanto o texto é escrito: o próximo ditado já vê fone novo
                    threading.Thread(target=atualizar_aparelhos, daemon=True).start()

    def _assobiar_quando_ouvir(self, gravador, fala):
        """O assobio de começo quer dizer "pode falar": só toca quando o microfone entrega som de verdade."""
        gravador.ouviu.wait(ESPERA_MICROFONE_S)
        if self.gravando and self._fala == fala:  # soltou antes: o assobio de fim já tocou
            som("comecou")

    def _trabalho(self):
        while True:
            item = self._trabalhos.get()
            if item is None:
                return
            try:
                self._processar(*item)
            except Exception as e:  # noqa: BLE001 — um ditado com defeito não derruba o app
                traceback.print_exc()
                self.avisar("erro", f"{type(e).__name__}: {e}")

    def _processar(self, audio, taxa, ctx, soltou):
        dur = len(audio) / taxa if taxa else 0
        esperar_segunda = self.segunda.pedir(audio, taxa)  # vai para a nuvem enquanto o Parakeet trabalha
        t0 = time.perf_counter()
        cru = self.rec.transcrever(audio, taxa)
        outra = esperar_segunda()
        t_asr = time.perf_counter() - t0
        if not cru and outra:
            cru, outra = outra, None
        if not cru:
            self.avisar("silencio", round(dur, 1))
            return
        t1 = time.perf_counter()
        final, motivo, onde = self.polidor.polir(cru, ctx, outra=outra, duracao_s=dur)
        t_pol = time.perf_counter() - t1
        final = aplicar_substituicoes(final, self.cfg, ctx["processo"])  # regras fixas valem para todo caminho
        final = manter_pergunta(cru, final)
        final = aplicar_atalhos_de_texto(final, self.cfg)

        entregar = self.entregar
        if entregar:
            entregar(final)
            ok, resultado = True, "entregue"
            self.avisar("entregue", final)
        else:
            restauracao = colar.colar(final, hwnd=ctx["hwnd"])
            if restauracao == "copiado":  # a janela onde a fala começou sumiu ou não voltou para a frente
                if self.cfg["sons"]:
                    som("copiou")
                ok, resultado, restauracao = True, "copiado", None
                self.avisar("copiado", None)
            else:
                ok = restauracao is not None
                resultado = "colado" if ok else "falhou"
                self.avisar("colado" if ok else "erro", ctx["processo"] if ok else "Não consegui colar o texto.")
            self.ultima_restauracao = restauracao

        registro = {"app": ctx["processo"], "titulo": ctx["titulo"], "duracao_s": round(dur, 2), "cru": cru,
                    "segunda_opiniao": outra, "polimento": onde, "trocas": self.polidor.ultimas_trocas,
                    "final": final, "motivo_cru": motivo, "t_asr": round(t_asr, 3), "t_polimento": round(t_pol, 3),
                    "t_total": round(time.perf_counter() - soltou, 3), "colou": ok, "resultado": resultado,
                    "volume": medir_volume(audio, taxa)}
        if self.cfg["historico"] and not self.arquivo_teste and not entregar:
            registro["arquivo"] = str(historico.salvar(audio, taxa, registro))
        self.ultimo = registro
        self.avisar("ditado", registro)
