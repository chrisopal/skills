import copy
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "tests"))

import ai_scoring  # noqa: E402
import bidkit  # noqa: E402
from core_review_fixture import populate  # noqa: E402


class AIScoringTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.project = Path(self.tmp.name) / "project"
        bidkit.init_project(self.project, "TEST-AI-SCORING")
        populate(self.project)

    def tearDown(self):
        self.tmp.cleanup()

    def draft(self, scope="full"):
        return ai_scoring.prepare(self.project, scope)

    def complete(self, scope="full"):
        value = self.draft(scope)
        row = value["rows"][0]
        body = self.project / "artifacts/11-technical-content.json"
        body_ref = {
            "relative_path": "artifacts/11-technical-content.json",
            "sha256": bidkit.digest(body),
            "location": "/data/chapters/0/body",
            "quote": "测试主体提交营业执照。类似业绩附合同A和合同B。",
        }
        row.update(
            status="scored", simulated_score=2, range={"low": 2, "high": 2},
            confidence="high", rationale="按招标规则逐项核验当前正文和证明材料。",
            rubric_basis="类似业绩：合同与验收证明齐备计分。", bid_refs=[body_ref],
            deductions=[], limitations=[],
        )
        value.update(status="completed", semantic_evaluation="COMPLETED",
                     evaluator={"kind": "host_agent", "host": "test-host", "model": None},
                     evaluated_at="2026-10-14T00:00:00+00:00")
        value["summary"] = ai_scoring.summarize(
            value["rows"], {"data": {"items": [{"aggregation": "none"}]}}, scope, "COMPLETED")
        return value

    def test_prepare_is_draft_and_covers_each_scored_leaf_once(self):
        value = self.draft()
        self.assertEqual(value["semantic_evaluation"], "NOT_RUN")
        self.assertEqual(value["status"], "draft")
        self.assertEqual([row["status"] for row in value["rows"]], ["not_reviewed"])
        self.assertIsNone(value["rows"][0]["simulated_score"])
        self.assertEqual(ai_scoring.check(self.project, value)["valid"], True)
        invalid = copy.deepcopy(value)
        invalid["rows"][0]["status"] = "scored"
        invalid["rows"][0]["simulated_score"] = 0
        invalid["rows"][0]["range"] = {"low": 0, "high": 0}
        result = ai_scoring.check(self.project, invalid)
        self.assertTrue(any("draft不能包含语义评分结果" in item for item in result["errors"]))

    def test_evidence_form_name_does_not_turn_warranty_into_price_score(self):
        path = self.project / "artifacts/04-scoring.json"
        scoring = bidkit.read(path)
        scoring["data"]["items"][0].update(
            title="质保期", rule_text="每增加8个月得0.5分，不足8个月不得分。",
            evidence_requirements=["响应函/报价一览表中承诺的质保期"])
        bidkit.atomic(path, scoring)
        value = self.draft()
        self.assertEqual(value["rows"][0]["scoring_type"], "objective")
        self.assertTrue(ai_scoring.check(self.project, value)["valid"])

        scoring["data"]["items"][0].update(
            title="投标报价", rule_text="按基准价与报价比例计算价格分。",
            evidence_requirements=["报价一览表"])
        bidkit.atomic(path, scoring)
        value = self.draft()
        self.assertEqual(value["rows"][0]["scoring_type"], "price")
        value["rows"][0]["scoring_type"] = "objective"
        self.assertTrue(any("scoring_type必须是price" in error for error in
                            ai_scoring.check(self.project, value)["errors"]))

    def test_saved_and_workspace_reports_keep_usable_evidence_links(self):
        value = self.complete()
        saved = ai_scoring.render(self.project, value)
        content = Path(saved["path"]).read_text(encoding="utf-8")
        self.assertIn('href="../artifacts/11-technical-content.json"', content)
        self.assertNotIn('/api/file?path=', content)
        live = ai_scoring.render_html(self.project, value)
        self.assertIn('/api/file?path=artifacts%2F11-technical-content.json', live)

    def test_wrong_maximum_and_score_deduction_are_rejected(self):
        value = self.complete()
        value["rows"][0]["max_score"] = 3
        result = ai_scoring.check(self.project, value)
        self.assertFalse(result["valid"])
        self.assertTrue(any("max_score" in item for item in result["errors"]))
        value = self.complete()
        value["rows"][0]["deductions"] = [{"points": 1, "reason": "少一分", "action": "补证据"}]
        result = ai_scoring.check(self.project, value)
        self.assertTrue(any("deductions" in item for item in result["errors"]))

    def test_missing_body_quote_and_stale_inventory_are_rejected(self):
        value = self.complete()
        value["rows"][0]["bid_refs"][0]["quote"] = "不存在的正文"
        result = ai_scoring.check(self.project, value)
        self.assertTrue(any("正文引用无效" in item for item in result["errors"]))
        value = self.draft()
        (self.project / "artifacts/new-input.txt").write_text("new", encoding="utf-8")
        result = ai_scoring.check(self.project, value)
        self.assertTrue(any("快照过期" in item for item in result["errors"]))

    def test_positive_score_requires_real_evidence_and_price_requires_base(self):
        value = self.complete()
        value["rows"][0]["bid_refs"] = []
        result = ai_scoring.check(self.project, value)
        self.assertTrue(any("正分必须有实际正文或材料引用" in item for item in result["errors"]))
        price = self.draft()
        row = price["rows"][0]
        row.update(scoring_type="price", status="scored", max_score=2, simulated_score=1,
                   range={"low": 1, "high": 1}, confidence="high", rationale="按价格公式核验。",
                   rubric_basis="价格分公式", calculation_explanation="已读取本项目报价并按招标公式计算。",
                   price_inputs={"quote": 100, "formula": "base/quote*max"}, limitations=[])
        price.update(status="completed", semantic_evaluation="COMPLETED",
                     evaluator={"kind": "host_agent", "host": "test-host", "model": None},
                     evaluated_at="2026-10-14T00:00:00+00:00")
        price["summary"] = ai_scoring.summarize(price["rows"], {"data": {"items": [{"aggregation": "none"}]}}, "full", "COMPLETED")
        result = ai_scoring.check(self.project, price)
        self.assertTrue(any("quote和base" in item for item in result["errors"]))

    def test_objective_contract_positive_score_requires_registered_material(self):
        scoring_path = self.project / "artifacts/04-scoring.json"
        scoring = bidkit.read(scoring_path)
        scoring["data"]["items"][0].update(
            title="合同业绩", rule_text="合同业绩客观计分", evidence_requirements=["合同"])
        bidkit.atomic(scoring_path, scoring)
        value = self.draft()
        row = value["rows"][0]
        body = self.project / "artifacts/11-technical-content.json"
        row.update(scoring_type="objective", status="scored", simulated_score=1,
                   range={"low": 1, "high": 1}, confidence="high",
                   rationale="正文提到合同。", rubric_basis="合同业绩规则",
                   calculation_explanation="已检查正文范围。", inspection_scope="11技术正文全文",
                   bid_refs=[{"relative_path": "artifacts/11-technical-content.json",
                              "sha256": bidkit.digest(body), "location": "/data/chapters/0/body",
                              "quote": "测试主体提交营业执照。类似业绩附合同A和合同B。"}],
                   deductions=[], limitations=[])
        value.update(status="completed", semantic_evaluation="COMPLETED",
                     evaluator={"kind": "host_agent", "host": "test-host", "model": None},
                     evaluated_at="2026-10-14T00:00:00+00:00")
        value["summary"] = ai_scoring.summarize(value["rows"], scoring, "full", "COMPLETED")
        result = ai_scoring.check(self.project, value)
        self.assertTrue(any("登记材料引用" in item for item in result["errors"]))

    def test_limited_scope_does_not_claim_full_total_and_renderer_escapes_html(self):
        value = self.draft("limited")
        value["rows"][0]["rationale"] = "<script>alert(1)</script>"
        self.assertEqual(value["summary"]["scope"], "limited")
        self.assertEqual(value["summary"]["known_score"], 0)
        self.assertIsNone(value["summary"]["computed_total"])
        rendered = ai_scoring.render(self.project, value)
        content = Path(rendered["path"]).read_text(encoding="utf-8")
        self.assertNotIn("<script>alert(1)</script>", content)
        self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", content)
        self.assertIn("空评分计划", content)

    def test_price_criterion_cannot_bypass_missing_base_by_changing_type(self):
        scoring_path = self.project / "artifacts/04-scoring.json"
        scoring = bidkit.read(scoring_path)
        scoring["data"]["items"][0].update(title="报价价格", rule_text="按价格公式计分")
        bidkit.atomic(scoring_path, scoring)
        value = self.draft()
        row = value["rows"][0]
        row.update(scoring_type="subjective", status="scored", simulated_score=1,
                   range={"low": 1, "high": 1}, confidence="high", rationale="价格评读。",
                   rubric_basis="按价格公式", bid_refs=[], material_sources=[], deductions=[
                       {"points": 1, "reason": "缺少报价基准", "action": "补充报价"}], limitations=[])
        value.update(status="completed", semantic_evaluation="COMPLETED",
                     evaluator={"kind": "host_agent", "host": "test-host", "model": None},
                     evaluated_at="2026-10-14T00:00:00+00:00")
        value["summary"] = ai_scoring.summarize(value["rows"], scoring, "full", "COMPLETED")
        result = ai_scoring.check(self.project, value)
        self.assertTrue(any("必须是price" in item for item in result["errors"]))

    def test_missing_scoring_rules_cannot_become_empty_score_result(self):
        path = self.project / "artifacts/04-scoring.json"
        scoring = bidkit.read(path)
        scoring["data"]["items"] = []
        bidkit.atomic(path, scoring)
        with self.assertRaisesRegex(ValueError, "计分叶子"):
            self.draft()

    def test_full_semantic_run_cannot_leave_one_criterion_unreviewed(self):
        path = self.project / "artifacts/04-scoring.json"
        scoring = bidkit.read(path)
        second = copy.deepcopy(scoring["data"]["items"][0])
        second["id"] = "TEST-SECOND"
        scoring["data"]["items"].append(second)
        bidkit.atomic(path, scoring)
        value = self.complete()
        value["summary"] = ai_scoring.summarize(value["rows"], scoring, "full", "COMPLETED")
        result = ai_scoring.check(self.project, value)
        self.assertTrue(any("完整评分不能保留未评项" in item for item in result["errors"]))
        value["scope"] = "limited"
        value["summary"] = ai_scoring.summarize(value["rows"], scoring, "limited", "COMPLETED")
        self.assertTrue(ai_scoring.check(self.project, value)["valid"])
        self.assertIsNone(value["summary"]["computed_total"])

    def test_scored_leaf_cap_keeps_subtotal_but_rollup_cap_does_not(self):
        value = self.complete()
        scoring = bidkit.read(self.project / "artifacts/04-scoring.json")
        scoring["data"]["items"][0]["aggregation"] = "capped"
        summary = ai_scoring.summarize(value["rows"], scoring, "full", "COMPLETED")
        self.assertEqual(summary["known_score"], 2)
        self.assertEqual(summary["scored_max"], 2)
        self.assertEqual(summary["computed_total"], 2)
        scoring["data"]["items"].append({"id": "GROUP", "node_type": "rollup",
                                         "aggregation": "capped", "max_score": 1})
        summary = ai_scoring.summarize(value["rows"], scoring, "full", "COMPLETED")
        self.assertIsNone(summary["known_score"])
        self.assertFalse(summary["aggregate_available"])

    def test_review_digest_is_frozen_and_non_additive_totals_stay_unavailable(self):
        review = {
            "project_id": "TEST-AI-SCORING", "artifact_id": "R15", "revision": 1,
            "data": {"release_recommendation": "blocked", "review_scope": "limited"},
        }
        bidkit.atomic(self.project / "reviews/15-review.json", review)
        value = self.draft("limited")
        self.assertEqual(value["eligibility"]["release_recommendation"], "blocked")
        review["data"]["release_recommendation"] = "eligible_for_user_release"
        bidkit.atomic(self.project / "reviews/15-review.json", review)
        result = ai_scoring.check(self.project, value)
        self.assertTrue(any("15-review" in item for item in result["errors"]))

        # A max rollup must never be treated as a sum of leaves.
        scoring_path = self.project / "artifacts/04-scoring.json"
        scoring = bidkit.read(scoring_path)
        scoring["data"]["items"] = [
            {"id": "ROOT", "parent_id": None, "title": "择优", "max_score": 2,
             "node_type": "rollup", "aggregation": "max", "rule_text": "择优取最高项",
             "evidence_requirements": [], "sources": scoring["data"]["items"][0]["sources"]},
            dict(scoring["data"]["items"][0], parent_id="ROOT"),
        ]
        bidkit.atomic(scoring_path, scoring)
        value = self.draft()
        self.assertFalse(value["summary"]["aggregate_available"])
        self.assertIsNone(value["summary"]["known_score"])
        self.assertIsNone(value["summary"]["nominal_max"])
        self.assertIsNone(value["summary"]["computed_total"])

    def test_optional_upstream_stages_and_project_binding(self):
        (self.project / "artifacts/05-compliance.json").unlink()
        (self.project / "artifacts/09-evidence-selection.json").unlink()
        value = self.draft()
        self.assertTrue(ai_scoring.check(self.project, value)["valid"])
        value["project_id"] = "OTHER-PROJECT"
        self.assertFalse(ai_scoring.check(self.project, value)["valid"])

    def test_claimed_aggregate_fields_are_recomputed(self):
        value = self.draft()
        value["summary"]["aggregate_available"] = True
        value["summary"]["computed_total"] = 1000
        value["summary"]["aggregate_explanation"] = "伪造的完整总分"
        result = ai_scoring.check(self.project, value)
        self.assertFalse(result["valid"])
        self.assertTrue(any("aggregate_available" in item for item in result["errors"]))
        self.assertTrue(any("computed_total" in item for item in result["errors"]))
        self.assertTrue(any("aggregate_explanation" in item for item in result["errors"]))

    def test_claimed_eligibility_must_match_current_review_binding(self):
        review = {
            "project_id": "TEST-AI-SCORING", "artifact_id": "R15", "revision": 1,
            "data": {"release_recommendation": "blocked", "review_scope": "full"},
        }
        bidkit.atomic(self.project / "reviews/15-review.json", review)
        value = self.draft()
        value["eligibility"]["release_recommendation"] = "eligible_for_user_release"
        value["eligibility"]["review_scope"] = "limited"
        value["eligibility"]["review_present"] = False
        result = ai_scoring.check(self.project, value)
        self.assertFalse(result["valid"])
        self.assertTrue(any("release_recommendation" in item for item in result["errors"]))
        self.assertTrue(any("review_scope" in item for item in result["errors"]))
        self.assertTrue(any("review_present" in item for item in result["errors"]))

    def test_score_range_nan_tree_and_parent_validation(self):
        value = self.complete()
        value["rows"][0]["simulated_score"] = 3
        result = ai_scoring.check(self.project, value)
        self.assertTrue(any("超出" in item for item in result["errors"]))
        value = self.complete()
        value["rows"][0]["simulated_score"] = float("nan")
        result = ai_scoring.check(self.project, value)
        self.assertFalse(result["valid"])
        self.assertTrue(any("NaN" in item for item in result["errors"]))
        scoring_path = self.project / "artifacts/04-scoring.json"
        scoring = bidkit.read(scoring_path)
        scoring["data"]["items"][0]["parent_id"] = "MISSING"
        bidkit.atomic(scoring_path, scoring)
        with self.assertRaises(ValueError):
            self.draft()

    def test_blocked_result_remains_independent_and_output_guards_hold(self):
        value = self.complete()
        value["status"] = "blocked"
        result = ai_scoring.check(self.project, value)
        self.assertTrue(result["valid"])
        self.assertTrue(result["review_release_independent"])
        with self.assertRaises(ValueError):
            ai_scoring.render(self.project, value, "../reviews/escaped.html")
        with self.assertRaises(ValueError):
            ai_scoring.render(self.project, value, "reviews/wrong-directory.html")


if __name__ == "__main__":
    unittest.main()
