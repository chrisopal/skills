"""Verify the renderer drops skipped placeholders and propagates other statuses."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

SKILL_ROOT = Path(__file__).resolve().parent.parent


def _load_renderer():
    sys.path.insert(0, str(SKILL_ROOT / "scripts"))
    name = "ppt_renderer"
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, SKILL_ROOT / "scripts" / "ppt_renderer.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


renderer = _load_renderer()


def test_skipped_placeholder_dropped():
    raw = [
        {"id": "a", "prompt": "img a", "status": "skipped"},
        {"id": "b", "prompt": "img b", "status": "placeholder"},
    ]
    out = renderer.normalize_placeholders(raw, page_no=3)
    ids = [p["id"] for p in out]
    assert ids == ["b"]


def test_generated_status_preserved():
    raw = [{"id": "a", "prompt": "img a", "status": "generated"}]
    out = renderer.normalize_placeholders(raw, page_no=1)
    assert out[0]["status"] == "generated"


def test_missing_status_defaults_to_placeholder():
    raw = [{"id": "a", "prompt": "img a"}]
    out = renderer.normalize_placeholders(raw, page_no=1)
    assert out[0]["status"] == "placeholder"


def test_only_skipped_placeholders_means_no_image_region():
    raw = [
        {"id": "a", "prompt": "img a", "status": "skipped"},
        {"id": "b", "prompt": "img b", "status": "skipped"},
    ]
    out = renderer.normalize_placeholders(raw, page_no=2)
    assert out == []
    regions = renderer.derive_layout_regions(out)
    # No image placeholders → no images region in derived layout regions
    assert "images" not in regions or not regions.get("images")
