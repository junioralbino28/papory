"""Escolhe as peças do sistema em que o Papory está rodando (Windows ou Mac). O resto do app só fala com isto."""
import sys

if sys.platform == "win32":
    from .windows import *  # noqa: F401,F403
elif sys.platform == "darwin":
    from .mac import *  # noqa: F401,F403
else:
    raise SystemExit("O Papory roda no Windows e no Mac.")
