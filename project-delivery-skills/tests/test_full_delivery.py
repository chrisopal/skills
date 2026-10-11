"""One complete portable simulation; negative checks clone only its runtime."""
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

SUITE = Path(__file__).resolve().parents[1]
SCRIPTS = SUITE / "scripts"


def load_runner():
    # The executable imports its existing sibling helper. Keep this import
    # scoped rather than requiring package installation or a new dependency.
    sys.path.insert(0, str(SCRIPTS))
    try:
        spec = importlib.util.spec_from_file_location("test_full_delivery_runner", SCRIPTS / "verify_full_delivery.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.pop(0)


class FullDeliveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.base = Path(cls.temp.name)
        cls.out = cls.base / "complete-case"
        cls.out.mkdir()
        cls.runner = load_runner()
        # A fresh clone has no root output/preflight directory. The entire case
        # must still execute current engineering tests without fake history.
        cls.report = cls.runner.build_case(cls.out, preflight_dir=cls.base / "missing-preflight")
        cls.runtime = cls.runner.phase.load_module(cls.runner.phase.RUNTIME_PATH, "test_full_runtime")
        cls.project = cls.out / "project"
        cls.snapshot = json.loads((cls.out / "snapshot.json").read_text(encoding="utf-8"))

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_all_25_tasks_bind_real_skill_and_exact_runtime_refs(self):
        runs = self.report["skill_runs"]
        expected = {path.parent.name for path in (SUITE / "skills").glob("delivery-*/SKILL.md")}
        self.assertEqual(len(runs), 25)
        self.assertEqual({run["skill"] for run in runs}, expected)
        for run in runs:
            with self.subTest(skill=run["skill"]):
                self.assertEqual(run["skill_sha256"], self.runner.phase.digest(SUITE / run["skill_source"]))
                for group in ("input_refs", "output_refs", "evidence_refs"):
                    self.assertTrue(run[group])
                    for ref in run[group]:
                        self.runtime.check_ref(self.project, ref)
                self.assertIn("simulation", run["boundary"])

    def test_full_lifecycle_has_distinct_streams_and_all_artifact_kinds(self):
        expected = {"evidence", "contract", "kickoff", "discovery", "minutes", "requirements", "blueprint", "plan",
                    "timesheets", "costs", "risks", "change", "weekly", "milestone", "confirmation", "review",
                    "solution", "ui_design", "integration", "work_package", "testing", "release", "handover", "closure"}
        self.assertLessEqual(expected, {record["kind"] for record in self.snapshot["artifacts"]})
        plan = next(record["data"] for record in self.snapshot["artifacts"] if record["kind"] == "plan")
        self.assertEqual({row["id"] for row in plan["work_packages"]}, {"WP-ANALYSIS", "WP-APP", "WP-INT", "WP-QA", "WP-RELEASE"})
        self.assertEqual(len(plan["milestones"]), 5)
        self.assertEqual(len([record for record in self.snapshot["artifacts"] if record["kind"] == "work_package"]), 5)
        self.assertTrue(self.report["validation"]["ok"])
        self.assertFalse(self.snapshot["alerts"])
        self.assertTrue(all(check["passed"] for check in self.report["checks"]))

    def test_actual_engineering_and_simulated_acceptance_are_separate(self):
        self.assertEqual(self.report["test_status"]["tests_run"], 13)
        self.assertTrue(self.report["test_status"]["successful"])
        operations = json.loads((self.out / "engineering-operations.json").read_text(encoding="utf-8"))
        self.assertTrue(operations["rollback_restored"])
        self.assertEqual(operations['before_backup_row'], operations['after_restore_row'])
        self.assertEqual(operations['after_restore_row']['state'], 'approved')
        self.assertEqual(operations["after_migration"]["business_keys"], ["O1", "O2"])
        self.assertEqual(operations["after_restore"]["business_keys"], ["O1"])
        self.assertFalse(operations["local_release"]["production"])
        testing = next(record["data"] for record in self.snapshot["artifacts"] if record["kind"] == "testing")
        self.assertEqual(testing["uat"]["origin"], "simulation")
        self.assertEqual({rid for case in testing["cases"] for rid in case["requirement_ids"]}, {"R1", "R2", "R3"})
        for record in self.snapshot["artifacts"]:
            if record["kind"] == "confirmation":
                self.assertEqual(record["data"]["origin"], "simulation")
        self.assertFalse(self.report["boundary"]["production_executed"])
        self.assertFalse(self.report["boundary"]["real_customer_signatures"])

    def test_design_confirmation_has_explicit_fields_permissions_and_data(self):
        blueprint = next(a['data'] for a in self.snapshot['artifacts'] if a['kind']=='blueprint')
        permissions = {row['id'] for row in blueprint['permissions']}
        data = {row['id'] for row in blueprint['data']}
        fields = {row['id'] for row in blueprint['fields']}
        for row in blueprint['coverage']:
            self.assertTrue(set(row['permission_ids']) <= permissions)
            self.assertTrue(set(row['data_ids']) <= data)
            self.assertTrue(set(row['design_ids']) & fields)
        ui = next(a['data'] for a in self.snapshot['artifacts'] if a['kind']=='ui_design')
        for page in ui['pages']:
            for key in ('entry','exit','flow_ids','visible_buttons','preconditions','success_result','failure_recovery','audit_event','operations'):
                self.assertTrue(page[key])
        for field in ui['fields']:
            for key in ('business_meaning','unique','visibility','read_write','calculation','interface_mapping','exception_display'):
                self.assertIn(key, field)
        cases = next(a['data']['cases'] for a in self.snapshot['artifacts'] if a['kind']=='testing')
        self.assertNotIn('503', json.dumps(cases))
        costs = next(a['data'] for a in self.snapshot['artifacts'] if a['kind']=='costs')
        self.assertIsNone(costs['warranty_cost_estimate'])
        self.assertIn('质保', costs['forecast_scope'])

    def test_unapproved_rejection_atomic_change_and_nonduplicated_finance(self):
        self.assertIn("approved", self.report["unapproved_change_rejection"])
        effective = self.snapshot["effective"]
        self.assertEqual(effective["PLAN"]["revision"], 2)
        self.assertEqual(effective["COST"]["revision"], 2)
        self.assertEqual({ref["artifact_id"] for ref in self.report["change_application"]["replacements"]}, {"PLAN", "COST"})
        summary = self.report["cost_summary"]
        self.assertTrue(summary["complete"])
        self.assertEqual(summary["forecast"], "6600.00")
        self.assertEqual(summary["internal_labor"], "4200.00")
        self.assertEqual(summary["other_incurred"], "2400.00")
        self.assertEqual(summary["budget"], "8500.00")
        self.assertEqual(summary["estimated_remaining"], "0.00")
        plan = next(record["data"] for record in self.snapshot["artifacts"] if record["kind"] == "plan")
        integration = next(row for row in plan["work_packages"] if row["id"] == "WP-INT")
        self.assertEqual(integration["original_baseline_finish"], "2026-10-09")
        self.assertEqual(integration["baseline_finish"], "2026-10-10")
        self.assertEqual(integration["variance_days"], 1)

    def test_actual_review_rejection_correction_and_visual_limits(self):
        self.assertIn("conditional review", self.report["review_rejection"])
        review = self.runtime.load_artifact(self.project, self.runtime.latest_ref(self.project, "REVIEW"))
        self.assertEqual(review["revision"], 2)
        self.assertEqual(review["data"]["verdict"], "pass")
        self.assertEqual(review["data"]["findings"][0]["status"], "closed")
        self.assertTrue(review["data"]["findings"][0]["resolution_evidence"])
        self.assertFalse(review["data"]["actual_visual_audit_pass"])
        self.assertTrue(any("Office" in value for value in review["data"]["unchecked"]))
        self.assertFalse((self.out / "rejected-customer-package").exists())
        planned, executed = self.report["release_gate_snapshots"].values()
        self.assertTrue(planned["ready_to_execute"])
        self.assertFalse(planned["ready"])
        self.assertTrue(executed["ready"])
        self.assertFalse(executed["ready_to_execute"])

    def test_portable_case_has_runnable_artifacts_without_historical_failure_claims(self):
        self.assertFalse(self.report["historical_defect_evidence_available"])
        self.assertIn("unavailable", self.report["historical_defect_gap"])
        testing = next(record["data"] for record in self.snapshot["artifacts"] if record["kind"] == "testing")
        self.assertEqual(testing["defects"], [])
        engineering = self.out / "materials/engineering"
        for path in (engineering / "test_local_engineering.py", engineering / "test_local_engineering_boundaries.py", engineering / "fixtures/work_order_service.py"):
            self.assertTrue(path.is_file())
        self.assertEqual(self.runner.phase.digest(engineering / "fixtures/work_order_service.py"), self.report["build_ref"]["sha256"])
        findings = (self.out / "review-findings.md").read_text(encoding="utf-8")
        self.assertIn("历史失败日志未提供", findings)
        self.assertNotIn("DEF-CONC-001 的失败日志", findings)

    def test_closure_cannot_confuse_administration_with_warranty_end(self):
        gate = self.report["closure_gate"]
        self.assertTrue(gate["administrative_closed"])
        self.assertTrue(gate["warranty_transferred"])
        self.assertFalse(gate["warranty_ended"])
        self.assertFalse(gate["fully_discharged"])
        self.assertFalse(gate["ready"])
        self.assertTrue(any("not passed" in reason for reason in gate["reasons"]))
        closure = next(record["data"] for record in self.snapshot["artifacts"] if record["kind"] == "closure")
        self.assertEqual(closure["settlement"]["state"], "reconciled")
        self.assertTrue(any(row["state"] == "transferred" for row in closure["obligations"]))
        self.assertTrue(any(row["state"] == "open" for row in closure["warranty"]["items"]))

    def test_tampered_clone_fails_validation_without_rerunning_engineering(self):
        clone = self.base / "tampered-clone"
        shutil.copytree(self.project, clone)
        target = self.runtime.latest_ref(clone, "REQ")
        path = self.runtime.artifact_path(clone, target)
        path.write_text(path.read_text(encoding="utf-8") + " ", encoding="utf-8")
        result = self.runtime.validate(clone)
        self.assertFalse(result["ok"])
        self.assertTrue(any("REQ" in value for value in result["errors"]))

    def test_cli_refuses_existing_output_before_work(self):
        process = subprocess.run([sys.executable, str(SCRIPTS / "verify_full_delivery.py"), "--out", str(self.out)], capture_output=True, text=True)
        self.assertEqual(process.returncode, 2)
        self.assertIn("Refusing existing output directory", process.stderr)


if __name__ == "__main__":
    unittest.main()
