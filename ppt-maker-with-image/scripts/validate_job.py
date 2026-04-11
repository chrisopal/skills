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


def find_missing_required_fields(data: dict) -> list[str]:
    return [field for field in REQUIRED_FIELDS if is_missing(data.get(field))]


def has_confirmed_template(data: dict) -> bool:
    if not is_missing(data.get("template_id")) or not is_missing(data.get("template_name")):
        return True
    style = str(data.get("style", "")).strip()
    if not style:
        return False
    known_aliases = {
        "慧新",
        "慧新-产品及解决方案介绍",
        "慧新产品及解决方案介绍",
        "慧新-市场宣传",
        "慧新市场宣传",
        "慧新-内部会议",
        "慧新内部会议",
    }
    return style in known_aliases


def validate_job_data(
    data: dict,
    *,
    require_confirmation: bool = False,
    require_template_confirmation: bool = False,
) -> list[str]:
    missing = find_missing_required_fields(data)

    page_count = data.get("page_count")
    if page_count is not None and (not isinstance(page_count, int) or page_count <= 0):
        missing.append("page_count(valid positive integer)")

    if require_confirmation and not data.get("requirement_confirmed"):
        missing.append("requirement_confirmed")

    if require_template_confirmation and not has_confirmed_template(data):
        missing.append("template_id/template_name(confirmed template selection)")

    return missing


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    job_path = Path(args.job).expanduser().resolve()
    data = json.loads(job_path.read_text(encoding="utf-8"))

    missing = validate_job_data(
        data,
        require_confirmation=True,
        require_template_confirmation=True,
    )
    if missing:
        print("[MISSING] Required fields or confirmations:")
        for field in missing:
            print(f"- {field}")
        return 1

    print("[OK] Job input is complete enough to continue.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
