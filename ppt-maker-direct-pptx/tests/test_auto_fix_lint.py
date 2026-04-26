"""Cover auto-fix runner: known fixers, fixes_applied recording, page state reset."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

SKILL_ROOT = Path(__file__).resolve().parent.parent
SCRIPT_PATH = SKILL_ROOT / "scripts" / "auto_fix_lint.py"


def _load_module():
    name = "auto_fix_lint"
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


fixer = _load_module()


def _slide(page_no: int = 1, **extra) -> dict:
    base = {
        "page_no": page_no,
        "title": "demo",
        "visible_content": {"title": "demo", "blocks": [], "image_placeholders": [], "image_assets": []},
        "image_placeholders": [],
        "image_assets": [],
        "layout_regions": {
            "title": {"x": 0.5, "y": 0.4, "w": 12.333, "h": 1.0},
            "content": {"x": 0.5, "y": 1.6, "w": 12.333, "h": 5.4},
            "images": {},
            "mode": "auto",
        },
        "template_variant": {},
        "script_path": f"slides/slide-0{page_no}.js",
    }
    base.update(extra)
    return base


def _report(*results: dict) -> dict:
    return {
        "ts": "2026-04-26T10:00:00Z",
        "gate": "gate_7",
        "results": list(results),
    }


def test_clamps_region_outside_canvas():
    specs = {"slides": [_slide()]}
    specs["slides"][0]["layout_regions"]["content"] = {"x": 0.5, "y": 1.6, "w": 99.0, "h": 5.4}
    report = _report({
        "page_no": 1,
        "category": "layout_geometry",
        "rule": "region_outside_canvas",
        "severity": "fail",
        "auto_fixable": True,
    })
    new_report, new_specs, affected = fixer.auto_fix(report=report, slide_specs=specs)
    assert affected == [1]
    assert new_specs["slides"][0]["layout_regions"]["content"]["w"] <= 13.334
    assert len(new_report["fixes_applied"]) == 1


def test_shifts_overlapping_regions():
    specs = {"slides": [_slide()]}
    specs["slides"][0]["layout_regions"]["title"] = {"x": 0.5, "y": 0.4, "w": 12, "h": 2.0}
    specs["slides"][0]["layout_regions"]["content"] = {"x": 0.5, "y": 1.6, "w": 12, "h": 5.4}
    report = _report({
        "page_no": 1,
        "category": "layout_geometry",
        "rule": "regions_overlap",
        "severity": "fail",
        "auto_fixable": True,
    })
    _new_report, new_specs, affected = fixer.auto_fix(report=report, slide_specs=specs)
    assert affected == [1]
    new_content = new_specs["slides"][0]["layout_regions"]["content"]
    new_title = new_specs["slides"][0]["layout_regions"]["title"]
    assert new_content["y"] >= new_title["y"] + new_title["h"]


def test_clamps_block_outside_canvas():
    specs = {"slides": [_slide()]}
    specs["slides"][0]["visible_content"]["blocks"] = [
        {"placement": {"x": 0, "y": 0, "w": 99, "h": 5}}
    ]
    report = _report({
        "page_no": 1,
        "category": "layout_geometry",
        "rule": "block_outside_canvas",
        "severity": "fail",
        "detail": "block #0 placement extends outside canvas",
        "auto_fixable": True,
    })
    _new_report, new_specs, _ = fixer.auto_fix(report=report, slide_specs=specs)
    assert new_specs["slides"][0]["visible_content"]["blocks"][0]["placement"]["w"] <= 13.334


def test_clamps_font_size_into_range():
    specs = {"slides": [_slide()]}
    specs["slides"][0]["visible_content"]["blocks"] = [
        {"placement": {"x": 1, "y": 1, "w": 4, "h": 1.5}, "font_size": 200}
    ]
    report = _report({
        "page_no": 1,
        "category": "layout_geometry",
        "rule": "font_size_out_of_range",
        "severity": "fail",
        "detail": "block #0 font_size=200 outside [16, 44]",
        "auto_fixable": True,
    })
    _new_report, new_specs, _ = fixer.auto_fix(report=report, slide_specs=specs)
    assert new_specs["slides"][0]["visible_content"]["blocks"][0]["font_size"] == 44


def test_snaps_palette_compliance():
    specs = {"slides": [_slide()]}
    specs["slides"][0]["visible_content"]["blocks"] = [
        {"placement": {"x": 1, "y": 1, "w": 1, "h": 1}, "fill": "#FF0000"}
    ]
    master_style = {"color_strategy": {
        "primary_green": "#A8D86B",
        "secondary_teal": "#0F95B6",
        "background": "#FFFFFF",
    }}
    report = _report({
        "page_no": 1,
        "category": "style_consistency",
        "rule": "palette_compliance",
        "severity": "fail",
        "auto_fixable": True,
    })
    _new_report, new_specs, _ = fixer.auto_fix(report=report, slide_specs=specs, master_style=master_style)
    new_fill = new_specs["slides"][0]["visible_content"]["blocks"][0]["fill"]
    # #FF0000 has snapped onto one of the palette colors
    assert new_fill in {"#A8D86B", "#0F95B6", "#FFFFFF"}


def test_non_auto_fixable_skipped():
    specs = {"slides": [_slide()]}
    report = _report({
        "page_no": 1,
        "category": "schema",
        "rule": "outline.duplicate_page_no",
        "severity": "fail",
        "auto_fixable": False,
    })
    new_report, new_specs, affected = fixer.auto_fix(report=report, slide_specs=specs)
    assert affected == []
    assert "fixes_applied" not in new_report


def test_unknown_rule_skipped():
    specs = {"slides": [_slide()]}
    report = _report({
        "page_no": 1,
        "category": "layout_geometry",
        "rule": "unknown_rule_we_dont_handle",
        "severity": "fail",
        "auto_fixable": True,
    })
    new_report, _, affected = fixer.auto_fix(report=report, slide_specs=specs)
    assert affected == []
    assert "fixes_applied" not in new_report


def test_reset_pages_to_pending_review():
    prompts = {"slides": [
        {"page_no": 1, "intent_status": "needs_rework"},
        {"page_no": 2, "intent_status": "locked"},
    ]}
    mutated = fixer.reset_pages_to_pending_review(prompts, [1, 2])
    assert mutated == 2
    assert prompts["slides"][0]["intent_status"] == "pending_review"
    assert prompts["slides"][1]["intent_status"] == "pending_review"


def test_only_affected_pages_reset():
    prompts = {"slides": [
        {"page_no": 1, "intent_status": "locked"},
        {"page_no": 2, "intent_status": "locked"},
    ]}
    mutated = fixer.reset_pages_to_pending_review(prompts, [2])
    assert mutated == 1
    assert prompts["slides"][0]["intent_status"] == "locked"
    assert prompts["slides"][1]["intent_status"] == "pending_review"
