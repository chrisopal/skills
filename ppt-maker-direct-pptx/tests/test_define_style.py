"""Cover the unified style CLI dispatcher."""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path

import pytest
from PIL import Image

SKILL_ROOT = Path(__file__).resolve().parent.parent
SCRIPT_PATH = SKILL_ROOT / "scripts" / "define_style.py"


def _load_module():
    name = "define_style"
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


cli = _load_module()


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_parse_override_with_hex_string():
    key, value = cli._parse_override("color_strategy.primary_green=#1A237E")
    assert key == "color_strategy.primary_green"
    assert value == "#1A237E"


def test_parse_override_with_json_value():
    key, value = cli._parse_override("layout_system.grid_columns=12")
    assert key == "layout_system.grid_columns"
    assert value == 12


def test_parse_override_with_array_value():
    key, value = cli._parse_override('module_layout_patterns=["KPI","Compare"]')
    assert key == "module_layout_patterns"
    assert value == ["KPI", "Compare"]


def test_parse_override_missing_equals_raises():
    with pytest.raises(argparse.ArgumentTypeError):
        cli._parse_override("missing-equals")


def test_preset_subcommand_writes_file(tmp_path):
    out = tmp_path / "master_style.json"
    parser = cli.build_parser()
    args = parser.parse_args(["preset", "--id", "huixin", "--out", str(out)])
    rc = args.func(args)
    assert rc == 0
    written = _read_json(out)
    assert written["template_id"] == "huixin"
    assert written["source"] == "preset"


def test_preset_subcommand_with_overrides(tmp_path):
    out = tmp_path / "master_style.json"
    parser = cli.build_parser()
    args = parser.parse_args([
        "preset", "--id", "huixin",
        "--override", "color_strategy.primary_green=#1A237E",
        "--out", str(out),
    ])
    args.func(args)
    written = _read_json(out)
    assert written["color_strategy"]["primary_green"] == "#1A237E"
    assert written["source"] == "hybrid"
    assert written["parent_template_id"] == "huixin"


def test_nl_subcommand_with_injected_caller(tmp_path):
    out = tmp_path / "master_style.json"

    valid = {
        "template_id": "demo",
        "template_name": "Demo",
        "language": "zh-CN",
        "color_strategy": {
            "primary": "#7C4DFF",
            "secondary": "#00E5FF",
            "neutral": "#1A1A2E",
            "background": "#0F0F1F",
            "text_primary": "#FFFFFF",
            "text_secondary": "#A8A8C0",
            "divider": "#2A2A4A",
        },
        "typography": {"title_font": "Inter", "body_font": "Inter"},
        "source": "nl_generated",
        "parent_template_id": None,
    }

    parser = cli.build_parser()
    args = parser.parse_args([
        "nl", "--description", "neon dark", "--out", str(out),
    ])
    rc = cli.cmd_nl(args, model_caller=lambda prompt: valid)
    assert rc == 0
    written = _read_json(out)
    assert written["template_id"] == "demo"
    assert written["source"] == "nl_generated"


def test_reference_subcommand_with_injected_vision(tmp_path):
    out = tmp_path / "master_style.json"
    image = tmp_path / "ref.png"
    img = Image.new("RGB", (40, 30), (12, 16, 32))
    swatch = Image.new("RGB", (10, 30), (124, 77, 255))
    img.paste(swatch, (30, 0))
    img.save(image)

    vision_response = {
        "template_id": "ref-style",
        "template_name": "Reference Style",
        "language": "zh-CN",
        "typography": {"title_font": "Inter", "body_font": "Inter"},
    }

    parser = cli.build_parser()
    args = parser.parse_args([
        "reference", "--file", str(image), "--out", str(out),
    ])
    rc = cli.cmd_reference(args, vision_caller=lambda b, p: vision_response)
    assert rc == 0
    written = _read_json(out)
    assert written["template_id"] == "ref-style"
    assert written["source"] == "reference_extracted"


def test_main_requires_subcommand():
    parser = cli.build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args([])
