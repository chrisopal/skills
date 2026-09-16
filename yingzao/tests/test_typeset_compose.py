#!/usr/bin/env python3
"""Regression tests for deterministic typeset-guide gates."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "typeset_compose.py"
FONT_CANDIDATES = [
    Path("/System/Library/Fonts/Supplemental/Arial.ttf"),
    Path("/System/Library/Fonts/Supplemental/Arial Unicode.ttf"),
    Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
]


def available_font() -> Path:
    for candidate in FONT_CANDIDATES:
        if candidate.is_file():
            return candidate
    raise unittest.SkipTest("no deterministic test font found")


def latin_only_font() -> Path:
    candidates = [
        Path("/System/Library/Fonts/Supplemental/Arial.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    raise unittest.SkipTest("no deterministic Latin-only test font found")


def chinese_font() -> Path:
    candidates = [
        Path("/System/Library/Fonts/Supplemental/Songti.ttc"),
        Path("/System/Library/Fonts/STHeiti Medium.ttc"),
        Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"),
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    raise unittest.SkipTest("no deterministic CJK test font found")


class TypesetComposeGateTests(unittest.TestCase):
    def run_spec(self, spec: dict) -> tuple[subprocess.CompletedProcess[str], dict]:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            spec_path = root / "spec.json"
            report_path = root / "report.json"
            output_path = root / "guide.png"
            spec_path.write_text(json.dumps(spec), encoding="utf-8")
            completed = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "blank",
                    str(spec_path),
                    str(output_path),
                    "--report",
                    str(report_path),
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            return completed, json.loads(report_path.read_text(encoding="utf-8"))

    def crossing_rule_spec(self) -> dict:
        return {
            "mode": "typeset-guide",
            "canvas": [640, 360],
            "background": "#F3EFE6",
            "primitives": [
                {
                    "id": "bad-rule",
                    "type": "line",
                    "points": [[0, 140], [640, 140]],
                    "stroke": "#111111",
                    "width_px": 3,
                }
            ],
            "layers": [
                {
                    "id": "display-title",
                    "role": "display",
                    "glyph_design_mode": "literal",
                    "text": "TEST TITLE",
                    "font": str(available_font()),
                    "size_px": 64,
                    "x": 72,
                    "y": 92,
                    "fill": "#111111",
                }
            ],
            "alignment_groups": [],
        }

    def test_rule_crossing_text_exclusion_fails(self) -> None:
        completed, report = self.run_spec(self.crossing_rule_spec())
        self.assertNotEqual(completed.returncode, 0)
        self.assertFalse(report["passed"])
        self.assertTrue(any("intersects text exclusion zone" in error for error in report["errors"]))
        self.assertEqual(report["primitive_text_intersections"][0]["allowed"], False)

    def test_registered_primitive_text_overlap_passes(self) -> None:
        spec = self.crossing_rule_spec()
        spec["overlap_contracts"] = [
            {
                "id": "rule-through-title",
                "primitive": "bad-rule",
                "text": "display-title",
                "reason": "Regression fixture: explicitly test the contract path.",
                "z_order": "rule-behind-text",
            }
        ]
        completed, report = self.run_spec(spec)
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        self.assertTrue(report["passed"])
        self.assertEqual(report["primitive_text_intersections"][0]["contract_id"], "rule-through-title")
        self.assertEqual(report["overlap_contracts"][0]["used"], True)

    def test_text_behind_subject_rejects_an_ordinary_rule(self) -> None:
        spec = self.crossing_rule_spec()
        spec["layers"][0]["layer"] = "behind_subject"
        spec["overlap_contracts"] = [
            {
                "id": "false-subject-overlap",
                "primitive": "bad-rule",
                "text": "display-title",
                "reason": "A line must not impersonate the subject silhouette.",
                "z_order": "text-behind-subject",
            }
        ]
        completed, report = self.run_spec(spec)
        self.assertNotEqual(completed.returncode, 0)
        self.assertTrue(any("requires a subject_front primitive" in error for error in report["errors"]))

    def test_subject_footprint_can_prove_text_occlusion_without_external_mask(self) -> None:
        spec = self.crossing_rule_spec()
        spec["primitives"] = [
            {
                "id": "traced-subject-footprint",
                "type": "polygon",
                "role": "subject-footprint",
                "layer": "subject_front",
                "guide_marker": "S1",
                "guide_label": "REAL SUBJECT",
                "points": [[0.05, 0.30], [0.95, 0.30], [0.88, 0.72], [0.12, 0.72]],
                "fill": "#60645F",
                "opacity": 72,
            }
        ]
        spec["layers"][0]["layer"] = "behind_subject"
        spec["layers"][0]["guide_marker"] = "T1"
        spec["layers"][0]["guide_label"] = "DISPLAY TITLE"
        spec["overlap_contracts"] = [
            {
                "id": "roof-cuts-title",
                "primitive": "traced-subject-footprint",
                "text": "display-title",
                "reason": "The traced roof mass must visibly cut the display title in the guide.",
                "z_order": "text-behind-subject",
            }
        ]
        completed, report = self.run_spec(spec)
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        self.assertTrue(report["passed"])
        primitive = report["primitives"][0]
        self.assertEqual(primitive["layer"], "subject_front")
        self.assertEqual(primitive["role"], "subject-footprint")
        self.assertEqual(primitive["guide_marker"], "S1")
        self.assertEqual(report["layers"][0]["guide_marker"], "T1")
        self.assertEqual([item["id"] for item in report["guide_markers"]], ["S1", "T1"])
        self.assertTrue(report["overlap_contracts"][0]["used"])

    def test_guide_marker_requires_a_portable_ascii_label(self) -> None:
        spec = self.crossing_rule_spec()
        spec["primitives"] = []
        spec["layers"][0]["guide_marker"] = "T1"
        spec["layers"][0]["guide_label"] = "展示标题"
        completed, report = self.run_spec(spec)
        self.assertNotEqual(completed.returncode, 0)
        self.assertTrue(any("printable ASCII" in error for error in report["errors"]))

    def test_display_layout_alignment_requires_reason(self) -> None:
        spec = {
            "mode": "typeset-guide",
            "canvas": [900, 420],
            "background": "#FFFFFF",
            "layers": [
                {
                    "id": "display-title",
                    "role": "display",
                    "glyph_design_mode": "literal",
                    "text": "TITLE",
                    "font": str(available_font()),
                    "size_px": 72,
                    "x": 80,
                    "y": 70,
                },
                {
                    "id": "metadata",
                    "role": "metadata",
                    "text": "METADATA",
                    "font": str(available_font()),
                    "size_px": 28,
                    "x": 80,
                    "y": 250,
                },
            ],
            "alignment_groups": [
                {
                    "id": "left-axis",
                    "axis": "left",
                    "basis": "layout",
                    "members": ["display-title", "metadata"],
                }
            ],
        }
        completed, report = self.run_spec(spec)
        self.assertNotEqual(completed.returncode, 0)
        self.assertTrue(any("basis=layout requires layout_reason" in error for error in report["errors"]))

        allowed = deepcopy(spec)
        allowed["alignment_groups"][0]["layout_reason"] = "The parent grid locks nominal boxes by contract."
        completed, report = self.run_spec(allowed)
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        self.assertTrue(report["alignment_groups"][0]["display_group"])

    def test_multiline_baseline_report_names_first_line(self) -> None:
        spec = {
            "mode": "typeset-guide",
            "canvas": [900, 420],
            "background": "#FFFFFF",
            "layers": [
                {
                    "id": "facts-a",
                    "role": "metadata",
                    "text": "FIRST\nSECOND",
                    "font": str(available_font()),
                    "size_px": 28,
                    "line_height_px": 48,
                    "x": 80,
                    "y": 80,
                },
                {
                    "id": "facts-b",
                    "role": "metadata",
                    "text": "ALPHA\nBETA",
                    "font": str(available_font()),
                    "size_px": 28,
                    "line_height_px": 48,
                    "x": 520,
                    "y": 80,
                },
            ],
            "alignment_groups": [
                {
                    "id": "first-baseline",
                    "axis": "baseline",
                    "basis": "ink",
                    "members": ["facts-a", "facts-b"],
                }
            ],
        }
        completed, report = self.run_spec(spec)
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        self.assertEqual(report["layers"][0]["line_count"], 2)
        self.assertEqual(len(report["layers"][0]["baseline_ys"]), 2)
        self.assertEqual(report["layers"][0]["baseline_y"], report["layers"][0]["baseline_y_first"])

    def test_missing_chinese_cmap_fails_instead_of_accepting_notdef(self) -> None:
        spec = {
            "mode": "typeset-guide",
            "canvas": [640, 360],
            "background": "#FFFFFF",
            "layers": [
                {
                    "id": "display-title",
                    "role": "display",
                    "glyph_design_mode": "literal",
                    "text": "飞檐",
                    "font": str(latin_only_font()),
                    "size_px": 72,
                    "x": 80,
                    "y": 80,
                }
            ],
            "alignment_groups": [],
        }
        completed, report = self.run_spec(spec)
        self.assertNotEqual(completed.returncode, 0)
        self.assertFalse(report["layers"][0]["font_coverage"]["passed"])
        self.assertEqual(report["layers"][0]["fallback"], True)
        self.assertTrue(any("font does not cover" in error for error in report["errors"]))

    def test_cjk_font_passes_character_coverage(self) -> None:
        spec = {
            "mode": "typeset-guide",
            "canvas": [640, 360],
            "background": "#FFFFFF",
            "layers": [
                {
                    "id": "display-title",
                    "role": "display",
                    "glyph_design_mode": "literal",
                    "text": "飞檐",
                    "font": str(chinese_font()),
                    "size_px": 72,
                    "x": 80,
                    "y": 80,
                }
            ],
            "alignment_groups": [],
        }
        completed, report = self.run_spec(spec)
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        self.assertTrue(report["layers"][0]["font_coverage"]["passed"])
        self.assertFalse(report["layers"][0]["fallback"])

    def test_display_guide_requires_explicit_glyph_mode(self) -> None:
        spec = {
            "mode": "typeset-guide",
            "canvas": [640, 360],
            "background": "#FFFFFF",
            "layers": [
                {
                    "id": "display-title",
                    "role": "display",
                    "text": "TITLE",
                    "font": str(available_font()),
                    "size_px": 72,
                    "x": 80,
                    "y": 80,
                }
            ],
            "alignment_groups": [],
        }
        completed, report = self.run_spec(spec)
        self.assertNotEqual(completed.returncode, 0)
        self.assertTrue(any("require glyph_design_mode" in error for error in report["errors"]))

    def test_reinterpret_guide_uses_scaffold_instead_of_stock_silhouette(self) -> None:
        spec = {
            "mode": "typeset-guide",
            "canvas": [640, 360],
            "background": "#FFFFFF",
            "layers": [
                {
                    "id": "display-title",
                    "role": "display",
                    "glyph_design_mode": "reinterpret",
                    "guide_render": "scaffold",
                    "text": "飞檐",
                    "font": str(chinese_font()),
                    "size_px": 96,
                    "x": 80,
                    "y": 80,
                }
            ],
            "alignment_groups": [],
        }
        completed, report = self.run_spec(spec)
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        layer = report["layers"][0]
        self.assertEqual(layer["glyph_design_mode"], "reinterpret")
        self.assertEqual(layer["guide_render"], "scaffold")

        stock = deepcopy(spec)
        stock["layers"][0].pop("guide_render")
        completed, report = self.run_spec(stock)
        self.assertNotEqual(completed.returncode, 0)
        self.assertTrue(any("require guide_render=scaffold" in error for error in report["errors"]))

    def test_title_substring_does_not_override_metadata_role(self) -> None:
        spec = {
            "mode": "typeset-guide",
            "canvas": [640, 360],
            "background": "#FFFFFF",
            "layers": [
                {
                    "id": "subtitle-pinyin",
                    "role": "metadata",
                    "text": "DATONG",
                    "font": str(available_font()),
                    "size_px": 40,
                    "x": 80,
                    "y": 80,
                }
            ],
            "alignment_groups": [],
        }
        completed, report = self.run_spec(spec)
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        layer = report["layers"][0]
        self.assertFalse(layer["display_layer"])
        self.assertGreaterEqual(layer["primitive_exclusion_padding_px"], 20)

    def test_vertical_text_requires_explicit_reading_order(self) -> None:
        spec = {
            "mode": "typeset-guide",
            "canvas": [640, 360],
            "background": "#FFFFFF",
            "layers": [
                {
                    "id": "vertical-place",
                    "role": "metadata",
                    "text": "DATONG",
                    "font": str(available_font()),
                    "size_px": 36,
                    "x": 80,
                    "y": 40,
                    "orientation": "vertical",
                }
            ],
            "alignment_groups": [],
        }
        completed, report = self.run_spec(spec)
        self.assertNotEqual(completed.returncode, 0)
        self.assertTrue(any("vertical_order=top-to-bottom" in error for error in report["errors"]))

        allowed = deepcopy(spec)
        allowed["layers"][0]["vertical_order"] = "top-to-bottom"
        completed, report = self.run_spec(allowed)
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        self.assertEqual(report["layers"][0]["vertical_order"], "top-to-bottom")


if __name__ == "__main__":
    unittest.main()
