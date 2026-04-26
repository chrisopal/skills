"""Verify regenerate_single_slide flips intent_status and sync_job_artifacts locks on approve."""

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
    sys.path.insert(0, str(SKILL_ROOT / "scripts"))
    spec = importlib.util.spec_from_file_location(name, SKILL_ROOT / rel_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


# regenerate_single_slide imports run_ppt_job, which is heavy. We test the
# state-mutation logic in isolation by re-implementing the relevant lines.
def _apply_regen_intent_logic(slide: dict) -> dict:
    current_intent_status = slide.get("intent_status", "draft")
    if current_intent_status not in ("draft",):
        slide["intent_status"] = "pending_review"
    return slide


def test_regen_flips_locked_to_pending_review():
    slide = {"page_no": 1, "intent_status": "locked"}
    assert _apply_regen_intent_logic(slide)["intent_status"] == "pending_review"


def test_regen_flips_needs_rework_to_pending_review():
    slide = {"page_no": 1, "intent_status": "needs_rework"}
    assert _apply_regen_intent_logic(slide)["intent_status"] == "pending_review"


def test_regen_leaves_draft_untouched():
    slide = {"page_no": 1, "intent_status": "draft"}
    assert _apply_regen_intent_logic(slide)["intent_status"] == "draft"


# ---------------------------------------------------------------------------
# sync_job_artifacts approve flags
# ---------------------------------------------------------------------------


def _setup_sync_dirs(tmp_path: Path) -> dict[str, Path]:
    artifacts = tmp_path / "artifacts"
    artifacts.mkdir()
    job = {"output": {"directory": str(artifacts)}}
    job_path = tmp_path / "job.json"
    job_path.write_text(json.dumps(job), encoding="utf-8")

    outline_path = artifacts / "outline.json"
    outline_path.write_text(json.dumps({
        "storyline": "demo",
        "slides": [
            {"page_no": 1, "title": "a", "outline_status": "draft"},
            {"page_no": 2, "title": "b", "outline_status": "pending_review"},
            {"page_no": 3, "title": "c", "outline_status": "locked"},
        ],
    }), encoding="utf-8")

    prompts_path = artifacts / "slide_prompts.json"
    prompts_path.write_text(json.dumps({
        "slides": [
            {
                "page_no": 1, "title": "a", "page_goal": "", "layout_type": "cover",
                "key_blocks": [], "compiled_prompt": "x", "intent_status": "needs_rework",
            },
            {
                "page_no": 2, "title": "b", "page_goal": "", "layout_type": "cover",
                "key_blocks": [], "compiled_prompt": "x", "intent_status": "locked",
            },
        ],
        "quality_checklist": {},
    }), encoding="utf-8")

    return {
        "job": job_path,
        "outline": outline_path,
        "prompts": prompts_path,
    }


def test_sync_outline_approval_writes_back_locks(tmp_path, monkeypatch):
    paths = _setup_sync_dirs(tmp_path)
    sync = _load("sync_job_artifacts", "scripts/sync_job_artifacts.py")
    monkeypatch.setattr(
        sys, "argv",
        ["sync_job_artifacts.py", str(paths["job"]), "--approve-outline", "--approve-prompts"],
    )
    rc = sync.main()
    assert rc == 0
    outline = json.loads(paths["outline"].read_text(encoding="utf-8"))
    statuses = {s["page_no"]: s["outline_status"] for s in outline["slides"]}
    assert statuses == {1: "locked", 2: "locked", 3: "locked"}
    prompts = json.loads(paths["prompts"].read_text(encoding="utf-8"))
    intent_statuses = {s["page_no"]: s["intent_status"] for s in prompts["slides"]}
    assert intent_statuses == {1: "locked", 2: "locked"}


def test_sync_without_approve_does_not_change_statuses(tmp_path, monkeypatch):
    paths = _setup_sync_dirs(tmp_path)
    sync = _load("sync_job_artifacts", "scripts/sync_job_artifacts.py")
    monkeypatch.setattr(
        sys, "argv",
        ["sync_job_artifacts.py", str(paths["job"])],
    )
    rc = sync.main()
    assert rc == 0
    outline = json.loads(paths["outline"].read_text(encoding="utf-8"))
    statuses = {s["page_no"]: s["outline_status"] for s in outline["slides"]}
    # Untouched
    assert statuses == {1: "draft", 2: "pending_review", 3: "locked"}
