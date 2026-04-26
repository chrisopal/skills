"""Verify image-generation route selection between /chat/completions and /images/generations."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

SKILL_ROOT = Path(__file__).resolve().parent.parent


def _load():
    name = "generate_image_assets"
    if name in sys.modules:
        return sys.modules[name]
    sys.path.insert(0, str(SKILL_ROOT / "scripts"))
    spec = importlib.util.spec_from_file_location(name, SKILL_ROOT / "scripts" / "generate_image_assets.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


gia = _load()


@pytest.mark.parametrize("base_url, expected", [
    ("https://api.openai.com/v1", "images_api"),
    ("https://my-resource.openai.azure.com/openai/deployments/x", "images_api"),
    ("https://openrouter.ai/api/v1", "chat"),
    ("https://api.groq.com/openai/v1", "chat"),
    ("http://localhost:11434/v1", "chat"),
])
def test_route_inferred_from_base_url(base_url, expected):
    assert gia._detect_image_route(base_url, {}) == expected


def test_explicit_image_route_overrides_inference():
    assert gia._detect_image_route("https://api.openai.com/v1", {"image_route": "chat"}) == "chat"
    assert gia._detect_image_route("https://openrouter.ai/api/v1", {"image_route": "images_api"}) == "images_api"


def test_invalid_explicit_route_falls_back_to_inference():
    assert gia._detect_image_route("https://api.openai.com/v1", {"image_route": "garbage"}) == "images_api"
