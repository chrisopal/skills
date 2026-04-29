from __future__ import annotations

import json
from typing import Any

from llm import complete_json
from llm.config import ModelConfig

from ._stage_utils import _text_config
from .common import build_requirement_summary, load_prompt_template
from style.header import sanitize_image_prompt


def run_stage(
    job: dict[str, Any],
    config: ModelConfig,
    master_style: dict[str, Any],
    outline_payload: dict[str, Any],
    *,
    style_header: str = "",
    page_intent: dict[str, Any] | None = None,
    dry_run: bool,
) -> dict[str, Any]:
    if job.get("slides"):
        return {"slides": job["slides"]}

    if dry_run:
        slides = []
        for slide in outline_payload.get("slides", []):
            base_prompt = (
                f"中文PPT页面，标题为《{slide['title']}》，白底，结构清晰，包含"
                f"{','.join(slide.get('key_blocks', []))}。"
            )
            slides.append(
                {
                    "page_no": slide["page_no"],
                    "title": slide["title"],
                    "slide_role": slide.get("purpose", ""),
                    "key_blocks": slide.get("key_blocks", []),
                    "image_prompt": f"{style_header}\n\n{base_prompt}".strip(),
                }
            )
        return {"slides": slides}

    prompt_master_style = {} if style_header.strip() else master_style
    prompt = load_prompt_template("Per-Slide Prompt Generation Prompt").format(
        requirement_json=json.dumps(build_requirement_summary(job), ensure_ascii=False, indent=2),
        master_style_json=json.dumps(prompt_master_style, ensure_ascii=False, indent=2),
        page_intent_json=json.dumps(page_intent or {}, ensure_ascii=False, indent=2),
        outline_json=json.dumps(outline_payload, ensure_ascii=False, indent=2),
        style_header=style_header,
    )
    model, api_key, base_url = _text_config(config)
    payload = complete_json(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        api_key=api_key,
        base_url=base_url,
    )
    if isinstance(payload, dict):
        if "slides" not in payload and isinstance(payload.get("slide_prompts"), list):
            payload = {"slides": payload["slide_prompts"]}
        if style_header.strip():
            for slide in payload.get("slides", []):
                image_prompt = str(slide.get("image_prompt", "")).strip()
                slide["image_prompt"] = sanitize_image_prompt(f"{style_header}\n\n{image_prompt}")
        return payload
    raise RuntimeError("LLM slide prompt stage returned non-dict payload")
