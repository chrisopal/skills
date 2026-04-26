"""Cover lint orchestrator: per-gate routing, exit codes, state machine update."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

SKILL_ROOT = Path(__file__).resolve().parent.parent
SCRIPT_PATH = SKILL_ROOT / "scripts" / "run_all_lints.py"
REPORT_SCHEMA_PATH = SKILL_ROOT / "assets" / "schemas" / "lint_report.schema.json"


def _load_module():
    name = "run_all_lints"
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


orchestrator = _load_module()


def _outline(n: int = 2) -> dict:
    return {"slides": [{"page_no": i, "title": f"page {i}"} for i in range(1, n + 1)]}


def _slide_prompts() -> dict:
    return {
        "slides": [
            {
                "page_no": 1,
                "title": "page 1",
                "page_goal": "demo",
                "layout_type": "cover",
                "key_blocks": [],
                "compiled_prompt": "draw",
                "core_message": "msg one",
            }
        ],
        "quality_checklist": {},
    }


def _slide_specs() -> dict:
    return {
        "slides": [{
            "page_no": 1,
            "title": "page 1",
            "visible_content": {
                "title": "page 1",
                "blocks": [],
                "image_placeholders": [],
                "image_assets": [],
            },
            "image_placeholders": [],
            "image_assets": [],
            "layout_regions": {
                "title": {"x": 0.5, "y": 0.4, "w": 12.333, "h": 1.0},
                "content": {"x": 0.5, "y": 1.6, "w": 12.333, "h": 5.4},
                "images": {"x": 1, "y": 1, "w": 1, "h": 1},
                "mode": "auto",
            },
            "template_variant": {},
            "script_path": "slides/slide-01.js",
        }]
    }


@pytest.fixture(scope="module")
def report_validator():
    return Draft202012Validator(json.loads(REPORT_SCHEMA_PATH.read_text(encoding="utf-8")))


def test_gate_4_runs_only_outline_schema_lint():
    report = orchestrator.run(gate="gate_4", outline=_outline(2))
    rules = {r["rule"] for r in report["results"] + report["deck_level"]}
    # gate_4 should only emit schema-class rules; no geometry/style/content rules
    for rule in rules:
        assert "geometry" not in rule
        assert "style" not in rule
        assert "core_message" not in rule


def test_gate_5_runs_schema_plus_content_quality():
    bad = _slide_prompts()
    bad["slides"][0]["core_message"] = ""  # missing
    report = orchestrator.run(gate="gate_5", slide_prompts=bad)
    rules = {r["rule"] for r in report["results"]}
    assert "missing_core_message" in rules


def test_gate_7_runs_schema_geometry_style():
    specs = _slide_specs()
    # Make geometry fail
    specs["slides"][0]["layout_regions"]["title"] = {"x": 0, "y": 0, "w": 200, "h": 1}
    report = orchestrator.run(
        gate="gate_7",
        slide_specs=specs,
    )
    rules = {r["rule"] for r in report["results"]}
    assert "region_outside_canvas" in rules


def test_invalid_gate_raises():
    with pytest.raises(ValueError):
        orchestrator.run(gate="gate_99")


def test_report_validates_against_schema(report_validator):
    report = orchestrator.run(gate="gate_5", slide_prompts=_slide_prompts())
    report_validator.validate(report)


def test_exit_code_pass_when_all_pass():
    report = orchestrator.run(gate="gate_5", slide_prompts=_slide_prompts())
    assert orchestrator.report_exit_code(report) == 0


def test_exit_code_fail_when_any_fail():
    bad = _slide_prompts()
    bad["slides"][0]["core_message"] = ""
    report = orchestrator.run(gate="gate_5", slide_prompts=bad)
    assert orchestrator.report_exit_code(report) == 2


def test_exit_code_warn_only():
    prompts = _slide_prompts()
    prompts["slides"].append({
        "page_no": 2,
        "title": "page 2",
        "page_goal": "demo",
        "layout_type": "cover",
        "key_blocks": [],
        "compiled_prompt": "draw",
        "core_message": "msg one",  # duplicate -> warn, not fail
    })
    report = orchestrator.run(gate="gate_5", slide_prompts=prompts)
    assert orchestrator.report_exit_code(report) == 1


def test_update_page_state_flips_fail_pages_to_needs_rework(tmp_path):
    prompts = _slide_prompts()
    prompts["slides"][0]["core_message"] = ""
    prompts["slides"][0]["intent_status"] = "locked"
    prompts_path = tmp_path / "slide_prompts.json"
    prompts_path.write_text(json.dumps(prompts, ensure_ascii=False), encoding="utf-8")

    report = orchestrator.run(
        gate="gate_5", slide_prompts=json.loads(prompts_path.read_text(encoding="utf-8"))
    )
    mutated = orchestrator.update_page_state(
        report=report, outline_path=None, slide_prompts_path=prompts_path,
    )
    assert mutated == 1
    after = json.loads(prompts_path.read_text(encoding="utf-8"))
    assert after["slides"][0]["intent_status"] == "needs_rework"


def test_audience_propagates_to_content_judge():
    captured = {}

    def caller(prompt):
        captured["prompt"] = prompt
        return {"score": 0.9, "reason": "ok"}

    orchestrator.run(
        gate="gate_5",
        slide_prompts=_slide_prompts(),
        audience="C-suite",
        content_caller=caller,
    )
    assert "C-suite" in captured.get("prompt", "")
