#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from run_ppt_job import (
    build_js_generator,
    compile_slide_prompt,
    load_json,
    load_yaml,
    normalize_selected_template,
    openrouter_client,
    resolve_output_dir,
    skill_root,
    validate_runtime_config,
    write_json,
)
from ppt_renderer import build_slide_specs, render_ppt_from_specs


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Regenerate one slide render brief and redraw the PPTX while preserving deck-level consistency."
    )
    parser.add_argument("job", help="Path to job.json")
    parser.add_argument("--page-no", type=int, required=True, help="1-based slide number")
    parser.add_argument("--instruction", default="", help="Optional extra instruction for this single-slide regeneration")
    parser.add_argument("--output-dir", default="", help="Optional artifacts directory override")
    parser.add_argument(
        "--config",
        default=str(skill_root() / "assets" / "model_config.yaml"),
        help="Path to model config yaml",
    )
    parser.add_argument("--dry-run", action="store_true", help="Use deterministic fallback JS instead of live model calls")
    parser.add_argument("--prompt-only", action="store_true", help="Only regenerate the prompt and do not rerender the deck")
    return parser


def find_slide_by_page_no(slides: list[dict[str, Any]], page_no: int) -> tuple[int, dict[str, Any]]:
    for index, slide in enumerate(slides):
        if int(slide.get("page_no", index + 1)) == page_no:
            return index, slide
    raise ValueError(f"Slide with page_no={page_no} not found")


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    job_path = Path(args.job).expanduser().resolve()
    job = load_json(job_path)
    normalize_selected_template(job)
    output_dir = resolve_output_dir(job, args.output_dir, job_path)

    master_style_path = output_dir / "master_style.json"
    slide_prompts_path = output_dir / "slide_prompts.json"
    if not master_style_path.exists() or not slide_prompts_path.exists():
        raise FileNotFoundError("master_style.json and slide_prompts.json must exist before single-slide regeneration")

    master_style = load_json(master_style_path)
    slide_prompts = load_json(slide_prompts_path)

    prompt_index, slide = find_slide_by_page_no(slide_prompts.get("slides", []), args.page_no)
    slide["compiled_prompt"] = compile_slide_prompt(job, master_style, slide, additional_instruction=args.instruction)
    # Regenerated content needs explicit user re-confirmation; flip intent_status
    # back to pending_review unless the slide is still in draft.
    current_intent_status = slide.get("intent_status", "draft")
    if current_intent_status not in ("draft",):
        slide["intent_status"] = "pending_review"
    slide_prompts["slides"][prompt_index] = slide
    write_json(slide_prompts_path, slide_prompts)
    print(f"[OK] Updated slide prompt: {slide_prompts_path} page {args.page_no}")

    if args.prompt_only:
        return 0

    config = load_yaml(Path(args.config).expanduser().resolve())
    runtime_issues = validate_runtime_config(config, require_live_models=not args.dry_run)
    if runtime_issues:
        print("[ERROR] Runtime preflight failed:")
        for issue in runtime_issues:
            print(f"- {issue}")
        return 1
    client = None if args.dry_run else openrouter_client(config)
    try:
        js_generator = build_js_generator(client, config, dry_run=args.dry_run)
        slide_specs = build_slide_specs(job, master_style, slide_prompts)
        slide_specs_path = output_dir / "slide_specs.json"
        write_json(slide_specs_path, slide_specs)
        pptx_name = job.get("output", {}).get("pptx_filename", "deck.pptx")
        render_ppt_from_specs(
            slide_specs,
            master_style,
            output_dir / pptx_name,
            js_generator=js_generator,
            only_pages={args.page_no},
        )
    finally:
        if client is not None:
            client.close()
    print("[OK] Rebuilt PPTX from current slide specs")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
