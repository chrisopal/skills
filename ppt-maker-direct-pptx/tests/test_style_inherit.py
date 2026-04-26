"""Cover preset inheritance, override merging, lock-field enforcement, and aliases."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

SKILL_ROOT = Path(__file__).resolve().parent.parent
LIB_PATH = SKILL_ROOT / "scripts" / "lib" / "style_inherit.py"
SCHEMA_PATH = SKILL_ROOT / "assets" / "schemas" / "master_style.schema.json"


def _load_module():
    name = "style_inherit"
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, LIB_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


inherit = _load_module()


@pytest.fixture(scope="module")
def schema_validator():
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    return Draft202012Validator(schema)


def test_pure_preset_copy_marks_source_preset(schema_validator):
    result = inherit.inherit_preset("huixin")
    assert result["source"] == "preset"
    assert result["parent_template_id"] is None
    assert result["template_id"] == "huixin"
    schema_validator.validate(result)


def test_override_marks_source_hybrid_and_parent(schema_validator):
    result = inherit.inherit_preset(
        "huixin",
        {"color_strategy.primary_green": "#1A237E"},
    )
    assert result["source"] == "hybrid"
    assert result["parent_template_id"] == "huixin"
    assert result["color_strategy"]["primary_green"] == "#1A237E"
    # untouched fields preserved
    assert result["color_strategy"]["secondary_teal"] == "#0F95B6"
    schema_validator.validate(result)


def test_override_does_not_mutate_preset_brief_on_disk():
    before = (SKILL_ROOT / "assets" / "huixin_master_style_brief.json").read_text(encoding="utf-8")
    inherit.inherit_preset("huixin", {"color_strategy.primary_green": "#FF0000"})
    after = (SKILL_ROOT / "assets" / "huixin_master_style_brief.json").read_text(encoding="utf-8")
    assert before == after


def test_override_creates_intermediate_dicts():
    result = inherit.inherit_preset(
        "huixin",
        {"pattern_palette.icon_style": "rounded"},
    )
    assert result["pattern_palette"]["icon_style"] == "rounded"


def test_alias_resolution(schema_validator):
    result = inherit.inherit_preset("慧新")
    assert result["template_id"] == "huixin"
    schema_validator.validate(result)


def test_unknown_preset_raises():
    with pytest.raises(inherit.UnknownPresetError):
        inherit.inherit_preset("does-not-exist")


def test_lock_fields_block_overrides(tmp_path):
    """If a preset declares lock_fields, overrides on those paths must raise."""

    # Build a fake preset with lock_fields by writing temp manifest + brief.
    brief = json.loads(
        (SKILL_ROOT / "assets" / "huixin_master_style_brief.json").read_text(encoding="utf-8")
    )
    brief["lock_fields"] = ["color_strategy.primary_green", "typography"]
    brief_path = tmp_path / "locked_brief.json"
    brief_path.write_text(json.dumps(brief, ensure_ascii=False), encoding="utf-8")

    manifest = {
        "schema_version": 1,
        "templates": [
            {
                "template_id": "locked",
                "aliases": [],
                "preset_asset": "irrelevant.json",
                "brief_asset": brief_path.name,
            }
        ],
    }
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    # Direct override on locked leaf -> error
    with pytest.raises(inherit.LockedFieldError):
        inherit.inherit_preset(
            "locked",
            {"color_strategy.primary_green": "#000"},
            manifest_path=manifest_path,
            assets_dir=tmp_path,
        )

    # Override on a child of a locked subtree -> error
    with pytest.raises(inherit.LockedFieldError):
        inherit.inherit_preset(
            "locked",
            {"typography.title_font": "Arial"},
            manifest_path=manifest_path,
            assets_dir=tmp_path,
        )

    # Override on an unrelated field -> ok
    result = inherit.inherit_preset(
        "locked",
        {"color_strategy.secondary_teal": "#000"},
        manifest_path=manifest_path,
        assets_dir=tmp_path,
    )
    assert result["color_strategy"]["secondary_teal"] == "#000"


def test_list_preset_ids_returns_all_shipped():
    ids = inherit.list_preset_ids()
    assert "huixin" in ids
    assert "dark-english-business" in ids
    assert len(ids) >= 5
