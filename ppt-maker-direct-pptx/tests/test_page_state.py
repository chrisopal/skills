"""Cover page state machine: legal/illegal transitions, image aggregation, history."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

SKILL_ROOT = Path(__file__).resolve().parent.parent
LIB_PATH = SKILL_ROOT / "scripts" / "lib" / "page_state.py"


def _load_module():
    name = "page_state"
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, LIB_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


page_state = _load_module()


def _outline(*page_nos: int) -> dict:
    return {
        "slides": [
            {"page_no": p, "title": f"page {p}", "outline_status": "draft"}
            for p in page_nos
        ]
    }


def _slide_prompts(*page_nos: int) -> dict:
    return {
        "slides": [
            {
                "page_no": p,
                "title": f"page {p}",
                "page_goal": "demo",
                "layout_type": "cover",
                "key_blocks": [],
                "compiled_prompt": "draw",
                "intent_status": "draft",
            }
            for p in page_nos
        ],
        "quality_checklist": {},
    }


def _specs_with_placeholders(page_no: int, statuses: list[str]) -> dict:
    return {
        "slides": [{
            "page_no": page_no,
            "title": "demo",
            "visible_content": {"title": "demo", "blocks": [], "image_placeholders": [], "image_assets": []},
            "image_placeholders": [
                {"prompt": f"img {i}", "status": s} for i, s in enumerate(statuses)
            ],
            "image_assets": [],
            "layout_regions": {"content": {}, "images": {}, "mode": "auto"},
            "template_variant": {},
            "script_path": f"slides/slide-0{page_no}.js",
        }]
    }


def test_can_transition_legal_paths():
    machine = page_state.PageStateMachine()
    assert machine.can_transition("draft", "pending_review")
    assert machine.can_transition("pending_review", "locked")
    assert machine.can_transition("pending_review", "needs_rework")
    assert machine.can_transition("needs_rework", "pending_review")
    assert machine.can_transition("locked", "needs_rework")


def test_can_transition_illegal_paths():
    machine = page_state.PageStateMachine()
    assert not machine.can_transition("draft", "locked")
    assert not machine.can_transition("draft", "needs_rework")
    assert not machine.can_transition("locked", "draft")


def test_transition_outline_status_records_history():
    outline = _outline(1, 2)
    machine = page_state.PageStateMachine(outline=outline)
    assert machine.transition(1, "outline_status", "pending_review")
    assert outline["slides"][0]["outline_status"] == "pending_review"
    history = machine.history_for(1)
    assert len(history) == 1
    assert history[0]["from"] == "draft"
    assert history[0]["to"] == "pending_review"


def test_intent_status_blocked_when_outline_not_locked():
    machine = page_state.PageStateMachine(
        outline=_outline(1), slide_prompts=_slide_prompts(1),
    )
    with pytest.raises(page_state.IllegalTransitionError):
        machine.transition(1, "intent_status", "pending_review")


def test_intent_status_unblocked_after_outline_locked():
    machine = page_state.PageStateMachine(
        outline=_outline(1), slide_prompts=_slide_prompts(1),
    )
    machine.transition(1, "outline_status", "pending_review")
    machine.transition(1, "outline_status", "locked")
    assert machine.transition(1, "intent_status", "pending_review")


def test_illegal_state_value_rejected():
    machine = page_state.PageStateMachine(outline=_outline(1))
    with pytest.raises(page_state.IllegalTransitionError):
        machine.transition(1, "outline_status", "kinda")


def test_image_status_only_settable_via_placeholders():
    machine = page_state.PageStateMachine(slide_specs=_specs_with_placeholders(1, ["placeholder"]))
    with pytest.raises(page_state.IllegalTransitionError):
        machine.transition(1, "image_status", "fully_generated")


def test_aggregate_no_image_when_no_placeholders():
    machine = page_state.PageStateMachine(slide_specs={"slides": [{
        "page_no": 1,
        "title": "x",
        "visible_content": {"title": "x", "blocks": [], "image_placeholders": [], "image_assets": []},
        "image_placeholders": [],
        "image_assets": [],
        "layout_regions": {"content": {}, "images": {}, "mode": "auto"},
        "template_variant": {},
        "script_path": "slides/slide-01.js",
    }]})
    assert machine.aggregate_image_status(1) == "no_image"


def test_aggregate_no_image_when_all_skipped():
    machine = page_state.PageStateMachine(
        slide_specs=_specs_with_placeholders(1, ["skipped", "skipped"])
    )
    assert machine.aggregate_image_status(1) == "no_image"


def test_aggregate_placeholder_only():
    machine = page_state.PageStateMachine(
        slide_specs=_specs_with_placeholders(1, ["placeholder", "placeholder"])
    )
    assert machine.aggregate_image_status(1) == "placeholder_only"


def test_aggregate_partially_generated():
    machine = page_state.PageStateMachine(
        slide_specs=_specs_with_placeholders(1, ["placeholder", "generated"])
    )
    assert machine.aggregate_image_status(1) == "partially_generated"


def test_aggregate_fully_generated():
    machine = page_state.PageStateMachine(
        slide_specs=_specs_with_placeholders(1, ["generated", "generated"])
    )
    assert machine.aggregate_image_status(1) == "fully_generated"


def test_aggregate_has_failures_for_regenerating():
    machine = page_state.PageStateMachine(
        slide_specs=_specs_with_placeholders(1, ["placeholder", "regenerating"])
    )
    assert machine.aggregate_image_status(1) == "has_failures"


def test_status_for_page_returns_three_layers():
    outline = _outline(1)
    prompts = _slide_prompts(1)
    specs = _specs_with_placeholders(1, ["generated"])
    machine = page_state.PageStateMachine(outline=outline, slide_prompts=prompts, slide_specs=specs)
    status = machine.status_for(1)
    assert status == {
        "outline_status": "draft",
        "intent_status": "draft",
        "image_status": "fully_generated",
    }


def test_page_numbers_collected_from_all_artifacts():
    machine = page_state.PageStateMachine(
        outline=_outline(1, 2),
        slide_prompts=_slide_prompts(2, 3),
        slide_specs=_specs_with_placeholders(4, ["placeholder"]),
    )
    assert machine.page_numbers() == [1, 2, 3, 4]


def test_persist_writes_only_present_artifacts(tmp_path):
    outline = _outline(1)
    machine = page_state.PageStateMachine(outline=outline)
    machine.transition(1, "outline_status", "pending_review")
    outline_path = tmp_path / "outline.json"
    written = page_state.persist_machine(machine, outline_path=outline_path)
    assert written == 1
    assert outline_path.exists()
