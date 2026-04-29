#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from assemble_pptx import assemble_pptx
from llm import complete_json
from llm.config import ModelConfig, load_model_config
from llm.image.base import ReferenceImage
from pipeline.common import (
    build_requirement_summary,
    ensure_huixin_assets,
    load_json,
    load_prompt_template,
    resolve_output_dir,
    skill_root,
    write_json,
)
from pipeline._stage_utils import _text_config
from style.header import build_style_header, sanitize_image_prompt


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Regenerate one slide prompt or image while preserving deck-level consistency."
    )
    parser.add_argument("job", help="Path to job.json")
    parser.add_argument("--page-no", type=int, required=True, help="1-based slide number")
    parser.add_argument("--instruction", default="", help="Optional extra instruction for this single-slide regeneration")
    parser.add_argument("--config", default="", help="Optional model config yaml override")
    parser.add_argument("--output-dir", default="", help="Optional artifacts directory override")
    parser.add_argument(
        "--render-only",
        action="store_true",
        help="Skip prompt regeneration and only rerender the slide image from existing prompt",
    )
    parser.add_argument("--prompt-only", action="store_true", help="Only regenerate the prompt and do not rerender the image")
    parser.add_argument(
        "--skip-rebuild-pptx",
        action="store_true",
        help="Do not rebuild the full pptx after rerendering the slide",
    )
    parser.add_argument("--dry-run", action="store_true", help="Use placeholder prompt/image generation instead of live model calls")
    return parser


def find_slide_by_page_no(slides: list[dict[str, Any]], page_no: int) -> tuple[int, dict[str, Any]]:
    for index, slide in enumerate(slides):
        if int(slide.get("page_no", index + 1)) == page_no:
            return index, slide
    raise ValueError(f"Slide with page_no={page_no} not found")


def regenerate_single_prompt(
    job: dict[str, Any],
    master_style: dict[str, Any],
    outline_payload: dict[str, Any],
    slide_payload: dict[str, Any],
    existing_prompt: dict[str, Any],
    instruction: str,
    *,
    style_header: str = "",
    page_intent: dict[str, Any] | None = None,
    dry_run: bool,
    config: ModelConfig,
) -> dict[str, Any]:
    page_intent = page_intent or {}
    if not style_header.strip():
        style_header = build_style_header(master_style, page_intent)

    if dry_run:
        prompt = existing_prompt.get("image_prompt") or ""
        prompt = prompt.strip() or f"中文PPT页面，标题为《{slide_payload['title']}》，白底，结构清晰。"
        if instruction.strip():
            prompt += f" 额外要求：{instruction.strip()}。"
        prompt = sanitize_image_prompt(f"{style_header}\n\n{prompt}") if style_header.strip() else prompt
        return {
            "page_no": slide_payload["page_no"],
            "title": slide_payload["title"],
            "slide_role": slide_payload.get("purpose", existing_prompt.get("slide_role", "")),
            "key_blocks": slide_payload.get("key_blocks", existing_prompt.get("key_blocks", [])),
            "image_prompt": prompt,
        }

    model, api_key, base_url = _text_config(config)
    prompt_master_style = {} if style_header.strip() else master_style
    prompt = load_prompt_template("Single Slide Prompt Regeneration Prompt").format(
        requirement_json=json.dumps(build_requirement_summary(job), ensure_ascii=False, indent=2),
        master_style_json=json.dumps(prompt_master_style, ensure_ascii=False, indent=2),
        page_intent_json=json.dumps(page_intent, ensure_ascii=False, indent=2),
        outline_json=json.dumps(outline_payload, ensure_ascii=False, indent=2),
        style_header=style_header,
        slide_json=json.dumps(slide_payload, ensure_ascii=False, indent=2),
        existing_prompt_json=json.dumps(existing_prompt, ensure_ascii=False, indent=2),
        regeneration_instruction=instruction or "保持整体风格一致，仅优化本页表达。",
    )
    payload = complete_json(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        api_key=api_key,
        base_url=base_url,
    )
    if isinstance(payload, dict):
        if style_header.strip():
            image_prompt = str(payload.get("image_prompt", "")).strip()
            payload["image_prompt"] = sanitize_image_prompt(f"{style_header}\n\n{image_prompt}")
        return payload
    raise RuntimeError("Single slide prompt regeneration did not return JSON object")


def rebuild_pptx_if_possible(job: dict[str, Any], output_dir: Path, slide_prompts: dict[str, Any]) -> None:
    image_paths: list[Path] = []
    for slide in slide_prompts.get("slides", []):
        image_path = output_dir / "images" / f"slide_{int(slide['page_no']):02d}.png"
        if not image_path.exists():
            return
        image_paths.append(image_path)
    if not image_paths:
        return
    pptx_name = job.get("output", {}).get("pptx_filename", "deck.pptx")
    assemble_pptx(image_paths, output_dir / pptx_name)


def load_first_slide_reference(
    job: dict[str, Any],
    output_dir: Path,
    *,
    page_no: int,
) -> list[ReferenceImage] | None:
    consistency = job.get("consistency")
    if not isinstance(consistency, dict):
        return None
    if not bool(consistency.get("use_reference_image")):
        return None
    if consistency.get("reference_source") != "first_slide":
        return None
    if page_no <= 1:
        return None

    reference_path = output_dir / "images" / "slide_01.png"
    if not reference_path.exists():
        return None

    return [ReferenceImage(data=reference_path.read_bytes(), mime_type="image/png")]


def resolve_reference_images_for_provider(
    requested_reference_images: list[ReferenceImage] | None,
    provider: Any,
) -> list[ReferenceImage] | None:
    if not requested_reference_images:
        return None
    if not bool(getattr(provider, "supports_reference_images", False)):
        return None
    return requested_reference_images


def resolve_seed_for_provider(
    job: dict[str, Any],
    provider: Any,
) -> int | None:
    consistency = job.get("consistency")
    if not isinstance(consistency, dict):
        return None
    requested_seed = consistency.get("seed")
    if not isinstance(requested_seed, int):
        return None
    if not bool(getattr(provider, "supports_seed", False)):
        return None
    return requested_seed


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.render_only and args.prompt_only:
        parser.error("--render-only and --prompt-only cannot be used together")

    job_path = Path(args.job).expanduser().resolve()
    job = load_json(job_path)
    ensure_huixin_assets(job)
    output_dir = resolve_output_dir(job, args.output_dir, job_path)

    config_path = Path(args.config).expanduser().resolve() if args.config else skill_root() / "assets" / "model_config.yaml"
    config = load_model_config(config_path)

    master_style_path = output_dir / "master_style.json"
    outline_path = output_dir / "outline.json"
    slide_prompts_path = output_dir / "slide_prompts.json"
    if not master_style_path.exists() or not outline_path.exists() or not slide_prompts_path.exists():
        raise FileNotFoundError("master_style.json, outline.json, and slide_prompts.json must exist before single-slide regeneration")

    master_style = load_json(master_style_path)
    outline_payload = load_json(outline_path)
    slide_prompts = load_json(slide_prompts_path)
    page_intent_path = output_dir / "page_intent.json"
    page_intent_payload = load_json(page_intent_path) if page_intent_path.exists() else (job.get("page_intent") or {})
    style_header = build_style_header(master_style, page_intent_payload)

    _, outline_slide = find_slide_by_page_no(outline_payload.get("slides", []), args.page_no)
    prompt_index, existing_prompt = find_slide_by_page_no(slide_prompts.get("slides", []), args.page_no)

    updated_prompt = existing_prompt
    if not args.render_only:
        updated_prompt = regenerate_single_prompt(
            job,
            master_style,
            outline_payload,
            outline_slide,
            existing_prompt,
            args.instruction,
            style_header=style_header,
            page_intent=page_intent_payload,
            dry_run=args.dry_run,
            config=config,
        )
        slide_prompts["slides"][prompt_index] = updated_prompt
        write_json(slide_prompts_path, slide_prompts)
        print(f"[OK] Updated slide prompt: {slide_prompts_path} page {args.page_no}")

    if args.prompt_only:
        return 0

    image_path = output_dir / "images" / f"slide_{args.page_no:02d}.png"
    image_path.parent.mkdir(parents=True, exist_ok=True)
    if args.dry_run:
        from pipeline.stage_render import create_placeholder_image

        create_placeholder_image(outline_slide.get("title", f"第{args.page_no}页"), args.page_no, image_path)
    else:
        from llm.image import ImageRenderRequest, build_image_provider
        from pipeline.stage_render import build_image_render_prompt

        image_provider = build_image_provider(config)
        try:
            requested_reference_images = load_first_slide_reference(job, output_dir, page_no=args.page_no)
            request = ImageRenderRequest(
                prompt=build_image_render_prompt(updated_prompt.get("image_prompt", ""), config.resolution),
                model=config.image.model,
                resolution=config.resolution,
                aspect_ratio=config.aspect_ratio,
                seed=resolve_seed_for_provider(job, image_provider),
                reference_images=resolve_reference_images_for_provider(
                    requested_reference_images,
                    image_provider,
                ),
            )
            image_path.write_bytes(image_provider.render(request))
        finally:
            image_provider.close()

    print(f"[OK] Re-rendered slide image for page {args.page_no}")
    if not args.skip_rebuild_pptx:
        rebuild_pptx_if_possible(job, output_dir, slide_prompts)
        print("[OK] Rebuilt PPTX from current image set")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
