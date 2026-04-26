"""Cover the 7-gate orchestrator: gate routing, state persistence, fail blocking."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

SKILL_ROOT = Path(__file__).resolve().parent.parent
SCRIPT_PATH = SKILL_ROOT / "scripts" / "run_ppt_job_v2.py"


def _load_module():
    name = "run_ppt_job_v2"
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


orchestrator = _load_module()


def _setup_job(tmp_path: Path, job_extra: dict | None = None) -> tuple[Path, Path]:
    artifacts = tmp_path / "artifacts"
    artifacts.mkdir()
    job = {
        "topic": "FY26 plan",
        "target_audience": "C-suite",
        "purpose": "annual review",
        "page_count": 2,
        "key_points": ["growth", "cost"],
        "template_id": "huixin",
        "output": {"directory": str(artifacts)},
    }
    if job_extra:
        job.update(job_extra)
    job_path = tmp_path / "job.json"
    job_path.write_text(json.dumps(job, ensure_ascii=False), encoding="utf-8")
    return job_path, artifacts


def _outline(*pages, **slide_extra) -> dict:
    return {
        "slides": [
            {"page_no": p, "title": f"page {p}", **slide_extra} for p in pages
        ]
    }


def _slide_prompts(*pages, **slide_extra) -> dict:
    return {
        "slides": [
            {
                "page_no": p,
                "title": f"page {p}",
                "page_goal": "demo",
                "layout_type": "cover",
                "key_blocks": [],
                "compiled_prompt": "draw",
                "core_message": f"msg {p}",
                **slide_extra,
            }
            for p in pages
        ],
        "quality_checklist": {},
    }


def _slide_specs(*pages, image_status: str | None = None) -> dict:
    slides = []
    for p in pages:
        placeholders = []
        if image_status:
            placeholders = [{"id": f"p{p}_img1", "prompt": "img", "status": image_status}]
        slides.append({
            "page_no": p,
            "title": f"page {p}",
            "visible_content": {"title": "demo", "blocks": [], "image_placeholders": [], "image_assets": []},
            "image_placeholders": placeholders,
            "image_assets": [],
            "layout_regions": {
                "title": {"x": 0.5, "y": 0.4, "w": 12.333, "h": 1.0},
                "content": {"x": 0.5, "y": 1.6, "w": 12.333, "h": 5.4},
                "images": {"x": 0, "y": 0, "w": 0.1, "h": 0.1},
                "mode": "auto",
            },
            "template_variant": {},
            "script_path": f"slides/slide-{p:02d}.js",
        })
    return {"slides": slides}


# ---------------------------------------------------------------------------
# gate_1
# ---------------------------------------------------------------------------


def test_gate_1_passes_when_all_required_fields_present(tmp_path):
    job_path, _ = _setup_job(tmp_path)
    job = json.loads(job_path.read_text(encoding="utf-8"))
    outcome = orchestrator.run_gate("gate_1_requirement", job, job_path)
    assert outcome.status == "done"


def test_gate_1_fails_when_field_missing(tmp_path):
    job_path, _ = _setup_job(tmp_path, job_extra={"page_count": ""})
    job = json.loads(job_path.read_text(encoding="utf-8"))
    outcome = orchestrator.run_gate("gate_1_requirement", job, job_path)
    assert outcome.status == "fail"
    assert "page_count" in outcome.summary


# ---------------------------------------------------------------------------
# gate_2
# ---------------------------------------------------------------------------


def test_gate_2_writes_master_style_from_preset(tmp_path):
    job_path, artifacts = _setup_job(tmp_path)
    job = json.loads(job_path.read_text(encoding="utf-8"))
    outcome = orchestrator.run_gate("gate_2_style", job, job_path)
    assert outcome.status == "done"
    assert (artifacts / "master_style.json").exists()
    written = json.loads((artifacts / "master_style.json").read_text(encoding="utf-8"))
    assert written["template_id"] == "huixin"


def test_gate_2_fails_with_unknown_template(tmp_path):
    job_path, _ = _setup_job(tmp_path, job_extra={"template_id": "does-not-exist"})
    job = json.loads(job_path.read_text(encoding="utf-8"))
    outcome = orchestrator.run_gate("gate_2_style", job, job_path)
    assert outcome.status == "fail"


# ---------------------------------------------------------------------------
# gate_3
# ---------------------------------------------------------------------------


def test_gate_3_renders_pattern_catalog(tmp_path):
    job_path, artifacts = _setup_job(tmp_path)
    job = json.loads(job_path.read_text(encoding="utf-8"))
    orchestrator.run_gate("gate_2_style", job, job_path)
    job = json.loads(job_path.read_text(encoding="utf-8"))  # reload
    outcome = orchestrator.run_gate("gate_3_style_preview", job, job_path)
    assert outcome.status == "done"
    catalog_dir = artifacts / "pattern_catalog"
    assert catalog_dir.exists()
    # Some style hash subdir with svgs
    hash_dirs = list(catalog_dir.iterdir())
    assert hash_dirs and any(d.is_dir() for d in hash_dirs)


# ---------------------------------------------------------------------------
# gate_4
# ---------------------------------------------------------------------------


def test_gate_4_runs_outline_lint(tmp_path):
    job_path, artifacts = _setup_job(tmp_path)
    (artifacts / "outline.json").write_text(json.dumps(_outline(1, 2)), encoding="utf-8")
    job = json.loads(job_path.read_text(encoding="utf-8"))
    outcome = orchestrator.run_gate("gate_4_outline", job, job_path)
    assert outcome.status == "done"
    assert outcome.detail["gate"] == "gate_4"


# ---------------------------------------------------------------------------
# gate_5
# ---------------------------------------------------------------------------


def test_gate_5_writes_wireframes_for_pattern_slides(tmp_path):
    job_path, artifacts = _setup_job(tmp_path)
    prompts = _slide_prompts(1, 2)
    prompts["slides"][0]["pattern_id"] = "kpi_strip"
    prompts["slides"][0]["slots"] = {
        "kpi_1_value": "+38%", "kpi_1_label": "ROI",
        "kpi_2_value": "12k", "kpi_2_label": "MAU",
    }
    (artifacts / "slide_prompts.json").write_text(json.dumps(prompts), encoding="utf-8")
    job = json.loads(job_path.read_text(encoding="utf-8"))
    outcome = orchestrator.run_gate("gate_5_intent", job, job_path)
    assert outcome.status == "done"
    wireframes = list((artifacts / "wireframes").glob("*.svg"))
    assert len(wireframes) == 1


# ---------------------------------------------------------------------------
# gate_6
# ---------------------------------------------------------------------------


def test_gate_6_summarizes_image_plan(tmp_path):
    job_path, artifacts = _setup_job(tmp_path)
    specs = _slide_specs(1, image_status="placeholder")
    specs["slides"].append(_slide_specs(2, image_status="skipped")["slides"][0])
    (artifacts / "slide_specs.json").write_text(json.dumps(specs), encoding="utf-8")
    job = json.loads(job_path.read_text(encoding="utf-8"))
    outcome = orchestrator.run_gate("gate_6_image_plan", job, job_path)
    assert outcome.status == "done"
    assert outcome.detail["counts"]["placeholder"] == 1
    assert outcome.detail["counts"]["skipped"] == 1


# ---------------------------------------------------------------------------
# gate_7
# ---------------------------------------------------------------------------


def test_gate_7_runs_full_lint_and_writes_report(tmp_path):
    job_path, artifacts = _setup_job(tmp_path)
    (artifacts / "outline.json").write_text(json.dumps(_outline(1)), encoding="utf-8")
    (artifacts / "slide_prompts.json").write_text(json.dumps(_slide_prompts(1)), encoding="utf-8")
    (artifacts / "slide_specs.json").write_text(json.dumps(_slide_specs(1)), encoding="utf-8")
    orchestrator.run_gate("gate_2_style", json.loads(job_path.read_text(encoding="utf-8")), job_path)
    job = json.loads(job_path.read_text(encoding="utf-8"))
    outcome = orchestrator.run_gate("gate_7_pre_render", job, job_path)
    # Even if lint reports issues, the report file should land
    assert (artifacts / "lint_report.json").exists()
    assert outcome.detail["dashboard"]["deck_summary"]["total_pages"] == 1


# ---------------------------------------------------------------------------
# orchestration helpers
# ---------------------------------------------------------------------------


def test_next_gate_returns_first_pending(tmp_path):
    job_path, _ = _setup_job(tmp_path)
    job = json.loads(job_path.read_text(encoding="utf-8"))
    assert orchestrator.next_gate(job) == "gate_1_requirement"

    job["v2_gates"] = {"gate_1_requirement": {"status": "done"}}
    assert orchestrator.next_gate(job) == "gate_2_style"


def test_state_persists_to_job_json(tmp_path):
    job_path, _ = _setup_job(tmp_path)
    job = json.loads(job_path.read_text(encoding="utf-8"))
    orchestrator.run_gate("gate_1_requirement", job, job_path)
    persisted = json.loads(job_path.read_text(encoding="utf-8"))
    assert persisted["v2_gates"]["gate_1_requirement"]["status"] == "done"


def test_run_until_failure_stops_at_first_fail(tmp_path):
    job_path, _ = _setup_job(tmp_path, job_extra={"template_id": "made_up"})
    job = json.loads(job_path.read_text(encoding="utf-8"))
    outcomes = orchestrator.run_until_failure(job, job_path)
    # gate_1 passes (req fields ok), gate_2 fails (unknown template)
    assert outcomes[-1].status == "fail"
    assert outcomes[-1].gate == "gate_2_style"
