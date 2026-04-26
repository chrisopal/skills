"""Cover NL style generation: success, retry-on-invalid, and final failure."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

SKILL_ROOT = Path(__file__).resolve().parent.parent
SCRIPT_PATH = SKILL_ROOT / "scripts" / "style_from_nl.py"


def _load_module():
    name = "style_from_nl"
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


nl_mod = _load_module()


def _valid_response() -> dict:
    return {
        "template_id": "cyber-purple",
        "template_name": "Cyber Purple",
        "language": "zh-CN",
        "visual_positioning": "深蓝紫色赛博朋克科技风",
        "deck_voice": "前沿、科技感、冷峻",
        "color_strategy": {
            "primary": "#7C4DFF",
            "secondary": "#00E5FF",
            "neutral": "#1A1A2E",
            "background": "#0F0F1F",
            "text_primary": "#FFFFFF",
            "text_secondary": "#A8A8C0",
            "divider": "#2A2A4A",
        },
        "typography": {
            "title_font": "Inter",
            "body_font": "Inter",
            "page_title": "40px, bold",
            "body_text": "16px, regular",
        },
        "title_hierarchy_rules": ["title 区只有一个主标题"],
        "layout_system": {"grid": "12-column"},
        "module_layout_patterns": ["KPI 横条", "双栏对照"],
        "chart_rules": ["扁平 2D"],
        "icon_rules": ["线性图标"],
        "forbidden_elements": ["3D 拟物图标"],
        "prompt_block": "Cyber-purple deck, dark navy with violet accents.",
        "source": "nl_generated",
        "parent_template_id": None,
        "confidence": {
            "color_strategy.primary": 0.9,
            "typography.title_font": 0.6,
        },
    }


def _make_caller(responses):
    """Return a callable that yields the next response per call."""

    iterator = iter(responses)

    def call(prompt: str):
        try:
            return next(iterator)
        except StopIteration:  # pragma: no cover - test bug catcher
            raise AssertionError("model_caller invoked more times than configured")

    call.responses = responses
    call.calls = 0
    original = call

    def wrapper(prompt: str):
        wrapper.calls += 1
        return original(prompt)

    wrapper.calls = 0
    wrapper.responses = responses
    return wrapper


def test_first_attempt_success_returns_one_attempt():
    caller = _make_caller([_valid_response()])
    result = nl_mod.generate_style_from_nl("赛博朋克", model_caller=caller)
    assert result.attempts == 1
    assert result.master_style["source"] == "nl_generated"
    assert caller.calls == 1


def test_invalid_then_valid_retries(monkeypatch):
    invalid = _valid_response()
    invalid["source"] = "made_up"  # violates enum
    caller = _make_caller([invalid, _valid_response()])
    result = nl_mod.generate_style_from_nl("赛博朋克", model_caller=caller)
    assert result.attempts == 2
    assert caller.calls == 2


def test_three_invalid_responses_raise_error():
    invalid = _valid_response()
    invalid.pop("color_strategy")
    caller = _make_caller([dict(invalid), dict(invalid), dict(invalid)])
    with pytest.raises(nl_mod.StyleGenerationError) as excinfo:
        nl_mod.generate_style_from_nl("desc", model_caller=caller)
    assert "after 3 attempts" in str(excinfo.value)
    assert caller.calls == 3


def test_non_dict_response_treated_as_invalid_and_retried():
    caller = _make_caller(["not-a-dict", _valid_response()])
    result = nl_mod.generate_style_from_nl("desc", model_caller=caller)
    assert result.attempts == 2


def test_empty_description_rejected():
    with pytest.raises(ValueError):
        nl_mod.generate_style_from_nl("", model_caller=lambda p: {})


def test_prompt_includes_schema_and_description():
    captured: list[str] = []

    def caller(prompt):
        captured.append(prompt)
        return _valid_response()

    nl_mod.generate_style_from_nl("我的描述", model_caller=caller)
    prompt = captured[0]
    assert "我的描述" in prompt
    assert "nl_generated" in prompt
    assert "JSON Schema" in prompt or "json schema" in prompt.lower()


def test_retry_prompt_includes_prior_errors():
    captured: list[str] = []
    invalid = _valid_response()
    invalid["source"] = "wrong"

    def caller(prompt):
        captured.append(prompt)
        return invalid if len(captured) == 1 else _valid_response()

    nl_mod.generate_style_from_nl("desc", model_caller=caller)
    second_prompt = captured[1]
    assert "previous response failed schema" in second_prompt
    assert "source" in second_prompt
