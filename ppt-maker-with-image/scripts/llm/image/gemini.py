from __future__ import annotations

import base64
from typing import Any

from ..config import ProviderConfig
from ..errors import ProviderError, UnsupportedFeatureError
from .base import ImageProvider, ImageRenderRequest


class GeminiImageProvider(ImageProvider):
    def __init__(self, config: ProviderConfig, *, api_key: str) -> None:
        self._config = config
        self._api_key = api_key

    def render(self, request: ImageRenderRequest) -> bytes:
        try:
            from google import genai
            from google.genai import types
        except ImportError as exc:
            raise UnsupportedFeatureError("google-genai is required for Gemini image generation") from exc

        try:
            client = genai.Client(api_key=self._api_key)
            response = client.models.generate_content(
                model=request.model,
                contents=request.prompt,
                config=types.GenerateContentConfig(
                    response_modalities=["TEXT", "IMAGE"],
                ),
            )
        except Exception as exc:
            raise ProviderError(f"Gemini image render failed for model `{request.model}`") from exc

        return _extract_inline_image_bytes(response)


def _extract_inline_image_bytes(response: Any) -> bytes:
    for candidate in getattr(response, "candidates", []) or []:
        content = getattr(candidate, "content", None)
        for part in getattr(content, "parts", []) or []:
            inline_data = getattr(part, "inline_data", None)
            if inline_data is None and isinstance(part, dict):
                inline_data = part.get("inline_data")
            if inline_data is None:
                continue
            data = getattr(inline_data, "data", None)
            if data is None and isinstance(inline_data, dict):
                data = inline_data.get("data")
            if isinstance(data, bytes):
                return data
            if isinstance(data, str):
                return base64.b64decode(data)
    raise ProviderError("Gemini did not return inline image data")
