# Monta a pasta do Papory: Papory.exe (sem terminal) + papory-terminal.exe (diagnóstico), lado a lado.
#   pyinstaller empacotar/papory.spec --noconfirm --distpath empacotar/dist --workpath empacotar/build
# O modelo de voz NÃO entra: a primeira abertura baixa do Hugging Face.
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs, collect_submodules, copy_metadata

RAIZ = Path(SPECPATH).parent
ICONE = str(RAIZ / "marca" / "papory.ico")

DADOS = [
    (str(RAIZ / "papory" / "interface" / "fontes"), "papory/interface/fontes"),
    (str(RAIZ / "papory" / "interface" / "imagens"), "papory/interface/imagens"),
    (str(RAIZ / "papory" / "palavras_comuns.txt"), "papory"),
    *collect_data_files("onnx_asr"),
    # bibliotecas que perguntam a própria versão ao iniciar (importlib.metadata)
    *copy_metadata("onnx-asr"), *copy_metadata("huggingface_hub"), *copy_metadata("onnxruntime-directml"),
    *copy_metadata("tqdm"), *copy_metadata("requests"),
]
OCULTOS = [*collect_submodules("onnx_asr"), "pynput.keyboard._win32", "pynput.mouse._win32", "win32clipboard",
           "win32cred", "win32con", "hf_xet"]
FORA = ["tkinter", "matplotlib", "IPython", "jiwer", "faster_whisper", "ctranslate2", "torch", "pandas", "PIL",
        "papory.plataforma.mac",
        "PySide6.QtQml", "PySide6.QtQuick", "PySide6.QtPdf", "PySide6.QtOpenGL", "PySide6.QtOpenGLWidgets",
        "PySide6.QtSql", "PySide6.QtTest", "PySide6.QtXml", "PySide6.QtDBus", "PySide6.QtConcurrent",
        "PySide6.QtDesigner", "PySide6.QtHelp", "PySide6.QtPrintSupport", "PySide6.QtUiTools"]


def _sem_peso_morto(lista):
    """Tira traduções do Qt e o OpenGL por software (o Papory desenha tudo sem OpenGL)."""
    return [t for t in lista if "translations" not in t[0].replace("\\", "/") and "opengl32sw" not in t[0].lower()]


def analisar(script):
    a = Analysis([str(script)], pathex=[str(RAIZ)], binaries=collect_dynamic_libs("onnxruntime"), datas=DADOS,
                 hiddenimports=OCULTOS, excludes=FORA, noarchive=False)
    a.binaries = _sem_peso_morto(a.binaries)
    a.datas = _sem_peso_morto(a.datas)
    return a


app = analisar(RAIZ / "Papory.pyw")
term = analisar(RAIZ / "empacotar" / "papory_terminal.py")

exe_app = EXE(PYZ(app.pure), app.scripts, [], exclude_binaries=True, name="Papory", icon=ICONE, console=False,
              upx=False)
exe_term = EXE(PYZ(term.pure), term.scripts, [], exclude_binaries=True, name="papory-terminal", icon=ICONE,
               console=True, upx=False)

COLLECT(exe_app, app.binaries, app.datas, exe_term, term.binaries, term.datas, name="Papory", upx=False)
