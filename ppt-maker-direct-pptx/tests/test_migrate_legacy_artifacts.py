"""Verify the legacy artifact migrator adds defaults and is idempotent."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

import pytest

SKILL_ROOT = Path(__file__).resolve().parent.parent
SCRIPT_PATH = SKILL_ROOT / "scripts" / "migrate_legacy_artifacts.py"


def _load_module():
    name = "migrate_legacy_artifacts"
    spec = importlib.util.spec_from_file_location(name, SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


migrator = _load_module()


def _write(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _read(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture
def legacy_artifacts(tmp_path: Path) -> Path:
    artifacts = tmp_path / "artifacts"
    artifacts.mkdir()
    _write(
        artifacts / "outline.json",
        {
            "storyline": "demo",
            "slides": [
                {"page_no": 1, "title": "封面"},
                {"page_no": 2, "title": "目录"},
            ],
        },
    )
    _write(
        artifacts / "slide_prompts.json",
        {
            "slides": [
                {
                    "page_no": 1,
                    "title": "封面",
                    "page_goal": "建立场景",
                    "layout_type": "cover",
                    "key_blocks": [],
                    "compiled_prompt": "draw cover",
                },
                {
                    "page_no": 2,
                    "title": "目录",
                    "page_goal": "导航",
                    "layout_type": "agenda",
                    "key_blocks": [],
                    "compiled_prompt": "draw agenda",
                },
            ],
            "quality_checklist": {},
        },
    )
    _write(
        artifacts / "slide_specs.json",
        {
            "slides": [
                {
                    "page_no": 5,
                    "title": "效率",
                    "visible_content": {
                        "title": "效率",
                        "blocks": [],
                        "image_placeholders": [],
                        "image_assets": [],
                    },
                    "image_placeholders": [
                        {"prompt": "factory floor"},
                        {"prompt": "team photo"},
                    ],
                    "image_assets": [],
                    "layout_regions": {"content": {}, "images": {}, "mode": "auto"},
                    "template_variant": {},
                    "script_path": "slides/slide-05.js",
                }
            ]
        },
    )
    return artifacts


def test_migrate_adds_outline_status(legacy_artifacts):
    migrator.migrate_directory(legacy_artifacts)
    outline = _read(legacy_artifacts / "outline.json")
    for slide in outline["slides"]:
        assert slide["outline_status"] == "draft"


def test_migrate_adds_intent_status_and_layout_mode(legacy_artifacts):
    migrator.migrate_directory(legacy_artifacts)
    prompts = _read(legacy_artifacts / "slide_prompts.json")
    for slide in prompts["slides"]:
        assert slide["intent_status"] == "draft"
        assert slide["layout_mode"] == "custom"


def test_migrate_adds_image_placeholder_status(legacy_artifacts):
    migrator.migrate_directory(legacy_artifacts)
    specs = _read(legacy_artifacts / "slide_specs.json")
    placeholders = specs["slides"][0]["image_placeholders"]
    assert all(p["status"] == "placeholder" for p in placeholders)


def test_migrate_is_idempotent(legacy_artifacts):
    first = migrator.migrate_directory(legacy_artifacts)
    second = migrator.migrate_directory(legacy_artifacts)
    assert any(r.changed for r in first)
    assert all(not r.changed for r in second)


def test_dry_run_does_not_write(legacy_artifacts):
    before = (legacy_artifacts / "outline.json").read_text(encoding="utf-8")
    results = migrator.migrate_directory(legacy_artifacts, dry_run=True)
    after = (legacy_artifacts / "outline.json").read_text(encoding="utf-8")
    assert before == after
    assert any(r.additions > 0 for r in results)


def test_already_migrated_artifacts_unchanged(legacy_artifacts):
    migrator.migrate_directory(legacy_artifacts)
    snapshot = {
        f.name: f.read_text(encoding="utf-8")
        for f in legacy_artifacts.iterdir()
    }
    migrator.migrate_directory(legacy_artifacts)
    after = {
        f.name: f.read_text(encoding="utf-8")
        for f in legacy_artifacts.iterdir()
    }
    assert snapshot == after


def test_missing_directory_raises(tmp_path):
    with pytest.raises(NotADirectoryError):
        migrator.migrate_directory(tmp_path / "does_not_exist")


def test_partial_directory_processed(tmp_path):
    artifacts = tmp_path / "artifacts"
    artifacts.mkdir()
    _write(artifacts / "outline.json", {"slides": [{"page_no": 1, "title": "a"}]})
    results = migrator.migrate_directory(artifacts)
    assert {r.file for r in results} == {"outline.json"}
    assert results[0].changed is True


def test_cli_dry_run(legacy_artifacts, capsys):
    exit_code = migrator.main([str(legacy_artifacts), "--dry-run"])
    captured = capsys.readouterr()
    assert exit_code == 0
    assert "[dry-run]" in captured.out
    # No file was modified by dry-run
    outline = _read(legacy_artifacts / "outline.json")
    assert "outline_status" not in outline["slides"][0]
