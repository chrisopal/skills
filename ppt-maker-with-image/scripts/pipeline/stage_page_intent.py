from __future__ import annotations

import json
from typing import Any

from llm import complete_json
from llm.config import ModelConfig

from ._stage_utils import _text_config
from .common import build_requirement_summary, load_prompt_template


def run_stage(
    job: dict[str, Any],
    config: ModelConfig,
    master_style: dict[str, Any],
    outline_payload: dict[str, Any],
    *,
    dry_run: bool,
) -> dict[str, Any]:
    if job.get("page_intent"):
        return job["page_intent"]

    if dry_run:
        slides = []
        for slide in outline_payload.get("slides", []):
            page_no = int(slide.get("page_no") or 0)
            if page_no <= 0:
                continue
            slides.append(
                {
                    "page_no": page_no,
                    "intent": f"保持与主风格一致，突出{slide.get('purpose', '当前页面内容')}。",
                    "slide_role": slide.get("purpose", ""),
                    "slide_blocks": slide.get("key_blocks", []),
                }
            )
        global_intent = (
            f"围绕“{job.get('topic', '该主题')}”生成稳定一致的 deck；"
            "每页先统一叙事主线，再补齐页面差异化信息。"
        )
        return {
            "global_intent": global_intent,
            "slides": slides,
            "master_style_summary": {
                "visual_positioning": master_style.get("visual_positioning", ""),
                "deck_voice": master_style.get("deck_voice", ""),
            },
        }

    prompt = load_prompt_template("Page Intent Generation Prompt").format(
        requirement_json=json.dumps(build_requirement_summary(job), ensure_ascii=False, indent=2),
        master_style_json=json.dumps(master_style, ensure_ascii=False, indent=2),
        outline_json=json.dumps(outline_payload, ensure_ascii=False, indent=2),
    )
    model, api_key, base_url = _text_config(config)
    payload = complete_json(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        api_key=api_key,
        base_url=base_url,
    )
    if isinstance(payload, dict):
        if not payload.get("global_intent") and isinstance(payload.get("page_intent"), dict):
            payload = payload["page_intent"]
        if "global_intent" not in payload and "slides" not in payload and isinstance(payload.get("intent"), list):
            payload = {"global_intent": "以已生成主风格为约束的页面意图", "slides": payload["intent"]}
        return payload
    raise RuntimeError("LLM page-intent stage returned non-dict payload")
