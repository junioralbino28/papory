"""Configuração do usuário em config.json, na pasta de dados do Papory (criada com o padrão na primeira vez).

Windows: %APPDATA%\\Papory. Mac: ~/Library/Application Support/Papory.
Nada pessoal mora no código: vocabulário, atalhos de texto e o caminho das chaves ficam nesse arquivo.
"""
import json
import os
import shutil
from copy import deepcopy
from pathlib import Path

from . import plataforma

PASTA = plataforma.pasta_dados()
PASTA_ANTIGA = PASTA.with_name("Ditado")  # o protótipo se chamava "Ditado" (até 24/10/2026)
ARQUIVO = PASTA / "config.json"

# texto para a tela das regras escritas como expressão regular (casadas pelo padrão)
DESCRICOES_REGEX = [
    {"descricao": "o cloud, do cloud, no cloud…", "descricao_para": "o Claude, do Claude, no Claude…",
     "nota": "só no masculino: “a cloud” (a nuvem) fica como está"},
    {"descricao": "Cloud, (chamando, no começo da frase)", "descricao_para": "Claude,"},
]

PADRAO = {
    "atalho": ["ctrl", "win"],          # segurar para falar; nomes: ctrl, win, shift, alt, alt_gr, f1..f12
    "idioma": "pt",
    "microfone": None,                  # None = o padrão do sistema; ou parte do nome do dispositivo
    "asr": {
        "modelo": "nemo-parakeet-tdt-0.6b-v3",
        "dispositivo": "auto",          # auto = placa de vídeo (DirectML, no Windows) se houver, senão processador
    },
    "polimento": {                      # LOCAL e grátis: IA pequena na placa de vídeo via Ollama
        "ativo": True,
        "modelo_local": "qwen3.5:4b",   # instalar: ollama pull qwen3.5:4b
        "prazo_s": 3.0,                 # passou disso, cola o texto cru...
        "prazo_por_minuto_s": 6.0,      # ...mais isto por minuto de fala (ditado longo pede mais tempo)
        "minimo_palavras": 5,           # ditado mais curto que isso não passa pela IA
        "manter_carregado": "60m",      # quanto tempo o modelo fica na placa depois do último uso
    },
    "reforco_nuvem": {                  # OPCIONAL: Groq (plano grátis). Se falhar, o local assume sozinho.
        "ativo": False,                 # liga = o ÁUDIO e o texto vão para a Groq a cada ditado
        "modelo_texto": "qwen/qwen3.8-27b",
        "modelo_audio": "whisper-large-v3",
        "prazo_texto_s": 2.5,
        "prazo_audio_s": 4.0,           # sem a 2ª transcrição nesse tempo, segue só com o Parakeet
    },
    "arquivo_de_chaves": None,          # arquivo .env com GROQ_API_KEY; sem ele, usa a variável de ambiente
    "vocabulario": ["Claude", "Claude Code", "GitHub", "VS Code", "deploy", "commit", "push", "prompt"],
    "substituicoes": [                  # aplicadas quando o polimento não roda
        {"de": "Cláudio", "para": "Claude", "apps": ["code", "windowsterminal", "terminal", "cursor", "claude"]},
        {"de": "Claudio", "para": "Claude", "apps": ["code", "windowsterminal", "terminal", "cursor", "claude"]},
        {"de": "Claudia", "para": "Claude", "apps": ["code", "windowsterminal", "terminal", "cursor", "claude"]},
        # "o Claude" é masculino; "a cloud" (nuvem) é feminino: só o masculino e o chamado no começo viram Claude
        {"de_regex": r"(?i)\b(o|do|no|pro|pelo|ao|com o)\s+cloud\b", "para": r"\1 Claude",
         "apps": ["code", "windowsterminal", "terminal", "cursor", "claude"], **DESCRICOES_REGEX[0]},
        {"de_regex": r"(?i)(^|[.!?]\s+)cloud,", "para": r"\1Claude,", "apps": ["code", "windowsterminal", "terminal", "cursor", "claude"],
         **DESCRICOES_REGEX[1]},
    ],
    "atalhos_de_texto": {},             # "meu email" -> "fulano@exemplo.com"
    "historico": True,                  # guarda áudio e textos de cada ditado na pasta historico
    "sons": True,
    "interface": {
        "primeira_abertura_feita": False,
        "pilula": True,                 # mostra a pílula no rodapé da tela enquanto ouve
        "dicas_fechadas": [],
        "sugestoes_ignoradas": [],      # palavras aprendidas que a pessoa mandou ignorar
    },
}


def _mesclar(base, novo):
    for k, v in novo.items():
        if isinstance(v, dict) and isinstance(base.get(k), dict):
            _mesclar(base[k], v)
        else:
            base[k] = v
    return base


def carregar():
    # leva a configuração e o histórico do nome antigo. Confere o ARQUIVO, não a pasta: o log pode ter criado
    # a pasta nova antes (aconteceu no 1º teste da interface, em 25/10/2026, e a migração era pulada)
    if (PASTA_ANTIGA / "config.json").exists() and not ARQUIVO.exists():
        shutil.copytree(PASTA_ANTIGA, PASTA, dirs_exist_ok=True)
    PASTA.mkdir(parents=True, exist_ok=True)
    if not ARQUIVO.exists():
        ARQUIVO.write_bytes(json.dumps(PADRAO, ensure_ascii=False, indent=2).encode("utf-8"))
    usuario = json.loads(ARQUIVO.read_text(encoding="utf-8"))
    # config da 0.1.0: "fusao" e polimento na Groq viram o reforço na nuvem; o polimento passa a ser local
    antiga = usuario.pop("fusao", None)
    pol = usuario.get("polimento", {})
    if "provedor" in pol or antiga is not None:
        usuario.setdefault("reforco_nuvem", {})["ativo"] = bool((antiga or {}).get("ativo")) or pol.get("provedor") == "groq"
        for k in ("provedor", "modelo"):
            pol.pop(k, None)
        for k in ("prazo_s", "prazo_por_minuto_s"):
            pol.pop(k, None)  # os prazos antigos eram da nuvem; o local usa os novos padrões
        ARQUIVO.write_bytes(json.dumps(_mesclar(deepcopy(PADRAO), usuario), ensure_ascii=False, indent=2).encode("utf-8"))
    cfg = _mesclar(deepcopy(PADRAO), usuario)
    regex_padrao = {s["de_regex"]: d for s, d in zip([s for s in PADRAO["substituicoes"] if "de_regex" in s], DESCRICOES_REGEX)}
    for s in cfg["substituicoes"]:  # regras antigas sem texto para a tela
        if "de_regex" in s and "descricao" not in s and s["de_regex"] in regex_padrao:
            s.update(regex_padrao[s["de_regex"]])
    return cfg


def salvar(cfg):
    """Grava a configuração inteira (a interface chama depois de cada mudança)."""
    PASTA.mkdir(parents=True, exist_ok=True)
    tmp = ARQUIVO.with_suffix(".tmp")
    tmp.write_bytes(json.dumps(cfg, ensure_ascii=False, indent=2).encode("utf-8"))
    os.replace(tmp, ARQUIVO)


def guardar_chave(nome, valor):
    """Guarda (ou apaga, com valor vazio) uma chave de API no cofre do sistema (Credenciais do Windows, Keychain do Mac)."""
    plataforma.guardar_credencial(nome, valor)


def chave(nome, cfg):
    """Lê uma chave de API: arquivo .env indicado na config, cofre do sistema, variável de ambiente."""
    caminho = cfg.get("arquivo_de_chaves")
    if caminho and Path(caminho).exists():
        for linha in Path(caminho).read_text(encoding="utf-8", errors="replace").splitlines():
            linha = linha.strip()
            if linha.startswith("export "):
                linha = linha[7:]
            if linha.startswith(f"{nome}="):
                return linha.split("=", 1)[1].strip().strip("'\"")
    return plataforma.ler_credencial(nome) or os.environ.get(nome)
