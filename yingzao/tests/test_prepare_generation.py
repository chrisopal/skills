#!/usr/bin/env python3
"""Regression tests for the fixed ImageGen handoff manifest."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "prepare_generation.py"


PROMPT = """Primary transformation: Extract and materially reinterpret the real subject in one editorial scene.
Image roles: Image 1 is the edit target. Image 2 is the primary visual reference. Image 3 is the spatial typeset scaffold.
Composition diagnosis: The source has no deliberate title lane.
Composition repair: Shift the connected subject once and rebuild only a continuous wall field.
Subject treatment: Extract the real subject, change its scale, and apply region-specific material treatment.
Background treatment: Build one active mineral color field with a second low-frequency material zone.
Interaction: Let one real roof edge pass in front of the title while preserving legibility.
Reference transfer: Transfer the reference's subject/background/type mechanism, not merely its palette.
Identity invariants: Preserve the plaque, roof hierarchy, doorway, and real asymmetric details.
Typography layout: Follow Image 3's title slots, shared axis, reading order, and overlap boundary.
Display glyph design: Reinterpret only “飞檐” as a locked wordmark; do not copy a stock font silhouette.
Text (verbatim): “飞檐”; “善化寺”.
Do not add: invented architecture, mirrored parts, fake inscriptions, foreign text, or UI cards.
"""


class PrepareGenerationTests(unittest.TestCase):
    def make_fixture(
        self,
        root: Path,
        *,
        guide_render: str = "scaffold",
        prompt: str = PROMPT,
        mutate_plan=None,
    ) -> list[str]:
        run_dir = root / "output" / "yingzao" / "run"
        analysis = run_dir / "analysis"
        analysis.mkdir(parents=True)
        source = root / "source.jpg"
        reference = root / "reference.jpg"
        guide = analysis / "typeset-guide.png"
        Image.new("RGB", (320, 240), "#403020").save(source)
        Image.new("RGB", (240, 320), "#203040").save(reference)
        Image.new("RGB", (640, 360), "#EEEEEC").save(guide)
        spec = analysis / "typeset-spec.json"
        spec.write_text(
            json.dumps(
                {
                    "mode": "typeset-guide",
                    "canvas": [640, 360],
                    "primitives": [
                        {
                            "id": "active-background",
                            "type": "rect",
                            "bbox": [0, 0, 640, 360],
                            "guide_marker": "B1",
                            "guide_label": "ACTIVE BACKGROUND",
                        },
                        {
                            "id": "subject-footprint",
                            "type": "polygon",
                            "points": [[80, 130], [560, 130], [520, 320], [120, 320]],
                            "guide_marker": "S1",
                            "guide_label": "REAL SUBJECT",
                        },
                    ],
                    "layers": [
                        {
                            "id": "display-title",
                            "role": "display",
                            "text": "飞檐",
                            "glyph_design_mode": "reinterpret",
                            "guide_render": guide_render,
                            "guide_marker": "T1",
                            "guide_label": "DISPLAY TITLE",
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )
        report = analysis / "typeset-report.json"
        report.write_text(
            json.dumps(
                {
                    "passed": True,
                    "canvas": [640, 360],
                    "primitives": [
                        {
                            "id": "active-background",
                            "guide_marker": "B1",
                            "guide_label": "ACTIVE BACKGROUND",
                        },
                        {
                            "id": "subject-footprint",
                            "guide_marker": "S1",
                            "guide_label": "REAL SUBJECT",
                        },
                    ],
                    "layers": [
                        {
                            "id": "display-title",
                            "guide_marker": "T1",
                            "guide_label": "DISPLAY TITLE",
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )
        recipe = analysis / "recipe.json"
        token_rows = [
            {"id": "cap.subject.identity", "category": "subject", "label": "真实主体"},
            {"id": "cap.background.active", "category": "background", "label": "主动背景"},
            {"id": "cap.type.display", "category": "typography", "label": "展示字"},
            {"id": "cap.depth.occlusion", "category": "depth", "label": "主体压字"},
            {"id": "cap.subject.preflight-rectification", "category": "subject", "label": "入版校正"},
        ]
        recipe.write_text(
            json.dumps(
                {
                    "id": "cap.recipe.test",
                    "resolved_tokens": token_rows,
                    "optional": [],
                    "optional_tokens": [],
                    "forbidden": [],
                    "errors": [],
                }
            ),
            encoding="utf-8",
        )
        plan = {
            "schema_version": 1,
            "recipe_id": "cap.recipe.test",
            "selected_optional_tokens": [],
            "preprocess_tokens": ["cap.subject.preflight-rectification"],
            "bindings": [
                {
                    "id": "S1",
                    "domain": "subject",
                    "token_ids": ["cap.subject.identity"],
                    "target": "the complete real temple subject",
                    "prompt_instruction": "Semantically extract and materially relight the authentic connected structure.",
                    "visible_result": "One unmistakable real subject with edited visual hierarchy.",
                    "guide_markers": ["S1"],
                },
                {
                    "id": "B1",
                    "domain": "background",
                    "token_ids": ["cap.background.active"],
                    "target": "the full field behind the temple silhouette",
                    "prompt_instruction": "Rebuild this region as an active mineral field that shapes the negative space.",
                    "visible_result": "A deliberate background field rather than untouched source sky.",
                    "guide_markers": ["B1"],
                },
                {
                    "id": "T1",
                    "domain": "typography",
                    "token_ids": ["cap.type.display"],
                    "target": "the two-character display-title group",
                    "prompt_instruction": "Redraw the title as one custom architectural wordmark using the glyph brief.",
                    "visible_result": "A designed title silhouette rather than a stock Songti outline.",
                    "guide_markers": ["T1"],
                },
                {
                    "id": "I1",
                    "domain": "interaction",
                    "token_ids": ["cap.depth.occlusion"],
                    "target": "the meeting edge between the roof and title",
                    "prompt_instruction": "Place the authentic roof edge in front of part of the title with controlled occlusion.",
                    "visible_result": "One readable architecture-over-type depth event.",
                    "guide_markers": ["S1", "T1"],
                },
            ],
        }
        if mutate_plan is not None:
            mutate_plan(plan)
        plan_path = analysis / "design-plan.json"
        plan_path.write_text(json.dumps(plan), encoding="utf-8")
        glyph = analysis / "glyph-brief.md"
        glyph.write_text(
            "飞：横向屋檐决定长横、方切端点和高重心；保持全部标准笔画。\n"
            "檐：斗拱叠涩决定开放字腔和层级横画；保持木、詹的标准拓扑。\n" * 5,
            encoding="utf-8",
        )
        prompt_path = analysis / "generation-prompt.txt"
        prompt_path.write_text(prompt, encoding="utf-8")
        return [
            sys.executable,
            str(SCRIPT),
            "--run-dir",
            str(run_dir),
            "--source",
            str(source),
            "--reference",
            str(reference),
            "--guide",
            str(guide),
            "--typeset-spec",
            str(spec),
            "--typeset-report",
            str(report),
            "--recipe-json",
            str(recipe),
            "--design-plan",
            str(plan_path),
            "--glyph-brief",
            str(glyph),
            "--prompt",
            str(prompt_path),
            "--output-image",
            str(run_dir / "final" / "poster.png"),
        ]

    def test_compiles_self_contained_three_image_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            completed = subprocess.run(self.make_fixture(root), capture_output=True, text=True, check=False)
            self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
            manifest_path = root / "output" / "yingzao" / "run" / "analysis" / "generation-call.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(manifest["input_order"], ["edit-target", "primary-visual-reference", "typeset-guide"])
            self.assertEqual(len(manifest["referenced_image_paths"]), 3)
            self.assertTrue(all(Path(path).is_file() for path in manifest["referenced_image_paths"]))
            self.assertIn("Mechanism bindings:", manifest["prompt"])
            self.assertIn("[S1 / subject]", manifest["prompt"])
            self.assertIn("S1=REAL SUBJECT", manifest["prompt"])
            self.assertNotIn("cap.subject.identity", manifest["prompt"])
            self.assertNotEqual(manifest["prompt"], PROMPT.strip())
            self.assertEqual(manifest["tool_arguments"]["prompt"], manifest["prompt"])
            self.assertEqual(manifest["schema_version"], 2)
            self.assertEqual(manifest["token_delivery"]["cap.type.display"]["binding"], "T1")
            self.assertEqual(
                manifest["token_delivery"]["cap.subject.preflight-rectification"]["channel"],
                "preprocess",
            )
            self.assertEqual(
                manifest["tool_arguments"]["referenced_image_paths"], manifest["referenced_image_paths"]
            )
            self.assertEqual(Path(manifest["prompt_path"]).name, "04-imagegen-prompt.txt")
            self.assertEqual(len(manifest["call_signature"]), 64)

    def test_rejects_an_active_token_without_a_delivery_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)

            def remove_subject_binding(plan: dict) -> None:
                plan["bindings"] = [item for item in plan["bindings"] if item["id"] != "S1"]

            completed = subprocess.run(
                self.make_fixture(root, mutate_plan=remove_subject_binding),
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertNotEqual(completed.returncode, 0)
            self.assertIn("active recipe tokens have no delivery path", completed.stdout)
            self.assertIn("missing required model-work domains: subject", completed.stdout)

    def test_rejects_a_prompt_binding_without_a_matching_guide_marker(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)

            def bad_marker(plan: dict) -> None:
                plan["bindings"][0]["guide_markers"] = ["S9"]

            completed = subprocess.run(
                self.make_fixture(root, mutate_plan=bad_marker),
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertNotEqual(completed.returncode, 0)
            self.assertIn("design-plan guide markers missing from Image 3: S9", completed.stdout)

    def test_rejects_prompt_that_drops_a_model_work_domain(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            prompt = PROMPT.replace("Subject treatment:", "Subject notes:")
            completed = subprocess.run(
                self.make_fixture(root, prompt=prompt), capture_output=True, text=True, check=False
            )
            self.assertNotEqual(completed.returncode, 0)
            self.assertIn("Subject treatment:", completed.stdout)

    def test_rejects_stock_font_silhouette_for_reinterpret_title(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            completed = subprocess.run(
                self.make_fixture(root, guide_render="text"), capture_output=True, text=True, check=False
            )
            self.assertNotEqual(completed.returncode, 0)
            self.assertIn("reinterpret requires guide_render=scaffold", completed.stdout)

    def test_appends_named_support_images_after_the_fixed_three_inputs(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            prompt = PROMPT.replace(
                "Image 3 is the spatial typeset scaffold.",
                "Image 3 is the spatial typeset scaffold. Image 4 is a same-place food support source.",
            )
            command = self.make_fixture(root, prompt=prompt)
            support = root / "support.jpg"
            Image.new("RGB", (300, 220), "#604020").save(support)
            insertion = command.index("--typeset-spec")
            command[insertion:insertion] = ["--support", str(support)]
            completed = subprocess.run(command, capture_output=True, text=True, check=False)
            self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
            manifest = json.loads(
                (root / "output" / "yingzao" / "run" / "analysis" / "generation-call.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(manifest["input_order"][-1], "support-1")
            self.assertEqual(len(manifest["referenced_image_paths"]), 4)


if __name__ == "__main__":
    unittest.main()
