"""Cover dashboard aggregation: HTML/markdown formats, ordering, warnings."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

SKILL_ROOT = Path(__file__).resolve().parent.parent
SCRIPT_PATH = SKILL_ROOT / "scripts" / "preview_dashboard.py"


def _load_module():
    name = "preview_dashboard"
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


dashboard = _load_module()


def _intents_file(tmp_path: Path) -> Path:
    payload = {
        "slides": [
            {
                "page_no": 1,
                "title": "封面",
                "pattern_id": "cover",
                "intent_status": "locked",
                "slots": {
                    "title": "Quarterly Review",
                    "subtitle": "FY26 Q1",
                    "org_block": "ACME",
                },
            },
            {
                "page_no": 2,
                "title": "KPI",
                "pattern_id": "kpi_strip",
                "intent_status": "pending_review",
                "slots": {
                    "kpi_1_value": "+38%",
                    "kpi_1_label": "x" * 100,  # over max_chars
                    "kpi_2_value": "12k",
                    "kpi_2_label": "MAU",
                },
            },
        ]
    }
    path = tmp_path / "slide_prompts.json"
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return path


def test_html_includes_page_titles_and_pattern_ids(tmp_path):
    out = dashboard.build_dashboard(
        _intents_file(tmp_path), master_style=None, output_format="html"
    )
    assert "<!doctype html>" in out
    assert "封面" in out
    assert "pattern=kpi_strip" in out
    assert "Page Dashboard" not in out  # exact title check below
    assert "Preview Dashboard" in out


def test_html_includes_warnings_for_oversize_slot(tmp_path):
    out = dashboard.build_dashboard(
        _intents_file(tmp_path), master_style=None, output_format="html"
    )
    assert "warnings" in out
    assert "max_chars" in out


def test_markdown_format_has_h2_per_page(tmp_path):
    out = dashboard.build_dashboard(
        _intents_file(tmp_path), master_style=None, output_format="markdown"
    )
    h2_lines = [line for line in out.splitlines() if line.startswith("## ")]
    assert len(h2_lines) == 2
    assert "封面" in h2_lines[0]


def test_pages_appear_in_input_order(tmp_path):
    out = dashboard.build_dashboard(
        _intents_file(tmp_path), master_style=None, output_format="html"
    )
    assert out.find("封面") < out.find("KPI")


def test_unknown_format_raises(tmp_path):
    with pytest.raises(ValueError):
        dashboard.build_dashboard(
            _intents_file(tmp_path), master_style=None, output_format="pdf"
        )


def test_master_style_is_applied(tmp_path):
    style_path = tmp_path / "style.json"
    style_path.write_text(json.dumps({
        "color_strategy": {
            "primary_green": "#7C4DFF",
            "background": "#0F0F1F",
            "secondary_teal": "#00E5FF",
        }
    }), encoding="utf-8")
    style = json.loads(style_path.read_text(encoding="utf-8"))
    out = dashboard.build_dashboard(
        _intents_file(tmp_path), master_style=style, output_format="html"
    )
    assert "#7C4DFF" in out.upper()


def test_main_writes_default_out_html(tmp_path, capsys):
    intents = _intents_file(tmp_path)
    out = tmp_path / "dashboard.html"
    rc = dashboard.main([
        "--intents-file", str(intents),
        "--out", str(out),
    ])
    assert rc == 0
    assert out.exists()
    assert "Preview Dashboard" in out.read_text(encoding="utf-8")
