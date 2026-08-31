#!/usr/bin/env python3
"""Validate the human-authored final visual signoff contract."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

from pptx import Presentation

from common import load_validated_json, sha256_file

SKILL_ROOT = Path(__file__).resolve().parents[1]
SIGNOFF_SCHEMA = SKILL_ROOT / "schemas" / "visual_signoff.schema.json"
REQUIRED_CHECKS = {
    "rendered_all_slides",
    "checked_slide_overflow",
    "checked_alignment",
    "checked_fonts",
    "checked_images",
    "checked_editability",
}


def _same_file_label(declared: str, actual: Path) -> bool:
    declared_path = Path(declared)
    if declared_path.exists():
        return declared_path.resolve() == actual.resolve()
    return declared_path.name == actual.name


def validate_visual_signoff(
    signoff_path: str | Path,
    candidate_path: str | Path,
    source_path: str | Path | None = None,
) -> dict[str, Any]:
    signoff = load_validated_json(signoff_path, SIGNOFF_SCHEMA, label="visual_signoff.json")
    candidate = Path(candidate_path).resolve()
    source = Path(source_path).resolve() if source_path else None
    candidate_count = len(Presentation(str(candidate)).slides)
    expected_slides = set(range(1, candidate_count + 1))
    reviewed_slides = set(int(value) for value in signoff["reviewed_slides"])
    if signoff["status"] != "approved":
        raise PermissionError("visual_signoff.json status is not approved")
    if reviewed_slides != expected_slides:
        raise ValueError(
            f"visual_signoff.json reviewed_slides must cover all candidate slides: expected {sorted(expected_slides)}, got {sorted(reviewed_slides)}"
        )
    missing_checks = REQUIRED_CHECKS - set(signoff["confirmed_checks"])
    if missing_checks:
        raise ValueError(f"visual_signoff.json is missing confirmed_checks: {sorted(missing_checks)}")
    if not _same_file_label(signoff["candidate_file"], candidate):
        raise ValueError("visual_signoff.json candidate_file does not match the candidate deck")
    if source is not None and not _same_file_label(signoff["source_file"], source):
        raise ValueError("visual_signoff.json source_file does not match the source deck")
    if signoff["candidate_sha256"].lower() != sha256_file(candidate):
        raise ValueError("visual_signoff.json candidate_sha256 does not match the candidate deck")
    if source is not None and signoff["source_sha256"].lower() != sha256_file(source):
        raise ValueError("visual_signoff.json source_sha256 does not match the source deck")
    return {
        "approved": True,
        "reviewer": signoff["reviewer"],
        "reviewed_slides": sorted(reviewed_slides),
        "confirmed_checks": sorted(signoff["confirmed_checks"]),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate an approved final visual signoff JSON.")
    parser.add_argument("--signoff", required=True)
    parser.add_argument("--candidate", required=True)
    parser.add_argument("--source")
    args = parser.parse_args()
    try:
        result = validate_visual_signoff(args.signoff, args.candidate, args.source)
        print(f"Visual signoff: approved by {result['reviewer']}")
        return 0
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
