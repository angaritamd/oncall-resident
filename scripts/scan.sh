#!/usr/bin/env bash
# Repo scanner: gitleaks + external denylist + PHI patterns.
#   scripts/scan.sh --staged   scan staged changes (pre-commit hook)
#   scripts/scan.sh --all      scan every tracked file (CI)
# The denylist lives OUTSIDE the repo: $DENYLIST_FILE (default ~/.config/oncall-resident/denylist.txt)
# or the DENYLIST env var (one term per line, used in CI from a secret). Matched terms are never printed.
set -uo pipefail
mode="${1:---staged}"
cd "$(git rev-parse --show-toplevel)"
fail=0

if [ "$mode" = "--staged" ]; then
  files=$(git diff --cached --name-only --diff-filter=ACMR)
else
  files=$(git ls-files)
fi
[ -z "$files" ] && exit 0

# 1. gitleaks
if command -v gitleaks >/dev/null; then
  if [ "$mode" = "--staged" ]; then
    gitleaks git --pre-commit --staged --redact --no-banner -l warn . || fail=1
  else
    gitleaks git --redact --no-banner -l warn . || fail=1
  fi
else
  echo "scan: gitleaks not installed (brew install gitleaks)" >&2; fail=1
fi

content() { if [ "$mode" = "--staged" ]; then git show ":$1" 2>/dev/null; else cat "$1"; fi; }

# 2. denylist: matching rules live in scripts/denylist-match.sh (only file:line is reported)
match="$(dirname "$0")/denylist-match.sh"
if ! printf '' | "$match" >/dev/null; then fail=1; fi

# 3. PHI patterns (extended regex). Synthetic demo data must never match these.
phi_patterns=(
  '\b[0-9]{3}-[0-9]{2}-[0-9]{4}\b'                       # US SSN
  '\b(MRN|NHC|historia cl[ií]nica)[ :#]*[0-9]{5,}'       # record numbers
  '\b(C\.?C\.?|c[eé]dula)[ :#]*[0-9]{6,10}\b'            # national ID (CO)
  '\(0010,0010\)[^\n]*[A-Za-z]{2,}\^[A-Za-z]{2,}'        # DICOM PatientName dumps
  '\bPatientBirthDate\b[^\n]*[12][0-9]{7}'               # DICOM birth dates
)

while IFS= read -r f; do
  [ -f "$f" ] || continue
  lower=$(printf '%s' "$f" | tr '[:upper:]' '[:lower:]')
  case "$lower" in
    *.dcm|*.dicom|*.ima|*dicomdir) echo "scan: DICOM file must not be committed: $f" >&2; fail=1; continue ;;
  esac
  if [ "$(content "$f" 2>/dev/null | head -c 132 | tail -c 4)" = "DICM" ]; then
    echo "scan: DICOM content must not be committed: $f" >&2; fail=1; continue
  fi
  case "$f" in
    LICENSE|*.png|*.jpg|*.jpeg|*.ico|*.woff2|package-lock.json|uv.lock) continue ;;
  esac
  body=$(content "$f")
  for n in $(printf '%s\n' "$body" | "$match" 2>/dev/null); do
    echo "$f:$n: término de la denylist" >&2; fail=1
  done
  [ "$f" = "scripts/scan.sh" ] && continue
  for p in "${phi_patterns[@]}"; do
    hits=$(printf '%s' "$body" | grep -n -i -E -e "$p" | cut -d: -f1 | tr '\n' ' ')
    [ -n "$hits" ] && { echo "scan: possible PHI in $f (lines: $hits)" >&2; fail=1; }
  done
done <<< "$files"

# commit messages are checked by the commit-msg hook (scripts/check-msg.sh)
[ $fail -eq 0 ] && echo "scan: ok ($mode)"
exit $fail
