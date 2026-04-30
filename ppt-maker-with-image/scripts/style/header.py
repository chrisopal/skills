from __future__ import annotations

import re
from typing import Any


_HEX_COLOR_RE = re.compile(r"#[0-9A-Fa-f]{6}\b")
_RAW_KEY_VALUE_RE = re.compile(
    r"\b(?:primary_green|secondary_teal|neutral_gray|background|section_background|text_primary|text_secondary|"
    r"divider|grid|margins?|module_spacing|module_shapes|stroke|shadow|title_font|body_font|page_title|"
    r"section_title|subtitle|body_text|caption)\s*:\s*[^;\n]+",
    re.IGNORECASE,
)
_MEASUREMENT_RE = re.compile(r"\b\d+(?:\.\d+)?\s*(?:-\s*\d+(?:\.\d+)?)?\s*(?:px|pt)\b", re.IGNORECASE)
_EXPLICIT_RANGE_RE = re.compile(
    r"\b(?:40\s*-\s*56|56\s*-\s*72|20\s*-\s*28|24\s*-\s*30|12\s*-\s*14|16\s*-\s*18|18\s*-\s*22|36\s*-\s*44)\b"
)
_RADIUS_RE = re.compile(r"R\s*=\s*\d+(?:\.\d+)?(?:\s*(?:px|pt))?", re.IGNORECASE)
_DANGLING_RADIUS_RE = re.compile(r"\bR\s*=\s*", re.IGNORECASE)
_FORBIDDEN_WORD_RE = re.compile(r"\b(?:margins?|spacing|caption|stroke|shadow)\b\s*[:=]?", re.IGNORECASE)
_FORBIDDEN_UNIT_RE = re.compile(r"\b(?:px|pt)\b", re.IGNORECASE)
_FORBIDDEN_LINE_MARKERS = (
    "【版式系统】",
    "【字体】",
    "primary_green:",
    "secondary_teal:",
    "neutral_gray:",
    "section_background:",
    "text_primary:",
    "text_secondary:",
    "divider:",
)
_WHITESPACE_RE = re.compile(r"[ \t]+")
_PUNCT_RE = re.compile(r"(?:\s*[;,:，；]\s*){2,}")
_SPACE_BEFORE_PUNCT_RE = re.compile(r"\s+([,.;:，。；])")
_EMPTY_WITH_AND_RE = re.compile(r"\bwith\s+and\b", re.IGNORECASE)
_DANGLING_CONNECTOR_RE = re.compile(r"\b(?:and|with)\b(?=\s*[,.;:，。；]|$)", re.IGNORECASE)


def _join_lines(lines: list[str]) -> str:
    return "\n".join(line for line in lines if line)


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        result.append(item)
    return result


def _safe_int(item: Any, fallback: str = "") -> str:
    if item is None:
        return fallback
    if isinstance(item, str):
        return item.strip()
    return str(item)


def _normalize_text(text: str) -> str:
    cleaned = text.strip()
    cleaned = _WHITESPACE_RE.sub(" ", cleaned)
    cleaned = _SPACE_BEFORE_PUNCT_RE.sub(r"\1", cleaned)
    cleaned = _EMPTY_WITH_AND_RE.sub("with", cleaned)
    cleaned = _DANGLING_CONNECTOR_RE.sub("", cleaned)
    cleaned = _WHITESPACE_RE.sub(" ", cleaned)
    cleaned = _SPACE_BEFORE_PUNCT_RE.sub(r"\1", cleaned)
    cleaned = re.sub(r"\s*([。！？])", r"\1", cleaned)
    cleaned = _PUNCT_RE.sub("；", cleaned)
    return cleaned.strip("；,，:： ")


def _clean_free_text(value: Any) -> str:
    text = _safe_int(value)
    if not text:
        return ""
    text = _RAW_KEY_VALUE_RE.sub("", text)
    text = _MEASUREMENT_RE.sub("", text)
    text = _EXPLICIT_RANGE_RE.sub("", text)
    text = _RADIUS_RE.sub("", text)
    text = _DANGLING_RADIUS_RE.sub("", text)
    text = _FORBIDDEN_WORD_RE.sub("", text)
    text = _FORBIDDEN_UNIT_RE.sub("", text)
    text = _HEX_COLOR_RE.sub("", text)
    return _normalize_text(text)


def _join_phrases(phrases: list[str]) -> str:
    return "；".join(_dedupe([_normalize_text(phrase) for phrase in phrases if _normalize_text(phrase)]))


def _summarize_list(items: Any) -> str:
    if not isinstance(items, list):
        return _clean_free_text(items)
    cleaned = [_clean_free_text(item) for item in items]
    return _join_phrases([item for item in cleaned if item])


def _summarize_color_strategy(value: Any) -> str:
    if not isinstance(value, dict):
        return _clean_free_text(value)
    serialized = " ".join(_safe_int(part) for part in [*value.keys(), *value.values()])
    serialized_lower = serialized.lower()
    phrases: list[str] = []
    if value or value.get("background") or value.get("section_background"):
        phrases.append("白底为主，允许极浅灰用于分区承托")
    if value.get("primary_green") or "green" in serialized_lower or "#a8d86b" in serialized_lower or "primary" in value:
        phrases.append("绿色用于关键数字、关键词和核心模块")
    if value.get("secondary_teal") or "teal" in serialized_lower or "#0f95b6" in serialized_lower or "secondary" in value:
        phrases.append("teal 用于结构线、二级标题和辅助强调")
    if value.get("neutral_gray") or "gray" in serialized_lower or "grey" in serialized_lower:
        phrases.append("浅灰用于背景层和分隔关系")
    if value.get("text_primary") or value.get("text_secondary"):
        phrases.append("正文以深灰为主，辅助信息用中灰")
    if value.get("divider"):
        phrases.append("分隔线保持轻和克制")
    return _join_phrases(phrases) or _clean_free_text(value)


def _summarize_layout_system(value: Any) -> str:
    if not isinstance(value, dict):
        return _clean_free_text(value)
    phrases: list[str] = []
    if value.get("grid"):
        phrases.append("使用规整栅格和清晰对齐关系")
    if value.get("margins"):
        phrases.append("页面四周保留充足留白")
    if value.get("module_spacing"):
        phrases.append("模块之间保持一致而舒展的间隔")
    if value.get("module_shapes"):
        phrases.append("内容容器采用圆角卡片")
    if value.get("stroke"):
        phrases.append("分隔线细而轻")
    if value.get("shadow"):
        phrases.append("层次感轻微且克制")
    return _join_phrases(phrases) or _clean_free_text(value)


def _summarize_typography(value: Any) -> str:
    if not isinstance(value, dict):
        return _clean_free_text(value)
    phrases: list[str] = []
    font_name = _clean_free_text(value.get("title_font") or value.get("body_font"))
    if font_name:
        phrases.append(f"统一使用 {font_name}")
    if any(value.get(key) for key in ("page_title", "section_title", "subtitle", "body_text", "caption")):
        phrases.append("标题、副标题、正文和辅助说明层级清楚")
        phrases.append("重点信息通过字重与颜色形成明确对比")
    return _join_phrases(phrases) or _clean_free_text(value)


def _contains_forbidden_spec(text: str) -> bool:
    lowered = text.lower()
    return any(marker.lower() in lowered for marker in _FORBIDDEN_LINE_MARKERS) or bool(
        _MEASUREMENT_RE.search(text)
        or _EXPLICIT_RANGE_RE.search(text)
        or _RADIUS_RE.search(text)
        or _FORBIDDEN_WORD_RE.search(text)
        or _FORBIDDEN_UNIT_RE.search(text)
    )


def sanitize_image_prompt(text: str) -> str:
    cleaned_lines: list[str] = []
    for raw_line in text.splitlines():
        line = _normalize_text(raw_line)
        if not line:
            continue
        if _contains_forbidden_spec(line):
            line = _clean_free_text(line)
        if _contains_forbidden_spec(line):
            continue
        if line:
            cleaned_lines.append(line)
    return _join_lines(_dedupe(cleaned_lines)).strip()


def build_style_header(
    master_style: dict[str, Any],
    page_intent: dict[str, Any] | None = None,
) -> str:
    """
    Build a renderer-safe style header for slide prompt generation.
    """
    lines: list[str] = []
    master_style = master_style or {}
    page_intent = page_intent or {}
    lines.append("以下内容只用于控制画面风格与版式，不属于幻灯片可见文案。")
    lines.append(
        "必须生成业务演示文稿页面本身，不得生成设计规范页、样式指南页、标注稿、参数表、色板页、字体说明页、"
        "线框图或任何带辅助线、标尺、注释框、键名和说明标签的页面。"
    )

    prompt_block = _clean_free_text(master_style.get("prompt_block"))
    if prompt_block:
        lines.append(f"整体基调：{prompt_block}。")

    visual_positioning = _clean_free_text(master_style.get("visual_positioning"))
    if visual_positioning:
        lines.append(f"视觉定位：{visual_positioning}。")

    deck_voice = _clean_free_text(master_style.get("deck_voice"))
    if deck_voice:
        lines.append(f"表达气质：{deck_voice}。")

    color_strategy = _summarize_color_strategy(master_style.get("color_strategy"))
    if color_strategy:
        lines.append(f"配色关系：{color_strategy}。")

    layout_system = _summarize_layout_system(master_style.get("layout_system"))
    if layout_system:
        lines.append(f"排版节奏：{layout_system}。")

    typography = _summarize_typography(master_style.get("typography"))
    if typography:
        lines.append(f"字体与层级：{typography}。")

    title_rules = _summarize_list(master_style.get("title_hierarchy_rules"))
    if title_rules:
        lines.append(f"标题层级遵循：{title_rules}。")

    module_patterns = _summarize_list(master_style.get("module_layout_patterns"))
    if module_patterns:
        lines.append(f"常用版面组织：{module_patterns}。")

    chart_rules = _summarize_list(master_style.get("chart_rules"))
    if chart_rules:
        lines.append(f"图表表现：{chart_rules}。")

    icon_rules = _summarize_list(master_style.get("icon_rules"))
    if icon_rules:
        lines.append(f"图标表现：{icon_rules}。")

    forbidden_elements = _summarize_list(master_style.get("forbidden_elements"))
    if forbidden_elements:
        lines.append(f"避免出现：{forbidden_elements}。")

    global_intent = _clean_free_text(page_intent.get("global_intent"))
    if global_intent:
        lines.append(f"整套页面目标：{global_intent}。")

    lines.append("只渲染当前页需要的业务内容，不要把其他页面说明、目录或设计说明带入当前页面。")

    return sanitize_image_prompt(_join_lines(lines))
