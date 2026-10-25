"""Peças que falam direto com o macOS: teclado (Quartz), área de transferência (NSPasteboard), app da frente
(NSWorkspace), Keychain, LaunchAgent e som.

O macOS pede duas permissões para o Papory funcionar: Acessibilidade (ouvir o atalho e mandar o Cmd+V) e
Microfone. Sem Acessibilidade o texto fica copiado em vez de colado.
"""
import os
import plistlib
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path

from AppKit import (NSApplicationActivateIgnoringOtherApps, NSPasteboard, NSPasteboardItem, NSPasteboardTypeString,
                    NSRunningApplication, NSSound, NSWorkspace)
import CoreFoundation as CF
from Foundation import NSData
from Quartz import (CGEventCreateKeyboardEvent, CGEventGetFlags, CGEventGetIntegerValueField, CGEventMaskBit, CGEventPost,
                    CGEventSetFlags, CGEventSourceFlagsState, CGEventTapCreate, CGEventTapEnable,
                    kCGEventFlagMaskAlternate, kCGEventFlagMaskCommand, kCGEventFlagMaskControl,
                    kCGEventFlagMaskShift, kCGEventFlagsChanged, kCGEventKeyDown, kCGEventKeyUp,
                    kCGEventSourceStateHIDSystemState, kCGEventTapDisabledByTimeout, kCGEventTapDisabledByUserInput,
                    kCGEventTapOptionListenOnly, kCGHeadInsertEventTap, kCGHIDEventTap, kCGKeyboardEventKeycode,
                    kCGSessionEventTap)

NOME = "Mac"
TECLAS = {"ctrl": "Control", "win": "Command", "shift": "Shift", "alt": "Option", "alt_gr": "Option direito"}
OUTRO_APP_ATALHO = "o Wispr Flow no Mac usa Fn"
ICONE_FICA = "Abre escondido, só o ícone na barra de menus."
ONDE_ICONE = "no ícone da barra de menus, lá em cima"
ONDE_PILULA = "acima do Dock"
COLAR = "Cmd+V"

# apps conhecidos pelo identificador do pacote → o mesmo nome curto que o Windows usa (vale para as trocas por app)
PACOTES = {"com.microsoft.VSCode": "code", "com.todesktop.230313mzl4w4u92": "cursor", "com.apple.Terminal": "terminal",
           "com.googlecode.iterm2": "terminal", "net.whatsapp.WhatsApp": "whatsapp", "com.google.Chrome": "chrome",
           "com.apple.Safari": "safari", "org.mozilla.firefox": "firefox", "com.anthropic.claudefordesktop": "claude",
           "com.apple.Notes": "notas", "com.tinyspeck.slackmacgap": "slack", "com.microsoft.Word": "winword",
           "com.microsoft.Outlook": "outlook", "com.apple.mail": "mail", "com.apple.TextEdit": "textedit"}


def pasta_dados():
    if os.environ.get("PAPORY_DADOS"):  # testes usam uma pasta temporária
        return Path(os.environ["PAPORY_DADOS"])
    return Path.home() / "Library" / "Application Support" / "Papory"


# ---------------------------------------------------------------- teclado
# códigos físicos das teclas do Mac que contam para cada nome de atalho ("win" = Command, "alt" = Option)
GRUPOS = {"ctrl": {59, 62}, "win": {55, 54}, "shift": {56, 60}, "alt": {58}, "alt_gr": {61},
          **{f"f{n}": {c} for n, c in enumerate((122, 120, 99, 118, 96, 97, 98, 100, 101, 109, 103, 111), start=1)}}
# bit de cada tecla modificadora (esquerda e direita separadas) nas flags do evento
LADO = {59: 0x01, 62: 0x2000, 56: 0x02, 60: 0x04, 55: 0x08, 54: 0x10, 58: 0x20, 61: 0x40}


class OuvinteTeclado:
    """Escuta o teclado do sistema só para ler (não segura nenhuma tecla), pelo código físico das teclas.

    Não usa o pynput: ele traduz tecla em letra fora da thread principal, o que o macOS 14+ não aceita.
    O atalho só precisa dos modificadores e das teclas F, que não exigem tradução nenhuma.
    """

    def __init__(self, ao_apertar, ao_soltar):
        self.ao_apertar, self.ao_soltar = ao_apertar, ao_soltar
        self.gancho = self.laco = None
        self._resposta = self._evento  # o macOS guarda só um ponteiro: a referência fica aqui
        self.thread = threading.Thread(target=self._rodar, daemon=True, name="teclado")

    def start(self):
        self.thread.start()

    def stop(self):
        if self.laco is not None:
            CF.CFRunLoopStop(self.laco)

    def _rodar(self):
        mascara = CGEventMaskBit(kCGEventKeyDown) | CGEventMaskBit(kCGEventKeyUp) | CGEventMaskBit(kCGEventFlagsChanged)
        self.gancho = CGEventTapCreate(kCGSessionEventTap, kCGHeadInsertEventTap, kCGEventTapOptionListenOnly, mascara,
                                       self._resposta, None)
        if self.gancho is None:
            print("teclado: o macOS não deixou ouvir o atalho (falta a permissão de Monitoramento de Entrada)")
            return
        self.laco = CF.CFRunLoopGetCurrent()
        CF.CFRunLoopAddSource(self.laco, CF.CFMachPortCreateRunLoopSource(None, self.gancho, 0), CF.kCFRunLoopCommonModes)
        CGEventTapEnable(self.gancho, True)
        print("teclado: ouvindo o atalho")
        CF.CFRunLoopRun()

    def _evento(self, _proxy, tipo, evento, _refcon):
        try:
            if tipo in (kCGEventTapDisabledByTimeout, kCGEventTapDisabledByUserInput):
                CGEventTapEnable(self.gancho, True)  # o sistema desliga o gancho que demora; religa
            else:
                codigo = CGEventGetIntegerValueField(evento, kCGKeyboardEventKeycode)
                if tipo == kCGEventFlagsChanged:
                    if codigo in LADO:
                        (self.ao_apertar if CGEventGetFlags(evento) & LADO[codigo] else self.ao_soltar)(codigo)
                elif tipo == kCGEventKeyDown:
                    self.ao_apertar(codigo)
                elif tipo == kCGEventKeyUp:
                    self.ao_soltar(codigo)
        except Exception as e:  # noqa: BLE001 — erro aqui não pode derrubar o gancho do sistema
            print("teclado:", e)
        return evento


def ouvinte_teclado(ao_apertar, ao_soltar):
    return OuvinteTeclado(ao_apertar, ao_soltar)


MASCARA_MODIFICADORES = kCGEventFlagMaskShift | kCGEventFlagMaskControl | kCGEventFlagMaskAlternate | kCGEventFlagMaskCommand
TECLA_V = 9  # código físico da tecla V no teclado do Mac


def mascarar_menu_iniciar():
    pass  # só existe no Windows


def esperar_modificadores_soltos(limite_s=1.5):
    """Colar com Control ainda apertado viraria Control+Cmd+V."""
    fim = time.monotonic() + limite_s
    while time.monotonic() < fim:
        if not CGEventSourceFlagsState(kCGEventSourceStateHIDSystemState) & MASCARA_MODIFICADORES:
            return True
        time.sleep(0.02)
    return False


def colar_atalho():
    for desce in (True, False):
        ev = CGEventCreateKeyboardEvent(None, TECLA_V, desce)
        CGEventSetFlags(ev, kCGEventFlagMaskCommand)
        CGEventPost(kCGHIDEventTap, ev)


def pode_colar():
    """Sem a permissão de Acessibilidade, o macOS ignora o Cmd+V enviado em silêncio."""
    try:
        from ApplicationServices import AXIsProcessTrusted
        return bool(AXIsProcessTrusted())
    except Exception:  # noqa: BLE001
        return False


def estado_permissoes():
    """{nome nos ajustes do Mac: liberada?}, sem abrir pedido nenhum."""
    estado = {}
    try:
        from Quartz import CGPreflightListenEventAccess
        estado["Monitoramento de Entrada"] = bool(CGPreflightListenEventAccess())
    except Exception:  # noqa: BLE001 — macOS sem essa permissão separada
        pass
    estado["Acessibilidade"] = pode_colar()
    return estado


def pedir_permissoes():
    """Abre os pedidos do macOS que ainda faltam e devolve os nomes deles (como aparecem nos ajustes do Mac).

    Monitoramento de Entrada: ouvir o atalho. Acessibilidade: mandar o Cmd+V que cola o texto.
    """
    estado = estado_permissoes()
    print(f"permissões ao abrir: {estado}")
    faltam = [nome for nome, ok in estado.items() if not ok]
    try:
        if "Monitoramento de Entrada" in faltam:
            from Quartz import CGRequestListenEventAccess
            CGRequestListenEventAccess()
        if "Acessibilidade" in faltam:
            from ApplicationServices import AXIsProcessTrustedWithOptions, kAXTrustedCheckOptionPrompt
            AXIsProcessTrustedWithOptions({kAXTrustedCheckOptionPrompt: True})
    except Exception as e:  # noqa: BLE001
        print("permissões: não consegui abrir o pedido:", e)
    return faltam


# ---------------------------------------------------- área de transferência
MARCAS_TRANSITORIAS = ["org.nspasteboard.TransientType", "org.nspasteboard.ConcealedType"]  # gerenciadores ignoram


def _quadro():
    return NSPasteboard.generalPasteboard()


def guardar():
    """Todos os itens e tipos (texto, imagem, arquivos...) para devolver depois de colar."""
    salvo = []
    for item in _quadro().pasteboardItems() or []:
        tipos = {}
        for t in item.types():
            dado = item.dataForType_(t)
            if dado is not None:
                tipos[str(t)] = bytes(dado)
        salvo.append(tipos)
    return salvo


def restaurar(salvo):
    q = _quadro()
    q.clearContents()
    if not salvo:
        return True
    itens = []
    for tipos in salvo:
        item = NSPasteboardItem.alloc().init()
        for t, b in tipos.items():
            item.setData_forType_(NSData.dataWithBytes_length_(b, len(b)), t)
        itens.append(item)
    return bool(q.writeObjects_(itens))


def escrever_texto(texto, fora_do_historico=False):
    q = _quadro()
    q.clearContents()
    tipos = [NSPasteboardTypeString] + (MARCAS_TRANSITORIAS if fora_do_historico else [])
    q.declareTypes_owner_(tipos, None)
    ok = q.setString_forType_(texto, NSPasteboardTypeString)
    for marca in tipos[1:]:
        q.setData_forType_(NSData.data(), marca)
    return bool(ok)


def limpar():
    _quadro().clearContents()


def ler_texto():
    t = _quadro().stringForType_(NSPasteboardTypeString)
    return str(t) if t is not None else None


# ------------------------------------------------------- app da frente
def janela_ativa():
    """(processo, título, pid). O título da janela pediria a permissão de Gravação de Tela; fica vazio."""
    app = NSWorkspace.sharedWorkspace().frontmostApplication()
    if app is None:
        return "", "", 0
    pacote, nome = str(app.bundleIdentifier() or ""), str(app.localizedName() or "")
    return PACOTES.get(pacote, nome.lower()), "", int(app.processIdentifier())


def trazer_de_volta(pid):
    atual = NSWorkspace.sharedWorkspace().frontmostApplication()
    if not pid or (atual is not None and int(atual.processIdentifier()) == pid):
        return True
    app = NSRunningApplication.runningApplicationWithProcessIdentifier_(pid)
    if app is None or app.isTerminated():
        return False
    app.activateWithOptions_(NSApplicationActivateIgnoringOtherApps)
    for _ in range(25):
        atual = NSWorkspace.sharedWorkspace().frontmostApplication()
        if atual is not None and int(atual.processIdentifier()) == pid:
            return True
        time.sleep(0.02)
    return False


# ----------------------------------------------------------------- cofre
def ler_credencial(nome):
    r = subprocess.run(["security", "find-generic-password", "-s", f"Papory/{nome}", "-a", "Papory", "-w"],
                       capture_output=True, text=True)
    return (r.stdout.strip() or None) if r.returncode == 0 else None


def guardar_credencial(nome, valor):
    """Keychain do macOS; valor vazio apaga."""
    if not valor:
        subprocess.run(["security", "delete-generic-password", "-s", f"Papory/{nome}", "-a", "Papory"],
                       capture_output=True)
        return
    subprocess.run(["security", "add-generic-password", "-U", "-s", f"Papory/{nome}", "-a", "Papory", "-w", valor],
                   capture_output=True, check=True)


# ------------------------------------------------------- iniciar com o sistema
AGENTE = Path.home() / "Library" / "LaunchAgents" / "com.papory.app.plist"


def comando_inicio():
    if getattr(sys, "frozen", False):
        return [sys.executable, "--escondido"]
    return [sys.executable, str(Path(__file__).resolve().parents[2] / "Papory.pyw"), "--escondido"]


def inicio_ligado():
    return AGENTE.exists()


def ligar_inicio(sim):
    if sim:
        AGENTE.parent.mkdir(parents=True, exist_ok=True)
        AGENTE.write_bytes(plistlib.dumps({"Label": "com.papory.app", "ProgramArguments": comando_inicio(),
                                           "RunAtLoad": True, "ProcessType": "Interactive"}))
    elif AGENTE.exists():
        AGENTE.unlink()


# ------------------------------------------------------------- miudezas
def bipe(freq, ms):
    """Sons do próprio Mac no lugar dos tons do Windows: agudo = começou, médio = terminou, grave = só copiou."""
    nome = "Tink" if freq >= 800 else "Pop" if freq >= 600 else "Basso"
    try:
        som = NSSound.soundNamed_(nome)
        if som is not None:
            som.stop()
            som.play()
    except Exception:  # noqa: BLE001 — sem saída de som, segue sem bipe
        pass


def abrir(caminho):
    subprocess.run(["open", str(caminho)], check=False)


def ollama_app():
    app = Path("/Applications/Ollama.app")
    if app.exists():
        return app
    achado = shutil.which("ollama")
    return Path(achado) if achado else None


def abrir_programa(caminho):
    subprocess.Popen(["open", str(caminho)])


def ajustar_pilula(janela):
    pass  # no Mac a janela-ferramenta sem foco do Qt já não rouba o foco


def identidade_app():
    pass
