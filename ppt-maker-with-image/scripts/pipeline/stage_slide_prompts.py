from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from llm import complete_json, read_provider_key
from llm.config import ModelConfig


def _skill_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _load_prompt_template(name: str) -> str:
    content = (_skill_root() / "references" / "prompt-templates.md").read_text(encoding="utf-8")
    anchor = f"## {name}"
    start = content.index(anchor)
    next_idx = content.find("\n## ", start + 1)
    block = content[start : next_idx if next_idx != -1 else len(content)]
    first = block.find("```text")
    last = block.rfind("```")
    if first == -1 or last == -1 or last <= first:
        raise ValueError(f"Prompt template not found: {name}")
    return block[first + len("```text") : last].strip()


def _build_requirement_summary(job: dict[str, Any]) -> dict[str, Any]:
    return {
        "template_id": job.get("template_id"),
        "template_name": job.get("template_name"),
        "topic": job.get("topic"),
        "target_audience": job.get("target_audience"),
        "purpose": job.get("purpose"),
        "style": job.get("style"),
        "page_count": job.get("page_count"),
        "key_points": job.get("key_points", []),
        "must_have_sections": job.get("must_have_sections", []),
        "constraints": job.get("constraints", {}),
    }


def _text_config(config: ModelConfig) -> tuple[str, str | None, str | None]:
    provider = config.get_provider(config.text.provider)
    model = (config.text.model or "").strip()
    if not model and provider:
        model = (provider.text_model or "").strip()
    return (
        model,
        read_provider_key(config.text.provider, providers=config.providers),
        provider.base_url if provider else None,
    )


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
    prompt = _load_prompt_template("Per-Slide Prompt Generation Prompt").format(
        requirement_json=json.dumps(_build_requirement_summary(job), ensure_ascii=False, indent=2),
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
                slide["image_prompt"] = f"{style_header}\n\n{image_prompt}".strip()
        return payload
    raise RuntimeError("LLM slide prompt stage returned non-dict payload")
