"""
Recorta um render 4:3 da vitrine nos formatos usados pela página:

- computador: 16:9, largura inteira, produto onde a câmera o colocou (à direita);
- celular: 9:16, centrado no produto.

Uso: python3 3d/recortes.py 3d/renders/parada-0.png [--centro-x 0.65]
Gera <nome>-computador.webp e <nome>-celular.webp ao lado do original.
Precisa do Pillow (pip install pillow).
"""

import argparse
import os

from PIL import Image


def recortar(caminho, centro_x, qualidade):
    img = Image.open(caminho).convert("RGB")
    larg, alt = img.size
    base = os.path.splitext(caminho)[0]

    alt_pc = round(larg * 9 / 16)
    topo = (alt - alt_pc) // 2
    pc = img.crop((0, topo, larg, topo + alt_pc))
    pc.save(base + "-computador.webp", quality=qualidade, method=6)

    larg_cel = round(alt * 9 / 16)
    esquerda = min(max(round(larg * centro_x - larg_cel / 2), 0), larg - larg_cel)
    cel = img.crop((esquerda, 0, esquerda + larg_cel, alt))
    cel.save(base + "-celular.webp", quality=qualidade, method=6)

    for sufixo, im in (("computador", pc), ("celular", cel)):
        arquivo = f"{base}-{sufixo}.webp"
        print(f"{arquivo}: {im.size[0]}x{im.size[1]}, {os.path.getsize(arquivo) // 1024} KB")


def main():
    p = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    p.add_argument("render")
    p.add_argument("--centro-x", type=float, default=0.65, help="Posição horizontal do produto no render (0 a 1)")
    p.add_argument("--qualidade", type=int, default=82)
    a = p.parse_args()
    recortar(a.render, a.centro_x, a.qualidade)


if __name__ == "__main__":
    main()
