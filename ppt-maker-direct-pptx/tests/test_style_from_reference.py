"""End-to-end test for reference-image style extraction with mocked vision call."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest
from PIL import Image

SKILL_ROOT = Path(__file__).resolve().parent.parent
SCRIPT_PATH = SKILL_ROOT / "scripts" / "style_from_reference.py"


def _load_module():
    name = "style_from_reference"
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


reference_mod = _load_module()


def _make_image(path: Path):
    img = Image.new("RGB", (60, 40), (12, 16, 32))
    swatch = Image.new("RGB", (20, 40), (124, 77, 255))
    img.paste(swatch, (40, 0))
    img.save(path)


def _vision_response() -> dict:
    return {
        "template_id": "cyber-purple",
        "template_name": "Cyber Purple",
        "language": "en-US",
        "visual_positioning": "深蓝紫色赛博朋克",
        "deck_voice": "前沿、科技感",
        "typography": {
            "title_font": "Inter",
            "body_font": "Inter",
            "page_title": "40px, bold",
            "body_text": "16px",
        },
        "title_hierarchy_rules": ["one main title per page"],
        "module_layout_patterns": ["KPI strip", "two-column compare"],
        "chart_rules": ["flat 2D"],
        "icon_rules": ["thin line icons"],
        "forbidden_elements": ["3D bevel"],
        "prompt_block": "Cyber purple deck.",
        "confidence": {"typography.title_font": 0.6, "module_layout_patterns": 0.7},
    }


def test_build_master_style_combines_palette_and_vision(tmp_path):
    image = tmp_path / "ref.png"
    _make_image(image)

    captured = {}

    def vision_caller(image_bytes, prompt):
        captured["bytes_len"] = len(image_bytes)
        captured["prompt"] = prompt
        return _vision_response()

    result = reference_mod.build_master_style(image, vision_caller=vision_caller)
    ms = result.master_style

    assert ms["source"] == "reference_extracted"
    assert ms["parent_template_id"] is None
    assert ms["template_name"] == "Cyber Purple"
    assert ms["color_strategy"]["primary"].startswith("#")
    assert ms["color_strategy"]["background"].startswith("#")
    # Vision response did NOT supply color_strategy; ours stays from palette
    assert ms["color_strategy"]["text_primary"] in {"#1E1E1E", "#FFFFFF"} or ms["color_strategy"]["text_primary"].startswith("#")
    # Vision-supplied fields propagated
    assert ms["module_layout_patterns"] == ["KPI strip", "two-column compare"]
    assert "前沿" in ms["deck_voice"]
    # Bytes were forwarded
    assert captured["bytes_len"] > 0
    # Palette hexes present in prompt
    for color in result.palette:
        assert color.hex in captured["prompt"]


def test_vision_color_strategy_overrides_are_dropped(tmp_path):
    """Palette is the source of truth for colors; vision attempts to overwrite are ignored."""

    image = tmp_path / "ref.png"
    _make_image(image)

    response = _vision_response()
    response["color_strategy"] = {"primary": "#FF0000"}

    extracted_strategy = {}

    def caller(image_bytes, prompt):
        return response

    result = reference_mod.build_master_style(image, vision_caller=caller)
    extracted_strategy.update(result.master_style["color_strategy"])
    # The palette colors won, not the vision override
    assert extracted_strategy.get("primary") != "#FF0000"


def test_vision_returns_non_dict_raises(tmp_path):
    image = tmp_path / "ref.png"
    _make_image(image)

    with pytest.raises(reference_mod.ReferenceStyleError):
        reference_mod.build_master_style(image, vision_caller=lambda b, p: "not-an-object")


def test_assembled_style_validates_against_schema(tmp_path):
    image = tmp_path / "ref.png"
    _make_image(image)

    result = reference_mod.build_master_style(
        image, vision_caller=lambda b, p: _vision_response()
    )

    schema_path = SKILL_ROOT / "assets" / "schemas" / "master_style.schema.json"
    from jsonschema import Draft202012Validator

    Draft202012Validator(json.loads(schema_path.read_text(encoding="utf-8"))).validate(
        result.master_style
    )


def test_missing_image_raises_file_not_found(tmp_path):
    with pytest.raises(FileNotFoundError):
        reference_mod.build_master_style(tmp_path / "nope.png", vision_caller=lambda b, p: {})


def test_minimal_vision_response_still_validates(tmp_path):
    image = tmp_path / "ref.png"
    _make_image(image)
    response = {"template_id": "minimal", "template_name": "Minimal"}
    result = reference_mod.build_master_style(image, vision_caller=lambda b, p: response)
    assert result.master_style["template_id"] == "minimal"
    assert result.master_style["typography"]
