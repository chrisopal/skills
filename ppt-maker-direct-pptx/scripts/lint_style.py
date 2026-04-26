"""Style consistency lint pass: cross-deck statistics about color/typography drift.

Checks:
  - color palette compliance: every #RRGGBB / #RGB color used across slide_specs
    must appear in master_style.color_strategy
  - title font scale unified: all slides where intent_status == "locked" must
    declare the same title font_size (when given)
  - forbidden elements: each forbidden_elements regex from master_style is
    searched against the JSON-serialized slide_specs; any hit is flagged
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parent.parent

_HEX_RE = re.compile(r"#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})\b")


def _load_local(name: str, rel_path: str):
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, SKILL_ROOT / rel_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


lint_common = _load_local("lint_common", "scripts/lib/lint_common.py")


def _expand_hex(value: str) -> str:
    if len(value) == 4:
        return "#" + "".join(ch * 2 for ch in value[1:])
    return value


def _allowed_palette(master_style: dict | None) -> set[str]:
    if not master_style:
        return set()
    out: set[str] = set()
    for value in (master_style.get("color_strategy") or {}).values():
        if isinstance(value, str) and value.startswith("#"):
            out.add(_expand_hex(value).upper())
    return out


def _walk_strings(node) -> list[str]:
    out: list[str] = []
    stack = [node]
    while stack:
        cur = stack.pop()
        if isinstance(cur, dict):
            stack.extend(cur.values())
        elif isinstance(cur, list):
            stack.extend(cur)
        elif isinstance(cur, str):
            out.append(cur)
    return out


def _walk_strings_per_slide(slide_specs: dict) -> dict[int | None, list[str]]:
    out: dict[int | None, list[str]] = {}
    for slide in slide_specs.get("slides", []):
        page_no = slide.get("page_no") if isinstance(slide.get("page_no"), int) else None
        out.setdefault(page_no, []).extend(_walk_strings(slide))
    return out


def _check_palette_compliance(slide_specs: dict, master_style: dict | None) -> list:
    out = []
    palette = _allowed_palette(master_style)
    if not palette:
        return out
    for page_no, strings in _walk_strings_per_slide(slide_specs).items():
        used: set[str] = set()
        for value in strings:
            for match in _HEX_RE.finditer(value):
                used.add(_expand_hex(match.group(0)).upper())
        offenders = used - palette
        if offenders:
            out.append(lint_common.LintResult(
                category="style_consistency",
                rule="palette_compliance",
                severity="fail",
                detail=(
                    f"slide uses hex colors outside master_style palette: "
                    f"{sorted(offenders)}"
                ),
                page_no=page_no,
                auto_fixable=True,
            ))
    return out


def _title_font_size(slide: dict) -> float | None:
    visible = (slide.get("visible_content") or {})
    title = visible.get("title")
    if isinstance(title, dict):
        size = title.get("font_size")
        if isinstance(size, (int, float)):
            return float(size)
    blocks = visible.get("blocks") or []
    for block in blocks:
        role = (block or {}).get("role")
        if role == "title":
            size = (block or {}).get("font_size")
            if isinstance(size, (int, float)):
                return float(size)
    return None


def _check_title_font_uniform(slide_specs: dict) -> list:
    out = []
    sizes_per_size: dict[float, list[int]] = defaultdict(list)
    for slide in slide_specs.get("slides", []):
        if (slide.get("intent_status") or "draft") != "locked":
            continue
        size = _title_font_size(slide)
        if size is None:
            continue
        page_no = slide.get("page_no")
        if isinstance(page_no, int):
            sizes_per_size[size].append(page_no)
    if len(sizes_per_size) > 1:
        # All locked slides should share one title font size.
        sample = ", ".join(f"{size}: {pages}" for size, pages in sorted(sizes_per_size.items()))
        out.append(lint_common.LintResult(
            category="style_consistency",
            rule="title_font_scale_unified",
            severity="warn",
            detail=f"locked slides disagree on title font size — {sample}",
            auto_fixable=False,
        ))
    return out


def _check_forbidden_elements(slide_specs: dict, master_style: dict | None) -> list:
    out = []
    forbidden = (master_style or {}).get("forbidden_elements") or []
    if not forbidden:
        return out
    serialized_per_slide = {
        slide.get("page_no"): json.dumps(slide, ensure_ascii=False)
        for slide in slide_specs.get("slides", [])
    }
    for page_no, blob in serialized_per_slide.items():
        for forbidden_value in forbidden:
            if not isinstance(forbidden_value, str) or not forbidden_value.strip():
                continue
            if forbidden_value in blob:
                out.append(lint_common.LintResult(
                    category="style_consistency",
                    rule="forbidden_element_present",
                    severity="fail",
                    detail=f"slide_specs mention forbidden element {forbidden_value!r}",
                    page_no=page_no if isinstance(page_no, int) else None,
                    auto_fixable=False,
                ))
    return out


def lint_style(slide_specs: dict, *, master_style: dict | None = None) -> list:
    out: list = []
    out.extend(_check_palette_compliance(slide_specs, master_style))
    out.extend(_check_title_font_uniform(slide_specs))
    out.extend(_check_forbidden_elements(slide_specs, master_style))
    return out


def _read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Cross-deck style consistency lint.")
    parser.add_argument("--slide-specs", required=True, type=Path)
    parser.add_argument("--master-style", type=Path)
    args = parser.parse_args(argv)
    results = lint_style(
        _read(args.slide_specs),
        master_style=_read(args.master_style) if args.master_style else None,
    )
    fails = [r for r in results if r.severity == "fail"]
    print(json.dumps({
        "results": [r.to_result_dict() for r in results],
        "summary": {
            "fail": len(fails),
            "warn": sum(r.severity == "warn" for r in results),
        },
    }, ensure_ascii=False, indent=2))
    return 0 if not fails else 2


if __name__ == "__main__":
    sys.exit(main())
