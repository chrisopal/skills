#!/usr/bin/env python3
"""Create a requirements-to-delivery artifact workspace."""

from __future__ import annotations

import argparse
import datetime as dt
import re
from pathlib import Path


TEMPLATE_DIR = Path(__file__).resolve().parents[1] / "assets" / "templates"


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9._-]+", "-", value.strip()).strip("-").lower()
    return slug or "delivery-project"


def render_template(text: str, project_name: str, date: str) -> str:
    return text.replace("{{PROJECT_NAME}}", project_name).replace("{{DATE}}", date)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project", help="Project name or slug")
    parser.add_argument("--root", default="delivery", help="Output root directory")
    parser.add_argument("--force", action="store_true", help="Overwrite existing files")
    args = parser.parse_args()

    project_slug = slugify(args.project)
    project_name = args.project.strip() or project_slug
    output_dir = Path(args.root) / project_slug
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "06-prototype").mkdir(exist_ok=True)

    today = dt.date.today().isoformat()
    created: list[Path] = []
    skipped: list[Path] = []

    for template in sorted(TEMPLATE_DIR.glob("*.md")):
        target_name = template.name
        if target_name == "06-prototype-brief.md":
            target = output_dir / "06-prototype" / "prototype-brief.md"
        else:
            target = output_dir / target_name

        if target.exists() and not args.force:
            skipped.append(target)
            continue

        target.write_text(
            render_template(template.read_text(encoding="utf-8"), project_name, today),
            encoding="utf-8",
        )
        created.append(target)

    print(f"workspace: {output_dir}")
    print(f"created: {len(created)}")
    if skipped:
        print(f"skipped_existing: {len(skipped)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
