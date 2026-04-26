"""Render the pattern catalog preview for a given master_style.

Each pattern's wireframe_template (an SVG string with {slot} placeholders) is
filled with lorem-ipsum slot data and re-colored to reflect the active
master_style palette. The result is written to:

    artifacts/pattern_catalog/<style_hash>/<pattern_id>.svg

Plus a manifest.json indexing every produced file. The catalog is cached by
master_style content hash, so re-running with the same style is a no-op
unless --force is passed.

LibreOffice / Node-based PNG conversion is intentionally NOT performed in
this script — SVG is the lingua franca of the preview gates and works
without extra system dependencies. A future phase can layer PNG conversion
on top.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from importlib import util as _importlib_util
from pathlib import Path
from typing import Any

SKILL_ROOT = Path(__file__).resolve().parent.parent
PATTERNS_DIR = SKILL_ROOT / "assets" / "patterns"
DEFAULT_OUT_DIR = SKILL_ROOT / "artifacts" / "pattern_catalog"


def _load_pattern_registry():
    name = "pattern_registry"
    if name in sys.modules:
        return sys.modules[name]
    lib_path = SKILL_ROOT / "scripts" / "lib" / "pattern_registry.py"
    spec = _importlib_util.spec_from_file_location(name, lib_path)
    module = _importlib_util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


registry_mod = _load_pattern_registry()


# Mapping from the legacy huixin baseline hex codes that appear in shipped
# wireframe templates to semantic color_strategy keys. When a style's
# color_strategy has the corresponding key, we substitute the literal hex.
HUIXIN_COLOR_MAP = {
    "#A8D86B": ("primary_green", "primary", "primary_blue", "accent_green", "accent"),
    "#0F95B6": ("secondary_teal", "secondary", "accent_amber"),
    "#D9D9D9": ("neutral_gray", "neutral"),
    "#F5F7FA": ("section_background", "panel_background", "background"),
    "#FFFFFF": ("background",),
    "#1E1E1E": ("text_primary",),
    "#6B7280": ("text_secondary",),
    "#E5E7EB": ("divider", "neutral"),
}


def style_hash(master_style: dict) -> str:
    canonical = json.dumps(master_style, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:12]


def _resolve_color(master_style: dict, candidate_keys: tuple[str, ...]) -> str | None:
    color_strategy = master_style.get("color_strategy", {}) or {}
    for key in candidate_keys:
        value = color_strategy.get(key)
        if isinstance(value, str) and value.startswith("#"):
            return value
    return None


_HEX_RE = re.compile(r"#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})\b")


def _expand_hex(value: str) -> str:
    """Expand a #abc shorthand to #aabbcc; pass through 6-digit unchanged."""

    if len(value) == 4:  # '#abc'
        return "#" + "".join(ch * 2 for ch in value[1:])
    return value


def apply_style_to_svg(svg: str, master_style: dict) -> str:
    """Substitute the hardcoded huixin baseline colors in an SVG with the
    matching color_strategy values from `master_style`. Handles both 3- and
    6-digit hex codes; the rewritten hexes are emitted in canonical 6-digit
    upper-case form for stable diffs.
    """

    def repl(match: re.Match) -> str:
        original = match.group(0)
        canonical = _expand_hex(original).upper()
        candidate_keys = HUIXIN_COLOR_MAP.get(canonical)
        if not candidate_keys:
            return original
        replacement = _resolve_color(master_style, candidate_keys)
        if not replacement:
            return original
        replacement_canonical = _expand_hex(replacement).upper()
        if replacement_canonical == canonical:
            return original
        return replacement_canonical

    return _HEX_RE.sub(repl, svg)


def _lorem_value_for_slot(slot) -> str:
    """Generate a placeholder value for a slot when no sample data is provided."""

    if slot.accepts_image:
        return "[image]"
    cap = slot.max_chars or 60
    base = slot.name.replace("_", " ").title()
    if cap <= len(base):
        return base[:cap]
    filler = " — " + ("Lorem ipsum dolor sit amet" if cap > 30 else "Lorem")
    return (base + filler)[:cap]


def _slot_values_for(pattern) -> dict[str, str]:
    return {slot.name: _lorem_value_for_slot(slot) for slot in pattern.slots}


def _truncate(value: str, limit: int) -> str:
    if len(value) <= limit:
        return value
    if limit <= 1:
        return value[:limit]
    return value[: limit - 1] + "…"


def fill_wireframe(pattern, slots: dict[str, str]) -> str:
    """Substitute {slot_name} placeholders in the wireframe_template."""

    out = pattern.wireframe_template
    for slot in pattern.slots:
        token = "{" + slot.name + "}"
        if token not in out:
            continue
        raw = slots.get(slot.name, "")
        if slot.max_chars is not None:
            raw = _truncate(str(raw), slot.max_chars)
        out = out.replace(token, str(raw))
    return out


def render_catalog(
    master_style: dict,
    *,
    patterns_dir: Path = PATTERNS_DIR,
    out_dir: Path = DEFAULT_OUT_DIR,
    force: bool = False,
) -> Path:
    registry = registry_mod.PatternRegistry(patterns_dir)
    digest = style_hash(master_style)
    target_dir = out_dir / digest
    if target_dir.exists() and not force:
        return target_dir

    target_dir.mkdir(parents=True, exist_ok=True)
    manifest: dict[str, Any] = {
        "style_hash": digest,
        "template_id": master_style.get("template_id"),
        "template_name": master_style.get("template_name"),
        "patterns": [],
    }
    for pattern_id in registry.list_ids():
        pattern = registry.get(pattern_id)
        slot_values = _slot_values_for(pattern)
        svg = fill_wireframe(pattern, slot_values)
        styled_svg = apply_style_to_svg(svg, master_style)
        out_file = target_dir / f"{pattern_id}.svg"
        out_file.write_text(styled_svg, encoding="utf-8")
        manifest["patterns"].append({
            "pattern_id": pattern_id,
            "svg_path": out_file.name,
        })
    (target_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return target_dir


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Render the pattern catalog for a master_style.")
    parser.add_argument("--master-style", type=Path, required=True, help="Path to master_style.json")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--patterns-dir", type=Path, default=PATTERNS_DIR)
    parser.add_argument("--force", action="store_true", help="Re-render even when cached")
    args = parser.parse_args(argv)

    master_style = json.loads(args.master_style.read_text(encoding="utf-8"))
    target = render_catalog(
        master_style,
        patterns_dir=args.patterns_dir,
        out_dir=args.out,
        force=args.force,
    )
    print(f"catalog ready at {target}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
