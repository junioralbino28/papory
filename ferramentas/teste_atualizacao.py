"""Confere a atualização contra o GitHub de verdade, sem instalar nada.

Finge ser uma versão antiga, acha a mais nova, baixa conferindo o SHA-256 e prova que um arquivo com
impressão digital errada é recusado e apagado.
uso:  python ferramentas/teste_atualizacao.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.stdout.reconfigure(encoding="utf-8")

from papory import atualizacao as at  # noqa: E402

falhas = 0


def confere(nome, obtido, esperado):
    global falhas
    ok = obtido == esperado
    falhas += not ok
    print(f"{'ok ' if ok else 'ERRO'} {nome}: {obtido!r}" + ("" if ok else f"  (esperava {esperado!r})"))


confere("0.1.11 > 0.1.10", at.versao_tupla("v0.1.11") > at.versao_tupla("0.1.10"), True)
confere("igual não é mais nova", at.versao_tupla("v0.1.7") > at.versao_tupla("0.1.7"), False)
nomes = ["Papory-0.1.7-Mac-Apple-Silicon.dmg", "Papory-0.1.7-Mac-Intel.dmg", "Papory-Setup-0.1.7.exe"]
if sys.platform == "win32":
    confere("arquivo do Windows", at.arquivo_deste_sistema(nomes), "Papory-Setup-0.1.7.exe")

nova = at.procurar(atual="0.0.1")
confere("achou versão nova", nova is not None, True)
print(f"   versão {nova['versao']} · {nova['nome']} · {nova['tamanho'] / 1e6:.1f} MB · sha256 {nova['sha256'][:12]}…")
confere("já na mais nova: nada a oferecer", at.procurar(atual=nova["versao"]), None)

marcas = []
caminho = at.baixar(nova, lambda feito, total: marcas.append(feito))
confere("baixou inteiro", caminho.stat().st_size, nova["tamanho"])
confere("andamento informado", len(marcas) > 10 and marcas[-1] == nova["tamanho"], True)

falsa = dict(nova, sha256="0" * 64)
try:
    at.baixar(falsa)
    confere("impressão digital errada recusada", False, True)
except ValueError as e:
    confere("impressão digital errada recusada", "não confere" in str(e), True)
confere("arquivo recusado foi apagado", (at.PASTA / nova["nome"]).exists(), False)

try:
    at.baixar(nova, parar=lambda: True)
except InterruptedError:
    confere("dá para cancelar", True, True)

print("\nTUDO CERTO" if not falhas else f"\n{falhas} FALHA(S)")
sys.exit(1 if falhas else 0)
