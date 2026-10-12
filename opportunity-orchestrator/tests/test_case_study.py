import importlib.util
import json
from html.parser import HTMLParser
from pathlib import Path
import tempfile
import unittest
from urllib.parse import unquote, urlsplit


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("full_opportunity_case", ROOT / "scripts" / "case_study.py")
case = importlib.util.module_from_spec(spec)
spec.loader.exec_module(case)


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.targets = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self.targets.extend(value for key, value in attrs if key == "href")


class CaseStudyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.output = (Path(cls.temp.name) / "case").resolve()
        cls.result = case.run_case(cls.output)
        cls.snapshots = [json.loads(p.read_text(encoding="utf-8")) for p in sorted((cls.output / "stages").glob("*/snapshot.json"))]

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_one_opportunity_and_no_future_evidence(self):
        self.assertEqual(len(self.snapshots), 12)
        ids = set()
        for number, snapshot in enumerate(self.snapshots, 1):
            detail = snapshot["detail"]
            ids.add(detail["opportunity"]["id"])
            self.assertEqual({e["id"] for e in detail["evidence"]}, {f"EV-{n:02d}" for n in range(1, number + 1)})
            self.assertEqual(snapshot["number"], number)
        self.assertEqual(len(ids), 1)
        self.assertNotIn("contract-signed.md", self.snapshots[0]["documents"])
        first = (self.output / "light" / "01.html").read_text(encoding="utf-8")
        self.assertNotIn("358000", first)
        self.assertNotIn("方案 V2；客户认可", first)

    def test_review_is_a_loop_and_score_can_fall(self):
        for index in (3, 4, 5):
            self.assertEqual(self.snapshots[index]["detail"]["lifecycle"]["current_stage_id"], "solution_cocreation")
        self.assertEqual(self.snapshots[4]["review_status"], "open")
        self.assertEqual(self.snapshots[5]["review_status"], "closed")
        fit = [next(d["score"] for d in s["detail"]["commercial_assessment"]["dimensions"] if d["dimension_id"] == "solution_fit") for s in self.snapshots]
        self.assertEqual((fit[3], fit[4], fit[5]), (65, 25, 100))
        returned = (self.output / "light" / "05.html").read_text(encoding="utf-8")
        self.assertIn("方案 V1 已评审退回", returned)
        self.assertNotIn("等待客户评审", returned)
        scores = self.result["scores"]
        self.assertLess(scores[4], scores[3])
        self.assertLess(scores[8], scores[7])

    def test_quote_revision_and_signed_facts_are_separate(self):
        draft, final = [self.snapshots[i]["detail"]["lifecycle"] for i in (10, 11)]
        self.assertEqual(draft["current_stage_id"], "contract_signing")
        self.assertEqual(draft["contracts"], [])
        self.assertEqual(final["status"], "won")
        self.assertEqual(final["contracts"][0]["artifact_id"], "C-2")
        self.assertEqual(final["contracts"][0]["amount"], 358000)
        self.assertEqual([a["version"] for a in final["artifacts"] if a["kind"] == "quote"], [1, 2])
        self.assertEqual([f for f in final["facts"] if f["fact_id"] == "quote_authorized"][-1]["artifact_id"], "Q-2")
        self.assertEqual(self.result["scores"][-1], self.result["scores"][-2])
        self.assertNotEqual(self.result["scores"][-1], 100)
        self.assertTrue(any(a["id"] == "A-09" and a["status"] == "open" for a in final["actions"]))

    def test_customer_reviews_and_lineage_come_from_persisted_runtime(self):
        opened = self.snapshots[4]["detail"]["lifecycle"]["reviews"]
        closed = self.snapshots[5]["detail"]["lifecycle"]["reviews"]
        self.assertEqual({r["id"] for r in opened}, {"RV-01", "RV-02", "RV-03"})
        self.assertTrue(all(r["status"] == "open" and r["artifact_id"] == "SOL-1" for r in opened))
        self.assertTrue(all(r["status"] == "resolved" and r["verification_status"] == "current" and
                            r["closure"]["artifact_id"] == "SOL-2" and r["closure"]["evidence"] == ["EV-06"] for r in closed))
        self.assertTrue(all(len(r["history"]) == 2 for r in closed))
        final = self.snapshots[-1]["detail"]["lifecycle"]
        by_id = {a["id"]: a for a in final["artifacts"]}
        for aid, expected in {"Q-2": ["SOL-2"], "N-1": ["Q-2"], "C-2": ["Q-2", "N-1"], "H-1": ["C-2"]}.items():
            artifact = by_id[aid]
            self.assertEqual([d["artifact_id"] for d in artifact["dependencies"]], expected)
            self.assertTrue(all(d["sha256"] == by_id[d["artifact_id"]]["sha256"] for d in artifact["dependencies"]))
            self.assertEqual(artifact["validity"], "valid")
        self.assertEqual(final["verification_status"], "current")

    def test_every_case_page_and_artifact_link_resolves(self):
        for folder in ("light", "dark", "documents"):
            for page in (self.output / folder).glob("*.html"):
                parser = Links()
                parser.feed(page.read_text(encoding="utf-8"))
                for href in parser.targets:
                    url = urlsplit(href)
                    if not url.scheme and url.path:
                        target = (page.parent / unquote(url.path)).resolve()
                        self.assertTrue(target.is_relative_to(self.output), (page, href))
                        self.assertTrue(target.is_file(), (page, href))

    def test_partial_rehearsal_does_not_claim_later_signing(self):
        partial = Path(self.temp.name) / "partial"
        result = case.run_case(partial, through=6)
        self.assertEqual(result["timepoints"], 6)
        saved = json.loads((partial / "acceptance.json").read_text())
        self.assertFalse(saved["complete_case"])
        self.assertEqual(saved["final_lifecycle"]["contracts"], [])
        report = (partial / "case-report.md").read_text()
        self.assertNotIn("35.8", report)
        self.assertIn("尚未记录合同签署", report)
        latest = json.loads((partial / "stages/06/snapshot.json").read_text())
        solution_fit = next(d for d in latest["detail"]["assessment_history"][-1]["dimensions"] if d["dimension_id"] == "solution_fit")
        self.assertEqual(solution_fit["evidence_refs"], ["EV-06"])

    def test_existing_case_is_preserved(self):
        original = (self.output / "acceptance.json").read_bytes()
        with self.assertRaises(ValueError):
            case.run_case(self.output)
        self.assertEqual((self.output / "acceptance.json").read_bytes(), original)


if __name__ == "__main__":
    unittest.main()
