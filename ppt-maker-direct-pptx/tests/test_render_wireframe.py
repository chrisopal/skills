"""Cover per-page wireframe rendering: substitution, truncation, warnings."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

SKILL_ROOT = Path(__file__).resolve().parent.parent
SCRIPT_PATH = SKILL_ROOT / "scripts" / "render_wireframe.py"


def _load_module():
    name = "render_wireframe"
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


wireframe = _load_module()


def _intent_kpi() -> dict:
    return {
        "page_no": 4,
        "pattern_id": "kpi_strip",
        "slots": {
            "kpi_1_value": "+38%",
            "kpi_1_label": "效率提升",
            "kpi_2_value": "12k",
            "kpi_2_label": "MAU",
        },
    }


def test_renders_filled_svg_with_real_text():
    result = wireframe.render_wireframe(_intent_kpi())
    assert "<svg" in result.svg
    assert "+38%" in result.svg
    assert "效率提升" in result.svg
    assert "{kpi_1_value}" not in result.svg


def test_truncates_oversize_slot_with_ellipsis():
    intent = _intent_kpi()
    intent["slots"]["kpi_1_label"] = "x" * 100  # max_chars=24
    result = wireframe.render_wireframe(intent)
    assert "…" in result.svg
    # Truncated value, not the original 100 chars
    assert "x" * 100 not in result.svg
    truncation_warnings = [w for w in result.warnings if w.rule == "max_chars"]
    assert len(truncation_warnings) == 1
    assert truncation_warnings[0].slot == "kpi_1_label"


def test_missing_required_slot_emits_warning():
    intent = _intent_kpi()
    intent["slots"].pop("kpi_2_label")
    result = wireframe.render_wireframe(intent)
    rules = {(w.slot, w.rule) for w in result.warnings}
    assert ("kpi_2_label", "missing_required") in rules


def test_unknown_slot_emits_warning():
    intent = _intent_kpi()
    intent["slots"]["bogus_slot"] = "x"
    result = wireframe.render_wireframe(intent)
    rules = {(w.slot, w.rule) for w in result.warnings}
    assert ("bogus_slot", "unknown_slot") in rules


def test_unknown_pattern_returns_warning_no_svg():
    result = wireframe.render_wireframe({"page_no": 5, "pattern_id": "made_up"})
    assert result.svg == ""
    assert result.warnings[0].rule == "unknown_pattern"


def test_no_pattern_id_returns_warning():
    result = wireframe.render_wireframe({"page_no": 6})
    assert result.svg == ""
    assert result.warnings[0].rule == "unknown_pattern"


def test_master_style_applies_color_swap():
    style = {
        "color_strategy": {
            "primary_green": "#7C4DFF",
            "secondary_teal": "#00E5FF",
            "background": "#0F0F1F",
        }
    }
    result = wireframe.render_wireframe(_intent_kpi(), master_style=style)
    assert "#7C4DFF" in result.svg.upper()
    assert "#0F0F1F" in result.svg.upper()


def test_nested_slot_dict_is_flattened():
    intent = {
        "page_no": 7,
        "pattern_id": "four_card_matrix",
        "slots": {
            "cell_1": {"label": "ROI", "value": "+38%", "desc": "demo"},
            "cell_2": {"label": "MAU", "value": "12k", "desc": "demo"},
            "cell_3": {"label": "NPS", "value": "62", "desc": "demo"},
            "cell_4": {"label": "GMV", "value": "100M", "desc": "demo"},
        },
    }
    result = wireframe.render_wireframe(intent)
    assert "ROI" in result.svg
    assert "+38%" in result.svg
    # No missing-required warnings if flattening works
    missing = [w for w in result.warnings if w.rule == "missing_required"]
    assert missing == [], f"unexpected missing warnings: {missing}"
