#!/bin/sh
# Confere se o computador está pronto para renderizar a vitrine: Python do Blender,
# Pillow, ffmpeg, texturas e placa de vídeo. Uso: sh 3d/verificar.sh
cd "$(dirname "$0")/.."
ok=1
. 3d/ambiente.sh
echo "Python do Blender: $PY"
"$PY" -c "import sys, bpy; print('  Python', sys.version.split()[0], '| Blender', bpy.app.version_string)" || ok=0
"$PY" -c "import PIL; print('  Pillow', PIL.__version__)" || { echo "  Falta o Pillow: $PY -m pip install pillow"; ok=0; }
if command -v ffmpeg > /dev/null; then echo "ffmpeg: $(ffmpeg -version | head -1 | cut -d' ' -f1-3)"; else echo "Falta o ffmpeg (só para as transições)."; ok=0; fi
n=$(ls 3d/texturas/*.jpg 2>/dev/null | wc -l)
echo "Texturas: $n de 9"; [ "$n" -ge 9 ] || { echo "  Rode: sh 3d/baixar_texturas.sh"; ok=0; }
echo "Placa de vídeo:"
"$PY" 3d/vitrine.py --parada 7 --largura 64 --altura 48 --amostras 1 --dispositivo GPU \
  --saida "${TMPDIR:-/tmp}/vitrine-teste-gpu.png" 2>&1 | grep -E "GPU|CPU" | sed 's/^/  /'
[ "$ok" = 1 ] && echo "Pronto para renderizar." || { echo "Corrija os itens acima."; exit 1; }
