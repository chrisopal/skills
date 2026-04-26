"""Cover dashboard rendering: row layout, lint summary, deck summary, formats."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

SKILL_ROOT = Path(__file__).resolve().parent.parent
SCRIPT_PATH = SKILL_ROOT / "scripts" / "dashboard.py"


def _load_module():
    name = "dashboard"
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


dashboard = _load_module()


def _outline(*statuses) -> dict:
    return {
        "slides": [
            {"page_no": i + 1, "title": f"page {i+1}", "outline_status": s}
            for i, s in enumerate(statuses)
        ]
    }


def _slide_prompts(*statuses) -> dict:
    return {
        "slides": [
            {
                "page_no": i + 1,
                "title": f"page {i+1}",
                "page_goal": "demo",
                "layout_type": "cover",
                "key_blocks": [],
                "compiled_prompt": "draw",
                "intent_status": s,
            }
            for i, s in enumerate(statuses)
        ],
        "quality_checklist": {},
    }


def _specs(*image_status_lists) -> dict:
    slides = []
    for i, statuses in enumerate(image_status_lists):
        placeholders = [
            {"prompt": f"img {j}", "status": s} for j, s in enumerate(statuses)
        ]
        slides.append({
            "page_no": i + 1,
            "title": "demo",
            "visible_content": {"title": "demo", "blocks": [], "image_placeholders": [], "image_assets": []},
            "image_placeholders": placeholders,
            "image_assets": [],
            "layout_regions": {"content": {}, "images": {}, "mode": "auto"},
            "template_variant": {},
            "script_path": f"slides/slide-{i+1:02d}.js",
        })
    return {"slides": slides}


def test_dashboard_includes_row_per_page():
    db = dashboard.build_dashboard(
        outline=_outline("locked", "draft"),
        slide_prompts=_slide_prompts("locked", "draft"),
        slide_specs=_specs(["generated"], ["placeholder"]),
        lint_report=None,
    )
    rows = db["rows"]
    assert len(rows) == 2
    assert rows[0]["page_no"] == 1
    assert rows[0]["intent_status"] == "locked"
    assert rows[1]["intent_status"] == "draft"


def test_dashboard_image_status_aggregation():
    db = dashboard.build_dashboard(
        outline=None,
        slide_prompts=None,
        slide_specs=_specs(["generated", "generated"], ["placeholder", "placeholder"]),
        lint_report=None,
    )
    assert db["rows"][0]["image_status"] == "fully_generated"
    assert db["rows"][1]["image_status"] == "placeholder_only"


def test_dashboard_lint_summary_per_page():
    lint_report = {
        "ts": "2026-04-26T10:00:00Z",
        "gate": "gate_7",
        "results": [
            {"page_no": 1, "category": "layout_geometry", "rule": "regions_overlap", "severity": "fail"},
            {"page_no": 2, "category": "content_quality", "rule": "duplicate_core_message", "severity": "warn"},
        ],
        "deck_level": [],
    }
    db = dashboard.build_dashboard(
        outline=_outline("locked", "locked"),
        slide_prompts=_slide_prompts("locked", "locked"),
        slide_specs=_specs(["placeholder"], ["placeholder"]),
        lint_report=lint_report,
    )
    assert "fail" in db["rows"][0]["lint"]
    assert "warn" in db["rows"][1]["lint"]


def test_deck_summary_ready_for_render_when_all_locked():
    db = dashboard.build_dashboard(
        outline=_outline("locked", "locked"),
        slide_prompts=_slide_prompts("locked", "locked"),
        slide_specs=_specs(["generated"], ["generated"]),
        lint_report=None,
    )
    assert db["deck_summary"]["ready_for_render"] is True
    assert db["deck_summary"]["locked_intent"] == 2


def test_deck_summary_not_ready_when_any_draft():
    db = dashboard.build_dashboard(
        outline=_outline("locked", "draft"),
        slide_prompts=_slide_prompts("locked", "draft"),
        slide_specs=_specs(["placeholder"], ["placeholder"]),
        lint_report=None,
    )
    assert db["deck_summary"]["ready_for_render"] is False


def test_format_table_emits_human_readable_text():
    db = dashboard.build_dashboard(
        outline=_outline("locked"),
        slide_prompts=_slide_prompts("locked"),
        slide_specs=_specs(["generated"]),
        lint_report=None,
    )
    out = dashboard.format_table(db)
    assert "Page" in out and "Outline" in out and "Intent" in out
    assert "1" in out
    assert "locked" in out
    assert "fully_generated" in out


def test_main_with_explicit_paths(tmp_path, capsys):
    outline = _outline("draft", "locked")
    prompts = _slide_prompts("draft", "locked")
    specs = _specs(["placeholder"], ["generated"])
    out_path = tmp_path / "outline.json"
    out_path.write_text(json.dumps(outline), encoding="utf-8")
    p_path = tmp_path / "slide_prompts.json"
    p_path.write_text(json.dumps(prompts), encoding="utf-8")
    s_path = tmp_path / "slide_specs.json"
    s_path.write_text(json.dumps(specs), encoding="utf-8")

    rc = dashboard.main([
        "--outline", str(out_path),
        "--slide-prompts", str(p_path),
        "--slide-specs", str(s_path),
    ])
    assert rc == 0
    captured = capsys.readouterr().out
    assert "page" in captured.lower() or "Page" in captured


def test_main_json_output(tmp_path, capsys):
    outline = _outline("draft")
    out_path = tmp_path / "outline.json"
    out_path.write_text(json.dumps(outline), encoding="utf-8")
    rc = dashboard.main(["--outline", str(out_path), "--json"])
    assert rc == 0
    parsed = json.loads(capsys.readouterr().out)
    assert "rows" in parsed
    assert parsed["rows"][0]["page_no"] == 1
