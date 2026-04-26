"""Cover catalog rendering: caching, color substitution, slot truncation, manifest."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

SKILL_ROOT = Path(__file__).resolve().parent.parent
SCRIPT_PATH = SKILL_ROOT / "scripts" / "render_pattern_catalog.py"


def _load_module():
    name = "render_pattern_catalog"
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


catalog = _load_module()


def _huixin_brief() -> dict:
    return json.loads(
        (SKILL_ROOT / "assets" / "huixin_master_style_brief.json").read_text(encoding="utf-8")
    )


def _dark_brief() -> dict:
    return json.loads(
        (SKILL_ROOT / "assets" / "dark_english_business_master_style_brief.json").read_text(encoding="utf-8")
    )


def test_style_hash_is_stable_for_same_input():
    style = _huixin_brief()
    assert catalog.style_hash(style) == catalog.style_hash(style)


def test_style_hash_differs_for_different_styles():
    a = _huixin_brief()
    b = _dark_brief()
    assert catalog.style_hash(a) != catalog.style_hash(b)


def test_render_catalog_creates_one_svg_per_pattern(tmp_path):
    out_dir = tmp_path / "catalog"
    style = _huixin_brief()
    target = catalog.render_catalog(style, out_dir=out_dir)
    svg_files = sorted(p.name for p in target.glob("*.svg"))
    assert len(svg_files) == 12
    assert "manifest.json" in [p.name for p in target.iterdir()]


def test_catalog_manifest_lists_all_patterns(tmp_path):
    style = _huixin_brief()
    target = catalog.render_catalog(style, out_dir=tmp_path / "catalog")
    manifest = json.loads((target / "manifest.json").read_text(encoding="utf-8"))
    pattern_ids = {p["pattern_id"] for p in manifest["patterns"]}
    assert len(pattern_ids) == 12
    assert manifest["template_id"] == "huixin"


def test_catalog_caches_by_style_hash(tmp_path):
    style = _huixin_brief()
    target = catalog.render_catalog(style, out_dir=tmp_path / "catalog")
    one_svg = target / "cover.svg"
    original_text = one_svg.read_text(encoding="utf-8")
    # Manually edit the cached SVG, then re-render without --force; expect no overwrite.
    one_svg.write_text("MUTATED", encoding="utf-8")
    catalog.render_catalog(style, out_dir=tmp_path / "catalog")
    assert one_svg.read_text(encoding="utf-8") == "MUTATED"
    # With --force, the cache is regenerated.
    catalog.render_catalog(style, out_dir=tmp_path / "catalog", force=True)
    assert one_svg.read_text(encoding="utf-8") == original_text


def test_apply_style_substitutes_huixin_baseline_colors():
    style = {
        "color_strategy": {
            "primary_green": "#7C4DFF",
            "secondary_teal": "#00E5FF",
            "background": "#0F0F1F",
        }
    }
    svg = "<rect fill='#A8D86B'/><line stroke='#0F95B6'/><rect fill='#FFFFFF'/>"
    out = catalog.apply_style_to_svg(svg, style)
    assert "#7C4DFF" in out
    assert "#00E5FF" in out
    assert "#0F0F1F" in out
    assert "#A8D86B" not in out
    assert "#0F95B6" not in out


def test_apply_style_leaves_unchanged_when_color_strategy_missing():
    svg = "<rect fill='#A8D86B'/>"
    out = catalog.apply_style_to_svg(svg, {})
    assert out == svg


def test_fill_wireframe_truncates_to_max_chars(tmp_path):
    registry = catalog.registry_mod.PatternRegistry(SKILL_ROOT / "assets" / "patterns")
    pattern = registry.get("kpi_strip")
    long_value = "x" * 200  # max_chars on labels is 24
    slots = {slot.name: long_value for slot in pattern.slots}
    out = catalog.fill_wireframe(pattern, slots)
    # Truncated values should not contain 200 x's contiguously
    assert "x" * 200 not in out
    # And every {slot} placeholder should be substituted
    for slot in pattern.slots:
        assert "{" + slot.name + "}" not in out


def test_render_catalog_uses_styled_colors_in_dark_style(tmp_path):
    style = _dark_brief()
    target = catalog.render_catalog(style, out_dir=tmp_path / "catalog")
    svg_upper = (target / "kpi_strip.svg").read_text(encoding="utf-8").upper()
    # Dark style background is "#0B1020" — confirm it appears.
    assert "#0B1020" in svg_upper
    # Dark style primary blue should replace at least the huixin primary_green hex.
    assert "#38BDF8" in svg_upper
    # And the original baseline white is no longer present.
    assert "#FFFFFF" not in svg_upper
    assert "#FFF'" not in svg_upper.replace("'", "'")  # no shorthand white either
