"""Calibração: a pessoa lê frases curtas e o Papory aprende como ela fala.

Compara o que o reconhecimento ouviu com o texto que estava na tela:
- nome ou termo especial ouvido errado (os das frases e os que a pessoa escreveu) vira troca automática na hora,
  se o som for parecido, e entra no vocabulário. A pessoa confere a lista antes de salvar; troca que mexeria só
  em palavras comuns ("uma hora" no lugar de "Lumora") vem desmarcada;
- palavra comum ouvida errada só conta para o aprendizado normal, que pede a mesma correção duas vezes;
- o volume de cada leitura diz se o microfone está baixo demais ou estourando.
"""
import re
from difflib import SequenceMatcher
from pathlib import Path
from statistics import median

from . import aprendizado
from .aprendizado import _limpa, _no_vocabulario, sem_acento
from .polimento import _som

FRASES = [
    ("Oi, aqui é o Papory, o ditado por voz que roda no meu computador.", ["Papory"]),
    ("Me manda o link pelo WhatsApp que eu respondo ainda hoje.", ["WhatsApp"]),
    ("Amanhã de manhã eu preciso mandar o relatório para a equipe.", []),
    ("Vou postar o vídeo no Instagram e no YouTube depois do almoço.", ["Instagram", "YouTube"]),
    ("Será que dá para marcar a reunião para quinta-feira à tarde?", []),
    ("Anota aí: comprar pão, leite e café, e ligar para o banco.", []),
]
MODELOS_TERMO = [
    ("Hoje eu falei sobre {} na reunião.", "Hoje eu falei sobre {} e {} na reunião."),
    ("Me lembra de conferir {} antes do fim do dia.", "Me lembra de conferir {} e {} antes do fim do dia."),
]
MAX_TERMOS_NAS_FRASES = 4
SOM_PARECIDO = 0.5          # semelhança mínima entre o que ouviu e o termo para virar troca automática
FALA_BAIXA = 0.012          # volume típico da fala (RMS) abaixo disso: microfone baixo demais
SATURADO = 0.005            # fração de amostras no teto acima disso: som estourando
NOTA_REGRA = "aprendida lendo as frases"
ARQUIVO_COMUNS = Path(__file__).with_name("palavras_comuns.txt")
_comuns = None


def palavras_comuns():
    global _comuns
    if _comuns is None:
        try:
            linhas = ARQUIVO_COMUNS.read_text(encoding="utf-8").splitlines()
        except OSError:
            linhas = []
        _comuns = {p for p in linhas if p and not p.startswith("#")}
    return _comuns


def so_palavras_comuns(trecho):
    """'uma hora' -> True: uma troca automática nesse trecho estragaria o uso normal dele."""
    palavras = [_chave(p) for p in trecho.split()]
    return bool(palavras) and all(p in palavras_comuns() for p in palavras)


def separar_termos(texto):
    """'Lumora Hub, Zaptalk; Loja Azul' -> ['Lumora Hub', 'Zaptalk', 'Loja Azul'] (sem repetir, até 40 letras cada)."""
    termos = []
    for t in re.split(r"[,;\n]+", texto or ""):
        t = " ".join(t.split())[:40].strip()
        if t and t.lower() not in (x.lower() for x in termos):
            termos.append(t)
    return termos


def montar_frases(termos=()):
    """As frases fixas e, no fim, até duas com os termos da pessoa: [{"texto", "alvos"}, ...]."""
    frases = [{"texto": t, "alvos": list(a)} for t, a in FRASES]
    usados = list(termos)[:MAX_TERMOS_NAS_FRASES]
    grupos = [[t] for t in usados] if len(usados) <= 2 else [usados[:2], usados[2:]]
    for (um, dois), grupo in zip(MODELOS_TERMO, grupos):
        frases.append({"texto": (um if len(grupo) == 1 else dois).format(*grupo), "alvos": grupo})
    return frases


def _palavras(texto):
    return texto.split()


def _chave(palavra):
    return _limpa(palavra).lower()


def _normalizadas(texto):
    """Para a nota: sem acento, sem pontuação, hífen vira espaço (quinta-feira = quinta feira)."""
    return [p for p in (sem_acento(_chave(w)) for w in texto.replace("-", " ").split()) if p]


def _juntar(palavras):
    return " ".join(_limpa(p) for p in palavras).strip()


def _so_formato(a, b):
    """Diferença só de maiúscula, hífen ou espaço (não conta como erro de palavra comum)."""
    f = lambda s: re.sub(r"[\s-]+", "", s.lower())  # noqa: E731
    return f(a) == f(b)


def _parecido(a, b):
    sa, sb = _som(a), _som(b)
    return bool(sa) and (sa == sb or SequenceMatcher(None, sa, sb).ratio() >= SOM_PARECIDO)


def _trechos_dos_alvos(esperado, alvos):
    """Onde cada termo está no texto certo: [(alvo, início, fim)] em posições de palavra."""
    chaves = [_chave(p) for p in esperado]
    saida = []
    for alvo in alvos:
        partes = [_chave(p) for p in alvo.split()]
        for i in range(len(chaves) - len(partes) + 1):
            if chaves[i:i + len(partes)] == partes:
                saida.append((alvo, i, i + len(partes)))
                break
    return saida


def _mapear(opcodes, j, fim):
    """Posição j no texto certo -> (posição no texto ouvido, exata?). Num trecho trocado, vai até a borda dele."""
    for op, i1, i2, j1, j2 in opcodes:
        if (j1 < j <= j2) if fim else (j1 <= j < j2):
            if op == "equal":
                return i1 + (j - j1), True
            return (i2, j == j2) if fim else (i1, j == j1)
    return None, False


def _melhor_trecho(palavras, i1, i2, alvo):
    """O trecho trocado passa do termo ("uatsap qui" no lugar de "WhatsApp que"): fica com a parte que soa como ele."""
    n = len(alvo.split()) + 1
    candidatos = [(a, b) for a in range(i1, i2) for b in range(a + 1, min(i2, a + n) + 1)]
    if not candidatos:
        return i1, i2
    return max(candidatos, key=lambda c: (SequenceMatcher(None, _som(_juntar(palavras[c[0]:c[1]])), _som(alvo)).ratio(),
                                          -(c[1] - c[0])))


def _ouvido_nos_alvos(esperado, ouvido, alvos):
    """Para cada termo: o que foi ouvido no lugar dele (texto vazio se sumiu)."""
    certo, escutado = _palavras(esperado), _palavras(ouvido)
    ops = SequenceMatcher(None, [_chave(p) for p in escutado], [_chave(p) for p in certo],
                          autojunk=False).get_opcodes()
    saida = []
    for alvo, j1, j2 in _trechos_dos_alvos(certo, alvos):
        (i1, exato1), (i2, exato2) = _mapear(ops, j1, False), _mapear(ops, j2, True)
        if i1 is None or i2 is None:
            trecho = ""
        else:
            if not (exato1 and exato2):
                i1, i2 = _melhor_trecho(escutado, i1, i2, alvo)
            trecho = _juntar(escutado[i1:i2])
        saida.append((alvo, trecho, (j1, j2)))
    return saida, ops


def avaliar(frase, cru, final):
    """Compara uma leitura com o texto certo. cru: o que o reconhecimento ouviu; final: o que o Papory entregaria."""
    esperado, alvos = frase["texto"], frase["alvos"]
    certo = _normalizadas(esperado)
    nota = SequenceMatcher(None, _normalizadas(final), certo, autojunk=False)
    acertos = sum(b.size for b in nota.get_matching_blocks())

    no_cru, ops = _ouvido_nos_alvos(esperado, cru, alvos)
    erros_alvo = [(trecho, alvo) for alvo, trecho, _ in no_cru if trecho != alvo]
    faltou_no_final = [alvo for alvo, trecho, _ in _ouvido_nos_alvos(esperado, final, alvos)[0] if trecho != alvo]

    cobertos = set()
    for _, _, (j1, j2) in no_cru:
        cobertos.update(range(j1, j2))
    certo_p, cru_p = _palavras(esperado), _palavras(cru)
    comuns = []
    for op, i1, i2, j1, j2 in ops:
        if op != "replace" or cobertos.intersection(range(j1, j2)):
            continue
        de, para = _juntar(cru_p[i1:i2]), _juntar(certo_p[j1:j2])
        # só engano de ouvido numa palavra: leitura diferente ("pro" no lugar de "para o") não ensina nada
        if de and para and len(para.split()) == 1 and len(para) >= 4 and not re.search(r"\d", de) \
                and not _so_formato(de, para) and _parecido(de, para):
            comuns.append((de, para))

    diferencas = [(de, para) for de, para in aprendizado.diferencas(final, esperado) if not _so_formato(de, para)]
    return {"esperado": esperado, "cru": cru, "final": final, "acertos": acertos, "total": len(certo),
            "erros_alvo": erros_alvo, "faltou_no_final": faltou_no_final, "comuns": comuns,
            "diferencas": diferencas}


def _regra_existe(cfg, de):
    return any(s.get("de", "").lower() == de.lower() for s in cfg["substituicoes"])


def propor(cfg, resultados, termos=()):
    """O que a calibração vai ensinar, sem mexer em nada: {"regras", "marcadas", "vocabulario", "comuns"}.

    marcadas: as regras que já vêm aceitas (as outras trocariam palavras comuns e esperam a pessoa marcar).
    """
    regras, vocabulario, comuns = [], [], []

    def palavra(p):
        if not _no_vocabulario(cfg, p) and p.lower() not in (v.lower() for v in vocabulario):
            vocabulario.append(p)

    for t in termos:
        palavra(t)
    for r in resultados:
        for de, para in r["erros_alvo"]:
            palavra(para)
            if de and len(de) >= 3 and _parecido(de, para) and not _regra_existe(cfg, de) \
                    and de.lower() not in (x.lower() for x, _ in regras):
                regras.append((de, para))
        for alvo in r["faltou_no_final"]:
            palavra(alvo)  # o reconhecimento acertou e o polimento estragou: no vocabulário ele fica travado
        comuns.extend(r["comuns"])
    marcadas = [(de, para) for de, para in regras if not so_palavras_comuns(de)]
    return {"regras": regras, "marcadas": marcadas, "vocabulario": vocabulario, "comuns": comuns}


def regra(de, para):
    """Troca sem diferenciar maiúscula (no começo da frase o ouvido sai com maiúscula)."""
    return {"de": de, "de_regex": rf"(?i)(?<!\w){re.escape(de)}(?!\w)", "para": para.replace("\\", "\\\\"),
            "descricao": de, "descricao_para": para, "nota": NOTA_REGRA}


def aplicar(cfg, proposta, regras_aceitas=None):
    """Grava no cfg (a lista do vocabulário muda no lugar: o polimento usa a mesma). Devolve o que foi aprendido."""
    aceitas = proposta["marcadas"] if regras_aceitas is None else regras_aceitas
    feitas = []
    for de, para in aceitas:
        if not _regra_existe(cfg, de):
            cfg["substituicoes"].append(regra(de, para))
            feitas.append((de, para))
    palavras = [p for p in proposta["vocabulario"] if not _no_vocabulario(cfg, p)]
    cfg["vocabulario"].extend(palavras)
    normal = aprendizado.registrar(cfg, proposta["comuns"]) if proposta["comuns"] else {"vocabulario": [],
                                                                                        "regras": []}
    return {"regras": feitas + normal["regras"], "vocabulario": palavras + normal["vocabulario"]}


def veredito_volume(medidas):
    """medidas: [{"fala", "saturado"}, ...] de cada leitura -> "bom", "baixo", "alto" ou None (sem leitura)."""
    medidas = [m for m in medidas if m]
    if not medidas:
        return None
    if median(m["saturado"] for m in medidas) > SATURADO:
        return "alto"
    if median(m["fala"] for m in medidas) < FALA_BAIXA:
        return "baixo"
    return "bom"
