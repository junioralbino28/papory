"""Papory — ditado por voz: segure o atalho (padrão Ctrl+Win; Control+Command no Mac), fale, solte — o texto é
colado onde o cursor está.

uso:  python -m papory                      (app normal: bandeja, pílula e janela)
      python -m papory --terminal           (sem janelas, mostrando tudo no terminal)
      python -m papory --arquivo-teste x.wav --uma-vez   (teste: usa um WAV no lugar do microfone)
"""
import argparse
import json
import sys
import threading
import time

from . import __version__, config, plataforma
from .motor import Motor


def terminal(a):
    if sys.stdout is not None:
        sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
    cfg = config.carregar()
    if a.sem_polimento:
        cfg["polimento"]["ativo"] = False
    if a.com_reforco:
        cfg["reforco_nuvem"]["ativo"] = True
    if a.so_local:
        cfg["reforco_nuvem"]["ativo"] = False
    print(f"Papory {__version__} — configuração: {config.ARQUIVO}")
    fim = threading.Event()

    def avisar(evento, dados=None):
        if evento == "carregando":
            print(f"  carregando {dados}…")
        elif evento == "ouvindo":
            print(f"\n● ouvindo… ({dados or '?'})")
        elif evento == "silencio":
            print(f"  (nada reconhecido em {dados} s de áudio)")
            if a.uma_vez:
                fim.set()
        elif evento == "copiado":
            print(f"  !! não consegui colar na janela onde você falou: o texto ficou copiado, cole com {plataforma.COLAR}")
        elif evento in ("aviso", "erro"):
            print(f"  !! {dados}")
        elif evento == "sem_microfone":
            print("  !! nenhum microfone disponível")
        elif evento == "ditado":
            r = dados
            print(f"  fala {r['duracao_s']:.1f} s → reconhecimento {r['t_asr']:.2f} s"
                  f"{' (+2ª transcrição)' if r['segunda_opiniao'] else ''}, polimento {r['polimento'] or 'nenhum'} "
                  f"{r['t_polimento']:.2f} s{' (' + r['motivo_cru'] + ')' if r['motivo_cru'] else ''}, "
                  f"total desde soltar {r['t_total']:.2f} s{'' if r['colou'] else '  !! não consegui colar'}")
            print(f"  » {r['final']}")
            if a.uma_vez:
                if motor.ultima_restauracao:
                    motor.ultima_restauracao.join()  # sair antes mataria a devolução da área de transferência
                print("RESULTADO " + json.dumps(r, ensure_ascii=False))
                fim.set()

    autoteste = bool(a.arquivo_teste and a.sem_colar)  # sem teclado e sem colar: dá para rodar sem ninguém
    motor = Motor(cfg, avisar, arquivo_teste=a.arquivo_teste, com_atalho=not autoteste)
    if a.sem_colar:
        motor.entregar = lambda texto: None  # o texto sai só no terminal; nada vai para a área de transferência
    motor.carregar()
    if not motor.pronto:
        return 1
    d = motor.descricao()
    print(f"  microfone: {d['microfone']}\n  reconhecimento: Parakeet {'na' if 'placa' in d['voz'] else 'no'} {d['voz']}\n  polimento: {d['polimento']}\n"
          f"  reforço na nuvem: {d['reforco']}")
    if autoteste:
        motor._eventos.put("apertou")
        time.sleep(0.3)
        motor._eventos.put("soltou")
    else:
        print(f"\nPronto. Segure {' + '.join(t.capitalize() for t in cfg['atalho'])}, fale e solte. "
              "(Ctrl+C aqui para sair)")
    try:
        while not fim.wait(0.5):
            pass
    except KeyboardInterrupt:
        pass
    motor.parar()
    return 0


def main():
    ap = argparse.ArgumentParser(prog="papory")
    ap.add_argument("--terminal", action="store_true", help="roda sem janelas, mostrando tudo no terminal")
    ap.add_argument("--arquivo-teste", help="usa este WAV no lugar do microfone")
    ap.add_argument("--uma-vez", action="store_true", help="sai depois do primeiro ditado (para testes)")
    ap.add_argument("--sem-colar", action="store_true",
                    help="não cola: só mostra o texto (com --arquivo-teste, roda sozinho, sem teclado)")
    ap.add_argument("--sem-polimento", action="store_true")
    ap.add_argument("--com-reforco", action="store_true", help="liga o reforço na nuvem só nesta execução")
    ap.add_argument("--so-local", action="store_true", help="desliga o reforço na nuvem só nesta execução")
    ap.add_argument("--escondido", action="store_true", help="abre só o ícone (ao iniciar com o sistema)")
    ap.add_argument("--primeira-abertura", action="store_true", help="mostra a primeira abertura de novo")
    ap.add_argument("--sem-motor", action="store_true", help="só a interface, sem carregar a voz (para testes)")
    ap.add_argument("--atualizar-agora", action="store_true",
                    help="procura versão nova e, se houver, baixa e instala na hora (para testes)")
    a = ap.parse_args()
    if a.terminal or a.arquivo_teste or a.uma_vez:
        return terminal(a)
    from .interface.app import rodar
    return rodar(a)


if __name__ == "__main__":
    sys.exit(main())
