import json
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[1]
RUNTIME_DIR = ROOT / "skills/image-to-editable-ppt/cli/editppt/runtime"
sys.path.insert(0, str(RUNTIME_DIR))

from extract_source_asset import extract_asset  # noqa: E402
from visual_qa import run_visual_qa  # noqa: E402


def write_json(path, payload):
    Path(path).write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def base_manifest():
    return {
        "source": {"width_px": 200, "height_px": 120},
        "slide": {"width": 10, "height": 6},
        "content_box": {"left": 0, "top": 0, "width": 10, "height": 6},
        "text_boxes": [],
        "images": [],
        "shapes": [],
        "visual_qa": {},
    }


def run_page(page_dir, manifest, source, preview=None):
    page_dir = Path(page_dir)
    source.save(page_dir / "source.png")
    (preview or source).save(page_dir / "preview.png")
    write_json(page_dir / "manifest.json", manifest)
    report = run_visual_qa(
        page_dir,
        page_dir / "manifest.json",
        page_dir / "source.png",
        page_dir / "preview.png",
        page_dir / "visual-qa.json",
        page_dir / "visual-diff.png",
    )
    return report


class VisualQATest(unittest.TestCase):
    def test_image_ink_text_overlap_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            page = Path(tmp)
            source = Image.new("RGB", (200, 120), "white")
            icon = Image.new("RGBA", (20, 20), (255, 255, 255, 0))
            ImageDraw.Draw(icon).rectangle((2, 2, 17, 17), fill=(0, 90, 200, 255))
            icon.save(page / "icon.png")
            manifest = base_manifest()
            manifest["images"] = [{"id": "icon", "path": "icon.png", "box_px": [10, 10, 20, 20]}]
            manifest["text_boxes"] = [{"id": "title", "text": "Title", "box_px": [15, 10, 40, 20]}]

            report = run_page(page, manifest, source)

            self.assertIs(report["passed"], False)
            self.assertEqual(1, len(report["overlap_violations"]))
            self.assertEqual("image-text", report["overlap_violations"][0]["kind"])

    def test_explicit_reasoned_overlap_is_allowed(self):
        with tempfile.TemporaryDirectory() as tmp:
            page = Path(tmp)
            source = Image.new("RGB", (200, 120), "white")
            icon = Image.new("RGBA", (20, 20), (0, 90, 200, 255))
            icon.save(page / "icon.png")
            manifest = base_manifest()
            manifest["images"] = [{"id": "photo", "path": "icon.png", "box_px": [10, 10, 20, 20]}]
            manifest["text_boxes"] = [{"id": "caption", "text": "Caption", "box_px": [10, 10, 40, 20]}]
            manifest["visual_qa"] = {
                "allowed_overlaps": [
                    {
                        "kind": "image-text",
                        "image_id": "photo",
                        "text_id": "caption",
                        "reason": "caption intentionally overlays the photo",
                    }
                ]
            }

            report = run_page(page, manifest, source)

            self.assertIs(report["passed"], True)
            self.assertEqual([], report["overlap_violations"])

    def test_text_text_overlap_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            page = Path(tmp)
            source = Image.new("RGB", (200, 120), "white")
            manifest = base_manifest()
            manifest["text_boxes"] = [
                {"id": "title", "text": "Title", "box_px": [20, 20, 80, 24]},
                {"id": "subtitle", "text": "Subtitle", "box_px": [50, 20, 80, 24]},
            ]

            report = run_page(page, manifest, source)

            self.assertIs(report["passed"], False)
            self.assertEqual("text-text", report["overlap_violations"][0]["kind"])

    def test_source_shape_color_mismatch_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            page = Path(tmp)
            source = Image.new("RGB", (200, 120), "white")
            ImageDraw.Draw(source).rectangle((20, 20, 79, 49), fill=(22, 85, 176))
            manifest = base_manifest()
            manifest["shapes"] = [
                {"id": "dark_chip", "type": "rect", "box_px": [20, 20, 60, 30], "fill": "#EAF4FF"}
            ]

            report = run_page(page, manifest, source)

            self.assertIs(report["passed"], False)
            self.assertEqual("dark_chip", report["shape_color_mismatches"][0]["shape_id"])

    def test_tall_structure_geometry_drift_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            page = Path(tmp)
            source = Image.new("RGB", (200, 120), "white")
            ImageDraw.Draw(source).rectangle((150, 20, 169, 109), fill=(17, 159, 203))
            manifest = base_manifest()
            manifest["shapes"] = [
                {"id": "right_rail", "type": "rect", "box_px": [150, 0, 20, 110], "fill": "#119FCB"}
            ]

            report = run_page(page, manifest, source)

            self.assertIs(report["passed"], False)
            self.assertEqual("right_rail", report["geometry_mismatches"][0]["shape_id"])
            self.assertGreater(report["geometry_mismatches"][0]["edge_deltas_px"][1], 10)

    def test_clean_page_passes_and_writes_diff(self):
        with tempfile.TemporaryDirectory() as tmp:
            page = Path(tmp)
            source = Image.new("RGB", (200, 120), "white")

            report = run_page(page, base_manifest(), source)

            self.assertIs(report["passed"], True)
            self.assertTrue((page / "visual-diff.png").exists())
            self.assertEqual(0.0, report["diff_metrics"]["mean_absolute_error"])

    def test_uniform_source_extraction_preserves_exact_foreground_pixels(self):
        source = Image.new("RGB", (100, 100), (0, 80, 180))
        ImageDraw.Draw(source).rectangle((40, 30, 59, 69), fill="white")

        output, output_box, metadata = extract_asset(
            source,
            [30, 20, 40, 60],
            max_background_variation=5,
            low_threshold=10,
            feather=20,
            padding=0,
        )

        self.assertEqual([40, 30, 20, 40], output_box)
        self.assertEqual((20, 40), output.size)
        self.assertEqual([0, 80, 180], metadata["background_rgb"])
        alpha = np.asarray(output.getchannel("A"))
        self.assertTrue(np.all(alpha == 255))


if __name__ == "__main__":
    unittest.main()
