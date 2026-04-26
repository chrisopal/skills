"""Verify all 12 authored patterns load via PatternRegistry and meet expected invariants."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

SKILL_ROOT = Path(__file__).resolve().parent.parent
PATTERNS_DIR = SKILL_ROOT / "assets" / "patterns"
LIB_PATH = SKILL_ROOT / "scripts" / "lib" / "pattern_registry.py"

EXPECTED_PATTERN_IDS = [
    "architecture_layers",
    "before_after",
    "conclusion_top_modules",
    "cover",
    "evidence_grid",
    "four_card_matrix",
    "freeform",
    "kpi_strip",
    "section_divider",
    "summary_takeaways",
    "three_stage_path",
    "two_column_compare",
]


def _load_module():
    name = "pattern_registry"
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, LIB_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


registry_mod = _load_module()


@pytest.fixture(scope="module")
def registry():
    return registry_mod.PatternRegistry(PATTERNS_DIR)


def test_loads_all_twelve_patterns(registry):
    assert registry.list_ids() == EXPECTED_PATTERN_IDS
    assert len(registry) == 12


def test_every_pattern_has_required_slots(registry):
    for pattern_id in EXPECTED_PATTERN_IDS:
        pattern = registry.get(pattern_id)
        assert pattern.slots, f"{pattern_id} has no slots"


def test_every_pattern_has_title_and_content_regions(registry):
    for pattern_id in EXPECTED_PATTERN_IDS:
        pattern = registry.get(pattern_id)
        assert "title" in pattern.layout_regions
        assert "content" in pattern.layout_regions


def test_every_pattern_has_renderer_path(registry):
    for pattern_id in EXPECTED_PATTERN_IDS:
        pattern = registry.get(pattern_id)
        assert pattern.js_renderer == f"slides/renderers/{pattern_id}.js"


def test_every_pattern_has_nonempty_wireframe(registry):
    for pattern_id in EXPECTED_PATTERN_IDS:
        pattern = registry.get(pattern_id)
        assert "<svg" in pattern.wireframe_template


def test_every_pattern_has_at_least_one_required_slot(registry):
    for pattern_id in EXPECTED_PATTERN_IDS:
        pattern = registry.get(pattern_id)
        assert pattern.required_slot_names(), f"{pattern_id} has no required slots"


def test_pattern_layout_regions_within_canvas(registry):
    for pattern_id in EXPECTED_PATTERN_IDS:
        pattern = registry.get(pattern_id)
        for name, region in pattern.layout_regions.items():
            assert region["x"] + region["w"] <= 13.334, f"{pattern_id}.{name} exceeds width"
            assert region["y"] + region["h"] <= 7.501, f"{pattern_id}.{name} exceeds height"


def test_pattern_title_and_content_regions_do_not_overlap(registry):
    for pattern_id in EXPECTED_PATTERN_IDS:
        pattern = registry.get(pattern_id)
        title = pattern.layout_regions["title"]
        content = pattern.layout_regions["content"]
        title_bottom = title["y"] + title["h"]
        content_top = content["y"]
        assert title_bottom <= content_top + 1e-6, (
            f"{pattern_id}: title region (bottom={title_bottom}) overlaps content (top={content_top})"
        )


def test_validate_slots_for_minimal_required_input(registry):
    """For each pattern, supply just the required slots and ensure validation passes."""

    sample_value_for = {
        "section_no": "01",
        "kpi_1_unit": "%",
    }

    for pattern_id in EXPECTED_PATTERN_IDS:
        pattern = registry.get(pattern_id)
        slots = {}
        for slot in pattern.slots:
            if not slot.required:
                continue
            value = sample_value_for.get(slot.name, "x")
            if slot.max_chars is not None and len(value) > slot.max_chars:
                value = value[: slot.max_chars]
            slots[slot.name] = value
        errors = registry.validate_slots(pattern_id, slots)
        assert errors == [], f"{pattern_id}: {errors}"
