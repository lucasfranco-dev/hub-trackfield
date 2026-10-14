#!/bin/sh
# Baixa as texturas CC0 (Poly Haven) usadas pela vitrine para 3d/texturas/.
# Elas não ficam no repositório por serem grandes (~22 MB).
set -eu
cd "$(dirname "$0")"
mkdir -p texturas
for ativo in laminate_floor_02 oak_veneer_01 wood_table_001; do
  for mapa in diff nor_gl rough; do
    arquivo="texturas/${ativo}_${mapa}_2k.jpg"
    [ -f "$arquivo" ] && continue
    curl -fsSL -o "$arquivo" "https://dl.polyhaven.org/file/ph-assets/Textures/jpg/2k/${ativo}/${ativo}_${mapa}_2k.jpg"
    echo "baixado: $arquivo"
  done
done
