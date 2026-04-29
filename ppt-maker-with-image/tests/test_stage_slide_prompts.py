from __future__ import annotations

import re

from llm.config import ModelConfig, ModelRoleConfig, ProviderConfig
from pipeline import stage_slide_prompts
from style.header import build_style_header


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


def _assert_no_raw_specs(text: str) -> None:
    assert not re.search(r"\b(?:px|pt)\b", text, flags=re.IGNORECASE)
    assert not re.search(r"\b(?:stroke|shadow|margin|margins|spacing|caption)\b", text, flags=re.IGNORECASE)
    assert "R=" not in text
    assert "【版式系统】" not in text
    assert "【字体】" not in text
    assert "primary_green:" not in text.lower()
    assert not re.search(
        r"\b(?:40\s*-\s*56|56\s*-\s*72|20\s*-\s*28|24\s*-\s*30|12\s*-\s*14|16\s*-\s*18|18\s*-\s*22|36\s*-\s*44)\b",
        text,
    )


def test_stage_slide_prompts_omits_raw_master_style_when_style_header_present(monkeypatch) -> None:
    recorded: dict[str, object] = {}
    style_header = build_style_header(
        {
            "prompt_block": "白底，绿色主色，teal 辅色，咨询风。",
            "color_strategy": {
                "primary_green": "#A8D86B",
                "secondary_teal": "#0F95B6",
                "background": "#FFFFFF",
                "section_background": "#F5F7FA",
            },
            "layout_system": {
                "margins": "左右 56-72px，上下 40-56px",
                "module_spacing": "20-28px",
                "module_shapes": "圆角矩形，R=14px",
                "stroke": "1-1.25pt",
                "shadow": "5-8% black",
            },
            "typography": {"title_font": "Microsoft YaHei", "page_title": "36-44px, bold"},
        },
        {"global_intent": "突出经营结论"},
    )
    page_intent = {
        "global_intent": "突出经营结论",
        "slides": [{"page_no": 1, "intent": "先讲背景", "slide_role": "intro", "key_blocks": ["背景"]}],
    }

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
        page_intent=page_intent,
        dry_run=False,
    )

    assert payload["slides"][0]["image_prompt"].startswith(style_header)
    assert recorded["model"] == "test-text-model"
    message = recorded["messages"][0]["content"]
    assert "Page intent:" in message
    assert '"global_intent": "突出经营结论"' in message
    assert "Style header:" in message
    assert style_header in message
    assert "36-44px" not in message
    assert "Master style:\n{}" in message
    assert "白底" in payload["slides"][0]["image_prompt"]
    assert "Microsoft YaHei" in payload["slides"][0]["image_prompt"]
    assert "设计规范页" in payload["slides"][0]["image_prompt"]
    _assert_no_raw_specs(payload["slides"][0]["image_prompt"])


def test_stage_slide_prompts_sanitizes_raw_spec_fragments_from_final_image_prompt(monkeypatch) -> None:
    style_header = build_style_header(
        {
            "prompt_block": "白底，绿色主色，teal 辅色，咨询风。",
            "layout_system": {"margins": "左右 56-72px，上下 40-56px", "module_spacing": "20-28px"},
            "typography": {"title_font": "Microsoft YaHei", "page_title": "36-44px, bold"},
        },
        {"global_intent": "聚焦业务复盘"},
    )

    def _fake_complete_json(**_kwargs):
        return {
            "slides": [
                {
                    "page_no": 1,
                    "title": "封面",
                    "slide_role": "intro",
                    "key_blocks": ["背景"],
                    "image_prompt": (
                        "Create a slide titled '封面' with white background and green highlights, rounded cards, and Microsoft YaHei.\n"
                        "【字体】page_title: 36-44px, bold\n"
                        "Design slide with margins 56-72px and caption 12-14px, keep the hierarchy clean.\n"
                        "margins: 左右 56-72px，上下 40-56px\n"
                        "caption: 12-14px, gray"
                    ),
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
        page_intent={"global_intent": "聚焦业务复盘"},
        dry_run=False,
    )

    final_prompt = payload["slides"][0]["image_prompt"]
    assert "Create a slide titled '封面'" in final_prompt
    assert "白底" in final_prompt
    assert "绿色" in final_prompt
    assert "rounded cards" in final_prompt
    assert "Microsoft YaHei" in final_prompt
    assert "hierarchy clean" in final_prompt
    assert "设计规范页" in final_prompt
    _assert_no_raw_specs(final_prompt)
