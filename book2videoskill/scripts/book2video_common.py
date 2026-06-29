#!/usr/bin/env python3
"""Shared helpers for Book2VideoSkill scaffold tools."""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import re
from pathlib import Path
from typing import Any


DEFAULTS: dict[str, Any] = {
    "targetPlatform": "xiaohongshu",
    "durationLimitSec": 300,
    "targetDurationSec": 240,
    "aspectRatio": "9:16",
    "coverAspectRatio": "4:5",
    "targetAudience": ["职场人", "项目经理", "售前顾问", "管理者"],
    "tone": "专业、清晰、克制、启发式",
    "stylePreference": "极简商务知识风，暖白背景，黑字，橙色强调，卡片式结构，轻动画",
    "stylePreset": "orange_primary_green_secondary",
    "outputMode": "remotion",
    "language": "zh-CN",
    "generateAssets": True,
    "renderVideo": True,
}

PALETTE = {
    "background": "#FFFDF7",
    "primary": "#F97316",
    "secondary": "#0B5D3B",
    "primaryText": "#111111",
    "secondaryText": "#333333",
    "mutedText": "#666666",
    "cardBg": "#FFFFFF",
    "line": "#F4A261",
    "highlight": "#FF6A00",
}


def slugify_book(title: str) -> str:
    if is_pyramid_principle(title):
        return "pyramid-principle"
    if is_principles(title):
        return "principles-ray-dalio"
    ascii_slug = re.sub(r"[^a-zA-Z0-9._-]+", "-", title.strip()).strip("-").lower()
    ascii_slug = re.sub(r"-{2,}", "-", ascii_slug)
    if ascii_slug:
        return ascii_slug[:80]
    digest = hashlib.sha1(title.encode("utf-8")).hexdigest()[:8]
    return f"book-{digest}"


def slugify_skill_name(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip()).strip("-").lower()
    slug = re.sub(r"-{2,}", "-", slug)
    return (slug or "book-method-skill")[:64]


def project_name(title: str) -> str:
    if is_pyramid_principle(title):
        return "Book2Video_ThePyramidPrinciple"
    if is_principles(title):
        return "Book2Video_Principles_RayDalio"
    slug = slugify_book(title).replace("-", "_")
    return f"Book2Video_{slug}"


def is_pyramid_principle(title: str) -> bool:
    lowered = title.lower()
    return "金字塔原理" in title or "pyramid principle" in lowered


def is_principles(title: str) -> bool:
    lowered = title.lower()
    normalized = title.replace("《", "").replace("》", "").strip()
    return normalized == "原则" or "principles" in lowered or "ray dalio" in lowered


def load_input(path: str | None) -> dict[str, Any]:
    if not path:
        return {}
    return json.loads(Path(path).read_text(encoding="utf-8"))


def normalize_input(raw: dict[str, Any]) -> dict[str, Any]:
    data = {**DEFAULTS, **{k: v for k, v in raw.items() if v is not None}}
    if not data.get("bookTitle"):
        raise ValueError("bookTitle is required")
    data["durationLimitSec"] = int(data["durationLimitSec"])
    data["targetDurationSec"] = min(int(data["targetDurationSec"]), data["durationLimitSec"])
    return data


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def relpath(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def repo_default_projects_root() -> Path:
    return Path(__file__).resolve().parents[1] / "projects"


def style_bible(input_data: dict[str, Any], output_dir: Path) -> dict[str, Any]:
    aspect_ratio = input_data["aspectRatio"]
    width, height = (1080, 1920) if aspect_ratio == "9:16" else (1920, 1080)
    return {
        "projectName": project_name(input_data["bookTitle"]),
        "createdAt": dt.datetime.now().isoformat(timespec="seconds"),
        "aspectRatio": aspect_ratio,
        "coverAspectRatio": input_data.get("coverAspectRatio", "4:5"),
        "width": width,
        "height": height,
        "coverWidth": 1080,
        "coverHeight": 1350,
        "fps": 30,
        "durationLimitSec": input_data["durationLimitSec"],
        "targetDurationSec": input_data["targetDurationSec"],
        "platform": input_data["targetPlatform"],
        "seriesLabel": "一本书，一个AI Skill",
        "stylePreset": input_data["stylePreset"],
        "visualStyle": {
            "styleKeywords": [
                "xiaohongshu knowledge poster",
                "business infographic",
                "consulting visual note",
                "orange primary color",
                "green secondary accent",
                "warm white background",
                "structured grid",
                "boxed modules",
                "clean line icons",
            ],
            "palette": PALETTE,
            "fontFamily": "system-ui, PingFang SC, Microsoft YaHei, sans-serif",
            "titleStyle": "extra bold, large, high contrast, orange dominant",
            "captionStyle": "max 2 lines, clean and high readability",
            "illustrationStyle": "minimal editorial line illustration, professional, not childish",
            "infographicStyle": "structured business infographic with panels, arrows, hierarchy diagrams and icons",
            "layoutStyle": "large title + modular cards + central diagram + bottom tags",
            "coverStyle": "4:5 Xiaohongshu poster, orange dominant, green supporting, strong headline",
            "transitionStyle": ["fade", "slide-left", "soft-zoom"],
            "motionStyle": "gentle, structured, not flashy",
        },
        "audioStyle": {
            "tts": {"voice": "default-zh-professional", "speed": 1.0, "emotion": "calm"},
            "bgm": {"style": "calm structured knowledge explainer", "volume": 0.18, "ducking": True},
        },
        "ctaStyle": "收藏这条，把一本书变成一个可执行的AI Skill。",
        "projectDir": output_dir.as_posix(),
    }


def hhmmss(seconds: int) -> str:
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    return f"{hours:02d}:{minutes:02d}:{secs:02d},000"
