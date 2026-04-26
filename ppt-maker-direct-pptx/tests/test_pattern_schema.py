"""Validate the pattern schema accepts the minimal fixture and rejects malformed docs."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, ValidationError

SKILL_ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = SKILL_ROOT / "assets" / "schemas" / "pattern.schema.json"
FIXTURE_PATH = SKILL_ROOT / "tests" / "fixtures" / "pattern_minimal.json"


@pytest.fixture(scope="module")
def validator() -> Draft202012Validator:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


@pytest.fixture
def minimal_pattern() -> dict:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def test_minimal_pattern_validates(validator, minimal_pattern):
    errors = sorted(validator.iter_errors(minimal_pattern), key=lambda e: list(e.path))
    assert not errors, "\n".join(f"{list(e.path)}: {e.message}" for e in errors)


def test_pattern_id_must_be_snake_case(validator, minimal_pattern):
    minimal_pattern["pattern_id"] = "FourCardMatrix"
    with pytest.raises(ValidationError):
        validator.validate(minimal_pattern)


def test_layout_regions_requires_title_and_content(validator, minimal_pattern):
    del minimal_pattern["layout_regions"]["title"]
    with pytest.raises(ValidationError):
        validator.validate(minimal_pattern)


def test_layout_region_must_be_in_canvas(validator, minimal_pattern):
    minimal_pattern["layout_regions"]["content"]["w"] = 99.0
    with pytest.raises(ValidationError):
        validator.validate(minimal_pattern)


def test_slot_must_declare_required_flag(validator, minimal_pattern):
    minimal_pattern["slots"][0] = {"name": "headline", "max_chars": 80}
    with pytest.raises(ValidationError):
        validator.validate(minimal_pattern)


def test_js_renderer_path_constrained(validator, minimal_pattern):
    minimal_pattern["js_renderer"] = "elsewhere/anything.js"
    with pytest.raises(ValidationError):
        validator.validate(minimal_pattern)


def test_unknown_slot_field_rejected(validator, minimal_pattern):
    minimal_pattern["slots"][0]["unexpected_field"] = "x"
    with pytest.raises(ValidationError):
        validator.validate(minimal_pattern)


def test_slots_required_at_least_one(validator, minimal_pattern):
    minimal_pattern["slots"] = []
    with pytest.raises(ValidationError):
        validator.validate(minimal_pattern)
