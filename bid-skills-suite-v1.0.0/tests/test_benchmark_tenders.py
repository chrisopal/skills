"""Regression checks for benchmark identity, citation and measurement boundaries."""
import copy
import hashlib
import sys
import tempfile
import unittest
from pathlib import Path

import fitz

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import benchmark_tenders as benchmark


class BenchmarkTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        path = self.root / "sample.pdf"
        with fitz.open() as doc:
            page = doc.new_page()
            page.insert_text((30, 50), "Tender project Alpha. Supply 20 servers. Price score 30.")
            page.insert_text((30, 80), "Late bids are rejected.")
            doc.save(path)
        sha = hashlib.sha256(path.read_bytes()).hexdigest()
        self.manifest = {"samples": [{"sample_id": "test", "relative_path": "sample.pdf",
                                     "sha256": sha, "bytes": path.stat().st_size, "pages": 1}]}
        anchors = [
            ("a", "basic_info", "Tender project Alpha"),
            ("b", "requirements", "Supply 20 servers"),
            ("c", "scoring", "Price score 30"),
            ("d", "disqualification", "Late bids are rejected"),
        ]
        self.label = {"sample_id": "test", "sha256": sha,
                      "annotation_status": "ai_reviewed_not_human_gold",
                      "lots": [{"categories": ["hardware_supply"], "evidence": [
                          {"page": 1, "quote": "Supply 20 servers"}]}],
                      "anchors": [{"id": a, "track": t, "page": 1, "quote": q, "meaning": q}
                                  for a, t, q in anchors]}
        self.annotations = {"samples": [self.label]}
        self.prediction = {"sample_id": "test", "sha256": sha,
                           "lots": copy.deepcopy(self.label["lots"]),
                           "facts": [{k: v for k, v in a.items() if k != "id"}
                                     for a in self.label["anchors"]]}

    def predictions(self, samples=None):
        return {"model": "fixture-no-model", "run_id": "unit-test",
                "scope": "synthetic", "input_scope": "fixture PDF only",
                "samples": [self.prediction] if samples is None else samples}

    def tearDown(self):
        self.tmp.cleanup()

    def test_audit_reads_real_pdf_and_keeps_acceptance_separate(self):
        result = benchmark.audit(self.manifest, self.annotations, self.root)
        self.assertEqual(result["total_anchors"], 4)
        self.assertEqual(result["human_expert_acceptance"], "NOT_RUN")

    def test_changed_pdf_rejected(self):
        with (self.root / "sample.pdf").open("ab") as stream:
            stream.write(b"changed")
        with self.assertRaisesRegex(ValueError, "原件"):
            benchmark.audit(self.manifest, self.annotations, self.root)

    def test_wrong_page_and_fabricated_quotes_rejected(self):
        for field, value in (("page", 2), ("page", True), ("quote", "Invented purchase")):
            with self.subTest(field=field, value=value):
                labels = copy.deepcopy(self.annotations)
                labels["samples"][0]["anchors"][0][field] = value
                with self.assertRaisesRegex(ValueError, "原页"):
                    benchmark.audit(self.manifest, labels, self.root)

    def test_missing_track_requires_reason(self):
        self.label["anchors"].pop()
        with self.assertRaisesRegex(ValueError, "四类"):
            benchmark.audit(self.manifest, self.annotations, self.root)
        self.label["unavailable_tracks"] = {"disqualification": "Not in selected source scope"}
        self.assertTrue(benchmark.audit(self.manifest, self.annotations, self.root)["passed"])

    def test_prediction_not_gold_and_metrics_are_limited(self):
        self.prediction["facts"].pop()
        result = benchmark.evaluate(self.manifest, self.annotations, self.root,
                                    self.predictions())
        self.assertEqual(result["matched_anchors"], 3)
        self.assertEqual(result["samples"][0]["missing_anchor_ids"], ["d"])
        self.assertEqual(result["semantic_correctness"], "REQUIRES_SEPARATE_REVIEW")

    def test_invalid_prediction_citation_cannot_score(self):
        self.prediction["facts"][0]["page"] = 2
        result = benchmark.evaluate(self.manifest, self.annotations, self.root,
                                    self.predictions())
        self.assertEqual(result["samples"][0]["valid_citations"], 3)
        self.assertEqual(result["matched_anchors"], 3)

    def test_two_single_lots_do_not_equal_one_mixed_lot(self):
        left = [{"categories": ["hardware_supply"]}, {"categories": ["software_integration"]}]
        right = [{"categories": ["hardware_supply", "software_integration"]}]
        self.assertNotEqual(benchmark.category_groups(left), benchmark.category_groups(right))

    def test_unknown_prediction_id_and_duplicate_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "重复"):
            benchmark.evaluate(self.manifest, self.annotations, self.root,
                               self.predictions([self.prediction, self.prediction]))
        self.prediction["sample_id"] = "other"
        with self.assertRaisesRegex(ValueError, "不存在"):
            benchmark.evaluate(self.manifest, self.annotations, self.root,
                               self.predictions())

    def test_classification_without_source_evidence_cannot_pass(self):
        for evidence in ([], [{"page": 2, "quote": "Supply 20 servers"}]):
            self.prediction["lots"][0]["evidence"] = evidence
            result = benchmark.evaluate(self.manifest, self.annotations, self.root,
                                        self.predictions())["samples"][0]
            self.assertTrue(result["classification_labels_match"])
            self.assertFalse(result["classification_evidence_valid"])
            self.assertFalse(result["classification_match"])

    def test_run_metadata_required_and_preserved(self):
        for key in ("model", "run_id", "scope", "input_scope"):
            pred = self.predictions()
            del pred[key]
            with self.assertRaisesRegex(ValueError, "运行元数据"):
                benchmark.evaluate(self.manifest, self.annotations, self.root, pred)
        result = benchmark.evaluate(self.manifest, self.annotations, self.root,
                                    self.predictions())
        self.assertEqual(result["run"]["model"], "fixture-no-model")

    def test_ambiguous_lots_only_score_components_when_annotation_says_so(self):
        self.label["classification_scope"] = "procurement_components_only"
        self.prediction["lots"].append(copy.deepcopy(self.prediction["lots"][0]))
        result = benchmark.evaluate(self.manifest, self.annotations, self.root,
                                    self.predictions())["samples"][0]
        self.assertTrue(result["classification_match"])
        self.assertFalse(result["lot_grouping_scored"])

    def test_empty_corpus_is_not_a_pass(self):
        with self.assertRaisesRegex(ValueError, "为空"):
            benchmark.audit({"samples": []}, {"samples": []}, self.root)

    def test_short_real_field_is_not_rejected_as_fabricated(self):
        self.assertTrue(benchmark.quote_valid(
            {"page": 1, "quote": "质量标准：合格"}, {1: "质量标准：合格"}))

    def test_path_escape_rejected(self):
        for relative in ("../sample.pdf", "/etc/passwd"):
            with self.assertRaises(ValueError):
                benchmark.safe(self.root, relative)


if __name__ == "__main__":
    unittest.main()
