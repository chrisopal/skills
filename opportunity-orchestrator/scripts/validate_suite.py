#!/usr/bin/env python3
"""Check discoverable entries, local references and shared runtime availability."""
from pathlib import Path
import re
import sys

from install import SKILLS


def main():
    root = Path(__file__).resolve().parents[2]
    errors = []
    for name in SKILLS:
        entry = root / name / "SKILL.md"
        if not entry.is_file():
            errors.append(f"Missing entry: {entry}")
            continue
        text = entry.read_text(encoding="utf-8")
        if not text.startswith("---\n") or not re.search(rf"^name: {re.escape(name)}$", text, re.M):
            errors.append(f"Invalid frontmatter/name: {entry}")
        if not re.search(r"^description: \S", text, re.M):
            errors.append(f"Missing description: {entry}")
        for doc in (root / name).rglob("*.md"):
            for target in re.findall(r"\]\(([^)]+)\)", doc.read_text(encoding="utf-8")):
                if "://" in target or target.startswith("#"):
                    continue
                path = target.split("#", 1)[0]
                if path and not (doc.parent / path).exists():
                    errors.append(f"Broken link: {doc.relative_to(root)} -> {target}")
    if not (root / "opportunity-analysis-skill/src/opportunity_skill/cli.py").is_file():
        errors.append("Shared runtime missing")
    if errors:
        print("\n".join(errors), file=sys.stderr)
        raise SystemExit(1)
    print(f"suite validated: {len(SKILLS)} skill entries, local links and shared runtime")


if __name__ == "__main__":
    main()
