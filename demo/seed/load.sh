#!/usr/bin/env bash
# Uploads seed/data/**.dcm into the demo Orthanc through its REST API.
# Credentials come from demo/.env (never printed); curl reads them from a temp config, not argv.
set -euo pipefail
cd "$(dirname "$0")"
ORTHANC="${ORTHANC_URL:-http://127.0.0.1:18042}"
set -a; [ -f ../.env ] && . ../.env; set +a
: "${ORTHANC_USER:?set in demo/.env}" "${ORTHANC_PASSWORD:?set in demo/.env}"
cfg=$(mktemp); chmod 600 "$cfg"; trap 'rm -f "$cfg"' EXIT
printf 'user = "%s:%s"\n' "$ORTHANC_USER" "$ORTHANC_PASSWORD" > "$cfg"
n=0
for f in data/*/*.dcm; do
  curl -sSf -K "$cfg" -X POST "$ORTHANC/instances" --data-binary @"$f" -H 'Content-Type: application/dicom' >/dev/null
  n=$((n+1))
done
echo "uploaded $n instances to $ORTHANC"
curl -sSf -K "$cfg" "$ORTHANC/studies" | python3 -c 'import json,sys;print(len(json.load(sys.stdin)),"studies in Orthanc")'
