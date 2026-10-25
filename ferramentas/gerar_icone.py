"""Gera o ícone do Papory (.ico 16–256 px) a partir da arte em pixel art com fundo transparente.

uso: python gerar_icone.py [marca/papory.png] [marca/papory.ico]
Recorta pela parte realmente visível (alfa > 40), centraliza num quadrado e reduz com NEAREST
para os pixels continuarem nítidos.
"""
import sys
from pathlib import Path

from PIL import Image

RAIZ = Path(__file__).resolve().parent.parent
origem = Path(sys.argv[1]) if len(sys.argv) > 1 else RAIZ / "marca" / "papory.png"
destino = Path(sys.argv[2]) if len(sys.argv) > 2 else RAIZ / "marca" / "papory.ico"

im = Image.open(origem).convert("RGBA")
caixa = im.getchannel("A").point(lambda a: 255 if a > 40 else 0).getbbox()
im = im.crop(caixa)
lado = max(im.size)
quadrado = Image.new("RGBA", (lado, lado), (0, 0, 0, 0))
quadrado.paste(im, ((lado - im.width) // 2, (lado - im.height) // 2))
tamanhos = [256, 128, 64, 48, 32, 24, 16]
imagens = [quadrado.resize((t, t), Image.NEAREST) for t in tamanhos]
imagens[0].save(destino, format="ICO", sizes=[(t, t) for t in tamanhos], append_images=imagens[1:])
quadrado.resize((512, 512), Image.NEAREST).save(destino.with_name("papory-512.png"))

# Mac: o desenho ocupa ~80% da tela do ícone (margem padrão dos ícones do macOS)
grande = Image.new("RGBA", (1024, 1024), (0, 0, 0, 0))
miolo = quadrado.resize((820, 820), Image.NEAREST)
grande.paste(miolo, (102, 102))
icns = destino.with_suffix(".icns")
grande.save(icns, format="ICNS",
            append_images=[grande.resize((t, t), Image.NEAREST) for t in (512, 256, 128, 64, 32, 16)])
print(f"recorte {caixa} → {destino} ({destino.stat().st_size} bytes) + papory-512.png + {icns.name}")
