from __future__ import annotations

from typing import Any

from llm.config import ModelConfig, read_provider_key


def _text_config(config: ModelConfig) -> tuple[str, str | None, str | None]:
    provider = config.get_provider(config.text.provider)
    model = (config.text.model or "").strip()
    if not model and provider:
        model = (provider.text_model or "").strip()
    return (
        model,
        read_provider_key(config.text.provider, providers=config.providers),
        provider.base_url if provider else None,
    )


def build_provider_capabilities(config: ModelConfig) -> dict[str, dict[str, Any]]:
    text_provider = config.get_provider(config.text.provider)
    image_provider = config.get_provider(config.image.provider)
    return {
        "text": {
            "provider": config.text.provider,
            "model": config.text.model,
            "base_url": text_provider.base_url if text_provider else None,
            "has_api_key": bool(read_provider_key(config.text.provider, providers=config.providers)),
            "supports_json": True,
        },
        "image": {
            "provider": config.image.provider,
            "model": config.image.model,
            "base_url": image_provider.base_url if image_provider else None,
            "has_api_key": bool(read_provider_key(config.image.provider, providers=config.providers)),
            "supports_json": False,
        },
    }
