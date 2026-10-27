#!/usr/bin/env bash
set -euo pipefail
root=$(git rev-parse --show-toplevel)
printf '#!/usr/bin/env bash\nexec "%s/scripts/scan.sh" --staged\n' "$root" > "$root/.git/hooks/pre-commit"
printf '#!/usr/bin/env bash\nexec "%s/scripts/check-msg.sh" "$1"\n' "$root" > "$root/.git/hooks/commit-msg"
chmod +x "$root/.git/hooks/pre-commit" "$root/.git/hooks/commit-msg"
echo "hooks installed"
