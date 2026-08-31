#!/usr/bin/env bash
set -euo pipefail
export PYTHONDONTWRITEBYTECODE=1

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT="${1:-$ROOT/.smoke-test}"
PYTHON_BIN="${PYTHON_BIN:-python3}"
rm -rf "$OUT"
mkdir -p "$OUT"

"$PYTHON_BIN" "$ROOT/scripts/check_schemas.py" --root "$ROOT"
"$PYTHON_BIN" -m unittest discover -s "$ROOT/tests" -p 'test_*.py' -v
"$PYTHON_BIN" "$ROOT/tests/create_sample_deck.py" --out "$OUT/source.pptx"
"$PYTHON_BIN" "$ROOT/scripts/create_review_bundle.py" "$OUT/source.pptx" --out "$OUT/review"
"$PYTHON_BIN" "$ROOT/scripts/normalize_pptx.py" \
  "$OUT/source.pptx" "$OUT/normalized.pptx" \
  --tokens "$ROOT/examples/style_tokens.industrial-consulting.json" \
  --manifest "$ROOT/examples/change_manifest.l1.json" \
  --apply-role-sizes \
  --standardize-title-position \
  --log "$OUT/normalization_log.json"
"$PYTHON_BIN" "$ROOT/tests/create_visual_signoff.py" \
  --source "$OUT/source.pptx" \
  --candidate "$OUT/normalized.pptx" \
  --out "$OUT/visual_signoff.json"
"$PYTHON_BIN" "$ROOT/scripts/validate_pptx.py" \
  --original "$OUT/source.pptx" \
  --candidate "$OUT/normalized.pptx" \
  --manifest "$ROOT/examples/change_manifest.l1.json" \
  --out "$OUT/validation" \
  --visual-signoff "$OUT/visual_signoff.json"

echo "Smoke test completed: $OUT"
