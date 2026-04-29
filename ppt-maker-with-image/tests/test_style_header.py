from __future__ import annotations

import re

from style.header import build_style_header, sanitize_image_prompt


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


def test_build_style_header_merge_master_style_and_page_intent() -> None:
    header = build_style_header(
        {
            "prompt_block": "统一白底、强对比",
            "visual_positioning": "企业咨询风",
            "deck_voice": "稳重",
            "forbidden_elements": ["随机角标", "水印"],
        },
        {
            "global_intent": "突出决策与执行闭环",
            "slides": [{"page_no": 1, "intent": "先交代背景"}, {"page_no": 2, "intent": "再给出关键结论"}],
        },
    )

    assert "整体基调" in header
    assert "统一白底、强对比" in header
    assert "企业咨询风" in header
    assert "整套页面目标" in header
    assert "突出决策与执行闭环" in header


def test_build_style_header_rewrites_measurement_specs_as_qualitative_guidance() -> None:
    header = build_style_header(
        {
            "color_strategy": {"primary": "#A8D86B", "secondary": "#0F95B6"},
            "layout_system": {
                "margins": "左右 56-72px，上下 40-56px",
                "module_spacing": "20-28px",
                "module_shapes": "圆角矩形，R=14px",
            },
            "module_layout_patterns": ["双栏对照", "四卡片矩阵"],
            "typography": {"title_font": "Microsoft YaHei", "caption": "12-14px, gray", "page_title": "36-44px, bold"},
        }
    )

    assert "白底" in header
    assert "绿色" in header
    assert "圆角卡片" in header
    assert "Microsoft YaHei" in header
    assert "设计规范页" in header
    assert "业务内容" in header
    _assert_no_raw_specs(header)


def test_build_style_header_forbids_visible_design_annotations() -> None:
    header = build_style_header({"prompt_block": "白底，绿色主色。"})

    assert "样式指南页" in header
    assert "辅助线" in header
    assert "标尺" in header
    _assert_no_raw_specs(header)


def test_sanitize_image_prompt_removes_banned_words_from_freeform_prompt_text() -> None:
    prompt = (
        "Design slide with margins 56-72px and caption 12-14px, white background, "
        "green highlights, rounded cards, Microsoft YaHei, clear business hierarchy."
    )

    sanitized = sanitize_image_prompt(prompt)

    assert "white background" in sanitized
    assert "green highlights" in sanitized
    assert "rounded cards" in sanitized
    assert "Microsoft YaHei" in sanitized
    assert "business hierarchy" in sanitized
    _assert_no_raw_specs(sanitized)
