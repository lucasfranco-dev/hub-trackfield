"""
Converte os renders das paradas (3d/renders/parada-N.png, 4:3) nas imagens que a página
usa: midia/paradas/parada-N.webp, no mesmo 4:3 e com no máximo 1920 px de largura. A página recorta cada imagem
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
    p.add_argument("--largura-maxima", type=int, default=1920)
    a = p.parse_args()
    destino = os.path.join(RAIZ, "midia", "paradas")
    os.makedirs(destino, exist_ok=True)
    for png in sorted(glob.glob(os.path.join(RAIZ, "3d", "renders", "parada-*.png"))):
        nome = os.path.splitext(os.path.basename(png))[0] + ".webp"
        saida = os.path.join(destino, nome)
        img = Image.open(png).convert("RGB")
        if img.width > a.largura_maxima:
            img = img.resize((a.largura_maxima, round(img.height * a.largura_maxima / img.width)), Image.LANCZOS)
        img.save(saida, quality=a.qualidade, method=6)
        print(f"{saida}: {os.path.getsize(saida) // 1024} KB")


if __name__ == "__main__":
    main()
