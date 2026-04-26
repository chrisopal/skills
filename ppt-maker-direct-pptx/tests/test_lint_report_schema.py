"""Validate lint_report.schema.json shape and edge cases."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, ValidationError

SKILL_ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = SKILL_ROOT / "assets" / "schemas" / "lint_report.schema.json"


@pytest.fixture(scope="module")
def validator() -> Draft202012Validator:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


@pytest.fixture
def minimal_report() -> dict:
    return {
        "ts": "2026-04-26T10:00:00Z",
        "gate": "gate_5",
        "results": [
            {
                "page_no": 4,
                "category": "layout_geometry",
                "rule": "title_body_no_overlap",
                "severity": "fail",
                "detail": "title 区与 body 区垂直重叠 0.2 inch",
                "auto_fixable": True,
            }
        ],
        "deck_level": [
            {
                "category": "style_consistency",
                "rule": "font_scale_unified",
                "severity": "pass",
            }
        ],
    }


def test_minimal_report_validates(validator, minimal_report):
    errors = sorted(validator.iter_errors(minimal_report), key=lambda e: list(e.path))
    assert not errors, "\n".join(f"{list(e.path)}: {e.message}" for e in errors)


def test_unknown_gate_rejected(validator, minimal_report):
    minimal_report["gate"] = "gate_99"
    with pytest.raises(ValidationError):
        validator.validate(minimal_report)


def test_unknown_category_rejected(validator, minimal_report):
    minimal_report["results"][0]["category"] = "vibes"
    with pytest.raises(ValidationError):
        validator.validate(minimal_report)


def test_unknown_severity_rejected(validator, minimal_report):
    minimal_report["results"][0]["severity"] = "maybe"
    with pytest.raises(ValidationError):
        validator.validate(minimal_report)


def test_result_missing_rule_rejected(validator, minimal_report):
    del minimal_report["results"][0]["rule"]
    with pytest.raises(ValidationError):
        validator.validate(minimal_report)


def test_override_records_actor_and_ts(validator, minimal_report):
    minimal_report["overrides"] = [
        {
            "page_no": 4,
            "rule": "title_body_no_overlap",
            "ts": "2026-04-26T11:00:00Z",
            "actor": "user",
            "reason": "intentional emphasis",
        }
    ]
    validator.validate(minimal_report)


def test_override_without_actor_rejected(validator, minimal_report):
    minimal_report["overrides"] = [
        {
            "page_no": 4,
            "rule": "title_body_no_overlap",
            "ts": "2026-04-26T11:00:00Z",
        }
    ]
    with pytest.raises(ValidationError):
        validator.validate(minimal_report)


def test_unknown_top_level_field_rejected(validator, minimal_report):
    minimal_report["surprise"] = True
    with pytest.raises(ValidationError):
        validator.validate(minimal_report)


def test_deck_level_optional(validator):
    report = {
        "ts": "2026-04-26T10:00:00Z",
        "gate": "gate_4",
        "results": [],
    }
    Draft202012Validator(json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))).validate(report)
