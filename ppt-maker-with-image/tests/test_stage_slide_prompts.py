from __future__ import annotations

from llm.config import ModelConfig, ModelRoleConfig, ProviderConfig
from pipeline import stage_slide_prompts


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


def test_stage_slide_prompts_omits_raw_master_style_when_style_header_present(monkeypatch) -> None:
    recorded: dict[str, object] = {}
    style_header = "【不可见设计约束】只作为版式控制。"

    def _fake_complete_json(**kwargs):
        recorded.update(kwargs)
        return {
            "slides": [
                {
                    "page_no": 1,
                    "title": "封面",
                    "slide_role": "intro",
                    "key_blocks": ["背景"],
                    "image_prompt": "页面正文",
                }
            ]
        }

    monkeypatch.setattr(stage_slide_prompts, "complete_json", _fake_complete_json)
    monkeypatch.setattr(
        stage_slide_prompts,
        "_text_config",
        lambda *_args, **_kwargs: ("test-text-model", "test-key", "https://openrouter.ai/api/v1"),
    )

    payload = stage_slide_prompts.run_stage(
        {
            "topic": "Q2经营分析",
            "target_audience": "管理层",
            "purpose": "汇报",
            "style": "咨询风",
            "page_count": 1,
        },
        _model_config(),
        {"typography": {"page_title": "36-44px, bold"}},
        {"slides": [{"page_no": 1, "title": "封面", "purpose": "引言", "key_blocks": ["背景"]}]},
        style_header=style_header,
        dry_run=False,
    )

    assert payload["slides"][0]["image_prompt"].startswith(style_header)
    assert recorded["model"] == "test-text-model"
    message = recorded["messages"][0]["content"]
    assert style_header in message
    assert "36-44px" not in message
    assert "Master style:\n{}" in message
