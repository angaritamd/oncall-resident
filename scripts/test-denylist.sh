#!/usr/bin/env bash
# Tests for scripts/denylist-match.sh with a FICTITIOUS denylist (never the real one).
set -uo pipefail
m="$(dirname "$0")/denylist-match.sh"
export DENYLIST=$'  Acme  \nzeta\nñandú\n# comment\n\nacme-drafts.example'
fails=0
check() { # name, input, expected line numbers (space separated)
  local got; got=$(printf '%s\n' "$2" | "$m" | tr '\n' ' ' | sed 's/ $//')
  if [ "$got" = "$3" ]; then echo "ok   $1"; else echo "FAIL $1 (expected '$3', got '$got')"; fails=$((fails+1)); fi
}
check "whole word, any case"                 $'nada\nUsa ACME aquí'                 "2"
check "common word containing a term passes" $'acmeology y zetas, bizetaz'       ""
check "word boundaries: punctuation/hyphen"  $'(acme).\nacme-corp\nzeta,'         "1 2 3"
check "underscore is part of the word"       $'acme_tool'                         ""
check "domains match as substrings"          $'https://api.ACME-DRAFTS.example/v1' "1"
check "domain substring matches with a suffix"     $'acme-drafts.examplex'      "1"
check "invalid UTF-8 is still scanned"       $'ok\nANG-170 acme \xff'          "2"
check "accented neighbours never hide a term" $'éacmeé'                            "1"
check "accented term in upper case matches"  $'otro\nEl ÑANDÚ corre'            "2"
check "accented term inside a word passes"   $'ñandúes'                           ""
check "blank and comment lines are ignored"  $'# comment\n\n'                     ""
out=$(printf 'acme\n' | "$m"); [ "$out" = "1" ] || { echo "FAIL output must be line numbers only"; fails=$((fails+1)); }
if printf 'x' | DENYLIST= DENYLIST_FILE=/nonexistent "$m" >/dev/null 2>&1; then
  echo "FAIL missing denylist must exit non-zero"; fails=$((fails+1))
else echo "ok   missing denylist fails closed"; fi
fails_closed() { # name, command…
  local name=$1; shift
  if "$@" >/dev/null 2>&1; then echo "FAIL $name must exit non-zero"; fails=$((fails+1)); else echo "ok   $name"; fi
}
d=$(mktemp -d); printf 'acme\n' > "$d/dl"; chmod 000 "$d/dl"
if [ -r "$d/dl" ]; then echo "skip unreadable denylist (running as root)"
else fails_closed "unreadable denylist fails closed" env DENYLIST= DENYLIST_FILE="$d/dl" "$m" < /dev/null; fi
chmod 600 "$d/dl"; printf '# only a comment\n\n' > "$d/dl"
fails_closed "denylist with no terms fails closed" env DENYLIST= DENYLIST_FILE="$d/dl" "$m" < /dev/null
rm -rf "$d"
[ $fails -eq 0 ] && echo "denylist tests: all passed" || { echo "denylist tests: $fails failed"; exit 1; }
