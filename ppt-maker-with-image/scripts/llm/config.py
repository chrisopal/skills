from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping

import yaml


DEFAULT_PROVIDER_KEY_ENVS: dict[str, str] = {
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "openrouter": "OPENROUTER_API_KEY",
    "azure": "AZURE_OPENAI_API_KEY",
    "ollama": "",
    "gemini": "GEMINI_API_KEY",
}


@dataclass(frozen=True)
class ModelRoleConfig:
    provider: str
    model: str


@dataclass(frozen=True)
class ProviderConfig:
    name: str
    api_key_env: str | None = None
    base_url: str | None = None
    text_model: str | None = None
    image_model: str | None = None
    extra: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ModelConfig:
    default_provider: str
    text: ModelRoleConfig
    image: ModelRoleConfig
    aspect_ratio: str = "16:9"
    resolution: str = "3840x2160"
    default_output_mode: str = "image_pptx"
    language: str = "zh-CN"
    font_preferences: Mapping[str, str] = field(default_factory=dict)
    providers: Mapping[str, ProviderConfig] = field(default_factory=dict)
    raw: Mapping[str, Any] = field(default_factory=dict)

    def get_provider(self, name: str) -> ProviderConfig | None:
        return self.providers.get(name.lower())

    def require_provider(self, name: str) -> ProviderConfig:
        provider = self.get_provider(name)
        if provider is None:
            raise KeyError(f"Provider not configured: {name}")
        return provider


def load_model_config(path: str | Path) -> ModelConfig:
    config_path = Path(path).expanduser().resolve()
    raw = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    providers = _load_providers(raw.get("providers") or {})
    default_provider = str(raw.get("default_provider") or raw.get("text_provider") or "openrouter").strip()
    text = _load_role(raw, "text", default_provider)
    image = _load_role(raw, "image", default_provider)
    return ModelConfig(
        default_provider=default_provider,
        text=text,
        image=image,
        aspect_ratio=str(raw.get("aspect_ratio") or "16:9"),
        resolution=str(raw.get("resolution") or "3840x2160"),
        default_output_mode=str(raw.get("default_output_mode") or "image_pptx"),
        language=str(raw.get("language") or "zh-CN"),
        font_preferences=dict(raw.get("font_preferences") or {}),
        providers=providers,
        raw=raw,
    )


def read_provider_key(
    provider: str | ProviderConfig,
    *,
    providers: Mapping[str, ProviderConfig] | None = None,
    env: Mapping[str, str] | None = None,
) -> str | None:
    environ = env or os.environ
    if isinstance(provider, ProviderConfig):
        config = provider
    else:
        config = (providers or {}).get(provider.lower()) or ProviderConfig(name=provider.lower())
    key_env = (config.api_key_env or DEFAULT_PROVIDER_KEY_ENVS.get(config.name.lower(), "")).strip()
    if not key_env:
        return None
    value = environ.get(key_env, "").strip()
    return value or None


def _load_role(raw: Mapping[str, Any], role_name: str, default_provider: str) -> ModelRoleConfig:
    role_payload = raw.get(role_name)
    if isinstance(role_payload, Mapping):
        provider = str(role_payload.get("provider") or default_provider).strip()
        model = str(role_payload.get("model") or raw.get(f"{role_name}_model") or "").strip()
    else:
        provider = str(raw.get(f"{role_name}_provider") or default_provider).strip()
        model = str(raw.get(f"{role_name}_model") or "").strip()
    return ModelRoleConfig(provider=provider, model=model)


def _load_providers(raw_providers: Mapping[str, Any]) -> dict[str, ProviderConfig]:
    providers: dict[str, ProviderConfig] = {}
    for name, payload in raw_providers.items():
        normalized_name = str(name).strip().lower()
        data = dict(payload or {})
        providers[normalized_name] = ProviderConfig(
            name=normalized_name,
            api_key_env=_normalize_optional_string(data.pop("api_key_env", None)),
            base_url=_normalize_optional_string(data.pop("base_url", None)),
            text_model=_normalize_optional_string(data.pop("text_model", None)),
            image_model=_normalize_optional_string(data.pop("image_model", None)),
            extra=data,
        )
    return providers


def _normalize_optional_string(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None
