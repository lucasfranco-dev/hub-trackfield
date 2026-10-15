#!/bin/sh
# Renderiza o travelling de câmera entre cada par de paradas vizinhas e gera os vídeos
# da página em midia/transicoes/: transicao-N-ida (parada N -> N+1) e transicao-N-volta,
# cada um em MP4 (H.264) e WebM (VP9), para todos os navegadores.
# São 23 quadros renderizados em 960x720, a 24 quadros/s (~1 segundo).
# Uso: sh 3d/renderizar_transicoes.sh [primeira] [última]   (padrão 0 a 6; ~12 min cada)
#      SO_CODIFICAR=1 sh 3d/renderizar_transicoes.sh       (refaz só os vídeos a partir dos quadros)
#      QUADROS=pasta: onde ficam os quadros (padrão $TMPDIR/vitrine-quadros)
set -eu
cd "$(dirname "$0")/.."
PY="${PYTHON_BLENDER:-.venv-blender/bin/python}"
SAIDA=midia/transicoes
TEMP="${QUADROS:-${TMPDIR:-/tmp}/vitrine-quadros}"
mkdir -p "$SAIDA"
for n in $(seq "${1:-0}" "${2:-6}"); do
  if [ -z "${SO_CODIFICAR:-}" ]; then
    rm -rf "$TEMP/$n"
    DESFOQUE=0 "$PY" 3d/vitrine.py --parada "$n" --transicao --quadros 23 --largura 960 --altura 720 \
      --amostras 12 --saida "$TEMP/$n" > "$TEMP-$n.log" 2>&1
  fi
  for sentido in ida volta; do
    filtro="format=yuv420p"
    [ "$sentido" = volta ] && filtro="reverse,format=yuv420p"
    ffmpeg -loglevel error -y -framerate 24 -i "$TEMP/$n/quadro-%04d.png" -vf "$filtro" \
      -c:v libx264 -profile:v high -preset slow -crf 27 -movflags +faststart -an "$SAIDA/transicao-$n-$sentido.mp4"
    ffmpeg -loglevel error -y -framerate 24 -i "$TEMP/$n/quadro-%04d.png" -vf "$filtro" \
      -c:v libvpx-vp9 -b:v 0 -crf 40 -row-mt 1 -deadline good -cpu-used 2 -an "$SAIDA/transicao-$n-$sentido.webm"
  done
  echo "transição $n: $(du -ch "$SAIDA"/transicao-"$n"-* | tail -1 | cut -f1)"
done
