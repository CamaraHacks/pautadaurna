#!/usr/bin/env bash
# Daily refresh: Google Trends per group (SerpApi, budgeted) -> rebuild page -> publish atomically.
# Usage: deploy/atualiza.sh [--completo]   (--completo also re-downloads TSE/IBGE and rebuilds all data)
set -euo pipefail
cd "$(dirname "$0")/.."
DEST="${DEST:-/var/www/pautadaurna}"
mkdir -p logs
exec >>logs/atualiza.log 2>&1
echo "=== $(date '+%F %T')"
set -a; [ -f .env ] && . ./.env; set +a
PY=.venv/bin/python

PERFIL_2026=https://cdn.tse.jus.br/estatistica/sead/odsele/perfil_comparecimento_abstencao/perfil_comparecimento_abstencao_2026.zip
if [ "${1:-}" = "--completo" ] || { [ ! -f data/raw/perfil_comparecimento_abstencao_2026.zip ] \
     && [ "$(curl -s -o /dev/null -w '%{http_code}' -I "$PERFIL_2026")" = 200 ]; }; then
	echo "full rebuild (TSE/IBGE)"
	$PY pipeline/01_download.py
	$PY pipeline/02_build.py
	$PY pipeline/03_analyze.py
fi
[ -f data/raw/malha_municipios.topojson ] || $PY pipeline/01_download.py
$PY pipeline/06_group_trends.py
$PY pipeline/04_export.py
mkdir -p "$DEST"
cp site/index.html "$DEST/index.html.tmp" && mv "$DEST/index.html.tmp" "$DEST/index.html"
echo "published to $DEST"
