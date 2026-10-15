#!/bin/sh
# Renderiza toda a vitrine em qualidade máxima, para um computador com placa de vídeo:
#   - 8 paradas em 2400x1800 com 512 amostras (a página usa até 1920 px de largura);
#   - 7 transições em 1600x1200 com 128 amostras e desfoque de movimento.
# Depois gera midia/paradas e midia/transicoes. Leva de 30 min a 2 h, conforme a placa.
# Uso: sh 3d/renderizar_maxima.sh            (tudo)
#      sh 3d/renderizar_maxima.sh paradas    (só as paradas)
#      sh 3d/renderizar_maxima.sh transicoes (só as transições)
set -eu
cd "$(dirname "$0")/.."
export DISPOSITIVO="${DISPOSITIVO:-GPU}"
inicio=$(date +%s)
sh 3d/verificar.sh
if [ "${1:-tudo}" != transicoes ]; then
  LARGURA=2400 ALTURA=1800 sh 3d/renderizar_todas.sh 512
fi
if [ "${1:-tudo}" != paradas ]; then
  LARGURA=1600 ALTURA=1200 AMOSTRAS=128 DESFOQUE=1 sh 3d/renderizar_transicoes.sh
fi
echo "Pronto em $(( ($(date +%s) - inicio) / 60 )) min."
echo "Próximo passo: conferir as imagens em midia/, fazer o commit e o push das mídias e"
echo "apontar a constante MIDIA de src/Index.html para o hash desse commit (veja o README)."
