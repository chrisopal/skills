from __future__ import annotations

import base64

import httpx

from ..config import ProviderConfig
from ..errors import ProviderError
from .base import ImageProvider, ImageRenderRequest


class OpenAIImageProvider(ImageProvider):
    supports_reference_images = False
    supports_seed = False

    def __init__(self, config: ProviderConfig, *, api_key: str) -> None:
        self._config = config
        self._api_key = api_key

    def render(self, request: ImageRenderRequest) -> bytes:
        self._validate_request(request)
        payload = {
            "model": request.model,
            "prompt": request.prompt,
            "size": _openai_image_size(request.aspect_ratio, request.resolution),
        }
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        base_url = (self._config.base_url or "https://api.openai.com/v1").rstrip("/")
        try:
            with httpx.Client(timeout=60.0) as client:
                response = client.post(f"{base_url}/images/generations", headers=headers, json=payload)
                response.raise_for_status()
                data = response.json()["data"][0]
        except Exception as exc:
            raise ProviderError(f"OpenAI image render failed for model `{request.model}`") from exc

        image_base64 = data.get("b64_json")
        if image_base64:
            return base64.b64decode(image_base64)

        image_url = data.get("url", "")
        if image_url.startswith("http"):
            return _fetch_bytes(image_url)

        raise ProviderError("OpenAI did not return image data")


def _fetch_bytes(url: str) -> bytes:
    try:
        response = httpx.get(url, timeout=60.0)
        response.raise_for_status()
        return response.content
    except Exception as exc:
        raise ProviderError(f"OpenAI image download failed: {url}") from exc


def _openai_image_size(aspect_ratio: str, resolution: str) -> str:
    normalized_aspect = aspect_ratio.strip()
    normalized_resolution = resolution.strip().lower()
    if normalized_resolution in {"1024x1024", "1536x1024", "1024x1536"}:
        return normalized_resolution
    if normalized_aspect == "16:9":
        return "1536x1024"
    if normalized_aspect == "9:16":
        return "1024x1536"
    return "1024x1024"
