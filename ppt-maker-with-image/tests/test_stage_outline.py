from __future__ import annotations

from llm.config import ModelConfig, ModelRoleConfig, ProviderConfig
from pipeline import stage_outline


def _model_config() -> ModelConfig:
    return ModelConfig(
        default_provider="openrouter",
        text=ModelRoleConfig(provider="openrouter", model="test-text-model"),
        image=ModelRoleConfig(provider="openrouter", model="test-image-model"),
        providers={
            "openrouter": ProviderConfig(
                name="openrouter",
                api_key_env="OPENROUTER_API_KEY",
                base_url="https://openrouter.ai/api/v1",
            )
        },
    )


def test_stage_outline_dry_run_generates_requested_page_count() -> None:
    payload = stage_outline.run_stage(
        {
            "topic": "年度经营回顾",
            "page_count": 3,
            "key_points": ["营收", "利润", "风险"],
        },
        _model_config(),
        dry_run=True,
    )

    assert payload["storyline"] == "围绕年度经营回顾逐步展开"
    assert len(payload["slides"]) == 3
    assert payload["slides"][0]["page_no"] == 1


def test_stage_outline_uses_complete_json(monkeypatch) -> None:
    recorded: dict[str, object] = {}

    def _fake_complete_json(**kwargs):
        recorded.update(kwargs)
        return {"storyline": "mock", "slides": [{"page_no": 1, "title": "封面"}]}

    monkeypatch.setattr(stage_outline, "complete_json", _fake_complete_json)
    monkeypatch.setattr(
        stage_outline,
        "_text_config",
        lambda *_args, **_kwargs: ("test-text-model", "test-key", "https://openrouter.ai/api/v1"),
    )

    payload = stage_outline.run_stage(
        {
            "topic": "解决方案汇报",
            "target_audience": "客户",
            "purpose": "售前沟通",
            "style": "科技商务",
            "page_count": 4,
        },
        _model_config(),
        dry_run=False,
    )

    assert payload["storyline"] == "mock"
    assert recorded["model"] == "test-text-model"
    message = recorded["messages"][0]["content"]
    assert "解决方案汇报" in message
    assert "exactly 4 slides" in message
