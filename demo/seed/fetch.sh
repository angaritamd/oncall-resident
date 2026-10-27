#!/usr/bin/env bash
# Downloads the public LIDC-IDRI series listed in manifest.json into seed/data/ (git-ignored).
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p data
base=$(python3 -c 'import json;print(json.load(open("manifest.json"))["download"])')
python3 -c 'import json;[print(s["case"],s["series"]) for s in json.load(open("manifest.json"))["series"]]' |
while read -r case uid; do
  if [ -d "data/$case" ] && ls "data/$case"/*.dcm >/dev/null 2>&1; then echo "$case: cached"; continue; fi
  mkdir -p "data/$case"
  curl -sSfL --retry 3 "$base$uid" -o "data/$case.zip"
  unzip -q -o "data/$case.zip" -d "data/$case" && rm "data/$case.zip"
  echo "$case: $(ls "data/$case" | wc -l | tr -d ' ') files"
done
