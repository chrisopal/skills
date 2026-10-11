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

    def test_existing_case_is_preserved(self):
        original = (self.output / "acceptance.json").read_bytes()
        with self.assertRaises(ValueError):
            case.run_case(self.output)
        self.assertEqual((self.output / "acceptance.json").read_bytes(), original)


if __name__ == "__main__":
    unittest.main()
