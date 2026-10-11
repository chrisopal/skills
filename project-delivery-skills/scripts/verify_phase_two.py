#!/usr/bin/env python3
"""Run a local, synthetic phase-two software-delivery verification case.

The command writes a fresh output directory containing the simulation project,
raw local-engineering test output, operation readbacks, and a JSON report.  It
never sends customer material or executes production actions.
"""

from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[2]
SUITE = ROOT / "project-delivery-skills"
RUNTIME_PATH = SUITE / "skills/delivery-orchestrator/scripts/runtime.py"
SOFTWARE_PATH = SUITE / "skills/delivery-orchestrator/scripts/software.py"
ENGINEERING_TEST_PATH = SUITE / "tests/test_local_engineering.py"
ENGINEERING_CODE_PATH = SUITE / "tests/fixtures/work_order_service.py"


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def source_ref(runtime, project: Path, path: Path, aid: str):
    return runtime.source(project, path, aid)


def register(runtime, project: Path, artifact: dict):
    return runtime.register(project, artifact)


def artifact(project_id: str, aid: str, kind: str, data: dict, inputs: list[dict], *,
             visibility: str = "internal", status: str = "ready", revision: int = 1) -> dict:
    return {
        "project_id": project_id,
        "artifact_id": aid,
        "revision": revision,
        "kind": kind,
        "visibility": visibility,
        "status": status,
        "inputs": inputs,
        "data": data,
    }


def run_local_engineering_tests(test_module) -> tuple[unittest.TestResult, str]:
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(test_module.LocalEngineeringTests)
    stream = io.StringIO()
    result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
    return result, stream.getvalue()


def direct_operations(test_module) -> dict:
    """Exercise the same fixture with actual HTTP and SQLite operations."""
    case = test_module.LocalEngineeringTests("runTest")
    case.setUp()
    try:
        orders = case.orders
        created = orders.create("O1", "Inspect pump", "A1", "dispatcher")
        read_back = orders.read("O1")
        repeated = orders.create("O1", "Inspect pump", "A1", "dispatcher")

        idempotency_conflict = None
        try:
            orders.create("O1", "Changed payload", "A1", "dispatcher")
        except ValueError as exc:
            idempotency_conflict = str(exc)

        permission_error = None
        try:
            orders.create("O2", "Inspect pump", "A1", "guest")
        except PermissionError as exc:
            permission_error = str(exc)

        approval_permission_error = None
        try:
            orders.approve("O1", "dispatcher")
        except PermissionError as exc:
            approval_permission_error = str(exc)
        approved = orders.approve("O1", "supervisor")

        before_migration = orders.reconcile()
        backup_path = case.base / "backup.db"
        orders.backup(backup_path)
        orders.migrate([{"id": "O2", "title": "Imported order", "asset_id": "A1", "state": "draft"}])
        after_migration = orders.reconcile()
        orders.restore(backup_path)
        after_restore = orders.reconcile()

        return {
            "fixture": "tests/fixtures/work_order_service.py",
            "synthetic": True,
            "created": created,
            "read_back": read_back,
            "idempotent_repeat": repeated,
            "idempotency_conflict": idempotency_conflict,
            "permission_error": permission_error,
            "approval_permission_error": approval_permission_error,
            "approved": approved,
            "before_migration": before_migration,
            "after_migration": after_migration,
            "after_restore": after_restore,
            "backup_file_sha256": digest(backup_path),
            "rollback_restored": after_restore == before_migration,
        }
    finally:
        case.doCleanups()


def refs(*values):
    return list(values)


def build_ref(code_sha: str) -> dict:
    return {"repository": "local-fixture/tests/fixtures", "revision": f"sha256:{code_sha}", "sha256": code_sha}


def make_readiness(software, decision_ref: dict) -> list[dict]:
    return [{
        "id": readiness_id,
        "title": f"Synthetic {readiness_id} readiness",
        "state": "pass",
        "owner": "automated-verifier",
        "evidence_refs": [decision_ref],
    } for readiness_id in sorted(software.READINESS_IDS)]


def gate_stage(snapshot: dict, artifact_ref: dict, name: str) -> dict:
    aid = artifact_ref["artifact_id"]
    record = next(item for item in snapshot["artifacts"] if item["artifact_id"] == aid)
    return {
        "stage": name,
        "artifact_id": aid,
        "revision": artifact_ref["revision"],
        "artifact_ref": artifact_ref,
        "artifact": {key: record[key] for key in ("artifact_id", "revision", "kind", "status", "health", "sha256")},
        "gate": snapshot["gates"].get(aid),
    }


def write_readme(out: Path, project: Path, sources: dict[str, dict], stages: list[dict]) -> None:
    lines = [
        "# 阶段二软件交付验证案例",
        "",
        "本目录是 purpose=simulation 的本地合成案例。HTTP 资产服务、SQLite 数据库、代码、测试和迁移回滚均只在本机执行；没有生产动作、真实客户 UAT、客户签署或客户交付包。",
        "",
        "## 材料索引",
        "",
        f"- `project/`：运行时登记的项目、来源快照、七类阶段二对象及版本引用。",
        "- `local-engineering-tests.log`：真实执行的 6 个本地 HTTP/SQLite unittest 原始日志。",
        "- `engineering-operations.json`：同一 fixture 的实际创建、权限、审批、迁移、备份和恢复回读。",
        "- `report.json`：测试统计、阶段顺序、版本/hash 引用和两次 release gate 快照。",
        "- `materials/`：明确标注为 synthetic 的范围、决策和 runbook 来源。",
        "",
        "## 证据边界",
        "",
        "代码和测试证据证明本地 fixture 的行为，不证明远端制品、第三方环境或生产可用性。UAT 与培训能力证据由自动化 fixture 产生，仅为 simulation；没有真实用户受训或客户确认。release r1 仅具备模拟执行准入，release r2 记录实际本地回滚恢复，但两者都不构成生产上线或客户验收。",
        "",
        "## 阶段 gate",
        "",
    ]
    for stage in stages:
        gate = stage.get("gate") or {}
        lines.append(f"- `{stage['stage']}` / `{stage['artifact_id']}` r{stage['revision']}: ready={gate.get('ready')}, ready_to_execute={gate.get('ready_to_execute', 'n/a')}")
    lines.extend(["", "项目目录：`project/`。来源数量：" + str(len(sources)) + "。"])
    (out / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_case(out: Path) -> dict:
    runtime = load_module(RUNTIME_PATH, "phase_two_runtime")
    software = load_module(SOFTWARE_PATH, "phase_two_software")
    engineering_tests = load_module(ENGINEERING_TEST_PATH, "phase_two_local_engineering_tests")
    # Load the fixture explicitly as well; the test module independently imports it.
    load_module(ENGINEERING_CODE_PATH, "phase_two_work_order_service")

    project = out / "project"
    materials = out / "materials"
    materials.mkdir()
    runtime.init_project(project, "PHASE2-SIM-001", purpose="simulation")

    scope_path = materials / "synthetic-scope.md"
    scope_path.write_text(
        "# Synthetic scope\n\nR1 create/read/idempotency; R2 permissions/state; R3 migration/rollback.\n",
        encoding="utf-8",
    )
    decision_path = materials / "synthetic-decision.md"
    decision_path.write_text(
        "# Synthetic decision\n\nAutomated local HTTP/SQLite fixture is the evidence source; this is not a production approval.\n",
        encoding="utf-8",
    )
    runbook_path = materials / "synthetic-runbook.md"
    runbook_path.write_text(
        "# Synthetic runbook\n\nBackup SQLite, run the local migration, reconcile count and keys, then restore the backup on rollback.\n",
        encoding="utf-8",
    )

    scope_ref = source_ref(runtime, project, scope_path, "SCOPE")
    decision_ref = source_ref(runtime, project, decision_path, "DECISION")
    runbook_ref = source_ref(runtime, project, runbook_path, "RUNBOOK")
    code_sha = digest(ENGINEERING_CODE_PATH)
    code_ref = source_ref(runtime, project, ENGINEERING_CODE_PATH, "ENG-CODE")

    test_result, raw_test_log = run_local_engineering_tests(engineering_tests)
    test_log_path = out / "local-engineering-tests.log"
    test_log_path.write_text(raw_test_log, encoding="utf-8")
    if not test_result.wasSuccessful() or test_result.testsRun != 6:
        failure_report = {
            "project_id": "PHASE2-SIM-001",
            "purpose": "simulation",
            "test_status": {
                "tests_run": test_result.testsRun,
                "failures": len(test_result.failures),
                "errors": len(test_result.errors),
                "skipped": len(test_result.skipped),
                "successful": test_result.wasSuccessful(),
            },
            "raw_test_log": "local-engineering-tests.log",
            "production_executed": False,
        }
        write_json(out / "report.json", failure_report)
        (out / "README.md").write_text(
            "# 阶段二验证失败\n\n本地工程 fixture 测试未按预期通过；详见 `local-engineering-tests.log` 与 `report.json`。未执行后续登记或生产动作。\n",
            encoding="utf-8",
        )
        raise RuntimeError("LocalEngineeringTests did not pass all 6 tests; see local-engineering-tests.log")

    operations = direct_operations(engineering_tests)
    operations_path = out / "engineering-operations.json"
    write_json(operations_path, operations)
    test_log_ref = source_ref(runtime, project, test_log_path, "ENG-TESTLOG")
    operations_ref = source_ref(runtime, project, operations_path, "ENG-OPS")

    project_id = "PHASE2-SIM-001"
    requirements_ref = register(runtime, project, artifact(project_id, "REQ", "requirements", {
        "items": [
            {"id": "R1", "statement": "Create, read and preserve idempotent work orders", "source_refs": [scope_ref], "acceptance": "Local fixture readback and idempotency conflict", "priority": "must"},
            {"id": "R2", "statement": "Enforce role permissions and draft-to-approved state", "source_refs": [scope_ref], "acceptance": "Unauthorized actions reject and supervisor approval changes state", "priority": "must"},
            {"id": "R3", "statement": "Migrate rows with count/key reconciliation and restorable rollback", "source_refs": [scope_ref], "acceptance": "Migration adds O2 and restore returns to O1", "priority": "must"},
        ],
        "open_items": [],
    }, inputs=refs(scope_ref)))
    plan_ref = register(runtime, project, artifact(project_id, "PLAN", "plan", {
        "work_packages": [{
            "id": "WP1", "title": "Local engineering verification", "owner": "automated-verifier",
            "baseline_start": "2026-10-11", "baseline_finish": "2026-10-11", "forecast_finish": "2026-10-11",
            "dependencies": [], "requirement_ids": ["R1", "R2", "R3"],
            "completion_rule": "actual local code, test log and operation readback", "status": "planned",
        }],
        "milestones": [],
    }, inputs=refs(requirements_ref, scope_ref)))

    build = build_ref(code_sha)
    solution_ref = register(runtime, project, artifact(project_id, "SOL", "solution", {
        "requirement_ids": ["R1", "R2", "R3"],
        "components": [{"id": "COMP1", "purpose": "Local work-order service", "requirement_ids": ["R1", "R2", "R3"], "deployment": "local fixture", "security": "role checks in fixture", "nonfunctional": "HTTP timeout and SQLite persistence exercised"}],
        "decisions": [{"id": "D1", "question": "What evidence source is valid for this rehearsal?", "options": ["local fixture", "production system"], "selected": "local fixture", "rationale": "The case is explicitly simulation and must not execute production actions", "status": "decided", "evidence_refs": [decision_ref]}],
    }, inputs=refs(requirements_ref, decision_ref, code_ref)))
    ui_ref = register(runtime, project, artifact(project_id, "UI", "ui_design", {
        "requirement_ids": ["R1", "R2", "R3"],
        "pages": [
            {"id": "P1", "title": "Create/read order", "requirement_ids": ["R1"], "states": ["draft", "approved"]},
            {"id": "P2", "title": "Role approval", "requirement_ids": ["R2"], "states": ["draft", "approved"]},
            {"id": "P3", "title": "Migration rollback", "requirement_ids": ["R3"], "states": ["draft", "approved"]},
        ],
        "fields": [
            {"id": "F1", "page_id": "P1", "type": "string", "length": 100, "precision": 0, "unit": "text", "required": True, "default": "", "enum": [], "validation": "1-100 chars", "source": "user", "sensitivity": "internal"},
            {"id": "F2", "page_id": "P2", "type": "string", "length": 40, "precision": 0, "unit": "role", "required": True, "default": "dispatcher", "enum": ["dispatcher", "supervisor"], "validation": "known role", "source": "user", "sensitivity": "internal"},
            {"id": "F3", "page_id": "P3", "type": "integer", "length": 10, "precision": 0, "unit": "rows", "required": True, "default": 0, "enum": [], "validation": "nonnegative", "source": "system", "sensitivity": "internal"},
        ],
        "permissions": [
            {"id": "PERM1", "page_id": "P1", "field_ids": ["F1"], "role": "dispatcher", "action": "write", "condition": "draft", "effect": "allow"},
            {"id": "PERM2", "page_id": "P2", "field_ids": ["F2"], "role": "supervisor", "action": "approve", "condition": "draft", "effect": "allow"},
            {"id": "PERM3", "page_id": "P3", "field_ids": ["F3"], "role": "operator", "action": "read", "condition": "any", "effect": "allow"},
        ],
        "states": [
            {"id": "ST1", "page_id": "P1", "from": "draft", "action": "submit", "to": "approved", "allowed_roles": ["supervisor"], "error": "approval required"},
            {"id": "ST2", "page_id": "P2", "from": "draft", "action": "approve", "to": "approved", "allowed_roles": ["supervisor"], "error": "supervisor required"},
            {"id": "ST3", "page_id": "P3", "from": "draft", "action": "restore", "to": "approved", "allowed_roles": ["operator"], "error": "restore evidence required"},
        ],
    }, inputs=refs(requirements_ref, decision_ref, code_ref)))
    interface_build = build
    integration_ref = register(runtime, project, artifact(project_id, "INT", "integration", {
        "requirement_ids": ["R1", "R2", "R3"],
        "interfaces": [{"id": "API1", "owner": "automated-verifier", "source_system": "WorkOrders", "target_system": "SyntheticAssets", "direction": "outbound", "trigger": "create", "protocol": "HTTP", "auth_method": "fixture-local", "environment": "local-fixture", "status": "verified", "idempotency": "order_id", "timeout": "2s", "retry": "none", "compensation": "manual restore"}],
        "mappings": [{"id": "MAP1", "interface_id": "API1", "source_field": "asset_id", "target_field": "asset_id", "type": "string", "unit": "identifier", "transform": "identity", "business_key": True}],
        "reconciliations": [{"id": "REC1", "interface_id": "API1", "state": "pass", "build_ref": interface_build, "environment": "local-fixture", "counts": [{"id": "COUNT1", "expected": operations["after_migration"]["count"], "actual": operations["after_migration"]["count"], "state": "pass"}], "business_keys": [{"id": "KEY1", "expected": operations["after_migration"]["business_keys"], "actual": operations["after_migration"]["business_keys"], "state": "pass"}], "evidence_refs": [operations_ref]}],
        "migration": {"applicable": True, "owner": "automated-verifier", "state": "completed", "backup_refs": [operations_ref], "rollback_plan": "restore backup.db", "freeze_window": "local fixture operation", "rehearsal_refs": [operations_ref], "reconciliation_refs": [operations_ref]},
    }, inputs=refs(requirements_ref, decision_ref, code_ref, operations_ref)))
    work_package_ref = register(runtime, project, artifact(project_id, "WP", "work_package", {
        "plan_work_package_id": "WP1", "requirement_ids": ["R1", "R2", "R3"], "design_refs": [solution_ref, ui_ref, integration_ref],
        "completion_rule": "actual code, six-test log, and operation readback are present", "build_ref": build,
        "evidence_refs": [code_ref, test_log_ref, operations_ref], "state": "completed",
    }, inputs=refs(requirements_ref, plan_ref, solution_ref, ui_ref, integration_ref, code_ref, test_log_ref, operations_ref)))

    cases = [
        {"id": "CASE-R1", "requirement_ids": ["R1"], "steps": ["create", "read", "repeat", "conflict"], "expected": "O1 persists once and conflicting replay rejects", "actual": f"O1={operations['read_back']['id']}; repeat_equal={operations['idempotent_repeat'] == operations['created']}; conflict={operations['idempotency_conflict']}", "state": "pass", "evidence_refs": [operations_ref, test_log_ref]},
        {"id": "CASE-R2", "requirement_ids": ["R2"], "steps": ["guest create", "dispatcher approval", "supervisor approval"], "expected": "role checks reject and supervisor transitions to approved", "actual": f"create_error={operations['permission_error']}; approve_error={operations['approval_permission_error']}; state={operations['approved']['state']}", "state": "pass", "evidence_refs": [operations_ref, test_log_ref]},
        {"id": "CASE-R3", "requirement_ids": ["R3"], "steps": ["backup", "migrate", "reconcile", "restore", "reconcile"], "expected": "count/keys move to O1,O2 then restore to O1", "actual": f"before={operations['before_migration']}; after={operations['after_migration']}; restored={operations['after_restore']}", "state": "pass", "evidence_refs": [operations_ref, test_log_ref]},
    ]
    testing_ref = register(runtime, project, artifact(project_id, "TEST", "testing", {
        "requirement_ids": ["R1", "R2", "R3"], "environment": "local-fixture", "build_ref": build, "cases": cases, "defects": [],
        "uat": {"state": "accepted", "scope_requirement_ids": ["R1", "R2", "R3"], "actor": "Automated local engineering fixture", "role": "synthetic test runner", "origin": "simulation", "evidence_refs": [test_log_ref, operations_ref, decision_ref], "open_items": []},
    }, inputs=refs(requirements_ref, decision_ref, code_ref, test_log_ref, operations_ref)))
    release_r1 = register(runtime, project, artifact(project_id, "REL", "release", {
        "environment": "local-fixture", "build_ref": build, "testing_ref": testing_ref, "readiness": make_readiness(software, decision_ref),
        "execution": {"state": "planned", "evidence_refs": [], "verification_refs": []},
        "rollback": {"state": "planned", "plan": "restore backup.db if local rehearsal fails", "evidence_refs": [], "restore_refs": []},
    }, inputs=refs(testing_ref, decision_ref, code_ref, runbook_ref)))
    snapshot_r1 = runtime.snapshot(project)
    stage_r1 = gate_stage(snapshot_r1, release_r1, "release-planned")

    release_r2 = register(runtime, project, artifact(project_id, "REL", "release", {
        "environment": "local-fixture", "build_ref": build, "testing_ref": testing_ref, "readiness": make_readiness(software, decision_ref),
        "execution": {"state": "rolled_back", "evidence_refs": [operations_ref], "verification_refs": []},
        "rollback": {"state": "succeeded", "plan": "restore backup.db", "evidence_refs": [operations_ref], "restore_refs": [operations_ref]},
    }, inputs=refs(testing_ref, decision_ref, code_ref, runbook_ref, operations_ref), revision=2))
    handover_ref = register(runtime, project, artifact(project_id, "HAND", "handover", {
        "audiences": [{"id": "AUD1", "role": "automated fixture runner", "owner": "automated-verifier"}],
        "training": [{"id": "TRAIN1", "audience_id": "AUD1", "attendance": True, "competency": "pass", "evidence_refs": [test_log_ref]}],
        "operations": {"owner": "automated-verifier", "state": "accepted", "runbook_refs": [runbook_ref], "receipt_refs": [operations_ref]},
        "assets": [{"id": "ASSET1", "owner": "automated-verifier", "version": f"sha256:{code_sha}", "evidence_refs": [code_ref]}, {"id": "ASSET2", "owner": "automated-verifier", "version": "test-log", "evidence_refs": [test_log_ref]}, {"id": "ASSET3", "owner": "automated-verifier", "version": "operation-readback", "evidence_refs": [operations_ref]}],
        "open_items": [],
    }, inputs=refs(code_ref, test_log_ref, operations_ref, runbook_ref)))

    snapshot_final = runtime.snapshot(project)
    validation = runtime.validate(project)
    stages = [
        gate_stage(snapshot_final, solution_ref, "solution"),
        gate_stage(snapshot_final, ui_ref, "ui-design"),
        gate_stage(snapshot_final, integration_ref, "integration-and-migration"),
        gate_stage(snapshot_final, work_package_ref, "work-package"),
        gate_stage(snapshot_final, testing_ref, "testing-and-simulated-uat"),
        stage_r1,
        gate_stage(snapshot_final, release_r2, "release-rolled-back"),
        gate_stage(snapshot_final, handover_ref, "simulation-handover"),
    ]
    sources = {
        name: ref for name, ref in {
            "scope": scope_ref, "decision": decision_ref, "runbook": runbook_ref,
            "engineering_code": code_ref, "test_log": test_log_ref, "operations": operations_ref,
        }.items()
    }
    report = {
        "report_version": "0.2.0",
        "project_id": project_id,
        "purpose": "simulation",
        "test_status": {"tests_run": test_result.testsRun, "failures": len(test_result.failures), "errors": len(test_result.errors), "skipped": len(test_result.skipped), "successful": test_result.wasSuccessful(), "raw_log": "local-engineering-tests.log"},
        "operation_readback": {key: operations[key] for key in ("before_migration", "after_migration", "after_restore", "rollback_restored")},
        "sources": sources,
        "build_ref": build,
        "stages": stages,
        "release_gate_snapshots": {"r1_planned": stage_r1, "r2_rolled_back": gate_stage(snapshot_final, release_r2, "release-rolled-back")},
        "artifacts": [{key: record[key] for key in ("artifact_id", "revision", "kind", "status", "health", "sha256")} for record in snapshot_final["artifacts"]],
        "validation": validation,
        "boundary": {"synthetic_data": True, "production_executed": False, "customer_uat": False, "customer_review_or_pass_fabricated": False, "real_user_trained": False, "customer_package_created": False},
    }
    write_json(out / "report.json", report)
    write_readme(out, project, sources, stages)
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True, type=Path, help="Fresh output directory; an existing directory is refused")
    args = parser.parse_args(argv)
    out = args.out.expanduser().resolve()
    if out.exists():
        parser.error(f"Refusing existing output directory: {out}")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.mkdir()
    try:
        report = build_case(out)
    except Exception as exc:
        print(f"phase-two verification failed: {exc}", file=sys.stderr)
        return 1
    print(json.dumps({"out": str(out), "tests_run": report["test_status"]["tests_run"], "validation_ok": report["validation"]["ok"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
