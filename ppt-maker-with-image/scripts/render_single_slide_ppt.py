#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageDraw

from assemble_pptx import assemble_pptx
from llm.config import load_model_config
from llm.image import ImageRenderRequest, build_image_provider
from pipeline.common import load_asset_json, load_json, skill_root
from pipeline.stage_render import build_image_render_prompt


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate a single-slide image and assemble a one-slide PPTX."
    )
    parser.add_argument("--job", default="", help="Path to single_slide_job.json")
    parser.add_argument("--prompt", default="", help="Single-slide prompt text")
    parser.add_argument("--prompt-file", default="", help="Path to a file containing the single-slide prompt")
    parser.add_argument("--title", default="", help="Slide title used for output naming or placeholder rendering")
    parser.add_argument("--template-id", default="", help="Optional template id such as huixin")
    parser.add_argument("--template-name", default="", help="Optional template name such as 慧新")
    parser.add_argument(
        "--config",
        default=str(skill_root() / "assets" / "model_config.yaml"),
        help="Path to model config yaml",
    )
    parser.add_argument("--output-dir", default="", help="Output directory")
    parser.add_argument("--image-name", default="", help="Output image filename")
    parser.add_argument("--pptx-name", default="", help="Output pptx filename")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Generate a placeholder slide instead of calling a live image model",
    )
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


def resolve_single_slide_output_dir(job: dict, cli_value: str, job_path: str) -> Path:
    raw = cli_value or job.get("output", {}).get("directory", "./single-slide-artifacts")
    path = Path(raw).expanduser()
    if path.is_absolute():
        return path.resolve()
    if job_path:
        return (Path(job_path).expanduser().resolve().parent / path).resolve()
    return path.resolve()


def build_template_prefix(template_id: str, template_name: str) -> str:
    normalized_id = template_id.strip().lower()
    normalized_name = template_name.strip()
    if normalized_id == "huixin" or normalized_name == "慧新":
        prompt_block = load_asset_json("huixin_master_style_brief.json").get("prompt_block", "")
        return f"{prompt_block}\n\n"
    return ""


def create_placeholder_single_slide(title: str, prompt_text: str, image_path: Path) -> None:
    image = Image.new("RGB", (1920, 1080), "#FFFFFF")
    draw = ImageDraw.Draw(image)
    draw.rectangle((60, 60, 1860, 1020), outline="#0F95B6", width=8)
    draw.rounded_rectangle((100, 100, 1820, 260), radius=26, fill="#F5F7FA", outline="#E5E7EB")
    draw.text((140, 145), title, fill="#1E1E1E")
    draw.rounded_rectangle((100, 320, 900, 950), radius=26, fill="#F5F7FA", outline="#A8D86B")
    draw.rounded_rectangle((980, 320, 1820, 950), radius=26, fill="#F5F7FA", outline="#0F95B6")
    preview_text = prompt_text[:120] + ("..." if len(prompt_text) > 120 else "")
    draw.text((140, 360), preview_text, fill="#6B7280")
    image.save(image_path)


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

    config = load_model_config(Path(args.config).expanduser().resolve())
    output_dir = resolve_single_slide_output_dir(job, args.output_dir, args.job)
    output_dir.mkdir(parents=True, exist_ok=True)

    image_path = output_dir / resolve_output_value(job, args.image_name, "image_filename", "single_slide.png")
    pptx_path = output_dir / resolve_output_value(job, args.pptx_name, "pptx_filename", "single_slide.pptx")

    slide_spec = f"{build_template_prefix(template_id, template_name)}{prompt_text}".strip()

    if args.dry_run:
        create_placeholder_single_slide(title, slide_spec, image_path)
    else:
        provider = build_image_provider(config, provider_name=config.image.provider)
        try:
            request = ImageRenderRequest(
                prompt=build_image_render_prompt(slide_spec, config.resolution),
                model=config.image.model,
                resolution=config.resolution,
                aspect_ratio=config.aspect_ratio,
            )
            image_path.write_bytes(provider.render(request))
        finally:
            provider.close()

    assemble_pptx([image_path], pptx_path)
    print(f"[OK] Wrote image: {image_path}")
    print(f"[OK] Wrote PPTX: {pptx_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
