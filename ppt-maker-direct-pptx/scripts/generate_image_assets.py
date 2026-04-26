#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import json
import os
import re
from pathlib import Path
from typing import Any

import httpx
import yaml
from PIL import Image, ImageDraw, ImageFont


def skill_root() -> Path:
    return Path(__file__).resolve().parents[1]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate local image assets for slide image placeholders.")
    parser.add_argument("--slide-specs", required=True, help="Path to slide_specs.json")
    parser.add_argument("--master-style", required=True, help="Path to master_style.json")
    parser.add_argument(
        "--config",
        default=str(skill_root() / "assets" / "model_config.yaml"),
        help="Path to model config yaml",
    )
    parser.add_argument("--output-dir", default="", help="Directory for generated image assets")
    parser.add_argument("--manifest", default="", help="Optional image_manifest.json output path")
    parser.add_argument("--dry-run", action="store_true", help="Generate local placeholder PNGs without calling a model")
    parser.add_argument("--skip-update-slide-specs", action="store_true", help="Do not write image_assets back to slide_specs.json")
    parser.add_argument(
        "--respect-status",
        action="store_true",
        help="Process only placeholders with status in {pending, regenerating}; "
             "set status=generated on success and status=placeholder + fallback_reason on failure.",
    )
    parser.add_argument(
        "--ids",
        default="",
        help="Comma-separated list of placeholder ids to process (overrides status filter).",
    )
    return parser


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: dict[str, Any] | list[Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def load_yaml(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def clean_filename(value: str) -> str:
    value = re.sub(r"[^a-zA-Z0-9_-]+", "_", value).strip("_")
    return value or "image"


ACTIONABLE_STATUSES = {"pending", "regenerating"}


def collect_placeholders(
    slide_specs: dict[str, Any],
    *,
    respect_status: bool = False,
    target_ids: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Collect placeholders to process.

    Legacy behavior (respect_status=False, target_ids=None): every placeholder
    with a non-empty prompt is queued for generation, matching the
    pre-state-machine flow that the existing tests depend on.

    State-machine behavior (respect_status=True): only placeholders whose
    `status` is missing or in {pending, regenerating} are queued. When
    target_ids is provided, only matching ids are processed regardless of
    status (so users can force a regeneration of an already-generated
    placeholder).
    """

    target_set = set(target_ids or [])
    placeholders: list[dict[str, Any]] = []
    for slide in slide_specs.get("slides", []):
        page_no = int(slide.get("page_no") or len(placeholders) + 1)
        for idx, item in enumerate(slide.get("image_placeholders", []), start=1):
            prompt = str(item.get("prompt") or item.get("purpose") or "").strip()
            if not prompt:
                continue
            placeholder_id = str(item.get("id") or f"p{page_no}_img{idx}").strip()
            status = item.get("status")
            if target_set:
                if placeholder_id not in target_set:
                    continue
            elif respect_status:
                if status is not None and status not in ACTIONABLE_STATUSES:
                    continue
            placeholders.append(
                {
                    "page_no": page_no,
                    "placeholder_id": placeholder_id,
                    "role": item.get("role", "supporting_visual"),
                    "purpose": item.get("purpose", prompt),
                    "prompt": prompt,
                    "placement": item.get("placement") if isinstance(item.get("placement"), dict) else {},
                    "_source_item": item,
                }
            )
    return placeholders


def prompt_for_image(master_style: dict[str, Any], placeholder: dict[str, Any]) -> str:
    colors = master_style.get("color_strategy", {})
    return f"""Generate a clean business presentation visual asset, not a full slide.

Language context: Chinese business presentation.
Asset role: {placeholder.get('role')}
Asset purpose: {placeholder.get('purpose')}
Visual request: {placeholder.get('prompt')}

Style constraints:
- white or transparent-feeling business visual
- primary teal/blue: {colors.get('secondary_teal') or colors.get('primary_blue') or '#0F95B6'}
- accent green: {colors.get('primary_green') or colors.get('accent_green') or '#A8D86B'}
- neutral gray: {colors.get('neutral_gray') or '#D9D9D9'}
- flat 2D, enterprise consulting style
- no text-heavy poster, no random labels, no watermark
"""


def draw_placeholder_png(path: Path, placeholder: dict[str, Any], master_style: dict[str, Any]) -> None:
    colors = master_style.get("color_strategy", {})
    bg = (245, 247, 250)
    teal = colors.get("secondary_teal") or colors.get("primary_blue") or "#0F95B6"
    green = colors.get("primary_green") or colors.get("accent_green") or "#A8D86B"
    img = Image.new("RGB", (1280, 720), bg)
    draw = ImageDraw.Draw(img)
    teal_rgb = tuple(int(teal.replace("#", "")[i : i + 2], 16) for i in (0, 2, 4))
    green_rgb = tuple(int(green.replace("#", "")[i : i + 2], 16) for i in (0, 2, 4))
    draw.rounded_rectangle((70, 70, 1210, 650), radius=36, outline=teal_rgb, width=8, fill=(255, 255, 255))
    draw.polygon([(150, 160), (470, 160), (400, 260), (80, 260)], fill=teal_rgb)
    draw.polygon([(880, 470), (1180, 470), (1110, 570), (810, 570)], fill=green_rgb)
    title = str(placeholder.get("purpose") or "Image Placeholder")[:34]
    try:
        font = ImageFont.truetype("/System/Library/Fonts/PingFang.ttc", 42)
        small = ImageFont.truetype("/System/Library/Fonts/PingFang.ttc", 26)
    except OSError:
        font = ImageFont.load_default()
        small = ImageFont.load_default()
    draw.text((140, 330), title, fill=(30, 30, 30), font=font)
    draw.text((140, 392), "Generated image placeholder", fill=(107, 114, 128), font=small)
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path)


def openrouter_headers(api_key: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}


def decode_data_uri(data_uri: str) -> bytes:
    marker = ";base64,"
    if marker not in data_uri:
        raise ValueError("Unsupported data URI format")
    return base64.b64decode(data_uri.split(marker, 1)[1])


def extract_image_url(payload: dict[str, Any]) -> str:
    message = payload["choices"][0]["message"]
    images = message.get("images") or []
    for image in images:
        if isinstance(image, dict):
            image_url = image.get("image_url") or {}
            if isinstance(image_url, dict) and image_url.get("url"):
                return image_url["url"]
            if image.get("url"):
                return image["url"]
    content = message.get("content", "")
    if isinstance(content, str):
        match = re.search(r"data:image/[^\\s)]+", content)
        if match:
            return match.group(0)
    raise ValueError("No image URL found in model response")


def _detect_image_route(base_url: str, config: dict[str, Any]) -> str:
    """Pick the image-generation API route. Explicit `image_route` in config
    wins; otherwise infer from base_url (OpenAI/Azure → /v1/images/generations,
    everything else → /chat/completions with image-in-message)."""

    explicit = (config.get("image_route") or "").strip().lower()
    if explicit in {"images_api", "chat"}:
        return explicit
    haystack = (base_url or "").lower()
    if "openrouter.ai" in haystack:
        return "chat"
    if "openai.com" in haystack or "azure" in haystack:
        return "images_api"
    return "chat"


def _generate_via_chat(client: httpx.Client, model: str, prompt: str, path: Path) -> None:
    response = client.post(
        "/chat/completions",
        json={
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2,
        },
    )
    response.raise_for_status()
    image_url = extract_image_url(response.json())
    path.parent.mkdir(parents=True, exist_ok=True)
    if image_url.startswith("data:image/"):
        path.write_bytes(decode_data_uri(image_url))
    else:
        image_response = httpx.get(image_url, timeout=120.0)
        image_response.raise_for_status()
        path.write_bytes(image_response.content)


def _generate_via_images_api(client: httpx.Client, model: str, prompt: str, path: Path, *, size: str) -> None:
    response = client.post(
        "/images/generations",
        json={
            "model": model,
            "prompt": prompt,
            "size": size,
            "n": 1,
            "response_format": "b64_json",
        },
    )
    response.raise_for_status()
    payload = response.json()
    data = (payload.get("data") or [{}])[0]
    path.parent.mkdir(parents=True, exist_ok=True)
    if data.get("b64_json"):
        path.write_bytes(base64.b64decode(data["b64_json"]))
    elif data.get("url"):
        image_response = httpx.get(data["url"], timeout=120.0)
        image_response.raise_for_status()
        path.write_bytes(image_response.content)
    else:
        raise ValueError("No image data in /images/generations response")


def generate_model_image(path: Path, prompt: str, config: dict[str, Any]) -> None:
    api_key = (os.getenv("LLM_API_KEY") or os.getenv("OPENROUTER_API_KEY") or "").strip()
    if not api_key:
        raise RuntimeError(
            "LLM API key is required for live image generation. "
            "Set LLM_API_KEY (or legacy OPENROUTER_API_KEY)."
        )
    base_url = (
        os.getenv("LLM_BASE_URL")
        or os.getenv("OPENROUTER_BASE_URL")
        or (config.get("base_url") if isinstance(config, dict) else None)
        or ""
    ).strip()
    if not base_url:
        raise RuntimeError(
            "LLM base URL is required. Set LLM_BASE_URL (or legacy OPENROUTER_BASE_URL), "
            "or add `base_url` to model_config.yaml."
        )
    model = config.get("image_model") or config.get("pptx_image_model")
    if not model:
        raise RuntimeError("Configure image_model or pptx_image_model in model_config.yaml")
    route = _detect_image_route(base_url, config)
    size = config.get("image_size", "1024x1024")
    with httpx.Client(base_url=base_url, headers=openrouter_headers(api_key), timeout=httpx.Timeout(180.0, connect=20.0)) as client:
        if route == "images_api":
            _generate_via_images_api(client, model, prompt, path, size=size)
        else:
            _generate_via_chat(client, model, prompt, path)


def apply_manifest_to_specs(slide_specs: dict[str, Any], assets: list[dict[str, Any]]) -> dict[str, Any]:
    by_page: dict[int, list[dict[str, Any]]] = {}
    for asset in assets:
        by_page.setdefault(int(asset["page_no"]), []).append(asset)
    for slide in slide_specs.get("slides", []):
        page_no = int(slide.get("page_no") or 0)
        page_assets = [
            {
                "placeholder_id": asset["placeholder_id"],
                "path": asset["path"],
                "caption": asset.get("purpose", ""),
                "placement": asset.get("placement", {}),
                "fallback_reason": asset.get("fallback_reason", ""),
            }
            for asset in by_page.get(page_no, [])
        ]
        slide["image_assets"] = page_assets
        slide.setdefault("visible_content", {})["image_assets"] = page_assets
    return slide_specs


def generate_assets_for_specs(
    slide_specs: dict[str, Any],
    master_style: dict[str, Any],
    config: dict[str, Any],
    output_dir: Path,
    *,
    dry_run: bool,
    respect_status: bool = False,
    target_ids: list[str] | None = None,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    output_dir.mkdir(parents=True, exist_ok=True)
    assets: list[dict[str, Any]] = []
    for placeholder in collect_placeholders(
        slide_specs, respect_status=respect_status, target_ids=target_ids,
    ):
        filename = f"slide_{placeholder['page_no']:02d}_{clean_filename(placeholder['placeholder_id'])}.png"
        image_path = output_dir / filename
        fallback_reason = ""
        if dry_run:
            draw_placeholder_png(image_path, placeholder, master_style)
        else:
            try:
                generate_model_image(image_path, prompt_for_image(master_style, placeholder), config)
            except Exception as exc:  # noqa: BLE001 - image providers can fail with provider-specific exceptions.
                fallback_reason = str(exc)
                print(
                    f"[WARN] Image generation failed for slide {placeholder['page_no']} "
                    f"{placeholder['placeholder_id']}: {fallback_reason}"
                )
                print("[WARN] Falling back to local dry-run placeholder PNG for this image.")
                draw_placeholder_png(image_path, placeholder, master_style)
        # Mutate the original placeholder dict in slide_specs so status flips persist.
        source_item = placeholder.pop("_source_item", None)
        if respect_status and isinstance(source_item, dict):
            if fallback_reason:
                source_item["status"] = "placeholder"
                source_item["fallback_reason"] = fallback_reason
            elif not dry_run:
                source_item["status"] = "generated"
                source_item["generated_path"] = str(image_path)
                source_item.pop("fallback_reason", None)
            else:
                source_item["status"] = "placeholder"
        asset = {**placeholder, "path": str(image_path)}
        if fallback_reason:
            asset["fallback_reason"] = fallback_reason
        assets.append(asset)
    return apply_manifest_to_specs(slide_specs, assets), assets


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    slide_specs_path = Path(args.slide_specs).expanduser().resolve()
    master_style_path = Path(args.master_style).expanduser().resolve()
    config_path = Path(args.config).expanduser().resolve()
    slide_specs = load_json(slide_specs_path)
    master_style = load_json(master_style_path)
    config = load_yaml(config_path)
    output_dir = Path(args.output_dir).expanduser().resolve() if args.output_dir else slide_specs_path.parent / "generated-images"
    manifest_path = Path(args.manifest).expanduser().resolve() if args.manifest else slide_specs_path.parent / "image_manifest.json"

    target_ids = [s.strip() for s in args.ids.split(",") if s.strip()] if args.ids else None
    updated_specs, assets = generate_assets_for_specs(
        slide_specs,
        master_style,
        config,
        output_dir,
        dry_run=args.dry_run,
        respect_status=args.respect_status or bool(target_ids),
        target_ids=target_ids,
    )
    write_json(manifest_path, {"assets": assets})
    if not args.skip_update_slide_specs:
        write_json(slide_specs_path, updated_specs)
    print(f"[OK] Generated {len(assets)} image asset(s): {output_dir}")
    print(f"[OK] Wrote image manifest: {manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
