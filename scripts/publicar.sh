#!/bin/sh
# Envia o código de src/ para o Apps Script e atualiza a implantação do app da Web,
# mantendo a mesma URL. Usado localmente e pelo GitHub Actions.
#
# Precisa de ~/.clasprc.json (credenciais do clasp, criadas com `npx clasp login`).
# O ID da implantação fica em package.json (config.deploymentId); a variável
# DEPLOYMENT_ID, se definida, tem prioridade.
set -eu

DEPLOYMENT_ID="${DEPLOYMENT_ID:-$(node -p "require('./package.json').config.deploymentId")}"
DESCRICAO="${DESCRICAO:-$(git log -1 --format='%h %s' 2>/dev/null || date '+%Y-%m-%d %H:%M')}"

npx clasp push -f
npx clasp redeploy "$DEPLOYMENT_ID" -d "$DESCRICAO"
echo "Publicado: $DESCRICAO"
