"""Peças que falam direto com o Windows: teclado, área de transferência, janela da frente, cofre, início, som."""
import ctypes
import os
import shutil
import subprocess
import sys
import time
import winreg
import winsound
from ctypes import wintypes
from pathlib import Path

import win32clipboard as wc
import win32con
from pynput import keyboard as kb

NOME = "Windows"
TECLAS = {"ctrl": "Ctrl", "win": "Win", "shift": "Shift", "alt": "Alt", "alt_gr": "AltGr"}
OUTRO_APP_ATALHO = "o Wispr Flow usa Ctrl + Win"
ICONE_FICA = "Abre escondido, só o ícone perto do relógio."
ONDE_ICONE = "aqui perto do relógio"
ONDE_PILULA = "acima da barra de tarefas"
COLAR = "Ctrl+V"

user32, kernel32 = ctypes.windll.user32, ctypes.windll.kernel32


def pasta_dados():
    if os.environ.get("PAPORY_DADOS"):  # testes usam uma pasta temporária
        return Path(os.environ["PAPORY_DADOS"])
    return Path(os.environ.get("APPDATA", Path.home())) / "Papory"


# ---------------------------------------------------------------- teclado
GRUPOS = {  # teclas do pynput que contam para cada nome de atalho
    "ctrl": {kb.Key.ctrl, kb.Key.ctrl_l, kb.Key.ctrl_r},
    "win": {kb.Key.cmd, kb.Key.cmd_l, kb.Key.cmd_r},
    "shift": {kb.Key.shift, kb.Key.shift_l, kb.Key.shift_r},
    "alt": {kb.Key.alt, kb.Key.alt_l},
    "alt_gr": {kb.Key.alt_gr, kb.Key.alt_r},
    **{f"f{n}": {getattr(kb.Key, f"f{n}")} for n in range(1, 13)},
}


def ouvinte_teclado(ao_apertar, ao_soltar):
    """Gancho global do pynput; ao_apertar/ao_soltar recebem a tecla (comparada com GRUPOS)."""
    return kb.Listener(on_press=ao_apertar, on_release=ao_soltar)


KEYEVENTF_KEYUP = 0x0002
VK_CONTROL, VK_V, VK_MASCARA = 0x11, 0x56, 0xE8  # 0xE8 = não atribuído; serve de "tecla fantasma"
MODIFICADORES = (0x10, 0x11, 0x12, 0x5B, 0x5C)    # shift, ctrl, alt, win esquerdo, win direito


def _tecla(vk, solta=False):
    user32.keybd_event(vk, 0, KEYEVENTF_KEYUP if solta else 0, 0)


def mascarar_menu_iniciar():
    """Toque da tecla fantasma: com ela no meio, soltar o Win não abre o menu Iniciar."""
    _tecla(VK_MASCARA)
    _tecla(VK_MASCARA, solta=True)


def esperar_modificadores_soltos(limite_s=1.5):
    """Colar com o Win ainda apertado viraria Win+V (histórico da área de transferência)."""
    fim = time.monotonic() + limite_s
    while time.monotonic() < fim:
        if not any(user32.GetAsyncKeyState(vk) & 0x8000 for vk in MODIFICADORES):
            return True
        time.sleep(0.02)
    return False


def colar_atalho():
    _tecla(VK_CONTROL)
    _tecla(VK_V)
    _tecla(VK_V, solta=True)
    _tecla(VK_CONTROL, solta=True)


def pode_colar():
    return True


def estado_permissoes():
    return {}  # o Windows não pede permissão para ouvir o teclado nem para colar


def pedir_permissoes():
    return []


# ---------------------------------------------------- área de transferência
FORMATOS_INTERNOS = {win32con.CF_BITMAP, win32con.CF_ENHMETAFILE, win32con.CF_METAFILEPICT,
                     win32con.CF_PALETTE, win32con.CF_OWNERDISPLAY}


def _abrir(tentativas=20):
    for _ in range(tentativas):
        try:
            wc.OpenClipboard()
            return True
        except Exception:  # noqa: BLE001 — outro app está com a área de transferência aberta
            time.sleep(0.02)
    return False


def guardar():
    """Todos os formatos legíveis (texto, imagem, arquivos...). Os que o Windows não deixa ler ficam de fora."""
    if not _abrir():
        return None
    salvo = []
    try:
        fmt = wc.EnumClipboardFormats(0)
        while fmt:
            if fmt not in FORMATOS_INTERNOS:
                try:
                    salvo.append((fmt, wc.GetClipboardData(fmt)))
                except Exception:  # noqa: BLE001
                    pass
            fmt = wc.EnumClipboardFormats(fmt)
    finally:
        wc.CloseClipboard()
    return salvo


def _escrever(itens):
    if not _abrir():
        return False
    try:
        wc.EmptyClipboard()
        for fmt, dado in itens:
            try:
                wc.SetClipboardData(fmt, dado)
            except Exception:  # noqa: BLE001
                pass
    finally:
        wc.CloseClipboard()
    return True


def escrever_texto(texto, fora_do_historico=False):
    itens = [(win32con.CF_UNICODETEXT, texto)]
    if fora_do_historico:  # não entra no histórico do Win+V
        itens.append((wc.RegisterClipboardFormat("ExcludeClipboardContentFromMonitorProcessing"), b"\x00\x00\x00\x00"))
    return _escrever(itens)


def limpar():
    if _abrir():
        try:
            wc.EmptyClipboard()
        finally:
            wc.CloseClipboard()


def restaurar(salvo):
    return _escrever(salvo) if salvo else limpar()


def ler_texto():
    if not _abrir():
        return None
    try:
        return wc.GetClipboardData(win32con.CF_UNICODETEXT) if wc.IsClipboardFormatAvailable(win32con.CF_UNICODETEXT) else None
    finally:
        wc.CloseClipboard()


# ------------------------------------------------------- janela da frente
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000


def janela_ativa():
    """(processo, título da janela, identificador da janela) do que está em primeiro plano."""
    hwnd = user32.GetForegroundWindow()
    n = user32.GetWindowTextLengthW(hwnd)
    buf = ctypes.create_unicode_buffer(n + 1)
    user32.GetWindowTextW(hwnd, buf, n + 1)
    pid = wintypes.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    processo = ""
    h = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid.value)
    if h:
        tam = wintypes.DWORD(1024)
        caminho = ctypes.create_unicode_buffer(1024)
        if kernel32.QueryFullProcessImageNameW(h, 0, caminho, ctypes.byref(tam)):
            processo = Path(caminho.value).stem.lower()
        kernel32.CloseHandle(h)
    return processo, buf.value, hwnd


def trazer_de_volta(hwnd):
    """Põe de novo na frente a janela onde a pessoa começou a falar. True se ela está na frente."""
    if not hwnd or user32.GetForegroundWindow() == hwnd:
        return True
    if not user32.IsWindow(hwnd):
        return False
    # O Windows só deixa trocar o foco depois de uma tecla; um toque de Alt libera a troca (truque conhecido).
    user32.keybd_event(0x12, 0, 0, 0)
    user32.keybd_event(0x12, 0, 0x0002, 0)
    if user32.IsIconic(hwnd):
        user32.ShowWindow(hwnd, 9)  # SW_RESTORE
    user32.SetForegroundWindow(hwnd)
    for _ in range(25):
        if user32.GetForegroundWindow() == hwnd:
            return True
        time.sleep(0.02)
    return False


# ----------------------------------------------------------------- cofre
def ler_credencial(nome):
    try:
        import win32cred
        c = win32cred.CredRead(f"Papory/{nome}", win32cred.CRED_TYPE_GENERIC)
        blob = c["CredentialBlob"]
        return (blob.decode("utf-16-le") if isinstance(blob, bytes) else str(blob)) or None
    except Exception:  # noqa: BLE001 — não existe
        return None


def guardar_credencial(nome, valor):
    """Gerenciador de Credenciais do Windows; valor vazio apaga."""
    import win32cred
    alvo = f"Papory/{nome}"
    if not valor:
        try:
            win32cred.CredDelete(alvo, win32cred.CRED_TYPE_GENERIC)
        except Exception:  # noqa: BLE001
            pass
        return
    win32cred.CredWrite({"Type": win32cred.CRED_TYPE_GENERIC, "TargetName": alvo, "UserName": "Papory",
                         "CredentialBlob": valor, "Persist": win32cred.CRED_PERSIST_LOCAL_MACHINE}, 0)


# ------------------------------------------------------- iniciar com o sistema
CHAVE_RUN = r"Software\Microsoft\Windows\CurrentVersion\Run"


def comando_inicio():
    """O .exe empacotado, ou o pythonw com o lançador Papory.pyw."""
    if getattr(sys, "frozen", False):
        return f'"{sys.executable}" --escondido'
    pythonw = Path(sys.executable).with_name("pythonw.exe")
    lancador = Path(__file__).resolve().parents[2] / "Papory.pyw"
    return f'"{pythonw}" "{lancador}" --escondido'


def inicio_ligado():
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, CHAVE_RUN) as k:
            winreg.QueryValueEx(k, "Papory")
            return True
    except OSError:
        return False


def ligar_inicio(sim):
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, CHAVE_RUN, 0, winreg.KEY_SET_VALUE) as k:
        if sim:
            winreg.SetValueEx(k, "Papory", 0, winreg.REG_SZ, comando_inicio())
        else:
            try:
                winreg.DeleteValue(k, "Papory")
            except OSError:
                pass


# ------------------------------------------------------------- miudezas
SONS = Path(__file__).resolve().parent.parent / "sons"


def tocar_som(nome):
    """Assobio do papagaio (comecou, terminou, copiou), sem esperar terminar. Um som novo corta o anterior."""
    try:
        winsound.PlaySound(str(SONS / f"{nome}.wav"),
                           winsound.SND_FILENAME | winsound.SND_ASYNC | winsound.SND_NODEFAULT)
    except RuntimeError:  # sem saída de som: segue sem
        pass


def abrir(caminho):
    os.startfile(caminho)


def ollama_app():
    base = Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Ollama"
    for nome in ("ollama app.exe", "ollama.exe"):
        if (base / nome).exists():
            return base / nome
    achado = shutil.which("ollama")
    return Path(achado) if achado else None


def abrir_programa(caminho):
    subprocess.Popen([str(caminho)], creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP)


def ajustar_pilula(janela):
    """WS_EX_NOACTIVATE: a pílula nunca rouba o foco de quem está escrevendo."""
    hwnd = int(janela.winId())
    gwl_exstyle, noactivate, toolwindow, topmost = -20, 0x08000000, 0x00000080, 0x00000008
    user32.SetWindowLongW(hwnd, gwl_exstyle, user32.GetWindowLongW(hwnd, gwl_exstyle) | noactivate | toolwindow | topmost)


def identidade_app():
    """Rodando pelo Python: identidade própria na barra de tarefas (senão aparece o ícone do Python).

    No Papory.exe instalado não liga: o .exe já é o próprio Papory, com o papagaio gravado dentro, e uma identidade
    explícita sem atalho que a declare faz o Windows mostrar o ícone genérico de programa.
    """
    if getattr(sys, "frozen", False):
        return
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("Papory.Ditado")
