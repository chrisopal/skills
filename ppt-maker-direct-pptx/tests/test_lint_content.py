"""Cover content quality lint: core_message presence, duplicates, audience fit."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

SKILL_ROOT = Path(__file__).resolve().parent.parent
SCRIPT_PATH = SKILL_ROOT / "scripts" / "lint_content.py"


def _load_module():
    name = "lint_content"
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


lint_content = _load_module()


def _slide(page_no: int, **extra) -> dict:
    base = {
        "page_no": page_no,
        "title": f"page {page_no}",
        "page_goal": "demo",
        "layout_type": "cover",
        "key_blocks": [],
        "compiled_prompt": "draw",
        "core_message": f"page {page_no} message",
    }
    base.update(extra)
    return base


def test_missing_core_message_fails():
    prompts = {"slides": [_slide(1, core_message="")]}
    results = lint_content.lint_content(prompts)
    fails = [r for r in results if r.rule == "missing_core_message"]
    assert len(fails) == 1
    assert fails[0].severity == "fail"
    assert fails[0].page_no == 1


def test_duplicate_core_messages_warn():
    prompts = {"slides": [
        _slide(1, core_message="提升运营效率，降低成本"),
        _slide(2, core_message="提升运营效率，降低成本"),
    ]}
    results = lint_content.lint_content(prompts)
    warns = [r for r in results if r.rule == "duplicate_core_message"]
    assert len(warns) == 1
    assert warns[0].severity == "warn"
    assert warns[0].page_no == 1


def test_distinct_core_messages_pass():
    prompts = {"slides": [
        _slide(1, core_message="提升效率"),
        _slide(2, core_message="降低成本"),
    ]}
    results = lint_content.lint_content(prompts)
    assert not any(r.rule == "duplicate_core_message" for r in results)


def test_audience_fit_low_warn_via_mocked_caller():
    prompts = {"slides": [_slide(1, core_message="深入财务三表")]}

    def mock_caller(prompt):
        return {"score": 0.4, "reason": "财务深度对学生受众过载"}

    results = lint_content.lint_content(
        prompts, audience="高一新生", model_caller=mock_caller
    )
    warns = [r for r in results if r.rule == "audience_fit_low"]
    assert len(warns) == 1
    assert "0.40" in warns[0].detail


def test_audience_fit_high_no_warn():
    prompts = {"slides": [_slide(1, core_message="效率提升")]}

    def mock_caller(prompt):
        return {"score": 0.85, "reason": "fits well"}

    results = lint_content.lint_content(
        prompts, audience="C-suite executives", model_caller=mock_caller
    )
    assert not any(r.rule == "audience_fit_low" for r in results)


def test_audience_fit_invalid_response_warns_unavailable():
    prompts = {"slides": [_slide(1, core_message="msg")]}

    results = lint_content.lint_content(
        prompts, audience="X", model_caller=lambda p: "not-an-object"
    )
    assert any(r.rule == "audience_judge_unavailable" for r in results)


def test_audience_fit_skipped_without_caller():
    prompts = {"slides": [_slide(1, core_message="msg")]}
    results = lint_content.lint_content(prompts, audience="X")
    assert not any(r.rule.startswith("audience_") for r in results)


def test_audience_fit_skipped_for_slide_with_empty_core_message():
    prompts = {"slides": [_slide(1, core_message="")]}
    calls = []

    def caller(prompt):
        calls.append(prompt)
        return {"score": 0.9, "reason": ""}

    lint_content.lint_content(prompts, audience="X", model_caller=caller)
    assert calls == []  # never called for empty-core slides


def test_results_attribute_to_correct_page_no():
    prompts = {"slides": [
        _slide(1, core_message=""),
        _slide(2, core_message="ok"),
    ]}
    results = lint_content.lint_content(prompts)
    fail = [r for r in results if r.rule == "missing_core_message"][0]
    assert fail.page_no == 1
