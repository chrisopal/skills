"""Validate every existing *_master_style_brief.json against the new schema.

Phase 1 / Task 1.2: confirm the schema is permissive enough for the 5 shipped
preset briefs once each one has `source: "preset"` added, and strict enough
to reject obvious mistakes.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, ValidationError

SKILL_ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = SKILL_ROOT / "assets" / "schemas" / "master_style.schema.json"
PRESET_BRIEFS = sorted((SKILL_ROOT / "assets").glob("*_master_style_brief.json"))


@pytest.fixture(scope="module")
def validator() -> Draft202012Validator:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


@pytest.mark.parametrize("brief_path", PRESET_BRIEFS, ids=lambda p: p.name)
def test_preset_brief_validates(brief_path: Path, validator: Draft202012Validator) -> None:
    data = json.loads(brief_path.read_text(encoding="utf-8"))
    errors = sorted(validator.iter_errors(data), key=lambda e: e.path)
    assert not errors, "\n".join(
        f"{list(e.path)}: {e.message}" for e in errors
    )


def test_invalid_source_rejected(validator: Draft202012Validator) -> None:
    data = json.loads(PRESET_BRIEFS[0].read_text(encoding="utf-8"))
    data["source"] = "made_up_source"
    with pytest.raises(ValidationError):
        validator.validate(data)


def test_confidence_must_be_unit_interval(validator: Draft202012Validator) -> None:
    data = json.loads(PRESET_BRIEFS[0].read_text(encoding="utf-8"))
    data["confidence"] = {"color_strategy.primary_green": 1.5}
    with pytest.raises(ValidationError):
        validator.validate(data)


def test_unknown_top_level_field_rejected(validator: Draft202012Validator) -> None:
    data = json.loads(PRESET_BRIEFS[0].read_text(encoding="utf-8"))
    data["random_unknown_top_level"] = "boo"
    with pytest.raises(ValidationError):
        validator.validate(data)
