#!/usr/bin/env bash
# Reads text on stdin and prints the line numbers that contain a denylist term, one per line.
# Never prints the terms or the matched text.
#   - terms with a dot (domains) match as case-insensitive substrings
#   - other terms match as case-insensitive whole words (word boundaries), so a common word that merely
#     contains a term does not match
# Terms come from $DENYLIST (one per line, used in CI from a secret) or $DENYLIST_FILE
# (default ~/.config/oncall-resident/denylist.txt).
# Exit status: 0 = scanned (matches, if any, on stdout); 2 = could not scan (no/unreadable/empty denylist,
# or any step failed). Callers must treat 2 as a failure, never as "no matches".
set -uo pipefail
die() { echo "denylist: $1" >&2; exit 2; }
dir=$(mktemp -d) || die "cannot create temp dir"
trap 'rm -rf "$dir"' EXIT

list="${DENYLIST_FILE:-$HOME/.config/oncall-resident/denylist.txt}"
if [ -n "${DENYLIST:-}" ]; then
  printf '%s\n' "$DENYLIST" > "$dir/all" || die "cannot write terms"
elif [ -s "$list" ]; then
  cat "$list" > "$dir/all" || die "cannot read denylist"
else
  die "not found (set DENYLIST or create ~/.config/oncall-resident/denylist.txt)"
fi

# trim whitespace, drop blanks and comments, split by kind
sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//' -e '/^$/d' -e '/^#/d' "$dir/all" > "$dir/clean" || die "cannot prepare terms"
[ -s "$dir/clean" ] || die "no terms after removing blanks and comments"
LC_ALL=C grep -a -F '.' "$dir/clean" > "$dir/substr"; [ $? -le 1 ] || die "cannot split terms"
LC_ALL=C grep -a -v -F '.' "$dir/clean" > "$dir/words"; [ $? -le 1 ] || die "cannot split terms"

# Case folding is Unicode-aware and done before matching (terms and input alike); invalid UTF-8 bytes are
# kept as-is. Matching is then byte-oriented (LC_ALL=C, -a), so such input is still scanned as text instead
# of being skipped as "binary" or breaking -w; non-ASCII letters count as word boundaries, which can only
# add matches, never drop them.
fold() { python3 -c 'import sys; b=sys.stdin.buffer.read().decode("utf-8","surrogateescape"); sys.stdout.buffer.write(b.casefold().encode("utf-8","surrogateescape"))'; }
for f in words substr; do fold < "$dir/$f" > "$dir/$f.cf" || die "cannot fold terms"; done
fold > "$dir/input" || die "cannot read input"

# grep: 0 = match, 1 = no match, >1 = error
scan() { # mode-flags patterns-file
  [ -s "$2" ] || return 0
  LC_ALL=C grep -a -n $1 -F -f "$2" "$dir/input" > "$dir/hits.raw"
  [ $? -le 1 ] || die "grep failed"
  LC_ALL=C cut -d: -f1 "$dir/hits.raw" >> "$dir/hits" || die "cannot extract line numbers"
}
: > "$dir/hits"
scan -w "$dir/words.cf"
scan "" "$dir/substr.cf"
sort -n -u "$dir/hits" || die "cannot sort results"
