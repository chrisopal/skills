from __future__ import annotations

from pathlib import Path
from typing import Any

from llm import ProviderConfig, complete_json, read_provider_key
from llm.config import DEFAULT_PROVIDER_KEY_ENVS, ModelConfig

from .common import (
    build_requirement_summary,
    ensure_huixin_assets,
    load_asset_json,
    load_json,
    load_prompt_template,
    resolve_output_dir,
    skill_root,
    write_json,
)
from .manifest import load_manifest, manifest_path, write_manifest

def call_text_model(
    model_config: ModelConfig,
    prompt: str,
    *,
    temperature: float = 0.3,
) -> dict[str, Any]:
    provider = _resolve_provider_config(model_config, model_config.text.provider)
    model_name = (model_config.text.model or provider.text_model or "").strip()
    if not model_name:
        raise RuntimeError(f"Text model is not configured for provider `{provider.name}`")
    api_key = read_provider_key(provider, providers=model_config.providers)
    if provider.api_key_env and not api_key:
        raise RuntimeError(f"Text provider `{provider.name}` requires `{provider.api_key_env}`")
    payload = complete_json(
        model=model_name,
        messages=[{"role": "user", "content": prompt}],
        api_key=api_key,
        base_url=provider.base_url,
        temperature=temperature,
    )
    if not isinstance(payload, dict):
        raise ValueError("Text model must return a JSON object")
    return payload


def resolve_image_model_name(model_config: ModelConfig) -> str:
    provider = _resolve_provider_config(model_config, model_config.image.provider)
    model_name = (model_config.image.model or provider.image_model or "").strip()
    if not model_name:
        raise RuntimeError(f"Image model is not configured for provider `{provider.name}`")
    return model_name


def persist_stage(output_dir: Path, filename: str, data: dict[str, Any]) -> Path:
    path = output_dir / filename
    write_json(path, data)
    return path


def _resolve_provider_config(model_config: ModelConfig, provider_name: str) -> ProviderConfig:
    provider = model_config.get_provider(provider_name)
    if provider is not None:
        return provider
    return ProviderConfig(
        name=provider_name.lower(),
        api_key_env=DEFAULT_PROVIDER_KEY_ENVS.get(provider_name.lower()),
    )


__all__ = [
    "build_requirement_summary",
    "call_text_model",
    "ensure_huixin_assets",
    "load_asset_json",
    "load_json",
    "load_manifest",
    "load_prompt_template",
    "manifest_path",
    "persist_stage",
    "resolve_image_model_name",
    "resolve_output_dir",
    "skill_root",
    "write_json",
    "write_manifest",
]
