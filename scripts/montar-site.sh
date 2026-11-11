#!/bin/sh
# Monta o site do Hub para o GitHub Pages em _site/: as páginas de web/ e as mídias de midia/.
# Usado pelo workflow publicar-site.yml e para testar localmente:
#   sh scripts/montar-site.sh && python3 -m http.server -d _site 8080
set -eu
cd "$(dirname "$0")/.."
rm -rf _site
mkdir -p _site
cp -R web/. _site/
cp -R midia _site/midia
touch _site/.nojekyll
echo "Site montado em _site/ ($(du -sh _site | cut -f1))"
