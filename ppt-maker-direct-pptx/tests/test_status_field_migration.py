"""Verify status fields are accepted on extended schemas without breaking legacy artifacts.

Phase 1 / Task 1.5. The new fields (outline_status, intent_status,
image_placeholder.status, layout_mode, pattern_id, slots) must:

1. Be accepted when present with valid values
2. Be optional so legacy artifacts (without them) still validate
3. Be rejected when set to invalid enum values
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, ValidationError

SKILL_ROOT = Path(__file__).resolve().parent.parent
SCHEMAS_DIR = SKILL_ROOT / "assets" / "schemas"


def _validator(name: str) -> Draft202012Validator:
    schema = json.loads((SCHEMAS_DIR / name).read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


# ---------------------------------------------------------------------------
# outline.schema.json — outline_status
# ---------------------------------------------------------------------------


@pytest.fixture
def outline_legacy() -> dict:
    return {
        "storyline": "demo",
        "slides": [
            {"page_no": 1, "title": "封面"},
            {"page_no": 2, "title": "目录"},
        ],
    }


def test_legacy_outline_validates(outline_legacy):
    _validator("outline.schema.json").validate(outline_legacy)


def test_outline_with_status_validates(outline_legacy):
    outline_legacy["slides"][0]["outline_status"] = "locked"
    outline_legacy["slides"][1]["outline_status"] = "draft"
    _validator("outline.schema.json").validate(outline_legacy)


def test_outline_invalid_status_rejected(outline_legacy):
    outline_legacy["slides"][0]["outline_status"] = "kinda_done"
    with pytest.raises(ValidationError):
        _validator("outline.schema.json").validate(outline_legacy)


# ---------------------------------------------------------------------------
# slide_prompts.schema.json — intent_status, pattern_id, layout_mode, slots
# ---------------------------------------------------------------------------


@pytest.fixture
def prompts_legacy() -> dict:
    return {
        "slides": [
            {
                "page_no": 1,
                "title": "封面",
                "page_goal": "建立场景",
                "layout_type": "cover",
                "key_blocks": [],
                "compiled_prompt": "draw cover",
            }
        ],
        "quality_checklist": {},
    }


def test_legacy_slide_prompts_validates(prompts_legacy):
    _validator("slide_prompts.schema.json").validate(prompts_legacy)


def test_slide_prompts_with_pattern_fields_validates(prompts_legacy):
    slide = prompts_legacy["slides"][0]
    slide["intent_status"] = "pending_review"
    slide["pattern_id"] = "four_card_matrix"
    slide["layout_mode"] = "pattern"
    slide["slots"] = {"cell_1": {"label": "ROI", "value": "+38%"}}
    _validator("slide_prompts.schema.json").validate(prompts_legacy)


def test_slide_prompts_invalid_layout_mode_rejected(prompts_legacy):
    prompts_legacy["slides"][0]["layout_mode"] = "wild"
    with pytest.raises(ValidationError):
        _validator("slide_prompts.schema.json").validate(prompts_legacy)


def test_slide_prompts_invalid_pattern_id_rejected(prompts_legacy):
    prompts_legacy["slides"][0]["pattern_id"] = "FourCardMatrix"
    with pytest.raises(ValidationError):
        _validator("slide_prompts.schema.json").validate(prompts_legacy)


# ---------------------------------------------------------------------------
# slide_specs.schema.json — image_placeholders[].status, history
# ---------------------------------------------------------------------------


@pytest.fixture
def specs_legacy() -> dict:
    return {
        "slides": [
            {
                "page_no": 5,
                "title": "效率提升",
                "visible_content": {
                    "title": "效率提升",
                    "blocks": [],
                    "image_placeholders": [],
                    "image_assets": [],
                },
                "image_placeholders": [
                    {"prompt": "a factory floor"}
                ],
                "image_assets": [],
                "layout_regions": {"content": {}, "images": {}, "mode": "auto"},
                "template_variant": {},
                "script_path": "slides/slide-05.js",
            }
        ]
    }


def test_legacy_specs_validates(specs_legacy):
    _validator("slide_specs.schema.json").validate(specs_legacy)


def test_specs_with_status_and_history_validates(specs_legacy):
    placeholder = specs_legacy["slides"][0]["image_placeholders"][0]
    placeholder["status"] = "generated"
    placeholder["generated_path"] = "image-assets/page-05-img-1.png"
    placeholder["history"] = [
        {
            "ts": "2026-04-26T10:00:00Z",
            "from": "pending",
            "to": "placeholder",
        },
        {
            "ts": "2026-04-26T11:00:00Z",
            "from": "placeholder",
            "to": "generated",
            "reason": "user requested real image",
        },
    ]
    _validator("slide_specs.schema.json").validate(specs_legacy)


def test_specs_invalid_status_rejected(specs_legacy):
    specs_legacy["slides"][0]["image_placeholders"][0]["status"] = "in_progress"
    with pytest.raises(ValidationError):
        _validator("slide_specs.schema.json").validate(specs_legacy)


def test_specs_history_entry_requires_from_and_to(specs_legacy):
    placeholder = specs_legacy["slides"][0]["image_placeholders"][0]
    placeholder["history"] = [{"ts": "2026-04-26T10:00:00Z"}]
    with pytest.raises(ValidationError):
        _validator("slide_specs.schema.json").validate(specs_legacy)
