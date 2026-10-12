"""Daily operation ledger tests: persistence, revisions, and report boundaries."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills/delivery-orchestrator/scripts"


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


runtime = load("daily_test_runtime", SCRIPTS / "runtime.py")
daily = load("daily_operations_test_module", SCRIPTS / "daily_operations.py")


class DailyOperationsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.project = Path(self.temp.name) / "project"
        runtime.init_project(self.project, "DAILY-001")
        self.source = Path(self.temp.name) / "evidence.txt"
        self.source.write_text("registered evidence", encoding="utf-8")
        self.evidence_ref = runtime.source(self.project, self.source, "SRC")

    def fp(self):
        return daily.state(self.project)["registry_fingerprint"]

    def test_records_persist_as_immutable_runtime_revisions(self):
        first = daily.record_progress(self.project, {
            "entry_id": "OP1", "date": "2026-10-12", "work_package_id": "WP1",
            "status": "completed", "summary": "接口联调完成", "next_step": "准备回归",
            "evidence_refs": [self.evidence_ref],
        }, expected_registry_fingerprint=self.fp())
        second = daily.record_progress(self.project, {
            "entry_id": "OP2", "date": "2026-10-13", "work_package_id": "WP1",
            "status": "in_progress", "summary": "回归进行中", "next_step": "记录缺陷",
        }, expected_revision=first["revision"], expected_registry_fingerprint=self.fp())
        self.assertEqual((first["revision"], second["revision"]), (1, 2))
        self.assertEqual(runtime.latest_ref(self.project, "DAILY-PROGRESS")["revision"], 2)
        old = runtime.load_artifact(self.project, {"artifact_id": "DAILY-PROGRESS", "revision": 1, "sha256": first["ref"]["sha256"]})
        self.assertEqual([item["id"] for item in old["data"]["operations"]], ["OP1"])
        reopened = daily.state(self.project)
        self.assertEqual(reopened["active_ledgers"]["DAILY-PROGRESS"], 2)
        self.assertEqual(len(next(item for item in reopened["snapshot"]["artifacts"] if item["artifact_id"] == "DAILY-PROGRESS")["data"]["operations"]), 2)

    def test_hours_cost_summary_is_derived_and_customer_report_excludes_finance(self):
        daily.record_hours(self.project, {
            "entry_id": "H1", "date": "2026-10-12", "person": "工程师A",
            "work_package_id": "WP1", "hours": 3.5, "rate": 200,
            "resource_type": "internal", "status": "submitted",
        }, expected_registry_fingerprint=self.fp())
        daily.record_progress(self.project, {
            "entry_id": "OP1", "date": "2026-10-12", "work_package_id": "WP1",
            "status": "completed", "summary": "已完成", "next_step": "已完成后的回归仍需跟踪", "evidence_refs": [self.evidence_ref],
        }, expected_registry_fingerprint=self.fp())
        summary = runtime.snapshot(self.project)["cost_summary"]
        self.assertEqual(summary["internal_labor"], "700.00")
        self.assertEqual(summary["forecast"], "700.00")
        internal = daily.weekly_report(self.project, "2026-10-12/2026-10-18", "internal")
        customer = daily.weekly_report(self.project, "2026-10-12/2026-10-18", "customer")
        self.assertIn("内部工时与成本", internal)
        self.assertIn("700.00", internal)
        self.assertIn("已完成后的回归仍需跟踪", internal)
        self.assertNotIn("内部工时与成本", customer)
        self.assertNotIn("700.00", customer)
        self.assertNotIn("已完成。", customer)
        self.assertIn("无已登记的完成事实", customer)

    def test_invalid_input_injection_and_stale_writer_are_rejected(self):
        with self.assertRaises(ValueError):
            daily.record_hours(self.project, {"entry_id": "H1", "person": "A", "work_package_id": "../escape", "hours": 1}, expected_registry_fingerprint=self.fp())
        with self.assertRaises(ValueError):
            daily.record_hours(self.project, {"entry_id": "H1", "person": "A", "work_package_id": "WP1", "hours": 25}, expected_registry_fingerprint=self.fp())
        first = daily.record_progress(self.project, {"entry_id": "OP1", "work_package_id": "WP1", "summary": "<script>alert(1)</script>"}, expected_registry_fingerprint=self.fp())
        with self.assertRaises(daily.ConflictError):
            daily.record_progress(self.project, {"entry_id": "OP2", "work_package_id": "WP1", "summary": "second"}, expected_revision=0, expected_registry_fingerprint=self.fp())
        report = daily.weekly_report(self.project)
        self.assertIn("<script>alert(1)</script>", report)
        self.assertEqual(daily.state(self.project)["active_ledgers"]["DAILY-PROGRESS"], first["revision"])

    def test_registry_fingerprint_catches_external_cli_edit(self):
        old_fingerprint = self.fp()
        registry = runtime.read_registry(self.project)
        registry["external_cli_edit"] = True
        runtime.atomic_json(runtime.confined(self.project, "00-control/registry.json"), registry)
        with self.assertRaises(daily.ConflictError):
            daily.record_risk(self.project, {"entry_id": "R-CLI", "title": "外部修改", "owner": "A"}, expected_registry_fingerprint=old_fingerprint)

    def test_change_is_proposal_only_and_does_not_infer_signer(self):
        with self.assertRaises(ValueError):
            daily.record_change(self.project, {
                "change_id": "CHG-BAD", "state": "approved", "reason": "不应由此接口批准",
                "affected_ids": ["PLAN"], "impact": {"schedule": "待评估"},
            }, expected_registry_fingerprint=self.fp())
        result = daily.record_change(self.project, {
            "change_id": "CHG-1", "reason": "需求发生变化", "affected_ids": ["PLAN"],
            "impact": {"schedule": "待评估", "cost": "待评估"},
        }, expected_registry_fingerprint=self.fp())
        artifact = runtime.load_artifact(self.project, result["ref"])
        self.assertEqual(artifact["data"]["state"], "proposed")
        self.assertNotIn("actor", artifact["data"])
        self.assertEqual(runtime.read_registry(self.project)["effective"], {})
        with self.assertRaises(daily.ConflictError):
            daily.record_change(self.project, {
                "change_id": "CHG-1", "reason": "过期编辑", "affected_ids": ["PLAN"],
                "impact": {"schedule": "待评估"},
            }, expected_revision=0, expected_registry_fingerprint=self.fp())
        revised = daily.record_change(self.project, {
            "change_id": "CHG-1", "reason": "补充影响说明", "affected_ids": ["PLAN"],
            "impact": {"schedule": "两天"},
        }, expected_revision=1, expected_registry_fingerprint=self.fp())
        self.assertEqual(revised["change"]["state"], "proposed")
        collision_source = Path(self.temp.name) / "collision.txt"
        collision_source.write_text("collision", encoding="utf-8")
        runtime.source(self.project, collision_source, "COLLIDE")
        with self.assertRaises(ValueError):
            daily.record_change(self.project, {
                "change_id": "COLLIDE", "reason": "冲突", "affected_ids": ["PLAN"],
                "impact": {"schedule": "待评估"},
            }, expected_registry_fingerprint=self.fp())

    def test_risk_state_change_revises_same_row_and_requires_evidence_to_close(self):
        first = daily.record_risk(self.project, {"entry_id": "R1", "title": "接口风险", "owner": "A"}, expected_registry_fingerprint=self.fp())
        with self.assertRaises(ValueError):
            daily.record_risk(self.project, {"entry_id": "R1", "title": "接口风险", "owner": "A", "status": "closed"}, expected_revision=first["revision"], expected_registry_fingerprint=self.fp())
        second = daily.record_risk(self.project, {
            "entry_id": "R1", "title": "接口风险", "owner": "A", "status": "closed", "evidence_refs": [self.evidence_ref],
        }, expected_revision=first["revision"], expected_registry_fingerprint=self.fp())
        self.assertEqual(second["revision"], 2)
        latest = runtime.load_artifact(self.project, runtime.latest_ref(self.project, "RISKS"))
        self.assertEqual(latest["data"]["items"][0]["status"], "closed")

    def test_existing_master_ids_inputs_and_effective_refs_are_preserved(self):
        info = runtime.read_project(self.project)
        existing_hours = runtime.register(self.project, {
            "project_id": info["project_id"], "artifact_id": "TS", "revision": 1,
            "kind": "timesheets", "visibility": "internal", "status": "ready",
            "inputs": [self.evidence_ref],
            "data": {"items": [], "remaining_labor": None, "evidence_refs": [self.evidence_ref]},
        })
        existing_risks = runtime.register(self.project, {
            "project_id": info["project_id"], "artifact_id": "RISK", "revision": 1,
            "kind": "risks", "visibility": "internal", "status": "ready",
            "inputs": [self.evidence_ref],
            "data": {"items": [{"id": "R1", "type": "risk", "title": "已有风险", "owner": "A", "status": "open", "trigger": "供应商未响应", "action": "观察", "due": "", "evidence_refs": [self.evidence_ref]}]},
        })
        runtime.activate(self.project, ["TS", "RISK"])
        runtime.register(self.project, {
            "project_id": info["project_id"], "artifact_id": "WEEKLY", "revision": 1,
            "kind": "weekly", "visibility": "internal", "status": "ready", "inputs": [],
            "data": {"period": "2026-10-12/2026-10-18", "as_of": "2026-10-12", "completed": [], "next": [], "milestones": [], "risks": [], "decisions_required": [], "coverage_gaps": []},
        })
        runtime.register(self.project, {
            "project_id": info["project_id"], "artifact_id": "PLAN", "revision": 1,
            "kind": "plan", "visibility": "internal", "status": "ready", "inputs": [],
            "data": {"work_packages": [{
                "id": "WP1", "title": "已登记工作包", "owner": "A", "baseline_start": "2026-10-12",
                "baseline_finish": "2026-10-18", "forecast_finish": "2026-10-18", "dependencies": [],
                "requirement_ids": [], "completion_rule": "evidence", "status": "planned",
            }], "milestones": []},
        })
        runtime.activate(self.project, ["PLAN"])
        with self.assertRaises(ValueError):
            daily.record_hours(self.project, {"entry_id": "BAD", "person": "A", "work_package_id": "WP-X", "hours": 1}, expected_registry_fingerprint=self.fp())
        progress = daily.record_progress(self.project, {
            "entry_id": "OP-REAL", "work_package_id": "WP1", "status": "completed", "summary": "真实工作包完成", "evidence_refs": [self.evidence_ref],
        }, expected_registry_fingerprint=self.fp())
        self.assertEqual(progress["ref"]["artifact_id"], "DAILY-PROGRESS")
        self.assertEqual(runtime.latest_ref(self.project, "WEEKLY")["revision"], 1)
        hours = daily.record_hours(self.project, {
            "entry_id": "H1", "person": "A", "work_package_id": "WP1", "hours": 1,
        }, expected_revision=1, expected_registry_fingerprint=self.fp())
        self.assertEqual(hours["ledger_id"], "TS")
        risk = daily.record_risk(self.project, {
            "entry_id": "R1", "title": "已有风险", "owner": "A", "status": "closed",
            "evidence_refs": [self.evidence_ref],
        }, expected_revision=1, expected_registry_fingerprint=self.fp())
        self.assertEqual(risk["ledger_id"], "RISK")
        latest_hours = runtime.load_artifact(self.project, runtime.latest_ref(self.project, "TS"))
        latest_risks = runtime.load_artifact(self.project, runtime.latest_ref(self.project, "RISK"))
        self.assertIn(self.evidence_ref, latest_hours["inputs"])
        self.assertIn(self.evidence_ref, latest_risks["inputs"])
        self.assertEqual(latest_risks["data"]["items"][0]["trigger"], "供应商未响应")
        registry = runtime.read_registry(self.project)
        self.assertEqual(registry["effective"]["TS"], existing_hours)
        self.assertEqual(registry["effective"]["RISK"], existing_risks)


if __name__ == "__main__":
    unittest.main()
