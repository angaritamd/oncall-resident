#!/usr/bin/env bash
# Uploads seed/data/**.dcm into the demo Orthanc through its REST API.
set -euo pipefail
cd "$(dirname "$0")"
ORTHANC="${ORTHANC_URL:-http://127.0.0.1:18042}"
n=0
for f in data/*/*.dcm; do
  curl -sSf -X POST "$ORTHANC/instances" --data-binary @"$f" -H 'Content-Type: application/dicom' >/dev/null
  n=$((n+1))
done
echo "uploaded $n instances to $ORTHANC"
curl -sSf "$ORTHANC/studies" | python3 -c 'import json,sys;print(len(json.load(sys.stdin)),"studies in Orthanc")'
