#!/usr/bin/env bash
# Reads text on stdin and prints the line numbers that contain a denylist term, one per line.
# Never prints the terms or the matched text.
#   - terms with a dot (domains) match as case-insensitive substrings
#   - other terms match as case-insensitive whole words (word boundaries), so a common word that merely
#     contains a term does not match
# Terms come from $DENYLIST (one per line, used in CI from a secret) or $DENYLIST_FILE
# (default ~/.config/oncall-resident/denylist.txt). Exit 2 when no denylist is available.
set -uo pipefail
dir=$(mktemp -d); trap 'rm -rf "$dir"' EXIT
if [ -n "${DENYLIST:-}" ]; then
  printf '%s\n' "$DENYLIST" > "$dir/all"
elif [ -s "${DENYLIST_FILE:-$HOME/.config/oncall-resident/denylist.txt}" ]; then
  cat "${DENYLIST_FILE:-$HOME/.config/oncall-resident/denylist.txt}" > "$dir/all"
else
  echo "denylist not found (set DENYLIST or create ~/.config/oncall-resident/denylist.txt)" >&2
  exit 2
fi
# trim whitespace, drop blanks and comments, split by kind
sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//' -e '/^$/d' -e '/^#/d' "$dir/all" > "$dir/clean"
grep -F '.' "$dir/clean" > "$dir/substr" || true
grep -v -F '.' "$dir/clean" > "$dir/words" || true
# Case folding is Unicode-aware and done before matching (terms and input alike); invalid UTF-8 bytes are
# kept as-is. Matching is then byte-oriented (LC_ALL=C, -a), so such input is still scanned as text instead
# of being skipped as "binary" or breaking -w; non-ASCII letters count as word boundaries, which can only
# add matches, never drop them.
fold() { python3 -c 'import sys; b=sys.stdin.buffer.read().decode("utf-8","surrogateescape"); sys.stdout.buffer.write(b.casefold().encode("utf-8","surrogateescape"))'; }
for f in words substr; do fold < "$dir/$f" > "$dir/$f.cf"; done
fold > "$dir/input"
{
  [ -s "$dir/words.cf" ] && LC_ALL=C grep -a -n -w -F -f "$dir/words.cf" "$dir/input" | LC_ALL=C cut -d: -f1
  [ -s "$dir/substr.cf" ] && LC_ALL=C grep -a -n -F -f "$dir/substr.cf" "$dir/input" | LC_ALL=C cut -d: -f1
} | sort -n -u
exit 0
