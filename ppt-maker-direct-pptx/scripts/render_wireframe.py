"""Render a low-fidelity SVG wireframe for one page intent.

Used by the gate-5 (page intent confirmation) preview to show the user how
their real slot data will lay into the chosen pattern. Pure string templating
so each call is sub-millisecond and adds no system dependencies.

Usage:
    python scripts/render_wireframe.py --intents-file artifacts/slide_prompts.json
        --page-no 4 [--master-style artifacts/master_style.json]
        [--out artifacts/wireframes/page-04.svg]
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from importlib import util as _importlib_util
from pathlib import Path
from typing import Any

SKILL_ROOT = Path(__file__).resolve().parent.parent
PATTERNS_DIR = SKILL_ROOT / "assets" / "patterns"
DEFAULT_OUT_DIR = SKILL_ROOT / "artifacts" / "wireframes"


def _load_local(name: str, rel_path: str):
    if name in sys.modules:
        return sys.modules[name]
    path = SKILL_ROOT / rel_path
    spec = _importlib_util.spec_from_file_location(name, path)
    module = _importlib_util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


registry_mod = _load_local("pattern_registry", "scripts/lib/pattern_registry.py")
catalog_mod = _load_local("render_pattern_catalog", "scripts/render_pattern_catalog.py")


@dataclass
class WireframeWarning:
    page_no: int | None
    slot: str
    rule: str  # "max_chars" | "missing_required" | "unknown_pattern" | "unknown_slot"
    detail: str


@dataclass
class WireframeResult:
    svg: str
    warnings: list[WireframeWarning] = field(default_factory=list)


def _stringify(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (str, int, float)):
        return str(value)
    return json.dumps(value, ensure_ascii=False)


def _flatten_slots(slots: dict[str, Any]) -> dict[str, str]:
    """Page intents may store slots as nested dicts (cell_1: {label, value, desc}).
    The wireframe templates use flat names (cell_1_label). Flatten one level
    when nested dicts are present so authors can use either shape.
    """

    out: dict[str, str] = {}
    for key, value in (slots or {}).items():
        if isinstance(value, dict):
            for sub_key, sub_value in value.items():
                out[f"{key}_{sub_key}"] = _stringify(sub_value)
        else:
            out[key] = _stringify(value)
    return out


def render_wireframe(
    page_intent: dict,
    *,
    master_style: dict | None = None,
    patterns_dir: Path = PATTERNS_DIR,
) -> WireframeResult:
    pattern_id = page_intent.get("pattern_id")
    page_no = page_intent.get("page_no")
    if not pattern_id:
        return WireframeResult(
            svg="",
            warnings=[
                WireframeWarning(
                    page_no=page_no,
                    slot="",
                    rule="unknown_pattern",
                    detail="page intent has no pattern_id; freeform rendering not supported here",
                )
            ],
        )

    registry = registry_mod.PatternRegistry(patterns_dir)
    if pattern_id not in registry:
        return WireframeResult(
            svg="",
            warnings=[
                WireframeWarning(
                    page_no=page_no,
                    slot="",
                    rule="unknown_pattern",
                    detail=f"pattern '{pattern_id}' not in registry",
                )
            ],
        )

    pattern = registry.get(pattern_id)
    flat_slots = _flatten_slots(page_intent.get("slots", {}))

    warnings: list[WireframeWarning] = []
    truncated_slots: dict[str, str] = {}
    for slot in pattern.slots:
        raw = flat_slots.get(slot.name, "")
        if slot.required and not raw:
            warnings.append(
                WireframeWarning(
                    page_no=page_no,
                    slot=slot.name,
                    rule="missing_required",
                    detail=f"required slot '{slot.name}' missing or empty",
                )
            )
        if slot.max_chars is not None and len(raw) > slot.max_chars:
            warnings.append(
                WireframeWarning(
                    page_no=page_no,
                    slot=slot.name,
                    rule="max_chars",
                    detail=(
                        f"slot '{slot.name}' is {len(raw)} chars, "
                        f"exceeds max_chars={slot.max_chars}; truncating in wireframe"
                    ),
                )
            )
            raw = raw[: slot.max_chars - 1] + "…"
        truncated_slots[slot.name] = raw

    for unknown in set(flat_slots) - pattern.slot_names():
        warnings.append(
            WireframeWarning(
                page_no=page_no,
                slot=unknown,
                rule="unknown_slot",
                detail=f"slot '{unknown}' not declared by pattern '{pattern_id}'",
            )
        )

    svg = catalog_mod.fill_wireframe(pattern, truncated_slots)
    if master_style:
        svg = catalog_mod.apply_style_to_svg(svg, master_style)
    return WireframeResult(svg=svg, warnings=warnings)


def _read_intents(intents_path: Path) -> list[dict]:
    data = json.loads(intents_path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        return data
    return data.get("slides", [])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Render an SVG wireframe for a single page intent.")
    parser.add_argument("--intents-file", type=Path, required=True)
    parser.add_argument("--page-no", type=int, required=True)
    parser.add_argument("--master-style", type=Path, help="Optional master_style.json")
    parser.add_argument("--out", type=Path)
    args = parser.parse_args(argv)

    intents = _read_intents(args.intents_file)
    intent = next((i for i in intents if i.get("page_no") == args.page_no), None)
    if intent is None:
        print(f"page_no {args.page_no} not found in {args.intents_file}", file=sys.stderr)
        return 2

    master_style = None
    if args.master_style:
        master_style = json.loads(args.master_style.read_text(encoding="utf-8"))

    result = render_wireframe(intent, master_style=master_style)
    out_path = args.out or DEFAULT_OUT_DIR / f"page-{args.page_no:02d}.svg"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(result.svg, encoding="utf-8")

    for warning in result.warnings:
        print(
            f"[wireframe warn] page={warning.page_no} slot={warning.slot} "
            f"rule={warning.rule} {warning.detail}",
            file=sys.stderr,
        )
    print(f"wrote {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
