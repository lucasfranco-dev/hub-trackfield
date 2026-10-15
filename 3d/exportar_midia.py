"""
Converte os renders das paradas (3d/renders/parada-N.png, 1600x1200) nas imagens que
a página usa: midia/paradas/parada-N.webp, no mesmo 4:3. A página recorta cada imagem
para a tela (object-fit: cover), centrando no produto, que fica a 65% da largura.

Uso: python3 3d/exportar_midia.py [--qualidade 80]
Precisa do Pillow (pip install pillow).
"""

import argparse
import glob
import os

from PIL import Image

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    p = argparse.ArgumentParser(description="Gera as imagens WebP da página a partir dos renders")
    p.add_argument("--qualidade", type=int, default=80)
    a = p.parse_args()
    destino = os.path.join(RAIZ, "midia", "paradas")
    os.makedirs(destino, exist_ok=True)
    for png in sorted(glob.glob(os.path.join(RAIZ, "3d", "renders", "parada-*.png"))):
        nome = os.path.splitext(os.path.basename(png))[0] + ".webp"
        saida = os.path.join(destino, nome)
        Image.open(png).convert("RGB").save(saida, quality=a.qualidade, method=6)
        print(f"{saida}: {os.path.getsize(saida) // 1024} KB")


if __name__ == "__main__":
    main()
