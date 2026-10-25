"""Atalho de segurar-para-falar (gancho global de teclado, no Windows e no Mac).

O gancho roda numa thread própria e só empurra eventos para uma fila: nada pesado acontece nele,
senão o sistema atrasa o teclado inteiro. O que é de cada sistema (leitor de teclado, menu Iniciar, Ctrl/Cmd+V)
mora em plataforma; GRUPOS diz quais teclas físicas contam como "ctrl", "win" (Command no Mac), "alt" etc.
"""
from . import plataforma

GRUPOS = plataforma.GRUPOS

# nomes antigos, usados por ferramentas de teste
esperar_modificadores_soltos = plataforma.esperar_modificadores_soltos
ctrl_v = plataforma.colar_atalho


class Atalho:
    """Chama ao_apertar() quando todas as teclas do atalho estão pressionadas e ao_soltar() quando uma sai."""

    def __init__(self, nomes, ao_apertar, ao_soltar):
        desconhecidos = [n for n in nomes if n not in GRUPOS]
        if desconhecidos:
            raise ValueError(f"tecla de atalho desconhecida: {desconhecidos} (use {sorted(GRUPOS)})")
        self.nomes = list(nomes)
        self.grupos = [GRUPOS[n] for n in nomes]
        self.ao_apertar, self.ao_soltar = ao_apertar, ao_soltar
        self.apertadas = set()
        self.ativo = False
        self.ouvinte = plataforma.ouvinte_teclado(self._press, self._release)

    def _completo(self):
        return all(self.apertadas & g for g in self.grupos)

    def _press(self, tecla):
        self.apertadas.add(tecla)
        if not self.ativo and self._completo():
            self.ativo = True
            if "win" in self.nomes:
                plataforma.mascarar_menu_iniciar()
            self.ao_apertar()

    def _release(self, tecla):
        self.apertadas.discard(tecla)
        if self.ativo and not self._completo():
            self.ativo = False
            self.ao_soltar()

    def iniciar(self):
        self.ouvinte.start()

    def parar(self):
        self.ouvinte.stop()
