from __future__ import annotations

from llm.config import ModelConfig, ModelRoleConfig, ProviderConfig
from pipeline import stage_page_intent


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


def test_stage_page_intent_dry_run_payload_shape() -> None:
    payload = stage_page_intent.run_stage(
        {
            "topic": "财务复盘",
            "page_count": 2,
            "key_points": ["收入", "成本"],
        },
        _model_config(),
        {"visual_positioning": "商务", "deck_voice": "克制"},
        {"slides": [{"page_no": 1, "title": "封面", "purpose": "引言", "key_blocks": ["背景"]}, {"page_no": 2, "title": "结论", "purpose": "总结", "key_blocks": ["收益"]}]},
        dry_run=True,
    )

    assert payload["global_intent"]
    assert len(payload["slides"]) == 2
    assert payload["slides"][0]["page_no"] == 1


def test_stage_page_intent_uses_complete_json(monkeypatch) -> None:
    recorded: dict[str, object] = {}

    def _fake_complete_json(**kwargs):
        recorded.update(kwargs)
        return {"global_intent": "mock", "slides": [{"page_no": 1, "intent": "开场", "slide_role": "lead", "key_blocks": ["目标"]}]}

    monkeypatch.setattr(stage_page_intent, "complete_json", _fake_complete_json)
    monkeypatch.setattr(
        stage_page_intent,
        "_text_config",
        lambda *_args, **_kwargs: ("test-text-model", "test-key", "https://openrouter.ai/api/v1"),
    )

    payload = stage_page_intent.run_stage(
        {
            "topic": "Q2汇报",
            "target_audience": "管理层",
            "purpose": "复盘",
            "style": "咨询",
            "page_count": 1,
        },
        _model_config(),
        {"prompt_block": "白底"},
        {"slides": [{"page_no": 1, "title": "封面", "purpose": "引言"}]},
        dry_run=False,
    )

    assert payload["global_intent"] == "mock"
    assert payload["slides"][0]["intent"] == "开场"
    assert recorded["model"] == "test-text-model"
    assert recorded["messages"][0]["role"] == "user"
