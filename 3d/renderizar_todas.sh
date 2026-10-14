#!/bin/sh
# Renderiza as 8 paradas em 1600x1200 e gera os recortes de computador e celular.
# Uso: sh 3d/renderizar_todas.sh [amostras]   (padrão 96; ~12 min por parada em CPU de 4 núcleos)
set -eu
cd "$(dirname "$0")/.."
PY="${PYTHON_BLENDER:-.venv-blender/bin/python}"
AMOSTRAS="${1:-96}"
for n in 0 1 2 3 4 5 6 7; do
  "$PY" 3d/vitrine.py --parada "$n" --amostras "$AMOSTRAS" --saida "3d/renders/parada-$n.png" > "3d/renders/parada-$n.log" 2>&1
  python3 3d/recortes.py "3d/renders/parada-$n.png" --centro-x 0.65
  rm -f "3d/renders/parada-$n.log"
done
