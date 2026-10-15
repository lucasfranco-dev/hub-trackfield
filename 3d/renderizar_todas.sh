#!/bin/sh
# Renderiza as 8 paradas e gera as imagens da página (midia/paradas/).
# Uso: sh 3d/renderizar_todas.sh [amostras]   (padrão 96; ~12 min por parada em CPU de 4 núcleos)
# Variáveis: LARGURA e ALTURA (padrão 1600x1200, sempre 4:3), DISPOSITIVO (CPU ou GPU).
set -eu
cd "$(dirname "$0")/.."
. 3d/ambiente.sh
AMOSTRAS="${1:-96}"
for n in 0 1 2 3 4 5 6 7; do
  echo "parada $n: renderizando ($DISPOSITIVO, ${LARGURA:-1600}x${ALTURA:-1200}, $AMOSTRAS amostras)"
  "$PY" 3d/vitrine.py --parada "$n" --amostras "$AMOSTRAS" --largura "${LARGURA:-1600}" --altura "${ALTURA:-1200}" \
    --saida "3d/renders/parada-$n.png" > "3d/renders/parada-$n.log" 2>&1 || { tail -20 "3d/renders/parada-$n.log"; exit 1; }
  rm -f "3d/renders/parada-$n.log"
done
"$PY" 3d/exportar_midia.py
