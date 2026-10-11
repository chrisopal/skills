"""Customer/internal boundary and portable HTML review tests."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills/delivery-orchestrator/scripts/render_review.py"


def load_module():
    spec = importlib.util.spec_from_file_location("delivery_render_review", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class ReviewRendererTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.renderer = load_module()
        cls.forbidden_customer_key = staticmethod(cls.renderer.runtime.forbidden_customer_key)

    def setUp(self):
        self.snapshot = {
            "project_id": "DEMO-001",
            "purpose": "simulation",
            "artifacts": [
                {
                    "artifact_id": "REQ",
                    "revision": 2,
                    "kind": "requirements",
                    "visibility": "customer",
                    "status": "ready",
                    "health": "current",
                    "path": "artifacts/REQ-r2.json",
                    "sha256": "abc123",
                    "is_effective": True,
                    "effective_revision": 2,
                    "data": {
                        "items": [{"id": "R1", "statement": "Create work order", "source_refs": [{"locator": "page 2"}]}],
                        "open_items": [],
                        "forecast": "888888",
                    },
                },
                {
                    "artifact_id": "COSTS",
                    "revision": 1,
                    "kind": "costs",
                    "visibility": "internal",
                    "status": "ready",
                    "health": "current",
                    "path": "artifacts/COSTS-r1.json",
                    "sha256": "private",
                    "data": {"budget": "999999", "currency": "CNY"},
                },
                {
                    "artifact_id": "PRIVATE",
                    "revision": 1,
                    "kind": "review",
                    "visibility": "internal",
                    "status": "ready",
                    "health": "current",
                    "path": "artifacts/PRIVATE-r1.json",
                    "data": {"findings": [{"title": "private finding"}]},
                },
            ],
            "effective": {"REQ": {"revision": 2}},
            "cost_summary": {"budget": "999999", "gaps": ["rate missing"]},
            "alerts": ["private alert"],
            "gates": {"blueprint": {"ready": False, "reasons": ["not confirmed"]}},
        }
        self.renderer.runtime = type("Runtime", (), {
            "snapshot": staticmethod(lambda project: self.snapshot),
            "forbidden_customer_key": staticmethod(self.forbidden_customer_key),
        })

    def test_customer_view_filters_internal_data_and_snapshot_fields(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "customer.html"
            result = self.renderer.render_review(directory, output, "customer")
            html = output.read_text(encoding="utf-8")
            self.assertEqual(result["artifacts"], 1)
            self.assertIn("Create work order", html)
            self.assertIn("SIMULATION", html)
            self.assertNotIn("COSTS", html)
            self.assertNotIn("private finding", html)
            self.assertNotIn("999999", html)
            self.assertNotIn("888888", html)
            self.assertNotIn("private alert", html)
            self.assertNotIn("artifacts/REQ-r2.json", html)
            self.assertNotIn("window.__REVIEW_DATA__", html)

    def test_internal_view_keeps_costs_alerts_and_read_only_navigation(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "internal.html"
            result = self.renderer.render_review(directory, output, "internal")
            html = output.read_text(encoding="utf-8")
            self.assertEqual(result["artifacts"], 3)
            self.assertIn("999999", html)
            self.assertIn("private alert", html)
            self.assertIn("artifact-REQ", html)
            self.assertIn("record-search", html)
            self.assertIn("addEventListener('input'", html)
            self.assertNotIn("Approve", html)
            self.assertNotIn("Export", html)

    def test_invalid_view_is_rejected(self):
        with self.assertRaises(ValueError):
            self.renderer.render_review(".", "/tmp/review.html", "customer-facing")

    def test_candidate_is_not_marked_as_effective_by_id(self):
        candidate = self.snapshot['artifacts'][0]
        candidate['is_effective'] = False
        candidate['effective_revision'] = 1
        self.snapshot['effective']['REQ']['revision'] = 1
        rendered = self.renderer._artifact_html(candidate, 'internal', {'REQ'})
        self.assertNotIn('is-effective', rendered)
        self.assertNotIn('当前有效引用', rendered)
        self.assertIn('已生效版本', rendered)

    def test_customer_nested_sensitive_fields_are_removed(self):
        secrets = ['internal_rate', 'salary', 'margin', 'internal_notes', 'secret', 'access_token', 'password',
                   'private_key', 'apiKey', 'client-secret', 'refreshToken', 'Authorization', 'credential', 'token']
        self.snapshot['artifacts'][0]['data']['nested'] = [{key.upper(): 'hidden-' + key for key in secrets}]
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'customer.html'
            self.renderer.render_review(directory, output, 'customer')
            rendered = output.read_text()
            for key in secrets:
                self.assertNotIn('hidden-' + key, rendered)


if __name__ == "__main__":
    unittest.main()
