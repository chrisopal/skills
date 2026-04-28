from __future__ import annotations

from ..config import ModelConfig, ProviderConfig, read_provider_key
from ..errors import UnsupportedFeatureError
from .base import ImageProvider, ImageRenderRequest
from .gemini import GeminiImageProvider
from .openai import OpenAIImageProvider
from .openrouter import OpenRouterImageProvider


def build_image_provider(
    config: ModelConfig,
    *,
    provider_name: str | None = None,
) -> ImageProvider:
    resolved_name = (provider_name or config.image.provider).strip().lower()
    provider_config = config.get_provider(resolved_name)
    if provider_config is None:
        raise UnsupportedFeatureError(f"Image provider is not configured: {resolved_name}")

    if resolved_name == "openrouter":
        return OpenRouterImageProvider(provider_config, api_key=_require_provider_key(provider_config, config))
    if resolved_name == "openai":
        return OpenAIImageProvider(provider_config, api_key=_require_provider_key(provider_config, config))
    if resolved_name == "gemini":
        return GeminiImageProvider(provider_config, api_key=_require_provider_key(provider_config, config))
    raise UnsupportedFeatureError(f"Image provider is not supported: {resolved_name}")


def _require_provider_key(provider_config: ProviderConfig, config: ModelConfig) -> str:
    api_key = read_provider_key(provider_config, providers=config.providers)
    if api_key:
        return api_key
    key_hint = provider_config.api_key_env or provider_config.name.upper()
    raise UnsupportedFeatureError(
        f"Provider `{provider_config.name}` requires `{key_hint}` for image rendering"
    )


__all__ = [
    "ImageProvider",
    "ImageRenderRequest",
    "OpenAIImageProvider",
    "OpenRouterImageProvider",
    "GeminiImageProvider",
    "build_image_provider",
]
