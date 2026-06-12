#!/usr/bin/env python3
"""Validate the WeChat Official Account skill bundle structure."""

from __future__ import annotations

import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXPECTED = [
    "wechat-topic-planner",
    "wechat-article-writer",
    "wechat-article-layout",
    "wechat-article-reviewer",
    "wechat-account-operator",
    "wechat-daily-pipeline",
]


def main() -> int:
    errors: list[str] = []
    for name in EXPECTED:
        skill = ROOT / name / "SKILL.md"
        if not skill.exists():
            errors.append(f"missing {skill.relative_to(ROOT)}")
            continue
        text = skill.read_text(encoding="utf-8")
        if not re.match(r"^---\nname: [a-z0-9-]+\ndescription: .+\n---\n", text):
            errors.append(f"invalid frontmatter: {skill.relative_to(ROOT)}")
        if f"name: {name}" not in text:
            errors.append(f"name mismatch: {skill.relative_to(ROOT)}")
    for ref in ["account-positioning.md", "style-system.md", "review-checklist.md"]:
        if not (ROOT / "references" / ref).exists():
            errors.append(f"missing references/{ref}")
    writer = (ROOT / "wechat-article-writer" / "SKILL.md").read_text(encoding="utf-8")
    if "正文插图" not in writer or "Content Illustration Brief" not in writer:
        errors.append("writer skill must define content illustration brief")
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    print(f"ok: {len(EXPECTED)} skills validated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
