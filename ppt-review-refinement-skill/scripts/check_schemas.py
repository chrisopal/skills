#!/usr/bin/env python3
"""Validate bundled JSON templates and examples against their schemas."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]

CASES = [
    ("templates/deck_context.template.json", "schemas/deck_context.schema.json"),
    ("templates/change_manifest.template.json", "schemas/change_manifest.schema.json"),
    ("templates/style_tokens.template.json", "schemas/style_tokens.schema.json"),
    ("examples/context.solution-deck.json", "schemas/deck_context.schema.json"),
    ("examples/change_manifest.l1.json", "schemas/change_manifest.schema.json"),
    ("examples/style_tokens.industrial-consulting.json", "schemas/style_tokens.schema.json"),
    ("examples/review_report.example.json", "schemas/review_report.schema.json"),
    ("examples/validation_report.example.json", "schemas/validation_report.schema.json"),
    ("templates/refinement_plan.template.json", "schemas/refinement_plan.schema.json"),
    ("templates/pilot_confirmation.template.json", "schemas/pilot_confirmation.schema.json"),
    ("templates/visual_signoff.template.json", "schemas/visual_signoff.schema.json"),
    ("examples/pilot_confirmation.example.json", "schemas/pilot_confirmation.schema.json"),
    ("examples/visual_signoff.example.json", "schemas/visual_signoff.schema.json"),
]


def load(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate skill JSON examples/templates.")
    parser.add_argument("--root", default=str(ROOT))
    args = parser.parse_args()
    root = Path(args.root).resolve()
    failed = False
    for data_rel, schema_rel in CASES:
        data_path = root / data_rel
        schema_path = root / schema_rel
        data = load(data_path)
        schema = load(schema_path)
        validator = Draft202012Validator(schema)
        errors = sorted(validator.iter_errors(data), key=lambda e: list(e.path))
        if errors:
            failed = True
            print(f"FAIL {data_rel} -> {schema_rel}")
            for error in errors:
                location = ".".join(str(p) for p in error.path) or "<root>"
                print(f"  {location}: {error.message}")
        else:
            print(f"PASS {data_rel}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
