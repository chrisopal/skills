"""End-to-end smoke test: drive a tiny 3-page job through all 7 v2 gates."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

SKILL_ROOT = Path(__file__).resolve().parent.parent


def _load(name: str, rel_path: str):
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, SKILL_ROOT / rel_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


orchestrator = _load("run_ppt_job_v2", "scripts/run_ppt_job_v2.py")


def _huixin_palette() -> dict:
    return {
        "primary_green": "#A8D86B",
        "secondary_teal": "#0F95B6",
        "neutral_gray": "#D9D9D9",
        "background": "#FFFFFF",
        "section_background": "#F5F7FA",
        "text_primary": "#1E1E1E",
        "text_secondary": "#6B7280",
        "divider": "#E5E7EB",
    }


def _setup_three_page_job(tmp_path: Path) -> Path:
    artifacts = tmp_path / "artifacts"
    artifacts.mkdir()

    job = {
        "topic": "FY26 季度回顾",
        "target_audience": "C-suite",
        "purpose": "annual review",
        "page_count": 3,
        "key_points": ["growth", "cost", "outlook"],
        "template_id": "huixin",
        "output": {"directory": str(artifacts)},
    }
    job_path = tmp_path / "job.json"
    job_path.write_text(json.dumps(job, ensure_ascii=False), encoding="utf-8")

    outline = {
        "storyline": "open with cover, KPIs, then conclusion",
        "slides": [
            {"page_no": 1, "title": "封面", "outline_status": "locked"},
            {"page_no": 2, "title": "关键指标", "outline_status": "locked"},
            {"page_no": 3, "title": "总结", "outline_status": "locked"},
        ],
    }
    (artifacts / "outline.json").write_text(json.dumps(outline, ensure_ascii=False), encoding="utf-8")

    slide_prompts = {
        "slides": [
            {
                "page_no": 1, "title": "封面", "page_goal": "建立场景",
                "layout_type": "cover", "key_blocks": [],
                "compiled_prompt": "draw cover",
                "core_message": "用一页建立第一印象",
                "intent_status": "locked",
                "pattern_id": "cover",
                "layout_mode": "pattern",
                "slots": {"title": "FY26 季度回顾", "subtitle": "Q1 业务复盘", "org_block": "ACME 集团"},
            },
            {
                "page_no": 2, "title": "关键指标", "page_goal": "展示 KPI",
                "layout_type": "kpi_strip", "key_blocks": [],
                "compiled_prompt": "draw kpi",
                "core_message": "用 4 个 KPI 概括本季度表现",
                "intent_status": "locked",
                "pattern_id": "kpi_strip",
                "layout_mode": "pattern",
                "slots": {
                    "kpi_1_value": "+38%", "kpi_1_label": "ROI",
                    "kpi_2_value": "12k", "kpi_2_label": "MAU",
                    "kpi_3_value": "62", "kpi_3_label": "NPS",
                    "kpi_4_value": "100M", "kpi_4_label": "GMV",
                },
            },
            {
                "page_no": 3, "title": "总结", "page_goal": "Wrap up",
                "layout_type": "summary_takeaways", "key_blocks": [],
                "compiled_prompt": "draw summary",
                "core_message": "总结三大要点并给出下一步行动",
                "intent_status": "locked",
                "pattern_id": "summary_takeaways",
                "layout_mode": "pattern",
                "slots": {
                    "takeaway_1": "增长达成",
                    "takeaway_2": "成本可控",
                    "takeaway_3": "下季前景良好",
                    "next_step": "Q2 锁定北区新客户",
                },
            },
        ],
        "quality_checklist": {},
    }
    (artifacts / "slide_prompts.json").write_text(
        json.dumps(slide_prompts, ensure_ascii=False), encoding="utf-8",
    )

    slide_specs = {
        "slides": [
            {
                "page_no": p,
                "title": title,
                "visible_content": {
                    "title": title, "blocks": [], "image_placeholders": [], "image_assets": [],
                },
                "image_placeholders": [],
                "image_assets": [],
                "layout_regions": {
                    "title": {"x": 0.5, "y": 0.4, "w": 12.333, "h": 1.0},
                    "content": {"x": 0.5, "y": 1.6, "w": 12.333, "h": 5.4},
                    "images": {"x": 0, "y": 0, "w": 0.1, "h": 0.1},
                    "mode": "auto",
                },
                "template_variant": {},
                "script_path": f"slides/slide-{p:02d}.js",
            }
            for p, title in [(1, "封面"), (2, "关键指标"), (3, "总结")]
        ]
    }
    (artifacts / "slide_specs.json").write_text(
        json.dumps(slide_specs, ensure_ascii=False), encoding="utf-8",
    )

    return job_path


def test_e2e_three_page_job_walks_all_gates(tmp_path):
    job_path = _setup_three_page_job(tmp_path)
    job = json.loads(job_path.read_text(encoding="utf-8"))

    outcomes = orchestrator.run_until_failure(job, job_path)

    # All 7 gates ran
    assert [o.gate for o in outcomes] == list(orchestrator.GATES)
    # And each one reached "done" — no failures
    statuses = {o.gate: o.status for o in outcomes}
    failed = [g for g, s in statuses.items() if s != "done"]
    assert failed == [], f"gates failed: {failed} ({statuses})"

    # State persisted to job
    persisted = json.loads(job_path.read_text(encoding="utf-8"))
    history = persisted["v2_gates"]
    assert all(history[g]["status"] == "done" for g in orchestrator.GATES)

    # Artifacts produced
    artifacts = tmp_path / "artifacts"
    assert (artifacts / "master_style.json").exists()
    assert (artifacts / "lint_report.json").exists()
    catalog_dirs = list((artifacts / "pattern_catalog").glob("*"))
    assert any(d.is_dir() for d in catalog_dirs)
    wireframes = list((artifacts / "wireframes").glob("*.svg"))
    assert len(wireframes) == 3  # one per pattern-mode page

    # Lint report has zero fails
    report = json.loads((artifacts / "lint_report.json").read_text(encoding="utf-8"))
    fail_results = [r for r in report["results"] if r["severity"] == "fail"]
    assert fail_results == [], f"unexpected lint fails: {fail_results}"


def test_e2e_partial_run_resumes_from_next_gate(tmp_path):
    job_path = _setup_three_page_job(tmp_path)
    job = json.loads(job_path.read_text(encoding="utf-8"))

    # Run only the first three gates
    for gate in orchestrator.GATES[:3]:
        orchestrator.run_gate(gate, job, job_path)
        job = json.loads(job_path.read_text(encoding="utf-8"))

    # The next pending gate is gate_4
    assert orchestrator.next_gate(job) == "gate_4_outline"

    # Resume to completion
    outcomes = orchestrator.run_until_failure(job, job_path)
    statuses = {o.gate: o.status for o in outcomes}
    assert all(s == "done" for s in statuses.values())
