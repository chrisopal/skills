from __future__ import annotations

from typing import Any


def _join_lines(lines: list[str]) -> str:
    return "\n".join(line for line in lines if line)


def _format_items(items: list[str]) -> str:
    if not items:
        return ""
    return "\n".join(f"- {item}" for item in items)


def _format_dict_items(items: dict[str, Any]) -> str:
    parts: list[str] = []
    for key, value in items.items():
        text = _safe_int(value)
        if text:
            parts.append(f"{key}: {text}")
    return "; ".join(parts)


def _safe_int(item: Any, fallback: str = "") -> str:
    if item is None:
        return fallback
    if isinstance(item, str):
        return item.strip()
    return str(item)


def build_style_header(
    master_style: dict[str, Any],
    page_intent: dict[str, Any] | None = None,
) -> str:
    """
    Build a deterministic style header for slide prompt generation.
    """
    lines: list[str] = []
    master_style = master_style or {}
    page_intent = page_intent or {}
    lines.append("【不可见设计约束】以下规则只用于控制版式、层级、间距、字体和视觉一致性，不是幻灯片可见文案。")
    lines.append("【禁止渲染尺寸标注】不要把 px、pt、R=、stroke、shadow、margin、spacing、caption 字号、红色标注框、设计稿标尺、对齐辅助线、线框注释或任何提示词/schema文字画到页面上。")

    prompt_block = _safe_int(master_style.get("prompt_block"))
    if prompt_block:
        lines.append(f"【母版提示词】{prompt_block}")

    style_sections: list[tuple[str, Any]] = [
        ("视觉定位", master_style.get("visual_positioning")),
        ("风格语气", master_style.get("deck_voice")),
        ("配色策略", master_style.get("color_strategy")),
        ("版式系统", master_style.get("layout_system")),
        ("字体", master_style.get("typography")),
        ("标题层级", master_style.get("title_hierarchy_rules")),
        ("布局模式", master_style.get("module_layout_patterns")),
        ("图表规范", master_style.get("chart_rules")),
        ("图标规范", master_style.get("icon_rules")),
        ("禁用元素", master_style.get("forbidden_elements")),
    ]
    for title, value in style_sections:
        if value is None:
            continue
        if isinstance(value, list):
            text = _format_items([_safe_int(item) for item in value])
        elif isinstance(value, dict):
            text = _format_dict_items(value)
        else:
            text = _safe_int(value)
        if text:
            lines.append(f"【{title}】{text}")

    global_intent = _safe_int(page_intent.get("global_intent"), "")
    if global_intent:
        lines.append(f"【页面目标】{global_intent}")

    slide_intents = page_intent.get("slides") or []
    if isinstance(slide_intents, list) and slide_intents:
        slide_lines = []
        for item in slide_intents:
            if not isinstance(item, dict):
                continue
            page_no = item.get("page_no")
            intent = _safe_int(item.get("intent"))
            if not page_no or not intent:
                continue
            slide_lines.append(f"第{page_no}页：{intent}")
        if slide_lines:
            lines.append("【逐页约束】")
            lines.append(_format_items(slide_lines))

    return _join_lines(lines).strip()
