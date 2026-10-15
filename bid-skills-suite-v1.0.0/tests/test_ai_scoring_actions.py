from __future__ import annotations

import copy
import hashlib
import json
import sys
import tempfile
import unittest
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "tests"))

import ai_scoring
import bidkit
from ai_scoring_actions import _row_requires_input
from ai_scoring_actions import AIScoringActionError, AIScoringActionService
from core_review_fixture import populate


class AIScoringActionsTests(unittest.TestCase):
    def test_technical_authorization_and_equipment_design_are_editable(self):
        row = {"title": "数据资源设计方案", "scoring_type": "subjective",
               "rubric_basis": "数据目录与现场设备接入设计",
               "deductions": [{"reason": "缺少数据开放目录和交换平台对接方案",
                               "action": "补充接口字段、授权机制和失败恢复"}]}
        self.assertFalse(_row_requires_input(row))
        row["title"] = "人员资格"
        self.assertTrue(_row_requires_input(row))
        row["title"] = "设备架构方案"
        row["deductions"][0]["reason"] = "缺少设备权属和真实资质证书"
        self.assertTrue(_row_requires_input(row))

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.project = Path(self.temp.name) / "project"
        bidkit.init_project(self.project, "TEST-AI-ACTIONS")
        populate(self.project)
        writing = bidkit.read(self.project / "artifacts/11-technical-content.json")
        writing["data"]["chapters"][0]["section_id"] = "SEC-1"
        writing["data"]["chapters"][0]["body_markdown"] = writing["data"]["chapters"][0].get("body", "")
        writing["revision"] = 1
        bidkit.atomic(self.project / "artifacts/11-technical-content.json", writing)
        self.service = AIScoringActionService(self.project)

    def tearDown(self):
        self.temp.cleanup()

    def cas(self):
        path = self.project / "artifacts/11-technical-content.json"
        return bidkit.read(path).get("revision", 0), hashlib.sha256(path.read_bytes()).hexdigest()

    def request(self, action="score", **extra):
        revision, digest = self.cas()
        payload = {"action": action, "request_id": str(uuid.uuid4()),
                   "expected_revision": revision, "expected_sha256": digest}
        payload.update(extra)
        return self.service.request(payload)

    def completed_report(self, path: Path, *, deduction=False, target_id="S1", revision=1):
        report = ai_scoring.prepare(self.project, "full")
        row = report["rows"][0]
        body = self.project / "artifacts/11-technical-content.json"
        current_body = bidkit.read(body)["data"]["chapters"][0].get("body_markdown", "")
        reference = {"relative_path": "artifacts/11-technical-content.json",
                     "sha256": bidkit.digest(body), "location": "/data/chapters/0/body_markdown",
                     "quote": current_body}
        score = 1 if deduction else 2
        row.update(status="scored", simulated_score=score, range={"low": score, "high": score},
                   confidence="high", rationale="按原文回读正文。", rubric_basis="每项1分。",
                   bid_refs=[reference], deductions=([{"points": 1, "reason": "正文缺少完整说明",
                                                         "action": "补充主观技术方案"}] if deduction else []),
                   limitations=[])
        report.update(status="completed", semantic_evaluation="COMPLETED",
                      evaluator={"kind": "host_agent", "host": "test-host", "model": None},
                      evaluated_at="2026-10-15T00:00:00+00:00", revision=revision)
        report["summary"] = ai_scoring.summarize(report["rows"], bidkit.read(self.project / "artifacts/04-scoring.json"),
                                                   "full", "COMPLETED")
        bidkit.atomic(path, report)
        return report

    def evidence(self, request):
        path = self.project / "work/evidence.json"
        bidkit.atomic(path, {"project_id": "TEST-AI-ACTIONS", "request_id": request["request_id"],
                             "tool_or_agent": "test-host", "performed_actions": ["回读当前评分与正文"]})
        return "work/evidence.json"

    def test_score_request_is_draft_and_idempotent(self):
        payload = {"action": "score", "request_id": str(uuid.uuid4()),
                   "expected_revision": self.cas()[0], "expected_sha256": self.cas()[1]}
        first = self.service.request(payload)
        self.assertEqual(first["status"], "awaiting_host")
        self.assertIn("work/ai-scoring-actions", first["relative_path"])
        self.assertIn("claim", first["host_prompt"])
        self.assertEqual(self.service.request(payload), first)
        latest = self.service.view()["latest_report"]
        self.assertTrue(latest["valid"])
        self.assertTrue(latest["current"])
        self.assertIsNone(latest["report_url"])

    def test_cas_duplicate_and_path_safety(self):
        revision, digest = self.cas()
        with self.assertRaises(AIScoringActionError) as caught:
            self.service.request({"action": "score", "request_id": str(uuid.uuid4()),
                                  "expected_revision": revision, "expected_sha256": "0" * 64})
        self.assertEqual(caught.exception.code, "stale_write")
        req = self.request()
        with self.assertRaises(AIScoringActionError) as caught:
            self.request()
        self.assertEqual(caught.exception.code, "duplicate_active")
        with self.assertRaises(AIScoringActionError) as caught:
            self.service.request({"action": "score", "request_id": req["request_id"],
                                  "expected_revision": revision, "expected_sha256": digest, "scope": "limited"})
        self.assertEqual(caught.exception.code, "request_conflict")

    def test_finish_requires_actual_completed_current_score(self):
        req = self.request()
        self.service.claim(req["request_id"])
        with self.assertRaises(AIScoringActionError) as caught:
            self.service.finish(req["request_id"], self.evidence(req))
        self.assertEqual(caught.exception.code, "incomplete_scoring")
        self.completed_report(self.project / req["report_relative_path"])
        done = self.service.finish(req["request_id"], self.evidence(req))
        self.assertEqual(done["status"], "completed")
        self.assertIn("?path=", self.service.view()["latest_report"]["report_url"])
        before = set(p.relative_to(self.project).as_posix() for p in self.project.rglob("*"))
        html = self.service.report_html(self.service.view()["latest_report"]["relative_path"])
        after = set(p.relative_to(self.project).as_posix() for p in self.project.rglob("*"))
        self.assertIn("AI 模拟专家评分", html)
        self.assertEqual(before, after)

    def test_score_finish_rejects_reprepared_report_after_input_change(self):
        req = self.request()
        self.service.claim(req["request_id"])
        scoring = bidkit.read(self.project / "artifacts/04-scoring.json")
        scoring["data"]["items"][0]["rule_text"] = "输入发生变化"
        bidkit.atomic(self.project / "artifacts/04-scoring.json", scoring)
        self.completed_report(self.project / req["report_relative_path"])
        with self.assertRaises(AIScoringActionError) as caught:
            self.service.finish(req["request_id"], self.evidence(req))
        self.assertEqual(caught.exception.code, "stale_request")

    def test_improve_requires_subjective_deduction_and_actual_change(self):
        scoring_path = self.project / "artifacts/04-scoring.json"
        scoring = bidkit.read(scoring_path)
        scoring["data"]["items"][0]["title"] = "技术方案"
        bidkit.atomic(scoring_path, scoring)
        prior = self.request()
        self.service.claim(prior["request_id"])
        old = self.completed_report(self.project / prior["report_relative_path"], deduction=True)
        self.service.finish(prior["request_id"], self.evidence(prior))
        report_sha = bidkit.digest(self.project / prior["report_relative_path"])
        revision, digest = self.cas()
        req = self.service.request({"action": "improve", "request_id": str(uuid.uuid4()),
                                    "expected_revision": revision, "expected_sha256": digest,
                                    "scoring_sha256": report_sha, "target_ids": ["S1"]})
        self.assertEqual(req["status"], "awaiting_host")
        self.assertEqual(req["affected_section_ids"], ["SEC-1"])
        self.service.claim(req["request_id"])
        self.completed_report(self.project / req["report_relative_path"], revision=2)
        with self.assertRaises(AIScoringActionError) as caught:
            self.service.finish(req["request_id"], self.evidence(req))
        self.assertEqual(caught.exception.code, "no_content_change")

    def test_objective_and_material_deductions_route_to_input(self):
        prior = self.request()
        self.service.claim(prior["request_id"])
        report = self.completed_report(self.project / prior["report_relative_path"], deduction=True)
        report["rows"][0]["deductions"][0]["reason"] = "缺少真实材料证明"
        bidkit.atomic(self.project / prior["report_relative_path"], report)
        self.service.finish(prior["request_id"], self.evidence(prior))
        scoring_sha = bidkit.digest(self.project / prior["report_relative_path"])
        revision, digest = self.cas()
        req = self.service.request({"action": "improve", "request_id": str(uuid.uuid4()),
                                    "expected_revision": revision, "expected_sha256": digest,
                                    "scoring_sha256": scoring_sha, "target_ids": ["S1"]})
        self.assertEqual(req["status"], "requires_input")
        with self.assertRaises(AIScoringActionError) as caught:
            self.service.claim(req["request_id"])
        self.assertEqual(caught.exception.code, "requires_input")

    def test_latest_completed_report_remains_visible_while_new_draft_is_pending(self):
        first = self.request()
        self.service.claim(first["request_id"])
        self.completed_report(self.project / first["report_relative_path"])
        self.service.finish(first["request_id"], self.evidence(first))
        second = self.request()
        view = self.service.view()
        self.assertEqual(view["latest_report"]["relative_path"], first["report_relative_path"])
        self.assertEqual(view["latest_request"]["request_id"], second["request_id"])
        self.assertEqual(view["latest_request"]["report_relative_path"], second["report_relative_path"])

    def test_changed_scoring_retires_claimed_task_before_new_request(self):
        first = self.request()
        self.service.claim(first["request_id"])
        scoring = bidkit.read(self.project / "artifacts/04-scoring.json")
        scoring["revision"] = 2
        bidkit.atomic(self.project / "artifacts/04-scoring.json", scoring)
        second = self.request()
        self.assertEqual(second["status"], "awaiting_host")
        retired = json.loads((self.project / first["relative_path"]).read_text(encoding="utf-8"))
        self.assertEqual(retired["status"], "stale")

    def test_selected_unknown_improve_is_persisted_as_unresolved(self):
        scoring_path = self.project / "artifacts/04-scoring.json"
        scoring = bidkit.read(scoring_path)
        scoring["data"]["items"][0]["title"] = "技术方案"
        bidkit.atomic(scoring_path, scoring)
        first = self.request()
        self.service.claim(first["request_id"])
        self.completed_report(self.project / first["report_relative_path"], deduction=True)
        self.service.finish(first["request_id"], self.evidence(first))
        old_sha = bidkit.digest(self.project / first["report_relative_path"])
        revision, digest = self.cas()
        req = self.service.request({"action": "improve", "request_id": str(uuid.uuid4()),
                                    "expected_revision": revision, "expected_sha256": digest,
                                    "scoring_sha256": old_sha, "target_ids": ["S1"]})
        self.service.claim(req["request_id"])
        report = ai_scoring.prepare(self.project, "limited")
        row = report["rows"][0]
        row.update(status="unknown", rationale="缺少可确认输入。", limitations=["待核验"])
        report.update(status="completed", semantic_evaluation="COMPLETED", revision=2,
                      evaluator={"kind": "host_agent", "host": "test-host", "model": None},
                      evaluated_at="2026-10-15T00:00:00+00:00", scope="limited")
        report["summary"] = ai_scoring.summarize(report["rows"], bidkit.read(self.project / "artifacts/04-scoring.json"),
                                                   "limited", "COMPLETED")
        bidkit.atomic(self.project / req["report_relative_path"], report)
        with self.assertRaises(AIScoringActionError) as caught:
            self.service.finish(req["request_id"], self.evidence(req))
        self.assertEqual(caught.exception.code, "incomplete_scoring")
        persisted = json.loads((self.project / req["relative_path"]).read_text(encoding="utf-8"))
        self.assertEqual(persisted["status"], "requires_input")
        self.assertEqual(persisted["unresolved_target_ids"], ["S1"])

    def test_claimed_improve_stays_visible_when_allowed_chapter_body_changes(self):
        scoring_path = self.project / "artifacts/04-scoring.json"
        scoring = bidkit.read(scoring_path)
        scoring["data"]["items"][0]["title"] = "技术方案"
        bidkit.atomic(scoring_path, scoring)
        prior = self.request()
        self.service.claim(prior["request_id"])
        self.completed_report(self.project / prior["report_relative_path"], deduction=True)
        self.service.finish(prior["request_id"], self.evidence(prior))
        scoring_sha = bidkit.digest(self.project / prior["report_relative_path"])
        revision, digest = self.cas()
        req = self.service.request({"action": "improve", "request_id": str(uuid.uuid4()),
                                    "expected_revision": revision, "expected_sha256": digest,
                                    "scoring_sha256": scoring_sha, "target_ids": ["S1"]})
        self.service.claim(req["request_id"])
        writing_path = self.project / "artifacts/11-technical-content.json"
        writing = bidkit.read(writing_path)
        writing["data"]["chapters"][0]["body_markdown"] += "\n补充可验收的技术说明。"
        writing["revision"] = revision + 1
        bidkit.atomic(writing_path, writing)
        latest = self.service.view()["latest_request"]
        self.assertEqual(latest["request_id"], req["request_id"])
        self.assertEqual(latest["status"], "claimed")

    def test_newer_corrupt_report_blocks_older_completed_report(self):
        first = self.request()
        self.service.claim(first["request_id"])
        self.completed_report(self.project / first["report_relative_path"])
        self.service.finish(first["request_id"], self.evidence(first))
        corrupt = self.project / "reviews/15-ai-scoring-r99-corrupt.json"
        corrupt.write_text("{broken", encoding="utf-8")
        latest = self.service.view()["latest_report"]
        self.assertEqual(latest["relative_path"], "reviews/15-ai-scoring-r99-corrupt.json")
        self.assertFalse(latest["valid"])
        self.assertFalse(latest["current"])
        self.assertIsNone(latest["report_url"])

    def test_fail_records_reason_and_releases_active_request(self):
        req = self.request()
        evidence_path = self.project / "work/failure.json"
        bidkit.atomic(evidence_path, {"project_id": self.service.project_id,
                                      "request_id": req["request_id"],
                                      "tool_or_agent": "test-host",
                                      "performed_actions": ["读取评分输入"],
                                      "reason": "宿主模型超时"})
        failed = self.service.fail(req["request_id"], "work/failure.json")
        self.assertEqual(failed["status"], "failed")
        self.assertEqual(failed["failure_reason"], "宿主模型超时")
        self.assertEqual(failed["attempts"][0]["reason"], "宿主模型超时")
        replacement = self.request()
        self.assertEqual(replacement["status"], "awaiting_host")


if __name__ == "__main__":
    unittest.main()
