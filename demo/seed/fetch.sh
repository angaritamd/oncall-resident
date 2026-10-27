#!/usr/bin/env bash
# Downloads the public LIDC-IDRI series listed in manifest.json into seed/data/ (git-ignored).
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p data
base=$(python3 -c 'import json;print(json.load(open("manifest.json"))["download"])')
case "$base" in https://services.cancerimagingarchive.net/*) ;; *) echo "unexpected download base" >&2; exit 1 ;; esac
python3 -c 'import json;[print(s["case"],s["series"]) for s in json.load(open("manifest.json"))["series"]]' |
while read -r case uid; do
  [[ "$case" =~ ^[A-Za-z0-9_-]+$ && "$uid" =~ ^[0-9.]+$ ]] || { echo "invalid manifest entry" >&2; exit 1; }
  if [ -d "data/$case" ] && ls "data/$case"/*.dcm >/dev/null 2>&1; then echo "$case: cached"; continue; fi
  mkdir -p "data/$case"
  curl -sSf --proto '=https' --retry 3 "$base$uid" -o "data/$case.zip"
  tmp=$(mktemp -d)
  unzip -q -j -o "data/$case.zip" -d "$tmp" && rm "data/$case.zip"
  mv "$tmp"/*.dcm "data/$case/" && rm -rf "$tmp"
  echo "$case: $(ls "data/$case" | wc -l | tr -d ' ') files"
done
