#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from assemble_pptx import assemble_pptx
from run_ppt_job import (
    build_requirement_summary,
    call_text_model,
    ensure_huixin_assets,
    load_json,
    load_prompt_template,
    load_yaml,
    openrouter_client,
    render_images,
    resolve_output_dir,
    write_json,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Regenerate one slide prompt or image while preserving deck-level consistency."
    )
    parser.add_argument("job", help="Path to job.json")
    parser.add_argument("--page-no", type=int, required=True, help="1-based slide number")
    parser.add_argument(
        "--instruction",
        default="",
        help="Optional extra instruction for this single-slide regeneration",
    )
    parser.add_argument(
        "--config",
        default="",
        help="Optional model config yaml override",
    )
    parser.add_argument(
        "--output-dir",
        default="",
        help="Optional artifacts directory override",
    )
    parser.add_argument(
        "--render-only",
        action="store_true",
        help="Skip prompt regeneration and only rerender the slide image from existing prompt",
    )
    parser.add_argument(
        "--prompt-only",
        action="store_true",
        help="Only regenerate the prompt and do not rerender the image",
    )
    parser.add_argument(
        "--skip-rebuild-pptx",
        action="store_true",
        help="Do not rebuild the full pptx after rerendering the slide",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Use placeholder prompt/image generation instead of live model calls",
    )
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
    dry_run: bool,
    text_model: str,
) -> dict[str, Any]:
    if dry_run:
        prompt = existing_prompt.get("image_prompt") or ""
        prompt = prompt.strip() or f"中文PPT页面，标题为《{slide_payload['title']}》，白底，结构清晰。"
        if instruction.strip():
            prompt += f" 额外要求：{instruction.strip()}。"
        return {
            "page_no": slide_payload["page_no"],
            "title": slide_payload["title"],
            "slide_role": slide_payload.get("purpose", existing_prompt.get("slide_role", "")),
            "key_blocks": slide_payload.get("key_blocks", existing_prompt.get("key_blocks", [])),
            "image_prompt": prompt,
        }

    client = openrouter_client({"text_model": text_model})
    if client is None:
        raise RuntimeError("OpenRouter client is not configured")
    try:
        prompt = load_prompt_template("Single Slide Prompt Regeneration Prompt").format(
            requirement_json=json.dumps(build_requirement_summary(job), ensure_ascii=False, indent=2),
            master_style_json=json.dumps(master_style, ensure_ascii=False, indent=2),
            outline_json=json.dumps(outline_payload, ensure_ascii=False, indent=2),
            slide_json=json.dumps(slide_payload, ensure_ascii=False, indent=2),
            existing_prompt_json=json.dumps(existing_prompt, ensure_ascii=False, indent=2),
            regeneration_instruction=instruction or "保持整体风格一致，仅优化本页表达。",
        )
        return call_text_model(client, text_model, prompt)
    finally:
        client.close()


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


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.render_only and args.prompt_only:
        parser.error("--render-only and --prompt-only cannot be used together")

    job_path = Path(args.job).expanduser().resolve()
    job = load_json(job_path)
    ensure_huixin_assets(job)
    output_dir = resolve_output_dir(job, args.output_dir, job_path)

    config_path = Path(args.config).expanduser().resolve() if args.config else Path(__file__).resolve().parents[1] / "assets" / "model_config.yaml"
    config = load_yaml(config_path)

    master_style_path = output_dir / "master_style.json"
    outline_path = output_dir / "outline.json"
    slide_prompts_path = output_dir / "slide_prompts.json"

    if not master_style_path.exists() or not outline_path.exists() or not slide_prompts_path.exists():
        raise FileNotFoundError("master_style.json, outline.json, and slide_prompts.json must exist before single-slide regeneration")

    master_style = load_json(master_style_path)
    outline_payload = load_json(outline_path)
    slide_prompts = load_json(slide_prompts_path)

    outline_index, outline_slide = find_slide_by_page_no(outline_payload.get("slides", []), args.page_no)
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
            dry_run=args.dry_run,
            text_model=config["text_model"],
        )
        slide_prompts["slides"][prompt_index] = updated_prompt
        write_json(slide_prompts_path, slide_prompts)
        print(f"[OK] Updated slide prompt: {slide_prompts_path} page {args.page_no}")

    if args.prompt_only:
        return 0

    client = None if args.dry_run else openrouter_client(config)
    try:
        single_payload = {"slides": [updated_prompt]}
        render_images(single_payload, client, config, output_dir, dry_run=args.dry_run)
    finally:
        if client is not None:
            client.close()

    print(f"[OK] Re-rendered slide image for page {args.page_no}")
    if not args.skip_rebuild_pptx:
        rebuild_pptx_if_possible(job, output_dir, slide_prompts)
        print("[OK] Rebuilt PPTX from current image set")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
