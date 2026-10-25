"""Entrada do papory-terminal.exe: o mesmo app, sempre no modo terminal (diagnóstico e autoteste)."""
import sys

from papory.__main__ import main

if "--terminal" not in sys.argv:
    sys.argv.insert(1, "--terminal")
sys.exit(main())
