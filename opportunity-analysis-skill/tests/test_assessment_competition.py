from __future__ import annotations

import hashlib
import math
import tempfile
import unittest
from pathlib import Path

from opportunity_skill.extractor import analyze
from opportunity_skill.pipeline import run_analyze
from opportunity_skill.renderer import SkillDisplayRenderer
from opportunity_skill.storage import OpportunitySQLiteAdapter


class AssessmentCompetitionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.db_path = self.root / "opportunity.db"
        first = run_analyze({
            "request_id": "first",
            "materials": [{"evidence_id": "ev1", "content": "客户已确认MES集成需求，预算待核实。"}],
            "sales_confirmation_answers": [{
                "dimension_id": "customer_relationship", "rating": "medium",
                "answer_text": "客户愿意继续交流", "answered_by": "销售A", "evidence_refs": ["ev1"],
            }],
        }, self.db_path)
        self.oid = first["storage_result"]["opportunity_id"]

    def tearDown(self):
        self.temp.cleanup()

    def manage(self, adapter, operations, request_id, expected_revision):
        return adapter.manage({"request_id": request_id, "opportunity_id": self.oid,
                               "expected_revision": expected_revision, "actor": "销售A", "operations": operations})

    def test_assessment_history_survives_restart_and_exposes_adjacent_deltas(self):
        updated = run_analyze({
            "request_id": "second",
            "opportunity_id": self.oid,
            "expected_revision": 1,
            "materials": [{"evidence_id": "ev2", "content": "客户内部导师明确支持方案，预算已立项。"}],
            "sales_confirmation_answers": [{
                "dimension_id": "customer_relationship", "rating": "strong",
                "answer_text": "业务负责人明确支持", "answered_by": "销售A", "evidence_refs": ["ev2"],
            }],
        }, self.db_path)
        adapter = OpportunitySQLiteAdapter(self.db_path)
        try:
            history = adapter.get_opportunity_detail(self.oid)["assessment_history"]
        finally:
            adapter.close()
        self.assertEqual(len(history), 2)
        self.assertEqual(history[-1]["deltas"]["dimensions"]["customer_relationship"]["from_rating"], "medium")
        self.assertEqual(history[-1]["deltas"]["dimensions"]["customer_relationship"]["to_rating"], "strong")
        self.assertEqual(history[-1]["deltas"]["dimensions"]["customer_relationship"]["delta"], 35)
        dimension = next(d for d in updated["structured_data"]["commercial_assessment"]["dimensions"] if d["dimension_id"] == "customer_relationship")
        self.assertEqual(dimension["evidence_refs"], ["ev2"])

        adapter = OpportunitySQLiteAdapter(self.db_path)
        try:
            detail = adapter.get_opportunity_detail(self.oid)
            self.assertEqual(len(detail["assessment_history"]), 2)
            self.assertEqual(detail["sales_confirmation_answers"][-1]["evidence_refs"], ["ev2"])
        finally:
            adapter.close()

    def test_sales_answer_rejects_foreign_evidence_atomically(self):
        adapter = OpportunitySQLiteAdapter(self.db_path)
        try:
            adapter.append_evidence({"evidence_id": "foreign", "content": "另一商机证据"})
            with self.assertRaises(ValueError):
                run_analyze({
                    "request_id": "foreign-answer", "opportunity_id": self.oid, "expected_revision": 1,
                    "sales_confirmation_answers": [{"dimension_id": "customer_relationship", "rating": "strong", "answer_text": "外部来源", "evidence_refs": ["foreign"]}],
                }, self.db_path)
            self.assertEqual(adapter.get_lifecycle(self.oid)["revision"], 1)
        finally:
            adapter.close()

    def test_competitor_is_versioned_idempotent_and_does_not_change_score(self):
        adapter = OpportunitySQLiteAdapter(self.db_path)
        try:
            before = adapter.get_opportunity_detail(self.oid)["opportunity"]["score"]
            operation = {"type": "record_competitor", "competitor_id": "comp-a", "name": "友商甲",
                         "position": "客户已有接触", "strengths": ["低价"], "weaknesses": ["交付经验少"],
                         "response": "安排现场案例交流", "status": "reported", "price_amount": 320000,
                         "currency": "CNY", "evidence": ["ev1"]}
            first = self.manage(adapter, [operation], "competitor-1", 1)
            self.assertEqual(first["revision"], 2)
            self.assertEqual(len(first["lifecycle"]["competitors"]), 1)
            self.assertEqual(first["lifecycle"]["competitors"][0]["history"][0]["version"], 1)
            self.assertEqual(adapter.get_opportunity_detail(self.oid)["opportunity"]["score"], before)

            second_op = {**operation, "position": "进入技术评审", "status": "confirmed", "price_amount": 300000,
                         "response": "突出交付风险和接口能力"}
            second = self.manage(adapter, [second_op], "competitor-2", 2)
            competitor = second["lifecycle"]["competitors"][0]
            self.assertEqual(competitor["version"], 2)
            self.assertEqual(competitor["status"], "confirmed")
            self.assertEqual(competitor["price_amount"], 300000)
            self.assertEqual([h["version"] for h in competitor["history"]], [1, 2])
            html = SkillDisplayRenderer().render("opportunity_detail", adapter.get_opportunity_detail(self.oid))["html"]
            self.assertIn("竞争台账", html)
            self.assertIn("我方应对", html)
            self.assertIn("评分依据历史", html)
            self.assertTrue(self.manage(adapter, [second_op], "competitor-2", 2)["idempotent_replay"])
        finally:
            adapter.close()

    def test_sales_answer_without_source_remains_unverified(self):
        adapter = OpportunitySQLiteAdapter(self.db_path)
        try:
            created = run_analyze({
                "request_id": "without-source",
                "materials": [{"evidence_id": "ev-nosource", "content": "客户希望继续交流"}],
                "sales_confirmation_answers": [{"dimension_id": "customer_relationship", "rating": "strong", "answer_text": "客户口头支持"}],
            }, self.db_path)
            detail = adapter.get_opportunity_detail(created["storage_result"]["opportunity_id"])
            dimension = next(d for d in detail["commercial_assessment"]["dimensions"] if d["dimension_id"] == "customer_relationship")
            self.assertEqual(dimension["evidence_status"], "needs_sales_confirmation")
            self.assertEqual(dimension["evidence_refs"], [])
        finally:
            adapter.close()

    def test_competitor_rejects_foreign_evidence_and_invalid_price_atomically(self):
        adapter = OpportunitySQLiteAdapter(self.db_path)
        try:
            bad = {"type": "record_competitor", "competitor_id": "comp-b", "name": "友商乙", "position": "未知",
                   "strengths": ["未知"], "weaknesses": ["未知"], "response": "待确认", "status": "unknown", "evidence": ["foreign"]}
            with self.assertRaises(ValueError):
                self.manage(adapter, [bad], "competitor-foreign", 1)
            bad["evidence"] = ["ev1"]
            bad["price_amount"] = math.nan
            with self.assertRaises(ValueError):
                self.manage(adapter, [bad], "competitor-nan", 1)
            self.assertEqual(adapter.get_lifecycle(self.oid)["revision"], 1)
            self.assertEqual(adapter.get_lifecycle(self.oid)["competitors"], [])
        finally:
            adapter.close()

    def test_presales_binding_invalidates_on_upstream_source_change(self):
        adapter = OpportunitySQLiteAdapter(self.db_path)
        try:
            project = self.root / "presales"
            project.mkdir()
            source = project / "work.json"
            source.write_text("{\"version\": 1}", encoding="utf-8")
            solution = self.root / "solution.md"
            solution.write_text("solution", encoding="utf-8")
            binding = {"project_path": str(project), "files": [{"file_path": str(source), "sha256": hashlib.sha256(source.read_bytes()).hexdigest()}]}
            operation = {"type": "register_artifact", "artifact_id": "s-presales", "kind": "solution", "version": 1,
                         "file_path": str(solution), "metadata": {"presales_binding": binding}, "evidence": ["ev1"]}
            self.manage(adapter, [operation], "presales-1", 1)
            source.write_text("{\"version\": 2}", encoding="utf-8")
            artifact = adapter.get_lifecycle(self.oid)["artifacts"][0]
            self.assertEqual(artifact["validity"], "dependency_invalid")
            self.assertIn("presales source changed", " ".join(artifact["verification_reasons"]))
        finally:
            adapter.close()


if __name__ == "__main__":
    unittest.main()
