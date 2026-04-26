"""Apply known auto-fixers to fail-class lint results.

Reads a lint_report.json, walks every result with `severity=fail` and
`auto_fixable=true`, dispatches to a fixer for the rule, mutates the
relevant artifact, records `fixes_applied[]` on the report, and resets
affected pages' intent_status to `pending_review` so the user re-confirms
the patched layout before locking.

Supported rules (matches lint_geometry.py / lint_style.py):

  layout_geometry / region_outside_canvas      -> clamp region into canvas
  layout_geometry / regions_overlap            -> shift content/images below title
  layout_geometry / block_outside_canvas       -> clamp block placement
  layout_geometry / font_size_out_of_range     -> clamp into master_style range
  style_consistency / palette_compliance       -> snap off-palette hex to nearest palette color

Other rules (schema, content quality) are surfaced but not auto-fixed.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

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


geom = _load_local("geometry", "scripts/lib/geometry.py")
lint_geo = _load_local("lint_geometry", "scripts/lint_geometry.py")


CANVAS_W = geom.CANVAS_WIDTH
CANVAS_H = geom.CANVAS_HEIGHT


# ---------------------------------------------------------------------------
# Fixers
# ---------------------------------------------------------------------------


def _slide_for_page(slide_specs: dict, page_no: int) -> dict | None:
    for s in slide_specs.get("slides", []):
        if s.get("page_no") == page_no:
            return s
    return None


def _clamp_rect(rect: dict) -> bool:
    """Clamp x/y/w/h into the canvas; return True if anything changed."""

    changed = False
    if not rect:
        return False
    if rect.get("x", 0) < 0:
        rect["x"] = 0
        changed = True
    if rect.get("y", 0) < 0:
        rect["y"] = 0
        changed = True
    width_avail = CANVAS_W - rect.get("x", 0)
    if rect.get("w", 0) > width_avail:
        rect["w"] = round(width_avail, 3)
        changed = True
    height_avail = CANVAS_H - rect.get("y", 0)
    if rect.get("h", 0) > height_avail:
        rect["h"] = round(height_avail, 3)
        changed = True
    return changed


def fix_region_outside_canvas(slide: dict, _detail: str) -> str | None:
    layout_regions = slide.get("layout_regions", {})
    diffs: list[str] = []
    for name in ("title", "content", "images"):
        rect = layout_regions.get(name)
        if isinstance(rect, dict) and _clamp_rect(rect):
            diffs.append(f"clamped {name} to canvas")
    return "; ".join(diffs) or None


def fix_regions_overlap(slide: dict, _detail: str) -> str | None:
    layout_regions = slide.get("layout_regions", {})
    title = layout_regions.get("title")
    content = layout_regions.get("content")
    if not isinstance(title, dict) or not isinstance(content, dict):
        return None
    title_rect = geom.rect_from(title)
    content_rect = geom.rect_from(content)
    if not title_rect or not content_rect:
        return None
    if not title_rect.overlaps(content_rect):
        return None
    new_y = round(title_rect.bottom + 0.2, 3)
    if new_y >= CANVAS_H:
        return None
    delta = new_y - content_rect.y
    content["y"] = new_y
    new_h = round(min(content["h"], CANVAS_H - new_y), 3)
    content["h"] = new_h
    return f"shifted content.y by +{delta:.2f}\" and clamped h to {new_h}\""


def fix_block_outside_canvas(slide: dict, detail: str) -> str | None:
    """Detail string carries the block index; e.g. 'block #2 placement extends...'."""

    match = re.search(r"block #(\d+)", detail or "")
    if not match:
        return None
    idx = int(match.group(1))
    blocks = (slide.get("visible_content") or {}).get("blocks") or []
    if idx >= len(blocks):
        return None
    placement = blocks[idx].get("placement")
    if not _clamp_rect(placement):
        return None
    return f"clamped block #{idx} into canvas"


def fix_font_size_out_of_range(slide: dict, detail: str) -> str | None:
    """Detail: 'block #3 font_size=200 outside [16, 44]'"""

    match = re.search(r"block #(\d+) font_size=([0-9.]+) outside \[([0-9.]+), ([0-9.]+)\]", detail or "")
    if not match:
        return None
    idx = int(match.group(1))
    lo = float(match.group(3))
    hi = float(match.group(4))
    blocks = (slide.get("visible_content") or {}).get("blocks") or []
    if idx >= len(blocks):
        return None
    cur = blocks[idx].get("font_size")
    if not isinstance(cur, (int, float)):
        return None
    new = max(lo, min(hi, cur))
    blocks[idx]["font_size"] = new
    return f"clamped block #{idx} font_size {cur} -> {new}"


def _palette_set(master_style: dict | None) -> set[str]:
    if not master_style:
        return set()
    out = set()
    for value in (master_style.get("color_strategy") or {}).values():
        if isinstance(value, str) and value.startswith("#"):
            out.add(_expand_hex(value).upper())
    return out


def _expand_hex(value: str) -> str:
    if len(value) == 4:
        return "#" + "".join(ch * 2 for ch in value[1:])
    return value


def _hex_to_rgb(value: str) -> tuple[int, int, int]:
    v = _expand_hex(value).lstrip("#")
    return (int(v[0:2], 16), int(v[2:4], 16), int(v[4:6], 16))


def _color_distance(a: str, b: str) -> int:
    ar, ag, ab = _hex_to_rgb(a)
    br, bg, bb = _hex_to_rgb(b)
    return (ar - br) ** 2 + (ag - bg) ** 2 + (ab - bb) ** 2


def _snap_to_palette(value: str, palette: set[str]) -> str:
    if not palette:
        return value
    return min(palette, key=lambda c: _color_distance(value, c))


def fix_palette_compliance(slide: dict, _detail: str, *, palette: set[str]) -> str | None:
    if not palette:
        return None
    snaps: list[tuple[str, str]] = []

    def replace_in(node):
        if isinstance(node, dict):
            for key, value in list(node.items()):
                if isinstance(value, str):
                    new_value = value
                    for match in list(_HEX_RE.finditer(value)):
                        original = match.group(0)
                        canonical = _expand_hex(original).upper()
                        if canonical in palette:
                            continue
                        snapped = _snap_to_palette(canonical, palette)
                        if snapped != canonical:
                            new_value = new_value.replace(original, snapped)
                            snaps.append((canonical, snapped))
                    if new_value != value:
                        node[key] = new_value
                else:
                    replace_in(value)
        elif isinstance(node, list):
            for item in node:
                replace_in(item)

    replace_in(slide)
    if not snaps:
        return None
    sample = ", ".join(f"{a}->{b}" for a, b in snaps[:3])
    if len(snaps) > 3:
        sample += f", ... ({len(snaps) - 3} more)"
    return f"snapped {len(snaps)} hex(es) to palette: {sample}"


def _now_iso() -> str:
    return datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def auto_fix(
    *,
    report: dict,
    slide_specs: dict,
    master_style: dict | None = None,
) -> tuple[dict, dict, list[int]]:
    """Apply auto-fixers and return (mutated_report, mutated_slide_specs, affected_page_nos)."""

    palette = _palette_set(master_style)
    affected: set[int] = set()
    fixes: list[dict] = []

    fixers: dict[str, Callable[[dict, str], str | None]] = {
        "region_outside_canvas": fix_region_outside_canvas,
        "regions_overlap": fix_regions_overlap,
        "block_outside_canvas": fix_block_outside_canvas,
        "font_size_out_of_range": fix_font_size_out_of_range,
        "palette_compliance": lambda slide, detail: fix_palette_compliance(slide, detail, palette=palette),
    }

    for entry in report.get("results", []):
        if entry.get("severity") != "fail":
            continue
        if not entry.get("auto_fixable"):
            continue
        page_no = entry.get("page_no")
        rule = entry.get("rule", "")
        if not isinstance(page_no, int):
            continue
        slide = _slide_for_page(slide_specs, page_no)
        if slide is None:
            continue
        fixer = fixers.get(rule)
        if fixer is None:
            continue
        diff_summary = fixer(slide, entry.get("detail", ""))
        if diff_summary:
            fixes.append({
                "page_no": page_no,
                "rule": rule,
                "ts": _now_iso(),
                "diff_summary": diff_summary,
            })
            affected.add(page_no)

    if fixes:
        report = dict(report)
        report["fixes_applied"] = report.get("fixes_applied", []) + fixes

    return report, slide_specs, sorted(affected)


def reset_pages_to_pending_review(slide_prompts: dict, page_nos: list[int]) -> int:
    if not page_nos:
        return 0
    targets = set(page_nos)
    mutated = 0
    for slide in slide_prompts.get("slides", []):
        if slide.get("page_no") in targets and slide.get("intent_status") != "pending_review":
            slide["intent_status"] = "pending_review"
            mutated += 1
    return mutated


def _read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Apply auto-fixers to a lint report.")
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument("--slide-specs", required=True, type=Path)
    parser.add_argument("--master-style", type=Path)
    parser.add_argument("--slide-prompts", type=Path,
                        help="If given, affected pages get intent_status reset to pending_review")
    args = parser.parse_args(argv)

    report = _read(args.report)
    slide_specs = _read(args.slide_specs)
    master_style = _read(args.master_style) if args.master_style else None

    new_report, new_specs, affected = auto_fix(
        report=report, slide_specs=slide_specs, master_style=master_style,
    )

    args.report.write_text(json.dumps(new_report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.slide_specs.write_text(json.dumps(new_specs, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    reset_count = 0
    if args.slide_prompts and affected:
        prompts = _read(args.slide_prompts)
        reset_count = reset_pages_to_pending_review(prompts, affected)
        args.slide_prompts.write_text(json.dumps(prompts, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(
        f"applied {len(new_report.get('fixes_applied', [])) - len(report.get('fixes_applied', []))} fix(es) "
        f"affecting pages {affected}; reset {reset_count} intent_status to pending_review"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
