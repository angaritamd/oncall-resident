#!/usr/bin/env bash
# commit-msg hook: requires the issue key and rejects denylist terms in the message.
set -uo pipefail
msg_file="$1"
grep -q "ANG-170" "$msg_file" || { echo "commit-msg: message must reference ANG-170" >&2; exit 1; }
hits=$("$(dirname "$0")/denylist-match.sh" < "$msg_file") || { echo "commit-msg: denylist unavailable" >&2; exit 1; }
if [ -n "$hits" ]; then
  echo "mensaje de commit: término de la denylist" >&2; exit 1
fi
