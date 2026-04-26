"""Cover schema lint: validation failures, duplicates, pattern_id check, page_count match."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

SKILL_ROOT = Path(__file__).resolve().parent.parent
SCRIPT_PATH = SKILL_ROOT / "scripts" / "lint_schema.py"


def _load_module():
    name = "lint_schema"
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


lint_schema = _load_module()


def _outline(n: int = 2) -> dict:
    return {
        "storyline": "demo",
        "slides": [{"page_no": i, "title": f"page {i}"} for i in range(1, n + 1)],
    }


def _slide_prompts() -> dict:
    return {
        "slides": [
            {
                "page_no": 1,
                "title": "封面",
                "page_goal": "set the scene",
                "layout_type": "cover",
                "key_blocks": [],
                "compiled_prompt": "draw cover",
            }
        ],
        "quality_checklist": {},
    }


def _slide_specs() -> dict:
    return {
        "slides": [{
            "page_no": 1,
            "title": "封面",
            "visible_content": {"title": "封面", "blocks": [], "image_placeholders": [], "image_assets": []},
            "image_placeholders": [{"prompt": "img"}],
            "image_assets": [],
            "layout_regions": {"content": {}, "images": {}, "mode": "auto"},
            "template_variant": {},
            "script_path": "slides/slide-01.js",
        }]
    }


def test_clean_artifacts_pass():
    results = lint_schema.lint_artifacts(
        outline=_outline(2),
        slide_prompts=_slide_prompts(),
        slide_specs=_slide_specs(),
    )
    assert all(r.severity != "fail" for r in results)


def test_outline_invalid_field_flagged():
    bad = _outline(1)
    bad["slides"][0].pop("title")
    results = lint_schema.lint_artifacts(outline=bad)
    fails = [r for r in results if r.severity == "fail"]
    assert any("title" in r.detail or "title" in r.rule for r in fails)


def test_outline_duplicate_page_no_flagged():
    bad = _outline(1)
    bad["slides"].append({"page_no": 1, "title": "dup"})
    results = lint_schema.lint_artifacts(outline=bad)
    rules = [r.rule for r in results]
    assert "outline.duplicate_page_no" in rules


def test_outline_page_count_mismatch_flagged():
    results = lint_schema.lint_artifacts(outline=_outline(2), expected_page_count=5)
    rules = [r.rule for r in results]
    assert "outline.page_count_mismatch" in rules


def test_slide_prompts_unknown_pattern_id_flagged():
    bad = _slide_prompts()
    bad["slides"][0]["pattern_id"] = "made_up_pattern"
    bad["slides"][0]["layout_mode"] = "pattern"
    results = lint_schema.lint_artifacts(slide_prompts=bad)
    rules = [r.rule for r in results]
    assert "slide_prompts.unknown_pattern_id" in rules


def test_slide_prompts_known_pattern_id_passes():
    bad = _slide_prompts()
    bad["slides"][0]["pattern_id"] = "kpi_strip"
    bad["slides"][0]["layout_mode"] = "pattern"
    results = lint_schema.lint_artifacts(slide_prompts=bad)
    assert not any(r.rule == "slide_prompts.unknown_pattern_id" for r in results)


def test_slide_specs_invalid_image_status_flagged():
    bad = _slide_specs()
    bad["slides"][0]["image_placeholders"][0]["status"] = "in_progress"
    results = lint_schema.lint_artifacts(slide_specs=bad)
    rules = [r.rule for r in results]
    # Either the schema validator or the explicit check catches it; both are fail-class.
    assert any("image" in r.rule.lower() or "status" in r.detail.lower() for r in results if r.severity == "fail")


def test_results_attribute_to_page_no_when_possible():
    bad = _outline(1)
    bad["slides"][0].pop("title")
    bad["slides"][0]["page_no"] = 7
    results = lint_schema.lint_artifacts(outline=bad)
    fails = [r for r in results if r.severity == "fail"]
    # At least one fail must carry page_no=7
    assert any(r.page_no == 7 for r in fails)
