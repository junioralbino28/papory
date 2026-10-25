"""Cola o texto onde o cursor está: área de transferência + Ctrl+V (Cmd+V no Mac), e devolve o que você tinha copiado.

Guarda todos os formatos legíveis (texto, imagem, arquivos...), não só texto. A parte de cada sistema mora em
plataforma; aqui fica só a ordem das coisas.
"""
import threading
import time

from . import plataforma

trazer_de_volta = plataforma.trazer_de_volta
ler_texto = plataforma.ler_texto


def colar(texto, devolver_apos_s=0.6, hwnd=None):
    """Cola na janela onde a fala começou (hwnd) e depois restaura a área de transferência anterior.

    Devolve a thread da restauração (para quem precisa esperar por ela, como o teste); "copiado" se não deu para
    voltar à janela original ou o sistema não deixa colar (o texto fica copiado para colar à mão); None se falhou.
    """
    plataforma.esperar_modificadores_soltos()
    if not plataforma.pode_colar() or not plataforma.trazer_de_volta(hwnd):
        plataforma.escrever_texto(texto)  # não cola no lugar errado: deixa copiado
        return "copiado"
    anterior = plataforma.guardar()
    if not plataforma.escrever_texto(texto, fora_do_historico=True):
        return None
    plataforma.colar_atalho()

    def devolver():
        time.sleep(devolver_apos_s)  # o app de destino lê a área de transferência depois do Ctrl+V
        if anterior is not None:
            plataforma.restaurar(anterior)

    t = threading.Thread(target=devolver, daemon=True)
    t.start()
    return t
