#!/usr/bin/env python3
"""Regression tests for controlled preflight tag suggestions."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from photo_preflight import controlled_tags  # noqa: E402


def report_for(edge_density: float) -> dict:
    return {
        "image": {"width": 1600, "height": 1200},
        "quality": {"edge_density": edge_density},
        "exposure": {"mean_luminance": 120},
        "negative_space": [{"score": 0.5}],
        "exif": {"datetime": None},
    }


class ControlledTagTests(unittest.TestCase):
    def test_medium_density_does_not_emit_generic_architecture_tag(self) -> None:
        tags = controlled_tags(report_for(0.10))
        self.assertEqual(tags, ["横向"])
        self.assertNotIn("建筑", tags)

    def test_density_extremes_still_emit_discriminating_tags(self) -> None:
        self.assertIn("低密度", controlled_tags(report_for(0.04)))
        self.assertIn("高密度", controlled_tags(report_for(0.20)))


if __name__ == "__main__":
    unittest.main()
