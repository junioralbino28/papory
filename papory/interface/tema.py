"""Cores, fontes e folha de estilo do Papory (as mesmas do esboço aprovado em 25/10/2026).

Fundo verde-claro, verde do papagaio nos botões, laranja do bico nos destaques, pílula escura.
Fontes: Pixelify Sans (marca e números) e Plus Jakarta Sans (o resto), as duas com licença OFL (ver fontes/).
"""
from pathlib import Path

from PySide6.QtGui import QFont, QFontDatabase, QPixmap

PASTA = Path(__file__).resolve().parent
IMAGENS = PASTA / "imagens"

FUNDO = "#F4F7F0"
MENU = "#EDF2E7"
BRANCO = "#FFFFFF"
BORDA = "#DFE6D7"
BORDA_FORTE = "#C9D3BE"
TEXTO = "#17210F"
TEXTO_2 = "#4F5B46"
TEXTO_3 = "#66715C"
VERDE = "#237A15"
VERDE_ESCURO = "#1B6410"
VERDE_CLARO = "#E2F0D5"
VERDE_MENU = "#DCEFCB"
VERDE_VIVO = "#3FA52A"
VERDE_PAPAGAIO = "#6CC24A"
LARANJA = "#F28C1B"
LARANJA_TEXTO = "#8A4600"
LARANJA_CLARO = "#FFF4E5"
LARANJA_BORDA = "#F3D5A8"
VERMELHO = "#B42318"
PILULA = "#12170E"

FONTE = "Plus Jakarta Sans"
FONTE_MARCA = "Pixelify Sans"


def carregar_fontes():
    for f in sorted((PASTA / "fontes").glob("*.ttf")):
        QFontDatabase.addApplicationFont(str(f))


def fonte(tamanho=14, peso=QFont.Weight.Normal, marca=False):
    f = QFont(FONTE_MARCA if marca else FONTE)
    f.setPixelSize(tamanho)
    f.setWeight(peso)
    return f


def papagaio(nome="papory-512.png"):
    return QPixmap(str(IMAGENS / nome))


QSS = f"""
* {{ font-family: "{FONTE}"; color: {TEXTO}; }}
QWidget#fundo, QScrollArea, QScrollArea > QWidget > QWidget#pagina {{ background: {FUNDO}; border: 0; }}
QFrame#menu {{ background: {MENU}; border: 0; border-right: 1px solid #DCE4D2; }}

QPushButton[papel="nav"] {{
    text-align: left; padding: 0 12px; min-height: 44px; border: 0; border-radius: 10px;
    background: transparent; color: #2E3A27; font-size: 15px; font-weight: 600;
}}
QPushButton[papel="nav"]:hover {{ background: #E3EDD9; }}
QPushButton[papel="nav"]:checked {{ background: {VERDE_MENU}; color: #17410C; font-weight: 700; }}

QFrame[papel="cartao"] {{ background: {BRANCO}; border: 1px solid {BORDA}; border-radius: 16px; }}
QFrame[papel="cartao_destaque"] {{ background: {BRANCO}; border: 2px solid #9CCB82; border-radius: 16px; }}
QFrame[papel="cartao_laranja"] {{ background: {BRANCO}; border: 1px solid {LARANJA_BORDA}; border-radius: 16px; }}
QFrame[papel="passo"] {{ background: {BRANCO}; border: 1px solid {BORDA}; border-radius: 20px; }}
QFrame[papel="dica"] {{ background: {LARANJA_CLARO}; border: 1px solid {LARANJA_BORDA}; border-radius: 14px; }}
QFrame[papel="aviso"] {{ background: {LARANJA_CLARO}; border: 1px solid {LARANJA_BORDA}; border-radius: 12px; }}
QFrame[papel="ok"] {{ background: #E9F5DF; border: 0; border-radius: 14px; }}
QFrame[papel="suave"] {{ background: {FUNDO}; border: 0; border-radius: 14px; }}
QFrame[papel="linha"] {{ background: #E6ECDF; border: 0; max-height: 1px; min-height: 1px; }}
QFrame[papel="chip"] {{ background: {BRANCO}; border: 1px solid #D7DFCD; border-radius: 12px; }}

QLabel {{ background: transparent; }}
QLabel[papel="titulo"] {{ font-size: 30px; font-weight: 800; }}
QLabel[papel="h2"] {{ font-size: 19px; font-weight: 800; }}
QLabel[papel="h3"] {{ font-size: 16px; font-weight: 800; }}
QLabel[papel="sub"] {{ font-size: 15px; color: {TEXTO_2}; }}
QLabel[papel="texto"] {{ font-size: 15px; }}
QLabel[papel="meta"] {{ font-size: 13px; color: {TEXTO_2}; }}
QLabel[papel="rotulo"] {{ font-size: 13px; font-weight: 700; color: #3D4935; }}
QLabel[papel="pequeno"] {{ font-size: 12px; color: {TEXTO_3}; }}
QLabel[papel="numero"] {{ font-family: "{FONTE_MARCA}"; font-size: 42px; }}
QLabel[papel="numero_verde"] {{ font-family: "{FONTE_MARCA}"; font-size: 42px; color: {VERDE}; }}
QLabel[papel="marca"] {{ font-family: "{FONTE_MARCA}"; font-size: 28px; font-weight: 600; }}
QLabel[papel="tag_local"] {{ background: {VERDE_CLARO}; color: #1E5C12; border-radius: 9px; padding: 2px 8px;
    font-size: 12px; font-weight: 700; }}
QLabel[papel="tag_nuvem"] {{ background: #FFF0DE; color: {LARANJA_TEXTO}; border-radius: 9px; padding: 2px 8px;
    font-size: 12px; font-weight: 700; }}
QLabel[papel="tag_neutra"] {{ background: {FUNDO}; color: {TEXTO_2}; border: 1px solid #DCE4D2; border-radius: 9px;
    padding: 1px 8px; font-size: 12px; font-weight: 700; }}
QLabel[papel="tecla"] {{ background: {BRANCO}; border: 1px solid {BORDA_FORTE}; border-bottom: 3px solid {BORDA_FORTE};
    border-radius: 8px; padding: 2px 9px; font-weight: 700; font-size: 13px; }}
QLabel[papel="tecla_grande"] {{ background: {BRANCO}; border: 1px solid {BORDA_FORTE}; border-bottom: 3px solid {BORDA_FORTE};
    border-radius: 10px; padding: 8px 16px; font-weight: 700; font-size: 16px; }}
QLabel[papel="troca_de"] {{ color: #8C2A1C; background: #FDECEA; border-radius: 8px; padding: 5px 12px; font-size: 15px; }}
QLabel[papel="troca_para"] {{ color: #1E5C12; background: {VERDE_CLARO}; border-radius: 8px; padding: 5px 12px;
    font-size: 15px; font-weight: 700; }}
QLabel[papel="texto_atalho"] {{ background: {FUNDO}; border: 1px solid #E3E9DB; border-radius: 10px; padding: 8px 12px;
    font-size: 15px; font-weight: 600; }}
QLabel[papel="laranja"] {{ color: #4A2A00; font-size: 14px; }}
QLabel[papel="verde"] {{ color: #1E5C12; font-size: 13px; font-weight: 700; }}
QLabel[papel="erro"] {{ color: {VERMELHO}; font-size: 13px; font-weight: 600; }}
QLabel a {{ color: {VERDE}; }}

QPushButton {{ font-size: 14px; }}
QPushButton[papel="primario"] {{ background: {VERDE}; color: white; border: 0; border-radius: 10px;
    padding: 0 20px; min-height: 44px; font-weight: 700; }}
QPushButton[papel="primario"]:hover {{ background: {VERDE_ESCURO}; }}
QPushButton[papel="primario"]:disabled {{ background: #C9DABF; color: #2E3A27; }}
QPushButton[papel="secundario"] {{ background: {BRANCO}; color: {TEXTO}; border: 1px solid #CBD5C0; border-radius: 10px;
    padding: 0 18px; min-height: 42px; font-weight: 600; }}
QPushButton[papel="secundario"]:hover {{ background: {FUNDO}; }}
QPushButton[papel="secundario"]:disabled {{ color: {TEXTO_3}; }}
QPushButton[papel="contorno"] {{ background: {BRANCO}; color: #1E5C12; border: 1px solid {VERDE}; border-radius: 10px;
    padding: 0 16px; min-height: 42px; font-weight: 700; }}
QPushButton[papel="contorno"]:hover {{ background: #F1F8EC; }}
QPushButton[papel="perigo"] {{ background: {BRANCO}; color: {VERMELHO}; border: 1px solid #E8B4AE; border-radius: 10px;
    padding: 0 16px; min-height: 42px; font-weight: 600; }}
QPushButton[papel="perigo"]:hover {{ background: #FDECEA; }}
QPushButton[papel="texto"] {{ background: transparent; color: #3D4935; border: 0; border-radius: 10px;
    padding: 0 12px; min-height: 42px; font-weight: 600; }}
QPushButton[papel="texto"]:hover {{ background: #EEF3E8; }}
QPushButton[papel="link"] {{ background: transparent; color: {LARANJA_TEXTO}; border: 0; padding: 0; font-weight: 700;
    font-size: 14px; text-decoration: underline; text-align: left; }}
QPushButton[papel="ideia"] {{ background: {LARANJA_CLARO}; color: #6B3600; border: 1px solid {LARANJA_BORDA};
    border-radius: 17px; padding: 0 14px; min-height: 34px; font-weight: 600; font-size: 13px; }}
QPushButton[papel="ideia"]:hover {{ background: #FFE9CC; }}
QToolButton[papel="icone"] {{ background: transparent; border: 0; border-radius: 10px; min-width: 42px; min-height: 42px; }}
QToolButton[papel="icone"]:hover {{ background: #EEF3E8; }}
QToolButton[papel="icone"]:checked {{ background: {VERDE_CLARO}; }}

QLineEdit, QPlainTextEdit, QComboBox {{
    background: {BRANCO}; border: 1px solid {BORDA_FORTE}; border-radius: 12px; font-size: 15px;
    selection-background-color: #CFE8BE; selection-color: {TEXTO};
}}
QLineEdit, QComboBox {{ min-height: 44px; padding: 0 14px; }}
QPlainTextEdit {{ padding: 8px 10px; }}
QLineEdit:focus, QPlainTextEdit:focus, QComboBox:focus {{ border: 2px solid {VERDE_PAPAGAIO}; }}
QComboBox::drop-down {{ border: 0; width: 32px; }}
QComboBox QAbstractItemView {{ background: {BRANCO}; border: 1px solid {BORDA}; selection-background-color: #EEF3E8;
    selection-color: {TEXTO}; outline: 0; padding: 4px; }}

QCheckBox {{ font-size: 14px; spacing: 10px; }}
QCheckBox::indicator {{ width: 20px; height: 20px; border: 1px solid #8A9580; border-radius: 5px; background: white; }}
QCheckBox::indicator:checked {{ background: {VERDE}; border-color: {VERDE}; image: url("{(IMAGENS / "visto.svg").as_posix()}"); }}

QScrollBar:vertical {{ background: transparent; width: 12px; margin: 4px 2px; }}
QScrollBar::handle:vertical {{ background: #C9D3BE; border-radius: 4px; min-height: 40px; }}
QScrollBar::handle:vertical:hover {{ background: #A9B69C; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical, QScrollBar::add-page:vertical,
QScrollBar::sub-page:vertical {{ height: 0; background: transparent; }}

QProgressBar {{ background: #DCE4D2; border: 0; border-radius: 4px; max-height: 8px; min-height: 8px; }}
QProgressBar::chunk {{ background: {VERDE}; border-radius: 4px; }}

QMenu {{ background: {BRANCO}; border: 1px solid #DCE4D2; border-radius: 10px; padding: 6px; }}
QMenu::item {{ padding: 10px 18px 10px 32px; border-radius: 6px; font-size: 14px; color: {TEXTO}; }}
QMenu::item:selected {{ background: #EEF3E8; color: {TEXTO}; }}
QMenu::item:disabled {{ color: {TEXTO_2}; }}
QMenu::separator {{ height: 1px; background: #E6ECDF; margin: 4px 6px; }}
QMenu::indicator {{ width: 16px; height: 16px; left: 10px; }}
QMenu::indicator:checked {{ image: url("{(IMAGENS / "visto_verde.svg").as_posix()}"); }}

QToolTip {{ background: {PILULA}; color: white; border: 0; padding: 6px 10px; border-radius: 6px; font-size: 13px; }}
QMessageBox {{ background: {BRANCO}; }}
"""


def aplicar(app):
    carregar_fontes()
    app.setFont(fonte(14))
    app.setStyleSheet(QSS)
