#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path


REQUIRED_FIELDS = [
    "topic",
    "target_audience",
    "purpose",
    "style",
    "page_count",
]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate a PPT job JSON file.")
    parser.add_argument("job", help="Path to the job JSON file")
    return parser


def is_missing(value) -> bool:
    if value is None:
        return True
    if isinstance(value, str) and not value.strip():
        return True
    if isinstance(value, list) and not value:
        return True
    return False


def find_missing_fields(data: dict) -> list[str]:
    return [field for field in REQUIRED_FIELDS if is_missing(data.get(field))]


def validate_job_data(data: dict) -> list[str]:
    missing = find_missing_fields(data)
    page_count = data.get("page_count")
    if page_count is not None and (not isinstance(page_count, int) or page_count <= 0):
        missing.append("page_count(valid positive integer)")
    return missing


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    job_path = Path(args.job).expanduser().resolve()
    data = json.loads(job_path.read_text(encoding="utf-8"))

    missing = validate_job_data(data)
    if missing:
        print("[MISSING] Required fields:")
        for field in missing:
            print(f"- {field}")
        return 1

    print("[OK] Job input is complete enough to continue.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
