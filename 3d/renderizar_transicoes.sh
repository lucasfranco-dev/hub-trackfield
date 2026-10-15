#!/bin/sh
# Renderiza o travelling de câmera entre cada par de paradas vizinhas e gera os vídeos
# da página: midia/transicoes/transicao-N-ida.mp4 (parada N -> N+1) e -volta.mp4.
# São 12 quadros em 960x720, interpolados para 24 quadros/s pelo ffmpeg (1 segundo).
# Uso: sh 3d/renderizar_transicoes.sh [primeira] [última]   (padrão 0 a 6; ~7 min cada)
set -eu
cd "$(dirname "$0")/.."
PY="${PYTHON_BLENDER:-.venv-blender/bin/python}"
SAIDA=midia/transicoes
TEMP="${TMPDIR:-/tmp}/vitrine-quadros"
mkdir -p "$SAIDA"
for n in $(seq "${1:-0}" "${2:-6}"); do
  rm -rf "$TEMP/$n"
  DESFOQUE=0 "$PY" 3d/vitrine.py --parada "$n" --transicao --quadros 12 --largura 960 --altura 720 \
    --amostras 12 --saida "$TEMP/$n" > "$TEMP-$n.log" 2>&1
  ffmpeg -loglevel error -y -framerate 12 -i "$TEMP/$n/quadro-%04d.png" \
    -vf "minterpolate=fps=24:mi_mode=mci:mc_mode=aobmc:vsbmc=1,format=yuv420p" \
    -c:v libx264 -preset slow -crf 27 -movflags +faststart -an "$SAIDA/transicao-$n-ida.mp4"
  ffmpeg -loglevel error -y -i "$SAIDA/transicao-$n-ida.mp4" -vf reverse \
    -c:v libx264 -preset slow -crf 27 -pix_fmt yuv420p -movflags +faststart -an "$SAIDA/transicao-$n-volta.mp4"
  echo "transição $n: $(du -h "$SAIDA/transicao-$n-ida.mp4" | cut -f1)"
done
