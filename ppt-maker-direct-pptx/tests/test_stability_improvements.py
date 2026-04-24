from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = SKILL_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import generate_image_assets  # noqa: E402
import ppt_renderer  # noqa: E402
import run_ppt_job  # noqa: E402
import validate_job  # noqa: E402


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def minimal_slide_spec() -> dict:
    return {
        "page_no": 1,
        "title": "Executive Summary",
        "subtitle": "Stability test",
        "layout_type": "content",
        "visible_content": {
            "title": "Executive Summary",
            "subtitle": "Stability test",
            "blocks": [{"title": "Outcome", "items": ["Fallback keeps the deck build alive"], "summary": ""}],
            "image_placeholders": [],
            "image_assets": [],
        },
        "image_placeholders": [],
        "image_assets": [],
        "layout_regions": {"content": {"x": 0.72, "y": 1.55, "w": 11.86, "h": 5.25}, "images": [], "mode": "full"},
        "invisible_guidance": {"page_goal": "", "visual_focus": "", "detail_notes": "", "compiled_prompt": ""},
        "template_variant": {"id": "huixin", "name": "慧新", "rendering_recipe": ""},
    }


class StabilityImprovementTests(unittest.TestCase):
    def test_runtime_config_reports_actionable_preflight_issues(self) -> None:
        with mock.patch.dict(os.environ, {}, clear=True), mock.patch("run_ppt_job.shutil.which", return_value=None):
            issues = run_ppt_job.validate_runtime_config(
                {"text_model": "", "pptx_js_model": "openai/gpt-5.4-mini"},
                require_live_models=True,
            )

        joined = "\n".join(issues)
        self.assertIn("text_model", joined)
        self.assertIn("OPENROUTER_API_KEY", joined)
        self.assertIn("OPENROUTER_BASE_URL", joined)
        self.assertIn("model_config.yaml", joined)
        self.assertIn("node", joined)
        self.assertIn("npm", joined)

    def test_requirement_validation_requires_key_points(self) -> None:
        missing = validate_job.validate_job_data(
            {
                "topic": "Manufacturing AI",
                "target_audience": "制造业客户",
                "purpose": "客户汇报",
                "style": "慧新",
                "page_count": 8,
                "key_points": [],
                "requirement_confirmed": True,
                "template_id": "huixin",
            },
            require_confirmation=True,
            require_template_confirmation=True,
        )

        self.assertIn("key_points", missing)

    def test_template_manifest_loads_legacy_and_dark_english_template(self) -> None:
        registry = run_ppt_job.load_template_registry()

        self.assertIn("huixin", registry)
        self.assertIn("huixin-product-solution", registry)
        self.assertIn("huixin-market-promo", registry)
        self.assertIn("huixin-internal-meeting", registry)
        self.assertIn("dark-english-business", registry)

        bundle = run_ppt_job.load_template_variant_bundle("dark-english-business", None)
        self.assertIsNotNone(bundle)
        assert bundle is not None
        self.assertEqual(bundle["preset"]["template_id"], "dark-english-business")
        self.assertEqual(bundle["brief"]["template_id"], "dark-english-business")

    def test_artifact_validation_rejects_bad_counts_and_bad_placement(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp)
            job = {"page_count": 2}
            write_json(
                output_dir / "outline.json",
                {
                    "slides": [
                        {
                            "page_no": 1,
                            "title": "Only slide",
                            "image_placeholders": [
                                {"id": "bad", "prompt": "visual", "placement": {"x": 20, "y": 1, "w": 2, "h": 2}}
                            ],
                        }
                    ]
                },
            )
            write_json(output_dir / "slide_prompts.json", {"slides": [{"page_no": 1, "title": "Only slide"}]})
            write_json(output_dir / "slide_specs.json", {"slides": [{"page_no": 1, "visible_content": {}}]})

            issues = validate_job.validate_artifacts(job, output_dir)

        joined = "\n".join(issues)
        self.assertIn("outline.json 页数", joined)
        self.assertIn("placement", joined)
        self.assertIn("slide_specs.json", joined)

    def test_js_generation_falls_back_to_deterministic_slide_after_repairs_fail(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            slides_dir = Path(tmp)
            spec = minimal_slide_spec()
            theme = ppt_renderer.to_theme({"color_strategy": {}, "typography": {}})

            def invalid_generator(_prompt: str) -> str:
                return "module.exports = {};"

            def fake_validate(current_slides_dir: Path, filename: str, _spec: dict | None = None) -> None:
                script = (current_slides_dir / filename).read_text(encoding="utf-8")
                if "function addGrid" not in script:
                    raise ValueError("bad generated module")

            with mock.patch("ppt_renderer.validate_slide_module", side_effect=fake_validate):
                ppt_renderer.write_slide_module(
                    slides_dir,
                    spec,
                    {"color_strategy": {}, "typography": {}},
                    theme,
                    total_slides=1,
                    js_generator=invalid_generator,
                    max_repair_attempts=1,
                )

            script = (slides_dir / "slide-01.js").read_text(encoding="utf-8")
            self.assertIn("function addGrid", script)
            self.assertIn("module.exports", script)

    def test_image_generation_failure_writes_placeholder_with_fallback_reason(self) -> None:
        slide_specs = {
            "slides": [
                {
                    "page_no": 1,
                    "image_placeholders": [
                        {
                            "id": "p1_img1",
                            "role": "supporting_visual",
                            "purpose": "Factory scenario",
                            "prompt": "A factory floor visual",
                            "placement": {"x": 8.2, "y": 1.7, "w": 3.2, "h": 2.4},
                        }
                    ],
                }
            ]
        }

        with tempfile.TemporaryDirectory() as tmp, mock.patch(
            "generate_image_assets.generate_model_image", side_effect=RuntimeError("HTTP 500")
        ):
            updated_specs, assets = generate_image_assets.generate_assets_for_specs(
                slide_specs,
                {"color_strategy": {}, "typography": {}},
                {"image_model": "test-image-model"},
                Path(tmp),
                dry_run=False,
            )

            self.assertEqual(len(assets), 1)
            self.assertTrue(Path(assets[0]["path"]).exists())
            self.assertIn("HTTP 500", assets[0]["fallback_reason"])
            self.assertEqual(updated_specs["slides"][0]["image_assets"][0]["fallback_reason"], assets[0]["fallback_reason"])


if __name__ == "__main__":
    unittest.main()
