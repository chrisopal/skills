"""Cover provider-neutral LLM config resolution."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

SKILL_ROOT = Path(__file__).resolve().parent.parent
LIB_PATH = SKILL_ROOT / "scripts" / "lib" / "llm_config.py"


def _load():
    name = "llm_config"
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, LIB_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


cfg = _load()


# ---------------------------------------------------------------------------
# api_key
# ---------------------------------------------------------------------------


def test_api_key_prefers_llm_over_openrouter():
    env = {"LLM_API_KEY": "new-key", "OPENROUTER_API_KEY": "old-key"}
    assert cfg.resolve_api_key(env) == "new-key"


def test_api_key_falls_back_to_openrouter():
    env = {"OPENROUTER_API_KEY": "old-key"}
    assert cfg.resolve_api_key(env) == "old-key"


def test_api_key_returns_none_when_unset():
    env = {}
    assert cfg.resolve_api_key(env) is None


def test_api_key_strips_whitespace():
    env = {"LLM_API_KEY": "  abc  "}
    assert cfg.resolve_api_key(env) == "abc"


# ---------------------------------------------------------------------------
# base_url
# ---------------------------------------------------------------------------


def test_base_url_prefers_llm_env_over_legacy():
    env = {"LLM_BASE_URL": "https://api.openai.com/v1", "OPENROUTER_BASE_URL": "https://openrouter.ai/api/v1"}
    assert cfg.resolve_base_url({}, env) == "https://api.openai.com/v1"


def test_base_url_falls_back_to_legacy_env():
    env = {"OPENROUTER_BASE_URL": "https://openrouter.ai/api/v1"}
    assert cfg.resolve_base_url({}, env) == "https://openrouter.ai/api/v1"


def test_base_url_falls_back_to_config():
    env = {}
    assert cfg.resolve_base_url({"base_url": "http://localhost:8000/v1"}, env) == "http://localhost:8000/v1"


def test_base_url_no_hardcoded_default():
    """No hidden default — explicit configuration is required."""

    env = {}
    assert cfg.resolve_base_url({}, env) is None


# ---------------------------------------------------------------------------
# text/vision/image models
# ---------------------------------------------------------------------------


def test_text_model_env_overrides_config():
    env = {"LLM_TEXT_MODEL": "gpt-4o"}
    assert cfg.resolve_text_model({"text_model": "claude-3"}, env) == "gpt-4o"


def test_text_model_uses_config_when_env_empty():
    env = {}
    assert cfg.resolve_text_model({"text_model": "claude-3"}, env) == "claude-3"


def test_pptx_js_model_falls_back_to_text_model():
    env = {}
    assert cfg.resolve_pptx_js_model({"text_model": "claude-3"}, env) == "claude-3"


def test_vision_model_falls_back_to_text_model():
    env = {}
    assert cfg.resolve_vision_model({"text_model": "claude-3"}, env) == "claude-3"


def test_image_model_does_not_fall_back():
    env = {}
    assert cfg.resolve_image_model({"text_model": "claude-3"}, env) is None


# ---------------------------------------------------------------------------
# provider detection
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("base_url, expected", [
    ("https://openrouter.ai/api/v1", "openrouter"),
    ("https://api.openai.com/v1", "openai"),
    ("https://groq.com/openai/v1", "groq"),
    ("https://api.together.ai/v1", "together"),
    ("https://api.deepseek.com/v1", "deepseek"),
    ("https://my-resource.openai.azure.com/openai/deployments/gpt4", "azure"),
    ("http://localhost:11434/v1", "ollama"),
    ("http://localhost:8000/v1", "openai-compatible"),
    (None, "openai-compatible"),
])
def test_provider_inferred_from_base_url(base_url, expected):
    assert cfg._provider_from_base_url(base_url) == expected


def test_explicit_provider_in_config_wins():
    assert cfg.resolve_provider({"provider": "azure"}, "https://openrouter.ai/api/v1") == "azure"


# ---------------------------------------------------------------------------
# settings + diagnostics
# ---------------------------------------------------------------------------


def test_resolve_settings_aggregates(env=None):
    env = {
        "LLM_API_KEY": "sk-abc",
        "LLM_BASE_URL": "https://api.openai.com/v1",
        "LLM_TEXT_MODEL": "gpt-4o",
    }
    settings = cfg.resolve_settings({}, env)
    assert settings.api_key == "sk-abc"
    assert settings.base_url == "https://api.openai.com/v1"
    assert settings.text_model == "gpt-4o"
    assert settings.provider == "openai"
    assert settings.headers()["Authorization"] == "Bearer sk-abc"


def test_diagnose_lists_all_missing():
    settings = cfg.resolve_settings({}, {})
    issues = cfg.diagnose_for_live_calls(settings)
    assert any("LLM_API_KEY" in i for i in issues)
    assert any("LLM_BASE_URL" in i for i in issues)
    assert any("text_model" in i for i in issues)


def test_diagnose_passes_when_all_set():
    settings = cfg.resolve_settings(
        {"text_model": "x"},
        {"LLM_API_KEY": "k", "LLM_BASE_URL": "u"},
    )
    assert cfg.diagnose_for_live_calls(settings) == []


# ---------------------------------------------------------------------------
# image route
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("provider, expected", [
    ("openai", "images_api"),
    ("azure", "images_api"),
    ("openrouter", "chat"),
    ("anthropic", "chat"),
    ("openai-compatible", "chat"),
])
def test_image_route_per_provider(provider, expected):
    settings = cfg.LLMSettings(
        api_key="k", base_url="u", text_model=None,
        vision_model=None, image_model=None, provider=provider,
    )
    assert cfg.image_route(settings) == expected
