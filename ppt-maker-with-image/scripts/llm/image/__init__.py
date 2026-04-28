from __future__ import annotations

from ..config import DEFAULT_PROVIDER_KEY_ENVS, ModelConfig, ProviderConfig, read_provider_key
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
    if resolved_name == "openrouter":
        provider_config = _resolve_provider_config(config, resolved_name)
        return OpenRouterImageProvider(provider_config, api_key=_require_provider_key(provider_config, config))
    if resolved_name == "openai":
        provider_config = _resolve_provider_config(config, resolved_name)
        return OpenAIImageProvider(provider_config, api_key=_require_provider_key(provider_config, config))
    if resolved_name == "gemini":
        provider_config = _resolve_provider_config(config, resolved_name)
        return GeminiImageProvider(provider_config, api_key=_require_provider_key(provider_config, config))
    raise UnsupportedFeatureError(f"Image provider is not supported: {resolved_name}")


def _resolve_provider_config(config: ModelConfig, provider_name: str) -> ProviderConfig:
    provider_config = config.get_provider(provider_name)
    if provider_config is not None:
        return provider_config
    return ProviderConfig(
        name=provider_name,
        api_key_env=DEFAULT_PROVIDER_KEY_ENVS.get(provider_name),
    )


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
