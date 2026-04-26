"""Cover the state-machine extensions to generate_image_assets.py."""

from __future__ import annotations

import importlib.util
import sys
import tempfile
from pathlib import Path
from unittest import mock

import pytest

SKILL_ROOT = Path(__file__).resolve().parent.parent


def _load_module():
    name = "generate_image_assets"
    if name in sys.modules:
        return sys.modules[name]
    sys.path.insert(0, str(SKILL_ROOT / "scripts"))
    spec = importlib.util.spec_from_file_location(name, SKILL_ROOT / "scripts" / "generate_image_assets.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


gia = _load_module()


def _specs_with_statuses(*statuses) -> dict:
    placeholders = []
    for i, status in enumerate(statuses):
        item = {
            "id": f"img_{i}",
            "role": "supporting_visual",
            "purpose": f"placeholder {i}",
            "prompt": f"prompt {i}",
            "placement": {"x": 1, "y": 1, "w": 1, "h": 1},
        }
        if status is not None:
            item["status"] = status
        placeholders.append(item)
    return {"slides": [{"page_no": 1, "image_placeholders": placeholders}]}


def test_collect_processes_all_when_legacy_mode():
    specs = _specs_with_statuses("placeholder", "generated", "skipped")
    out = gia.collect_placeholders(specs, respect_status=False)
    # Legacy: every placeholder with a non-empty prompt is collected
    assert len(out) == 3


def test_collect_filters_by_status_when_respect_status():
    specs = _specs_with_statuses("placeholder", "generated", "skipped", "pending", "regenerating")
    out = gia.collect_placeholders(specs, respect_status=True)
    statuses = {p["placeholder_id"] for p in out}
    # 'pending' (idx=3) and 'regenerating' (idx=4) only
    assert statuses == {"img_3", "img_4"}


def test_collect_target_ids_overrides_status_filter():
    specs = _specs_with_statuses("generated", "skipped")
    out = gia.collect_placeholders(specs, respect_status=True, target_ids=["img_0"])
    # respect_status would skip 'generated', but target_ids forces inclusion
    assert [p["placeholder_id"] for p in out] == ["img_0"]


def test_collect_legacy_treats_missing_status_as_actionable():
    """Items without a status field are processed in respect_status mode too."""

    specs = {"slides": [{"page_no": 1, "image_placeholders": [
        {"id": "no_status", "prompt": "p"}
    ]}]}
    out = gia.collect_placeholders(specs, respect_status=True)
    assert [p["placeholder_id"] for p in out] == ["no_status"]


def test_generate_success_marks_placeholder_generated():
    specs = _specs_with_statuses("pending")
    with tempfile.TemporaryDirectory() as tmp, mock.patch.object(gia, "generate_model_image"):
        gia.generate_assets_for_specs(
            specs, {"color_strategy": {}, "typography": {}}, {"image_model": "x"},
            Path(tmp), dry_run=False, respect_status=True,
        )
    assert specs["slides"][0]["image_placeholders"][0]["status"] == "generated"
    assert specs["slides"][0]["image_placeholders"][0]["generated_path"]


def test_generate_failure_marks_placeholder_with_fallback():
    specs = _specs_with_statuses("pending")
    with tempfile.TemporaryDirectory() as tmp, mock.patch.object(
        gia, "generate_model_image", side_effect=RuntimeError("HTTP 500"),
    ):
        gia.generate_assets_for_specs(
            specs, {"color_strategy": {}, "typography": {}}, {"image_model": "x"},
            Path(tmp), dry_run=False, respect_status=True,
        )
    item = specs["slides"][0]["image_placeholders"][0]
    assert item["status"] == "placeholder"
    assert "HTTP 500" in item["fallback_reason"]


def test_generate_dry_run_marks_status_placeholder():
    specs = _specs_with_statuses("pending")
    with tempfile.TemporaryDirectory() as tmp:
        gia.generate_assets_for_specs(
            specs, {"color_strategy": {}, "typography": {}}, {"image_model": "x"},
            Path(tmp), dry_run=True, respect_status=True,
        )
    assert specs["slides"][0]["image_placeholders"][0]["status"] == "placeholder"


def test_legacy_mode_does_not_touch_status_field():
    specs = _specs_with_statuses("pending")
    with tempfile.TemporaryDirectory() as tmp, mock.patch.object(gia, "generate_model_image"):
        gia.generate_assets_for_specs(
            specs, {"color_strategy": {}, "typography": {}}, {"image_model": "x"},
            Path(tmp), dry_run=False,  # respect_status default False
        )
    # Status untouched in legacy mode
    assert specs["slides"][0]["image_placeholders"][0].get("status") == "pending"


def test_generate_target_ids_only_processes_those():
    specs = _specs_with_statuses("pending", "pending", "pending")
    with tempfile.TemporaryDirectory() as tmp, mock.patch.object(gia, "generate_model_image") as m:
        gia.generate_assets_for_specs(
            specs, {"color_strategy": {}, "typography": {}}, {"image_model": "x"},
            Path(tmp), dry_run=False, respect_status=True, target_ids=["img_1"],
        )
    statuses = [p.get("status") for p in specs["slides"][0]["image_placeholders"]]
    assert statuses == ["pending", "generated", "pending"]
    assert m.call_count == 1
