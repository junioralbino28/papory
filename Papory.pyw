"""Abre o Papory sem janela de terminal (atalho da Área de Trabalho e "Iniciar com o Windows")."""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))


def _texto(erro):
    partes = []
    while erro is not None and len(partes) < 5:
        partes.append(str(erro))
        erro = erro.__cause__ or erro.__context__
    return " ".join(partes)


# Logo depois de instalar ou atualizar, o antivírus ainda examina as DLLs novas e o Windows recusa carregá-las
# ("o arquivo já está sendo usado por outro processo"). Passa em poucos segundos: espera e tenta de novo. O Python
# tira do sys.modules o que falhou no meio, então a nova tentativa importa do zero só o que faltou.
inicio, sys.papory_esperas = time.monotonic(), 0  # o registro do app conta as esperas
while True:
    try:
        from papory.__main__ import main  # noqa: E402
        break
    except ImportError as e:
        if "DLL load failed" not in _texto(e) or time.monotonic() - inicio > 20:
            raise
        sys.papory_esperas += 1
        time.sleep(0.5)

sys.exit(main())
