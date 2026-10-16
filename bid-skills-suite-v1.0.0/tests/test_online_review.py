import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "tests"))
import ai_scoring
import bidkit
import online_review
from core_review_fixture import populate


class OnlineReviewTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.project = Path(self.tmp.name) / "project"
        bidkit.init_project(self.project, "TEST-ONLINE-REVIEW")
        populate(self.project)
        self.mapping = {"SEC-1": {"last_synced": {"local_hash": "a" * 64}, "remote_hash": "b" * 64}}
        self.remote = {"bound": True, "provider": "feishu", "canonical_id": "testdoc123",
                       "project_id": "TEST-ONLINE-REVIEW", "current_mapping": self.mapping}

    def tearDown(self):
        self.tmp.cleanup()

    def client(self):
        mocked = patch("online_documents.OnlineDocumentService", autospec=True)
        factory = mocked.start()
        self.addCleanup(mocked.stop)
        service = factory.return_value
        service.status.side_effect = lambda: copy.deepcopy(self.remote)
        service.assert_current.side_effect = lambda sections=None: {"binding": copy.deepcopy(self.remote)}
        return service

    def test_basis_is_stable_and_frozen_in_actual_content_inventory(self):
        self.client()
        first = online_review.basis(self.project, "limited")
        before = bidkit.scan_content(self.project)
        self.assertEqual(first, online_review.basis(self.project, "limited"))
        self.assertEqual(before, bidkit.scan_content(self.project))
        self.assertIn("work/online-review-basis.json", [x["relative_path"] for x in before])

    def test_changed_remote_invalidates_frozen_assessment(self):
        self.client()
        old = online_review.basis(self.project, "limited")
        self.remote["current_mapping"]["SEC-1"]["remote_hash"] = "c" * 64
        with self.assertRaisesRegex(ValueError, "已变化"):
            online_review.verify(self.project, old, "limited")

    def test_full_review_requires_all_sections_and_failure_cannot_prepare_score(self):
        service = self.client()
        service.assert_current.side_effect = ValueError("有未同步章节")
        with self.assertRaisesRegex(ValueError, "未同步"):
            ai_scoring.prepare(self.project)
        service.assert_current.assert_called_once_with(None)

    def test_scored_rows_cannot_reference_unpublished_local_chapter(self):
        self.client()
        body = self.project / "artifacts/11-technical-content.json"
        value = json.loads(body.read_text())
        value["data"]["chapters"] = [{"section_id": "SEC-OTHER", "body_markdown": "未发布"}]
        body.write_text(json.dumps(value))
        frozen = online_review.basis(self.project, "limited")
        rows = [{"status": "scored", "bid_refs": [{"relative_path": "artifacts/11-technical-content.json",
                    "location": "/data/chapters/0/body_markdown"}]}]
        with self.assertRaisesRegex(ValueError, "未同步的章节"):
            online_review.verify(self.project, frozen, "limited", rows)

    def test_bound_empty_document_cannot_prepare_limited_score(self):
        self.client()
        self.remote["current_mapping"] = {}
        with self.assertRaisesRegex(ValueError, "至少同步"):
            ai_scoring.prepare(self.project, "limited")


if __name__ == "__main__":
    unittest.main()
