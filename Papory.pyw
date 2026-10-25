"""Abre o Papory sem janela de terminal (atalho da Área de Trabalho e "Iniciar com o Windows")."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from papory.__main__ import main  # noqa: E402

sys.exit(main())
