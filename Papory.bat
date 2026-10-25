@echo off
rem Abre o Papory: segure Ctrl+Win, fale e solte. Feche esta janela (ou Ctrl+C) para sair.
title Papory
cd /d "%~dp0"
".venv-dml\Scripts\python.exe" -X utf8 -m papory
pause
