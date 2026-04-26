"""Cover style consistency lint: palette compliance, title font uniformity, forbidden words."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

SKILL_ROOT = Path(__file__).resolve().parent.parent
SCRIPT_PATH = SKILL_ROOT / "scripts" / "lint_style.py"


def _load_module():
    name = "lint_style"
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


lint_style = _load_module()


def _slide(page_no: int = 1, **extra) -> dict:
    base = {
        "page_no": page_no,
        "title": "demo",
        "visible_content": {
            "title": "demo",
            "blocks": [],
            "image_placeholders": [],
            "image_assets": [],
        },
        "image_placeholders": [],
        "image_assets": [],
        "layout_regions": {"content": {}, "images": {}, "mode": "auto"},
        "template_variant": {},
        "script_path": f"slides/slide-0{page_no}.js",
    }
    base.update(extra)
    return base


def _huixin_master_style() -> dict:
    return {
        "color_strategy": {
            "primary_green": "#A8D86B",
            "secondary_teal": "#0F95B6",
            "neutral_gray": "#D9D9D9",
            "background": "#FFFFFF",
            "text_primary": "#1E1E1E",
        },
        "forbidden_elements": ["3D 拟物图标", "厚重投影"],
    }


def test_palette_compliance_passes_when_only_palette_colors_used():
    specs = {"slides": [
        _slide(visible_content={
            "title": "demo",
            "blocks": [
                {"placement": {"x": 1, "y": 1, "w": 1, "h": 1}, "fill": "#A8D86B"},
                {"placement": {"x": 1, "y": 1, "w": 1, "h": 1}, "fill": "#FFFFFF"},
            ],
            "image_placeholders": [],
            "image_assets": [],
        })
    ]}
    results = lint_style.lint_style(specs, master_style=_huixin_master_style())
    assert not any(r.rule == "palette_compliance" for r in results)


def test_palette_compliance_fails_for_off_palette_color():
    specs = {"slides": [
        _slide(visible_content={
            "title": "demo",
            "blocks": [
                {"placement": {"x": 1, "y": 1, "w": 1, "h": 1}, "fill": "#FF0000"},
            ],
            "image_placeholders": [],
            "image_assets": [],
        })
    ]}
    results = lint_style.lint_style(specs, master_style=_huixin_master_style())
    fails = [r for r in results if r.rule == "palette_compliance"]
    assert len(fails) == 1
    assert fails[0].page_no == 1
    assert "#FF0000" in fails[0].detail


def test_palette_compliance_canonicalizes_3_digit_hex():
    specs = {"slides": [
        _slide(visible_content={
            "title": "demo",
            "blocks": [{"placement": {"x": 1, "y": 1, "w": 1, "h": 1}, "fill": "#fff"}],
            "image_placeholders": [],
            "image_assets": [],
        })
    ]}
    results = lint_style.lint_style(specs, master_style=_huixin_master_style())
    assert not any(r.rule == "palette_compliance" for r in results)


def test_title_font_disagreement_warns():
    specs = {"slides": [
        _slide(page_no=1, intent_status="locked", visible_content={
            "title": {"font_size": 36}, "blocks": [], "image_placeholders": [], "image_assets": [],
        }),
        _slide(page_no=2, intent_status="locked", visible_content={
            "title": {"font_size": 30}, "blocks": [], "image_placeholders": [], "image_assets": [],
        }),
    ]}
    results = lint_style.lint_style(specs, master_style=_huixin_master_style())
    warns = [r for r in results if r.rule == "title_font_scale_unified"]
    assert len(warns) == 1


def test_title_font_uniform_passes():
    specs = {"slides": [
        _slide(page_no=1, intent_status="locked", visible_content={
            "title": {"font_size": 36}, "blocks": [], "image_placeholders": [], "image_assets": [],
        }),
        _slide(page_no=2, intent_status="locked", visible_content={
            "title": {"font_size": 36}, "blocks": [], "image_placeholders": [], "image_assets": [],
        }),
    ]}
    results = lint_style.lint_style(specs, master_style=_huixin_master_style())
    assert not any(r.rule == "title_font_scale_unified" for r in results)


def test_forbidden_element_match_fails():
    specs = {"slides": [
        _slide(visible_content={
            "title": "demo",
            "blocks": [{"placement": {"x": 1, "y": 1, "w": 1, "h": 1}, "note": "采用 3D 拟物图标"}],
            "image_placeholders": [],
            "image_assets": [],
        })
    ]}
    results = lint_style.lint_style(specs, master_style=_huixin_master_style())
    fails = [r for r in results if r.rule == "forbidden_element_present"]
    assert len(fails) == 1
    assert fails[0].page_no == 1


def test_no_master_style_disables_palette_and_forbidden_checks():
    specs = {"slides": [_slide()]}
    results = lint_style.lint_style(specs)
    assert not any(r.rule in ("palette_compliance", "forbidden_element_present") for r in results)
