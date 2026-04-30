from __future__ import annotations

import json
from typing import Any

from llm import complete_json
from llm.config import ModelConfig

from ._stage_utils import _text_config
from .common import build_requirement_summary, load_asset_json, load_prompt_template


def load_template_preset(job: dict[str, Any]) -> dict[str, Any]:
    preset = (job.get("template_id") or "").strip().lower()
    template_name = (job.get("template_name") or "").strip()
    if preset == "huixin" or template_name == "慧新":
        return load_asset_json("huixin_template.json")
    return {}


def run_stage(job: dict[str, Any], config: ModelConfig, *, dry_run: bool) -> dict[str, Any]:
    if job.get("master_style"):
        return job["master_style"]

    if dry_run:
        return {
            "visual_positioning": "正式、专业、结构化",
            "deck_voice": "理性、克制、信息清晰",
            "color_strategy": {"background": "#FFFFFF"},
            "typography": {"title_font": "Microsoft YaHei", "body_font": "Microsoft YaHei"},
            "title_hierarchy_rules": ["每页一个主标题"],
            "layout_system": {"grid": "12-column"},
            "module_layout_patterns": ["双栏对照", "四卡片矩阵"],
            "chart_rules": ["扁平化 2D 图表"],
            "icon_rules": ["统一线性图标"],
            "forbidden_elements": ["3D图表", "随机角标"],
            "prompt_block": "语言：中文，白底，结构化布局。",
        }

    prompt = load_prompt_template("Master Style Brief Generation Prompt").format(
        requirement_json=json.dumps(build_requirement_summary(job), ensure_ascii=False, indent=2),
        template_preset_json=json.dumps(load_template_preset(job), ensure_ascii=False, indent=2),
    )
    model, api_key, base_url = _text_config(config)
    payload = complete_json(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        api_key=api_key,
        base_url=base_url,
    )
    if isinstance(payload, dict):
        return payload
    raise RuntimeError("LLM master-style stage returned non-dict payload")
