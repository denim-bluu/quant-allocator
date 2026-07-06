#!/usr/bin/env bash
# Publication-readiness scan (REPORT ONLY).
#
# A HUMAN reviews every hit and decides — this script never blocks, never
# rewrites history, and always exits 0.
#
# The committed TERMS below are GENERIC provenance markers only. Employer or
# manager names must NEVER be committed to this public repo; add them to the
# gitignored file tools/.publication_terms (one term per line, '#' comments
# allowed) before running the scan locally.
set -u

TERMS=(
  "CONFIDENTIAL"
  "INTERNAL USE ONLY"
  "DO NOT DISTRIBUTE"
  "PROPRIETARY"
)

LOCAL_TERMS_FILE="$(dirname "$0")/.publication_terms"
if [[ -f "$LOCAL_TERMS_FILE" ]]; then
  while IFS= read -r line || [[ -n "$line" ]]; do
    [[ -n "$line" && "$line" != \#* ]] && TERMS+=("$line")
  done < "$LOCAL_TERMS_FILE"
fi

echo "== Publication readiness scan =="
echo "Terms scanned: ${#TERMS[@]} (generic markers + any local terms)"
echo

for term in "${TERMS[@]}"; do
  echo "--- term: ${term} ---"
  echo "[working tree]"
  grep -rniI --exclude-dir=.git --exclude-dir=.venv \
    --exclude-dir=__pycache__ --exclude-dir=_build -- "$term" . \
    || echo "  (no working-tree hits)"
  echo "[git history]"
  git log --all -p -S "$term" 2>/dev/null | grep -i -- "$term" \
    || echo "  (no history hits)"
  echo
done

echo "Scan complete. A human must review every hit above before publishing."
exit 0
