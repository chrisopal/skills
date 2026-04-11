#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from assemble_pptx import assemble_pptx
from run_ppt_job import (
    compile_slide_prompt,
    load_json,
    load_yaml,
    normalize_selected_template,
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
    parser.add_argument("--instruction", default="", help="Optional extra instruction for this single-slide regeneration")
    parser.add_argument("--config", default="", help="Optional model config yaml override")
    parser.add_argument("--output-dir", default="", help="Optional artifacts directory override")
    parser.add_argument("--render-only", action="store_true", help="Skip prompt regeneration and only rerender the slide image from existing prompt")
    parser.add_argument("--prompt-only", action="store_true", help="Only regenerate the prompt and do not rerender the image")
    parser.add_argument("--skip-rebuild-pptx", action="store_true", help="Do not rebuild the full pptx after rerendering the slide")
    parser.add_argument("--dry-run", action="store_true", help="Use placeholder prompt/image generation instead of live model calls")
    return parser


def find_slide_by_page_no(slides: list[dict[str, Any]], page_no: int) -> tuple[int, dict[str, Any]]:
    for index, slide in enumerate(slides):
        if int(slide.get("page_no", index + 1)) == page_no:
            return index, slide
    raise ValueError(f"Slide with page_no={page_no} not found")


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
    normalize_selected_template(job)
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

    prompt_index, slide = find_slide_by_page_no(slide_prompts.get("slides", []), args.page_no)
    if not args.render_only:
        slide["compiled_prompt"] = compile_slide_prompt(
            job,
            master_style,
            slide,
            additional_instruction=args.instruction,
        )
        slide_prompts["slides"][prompt_index] = slide
        write_json(slide_prompts_path, slide_prompts)
        print(f"[OK] Updated slide prompt: {slide_prompts_path} page {args.page_no}")

    if args.prompt_only:
        return 0

    client = None if args.dry_run else openrouter_client(config)
    try:
        render_images({"slides": [slide]}, client, config, output_dir, dry_run=args.dry_run)
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
