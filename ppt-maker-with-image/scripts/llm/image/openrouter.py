from __future__ import annotations

import base64
from typing import Any

import httpx

from ..config import ProviderConfig
from ..errors import ProviderError
from .base import ImageProvider, ImageRenderRequest


class OpenRouterImageProvider(ImageProvider):
    def __init__(self, config: ProviderConfig, *, api_key: str) -> None:
        self._config = config
        self._api_key = api_key

    def render(self, request: ImageRenderRequest) -> bytes:
        payload = {
            "model": request.model,
            "messages": [{"role": "user", "content": request.prompt}],
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
            response = httpx.get(image_url, timeout=60.0)
            response.raise_for_status()
            return response.content
    raise ProviderError("OpenRouter did not return image data")


def _openrouter_image_size(resolution: str) -> str:
    normalized = resolution.strip().lower()
    if normalized == "3840x2160":
        return "4K"
    return normalized or "4K"
