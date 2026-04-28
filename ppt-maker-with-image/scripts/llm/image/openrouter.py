from __future__ import annotations

import base64
from typing import Any

import httpx

from ..config import ProviderConfig
from ..errors import ProviderError
from .base import ImageProvider, ImageRenderRequest


class OpenRouterImageProvider(ImageProvider):
    supports_reference_images = True
    supports_seed = False

    def __init__(self, config: ProviderConfig, *, api_key: str) -> None:
        self._config = config
        self._api_key = api_key

    def render(self, request: ImageRenderRequest) -> bytes:
        payload = {
            "model": request.model,
            "messages": [
                {
                    "role": "user",
                    "content": _build_message_content(request.prompt, request.reference_images),
                }
            ],
            "modalities": ["image", "text"],
            "temperature": 0.1,
            "image_config": {
                "aspect_ratio": request.aspect_ratio,
                "image_size": _openrouter_image_size(request.resolution),
            },
        }
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        base_url = (self._config.base_url or "https://openrouter.ai/api/v1").rstrip("/")
        try:
            with httpx.Client(timeout=60.0) as client:
                response = client.post(f"{base_url}/chat/completions", headers=headers, json=payload)
                response.raise_for_status()
                message = response.json()["choices"][0]["message"]
        except Exception as exc:
            raise ProviderError(f"OpenRouter image render failed for model `{request.model}`") from exc
        return _extract_image_bytes(message)


def _extract_image_bytes(message: dict[str, Any]) -> bytes:
    for image in message.get("images") or []:
        image_url = ((image or {}).get("image_url") or {}).get("url", "")
        if image_url.startswith("data:"):
            return base64.b64decode(image_url.split(",", 1)[1])
        if image_url.startswith("http"):
            return _fetch_bytes(image_url)
    raise ProviderError("OpenRouter did not return image data")


def _fetch_bytes(url: str) -> bytes:
    try:
        response = httpx.get(url, timeout=60.0)
        response.raise_for_status()
        return response.content
    except Exception as exc:
        raise ProviderError(f"OpenRouter image download failed: {url}") from exc


def _build_message_content(prompt: str, reference_images: Any) -> Any:
    if not reference_images:
        return prompt
    content: list[dict[str, Any]] = [{"type": "text", "text": prompt}]
    for image_bytes in reference_images:
        encoded = base64.b64encode(image_bytes).decode("ascii")
        content.append({"type": "image_url", "image_url": {"url": f"data:image/png;base64,{encoded}"}})
    return content


def _openrouter_image_size(resolution: str) -> str:
    normalized = resolution.strip().lower()
    if normalized == "3840x2160":
        return "4K"
    return normalized or "4K"
