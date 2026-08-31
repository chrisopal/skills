#!/usr/bin/env python3
"""Compose narrative and visual review payloads into the canonical report contract."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Iterable

from common import load_json, validate_json_data, write_json

SKILL_ROOT = Path(__file__).resolve().parents[1]
REPORT_SCHEMA = SKILL_ROOT / "schemas" / "review_report.schema.json"


def unwrap(payload: dict[str, Any], key: str) -> dict[str, Any]:
    value = payload.get(key, payload)
    if not isinstance(value, dict):
        raise ValueError(f"{key} review payload must be a JSON object")
    return value


def compose_review_report(
    *,
    source_file: str,
    narrative_path: str | Path,
    visual_path: str | Path,
    scores_path: str | Path,
    output_path: str | Path,
    executive_summary: str,
    recommended_level: str,
    manual_review_required: Iterable[str] = (),
    unresolved_assumptions: Iterable[str] = (),
) -> dict[str, Any]:
    """Merge separately produced review payloads and validate before writing."""
    narrative = unwrap(load_json(narrative_path), "narrative")
    visual = unwrap(load_json(visual_path), "visual")
    scores = load_json(scores_path)
    report = {
        "version": "1.0.0",
        "source_file": source_file,
        "executive_summary": executive_summary,
        "scores": scores,
        "narrative": narrative,
        "visual": visual,
        "recommended_level": recommended_level,
        "manual_review_required": list(dict.fromkeys(str(item) for item in manual_review_required)),
        "unresolved_assumptions": list(dict.fromkeys(str(item) for item in unresolved_assumptions)),
    }
    report = validate_json_data(report, REPORT_SCHEMA, label="review_report.json")
    write_json(output_path, report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Compose narrative and visual review inputs into review_report.json.")
    parser.add_argument("--source", required=True)
    parser.add_argument("--narrative", required=True)
    parser.add_argument("--visual", required=True)
    parser.add_argument("--scores", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--executive-summary", required=True)
    parser.add_argument("--recommended-level", required=True, choices=["L0", "L1", "L2", "L3"])
    parser.add_argument("--manual-review", action="append", default=[])
    parser.add_argument("--unresolved-assumption", action="append", default=[])
    args = parser.parse_args()

    try:
        report = compose_review_report(
            source_file=args.source,
            narrative_path=args.narrative,
            visual_path=args.visual,
            scores_path=args.scores,
            output_path=args.out,
            executive_summary=args.executive_summary,
            recommended_level=args.recommended_level,
            manual_review_required=args.manual_review,
            unresolved_assumptions=args.unresolved_assumption,
        )
        print(f"Wrote {args.out} for {len(report['narrative']['slides'])} narrative slides")
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
