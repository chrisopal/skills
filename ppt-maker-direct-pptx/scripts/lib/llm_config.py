"""Provider-neutral LLM configuration helpers.

The skill speaks the OpenAI Chat Completions wire format, so any compatible
endpoint works (OpenAI, Azure OpenAI, OpenRouter, Groq, Together, DeepSeek,
local vLLM/Ollama with OpenAI shim, etc.). This module centralizes how we
read configuration so the same skill can target any of those providers.

Resolution order (first non-empty wins):

  api_key       LLM_API_KEY  →  OPENROUTER_API_KEY
  base_url      LLM_BASE_URL →  OPENROUTER_BASE_URL  →  config["base_url"]
  text_model    LLM_TEXT_MODEL  →  config["text_model"]
  vision_model  LLM_VISION_MODEL  →  config["vision_model"]  →  text_model
  image_model   LLM_IMAGE_MODEL  →  config["image_model"]
  provider      config["provider"]  →  auto-detect from base_url

`base_url` has NO hardcoded default. Users must configure either
LLM_BASE_URL (env), OPENROUTER_BASE_URL (legacy env), or
model_config.yaml `base_url` to point at a real endpoint. The error message
on miss lists every option so OpenRouter, OpenAI, and self-hosted users all
know what to set.
"""

from __future__ import annotations

import os
from dataclasses import dataclass


# Provider hints used for image-generation routing and friendly diagnostics.
KNOWN_PROVIDERS = (
    "openrouter",
    "openai",
    "azure",
    "groq",
    "together",
    "deepseek",
    "anthropic",
    "ollama",
    "vllm",
    "openai-compatible",
)


@dataclass(frozen=True)
class LLMSettings:
    api_key: str | None
    base_url: str | None
    text_model: str | None
    vision_model: str | None
    image_model: str | None
    provider: str

    def headers(self) -> dict[str, str]:
        if not self.api_key:
            return {"Content-Type": "application/json"}
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }


def _first(*values: str | None) -> str | None:
    for v in values:
        if v is None:
            continue
        s = str(v).strip()
        if s:
            return s
    return None


def resolve_api_key(env: dict | None = None) -> str | None:
    e = env if env is not None else os.environ
    return _first(e.get("LLM_API_KEY"), e.get("OPENROUTER_API_KEY"))


def resolve_base_url(config: dict | None = None, env: dict | None = None) -> str | None:
    e = env if env is not None else os.environ
    config = config or {}
    return _first(
        e.get("LLM_BASE_URL"),
        e.get("OPENROUTER_BASE_URL"),
        config.get("base_url"),
    )


def resolve_text_model(config: dict | None = None, env: dict | None = None) -> str | None:
    e = env if env is not None else os.environ
    config = config or {}
    return _first(e.get("LLM_TEXT_MODEL"), config.get("text_model"))


def resolve_pptx_js_model(config: dict | None = None, env: dict | None = None) -> str | None:
    e = env if env is not None else os.environ
    config = config or {}
    return _first(
        e.get("LLM_PPTX_JS_MODEL"),
        config.get("pptx_js_model"),
        e.get("LLM_TEXT_MODEL"),
        config.get("text_model"),
    )


def resolve_vision_model(config: dict | None = None, env: dict | None = None) -> str | None:
    e = env if env is not None else os.environ
    config = config or {}
    return _first(
        e.get("LLM_VISION_MODEL"),
        config.get("vision_model"),
        e.get("LLM_TEXT_MODEL"),
        config.get("text_model"),
    )


def resolve_image_model(config: dict | None = None, env: dict | None = None) -> str | None:
    e = env if env is not None else os.environ
    config = config or {}
    return _first(
        e.get("LLM_IMAGE_MODEL"),
        config.get("image_model"),
        config.get("pptx_image_model"),
    )


def _provider_from_base_url(base_url: str | None) -> str:
    if not base_url:
        return "openai-compatible"
    haystack = base_url.lower()
    if "openrouter.ai" in haystack:
        return "openrouter"
    if "azure" in haystack:
        return "azure"
    if "groq.com" in haystack:
        return "groq"
    if "together.ai" in haystack or "together.xyz" in haystack:
        return "together"
    if "deepseek.com" in haystack:
        return "deepseek"
    if "anthropic.com" in haystack:
        return "anthropic"
    if "openai.com" in haystack or "openai.azure" in haystack:
        return "openai"
    if "11434" in haystack or "ollama" in haystack:
        return "ollama"
    if "vllm" in haystack:
        return "vllm"
    return "openai-compatible"


def resolve_provider(config: dict | None = None, base_url: str | None = None) -> str:
    config = config or {}
    explicit = _first(config.get("provider"))
    if explicit:
        return explicit
    return _provider_from_base_url(base_url)


def resolve_settings(config: dict | None = None, env: dict | None = None) -> LLMSettings:
    base_url = resolve_base_url(config, env)
    return LLMSettings(
        api_key=resolve_api_key(env),
        base_url=base_url,
        text_model=resolve_text_model(config, env),
        vision_model=resolve_vision_model(config, env),
        image_model=resolve_image_model(config, env),
        provider=resolve_provider(config, base_url),
    )


# ---------------------------------------------------------------------------
# Diagnostics
# ---------------------------------------------------------------------------


MISSING_API_KEY_MSG = (
    "LLM API key is required for live model calls. "
    "Set LLM_API_KEY (or OPENROUTER_API_KEY) in the environment. "
    "Use --dry-run for local placeholder output."
)

MISSING_BASE_URL_MSG = (
    "LLM base URL is required for live model calls. "
    "Set LLM_BASE_URL (or OPENROUTER_BASE_URL), or add `base_url` to model_config.yaml. "
    "Examples:\n"
    "  - OpenAI:     https://api.openai.com/v1\n"
    "  - OpenRouter: https://openrouter.ai/api/v1\n"
    "  - Azure:      https://<resource>.openai.azure.com/openai/deployments/<deployment>\n"
    "  - Groq:       https://api.groq.com/openai/v1\n"
    "  - Local vLLM: http://localhost:8000/v1\n"
    "  - Ollama:     http://localhost:11434/v1"
)


def diagnose_for_live_calls(settings: LLMSettings) -> list[str]:
    issues: list[str] = []
    if not settings.api_key:
        issues.append(MISSING_API_KEY_MSG)
    if not settings.base_url:
        issues.append(MISSING_BASE_URL_MSG)
    if not settings.text_model:
        issues.append(
            "text_model is required: set LLM_TEXT_MODEL or model_config.yaml `text_model`."
        )
    return issues


# ---------------------------------------------------------------------------
# Image generation routing
# ---------------------------------------------------------------------------


# Providers that support OpenAI-style /v1/images/generations.
NATIVE_IMAGE_API_PROVIDERS = {"openai", "azure", "together"}

# Providers that produce images by way of /chat/completions (image embedded
# in the message content).
CHAT_IMAGE_PROVIDERS = {"openrouter", "anthropic"}


def image_route(settings: LLMSettings) -> str:
    """Return 'images_api' (POST /images/generations) or 'chat' (POST
    /chat/completions with an image message)."""

    if settings.provider in NATIVE_IMAGE_API_PROVIDERS:
        return "images_api"
    if settings.provider in CHAT_IMAGE_PROVIDERS:
        return "chat"
    # Default: chat. Most OpenAI-compatible endpoints that don't have native
    # image gen will simply error, which the caller catches and falls back.
    return "chat"
