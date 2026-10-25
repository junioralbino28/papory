"""Qual app está na frente (processo + título da janela), para o polimento saber onde você está escrevendo."""
from . import plataforma

DESCRICOES = {
    "code": "VS Code (editor de código; pode ser uma conversa com o Claude Code)",
    "cursor": "Cursor (editor de código com assistente de IA)",
    "windowsterminal": "terminal (pode ser o Claude Code ou outro agente de código)",
    "powershell": "terminal PowerShell", "pwsh": "terminal PowerShell", "cmd": "prompt de comando",
    "whatsapp": "WhatsApp (mensagem informal)", "slack": "Slack (mensagem de trabalho)",
    "outlook": "Outlook (e-mail)", "winword": "Word (documento)", "notepad": "Bloco de Notas",
    "terminal": "terminal (pode ser o Claude Code ou outro agente de código)", "notas": "Notas (anotação)",
    "textedit": "TextEdit (documento)", "mail": "Mail (e-mail)",
}
NAVEGADORES = {"chrome", "msedge", "firefox", "brave", "opera", "safari"}
NOMES = {"code": "VS Code", "cursor": "Cursor", "windowsterminal": "Terminal", "powershell": "PowerShell",
         "pwsh": "PowerShell", "cmd": "Prompt de comando", "whatsapp": "WhatsApp", "whatsapp.root": "WhatsApp",
         "slack": "Slack", "outlook": "Outlook", "olk": "Outlook", "winword": "Word", "excel": "Excel",
         "notepad": "Bloco de Notas", "chrome": "Chrome", "msedge": "Edge", "firefox": "Firefox", "brave": "Brave",
         "opera": "Opera", "claude": "Claude", "telegram": "Telegram", "discord": "Discord", "notion": "Notion",
         "papory": "Papory", "python": "Papory", "pythonw": "Papory", "terminal": "Terminal", "safari": "Safari",
         "notas": "Notas", "textedit": "TextEdit", "mail": "Mail"}


def nome_do_app(processo):
    """Nome para mostrar na tela: "code" vira "VS Code"; desconhecido sai com a primeira letra maiúscula."""
    if not processo:
        return "app"
    return NOMES.get(processo, processo[:1].upper() + processo[1:])


def app_ativo():
    """Devolve {"processo": "code", "titulo": "...", "descricao": "...", "hwnd": ...} do que está em primeiro plano.

    No Mac o título vem vazio (lê-lo pediria outra permissão) e o "hwnd" é o número do processo.
    """
    processo, titulo, hwnd = plataforma.janela_ativa()
    if processo in NAVEGADORES:
        descricao = f"navegador, página: {titulo}" if titulo else "navegador"
    else:
        descricao = DESCRICOES.get(processo, processo or "desconhecido")
    return {"processo": processo, "titulo": titulo, "descricao": descricao, "hwnd": hwnd}
