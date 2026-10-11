"""Regression checks for the evidence and presentation handoff contracts."""
import json
from pathlib import Path
import unittest
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]


class EvidenceContractTests(unittest.TestCase):
    def setUp(self):
        self.validator = Draft202012Validator(json.loads(
            (ROOT / "shared/schemas/evidence-item.schema.json").read_text()))
        self.evidence = dict(evidence_id="E-001", project_id="test", source_type="data",
                             source_name="orders.csv", claim_or_observation="late orders",
                             status="verified")

    def test_verified_requires_audit_details(self):
        self.assertTrue(list(self.validator.iter_errors(self.evidence)))

    def test_verified_accepts_locatable_checked_source(self):
        self.evidence.update(source_owner="data-owner", source_date="2026-10-11",
                             location="orders.csv#rows=2:31", raw_excerpt="30 records",
                             scope="Plant A / September",
                             verification={"reviewer":"analyst", "checked_at":"2026-10-11",
                                           "method":"reconcile order and shipment IDs",
                                           "result_evidence_ids":["E-002"]})
        self.assertFalse(list(self.validator.iter_errors(self.evidence)))

    def test_verified_rejects_empty_location(self):
        self.evidence.update(source_owner="owner", source_date="2026-10-11", location="",
                             raw_excerpt="record", scope="A",
                             verification={"reviewer":"r", "checked_at":"2026-10-11",
                                           "method":"m", "result_evidence_ids":["E-002"]})
        self.assertTrue(list(self.validator.iter_errors(self.evidence)))

    def test_conflict_requires_both_sides_and_next_action(self):
        self.evidence["status"] = "conflicted"
        self.assertTrue(list(self.validator.iter_errors(self.evidence)))
        self.evidence.update(conflicts_with=["E-002"],
                             verification_plan={"owner":"process-owner", "due_date":"2026-10-20",
                                                "action":"reconcile raw records"})
        self.assertFalse(list(self.validator.iter_errors(self.evidence)))

    def test_unverified_does_not_invent_source_detail(self):
        self.evidence["status"] = "unverified"
        self.assertFalse(list(self.validator.iter_errors(self.evidence)))


class PresentationContractTests(unittest.TestCase):
    def test_project_style_defines_actual_points_and_pixel_conversion(self):
        path = ROOT / "shared/assets/consulting-ppt-style.json"
        self.assertTrue(path.exists(), "missing reusable style profile")
        style = json.loads(path.read_text())
        self.assertEqual(style["unit"], "pt")
        expected = {"cover_title":32, "section_title":28, "slide_title":24,
                    "group_heading":18, "body":18, "flow_node":18,
                    "table":14, "chart_label":14, "secondary":14,
                    "footnote":12, "key_number":28}
        self.assertEqual({k:v["size"] for k,v in style["roles"].items()}, expected)
        self.assertEqual(style["svg_px_per_pt"], 4/3)
        self.assertFalse(style["auto_shrink"])


if __name__ == "__main__":
    unittest.main()
