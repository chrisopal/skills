"""Cover lock_pages, reset_pages, and regenerate_image CLIs."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

SKILL_ROOT = Path(__file__).resolve().parent.parent


def _load_module(name: str, rel_path: str):
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, SKILL_ROOT / rel_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


lock_mod = _load_module("lock_pages", "scripts/lock_pages.py")
reset_mod = _load_module("reset_pages", "scripts/reset_pages.py")
regen_mod = _load_module("regenerate_image", "scripts/regenerate_image.py")


def _outline(*pages) -> dict:
    return {"slides": [{"page_no": p, "title": f"page {p}", "outline_status": "draft"} for p in pages]}


def _slide_prompts(*pages) -> dict:
    return {
        "slides": [
            {
                "page_no": p,
                "title": f"page {p}",
                "page_goal": "demo",
                "layout_type": "cover",
                "key_blocks": [],
                "compiled_prompt": "draw",
                "intent_status": "draft",
            }
            for p in pages
        ],
        "quality_checklist": {},
    }


def _slide_specs_with_image(page_no: int, img_id: str = "page-05-img-1", status: str = "placeholder") -> dict:
    return {
        "slides": [{
            "page_no": page_no,
            "title": "demo",
            "visible_content": {"title": "demo", "blocks": [], "image_placeholders": [], "image_assets": []},
            "image_placeholders": [{"id": img_id, "prompt": "img", "status": status}],
            "image_assets": [],
            "layout_regions": {"content": {}, "images": {}, "mode": "auto"},
            "template_variant": {},
            "script_path": f"slides/slide-{page_no:02d}.js",
        }]
    }


# ---------------------------------------------------------------------------
# parse helpers
# ---------------------------------------------------------------------------


def test_parse_pages_supports_ranges():
    assert lock_mod._parse_pages("1,3-5,7") == [1, 3, 4, 5, 7]


def test_parse_pages_handles_whitespace():
    assert lock_mod._parse_pages(" 2 , 4 - 6 , 9 ") == [2, 4, 5, 6, 9]


# ---------------------------------------------------------------------------
# lock_pages CLI
# ---------------------------------------------------------------------------


def test_lock_pages_outline_layer_writes_artifact(tmp_path):
    outline = _outline(1, 2, 3)
    path = tmp_path / "outline.json"
    path.write_text(json.dumps(outline), encoding="utf-8")
    rc = lock_mod.main(["--pages", "1,2", "--layer", "outline", "--outline", str(path)])
    assert rc == 0
    data = json.loads(path.read_text(encoding="utf-8"))
    statuses = {s["page_no"]: s["outline_status"] for s in data["slides"]}
    assert statuses[1] == "locked"
    assert statuses[2] == "locked"
    assert statuses[3] == "draft"


def test_lock_pages_intent_layer_blocked_when_outline_not_locked(tmp_path):
    outline_path = tmp_path / "outline.json"
    outline_path.write_text(json.dumps(_outline(1)), encoding="utf-8")
    prompts_path = tmp_path / "slide_prompts.json"
    prompts_path.write_text(json.dumps(_slide_prompts(1)), encoding="utf-8")

    with pytest.raises(Exception):  # IllegalTransitionError
        lock_mod.main([
            "--pages", "1", "--layer", "intent",
            "--outline", str(outline_path), "--slide-prompts", str(prompts_path),
        ])


def test_lock_pages_intent_layer_works_after_outline_locked(tmp_path):
    outline = _outline(1)
    outline["slides"][0]["outline_status"] = "locked"
    outline_path = tmp_path / "outline.json"
    outline_path.write_text(json.dumps(outline), encoding="utf-8")
    prompts_path = tmp_path / "slide_prompts.json"
    prompts_path.write_text(json.dumps(_slide_prompts(1)), encoding="utf-8")

    rc = lock_mod.main([
        "--pages", "1", "--layer", "intent",
        "--outline", str(outline_path), "--slide-prompts", str(prompts_path),
    ])
    assert rc == 0
    prompts = json.loads(prompts_path.read_text(encoding="utf-8"))
    assert prompts["slides"][0]["intent_status"] == "locked"


# ---------------------------------------------------------------------------
# reset_pages CLI
# ---------------------------------------------------------------------------


def test_reset_pages_locked_to_needs_rework(tmp_path):
    outline = _outline(1, 2)
    outline["slides"][0]["outline_status"] = "locked"
    outline["slides"][1]["outline_status"] = "locked"
    path = tmp_path / "outline.json"
    path.write_text(json.dumps(outline), encoding="utf-8")
    rc = reset_mod.main(["--pages", "1", "--layer", "outline", "--outline", str(path)])
    assert rc == 0
    data = json.loads(path.read_text(encoding="utf-8"))
    statuses = {s["page_no"]: s["outline_status"] for s in data["slides"]}
    assert statuses[1] == "needs_rework"
    assert statuses[2] == "locked"


def test_reset_pages_skips_draft(tmp_path):
    outline = _outline(1)
    path = tmp_path / "outline.json"
    path.write_text(json.dumps(outline), encoding="utf-8")
    rc = reset_mod.main(["--pages", "1", "--layer", "outline", "--outline", str(path)])
    assert rc == 0
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["slides"][0]["outline_status"] == "draft"


# ---------------------------------------------------------------------------
# regenerate_image CLI
# ---------------------------------------------------------------------------


def test_regenerate_image_targets_specific_id(tmp_path):
    specs = _slide_specs_with_image(5, img_id="page-05-img-1")
    specs["slides"][0]["image_placeholders"].append({
        "id": "page-05-img-2", "prompt": "img2", "status": "placeholder",
    })
    path = tmp_path / "slide_specs.json"
    path.write_text(json.dumps(specs), encoding="utf-8")
    rc = regen_mod.main([
        "--slide-specs", str(path), "--slide", "5", "--img-id", "page-05-img-1",
    ])
    assert rc == 0
    data = json.loads(path.read_text(encoding="utf-8"))
    placeholders = data["slides"][0]["image_placeholders"]
    statuses = {p["id"]: p["status"] for p in placeholders}
    assert statuses["page-05-img-1"] == "regenerating"
    assert statuses["page-05-img-2"] == "placeholder"


def test_regenerate_image_records_history(tmp_path):
    specs = _slide_specs_with_image(5, status="generated")
    path = tmp_path / "slide_specs.json"
    path.write_text(json.dumps(specs), encoding="utf-8")
    regen_mod.main([
        "--slide-specs", str(path), "--slide", "5", "--reason", "user wants different style",
    ])
    data = json.loads(path.read_text(encoding="utf-8"))
    history = data["slides"][0]["image_placeholders"][0]["history"]
    assert len(history) == 1
    assert history[0]["from"] == "generated"
    assert history[0]["to"] == "regenerating"
    assert "different style" in history[0]["reason"]


def test_regenerate_image_returns_2_when_no_match(tmp_path):
    specs = _slide_specs_with_image(5, img_id="exists")
    path = tmp_path / "slide_specs.json"
    path.write_text(json.dumps(specs), encoding="utf-8")
    rc = regen_mod.main([
        "--slide-specs", str(path), "--slide", "5", "--img-id", "does-not-exist",
    ])
    assert rc == 2
