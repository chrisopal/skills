"""Add default status fields to legacy outline/slide_prompts/slide_specs artifacts.

The schemas added in Phase 1 introduce optional status fields (outline_status,
intent_status, image_placeholder.status, layout_mode). Legacy artifacts produced
before Phase 1 don't have them. This script reads the three artifact files in a
job directory, fills in defaults for any missing status fields, and writes the
files back in place.

Usage:
    python scripts/migrate_legacy_artifacts.py path/to/artifacts_dir
    python scripts/migrate_legacy_artifacts.py path/to/artifacts_dir --dry-run

The script is idempotent: running it twice leaves the artifacts unchanged after
the first migration.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

OUTLINE_FILE = "outline.json"
SLIDE_PROMPTS_FILE = "slide_prompts.json"
SLIDE_SPECS_FILE = "slide_specs.json"


@dataclass
class MigrationResult:
    file: str
    changed: bool
    additions: int


def _migrate_outline(data: dict) -> int:
    additions = 0
    for slide in data.get("slides", []):
        if "outline_status" not in slide:
            slide["outline_status"] = "draft"
            additions += 1
    return additions


def _migrate_slide_prompts(data: dict) -> int:
    additions = 0
    for slide in data.get("slides", []):
        if "intent_status" not in slide:
            slide["intent_status"] = "draft"
            additions += 1
        if "layout_mode" not in slide:
            slide["layout_mode"] = "custom"
            additions += 1
    return additions


def _migrate_slide_specs(data: dict) -> int:
    additions = 0
    for slide in data.get("slides", []):
        for placeholder in slide.get("image_placeholders", []):
            if "status" not in placeholder:
                placeholder["status"] = "placeholder"
                additions += 1
    return additions


_MIGRATIONS: dict[str, Callable[[dict], int]] = {
    OUTLINE_FILE: _migrate_outline,
    SLIDE_PROMPTS_FILE: _migrate_slide_prompts,
    SLIDE_SPECS_FILE: _migrate_slide_specs,
}


def migrate_directory(artifacts_dir: Path, *, dry_run: bool = False) -> list[MigrationResult]:
    if not artifacts_dir.is_dir():
        raise NotADirectoryError(f"Not a directory: {artifacts_dir}")

    results: list[MigrationResult] = []
    for filename, migrator in _MIGRATIONS.items():
        path = artifacts_dir / filename
        if not path.exists():
            continue
        original_text = path.read_text(encoding="utf-8")
        data = json.loads(original_text)
        additions = migrator(data)
        new_text = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
        changed = additions > 0 and new_text != original_text
        if changed and not dry_run:
            path.write_text(new_text, encoding="utf-8")
        results.append(MigrationResult(file=filename, changed=changed, additions=additions))
    return results


def _format_results(results: list[MigrationResult], *, dry_run: bool) -> str:
    if not results:
        return "no migratable artifacts found"
    lines = []
    prefix = "[dry-run] " if dry_run else ""
    for r in results:
        verb = "would update" if dry_run and r.changed else ("updated" if r.changed else "unchanged")
        lines.append(f"{prefix}{r.file}: {verb} ({r.additions} field(s) defaulted)")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Add default status fields to legacy artifacts.")
    parser.add_argument("artifacts_dir", type=Path, help="Directory containing the artifact JSONs")
    parser.add_argument("--dry-run", action="store_true", help="Report changes without writing")
    args = parser.parse_args(argv)

    results = migrate_directory(args.artifacts_dir, dry_run=args.dry_run)
    print(_format_results(results, dry_run=args.dry_run))
    return 0


if __name__ == "__main__":
    sys.exit(main())
