#!/usr/bin/env bash
# commit-msg hook: requires a Linear issue key (ANG-<n>) and rejects denylist terms in the message.
set -uo pipefail
msg_file="$1"
grep -Eq "ANG-[0-9]+" "$msg_file" || { echo "commit-msg: message must reference a Linear issue (ANG-<n>)" >&2; exit 1; }
hits=$("$(dirname "$0")/denylist-match.sh" < "$msg_file") || { echo "commit-msg: denylist unavailable" >&2; exit 1; }
if [ -n "$hits" ]; then
  echo "mensaje de commit: término de la denylist" >&2; exit 1
fi
