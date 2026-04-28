from __future__ import annotations

from llm.config import ModelConfig, ModelRoleConfig, ProviderConfig
import regenerate_single_slide


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


def _provider_fallback_model_config() -> ModelConfig:
    return ModelConfig(
        default_provider="openrouter",
        text=ModelRoleConfig(provider="openrouter", model=""),
        image=ModelRoleConfig(provider="openrouter", model="test-image-model"),
        providers={
            "openrouter": ProviderConfig(
                name="openrouter",
                api_key_env="OPENROUTER_API_KEY",
                base_url="https://openrouter.ai/api/v1",
                text_model="provider-text-model",
            )
        },
    )


def test_regenerate_single_prompt_uses_style_header_page_intent_and_provider_model_fallback(monkeypatch) -> None:
    recorded: dict[str, object] = {}
    style_header = "【不可见设计约束】只作为版式控制。"
    page_intent = {
        "global_intent": "突出经营结论",
        "slides": [{"page_no": 1, "intent": "先讲背景", "slide_role": "intro", "key_blocks": ["背景"]}],
    }

    def _fake_complete_json(**kwargs):
        recorded.update(kwargs)
        return {
            "page_no": 1,
            "title": "封面",
            "slide_role": "intro",
            "key_blocks": ["背景"],
            "image_prompt": "页面正文",
        }

    monkeypatch.setattr(regenerate_single_slide, "complete_json", _fake_complete_json)

    payload = regenerate_single_slide.regenerate_single_prompt(
        {
            "topic": "Q2经营分析",
            "target_audience": "管理层",
            "purpose": "汇报",
            "style": "咨询风",
            "page_count": 1,
        },
        {"typography": {"page_title": "36-44px, bold"}},
        {"slides": [{"page_no": 1, "title": "封面", "purpose": "引言", "key_blocks": ["背景"]}]},
        {"page_no": 1, "title": "封面", "purpose": "引言", "key_blocks": ["背景"]},
        {"page_no": 1, "title": "封面", "slide_role": "intro", "key_blocks": ["背景"], "image_prompt": "旧提示词"},
        "只优化标题表达。",
        style_header=style_header,
        page_intent=page_intent,
        dry_run=False,
        config=_provider_fallback_model_config(),
    )

    assert payload["image_prompt"].startswith(style_header)
    assert recorded["model"] == "provider-text-model"
    message = recorded["messages"][0]["content"]
    assert "Page intent:" in message
    assert '"global_intent": "突出经营结论"' in message
    assert "Style header:" in message
    assert style_header in message
    assert "36-44px" not in message
    assert "Master style:\n{}" in message
