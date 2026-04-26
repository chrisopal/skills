"""Cover geometry lint: region overlap, canvas bounds, card height, font ranges."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

SKILL_ROOT = Path(__file__).resolve().parent.parent
SCRIPT_PATH = SKILL_ROOT / "scripts" / "lint_geometry.py"


def _load_module():
    name = "lint_geometry"
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


lint_geo = _load_module()


def _slide(page_no: int = 1, **regions) -> dict:
    base_regions = {
        "title": {"x": 0.5, "y": 0.4, "w": 12.333, "h": 1.0},
        "content": {"x": 0.5, "y": 1.6, "w": 12.333, "h": 5.4},
    }
    base_regions.update(regions)
    return {
        "page_no": page_no,
        "title": "demo",
        "visible_content": {"title": "demo", "blocks": [], "image_placeholders": [], "image_assets": []},
        "image_placeholders": [],
        "image_assets": [],
        "layout_regions": base_regions,
        "template_variant": {},
        "script_path": f"slides/slide-0{page_no}.js",
    }


def test_clean_specs_pass():
    specs = {"slides": [_slide()]}
    results = lint_geo.lint_geometry(specs)
    assert all(r.severity == "pass" for r in results) or results == []


def test_overlapping_regions_fail():
    specs = {"slides": [_slide(
        title={"x": 0.5, "y": 0.4, "w": 12.333, "h": 2.0},  # extends to y=2.4
        content={"x": 0.5, "y": 1.6, "w": 12.333, "h": 5.4},  # starts at 1.6
    )]}
    results = lint_geo.lint_geometry(specs)
    rules = [r.rule for r in results]
    assert "regions_overlap" in rules


def test_region_outside_canvas_fails():
    specs = {"slides": [_slide(
        content={"x": 0.5, "y": 1.6, "w": 99.0, "h": 5.4},
    )]}
    results = lint_geo.lint_geometry(specs)
    assert any(r.rule == "region_outside_canvas" for r in results)


def test_block_outside_canvas_fails():
    specs = {"slides": [_slide()]}
    specs["slides"][0]["visible_content"]["blocks"] = [
        {"placement": {"x": 0.0, "y": 0.0, "w": 99.0, "h": 5.0}}
    ]
    results = lint_geo.lint_geometry(specs)
    assert any(r.rule == "block_outside_canvas" for r in results)


def test_card_min_height_warn():
    specs = {"slides": [_slide()]}
    specs["slides"][0]["visible_content"]["blocks"] = [{
        "placement": {"x": 0.5, "y": 1.6, "w": 4.0, "h": 0.6},  # < 1.0 inch
        "bullets": ["a", "b", "c"],
    }]
    results = lint_geo.lint_geometry(specs)
    warns = [r for r in results if r.rule == "card_min_height"]
    assert len(warns) == 1
    assert warns[0].severity == "warn"


def test_font_size_out_of_range_fails():
    specs = {"slides": [_slide()]}
    specs["slides"][0]["visible_content"]["blocks"] = [
        {"placement": {"x": 0.5, "y": 1.6, "w": 4.0, "h": 1.5}, "font_size": 200}
    ]
    master_style = {"typography": {"page_title": "36-44px, bold", "body_text": "16-18px"}}
    results = lint_geo.lint_geometry(specs, master_style=master_style)
    assert any(r.rule == "font_size_out_of_range" for r in results)


def test_font_size_within_range_passes():
    specs = {"slides": [_slide()]}
    specs["slides"][0]["visible_content"]["blocks"] = [
        {"placement": {"x": 0.5, "y": 1.6, "w": 4.0, "h": 1.5}, "font_size": 18}
    ]
    master_style = {"typography": {"page_title": "36-44px, bold", "body_text": "16-18px"}}
    results = lint_geo.lint_geometry(specs, master_style=master_style)
    assert not any(r.rule == "font_size_out_of_range" for r in results)


def test_results_attribute_to_page_no():
    specs = {"slides": [
        _slide(page_no=4, content={"x": 0.5, "y": 1.6, "w": 99.0, "h": 5.4}),
    ]}
    results = lint_geo.lint_geometry(specs)
    assert all(r.page_no == 4 for r in results if r.severity in ("fail", "warn"))


def test_image_region_overlap_with_content_fails():
    specs = {"slides": [_slide(
        content={"x": 0.5, "y": 1.6, "w": 8.0, "h": 5.4},
        images={"x": 5.0, "y": 1.6, "w": 8.0, "h": 5.4},  # overlaps content
    )]}
    results = lint_geo.lint_geometry(specs)
    rules = {r.rule for r in results}
    assert "regions_overlap" in rules
