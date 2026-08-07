#!/usr/bin/env bash
set -euo pipefail
export PYTHONDONTWRITEBYTECODE=1

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT="${1:-$ROOT/.smoke-test}"
rm -rf "$OUT"
mkdir -p "$OUT"

python "$ROOT/scripts/check_schemas.py" --root "$ROOT"
python -m unittest discover -s "$ROOT/tests" -p 'test_*.py' -v
python "$ROOT/tests/create_sample_deck.py" --out "$OUT/source.pptx"
python "$ROOT/scripts/create_review_bundle.py" "$OUT/source.pptx" --out "$OUT/review"
python "$ROOT/scripts/normalize_pptx.py" \
  "$OUT/source.pptx" "$OUT/normalized.pptx" \
  --tokens "$ROOT/examples/style_tokens.industrial-consulting.json" \
  --manifest "$ROOT/examples/change_manifest.l1.json" \
  --apply-role-sizes \
  --standardize-title-position \
  --log "$OUT/normalization_log.json"
python "$ROOT/scripts/validate_pptx.py" \
  --original "$OUT/source.pptx" \
  --candidate "$OUT/normalized.pptx" \
  --manifest "$ROOT/examples/change_manifest.l1.json" \
  --out "$OUT/validation"

echo "Smoke test completed: $OUT"
