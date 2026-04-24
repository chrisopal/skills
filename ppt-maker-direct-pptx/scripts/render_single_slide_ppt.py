#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from assemble_pptx import assemble_from_specs
from run_ppt_job import (
    build_js_generator,
    build_single_slide_compiled_prompt,
    generate_master_style,
    load_json,
    load_template_variant_bundle,
    load_yaml,
    openrouter_client,
    write_json,
)
from ppt_renderer import build_slide_specs


def skill_root() -> Path:
    return Path(__file__).resolve().parents[1]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate a single-slide editable PPTX directly from one prompt."
    )
    parser.add_argument("--job", default="", help="Path to single_slide_job.json")
    parser.add_argument("--prompt", default="", help="Single-slide prompt text")
    parser.add_argument("--prompt-file", default="", help="Path to a file containing the single-slide prompt")
    parser.add_argument("--title", default="", help="Slide title used for output naming and rendering")
    parser.add_argument("--template-id", default="", help="Optional template id such as huixin")
    parser.add_argument("--template-name", default="", help="Optional template name such as 慧新")
    parser.add_argument(
        "--config",
        default=str(skill_root() / "assets" / "model_config.yaml"),
        help="Path to model config yaml",
    )
    parser.add_argument("--output-dir", default="", help="Output directory")
    parser.add_argument("--spec-name", default="", help="Output slide spec filename")
    parser.add_argument("--pptx-name", default="", help="Output pptx filename")
    parser.add_argument("--dry-run", action="store_true", help="Use deterministic placeholder intent instead of live model calls")
    return parser


def read_prompt_text(args: argparse.Namespace) -> str:
    if args.prompt_file:
        return Path(args.prompt_file).expanduser().resolve().read_text(encoding="utf-8").strip()
    return args.prompt.strip()


def load_job_payload(job_path: str) -> dict:
    if not job_path:
        return {}
    return load_json(Path(job_path).expanduser().resolve())


def resolve_value(job: dict, cli_value, key: str, default=None):
    if cli_value not in ("", None):
        return cli_value
    return job.get(key, default)


def resolve_output_value(job: dict, cli_value, key: str, default: str) -> str:
    if cli_value not in ("", None):
        return cli_value
    return job.get("output", {}).get(key, default)


def resolve_output_dir(job: dict, cli_value: str, job_path: str) -> Path:
    raw = cli_value or job.get("output", {}).get("directory", "./single-slide-artifacts")
    path = Path(raw).expanduser()
    if path.is_absolute():
        return path.resolve()
    if job_path:
        return (Path(job_path).expanduser().resolve().parent / path).resolve()
    return path.resolve()


def build_single_slide_intent(title: str, prompt_text: str, compiled_prompt: str) -> dict:
    layout_type = "content"
    lowered = prompt_text.lower()
    if any(word in lowered for word in ["架构", "蓝图", "分层", "平台", "layer", "blueprint"]):
        layout_type = "architecture"
    elif any(word in lowered for word in ["路线", "里程碑", "阶段", "roadmap", "计划"]):
        layout_type = "roadmap"
    elif any(word in lowered for word in ["对比", "双栏", "两栏", "left", "right"]):
        layout_type = "two-column"
    image_placeholders = []
    if any(word in prompt_text for word in ["图片", "配图", "照片", "场景图", "产品图", "示意图", "渲染图"]):
        image_placeholders.append(
            {
                "id": "p1_img1",
                "role": "supporting_visual",
                "purpose": "支撑单页主题的核心视觉",
                "prompt": prompt_text,
                "placement": {"x": 8.35, "y": 1.75, "w": 3.75, "h": 2.45},
                "required": False,
            }
        )

    return {
        "page_no": 1,
        "title": title,
        "subtitle": "",
        "page_goal": "根据单页输入直接绘制为可编辑PPT页面",
        "layout_type": layout_type,
        "key_blocks": [prompt_text],
        "image_placeholders": image_placeholders,
        "visual_focus": "保持整体风格一致，模块化表达",
        "detail_notes": "",
        "compiled_prompt": compiled_prompt,
    }


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    job = load_job_payload(args.job)
    prompt_text = read_prompt_text(args) or str(job.get("prompt", "")).strip()
    if not prompt_text:
        parser.error("Provide --prompt, --prompt-file, or --job")

    title = resolve_value(job, args.title, "title", "单页PPT")
    template_id = resolve_value(job, args.template_id, "template_id", "")
    template_name = resolve_value(job, args.template_name, "template_name", "")
    output_dir = resolve_output_dir(job, args.output_dir, args.job)
    output_dir.mkdir(parents=True, exist_ok=True)
    spec_path = output_dir / resolve_output_value(job, args.spec_name, "slide_spec_filename", "single_slide_spec.json")
    pptx_path = output_dir / resolve_output_value(job, args.pptx_name, "pptx_filename", "single_slide.pptx")
    config = load_yaml(Path(args.config).expanduser().resolve())

    bundle = load_template_variant_bundle(template_id, template_name)
    compiled_prompt = build_single_slide_compiled_prompt(title, prompt_text, bundle)
    client = None if args.dry_run else openrouter_client(config)

    try:
        if bundle is not None:
            master_style = bundle["brief"]
        elif args.dry_run:
            master_style = {
                "visual_positioning": "正式、专业、结构化",
                "deck_voice": "理性、克制、信息清晰",
                "color_strategy": {"background": "#FFFFFF", "section_background": "#F5F7FA", "secondary_teal": "#0F95B6", "primary_green": "#A8D86B", "text_primary": "#1E1E1E", "text_secondary": "#6B7280", "divider": "#E5E7EB"},
                "typography": {"title_font": "Microsoft YaHei", "body_font": "Microsoft YaHei"},
            }
        else:
            if client is None:
                raise RuntimeError("OpenRouter client is not configured")
            job_stub = {
                "topic": title,
                "target_audience": "单页模式",
                "purpose": "单页可编辑PPT直出",
                "style": template_name or template_id or "direct-ppt",
                "page_count": 1,
            }
            master_style = generate_master_style(job_stub, client, config, bundle, dry_run=False)
        js_generator = build_js_generator(client, config, dry_run=args.dry_run)

        slide_specs = build_slide_specs(
            {"template_name": bundle["preset"]["template_name"] if bundle else (template_name or template_id or "direct-ppt")},
            master_style,
            {"slides": [build_single_slide_intent(title, prompt_text, compiled_prompt)]},
        )
        write_json(spec_path, slide_specs)
        temp_master_style = output_dir / "single_slide_master_style.json"
        write_json(temp_master_style, master_style)
        assemble_from_specs(spec_path, temp_master_style, pptx_path, js_generator=js_generator)
    finally:
        if client is not None:
            client.close()
    print(f"[OK] Wrote slide spec: {spec_path}")
    print(f"[OK] Wrote PPTX: {pptx_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
