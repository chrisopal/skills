from __future__ import annotations

from json import dumps
from pathlib import Path
from typing import Any

from llm.config import ModelConfig
from llm.image import ImageRenderRequest, build_image_provider
from llm.image.base import ReferenceImage
from llm.image.gemini import GeminiImageProvider
from llm.image.openai import OpenAIImageProvider
from llm.image.openrouter import OpenRouterImageProvider
from PIL import Image, ImageDraw
from style.header import sanitize_image_prompt

from .common import load_prompt_template


RENDER_METADATA_FILENAME = "render_metadata.json"
_REFERENCE_IMAGE_SUPPORT_BY_PROVIDER = {
    "gemini": GeminiImageProvider.supports_reference_images,
    "openai": OpenAIImageProvider.supports_reference_images,
    "openrouter": OpenRouterImageProvider.supports_reference_images,
}
_WRAPPER_REPHRASES = {
    "Treat all style measurements, font sizes, spacing values, radius values, stroke values, and shadow values as invisible design instructions.": (
        "Treat all style measurements, font sizing, layout-rhythm details, corner-rounding details, "
        "line-weight details, and depth-effect details as invisible design instructions."
    ),
    'Never render measurement labels or design annotations such as "40-56px", "20-28px", "56-72px", "Caption: 12-14px", "R=14px", "stroke=1pt", red boxes, rulers, alignment guides, wireframes, or prompt/schema text.': (
        "Never render measurement labels or design annotations such as numeric size labels, "
        "corner-rounding notation, line-weight notation, red boxes, rulers, alignment guides, "
        "wireframes, or prompt/schema text."
    ),
}


def create_placeholder_image(title: str, page_no: int, output_path: Path) -> None:
    image = Image.new("RGB", (1920, 1080), "#FFFFFF")
    draw = ImageDraw.Draw(image)
    draw.rectangle((80, 80, 1840, 1000), outline="#0F95B6", width=8)
    draw.rounded_rectangle((120, 160, 1800, 300), radius=28, fill="#F5F7FA", outline="#E5E7EB")
    draw.text((160, 185), f"{page_no}. {title}", fill="#1E1E1E")
    draw.rounded_rectangle((120, 360, 860, 900), radius=28, fill="#F5F7FA", outline="#A8D86B")
    draw.rounded_rectangle((940, 360, 1800, 900), radius=28, fill="#F5F7FA", outline="#0F95B6")
    image.save(output_path)


def build_image_render_prompt(image_prompt: str, resolution: str) -> str:
    wrapper_prompt = load_prompt_template("Image Rendering Wrapper Prompt")
    for source, target in _WRAPPER_REPHRASES.items():
        wrapper_prompt = wrapper_prompt.replace(source, target)
    return wrapper_prompt.format(
        resolution=resolution,
        image_prompt=sanitize_image_prompt(image_prompt),
    )


def _consistency_config(job: dict[str, Any]) -> dict[str, Any]:
    consistency = job.get("consistency")
    return consistency if isinstance(consistency, dict) else {}


def _use_first_slide_reference(job: dict[str, Any]) -> bool:
    consistency = _consistency_config(job)
    return bool(consistency.get("use_reference_image")) and consistency.get("reference_source") == (
        "first_slide"
    )


def _reference_source(job: dict[str, Any]) -> Any:
    return _consistency_config(job).get("reference_source")


def _seed(job: dict[str, Any]) -> int | None:
    value = _consistency_config(job).get("seed")
    return value if isinstance(value, int) else None


def _provider_supports_reference_images(provider: Any, provider_name: str) -> bool:
    if provider is not None:
        return bool(getattr(provider, "supports_reference_images", False))
    return bool(_REFERENCE_IMAGE_SUPPORT_BY_PROVIDER.get(provider_name.strip().lower(), False))


def _resolve_seed_for_provider(provider: Any, requested_seed: int | None) -> int | None:
    if requested_seed is None:
        return None
    if not bool(getattr(provider, "supports_seed", False)):
        return None
    return requested_seed


def _write_render_metadata(
    output_dir: Path,
    *,
    use_reference_image: bool,
    provider_supports_reference_images: bool,
    reference_source: Any,
    fallback_reason: str | None,
) -> None:
    payload = {
        "use_reference_image": use_reference_image,
        "provider_supports_reference_images": provider_supports_reference_images,
        "reference_source": reference_source,
        "fallback_reason": fallback_reason,
    }
    path = output_dir / RENDER_METADATA_FILENAME
    path.write_text(dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def run_stage(
    job: dict[str, Any],
    config: ModelConfig,
    slide_prompts: dict[str, Any],
    output_dir: Path,
    *,
    dry_run: bool,
) -> list[Path]:
    image_dir = output_dir / "images"
    image_dir.mkdir(parents=True, exist_ok=True)
    image_paths: list[Path] = []
    use_reference = _use_first_slide_reference(job)
    reference_source = _reference_source(job)
    seed = _seed(job)
    first_slide_bytes: bytes | None = None

    provider = None if dry_run else build_image_provider(config, provider_name=config.image.provider)
    provider_supports_reference_images = _provider_supports_reference_images(provider, config.image.provider)
    fallback_reason = None
    if use_reference and not provider_supports_reference_images:
        fallback_reason = "provider_does_not_support_reference_images"
    reference_mode_enabled = use_reference and provider_supports_reference_images
    try:
        for slide in slide_prompts.get("slides", []):
            output_path = image_dir / f"slide_{int(slide['page_no']):02d}.png"
            if dry_run:
                create_placeholder_image(slide.get("title", ""), int(slide["page_no"]), output_path)
            else:
                page_no = int(slide["page_no"])
                reference_images = (
                    [ReferenceImage(data=first_slide_bytes, mime_type="image/png")]
                    if reference_mode_enabled and page_no > 1 and first_slide_bytes
                    else None
                )
                request = ImageRenderRequest(
                    prompt=build_image_render_prompt(slide.get("image_prompt", ""), config.resolution),
                    model=config.image.model,
                    resolution=config.resolution,
                    aspect_ratio=config.aspect_ratio,
                    seed=_resolve_seed_for_provider(provider, seed),
                    reference_images=reference_images,
                )
                rendered = provider.render(request)
                output_path.write_bytes(rendered)
                if page_no == 1:
                    first_slide_bytes = rendered
            image_paths.append(output_path)
    finally:
        if provider is not None:
            provider.close()

    _write_render_metadata(
        output_dir,
        use_reference_image=use_reference,
        provider_supports_reference_images=provider_supports_reference_images,
        reference_source=reference_source,
        fallback_reason=fallback_reason,
    )
    return image_paths
