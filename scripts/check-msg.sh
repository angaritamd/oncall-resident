#!/usr/bin/env bash
# commit-msg hook: requires the issue key and rejects denylist terms in the message.
set -uo pipefail
msg_file="$1"
grep -q "ANG-170" "$msg_file" || { echo "commit-msg: message must reference ANG-170" >&2; exit 1; }
list="${DENYLIST_FILE:-$HOME/.config/oncall-resident/denylist.txt}"
if [ -s "$list" ] && grep -v '^[[:space:]]*$' "$list" | grep -v '^#' | grep -q -i -F -f - "$msg_file"; then
  echo "mensaje de commit: término de la denylist" >&2; exit 1
fi
