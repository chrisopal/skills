from __future__ import annotations

from style.header import build_style_header


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

    assert "母版提示词" in header
    assert "统一白底、强对比" in header
    assert "企业咨询风" in header
    assert "逐页约束" in header


def test_build_style_header_marks_measurements_as_invisible_constraints() -> None:
    header = build_style_header(
        {
            "layout_system": {"margins": "左右 56-72px，上下 40-56px", "module_spacing": "20-28px"},
            "typography": {"caption": "12-14px, gray", "page_title": "36-44px, bold"},
        }
    )

    assert "不可见设计约束" in header
    assert "不要把" in header
    assert "px" in header
    assert "Caption" not in header


def test_build_style_header_forbids_visible_design_annotations() -> None:
    header = build_style_header({"prompt_block": "白底，绿色主色。"})

    assert "禁止渲染尺寸标注" in header
    assert "红色标注框" in header
    assert "设计稿标尺" in header
