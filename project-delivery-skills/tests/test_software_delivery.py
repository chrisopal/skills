"""Synthetic software-delivery evidence and gate checks.

Every fixture is deliberately synthetic and runs in a simulation project.  These
tests exercise the public runtime/register/snapshot/prepare_customer APIs; they
do not claim real customer approval, production execution, or evidence
authenticity.
"""

from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


RUNTIME = Path(__file__).resolve().parents[1] / "skills/delivery-orchestrator/scripts/runtime.py"


def load_runtime():
    spec = importlib.util.spec_from_file_location("delivery_runtime_software_tests", RUNTIME)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class SoftwareDeliveryTests(unittest.TestCase):
    """Focused phase-two checks without inheriting the first-batch test suite."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.project = self.base / "project"
        self.r = load_runtime()
        self.r.init_project(self.project, "TEST-001", purpose="simulation")
        source = self.base / "synthetic-contract.txt"
        source.write_text("SIMULATION ONLY: synthetic contract and test evidence.", encoding="utf-8")
        self.src = self.r.source(self.project, source, "SRC")
        self.req_ref = self.requirements()

    def register(self, artifact):
        return self.r.register(self.project, artifact)

    def artifact(self, aid, kind, data, inputs=None, visibility="internal", status="ready", revision=1):
        return self.register({
            "project_id": "TEST-001",
            "artifact_id": aid,
            "revision": revision,
            "kind": kind,
            "visibility": visibility,
            "status": status,
            "inputs": inputs if inputs is not None else [self.req_ref, self.src],
            "data": data,
        })

    def requirements(self, items=None, aid="REQ", revision=1):
        items = items if items is not None else [{
            "id": "R1",
            "statement": "Create a work order",
            "source_refs": [self.src],
            "acceptance": "Saved work order is read back",
            "priority": "must",
        }]
        return self.artifact(
            aid,
            "requirements",
            {"items": items, "open_items": []},
            inputs=[self.src],
            visibility="customer",
            revision=revision,
        )

    @staticmethod
    def build(revision="build-1", character="a"):
        return {"repository": "synthetic/repository", "revision": revision, "sha256": character * 64}

    def solution_data(self, requirement_ids=None, decision_status="decided", component_id="C1"):
        requirement_ids = requirement_ids if requirement_ids is not None else ["R1"]
        selected = "service boundary" if decision_status == "decided" else ""
        rationale = "Keeps the synthetic module independently deployable" if decision_status == "decided" else ""
        evidence = [self.src] if decision_status == "decided" else []
        return {
            "requirement_ids": requirement_ids,
            "components": [{
                "id": component_id,
                "purpose": "Work-order service",
                "requirement_ids": requirement_ids,
                "deployment": "synthetic-test",
                "security": "role boundary",
                "nonfunctional": "p95 under synthetic target",
            }],
            "decisions": [{
                "id": "D1",
                "question": "Where does validation live?",
                "options": ["service boundary", "client only"],
                "selected": selected,
                "rationale": rationale,
                "status": decision_status,
                "evidence_refs": evidence,
            }],
        }

    def solution(self, aid="SOL", requirement_ids=None, decision_status="decided", component_id="C1"):
        return self.artifact(aid, "solution", self.solution_data(requirement_ids, decision_status, component_id))

    def ui_data(self, requirement_ids=None, cross_page=False, bad_state=False):
        requirement_ids = requirement_ids if requirement_ids is not None else ["R1"]
        return {
            "requirement_ids": requirement_ids,
            "pages": [
                {"id": "P1", "title": "Create order", "requirement_ids": requirement_ids, "states": ["draft", "submitted"]},
                {"id": "P2", "title": "Review order", "requirement_ids": [], "states": ["draft", "submitted"]},
            ],
            "fields": [
                {"id": "F1", "page_id": "P1", "type": "string", "length": 100, "precision": 0, "unit": "text",
                 "required": True, "default": "", "enum": [], "validation": "non-empty", "source": "user",
                 "sensitivity": "internal"},
                {"id": "F2", "page_id": "P2", "type": "string", "length": 50, "precision": 0, "unit": "text",
                 "required": False, "default": "", "enum": [], "validation": "none", "source": "system",
                 "sensitivity": "internal"},
            ],
            "permissions": [{
                "id": "PERM1", "page_id": "P1", "field_ids": ["F2" if cross_page else "F1"],
                "role": "dispatcher", "action": "write", "condition": "draft", "effect": "allow",
            }],
            "states": [{
                "id": "ST1", "page_id": "P1", "from": "missing" if bad_state else "draft",
                "action": "submit", "to": "submitted", "allowed_roles": ["dispatcher"], "error": "Cannot submit",
            }],
        }

    def ui_design(self, aid="UI", **kwargs):
        return self.artifact(aid, "ui_design", self.ui_data(**kwargs))

    def integration_data(self, requirement_ids=None, interface_status="designed", reconciliation_state="pass",
                         reconciliation_counts=None, migration=None):
        requirement_ids = requirement_ids if requirement_ids is not None else ["R1"]
        migration = migration or {"applicable": False, "reason": "No migration in this synthetic module"}
        if reconciliation_state == "pass":
            counts = reconciliation_counts or [{"name": "records", "state": "pass", "actual": 10, "expected": 10}]
            keys = [{"name": "business keys", "state": "pass", "expected": ["A1"], "actual": ["A1"]}]
            evidence = [self.src]
        else:
            counts, keys, evidence = [], [], []
        return {
            "requirement_ids": requirement_ids,
            "interfaces": [{
                "id": "API1", "owner": "integration-owner", "source_system": "Order",
                "target_system": "ThirdParty", "direction": "outbound", "trigger": "order.saved",
                "protocol": "HTTPS", "auth_method": "synthetic-token", "environment": "test",
                "status": interface_status, "idempotency": "order_id", "timeout": "5s", "retry": "3",
                "compensation": "dead-letter review",
            }],
            "mappings": [{
                "id": "MAP1", "interface_id": "API1", "source_field": "order_id", "target_field": "external_id",
                "type": "string", "unit": "text", "transform": "identity", "business_key": True,
            }],
            "reconciliations": [{
                "id": "REC1", "interface_id": "API1", "state": reconciliation_state,
                "build_ref": self.build(), "environment": "test", "counts": counts,
                "business_keys": keys, "evidence_refs": evidence,
            }],
            "migration": migration,
        }

    def integration(self, aid="INT", **kwargs):
        return self.artifact(aid, "integration", self.integration_data(**kwargs))

    def plan(self, aid="PLAN"):
        return self.artifact(aid, "plan", {
            "work_packages": [{
                "id": "WP1", "title": "Build order module", "owner": "delivery-owner",
                "baseline_start": "2026-10-11", "baseline_finish": "2026-10-20", "forecast_finish": "2026-10-20",
                "dependencies": [], "requirement_ids": ["R1"], "completion_rule": "build and evidence readback",
                "status": "planned",
            }],
            "milestones": [],
        })

    def work_package(self, aid="WP", state="completed", build_ref=None, evidence_refs=None, design_ref=None):
        plan_ref = self.plan()
        design_ref = design_ref or self.solution()
        return self.artifact(aid, "work_package", {
            "plan_work_package_id": "WP1", "requirement_ids": ["R1"], "design_refs": [design_ref],
            "completion_rule": "build and evidence readback", "build_ref": build_ref,
            "evidence_refs": evidence_refs if evidence_refs is not None else [self.src], "state": state,
        }, inputs=[self.req_ref, plan_ref, design_ref, self.src])

    def make_testing_data(self, build_ref=None, case_state="pass", uat_state="accepted", uat_origin="simulation",
                     defects=None, uat_open_items=None):
        build_ref = build_ref or self.build()
        return {
            "requirement_ids": ["R1"], "environment": "test", "build_ref": build_ref,
            "cases": [{
                "id": "T1", "requirement_ids": ["R1"], "steps": ["save", "reopen"] if case_state != "not_run" else [],
                "expected": "same value" if case_state != "not_run" else "", "actual": "same value" if case_state != "not_run" else "",
                "state": case_state, "evidence_refs": [self.src] if case_state != "not_run" else [],
            }],
            "defects": defects or [],
            "uat": {
                "state": uat_state, "scope_requirement_ids": ["R1"], "actor": "Synthetic representative",
                "role": "test fixture", "origin": uat_origin,
                "evidence_refs": [self.src] if uat_state != "pending" else [],
                "open_items": uat_open_items or [],
            },
        }

    def make_testing(self, aid="TESTING", **kwargs):
        return self.artifact(aid, "testing", self.make_testing_data(**kwargs))

    def release_data(self, testing_ref, execution_state="planned", rollback_state="planned", build_ref=None,
                     readiness_state="pass", rollback_evidence=None, restore_refs=None):
        build_ref = build_ref or self.build()
        rollback_evidence = rollback_evidence if rollback_evidence is not None else []
        restore_refs = restore_refs if restore_refs is not None else []
        return {
            "environment": "staging", "build_ref": build_ref, "testing_ref": testing_ref,
            "readiness": [{"id": key, "title": key, "state": readiness_state,
                            "owner": "release-owner", "evidence_refs": [self.src] if readiness_state == "pass" else []}
                           for key in ("backup", "rollback", "window", "monitoring", "authorization")],
            "execution": {
                "state": execution_state, "evidence_refs": [self.src] if execution_state != "planned" else [],
                "verification_refs": [self.src] if execution_state == "succeeded" else [],
            },
            "rollback": {
                "state": rollback_state, "plan": "restore synthetic snapshot",
                "evidence_refs": rollback_evidence, "restore_refs": restore_refs,
            },
        }

    def release(self, aid="REL", testing_ref=None, inputs=None, revision=1, **kwargs):
        testing_ref = testing_ref or self.make_testing()
        return self.artifact(aid, "release", self.release_data(testing_ref, **kwargs),
                             inputs=inputs or [testing_ref, self.src], revision=revision)

    def handover_data(self, competency="pass", operations_state="accepted", open_items=None, credentials=False):
        operations = {
            "owner": "operations-owner", "state": operations_state, "runbook_refs": [self.src],
            "receipt_refs": [self.src],
        }
        if credentials:
            operations["password"] = "synthetic-secret-should-never-ship"
        return {
            "audiences": [{"id": "AUD1", "role": "operator", "owner": "operations-owner"}],
            "training": [{"id": "TRAIN1", "audience_id": "AUD1", "attendance": True,
                           "competency": competency, "evidence_refs": [self.src] if competency == "pass" else []}],
            "operations": operations,
            "assets": [{"id": "ASSET1", "owner": "operations-owner", "version": "r1", "evidence_refs": [self.src]}],
            "open_items": open_items or [],
        }

    def handover(self, aid="HAND", visibility="internal", **kwargs):
        return self.artifact(aid, "handover", self.handover_data(**kwargs), visibility=visibility)

    def review(self, target):
        return self.artifact("REVIEW", "review", {
            "targets": [target], "verdict": "pass", "reviewer": "Synthetic reviewer",
            "method": "independent-fixture-review", "findings": [], "unchecked": [], "scope": ["customer boundary"],
        }, inputs=[target, self.src], visibility="internal")

    def test_failed_reconciliation_on_another_build_blocks_integration(self):
        data = self.integration_data(interface_status="verified")
        failed = copy.deepcopy(data['reconciliations'][0])
        failed.update(id='REC2', state='fail', build_ref=self.build('new-build', 'b'))
        data['reconciliations'].append(failed)
        self.artifact('INT', 'integration', data)
        self.assertFalse(self.r.snapshot(self.project)['gates']['INT']['ready'])

    def test_undetailed_page_blocks_ui_gate(self):
        self.ui_design()
        self.assertFalse(self.r.snapshot(self.project)['gates']['UI']['ready'])

    def test_nested_credential_key_families_are_blocked_and_filtered(self):
        for key in ('private_key', 'apiKey', 'client-secret', 'refreshToken', 'Authorization', 'credential', 'token'):
            with self.subTest(key=key):
                with self.assertRaises(ValueError):
                    self.r.customer_fields({'operations': [{key: 'SYNTHETIC-SECRET'}]}, reject=True)
                self.assertEqual(self.r.customer_fields({'operations': [{key: 'SYNTHETIC-SECRET'}]}), {'operations': [{}]})

    def test_passing_label_cannot_hide_count_mismatch(self):
        data = self.integration_data(interface_status="verified")
        data["reconciliations"][0]["counts"][0]["actual"] = 9
        with self.assertRaisesRegex(ValueError, "unequal"):
            self.artifact("INT", "integration", data)

    def test_one_readiness_check_cannot_authorize_release(self):
        tested = self.make_testing()
        data = self.release_data(tested)
        data["readiness"] = data["readiness"][:1]
        self.artifact("REL", "release", data, inputs=[tested, self.src])
        self.assertFalse(self.r.snapshot(self.project)["gates"]["REL"]["ready_to_execute"])

    def test_failed_execution_does_not_automatically_authorize_retry(self):
        self.release(execution_state="failed")
        self.assertFalse(self.r.snapshot(self.project)["gates"]["REL"]["ready_to_execute"])

    def test_solution_exact_version_and_gate(self):
        solution = self.solution()
        loaded = self.r.load_artifact(self.project, solution)
        snapshot = self.r.snapshot(self.project)
        record = next(item for item in snapshot["artifacts"] if item["artifact_id"] == "SOL")
        self.assertEqual(loaded["inputs"][0], self.req_ref)
        self.assertEqual(record["revision"], solution["revision"])
        self.assertEqual(record["sha256"], solution["sha256"])
        self.assertTrue(snapshot["gates"]["SOL"]["ready"])
        self.assertEqual(solution["revision"], 1)

    def test_missing_requirement_ids_rejected(self):
        with self.assertRaises(ValueError):
            self.solution(requirement_ids=[])

    def test_foreign_requirement_ids_rejected(self):
        with self.assertRaises(ValueError):
            self.solution(requirement_ids=["R999"])

    def test_ui_permission_cross_page_rejected(self):
        with self.assertRaises(ValueError):
            self.ui_design(cross_page=True)

    def test_ui_unknown_state_rejected(self):
        with self.assertRaises(ValueError):
            self.ui_design(bad_state=True)

    def test_unknown_third_party_interface_blocks_gate(self):
        self.integration(interface_status="unknown", reconciliation_state="not_run")
        gate = self.r.snapshot(self.project)["gates"]["INT"]
        self.assertFalse(gate["ready"])
        self.assertTrue(any("verified" in reason for reason in gate["reasons"]))

    def test_verified_interface_without_reconciliation_rejected(self):
        with self.assertRaises(ValueError):
            self.integration(interface_status="verified", reconciliation_state="not_run")

    def test_business_count_mismatch_cannot_pass_reconciliation(self):
        with self.assertRaises(ValueError):
            self.integration(interface_status="verified", reconciliation_counts=[
                {"name": "records", "state": "fail", "actual": 9, "expected": 10},
            ])

    def test_migration_completion_requires_backup_and_rehearsal(self):
        base = {"applicable": True, "owner": "migration-owner", "state": "completed",
                "backup_refs": [self.src], "rollback_plan": "restore snapshot", "freeze_window": "synthetic",
                "rehearsal_refs": [self.src], "reconciliation_refs": [self.src]}
        for field in ("backup_refs", "rehearsal_refs"):
            mutation = copy.deepcopy(base)
            mutation[field] = []
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.integration(migration=mutation)

    def test_completed_package_requires_actual_build_and_evidence(self):
        for build_ref, evidence_refs in ((None, [self.src]), (self.build(), [])):
            with self.subTest(build_ref=build_ref, evidence_refs=evidence_refs), self.assertRaises(ValueError):
                self.work_package(build_ref=build_ref, evidence_refs=evidence_refs)

    def test_work_package_planned_is_separate_from_completed_gate(self):
        self.work_package(state="planned", build_ref=None, evidence_refs=[])
        gate = self.r.snapshot(self.project)["gates"]["WP"]
        self.assertFalse(gate["ready"])
        self.assertTrue(any("completed" in reason for reason in gate["reasons"]))

    def test_not_run_case_keeps_testing_gate_false(self):
        self.make_testing(case_state="not_run", uat_state="pending")
        gate = self.r.snapshot(self.project)["gates"]["TESTING"]
        self.assertFalse(gate["ready"])

    def test_closed_defect_without_passing_retest_rejected(self):
        defect = [{"id": "D1", "case_id": "T1", "severity": "major", "state": "closed",
                   "owner": "developer", "retest_case_id": "T1", "retest_refs": []}]
        with self.assertRaises(ValueError):
            self.make_testing(defects=defect)

    def test_conditional_uat_keeps_testing_gate_false(self):
        self.make_testing(uat_state="conditional", uat_open_items=["R1 follow-up"])
        gate = self.r.snapshot(self.project)["gates"]["TESTING"]
        self.assertFalse(gate["ready"])
        self.assertTrue(any("UAT" in reason for reason in gate["reasons"]))

    def test_simulated_uat_refused_in_internal_project(self):
        project_file = self.r.project_path(self.project)
        project_data = json.loads(project_file.read_text(encoding="utf-8"))
        project_data["purpose"] = "internal"
        project_file.write_text(json.dumps(project_data), encoding="utf-8")
        with self.assertRaises(ValueError):
            self.make_testing(uat_state="accepted", uat_origin="simulation")

    def test_release_planned_readiness_is_not_delivered(self):
        testing_ref = self.make_testing()
        self.release(testing_ref=testing_ref, execution_state="planned", rollback_state="planned")
        gate = self.r.snapshot(self.project)["gates"]["REL"]
        self.assertFalse(gate["ready"])
        self.assertTrue(gate["ready_to_execute"])
        self.assertTrue(any("succeed" in reason for reason in gate["reasons"]))

    def test_release_succeeded_with_business_verification_is_delivered(self):
        testing_ref = self.make_testing()
        self.release(testing_ref=testing_ref, execution_state="planned", rollback_state="planned")
        self.release(testing_ref=testing_ref, execution_state="succeeded", rollback_state="not_needed", revision=2)
        gate = self.r.snapshot(self.project)["gates"]["REL"]
        self.assertTrue(gate["ready"])
        self.assertFalse(gate["ready_to_execute"])

    def test_new_build_mismatch_release_rejected(self):
        testing_ref = self.make_testing(build_ref=self.build("build-1", "a"))
        with self.assertRaises(ValueError):
            self.release(testing_ref=testing_ref, build_ref=self.build("build-2", "b"))

    def test_failed_release_with_restored_rollback_is_not_delivered(self):
        testing_ref = self.make_testing()
        self.release(testing_ref=testing_ref, execution_state="failed", rollback_state="succeeded",
                     rollback_evidence=[self.src], restore_refs=[self.src])
        gate = self.r.snapshot(self.project)["gates"]["REL"]
        self.assertFalse(gate["ready"])
        self.assertFalse(gate["ready_to_execute"])

    def test_failed_rollback_cannot_claim_rolled_back(self):
        testing_ref = self.make_testing()
        with self.assertRaises(ValueError):
            self.release(testing_ref=testing_ref, execution_state="rolled_back", rollback_state="failed")

    def test_attendance_only_handover_keeps_gate_false(self):
        self.handover(competency="not_checked")
        gate = self.r.snapshot(self.project)["gates"]["HAND"]
        self.assertFalse(gate["ready"])
        self.assertTrue(any("competency" in reason or "Attendance" in reason for reason in gate["reasons"]))

    def test_customer_output_rejects_credentials(self):
        handover = self.handover(visibility="customer", credentials=True)
        self.review(handover)
        with self.assertRaises(ValueError):
            self.r.prepare_customer(self.project, ["HAND"], self.base / "customer-pack")

    def test_stale_design_source_invalidates_relevant_gate(self):
        self.solution()
        source_path = self.base / "synthetic-contract.txt"
        source_path.write_text("SIMULATION ONLY: revised source.", encoding="utf-8")
        self.r.source(self.project, source_path, "SRC")
        snapshot = self.r.snapshot(self.project)
        solution_record = next(item for item in snapshot["artifacts"] if item["artifact_id"] == "SOL")
        self.assertEqual(solution_record["health"], "stale")
        self.assertFalse(snapshot["gates"]["SOL"]["ready"])

    def test_two_module_records_have_separate_gates(self):
        self.solution(aid="SOL-A", component_id="CA")
        self.solution(aid="SOL-B", component_id="CB", decision_status="proposed")
        gates = self.r.snapshot(self.project)["gates"]
        self.assertTrue(gates["SOL-A"]["ready"])
        self.assertFalse(gates["SOL-B"]["ready"])


if __name__ == "__main__":
    unittest.main()
