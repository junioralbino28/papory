"""Confere a lógica da calibração com leituras montadas à mão (sem microfone, sem modelo de voz).

Roda numa pasta de dados temporária: não mexe na configuração nem nas correções de verdade.
uso:  python ferramentas/teste_calibracao.py
"""
import os
import sys
import tempfile
from copy import deepcopy
from pathlib import Path

os.environ["PAPORY_DADOS"] = tempfile.mkdtemp(prefix="papory-calib-")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.stdout.reconfigure(encoding="utf-8")

from papory import calibracao as cal  # noqa: E402
from papory import config  # noqa: E402
from papory.motor import aplicar_substituicoes  # noqa: E402

falhas = 0


def confere(nome, obtido, esperado):
    global falhas
    ok = obtido == esperado
    falhas += not ok
    print(f"{'ok ' if ok else 'ERRO'} {nome}: {obtido!r}" + ("" if ok else f"  (esperava {esperado!r})"))


termos = cal.separar_termos("Lumora Hub, Zaptalk; lumora hub,  ")
confere("termos", termos, ["Lumora Hub", "Zaptalk"])
frases = cal.montar_frases(termos)
confere("quantas frases", len(frases), 8)
confere("frase com termo", frases[6]["texto"], "Hoje eu falei sobre Lumora Hub na reunião.")
confere("frases com 3 termos", [f["alvos"] for f in cal.montar_frases(["A", "B", "C"])[6:]], [["A", "B"], ["C"]])

leituras = {  # frase -> (o que o reconhecimento ouviu, o que o Papory entregaria)
    0: ("Oi, aqui é o papore, o ditado por voz que roda no meu computador.",) * 2,
    1: ("Me manda o link pelo uatsap qui eu respondo ainda hoje.",) * 2,
    2: ("Amanhã de manhã eu preciso mandar o relatório para a equipe.",) * 2,
    3: ("Vou postar o vídeo no Instagram e no YouTube depois do almoço.",
        "Vou postar o vídeo no Instagram e no Youtube depois do almoço."),  # o polimento estragou o YouTube
    4: ("Será que dá para marcar a reunião para quinta feira à tarde?",) * 2,
    5: ("Anota aí, comprar pão, leiti e café, e ligar pro banco.",) * 2,
    6: ("Hoje eu falei sobre lumora hab na reunião.",) * 2,
    7: ("Me lembra de conferir Zaptalk antes do fim do dia.",) * 2,
}
resultados = [cal.avaliar(frases[i], cru, final) for i, (cru, final) in leituras.items()]
confere("papore", resultados[0]["erros_alvo"], [("papore", "Papory")])
confere("uatsap (sem levar o 'qui' junto)", resultados[1]["erros_alvo"], [("uatsap", "WhatsApp")])
confere("frase certa", (resultados[2]["acertos"], resultados[2]["total"], resultados[2]["erros_alvo"]), (11, 11, []))
confere("YouTube estragado depois", resultados[3]["faltou_no_final"], ["YouTube"])
confere("hífen não é erro", (resultados[4]["acertos"], resultados[4]["total"]), (12, 12))
confere("palavra comum", resultados[5]["comuns"], [("leiti", "leite")])
confere("termo de duas palavras", resultados[6]["erros_alvo"], [("lumora hab", "Lumora Hub")])

cfg = deepcopy(config.PADRAO)
proposta = cal.propor(cfg, resultados, termos)
confere("regras propostas", proposta["regras"], [("papore", "Papory"), ("uatsap", "WhatsApp"),
                                                 ("lumora hab", "Lumora Hub")])
confere("vocabulário proposto", proposta["vocabulario"],
        ["Lumora Hub", "Zaptalk", "Papory", "WhatsApp", "YouTube"])
confere("todas vêm marcadas (nenhuma mexe em palavra comum)", proposta["marcadas"], proposta["regras"])
feito = cal.aplicar(cfg, proposta)
confere("aprendeu", (len(feito["regras"]), len(feito["vocabulario"])), (3, 5))
confere("ditado seguinte: papore", aplicar_substituicoes("Papore, abre o papore aí.", cfg, "x"),
        "Papory, abre o Papory aí.")
confere("ditado seguinte: uatsap", aplicar_substituicoes("manda no uatsap", cfg, "x"), "manda no WhatsApp")
confere("ditado seguinte: lumora hab", aplicar_substituicoes("a Lumora Hab cresceu", cfg, "x"),
        "a Lumora Hub cresceu")
confere("não troca dentro de palavra", aplicar_substituicoes("papores", cfg, "x"), "papores")
confere("2ª calibração não duplica", cal.propor(cfg, resultados, termos)["regras"], [])
confere("leiti conta 1 vez (não vira regra)", any(s.get("de") == "leiti" for s in cfg["substituicoes"]), False)

comum = cal.avaliar(cal.montar_frases(["Lumora"])[6], *("Hoje eu falei sobre uma hora na reunião.",) * 2)
cfg2 = deepcopy(config.PADRAO)
p2 = cal.propor(cfg2, [comum], ["Lumora"])
confere("'uma hora' no lugar de termo: proposta", p2["regras"], [("uma hora", "Lumora")])
confere("'uma hora' vem desmarcada", p2["marcadas"], [])
cal.aplicar(cfg2, p2)
confere("sem marcar, 'uma hora' continua intacta", aplicar_substituicoes("daqui a uma hora", cfg2, "x"),
        "daqui a uma hora")
confere("palavra rara não é comum", (cal.so_palavras_comuns("papore"), cal.so_palavras_comuns("Vhatzep")),
        (False, False))
confere("palavras comuns", (cal.so_palavras_comuns("uma hora"), cal.so_palavras_comuns("noção")), (True, True))

confere("volume bom", cal.veredito_volume([{"fala": 0.1, "saturado": 0.0}] * 3), "bom")
confere("volume baixo", cal.veredito_volume([{"fala": 0.005, "saturado": 0.0}] * 3), "baixo")
confere("volume estourando", cal.veredito_volume([{"fala": 0.4, "saturado": 0.02}] * 3), "alto")
confere("sem leitura", cal.veredito_volume([None]), None)

print("\nTUDO CERTO" if not falhas else f"\n{falhas} FALHA(S)")
sys.exit(1 if falhas else 0)
