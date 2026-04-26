"""Verify palette extraction is deterministic and color_strategy mapping fills 6 slots."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest
from PIL import Image

SKILL_ROOT = Path(__file__).resolve().parent.parent
LIB_PATH = SKILL_ROOT / "scripts" / "lib" / "palette_extraction.py"


def _load_module():
    name = "palette_extraction"
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, LIB_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


palette_mod = _load_module()


def _make_two_color_image(path: Path, color_a: tuple[int, int, int], color_b: tuple[int, int, int]):
    img = Image.new("RGB", (40, 20), color_a)
    half = Image.new("RGB", (10, 20), color_b)
    img.paste(half, (30, 0))
    img.save(path)


def test_extract_returns_dominant_color_first(tmp_path):
    image_path = tmp_path / "two.png"
    _make_two_color_image(image_path, (200, 50, 50), (50, 200, 50))
    palette = palette_mod.extract_palette(image_path, n_colors=4)
    assert palette[0].fraction > palette[1].fraction
    assert palette[0].rgb[0] > 150 and palette[0].rgb[1] < 100  # red dominant


def test_extract_is_deterministic_for_same_input(tmp_path):
    image_path = tmp_path / "stable.png"
    _make_two_color_image(image_path, (10, 20, 30), (240, 230, 220))
    a = palette_mod.extract_palette(image_path, n_colors=3)
    b = palette_mod.extract_palette(image_path, n_colors=3)
    assert [c.hex for c in a] == [c.hex for c in b]


def test_extract_returns_at_most_n_colors(tmp_path):
    image_path = tmp_path / "n.png"
    _make_two_color_image(image_path, (10, 20, 30), (240, 230, 220))
    palette = palette_mod.extract_palette(image_path, n_colors=5)
    # The image has only 2 distinct colors, so the palette caps at 2.
    assert len(palette) <= 5
    assert len(palette) >= 2


def test_extract_invalid_n_colors_raises(tmp_path):
    image_path = tmp_path / "n.png"
    _make_two_color_image(image_path, (10, 20, 30), (240, 230, 220))
    with pytest.raises(ValueError):
        palette_mod.extract_palette(image_path, n_colors=0)


def test_extract_missing_file_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        palette_mod.extract_palette(tmp_path / "missing.png")


def test_palette_to_color_strategy_fills_all_six_slots(tmp_path):
    image_path = tmp_path / "cs.png"
    _make_two_color_image(image_path, (200, 50, 50), (50, 200, 50))
    palette = palette_mod.extract_palette(image_path, n_colors=6)
    strategy = palette_mod.palette_to_color_strategy(palette)
    assert set(strategy) == {
        "background", "primary", "secondary", "neutral", "text_primary", "text_secondary",
    }
    assert all(v.startswith("#") and len(v) == 7 for v in strategy.values())


def test_palette_to_color_strategy_uses_fallbacks_for_short_palette(tmp_path):
    image_path = tmp_path / "short.png"
    img = Image.new("RGB", (10, 10), (10, 10, 10))
    img.save(image_path)
    palette = palette_mod.extract_palette(image_path, n_colors=2)
    strategy = palette_mod.palette_to_color_strategy(palette)
    assert strategy["text_primary"] == "#1E1E1E"  # fallback
    assert strategy["text_secondary"] == "#6B7280"
