from __future__ import annotations

from llm.config import ModelConfig, ModelRoleConfig, ProviderConfig
from pipeline import stage_master_style


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


def test_stage_master_style_dry_run_returns_expected_shape() -> None:
    payload = stage_master_style.run_stage({"page_count": 3}, _model_config(), dry_run=True)

    assert payload["visual_positioning"] == "正式、专业、结构化"
    assert payload["prompt_block"] == "语言：中文，白底，结构化布局。"
    assert payload["layout_system"]["grid"] == "12-column"


def test_stage_master_style_uses_complete_json_and_huixin_template(monkeypatch) -> None:
    recorded: dict[str, object] = {}

    def _fake_complete_json(**kwargs):
        recorded.update(kwargs)
        return {"prompt_block": "mock-style"}

    monkeypatch.setattr(stage_master_style, "complete_json", _fake_complete_json)
    monkeypatch.setattr(
        stage_master_style,
        "_text_config",
        lambda *_args, **_kwargs: ("test-text-model", "test-key", "https://openrouter.ai/api/v1"),
    )

    payload = stage_master_style.run_stage(
        {
            "template_id": "huixin",
            "template_name": "慧新",
            "topic": "增长复盘",
            "target_audience": "管理层",
            "purpose": "月度汇报",
            "style": "咨询风",
            "page_count": 5,
        },
        _model_config(),
        dry_run=False,
    )

    assert payload == {"prompt_block": "mock-style"}
    assert recorded["model"] == "test-text-model"
    message = recorded["messages"][0]["content"]
    assert "增长复盘" in message
    assert "style_summary" in message
