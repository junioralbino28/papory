# Monta o Papory.app para o Mac (no próprio Mac). Diagnóstico: Papory.app/Contents/MacOS/Papory --terminal
#   pyinstaller empacotar/papory-mac.spec --noconfirm --distpath empacotar/dist --workpath empacotar/build
# O modelo de voz NÃO entra: a primeira abertura baixa do Hugging Face.
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs, collect_submodules, copy_metadata

RAIZ = Path(SPECPATH).parent
ICONE = str(RAIZ / "marca" / "papory.icns")
VERSAO = (RAIZ / "papory" / "__init__.py").read_text(encoding="utf-8").split('__version__ = "')[1].split('"')[0]

DADOS = [
    (str(RAIZ / "papory" / "interface" / "fontes"), "papory/interface/fontes"),
    (str(RAIZ / "papory" / "interface" / "imagens"), "papory/interface/imagens"),
    (str(RAIZ / "papory" / "palavras_comuns.txt"), "papory"),
    (str(RAIZ / "papory" / "sons"), "papory/sons"),
    (str(RAIZ / "mac" / "assinar-papory.sh"), "."),   # vira Papory.app/Contents/Resources/assinar-papory.sh
    *collect_data_files("onnx_asr"),
    # bibliotecas que perguntam a própria versão ao iniciar (importlib.metadata)
    *copy_metadata("onnx-asr"), *copy_metadata("huggingface_hub"), *copy_metadata("onnxruntime"),
    *copy_metadata("tqdm"), *copy_metadata("requests"),
]
OCULTOS = [*collect_submodules("onnx_asr"), "papory.plataforma.mac", "AppKit", "Foundation", "Quartz", "CoreFoundation",
           "ApplicationServices", "hf_xet"]
FORA = ["tkinter", "matplotlib", "IPython", "jiwer", "faster_whisper", "ctranslate2", "torch", "pandas", "PIL",
        "papory.plataforma.windows", "pynput",
        "PySide6.QtQml", "PySide6.QtQuick", "PySide6.QtPdf", "PySide6.QtOpenGL", "PySide6.QtOpenGLWidgets",
        "PySide6.QtSql", "PySide6.QtTest", "PySide6.QtXml", "PySide6.QtDBus", "PySide6.QtConcurrent",
        "PySide6.QtDesigner", "PySide6.QtHelp", "PySide6.QtPrintSupport", "PySide6.QtUiTools"]


def _sem_peso_morto(lista):
    """Tira as traduções do Qt (o Papory tem os próprios textos)."""
    return [t for t in lista if "translations" not in t[0]]


app = Analysis([str(RAIZ / "Papory.pyw")], pathex=[str(RAIZ)], binaries=collect_dynamic_libs("onnxruntime"),
               datas=DADOS, hiddenimports=OCULTOS, excludes=FORA, noarchive=False)
app.binaries = _sem_peso_morto(app.binaries)
app.datas = _sem_peso_morto(app.datas)

exe = EXE(PYZ(app.pure), app.scripts, [], exclude_binaries=True, name="Papory", icon=ICONE, console=False,
          upx=False, argv_emulation=False)
pasta = COLLECT(exe, app.binaries, app.datas, name="Papory", upx=False)

BUNDLE(pasta, name="Papory.app", icon=ICONE, bundle_identifier="com.papory.app", version=VERSAO,
       info_plist={
           "CFBundleName": "Papory",
           "CFBundleDisplayName": "Papory",
           "CFBundleShortVersionString": VERSAO,
           "LSUIElement": True,                 # só o ícone na barra de menus, sem ícone no Dock
           "LSMinimumSystemVersion": "12.0",
           "NSHighResolutionCapable": True,
           "NSMicrophoneUsageDescription": "O Papory ouve o microfone só enquanto você segura o atalho, "
                                           "para transformar a sua fala em texto no próprio Mac.",
       })
