#!/bin/sh
# Envia o código de src/ para o Apps Script e atualiza a implantação do app da Web,
# mantendo a mesma URL. Usado localmente e pelo GitHub Actions.
#
# Precisa de:
#   ~/.clasprc.json   credenciais do clasp (npx clasp login)
#   DEPLOYMENT_ID     ID da implantação do app da Web (npx clasp deployments)
set -eu

if [ -z "${DEPLOYMENT_ID:-}" ]; then
  echo "Defina DEPLOYMENT_ID com o ID da implantação do app da Web." >&2
  echo "Para ver os IDs: npx clasp deployments" >&2
  exit 1
fi

DESCRICAO="${DESCRICAO:-$(git log -1 --format='%h %s' 2>/dev/null || date '+%Y-%m-%d %H:%M')}"

npx clasp push -f
npx clasp redeploy "$DEPLOYMENT_ID" -d "$DESCRICAO"
echo "Publicado: $DESCRICAO"
