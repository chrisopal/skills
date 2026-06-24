#!/usr/bin/env python3
"""Validate requirements-to-delivery artifact workspaces."""

from __future__ import annotations

import argparse
import re
from pathlib import Path


PROFILES = {
    "intake": ["00-intake.md"],
    "research": ["00-intake.md", "01-research-plan.md", "02-requirements-analysis.md"],
    "solution": ["03-technical-solution.md"],
    "srs": ["04-srs.md"],
    "design": ["05-system-design.md"],
    "prototype": ["06-prototype/prototype-brief.md"],
    "development": ["07-development-plan.md", "08-test-spec.md"],
    "acceptance": ["09-acceptance-report.md", "traceability-matrix.md"],
}

FULL_ORDER = [
    "intake",
    "research",
    "solution",
    "srs",
    "design",
    "prototype",
    "development",
    "acceptance",
]

ID_CHECKS = {
    "01-research-plan.md": [r"\bEVID-\d{3}\b", r"\bBR-\d{3}\b"],
    "03-technical-solution.md": [r"\bDEC-\d{3}\b"],
    "04-srs.md": [r"\bFR-\d{3}\b", r"\bNFR-\d{3}\b"],
    "05-system-design.md": [r"\bDESIGN-\d{3}\b", r"\bAPI-\d{3}\b", r"\bDATA-\d{3}\b"],
    "07-development-plan.md": [r"\bTASK-\d{3}\b"],
    "08-test-spec.md": [r"\bTEST-\d{3}\b"],
    "traceability-matrix.md": [r"\bEVID-\d{3}\b", r"\bBR-\d{3}\b", r"\bFR-\d{3}\b", r"\bTASK-\d{3}\b", r"\bTEST-\d{3}\b"],
}


def files_for_profile(profile: str) -> list[str]:
    if profile == "full":
        files: list[str] = []
        for key in FULL_ORDER:
            files.extend(PROFILES[key])
        return files
    return PROFILES[profile]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("workspace", help="Delivery workspace directory")
    parser.add_argument(
        "--profile",
        choices=["full", *PROFILES.keys()],
        default="full",
        help="Artifact set to validate",
    )
    args = parser.parse_args()

    workspace = Path(args.workspace)
    errors: list[str] = []
    warnings: list[str] = []

    if not workspace.exists():
        errors.append(f"workspace does not exist: {workspace}")
    elif not workspace.is_dir():
        errors.append(f"workspace is not a directory: {workspace}")

    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1

    required_files = files_for_profile(args.profile)
    for rel_path in required_files:
        path = workspace / rel_path
        if not path.exists():
            errors.append(f"missing required artifact: {rel_path}")
            continue
        text = path.read_text(encoding="utf-8")
        if "{{" in text or "}}" in text:
            errors.append(f"unrendered template placeholder in: {rel_path}")
        for pattern in ID_CHECKS.get(rel_path, []):
            if not re.search(pattern, text):
                errors.append(f"missing ID pattern {pattern!r} in: {rel_path}")
        if "Unconfirmed" in text or "未确认" in text:
            warnings.append(f"contains unconfirmed assumptions: {rel_path}")

    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        for warning in warnings:
            print(f"WARNING: {warning}")
        return 1

    print(f"OK: {workspace} profile={args.profile} files={len(required_files)}")
    for warning in warnings:
        print(f"WARNING: {warning}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
