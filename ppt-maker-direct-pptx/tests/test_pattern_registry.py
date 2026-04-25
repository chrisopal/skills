"""Verify PatternRegistry loads, indexes, and slot-validates pattern docs."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

SKILL_ROOT = Path(__file__).resolve().parent.parent
LIB_PATH = SKILL_ROOT / "scripts" / "lib" / "pattern_registry.py"


def _load_module():
    name = "pattern_registry"
    spec = importlib.util.spec_from_file_location(name, LIB_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


registry_mod = _load_module()


def _minimal_pattern_doc(pattern_id: str = "kpi_strip", **overrides) -> dict:
    base = json.loads(
        (SKILL_ROOT / "tests" / "fixtures" / "pattern_minimal.json").read_text(encoding="utf-8")
    )
    base["pattern_id"] = pattern_id
    base.update(overrides)
    return base


def _write(dir_: Path, name: str, data: dict) -> Path:
    path = dir_ / name
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------


def test_loads_valid_patterns_dir(tmp_path):
    _write(tmp_path, "kpi_strip.json", _minimal_pattern_doc("kpi_strip"))
    _write(tmp_path, "summary_takeaways.json", _minimal_pattern_doc("summary_takeaways"))
    reg = registry_mod.PatternRegistry(tmp_path)
    assert reg.list_ids() == ["kpi_strip", "summary_takeaways"]
    assert "kpi_strip" in reg
    assert len(reg) == 2


def test_skips_sample_files(tmp_path):
    _write(tmp_path, "kpi_strip.json", _minimal_pattern_doc("kpi_strip"))
    _write(tmp_path, "kpi_strip.sample.json", {"unrelated": "data"})
    reg = registry_mod.PatternRegistry(tmp_path)
    assert reg.list_ids() == ["kpi_strip"]


def test_invalid_pattern_raises_pattern_schema_error(tmp_path):
    bad = _minimal_pattern_doc("kpi_strip")
    bad["pattern_id"] = "BadCamelCase"  # violates schema regex
    _write(tmp_path, "kpi_strip.json", bad)
    with pytest.raises(registry_mod.PatternSchemaError):
        registry_mod.PatternRegistry(tmp_path)


def test_filename_must_match_pattern_id(tmp_path):
    doc = _minimal_pattern_doc("kpi_strip")
    _write(tmp_path, "wrong_name.json", doc)
    with pytest.raises(registry_mod.PatternSchemaError):
        registry_mod.PatternRegistry(tmp_path)


def test_missing_directory_raises(tmp_path):
    with pytest.raises(NotADirectoryError):
        registry_mod.PatternRegistry(tmp_path / "nope")


def test_get_unknown_id_raises(tmp_path):
    _write(tmp_path, "kpi_strip.json", _minimal_pattern_doc("kpi_strip"))
    reg = registry_mod.PatternRegistry(tmp_path)
    with pytest.raises(KeyError):
        reg.get("does_not_exist")


# ---------------------------------------------------------------------------
# validate_slots
# ---------------------------------------------------------------------------


@pytest.fixture
def registry(tmp_path):
    _write(tmp_path, "kpi_strip.json", _minimal_pattern_doc("kpi_strip"))
    return registry_mod.PatternRegistry(tmp_path)


def test_validate_slots_passes_when_required_filled(registry):
    slots = {
        "kpi_1_value": "+38%",
        "kpi_1_label": "ROI",
        "kpi_2_value": "12k",
        "kpi_2_label": "MAU",
    }
    assert registry.validate_slots("kpi_strip", slots) == []


def test_validate_slots_reports_missing_required(registry):
    slots = {"kpi_1_value": "+38%", "kpi_1_label": "ROI", "kpi_2_value": "12k"}
    errors = registry.validate_slots("kpi_strip", slots)
    rules = {(e.slot, e.rule) for e in errors}
    assert ("kpi_2_label", "missing_required") in rules


def test_validate_slots_treats_empty_string_as_missing(registry):
    slots = {
        "kpi_1_value": "+38%",
        "kpi_1_label": "",
        "kpi_2_value": "12k",
        "kpi_2_label": "MAU",
    }
    errors = registry.validate_slots("kpi_strip", slots)
    rules = {(e.slot, e.rule) for e in errors}
    assert ("kpi_1_label", "missing_required") in rules


def test_validate_slots_reports_max_chars_violation(registry):
    slots = {
        "kpi_1_value": "+38%",
        "kpi_1_label": "x" * 50,  # max_chars=24 in fixture
        "kpi_2_value": "12k",
        "kpi_2_label": "MAU",
    }
    errors = registry.validate_slots("kpi_strip", slots)
    bad = [e for e in errors if e.rule == "max_chars"]
    assert len(bad) == 1
    assert bad[0].slot == "kpi_1_label"
    assert "24" in bad[0].detail


def test_validate_slots_reports_unknown_slot(registry):
    slots = {
        "kpi_1_value": "+38%",
        "kpi_1_label": "ROI",
        "kpi_2_value": "12k",
        "kpi_2_label": "MAU",
        "made_up_slot": "x",
    }
    errors = registry.validate_slots("kpi_strip", slots)
    rules = {(e.slot, e.rule) for e in errors}
    assert ("made_up_slot", "unknown_slot") in rules


def test_optional_slot_can_be_missing(registry):
    slots = {
        "kpi_1_value": "+38%",
        "kpi_1_label": "ROI",
        "kpi_2_value": "12k",
        "kpi_2_label": "MAU",
        # kpi_3 / kpi_4 are optional in the fixture
    }
    assert registry.validate_slots("kpi_strip", slots) == []


def test_pattern_helpers(registry):
    p = registry.get("kpi_strip")
    assert "kpi_1_value" in p.slot_names()
    assert "kpi_1_value" in p.required_slot_names()
    assert "kpi_3_value" not in p.required_slot_names()
