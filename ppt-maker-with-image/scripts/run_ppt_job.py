#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import json
import os
from io import BytesIO
from pathlib import Path
from typing import Any

import httpx
import yaml
from PIL import Image, ImageDraw

from assemble_pptx import assemble_pptx
from validate_job import validate_job_data


TEMPLATE_VARIANT_BUNDLES = {
    "huixin": {
        "aliases": ["慧新"],
        "preset_asset": "huixin_template.json",
        "brief_asset": "huixin_master_style_brief.json",
    },
    "huixin-product-solution": {
        "aliases": ["慧新-产品及解决方案介绍", "慧新产品及解决方案介绍", "产品及解决方案介绍风格"],
        "preset_asset": "huixin_product_solution_template.json",
        "brief_asset": "huixin_product_solution_master_style_brief.json",
    },
    "huixin-market-promo": {
        "aliases": ["慧新-市场宣传", "慧新市场宣传", "市场宣传风格"],
        "preset_asset": "huixin_market_promo_template.json",
        "brief_asset": "huixin_market_promo_master_style_brief.json",
    },
    "huixin-internal-meeting": {
        "aliases": ["慧新-内部会议", "慧新内部会议", "内部会议风格"],
        "preset_asset": "huixin_internal_meeting_template.json",
        "brief_asset": "huixin_internal_meeting_master_style_brief.json",
    },
}


def skill_root() -> Path:
    return Path(__file__).resolve().parents[1]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run a semi-automatic image-first PPT job from job.json to pptx."
    )
    parser.add_argument("job", help="Path to the job.json file")
    parser.add_argument(
        "--config",
        default=str(skill_root() / "assets" / "model_config.yaml"),
        help="Path to model config yaml",
    )
    parser.add_argument(
        "--output-dir",
        default="",
        help="Optional output directory override",
    )
    parser.add_argument(
        "--auto-approve-outline",
        action="store_true",
        help="Continue immediately after generating outline",
    )
    parser.add_argument(
        "--auto-approve-prompts",
        action="store_true",
        help="Continue immediately after generating slide prompts",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Skip live model calls and generate placeholder outputs",
    )
    return parser


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: dict[str, Any] | list[Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def load_yaml(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def load_asset_json(name: str) -> dict[str, Any]:
    return load_json(skill_root() / "assets" / name)


def resolve_template_variant_key(template_id: str | None, template_name: str | None) -> str | None:
    normalized_id = (template_id or "").strip().lower()
    normalized_name = (template_name or "").strip()
    if normalized_id in TEMPLATE_VARIANT_BUNDLES:
        return normalized_id
    for key, bundle in TEMPLATE_VARIANT_BUNDLES.items():
        if normalized_name and normalized_name in bundle["aliases"]:
            return key
    return None


def load_template_variant_bundle(template_id: str | None, template_name: str | None) -> dict[str, Any] | None:
    key = resolve_template_variant_key(template_id, template_name)
    if not key:
        return None
    bundle = TEMPLATE_VARIANT_BUNDLES[key]
    preset = load_asset_json(bundle["preset_asset"])
    brief = load_asset_json(bundle["brief_asset"])
    return {"key": key, "preset": preset, "brief": brief}


def resolve_output_dir(job: dict[str, Any], cli_output_dir: str, job_path: Path) -> Path:
    if cli_output_dir:
        return Path(cli_output_dir).expanduser().resolve()
    output_dir = job.get("output", {}).get("directory")
    if output_dir:
        return (job_path.parent / output_dir).resolve()
    return (job_path.parent / "artifacts").resolve()


def build_openrouter_headers(api_key: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }


def call_text_model(
    client: httpx.Client,
    model: str,
    prompt: str,
    *,
    temperature: float = 0.3,
) -> dict[str, Any]:
    if "json" not in prompt.lower():
        prompt = f"{prompt}\n\nReturn valid JSON only."
    response = client.post(
        "/chat/completions",
        json={
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "response_format": {"type": "json_object"},
        },
    )
    response.raise_for_status()
    content = response.json()["choices"][0]["message"]["content"]
    return json.loads(content)


def call_image_model(
    client: httpx.Client,
    model: str,
    prompt: str,
    resolution: str,
) -> bytes:
    response = client.post(
        "/chat/completions",
        json={
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "modalities": ["image", "text"],
            "temperature": 0.1,
            "image_config": {"aspect_ratio": "16:9", "image_size": "4K"},
        },
    )
    response.raise_for_status()
    message = response.json()["choices"][0]["message"]
    images = message.get("images") or []
    for image in images:
        image_url = image.get("image_url", {}).get("url", "")
        if image_url.startswith("data:"):
            return base64.b64decode(image_url.split(",", 1)[1])
        if image_url.startswith("http"):
            image_response = httpx.get(image_url, timeout=60.0)
            image_response.raise_for_status()
            return image_response.content
    raise ValueError("No image data returned from image model")


def load_prompt_template(name: str) -> str:
    content = (skill_root() / "references" / "prompt-templates.md").read_text(encoding="utf-8")
    anchor = f"## {name}"
    start = content.index(anchor)
    next_idx = content.find("\n## ", start + 1)
    block = content[start: next_idx if next_idx != -1 else len(content)]
    first = block.find("```text")
    last = block.rfind("```")
    if first == -1 or last == -1 or last <= first:
        raise ValueError(f"Prompt template not found: {name}")
    return block[first + len("```text"):last].strip()


def ensure_huixin_assets(job: dict[str, Any]) -> None:
    bundle = load_template_variant_bundle(job.get("template_id"), job.get("template_name"))
    if bundle:
        if not job.get("master_style"):
            job["master_style"] = bundle["brief"]
        if not job.get("style"):
            job["style"] = bundle["preset"]["template_name"]


def build_requirement_summary(job: dict[str, Any]) -> dict[str, Any]:
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


def generate_master_style(
    job: dict[str, Any],
    client: httpx.Client | None,
    config: dict[str, Any],
    *,
    dry_run: bool,
) -> dict[str, Any]:
    if job.get("master_style"):
        return job["master_style"]
    if dry_run:
        return {
            "visual_positioning": "正式、专业、结构化",
            "deck_voice": "理性、克制、信息清晰",
            "color_strategy": {"background": "#FFFFFF"},
            "typography": {"title_font": "Microsoft YaHei", "body_font": "Microsoft YaHei"},
            "title_hierarchy_rules": ["每页一个主标题"],
            "layout_system": {"grid": "12-column"},
            "module_layout_patterns": ["双栏对照", "四卡片矩阵"],
            "chart_rules": ["扁平化 2D 图表"],
            "icon_rules": ["统一线性图标"],
            "forbidden_elements": ["3D图表", "随机角标"],
            "prompt_block": "语言：中文，白底，结构化布局。"
        }
    if client is None:
        raise RuntimeError("OpenRouter client is not configured")
    bundle = load_template_variant_bundle(job.get("template_id"), job.get("template_name"))
    template_preset = bundle["preset"] if bundle else {}
    prompt = load_prompt_template("Master Style Brief Generation Prompt").format(
        requirement_json=json.dumps(build_requirement_summary(job), ensure_ascii=False, indent=2),
        template_preset_json=json.dumps(template_preset, ensure_ascii=False, indent=2),
    )
    return call_text_model(client, config["text_model"], prompt)


def generate_outline(
    job: dict[str, Any],
    master_style: dict[str, Any],
    client: httpx.Client | None,
    config: dict[str, Any],
    *,
    dry_run: bool,
) -> dict[str, Any]:
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
    if client is None:
        raise RuntimeError("OpenRouter client is not configured")
    prompt = load_prompt_template("Outline Generation Prompt").format(
        requirement_json=json.dumps(build_requirement_summary(job), ensure_ascii=False, indent=2),
        page_count=job["page_count"],
    )
    return call_text_model(client, config["text_model"], prompt)


def generate_slide_prompts(
    job: dict[str, Any],
    master_style: dict[str, Any],
    outline_payload: dict[str, Any],
    client: httpx.Client | None,
    config: dict[str, Any],
    *,
    dry_run: bool,
) -> dict[str, Any]:
    if job.get("slides"):
        return {"slides": job["slides"]}
    if dry_run:
        slides = []
        for slide in outline_payload["slides"]:
            slides.append(
                {
                    "page_no": slide["page_no"],
                    "title": slide["title"],
                    "slide_role": slide.get("purpose", ""),
                    "key_blocks": slide.get("key_blocks", []),
                    "image_prompt": f"中文PPT页面，标题为《{slide['title']}》，白底，结构清晰，包含{','.join(slide.get('key_blocks', []))}。",
                }
            )
        return {"slides": slides}
    if client is None:
        raise RuntimeError("OpenRouter client is not configured")
    prompt = load_prompt_template("Per-Slide Prompt Generation Prompt").format(
        requirement_json=json.dumps(build_requirement_summary(job), ensure_ascii=False, indent=2),
        master_style_json=json.dumps(master_style, ensure_ascii=False, indent=2),
        outline_json=json.dumps(outline_payload, ensure_ascii=False, indent=2),
    )
    return call_text_model(client, config["text_model"], prompt)


def create_placeholder_image(title: str, page_no: int, output_path: Path) -> None:
    image = Image.new("RGB", (1920, 1080), "#FFFFFF")
    draw = ImageDraw.Draw(image)
    draw.rectangle((80, 80, 1840, 1000), outline="#0F95B6", width=8)
    draw.rounded_rectangle((120, 160, 1800, 300), radius=28, fill="#F5F7FA", outline="#E5E7EB")
    draw.text((160, 185), f"{page_no}. {title}", fill="#1E1E1E")
    draw.rounded_rectangle((120, 360, 860, 900), radius=28, fill="#F5F7FA", outline="#A8D86B")
    draw.rounded_rectangle((940, 360, 1800, 900), radius=28, fill="#F5F7FA", outline="#0F95B6")
    image.save(output_path)


def render_images(
    slide_prompts: dict[str, Any],
    client: httpx.Client | None,
    config: dict[str, Any],
    output_dir: Path,
    *,
    dry_run: bool,
) -> list[Path]:
    image_dir = output_dir / "images"
    image_dir.mkdir(parents=True, exist_ok=True)
    image_paths: list[Path] = []
    for slide in slide_prompts["slides"]:
        output_path = image_dir / f"slide_{int(slide['page_no']):02d}.png"
        if dry_run:
            create_placeholder_image(slide["title"], int(slide["page_no"]), output_path)
        else:
            if client is None:
                raise RuntimeError("OpenRouter client is not configured")
            prompt = load_prompt_template("Image Rendering Wrapper Prompt").format(
                resolution=config.get("resolution", "3840x2160"),
                image_prompt=slide["image_prompt"],
            )
            image_bytes = call_image_model(client, config["image_model"], prompt, config.get("resolution", "3840x2160"))
            output_path.write_bytes(image_bytes)
        image_paths.append(output_path)
    return image_paths


def persist_stage(output_dir: Path, name: str, data: dict[str, Any]) -> Path:
    path = output_dir / name
    write_json(path, data)
    return path


def openrouter_client(config: dict[str, Any]) -> httpx.Client | None:
    api_key = os.getenv("OPENROUTER_API_KEY", "").strip()
    if not api_key:
        return None
    base_url = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
    return httpx.Client(
        base_url=base_url,
        headers=build_openrouter_headers(api_key),
        timeout=httpx.Timeout(180.0, connect=20.0),
    )


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    job_path = Path(args.job).expanduser().resolve()
    job = load_json(job_path)
    config = load_yaml(Path(args.config).expanduser().resolve())

    missing = validate_job_data(job)
    if missing:
        print("[ERROR] job.json 缺少必要字段：")
        for item in missing:
            print(f"- {item}")
        return 1

    ensure_huixin_assets(job)
    output_dir = resolve_output_dir(job, args.output_dir, job_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    client = None if args.dry_run else openrouter_client(config)

    try:
        master_style = generate_master_style(job, client, config, dry_run=args.dry_run)
        persist_stage(output_dir, "master_style.json", master_style)

        outline_payload = generate_outline(job, master_style, client, config, dry_run=args.dry_run)
        persist_stage(output_dir, "outline.json", outline_payload)
        if not (args.auto_approve_outline or job.get("outline_approved")):
            print(f"[STOP] 已生成大纲：{output_dir / 'outline.json'}")
            print("请确认并修改后，将 job.json 中的 outline_approved 设为 true，或使用 --auto-approve-outline 继续。")
            return 0

        slide_prompts = generate_slide_prompts(job, master_style, outline_payload, client, config, dry_run=args.dry_run)
        persist_stage(output_dir, "slide_prompts.json", slide_prompts)
        if not (args.auto_approve_prompts or job.get("prompts_approved")):
            print(f"[STOP] 已生成逐页提示词：{output_dir / 'slide_prompts.json'}")
            print("请确认并修改后，将 job.json 中的 prompts_approved 设为 true，或使用 --auto-approve-prompts 继续。")
            return 0

        image_paths = render_images(slide_prompts, client, config, output_dir, dry_run=args.dry_run)
        pptx_name = job.get("output", {}).get("pptx_filename", "deck.pptx")
        pptx_path = output_dir / pptx_name
        assemble_pptx(image_paths, pptx_path)
        print(f"[OK] PPTX 已生成：{pptx_path}")
        return 0
    finally:
        if client is not None:
            client.close()


if __name__ == "__main__":
    raise SystemExit(main())
