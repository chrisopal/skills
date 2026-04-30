from __future__ import annotations

import json
from typing import Any

from llm import complete_json
from llm.config import ModelConfig

from ._stage_utils import _text_config
from .common import build_requirement_summary, load_prompt_template


def run_stage(job: dict[str, Any], config: ModelConfig, *, dry_run: bool) -> dict[str, Any]:
    if job.get("outline"):
        return {"storyline": job.get("storyline", ""), "slides": job["outline"]}

    if dry_run:
        slides = []
        for idx in range(1, int(job["page_count"]) + 1):
            slides.append(
                {
                    "page_no": idx,
                    "title": f"{job['topic']} - 第{idx}页",
                    "subtitle": "",
                    "purpose": "支撑整体叙事",
                    "layout_type": "content",
                    "key_blocks": job.get("key_points", [])[:3] or [f"关键模块{idx}A", f"关键模块{idx}B"],
                }
            )
        return {"storyline": f"围绕{job['topic']}逐步展开", "slides": slides}

    prompt = load_prompt_template("Outline Generation Prompt").format(
        requirement_json=json.dumps(build_requirement_summary(job), ensure_ascii=False, indent=2),
        page_count=job["page_count"],
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
    raise RuntimeError("LLM outline stage returned non-dict payload")
