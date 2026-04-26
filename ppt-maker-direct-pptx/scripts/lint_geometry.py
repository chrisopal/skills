"""Geometry lint pass: enforces region containment, non-overlap, and font-size sanity.

Inputs (all optional, individually):
  - slide_specs.json: per-slide layout_regions + element placements
  - master_style.json: typography font-size range

Rules:
  - layout_regions title / content / images all sit inside the 16:9 canvas
  - title vs content vs images regions do not overlap (>0 area)
  - card / placeholder min height ≥ 1.0 inch when carrying bullet text
  - font_size used by any visible block falls inside master_style.typography
    page_title / body_text size hints (best-effort parse)
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parent.parent

CARD_MIN_HEIGHT_IN = 1.0


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
geom = _load_local("geometry", "scripts/lib/geometry.py")


def _parse_font_range(spec: str | None) -> tuple[float, float] | None:
    """Extract a min..max number range from strings like '36-44px, bold'."""

    if not isinstance(spec, str):
        return None
    match = re.search(r"(\d+(?:\.\d+)?)(?:\s*-\s*(\d+(?:\.\d+)?))?", spec)
    if not match:
        return None
    lo = float(match.group(1))
    hi = float(match.group(2)) if match.group(2) else lo
    return (lo, hi)


def _resolve_font_bounds(master_style: dict | None) -> tuple[float, float]:
    """Compute (min, max) font sizes allowed across all typography roles."""

    if not master_style:
        return (8.0, 96.0)
    typography = master_style.get("typography", {}) or {}
    ranges: list[tuple[float, float]] = []
    for value in typography.values():
        rng = _parse_font_range(value if isinstance(value, str) else None)
        if rng:
            ranges.append(rng)
    if not ranges:
        return (8.0, 96.0)
    return (min(lo for lo, _ in ranges), max(hi for _, hi in ranges))


def _check_regions(slide: dict, page_no: int | None) -> list:
    out = []
    layout_regions = slide.get("layout_regions", {})
    rects: list[tuple[str, geom.Rect]] = []
    for name in ("title", "content", "images"):
        rect = geom.rect_from(layout_regions.get(name))
        if rect is None:
            continue
        rects.append((name, rect))
        if not rect.is_in_canvas():
            out.append(lint_common.LintResult(
                category="layout_geometry",
                rule="region_outside_canvas",
                severity="fail",
                detail=f"region '{name}' extends outside 16:9 canvas: {layout_regions.get(name)}",
                page_no=page_no,
                auto_fixable=True,
            ))
    for label_a, label_b, area in geom.collect_overlap_pairs(rects):
        out.append(lint_common.LintResult(
            category="layout_geometry",
            rule="regions_overlap",
            severity="fail",
            detail=f"region '{label_a}' overlaps region '{label_b}' by {area:.3f} sq inch",
            page_no=page_no,
            auto_fixable=True,
        ))
    return out


def _check_element_placements(slide: dict, page_no: int | None) -> list:
    out = []
    blocks = (slide.get("visible_content") or {}).get("blocks") or []
    for idx, block in enumerate(blocks):
        rect = geom.rect_from((block or {}).get("placement"))
        if rect is None:
            continue
        if not rect.is_in_canvas():
            out.append(lint_common.LintResult(
                category="layout_geometry",
                rule="block_outside_canvas",
                severity="fail",
                detail=f"block #{idx} placement extends outside canvas: {block.get('placement')}",
                page_no=page_no,
                auto_fixable=True,
            ))
        bullets = (block or {}).get("bullets") or []
        if bullets and rect.h + 1e-6 < CARD_MIN_HEIGHT_IN:
            out.append(lint_common.LintResult(
                category="layout_geometry",
                rule="card_min_height",
                severity="warn",
                detail=(
                    f"block #{idx} carries {len(bullets)} bullets but height {rect.h:.2f}\""
                    f" < min {CARD_MIN_HEIGHT_IN}\""
                ),
                page_no=page_no,
                auto_fixable=False,
            ))
    return out


def _check_font_sizes(slide: dict, page_no: int | None, font_min: float, font_max: float) -> list:
    out = []
    blocks = (slide.get("visible_content") or {}).get("blocks") or []
    for idx, block in enumerate(blocks):
        size = (block or {}).get("font_size")
        if isinstance(size, (int, float)):
            if size < font_min - 1e-6 or size > font_max + 1e-6:
                out.append(lint_common.LintResult(
                    category="layout_geometry",
                    rule="font_size_out_of_range",
                    severity="fail",
                    detail=f"block #{idx} font_size={size} outside [{font_min}, {font_max}]",
                    page_no=page_no,
                    auto_fixable=True,
                ))
    return out


def lint_geometry(
    slide_specs: dict,
    *,
    master_style: dict | None = None,
) -> list:
    out: list = []
    font_min, font_max = _resolve_font_bounds(master_style)
    for slide in slide_specs.get("slides", []):
        page_no = slide.get("page_no")
        out.extend(_check_regions(slide, page_no))
        out.extend(_check_element_placements(slide, page_no))
        out.extend(_check_font_sizes(slide, page_no, font_min, font_max))
    return out


def _read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Geometry lint over slide_specs.")
    parser.add_argument("--slide-specs", required=True, type=Path)
    parser.add_argument("--master-style", type=Path)
    args = parser.parse_args(argv)
    results = lint_geometry(
        _read(args.slide_specs),
        master_style=_read(args.master_style) if args.master_style else None,
    )
    fails = [r for r in results if r.severity == "fail"]
    print(json.dumps({
        "results": [r.to_result_dict() for r in results],
        "summary": {"fail": len(fails), "warn": sum(r.severity == "warn" for r in results)},
    }, ensure_ascii=False, indent=2))
    return 0 if not fails else 2


if __name__ == "__main__":
    sys.exit(main())
