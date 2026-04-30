from __future__ import annotations

import pytest

from llm.errors import ProviderError
from llm import text


def test_complete_json_injects_json_instruction(monkeypatch) -> None:
    recorded: dict[str, object] = {}

    def _fake_complete_text(**kwargs):
        recorded.update(kwargs)
        return '{"ok": true}'

    monkeypatch.setattr(text, "complete_text", _fake_complete_text)

    payload = text.complete_json(
        model="test-model",
        messages=[{"role": "user", "content": "Return the result."}],
    )

    messages = recorded["messages"]
    assert payload == {"ok": True}
    assert messages[0]["role"] == "system"
    assert "JSON" in messages[0]["content"]


def test_complete_json_retries_malformed_json_until_valid(monkeypatch: pytest.MonkeyPatch) -> None:
    responses = iter(
        [
            '{"slides": ["unterminated"}',
            '{"slides": ["valid"]}',
        ]
    )
    recorded_calls: list[dict[str, object]] = []

    def _fake_complete_text(**kwargs):
        recorded_calls.append(kwargs)
        return next(responses)

    monkeypatch.setattr(text, "complete_text", _fake_complete_text)

    payload = text.complete_json(
        model="test-model",
        messages=[{"role": "user", "content": "Return the result."}],
    )

    assert payload == {"slides": ["valid"]}
    assert len(recorded_calls) == 2


def test_complete_json_raises_after_bounded_malformed_json_retries(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    recorded_calls: list[dict[str, object]] = []

    def _fake_complete_text(**kwargs):
        recorded_calls.append(kwargs)
        return '{"slides": ["unterminated"}'

    monkeypatch.setattr(text, "complete_text", _fake_complete_text)

    with pytest.raises(ProviderError, match="Text model did not return valid JSON content"):
        text.complete_json(
            model="test-model",
            messages=[{"role": "user", "content": "Return the result."}],
        )

    assert len(recorded_calls) == 3
