#!/usr/bin/env python3
"""Rehearse all 25 delivery Skills in one traceable, local simulated project.

Run with --out NEW_DIRECTORY. No connector, customer signature, payment or
production action is performed. Engineering evidence is actual local HTTP and
SQLite execution; management, customer, financial and training records are
explicitly simulated. Existing output directories are never overwritten.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import datetime, timezone
import json
import io
import unittest
from pathlib import Path
import shutil
import sys

# Only helpers are reused: never run the partial phase-two build_case.
import verify_phase_two as phase

PROJECT_ID = "FULL-SIM-001"
TITLE = "设备维保工单定制平台与 ERP 集成"
DATE = "2026-10-11"
BOUNDARY = {
    "synthetic_management_materials": True, "engineering_execution": "actual local HTTP + SQLite fixture",
    "customer_confirmation_origin": "simulation", "uat_origin": "simulation", "training_origin": "simulation",
    "production_executed": False, "external_actions": False, "real_customer_signatures": False,
    "revenue_recognized": False, "real_payments_executed": False,
}


def build_case(out: Path, *, preflight_dir: Path | None = None) -> dict:
    out = out.expanduser().resolve()
    runtime = phase.load_module(phase.RUNTIME_PATH, "full_delivery_runtime")
    software = phase.load_module(phase.SOFTWARE_PATH, "full_delivery_software")
    engineering = phase.load_module(phase.ENGINEERING_TEST_PATH, "full_delivery_engineering")
    project, materials = out / "project", out / "materials"
    materials.mkdir()
    runtime.init_project(project, PROJECT_ID, purpose="simulation")
    sources, stages, checks, skill_runs = {}, [], [], []

    def source(name, filename, content):
        path = materials / filename
        if isinstance(content, dict):
            phase.write_json(path, content)
        else:
            path.write_text(content, encoding="utf-8")
        ref = runtime.source(project, path, name)
        sources[name] = ref
        return ref

    def minimal_inputs(inputs):
        # Keep exact business-reference closure while removing redundant direct
        # edges. The runtime recursively re-reads every edge, so repeated full
        # upstream lists otherwise grow exponentially in a full lifecycle DAG.
        refs = {runtime.ref_key(ref): ref for ref in inputs}
        ancestors = set()
        seen = set()
        def collect(ref):
            key = runtime.ref_key(ref)
            if key in seen:
                return
            seen.add(key)
            for child in runtime.load_artifact(project, ref)["inputs"]:
                ancestors.add(runtime.ref_key(child))
                collect(child)
        for ref in refs.values():
            collect(ref)
        return [ref for key, ref in refs.items() if key not in ancestors]

    def reg(aid, kind, data, inputs=(), revision=1, visibility="internal"):
        return runtime.register(project, phase.artifact(PROJECT_ID, aid, kind, data, minimal_inputs(inputs),
                                                        revision=revision, visibility=visibility))

    def skill(name, inputs, outputs, evidence, goal):
        path = phase.SUITE / "skills" / name / "SKILL.md"
        # Read the actual package content, rather than journal a name alone.
        text = path.read_text(encoding="utf-8")
        if f"name: {name}" not in text:
            raise ValueError(f"Skill identity mismatch: {path}")
        skill_runs.append({
            "skill": name, "skill_source": str(path.relative_to(phase.SUITE)),
            "skill_sha256": phase.digest(path), "project_id": PROJECT_ID, "goal": goal,
            "input_refs": list(inputs), "output_refs": list(outputs), "evidence_refs": list(evidence),
            "output_location": "project/00-control/artifacts (exact refs); readable record in project stage directories",
            "boundary": "purpose=simulation; actual local fixture evidence only where explicitly marked",
            "write_owner": name, "unresolved": ["No real customer, ERP environment, production deployment or signature"],
        })

    def stage(name, *targets):
        snap = runtime.snapshot(project)
        stages.append({"stage": name, "captured_at": datetime.now(timezone.utc).isoformat(),
                       "artifact_refs": list(targets), "validation": runtime.validate(project),
                       "effective": snap["effective"], "cost_summary": snap["cost_summary"],
                       "gates": snap["gates"], "alerts": snap["alerts"]})

    def check(cid, passed, detail):
        checks.append({"id": cid, "passed": bool(passed), "detail": detail})
        if not passed:
            raise RuntimeError(f"Full-delivery check failed: {cid}: {detail}")

    contract_src = source("SRC-CONTRACT", "01-simulated-contract.md", f"""# 模拟合同 — {TITLE}
origin=simulation；非真实合同、签章或付款依据。
C1 范围：R1 工单创建/读取/相同业务键幂等与冲突拒绝；R2 调度员创建、主管审批、访客拒绝；R3 历史工单导入、条数/业务键核对、备份恢复。
C2 里程碑：蓝图、详细设计、接口联调、UAT、最终本地演练交付，均需精确版本模拟确认。
C3 边界：ERP 只由本机 HTTP 资产服务替身表示；不含真实 ERP 接入、生产部署、财务过账、移动端或性能 SLA。
C4 责任：模拟业务代表提供规则和数据；模拟 ERP 负责人提供字段资料；项目经理维护基线、变更及周报。
C5 财务：固定总价 CNY 12000 仅为模拟计费估计；内部预算初始 CNY 8000；所有台账是合成演练，不是收入/发票/到账。
C6 质保：2026-10-11 至 2027-10-10；行政结项可移交质保义务，不能提前宣布全部义务解除。
""")
    interview_src = source("SRC-INTERVIEWS", "02-simulated-interviews.md", """# 模拟访谈转录（完整读取）
origin=simulation；角色均为虚构。
00:00 业务代表：设备 A1 故障后调度员建单，重复提交同内容应返回同单；相同编号不同内容应拒绝。
00:30 主管：调度员不能审批；主管才能将 draft 转为 approved；访客无创建权。
01:00 ERP 负责人：本机替身 GET /assets/A1 返回资产编号 A1；404 与连接异常必须报错，禁止保存坏资产。
01:30 数据负责人：迁入 O2 后应有 O1/O2 两个业务键；先备份，恢复后只剩 O1。
02:00 模拟项目经理：现场规则讨论已完；正式 ERP、安全/压力测试、真实客户 UAT 仍在本次范围外。
""")
    decision_src = source("SRC-DECISIONS", "03-simulated-decisions.md", """# 模拟授权、变更和确认记录
origin=simulation；无真实客户签署或身份认证。
D1 批准本地 fixture 演练，禁止外部系统/生产写入。蓝图确认覆盖 processes/pages/fields/permissions/interfaces/data/acceptance。
D2 联调补充故障场景复核，WP-INT 批准基线从 2026-10-09 调至 2026-10-10，预算从 CNY8000 调至 CNY8500；同时应用 PLAN 和 COST，需求 R1-R3 不变。
D3 模拟代表完成本地 UAT 观察并接受 R1-R3；所有里程碑确认仅为 simulation。
D4 模拟运维人员接受手册、代码及本地恢复演练资产；培训练习结果来自本地自动 fixture，不是真实人员能力认证。
D5 模拟财务已逐项对照 ledger-source.json：审核内部工时42小时×100=4200，外包1600，采购600，差旅200，总成本6600；剩余人工/费用0；付款条件2400仅为模拟台账已付，不执行付款。
D6 模拟项目经理行政结项，质保移交 support-sim，保留一年支持义务和一项开放质保跟踪，未来到期再核验。
""")
    runbook_ref = source("SRC-RUNBOOK", "04-local-runbook.md", """# 本地演练运行手册
origin=simulation。仅 loopback HTTP 与临时 SQLite；不接生产 ERP。
1 启动 HTTP 资产替身与临时 SQLite 工单服务；2 调度员创建 O1，读取、重复及冲突校验；3 校验访客与调度员审批拒绝，主管审批；4 备份 SQLite，导入 O2，对账条数/业务键；5 演练恢复并回读；6 本地创建/审批/恢复回读全通过才记录本地执行 succeeded。
回滚触发：保存失败、业务键/条数不匹配或权限异常；停止写入并 restore backup.db，核对恢复前后相等。演练主动恢复证明可恢复性，与正式发布失败/回滚分开。
监测：HTTP 错误与 SQLite 数据读回；支持路径 support-sim→pm-sim。无生产账号或真实值守。
""")
    ledger_data = {
        "origin": "simulation", "as_of": DATE, "currency": "CNY", "tax_basis": "synthetic gross amounts",
        "time_records": [
            {"id": "H-AN", "person": "analyst-sim", "work_package_id": "WP-ANALYSIS", "hours": 8, "rate": 100},
            {"id": "H-APP", "person": "developer-sim", "work_package_id": "WP-APP", "hours": 16, "rate": 100},
            {"id": "H-INT", "person": "integrator-sim", "work_package_id": "WP-INT", "hours": 8, "rate": 100},
            {"id": "H-QA", "person": "tester-sim", "work_package_id": "WP-QA", "hours": 6, "rate": 100},
            {"id": "H-REL", "person": "operator-sim", "work_package_id": "WP-RELEASE", "hours": 4, "rate": 100},
        ],
        "expenses": [
            {"id": "OUT-1", "category": "outsourcing", "work_package_id": "WP-INT", "amount": 1600, "external_ref": "SIM-OUT-1"},
            {"id": "PO-1", "category": "purchase", "work_package_id": "WP-RELEASE", "amount": 600, "procurement_ref": "SIM-PO-1"},
            {"id": "TRIP-1", "category": "travel", "work_package_id": "WP-ANALYSIS", "amount": 200, "travel_or_expense_ref": "SIM-TRIP-1"},
        ], "internal_labor_total": 4200, "expense_total": 2400, "total": 6600, "remaining": 0,
        "settlement": "simulated ledger reconciliation only; no real funds movement",
    }
    ledger_ref = source("SRC-LEDGER", "05-ledger-source.json", ledger_data)
    code_path, test_path = materials / "work_order_service.py", materials / "test_local_engineering.py"
    shutil.copyfile(phase.ENGINEERING_CODE_PATH, code_path)
    shutil.copyfile(phase.ENGINEERING_TEST_PATH, test_path)
    code_ref = runtime.source(project, code_path, "ENG-CODE")
    sources["ENG-CODE"] = code_ref
    test_code_ref = runtime.source(project, test_path, "ENG-TESTCODE")
    sources["ENG-TESTCODE"] = test_code_ref
    engineering_dir = materials / "engineering"
    (engineering_dir / "fixtures").mkdir(parents=True)
    shutil.copyfile(code_path, engineering_dir / "fixtures/work_order_service.py")
    shutil.copyfile(test_path, engineering_dir / "test_local_engineering.py")
    code_sha = phase.digest(code_path)
    build = phase.build_ref(code_sha)
    build["repository"] = "materials/work_order_service.py (local HTTP/SQLite fixture)"
    boundary_test_path = phase.SUITE / "tests/test_local_engineering_boundaries.py"
    boundary_tests = phase.load_module(boundary_test_path, "full_delivery_boundary_tests")
    shutil.copyfile(boundary_test_path, materials / boundary_test_path.name)
    shutil.copyfile(boundary_test_path, engineering_dir / boundary_test_path.name)
    boundary_code_ref = runtime.source(project, materials / boundary_test_path.name, "ENG-BOUNDARY-TESTCODE")
    sources["ENG-BOUNDARY-TESTCODE"] = boundary_code_ref
    suite = unittest.TestSuite([
        unittest.defaultTestLoader.loadTestsFromTestCase(engineering.LocalEngineeringTests),
        unittest.defaultTestLoader.loadTestsFromTestCase(boundary_tests.LocalEngineeringBoundaryTests),
    ])
    stream = io.StringIO()
    result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
    log = stream.getvalue()
    preflight = (preflight_dir if preflight_dir is not None else phase.ROOT / "output/full-delivery-preflight-20261011") / "before-fix.log"
    # Historical real defect evidence is optional on another checkout. Never
    # invent a failure if the original source is unavailable.
    failed_log_ref = None
    if preflight.is_file():
        failed_log_ref = source("ENG-FAIL", "06-before-fix-engineering.log", preflight.read_text(encoding="utf-8"))
        for filename in ("work_order_service-before.py", "remediation.json", "after-fix.log"):
            original = preflight.parent / filename
            if original.is_file():
                source("ENG-HISTORY-" + filename.replace(".", "-").upper(), filename, original.read_text(encoding="utf-8"))
    test_log_ref = source("ENG-TESTLOG", "06-local-engineering-tests.log", log)
    (out / "local-engineering-tests.log").write_text(log, encoding="utf-8")
    check("actual-thirteen-engineering-tests", result.wasSuccessful() and result.testsRun == 13,
          {"tests_run": result.testsRun, "failures": len(result.failures), "errors": len(result.errors)})
    operations = phase.direct_operations(engineering)
    operations["local_release"] = {
        "state": "succeeded", "environment": "local-fixture", "build_ref": build,
        "execution": "Started loopback HTTP service and temporary SQLite; created, read and approved O1; rehearsed backup/import/restore and verified state",
        "business_verified": operations["read_back"] == operations["created"] and operations["approved"]["state"] == "approved" and operations["rollback_restored"],
        "rollback_triggered_for_release_failure": False, "recovery_rehearsal_executed": True,
        "production": False, "environment_retained": False,
    }
    operations_ref = source("ENG-OPS", "07-engineering-operations.json", operations)
    phase.write_json(out / "engineering-operations.json", operations)
    check("actual-operation-readback", operations["local_release"]["business_verified"], operations["local_release"])

    evidence_ref = reg("EVIDENCE", "evidence", {"items": [
        {"id": f"E-{i}", "source_id": ref["artifact_id"], "locator": locator,
         "content": content, "read_status": "read"}
        for i, (ref, locator, content) in enumerate([
            (contract_src, "C1-C6", "模拟合同范围、里程碑、预算、排除项、质保已完整读取"),
            (interview_src, "00:00-02:00", "模拟访谈完整转录：创建/幂等、角色审批、资产查验、迁移恢复"),
            (decision_src, "D1-D6", "模拟授权、变更、UAT、培训、结算和行政结项"),
            (ledger_ref, "/time_records and /expenses", "逐项合成财务记录，总成本6600；无真实支付"),
            (test_log_ref, "all 13 unittest outcomes", "实际本地 HTTP/SQLite 十三项测试通过"),
            (operations_ref, "/", "实际本地创建/权限/审批/迁移/恢复读回"),
        ], 1)], "unread_scope": [], "origin": "simulation", "reading_boundary": "Only the supplied synthetic text and actual local fixture logs"},
        [contract_src, interview_src, decision_src, ledger_ref, test_log_ref, operations_ref])
    skill("delivery-source-intake", list(sources.values()), [evidence_ref], [evidence_ref], "保存并逐份读取模拟材料及本地工程证据")
    contract_ref = reg("CONTRACT", "contract", {
        "obligations": [{"id": f"C{i}", "statement": text, "source_id": contract_src["artifact_id"], "locator": f"C{i}", "acceptance": accept}
                        for i, text, accept in [(1, "R1-R3 工单与 ERP 替身集成", "实际本地用例与操作读回"), (2, "五阶段里程碑", "精确版本模拟确认"),
                                              (5, "模拟预算与结算", "合成台账逐项核对"), (6, "一年质保", "移交后继续保留义务")]],
        "scope_in": ["R1 create/read/idempotency", "R2 role approval", "R3 migration/rollback", "local ERP asset fixture"],
        "scope_out": ["真实ERP", "生产部署", "移动端", "财务过账", "压力/安全认证", "真实合同签署"],
        "customer_dependencies": [{"id": "DEP1", "owner": "business-sim", "item": "规则/模拟数据", "state": "provided-simulation"}, {"id": "DEP2", "owner": "erp-sim", "item": "本机替身字段资料", "state": "provided-simulation"}],
        "origin": "simulation", "open_items": []}, [contract_src, evidence_ref])
    skill("delivery-contract-handover", [contract_src, evidence_ref], [contract_ref], [contract_src], "提取合同义务、排除项、验收付款质保及客户配合")
    milestone_ids = ["M-BLUEPRINT", "M-DESIGN", "M-INTEGRATION", "M-UAT", "M-FINAL"]
    kickoff_ref = reg("KICKOFF", "kickoff", {
        "goals": [TITLE, "先验证 R1-R3 的本地最小主线"],
        "roles": [{"id": r, "role": role, "actor": actor, "authority": "simulation only", "state": "accepted-simulation"} for r, role, actor in [
            ("PM", "基线/变更/行政结项", "pm-sim"), ("BUS", "业务确认/UAT", "business-sim"), ("ERP", "资产接口资料", "erp-sim"), ("DEV", "本地工程", "developer-sim"), ("QA", "本地验证", "tester-sim"), ("OPS", "移交/支持", "support-sim")]],
        "milestones": milestone_ids, "customer_actions": ["提供规则/样本/ERP 替身资料", "分阶段模拟确认"],
        "communication": "模拟周会，阻塞24小时升级pm-sim", "open_items": [], "origin": "simulation"}, [contract_ref, decision_src])
    skill("delivery-initiation-kickoff", [contract_ref, decision_src], [kickoff_ref], [decision_src], "建立项目目标、RACI、客户配合与升级路径")
    discovery_ref = reg("DISCOVERY", "discovery", {"sessions": [
        {"id": f"DISC{i}", "customer_role": role, "date": "2026-10-06", "topic": topic, "questions": questions,
         "customer_inputs": ["模拟转录及规则"], "expected_outputs": outputs, "owner": "analyst-sim", "status": "completed-simulation", "source_refs": [interview_src]}
        for i, (role, topic, questions, outputs) in enumerate([
            ("业务/主管", "工单流程与审批", ["重复提交如何处理?", "谁能审批?"], ["R1/R2 规则"]),
            ("ERP/数据负责人", "接口与迁移", ["资产编号如何映射?", "如何对账和恢复?"], ["R3 与接口设计"]),
        ], 1)]}, [contract_ref, kickoff_ref, interview_src])
    skill("delivery-discovery-planning", [contract_ref, kickoff_ref], [discovery_ref], [interview_src], "安排业务及ERP两场模拟调研并回读完整底稿")
    minutes_ref = reg("MINUTES", "minutes", {"meeting_date": "2026-10-06", "title": TITLE,
        "participants": ["business-sim", "supervisor-sim", "erp-sim", "analyst-sim"],
        "decisions": [{"id": "D-RULES", "text": "确认R1-R3模拟规则与ERP替身边界", "origin": "simulation", "source_refs": [interview_src, decision_src]}],
        "actions": [{"id": "ACT1", "owner": "integrator-sim", "due": "2026-10-10", "action": "执行故障/恢复联调", "state": "completed", "evidence_refs": [test_log_ref, operations_ref]}],
        "open_items": [], "read_range": "00:00-02:00 full synthetic transcript", "origin": "simulation"}, [discovery_ref, interview_src, decision_src, test_log_ref, operations_ref], visibility="customer")
    skill("delivery-meeting-records", [discovery_ref, interview_src], [minutes_ref], [interview_src, decision_src], "区分发言、规则决定与已完成行动，登记来源定位")
    requirements_ref = reg("REQ", "requirements", {"items": [
        {"id": rid, "statement": statement, "source_refs": [dict(interview_src, locator=loc), dict(contract_src, locator="C1")],
         "acceptance": accept, "priority": "must", "origin": "simulation", "status": "baselined-simulation"}
        for rid, statement, loc, accept in [
            ("R1", "创建/读取工单，相同编号相同内容幂等，不同内容冲突拒绝，并验证资产", "00:00,01:00", "创建后读回一致、重复不增单、冲突/未知资产/HTTP故障不保存"),
            ("R2", "调度员能创建，访客不能创建；主管独占draft到approved审批", "00:30", "访客创建和调度员审批拒绝，主管审批后状态approved"),
            ("R3", "历史工单迁移核对条数/业务键，备份后可恢复原状态", "01:30", "迁入O2后O1/O2两个键，恢复后与原O1状态完全一致"),
        ]], "open_items": []}, [contract_ref, minutes_ref, evidence_ref, interview_src])
    skill("delivery-requirements-baseline", [contract_ref, minutes_ref, evidence_ref], [requirements_ref], [interview_src, contract_src], "建立三个稳定原子需求及可实测验收规则")
    blueprint_data = {
        "processes": [{"id": f"BP-P{i}", "title": title, "steps": steps, "roles": roles, "requirement_ids": [rid], "exceptions": exceptions}
            for i, rid, title, steps, roles, exceptions in [
                (1, "R1", "故障建单", ["输入O1/A1", "ERP替身查资产", "幂等校验", "SQLite保存并读回"], ["dispatcher"], ["404、错误资产业务键与连接不可达时不落库", "相同业务键冲突拒绝"]),
                (2, "R2", "主管审批", ["调度员提单", "主管审批", "approved读回"], ["dispatcher", "supervisor"], ["访客和非主管拒绝"]),
                (3, "R3", "历史迁移", ["备份", "导入O2", "条数/业务键核对", "恢复演练"], ["operator"], ["核对不一致停止写入并恢复"])]],
        "pages": [{"id": "BP-UI1", "title": "工单创建/审批", "requirement_ids": ["R1", "R2"]}, {"id": "BP-UI2", "title": "迁移核对", "requirement_ids": ["R3"]}],
        "fields": [{"id": "BP-F1", "page_id": "BP-UI1", "name": "asset_id", "type": "string", "validation": "ERP替身存在资产", "permission": "dispatcher writes"}, {"id": "BP-F2", "page_id": "BP-UI2", "name": "business_keys", "type": "array", "permission": "operator reads"}],
        "interfaces": [{"id": "BP-API", "title": "ERP资产查验替身", "source_system": "work-order", "target_system": "local ERP asset fixture", "field_mappings": ["asset_id -> asset_id"], "acceptance": "返回A1且错误阻止落库"}],
        "acceptance_scenarios": [{"id": f"BP-T{i}", "requirement_ids": [f"R{i}"], "expected": exp} for i, exp in [(1,"创建/读取/重复/冲突与接口故障"),(2,"角色拒绝与主管审批"),(3,"迁移及备份恢复一致")]],
        "coverage": [{"requirement_id": f"R{i}", "design_ids": [f"BP-P{i}", "BP-UI1" if i < 3 else "BP-UI2", f"BP-T{i}", "BP-API"]} for i in range(1,4)],
        "system_boundary": "ERP loopback asset fixture; no real ERP or browser UI implemented", "open_items": []}
    blueprint_data['current_state'] = '模拟访谈仅定义目标规则，未提供既有系统现状材料；不推断现状。'
    blueprint_data['fields'] = [
        {'id': fid, 'page_id': page, 'name': name, 'type': typ, 'required': True,
         'validation': rule, 'permission': permission}
        for fid, page, name, typ, rule, permission in [
            ('BP-F1', 'BP-UI1', 'title', 'string', '去首尾空白后1至100字符', 'dispatcher creates'),
            ('BP-F2', 'BP-UI1', 'order_id', 'string', '非空且为SQLite唯一业务键', 'dispatcher creates'),
            ('BP-F3', 'BP-UI1', 'asset_id', 'string', '字母数字且响应业务键一致', 'dispatcher creates'),
            ('BP-F4', 'BP-UI1', 'state', 'string', 'draft或approved；审批仅主管', 'service writes'),
            ('BP-F5', 'BP-UI2', 'count', 'integer', '独立预期迁入后2、恢复后1', 'system calculates'),
            ('BP-F6', 'BP-UI2', 'business_keys', 'array', '迁入后O1/O2，恢复后O1', 'system calculates'),
        ]]
    blueprint_data['permissions'] = [
        {'id': 'BP-PERM1', 'page_id': 'BP-UI1', 'role': 'dispatcher', 'action': 'create', 'condition': '新业务键或相同载荷重放', 'field_ids': ['BP-F1','BP-F2','BP-F3'], 'implementation': '实际fixture校验'},
        {'id': 'BP-PERM2', 'page_id': 'BP-UI1', 'role': 'supervisor', 'action': 'approve', 'condition': 'draft', 'field_ids': ['BP-F4'], 'implementation': '实际fixture校验'},
        {'id': 'BP-PERM3', 'page_id': 'BP-UI2', 'role': 'operator', 'action': 'reconcile/restore', 'condition': '备份已存在且完成导入', 'field_ids': ['BP-F5','BP-F6'], 'implementation': '设计角色；fixture未实现此操作鉴权'},
    ]
    blueprint_data['data'] = [
        {'id': 'BP-DATA1', 'name': '工单', 'business_key': 'order_id', 'storage': 'SQLite orders(id,title,asset,state)', 'field_ids': ['BP-F1','BP-F2','BP-F3','BP-F4'], 'rules': 'id唯一；create先HTTP校验资产键；migrate仅校验非空asset、合法state与唯一键，历史资产真实性未另核验；审批draft到approved'},
        {'id': 'BP-DATA2', 'name': '迁移核对结果', 'business_key': '工单ID集合', 'storage': 'reconcile返回值及操作日志', 'field_ids': ['BP-F5','BP-F6'], 'rules': '按独立预期核对数量和业务键；异常停止写入、从备份恢复'},
    ]
    blueprint_data['coverage'] = [
        {'requirement_id': 'R1', 'design_ids': ['BP-P1','BP-UI1','BP-F1','BP-F2','BP-F3','BP-API','BP-T1'], 'permission_ids':['BP-PERM1'], 'data_ids':['BP-DATA1']},
        {'requirement_id': 'R2', 'design_ids': ['BP-P2','BP-UI1','BP-F4','BP-T2'], 'permission_ids':['BP-PERM2'], 'data_ids':['BP-DATA1']},
        {'requirement_id': 'R3', 'design_ids': ['BP-P3','BP-UI2','BP-F5','BP-F6','BP-T3'], 'permission_ids':['BP-PERM3'], 'data_ids':['BP-DATA2']},
    ]
    for index, process in enumerate(blueprint_data['processes'], 1):
        process.update(trigger={1:'资产A1需维保',2:'工单draft待审批',3:'迁移窗口开始'}[index],
                       entry=process['steps'][0], exit=process['steps'][-1],
                       documents={1:['工单O1'],2:['工单状态'],3:['备份文件','条数/业务键核对日志']}[index])
    blueprint_ref = reg('BLUEPRINT', 'blueprint', blueprint_data,
                        [requirements_ref, minutes_ref, contract_ref], visibility='customer')

    def confirm(aid, target, scope, evidence=decision_src):
        return reg(aid, "confirmation", {"target": target, "state": "accepted", "actor": "business-sim", "role": "模拟业务确认代表",
            "date": DATE, "scope": scope, "evidence_refs": [evidence], "origin": "simulation", "channel": "synthetic decision source D1-D6", "open_items": []}, [target, evidence])
    bp_conf = confirm("CONF-BLUEPRINT", blueprint_ref, ["processes", "pages", "fields", "permissions", "interfaces", "data", "acceptance"])
    skill("delivery-business-blueprint", [requirements_ref, minutes_ref, contract_ref], [blueprint_ref, bp_conf], [decision_src], "形成流程/页面/数据/接口与需求覆盖，并逐项模拟确认")
    stage("contract-discovery-blueprint", contract_ref, kickoff_ref, discovery_ref, minutes_ref, requirements_ref, blueprint_ref, bp_conf)

    packages = []
    package_specs = [
        ("WP-ANALYSIS", "需求/蓝图", "analyst-sim", [], ["R1","R2","R3"], "2026-10-06", "2026-10-07", "蓝图覆盖+模拟确认"),
        ("WP-APP", "工单定制开发", "developer-sim", ["WP-ANALYSIS"], ["R1","R2"], "2026-10-08", "2026-10-09", "实际代码及创建/权限/审批读回"),
        ("WP-INT", "ERP替身联调/迁移", "integrator-sim", ["WP-ANALYSIS"], ["R1","R3"], "2026-10-08", "2026-10-09", "真实HTTP/SQLite故障用例与迁移恢复对账"),
        ("WP-QA", "测试/UAT演练", "tester-sim", ["WP-APP","WP-INT"], ["R1","R2","R3"], "2026-10-10", "2026-10-10", "13个工程测试+三个需求用例+模拟UAT"),
        ("WP-RELEASE", "本地发布/培训移交", "operator-sim", ["WP-QA"], ["R1","R2","R3"], "2026-10-11", "2026-10-11", "本地运行读回+手册/资产/模拟接收+质保移交"),
    ]
    for wp, title, owner, deps, reqs, start, finish, rule in package_specs:
        packages.append({"id": wp, "stream_id": wp, "title": title, "owner": owner, "baseline_start": start, "baseline_finish": finish,
                         "forecast_finish": finish, "dependencies": deps, "requirement_ids": reqs, "completion_rule": rule, "status": "planned"})
    plan_data = {"work_packages": packages, "milestones": [{"id": mid, "title": title, "work_package_ids": wps, "criterion": criterion}
        for mid, title, wps, criterion in [("M-BLUEPRINT", "蓝图确认", ["WP-ANALYSIS"], "七项范围确认"), ("M-DESIGN", "详细设计", ["WP-APP","WP-INT"], "方案/UI/接口评审"),
                                          ("M-INTEGRATION", "联调", ["WP-INT"], "对账及错误路径实测"), ("M-UAT", "模拟UAT", ["WP-QA"], "测试及模拟接受"), ("M-FINAL", "最终演练交付", ["WP-RELEASE"], "本地执行/模拟移交/行政结项")]],
                 "calendar": "synthetic planned dates; not actual duration measured", "critical_path": "not calculated; no reliable duration/calendar model", "origin": "simulation"}
    plan_r1 = reg("PLAN", "plan", plan_data, [requirements_ref, blueprint_ref, contract_ref, kickoff_ref])
    cost_data = {"currency": "CNY", "budget": 8000, "items": [dict(item, state="incurred", basis="SRC-LEDGER /expenses synthetic ledger", payment_status="paid", evidence_refs=[ledger_ref]) for item in ledger_data["expenses"]],
                 "other_remaining": 0, "tax_basis": "synthetic gross amounts", "payment_conditions": [
                     {"id": "PAY-"+item["id"], "cost_item_id": item["id"], "amount": item["amount"], "due_date": DATE, "condition": "模拟凭据逐项核对", "state": "paid", "evidence_refs": [ledger_ref]} for item in ledger_data["expenses"]], "origin": "simulation"}
    cost_data.update(forecast_scope='仅本次实施范围；持续质保成本未估算，不包含在6600完工预测内',
                     warranty_cost_estimate=None, warranty_cost_status='unknown; separately estimate before real warranty commitment')
    cost_r1 = reg("COST", "costs", cost_data, [ledger_ref, contract_ref])
    runtime.activate(project, ["REQ", "BLUEPRINT", "PLAN", "COST"])
    skill("delivery-master-planning", [requirements_ref, blueprint_ref, contract_ref, kickoff_ref], [plan_r1], [contract_src, decision_src], "建立五条WBS工作流、依赖、完成规则及五个里程碑")
    stage("initial-approved-baselines", plan_r1, cost_r1)
    plan_changed = deepcopy(plan_data)
    for wp in plan_changed["work_packages"]:
        wp["original_baseline_start"] = wp["baseline_start"]
        wp["original_baseline_finish"] = wp["baseline_finish"]
        if wp["id"] == "WP-INT":
            wp.update(baseline_finish="2026-10-10", forecast_finish="2026-10-10", variance_days=1, variance_reason="D2增加故障场景复核")
        wp["status"] = "completed"
        wp["actual_start"] = DATE
        wp["actual_finish"] = DATE
        wp["schedule_boundary"] = "all actual local engineering runs occur on rehearsal day; past dates are synthetic plan only"
        wp["evidence_refs"] = [test_log_ref, operations_ref] if wp["id"] != "WP-ANALYSIS" else [decision_src]
    plan_changed["progress_as_of"] = DATE
    plan_changed["variance_analysis"] = [{"id": "VAR-INT", "work_package_id": "WP-INT", "baseline_variance_days": 1,
        "cause": "故障场景复核", "impact": "M-INTEGRATION 调至10日，M-UAT/FINAL不变", "action": "重排QA在联调完成后执行", "decision_refs": [decision_src]}]
    plan_ref = reg("PLAN", "plan", plan_changed, [requirements_ref, blueprint_ref, contract_ref, kickoff_ref, decision_src, test_log_ref, operations_ref], revision=2)
    cost_changed = deepcopy(cost_data)
    cost_changed["budget"] = 8500
    cost_ref = reg("COST", "costs", cost_changed, [ledger_ref, contract_ref, decision_src], revision=2)
    check("candidate-baselines-preserved", runtime.snapshot(project)["effective"]["PLAN"] == plan_r1 and runtime.snapshot(project)["effective"]["COST"] == cost_r1, "Candidates do not alter effective plan/budget")
    change_data = {"state": "proposed", "reason": "D2故障路径复核与计划/预算同时调整", "affected_ids": ["PLAN","COST"], "baseline_refs": [plan_r1,cost_r1], "replacements": [plan_ref,cost_ref],
                   "decision_refs": [decision_src], "impact": {"scope": "R1-R3不变", "schedule": "+1 day WP-INT; final unchanged", "cost": "budget +500 CNY", "quality": "add failure-path review", "contract": "no production scope"}}
    change_proposed = reg("CHANGE", "change", change_data, [plan_r1,cost_r1,plan_ref,cost_ref,decision_src])
    try:
        runtime.apply_change(project, "CHANGE")
    except ValueError as exc:
        rejected_change = str(exc)
    else:
        raise RuntimeError("Proposed change unexpectedly applied")
    check("unapproved-change-rejected", "approved" in rejected_change and runtime.read_registry(project)["effective"]["PLAN"] == plan_r1, rejected_change)
    change_data["state"] = "approved"
    change_ref = reg("CHANGE", "change", change_data, [plan_r1,cost_r1,plan_ref,cost_ref,decision_src], revision=2)
    application = runtime.apply_change(project, "CHANGE")
    check("atomic-plan-cost-change", application["state"] == "effective" and runtime.snapshot(project)["effective"]["PLAN"] == plan_ref and runtime.snapshot(project)["effective"]["COST"] == cost_ref,
          {"application": application, "repeat_identical": runtime.apply_change(project,"CHANGE") == application})
    skill("delivery-progress-control", [plan_r1, test_log_ref, operations_ref, decision_src], [plan_ref], [test_log_ref,operations_ref,decision_src], "对照原始/当前批准基线、实际演练和预测，登记延期分析与纠偏")
    skill("delivery-change-control", [plan_r1,cost_r1,decision_src,plan_ref,cost_ref], [change_proposed,change_ref,plan_ref,cost_ref], [decision_src], "实际触发未批准拒绝，批准后一次应用计划和预算候选")
    hours_data = {"items": [dict(row, date=DATE, resource_type="internal", status="approved", activity="simulation lifecycle task", source_refs=[ledger_ref]) for row in ledger_data["time_records"]] + [
        {"id": "H-OUT", "person": "vendor-sim", "date": DATE, "work_package_id": "WP-INT", "hours": 8, "rate": 200, "resource_type": "outsourced", "status": "approved", "source_refs": [ledger_ref]}],
        "remaining_labor": None, "remaining_work": [{"id":"RW-END", "person":"operator-sim", "work_package_id":"WP-RELEASE", "remaining_hours":0, "rate":100, "resource_type":"internal", "basis":"模拟收尾剩余实施0；质保另行保留"}],
        "capacities": [{"id":"CAP-"+str(i), "person":row["person"], "period":"rehearsal", "available_hours":16} for i,row in enumerate(ledger_data["time_records"])],
        "allocations": [{"id":"ALLOC-"+str(i), "person":row["person"], "period":"rehearsal", "work_package_id":row["work_package_id"], "planned_hours":row["hours"]} for i,row in enumerate(ledger_data["time_records"])], "origin":"simulation"}
    hours_ref = reg("HOURS", "timesheets", hours_data, [plan_ref,ledger_ref])
    skill("delivery-resource-timesheets", [plan_ref,ledger_ref], [hours_ref], [ledger_ref], "关联五个工作包工时、容量和剩余工作，外包不重复计人工")
    summary = runtime.cost_summary(project)
    check("supported-cost-reconciliation", summary["complete"] and summary["forecast"] == "6600.00" and summary["budget"] == "8500.00" and summary["internal_labor"] == "4200.00", summary)
    skill("delivery-cost-expenses", [hours_ref,contract_ref,ledger_ref], [cost_r1,cost_ref], [ledger_ref], "逐项核对人工、外包、采购、差旅和付款条件；成本6600、批准预算8500")
    risks_ref = reg("RISKS", "risks", {"items": [
        {"id":"RISK-ERP", "type":"risk", "title":"真实ERP兼容性尚未知", "owner":"erp-sim", "status":"open", "action":"真实项目另取接口/授权/环境后验证", "due":"2027-10-10", "evidence_refs":[contract_src], "probability":"unassessed", "impact":"real rollout blocked outside simulation scope"},
        {"id":"ISSUE-MAPPING", "type":"issue", "title":"接口故障路径证据需要复核", "owner":"integrator-sim", "status":"closed", "action":"补全HTTP错误/恢复测试与D2基线变更", "due":DATE, "evidence_refs":[test_log_ref,operations_ref,decision_src]},
        {"id":"QUALITY-REVIEW", "type":"quality", "title":"交付审查需要明确本地和模拟边界", "owner":"pm-sim", "status":"closed", "action":"审查整改记录明确真实未查项", "due":DATE, "evidence_refs":[decision_src]}]}, [contract_ref,decision_src,test_log_ref,operations_ref])
    skill("delivery-risk-issue", [contract_ref,plan_ref,change_ref,test_log_ref,operations_ref], [risks_ref], [contract_src,test_log_ref,operations_ref], "区分风险、已发生问题和质量事项，按真实本地结果关闭演练问题")
    stage("controls-and-effective-change", plan_ref,cost_ref,hours_ref,risks_ref,change_ref)
    def register(runtime_module, project_path, value):
        value["inputs"] = minimal_inputs(value["inputs"])
        return runtime_module.register(project_path, value)
    artifact, refs = phase.artifact, phase.refs
    project_id, decision_ref = PROJECT_ID, decision_src
    solution_ref = register(runtime, project, artifact(project_id, "SOL", "solution", {
        "requirement_ids": ["R1", "R2", "R3"],
        "components": [{"id": "COMP1", "purpose": "Local work-order service", "requirement_ids": ["R1", "R2", "R3"], "deployment": "local fixture", "security": "role checks in fixture", "nonfunctional": "SQLite持久化已实测；HTTP配置2秒超时，超时触发及503未实测"}],
        "decisions": [{"id": "D1", "question": "What evidence source is valid for this rehearsal?", "options": ["local fixture", "production system"], "selected": "local fixture", "rationale": "The case is explicitly simulation and must not execute production actions", "status": "decided", "evidence_refs": [decision_ref]}],
    }, inputs=refs(blueprint_ref, requirements_ref, decision_ref, code_ref)))
    ui_data = {
        "requirement_ids": ["R1", "R2", "R3"],
        "pages": [
            {"id": "P1", "title": "Create/read order", "requirement_ids": ["R1"], "states": ["draft", "approved"]},
            {"id": "P2", "title": "Role approval", "requirement_ids": ["R2"], "states": ["draft", "approved"]},
            {"id": "P3", "title": "Migration rollback", "requirement_ids": ["R3"], "states": ["pre-migration", "migrated", "restored"]},
        ],
        "fields": [
            {"id": "F1", "name": "title", "page_id": "P1", "type": "string", "length": 100, "precision": 0, "unit": "text", "required": True, "default": "", "enum": [], "validation": "1-100 chars", "source": "user", "sensitivity": "internal"},
            {"id": "F2", "name": "actor_role", "page_id": "P2", "type": "string", "length": 40, "precision": 0, "unit": "role", "required": True, "default": "dispatcher", "enum": ["dispatcher", "supervisor"], "validation": "known role", "source": "user", "sensitivity": "internal"},
            {"id": "F3", "name": "row_count", "page_id": "P3", "type": "integer", "length": 10, "precision": 0, "unit": "rows", "required": True, "default": 0, "enum": [], "validation": "nonnegative", "source": "system", "sensitivity": "internal"},
            {"id": "F4", "name": "order_id", "page_id": "P1", "type": "string", "length": None, "precision": 0, "unit": "identifier", "required": True, "default": "", "enum": [], "validation": "nonempty; fixture has no maximum length; business key bound in SQL parameters", "source": "user", "sensitivity": "internal"},
            {"id": "F5", "name": "asset_id", "page_id": "P1", "type": "string", "length": None, "precision": 0, "unit": "identifier", "required": True, "default": "", "enum": [], "validation": "alphanumeric identifier; GET asset response key must match", "source": "user/ERP fixture", "sensitivity": "internal"},
            {"id": "F6", "name": "state", "page_id": "P2", "type": "string", "length": 8, "precision": 0, "unit": "state", "required": True, "default": "draft", "enum": ["draft", "approved"], "validation": "supervisor-only approve from draft", "source": "service", "sensitivity": "internal"},
        ],
        "permissions": [
            {"id": "PERM1", "page_id": "P1", "field_ids": ["F1", "F4", "F5"], "role": "dispatcher", "action": "create-or-replay", "condition": "新建生成draft；同载荷幂等重放允许原单任何状态，且不修改数据", "effect": "allow"},
            {"id": "PERM2", "page_id": "P2", "field_ids": ["F2", "F6"], "role": "supervisor", "action": "approve", "condition": "draft", "effect": "allow"},
            {"id": "PERM3", "page_id": "P3", "field_ids": ["F3"], "role": "operator", "action": "read", "condition": "any", "effect": "allow"},
        ],
        "states": [
            {"id": "ST1", "page_id": "P1", "from": "draft", "action": "refresh", "to": "approved", "allowed_roles": ["dispatcher"], "preconditions":"主管已在P2审批；刷新只读且不修改状态", "error": "未审批仍显示draft；页面角色限制仅为设计，fixture read无鉴权"},
            {"id": "ST2", "page_id": "P2", "from": "draft", "action": "approve", "to": "approved", "allowed_roles": ["supervisor"], "error": "supervisor required"},
            {"id": "ST3", "page_id": "P3", "from": "migrated", "action": "restore", "to": "restored", "allowed_roles": ["operator"], "error": "restore evidence required; operator is design role, fixture restore has no authorization check"},
        ],
    }
    page_rules = {
        'P1': ('BP-P1', ['dispatcher'], ['创建','读取'], '填写工单编号、标题与资产键', '落库后返回draft工单；同载荷重复返回同单', '校验错误或HTTP失败时保留输入、不写库；冲突须使用原载荷或新编号'),
        'P2': ('BP-P2', ['supervisor'], ['审批'], '工单已存在且为draft', '返回approved工单', '非主管或重复审批拒绝，重新读取当前状态'),
        'P3': ('BP-P3', ['operator'], ['备份','迁移','核对','恢复'], '演练窗口和备份路径已准备', '显示条数/业务键及恢复后的核对结果', '迁移失败事务回退；核对异常停止写入、恢复备份并重新核对'),
    }
    for page in ui_data['pages']:
        flow, roles, buttons, before, success, recovery = page_rules[page['id']]
        page.update(flow_ids=[flow], entry='管理导航进入'+page['title'], exit='返回工单列表或核对记录',
                    roles=roles, visible_buttons=buttons, preconditions=before, success_result=success,
                    failure_recovery=recovery, error_message=recovery, audit_event='设计要求记录动作、操作者、工单ID和结果；fixture无审计日志',
                    implementation='仅页面交互规格；未实现业务浏览器页面', open_items=[])
        page['operations'] = [{'id':page['id']+'-OP'+str(i), 'button':button,
                               'requirement_ids':page['requirement_ids'], 'flow_ids':[flow],
                               'precondition':before, 'success':success, 'failure_recovery':recovery,
                               'audit_event':page['audit_event'], 'implementation':'页面操作设计；工程证据仅覆盖相应fixture函数'}
                              for i, button in enumerate(buttons, 1)]
    meanings = {'title':'维保事项标题','actor_role':'调用者角色','row_count':'核对的工单条数',
                'order_id':'工单唯一业务编号','asset_id':'被维保资产业务键','state':'工单审批状态'}
    mappings = {'title':'orders.title','actor_role':'approve(role)；角色来自调用参数，未认证身份',
                'row_count':'reconcile().count','order_id':'orders.id',
                'asset_id':'GET /assets/{asset_id} 响应asset_id -> orders.asset','state':'orders.state'}
    for field in ui_data['fields']:
        field.update(business_meaning=meanings[field['name']], unique=field['name']=='order_id',
                     visibility='对应页面始终显示；无额外隐蔽规则',
                     read_write='创建时输入；保存后只读' if field['page_id']=='P1' else '只读输出' if field['name'] in {'row_count','state'} else '调用上下文；正式系统不可由用户自选',
                     calculation='按实际工单数计算' if field['name']=='row_count' else '无派生计算',
                     interface_mapping=mappings[field['name']], exception_display=page_rules[field['page_id']][-1])
    ui_data['design_boundary'] = '页面可见按钮和审计为设计规格；实际fixture仅验证函数权限、状态与数据，不包含业务前端或身份认证。'
    ui_data['permissions'][2]['implementation'] = '仅设计角色；fixture的核对/恢复未实现operator鉴权'
    ui_ref = register(runtime, project, artifact(project_id, 'UI', 'ui_design', ui_data,
                      inputs=refs(blueprint_ref, requirements_ref, decision_ref, code_ref)))
    interface_build = build
    integration_ref = register(runtime, project, artifact(project_id, "INT", "integration", {
        "requirement_ids": ["R1", "R2", "R3"],
        "interfaces": [{"id": "API1", "owner": "automated-verifier", "source_system": "WorkOrders", "target_system": "SyntheticAssets", "direction": "outbound", "trigger": "create", "protocol": "HTTP", "auth_method": "none (loopback only, no production auth)", "environment": "local-fixture", "status": "verified", "idempotency": "GET is read-only; local work-order write uses order_id", "timeout": "2s", "retry": "none", "compensation": "manual restore"}],
        "mappings": [{"id": "MAP1", "interface_id": "API1", "source_field": "asset_id", "target_field": "asset_id", "type": "string", "unit": "identifier", "transform": "identity", "business_key": True}],
        "reconciliations": [{"id": "REC1", "interface_id": "API1", "state": "pass", "build_ref": interface_build, "environment": "local-fixture", "counts": [{"id": "COUNT1", "expected": 2, "actual": operations["after_migration"]["count"], "state": "pass"}], "business_keys": [{"id": "KEY1", "expected": ["O1", "O2"], "actual": operations["after_migration"]["business_keys"], "state": "pass"}], "evidence_refs": [operations_ref]}],
        "migration": {"applicable": True, "owner": "automated-verifier", "state": "completed", "backup_refs": [operations_ref], "rollback_plan": "restore backup.db", "freeze_window": "local fixture operation", "rehearsal_refs": [operations_ref], "reconciliation_refs": [operations_ref]},
    }, inputs=refs(blueprint_ref, requirements_ref, decision_ref, code_ref, operations_ref)))
    # Detailed specifications match the fixture's actual contract; a browser UI
    # is a design-only deliverable and is explicitly outside engineering claims.
    skill("delivery-solution-design", [requirements_ref,blueprint_ref,decision_src,code_ref], [solution_ref], [code_ref,decision_src], "按R1-R3定义本地服务、SQLite、ERP替身及无生产认证的边界")
    skill("delivery-ui-field-design", [requirements_ref,blueprint_ref,decision_src,code_ref], [ui_ref], [code_ref,interview_src], "编制页面/字段/权限/状态规格；未生成或实现浏览器页面")
    skill("delivery-integration-data", [requirements_ref,blueprint_ref,code_ref,operations_ref], [integration_ref], [operations_ref,test_log_ref], "以实际本地HTTP、条数/键及备份恢复支撑联调/迁移")
    wp_refs = []
    for row in plan_changed["work_packages"]:
        wp_refs.append(reg(row["id"], "work_package", {
            "plan_work_package_id": row["id"], "requirement_ids": row["requirement_ids"],
            "design_refs": [blueprint_ref,solution_ref,ui_ref,integration_ref], "owner": row["owner"], "dependencies": row["dependencies"],
            "completion_rule": row["completion_rule"], "build_ref": build, "evidence_refs": [code_ref,test_log_ref,operations_ref,decision_src],
            "state": "completed", "origin": "simulation", "environment": "local-fixture",
            "completion_boundary": "Local engineering fixture executed; management/training tasks are simulated; no full production platform"},
            [requirements_ref,plan_ref,blueprint_ref,solution_ref,ui_ref,integration_ref,code_ref,test_log_ref,operations_ref,decision_src]))
    skill("delivery-work-package", [plan_ref,requirements_ref,solution_ref,ui_ref,integration_ref], wp_refs, [code_ref,test_log_ref,operations_ref,decision_src], "拆解并按不同完成规则回读五个实施任务包的工程/模拟证据")
    stage("detailed-design-and-work-packages", solution_ref,ui_ref,integration_ref,*wp_refs)
    cases = [
        {"id":"CASE-R1", "requirement_ids":["R1"], "steps":["create O1", "read O1", "identical replay", "conflicting replay", "asset HTTP404 / wrong business key / unreachable connection"],
         "expected":"单一O1且相同内容读回；冲突/接口错误不落库", "actual":json.dumps({"created":operations["created"],"read_back":operations["read_back"],"same_repeat":operations["idempotent_repeat"]==operations["created"],"conflict":operations["idempotency_conflict"]}, ensure_ascii=False), "state":"pass", "evidence_refs":[test_log_ref,operations_ref]},
        {"id":"CASE-R1-CONC", "requirement_ids":["R1"], "steps":["4 concurrent identical create calls", "read SQL count/business key"],
         "expected":"所有调用相同结果，仅一条O1，无IntegrityError", "actual":"test_concurrent_identical_replay_produces_one_order passes against current code SHA; original failure evidence " + ("available and bound" if failed_log_ref else "not available in this checkout; no historical defect closure claimed"), "state":"pass", "evidence_refs":[ref for ref in [test_log_ref,failed_log_ref,code_ref,boundary_code_ref] if ref]},
        {"id":"CASE-R2", "requirement_ids":["R2"], "steps":["guest create", "dispatcher approve", "supervisor approve", "missing order approve"],
         "expected":"越权拒绝；主管draft→approved；不存在工单无副作用", "actual":json.dumps({"guest":operations["permission_error"],"dispatcher_approve":operations["approval_permission_error"],"approved":operations["approved"]}, ensure_ascii=False), "state":"pass", "evidence_refs":[test_log_ref,operations_ref]},
        {"id":"CASE-R3", "requirement_ids":["R3"], "steps":["backup", "migrate O2", "count/key reconcile", "restore", "duplicate migration rollback"],
         "expected":"O1→O1/O2→O1；迁移批次冲突不残留部分写入", "actual":json.dumps({"before":operations["before_migration"],"after":operations["after_migration"],"restore":operations["after_restore"],"restored":operations["rollback_restored"]}, ensure_ascii=False), "state":"pass", "evidence_refs":[test_log_ref,operations_ref]},
    ]
    testing_ref = reg("TEST", "testing", {"requirement_ids":["R1","R2","R3"], "environment":"local-fixture", "build_ref":build,
        "cases":cases, "defects":[{"id":"DEF-CONC-001", "case_id":"CASE-R1-CONC", "severity":"major", "state":"closed", "owner":"developer-sim",
            "retest_case_id":"CASE-R1-CONC", "retest_refs":[test_log_ref,code_ref], "original_evidence_refs":[failed_log_ref],
            "description":"Real preflight concurrent identical replay raced SELECT/INSERT and raised sqlite3.IntegrityError",
            "fix":"BEGIN IMMEDIATE transaction serializes idempotency read/insert", "fix_build_ref":build,
            "origin":"actual local defect; simulated project owner"}] if failed_log_ref else [],
        "uat":{"state":"accepted", "scope_requirement_ids":["R1","R2","R3"], "actor":"business-sim", "role":"模拟业务代表", "origin":"simulation", "evidence_refs":[test_log_ref,operations_ref,decision_src], "open_items":[]},
        "unchecked":["browser UI implementation", "real ERP protocol/authentication", "production security", "load/availability SLA", "real customer UAT"]},
        [ref for ref in [requirements_ref,blueprint_ref,*wp_refs,code_ref,test_code_ref,boundary_code_ref,failed_log_ref,test_log_ref,operations_ref,decision_src] if ref])
    skill("delivery-quality-testing", [requirements_ref,solution_ref,ui_ref,integration_ref,*wp_refs,code_ref], [testing_ref], [ref for ref in [failed_log_ref,test_log_ref,operations_ref,boundary_code_ref] if ref], "执行13项实际本地测试和并发回归、按可用历史证据登记缺陷并明确模拟UAT")
    release_r1 = reg("REL", "release", {"environment":"local-fixture", "build_ref":build, "testing_ref":testing_ref, "readiness":phase.make_readiness(software,decision_src),
        "execution":{"state":"planned", "evidence_refs":[], "verification_refs":[]},
        "rollback":{"state":"planned", "plan":"停止本地fixture写入，恢复backup.db并核对O1业务键", "evidence_refs":[], "restore_refs":[]},
        "boundary":"Local demo fixture startup/run only; not deployed browser app or production release"}, [testing_ref,decision_src,runbook_ref,operations_ref])
    stage("release-planned", release_r1)
    check("planned-release-is-not-executed", stages[-1]["gates"]["REL"]["ready_to_execute"] and not stages[-1]["gates"]["REL"]["ready"], stages[-1]["gates"]["REL"])
    release_ref = reg("REL", "release", {"environment":"local-fixture", "build_ref":build, "testing_ref":testing_ref, "readiness":phase.make_readiness(software,decision_src),
        "execution":{"state":"succeeded", "evidence_refs":[operations_ref], "verification_refs":[operations_ref,test_log_ref], "scope":"actual local demo fixture run; environment torn down after test"},
        "rollback":{"state":"not_needed", "plan":"停止写入并恢复backup.db；此前已在本地演练恢复读回", "evidence_refs":[operations_ref], "restore_refs":[operations_ref]},
        "boundary":"Backup restore is a successful recovery rehearsal; no release failure or production rollback claimed"}, [testing_ref,decision_src,code_ref,runbook_ref,operations_ref,test_log_ref], revision=2)
    skill("delivery-go-live-transition", [testing_ref,integration_ref,runbook_ref,decision_src], [release_r1,release_ref], [operations_ref,test_log_ref], "区分计划准入与实际本地fixture执行，回读运行与恢复演练")
    handover_ref = reg("HANDOVER", "handover", {
        "audiences":[{"id":"AUD-DISPATCH", "role":"模拟调度员/主管", "owner":"business-sim"}, {"id":"AUD-OPS", "role":"模拟运维人员", "owner":"support-sim"}],
        "training":[{"id":"TRAIN-DISPATCH", "audience_id":"AUD-DISPATCH", "attendance":True, "competency":"pass", "evidence_refs":[test_log_ref,operations_ref,decision_src], "origin":"simulation", "assessment":"自动fixture的创建/审批练习作为模拟人员练习替身"},
                    {"id":"TRAIN-OPS", "audience_id":"AUD-OPS", "attendance":True, "competency":"pass", "evidence_refs":[operations_ref,decision_src], "origin":"simulation", "assessment":"本地备份/迁移/恢复读回作为模拟运维练习"}],
        "operations":{"owner":"support-sim", "state":"accepted", "runbook_refs":[runbook_ref], "receipt_refs":[decision_src], "origin":"simulation"},
        "assets":[{"id":aid,"owner":"support-sim","version":version,"evidence_refs":[ref],"origin":"simulation"} for aid,version,ref in [
            ("CODE", "sha256:"+code_sha, code_ref),("RUNBOOK","r1",runbook_ref),("TESTLOG","13 tests",test_log_ref),("OPS","local readback",operations_ref)]],
        "open_items":[], "origin":"simulation", "unchecked":["real user attendance/competence", "production access handoff", "real operations ownership"]},
        [release_ref,solution_ref,ui_ref,integration_ref,runbook_ref,code_ref,test_log_ref,operations_ref,decision_src])
    skill("delivery-training-handover", [release_ref,solution_ref,ui_ref,integration_ref,runbook_ref], [handover_ref], [decision_src,test_log_ref,operations_ref], "按业务/运维受众准备手册、模拟练习及精确资产接收，保留真实培训未查")
    stage("tested-released-and-handed-over-locally", testing_ref,release_ref,handover_ref)

    milestone_refs, confirmation_refs = [], []
    for mid, deliverables, criterion in [
        ("M-BLUEPRINT",[blueprint_ref],"七项蓝图范围与R1-R3覆盖"),
        ("M-DESIGN",[solution_ref,ui_ref,integration_ref],"字段/角色/状态/接口/恢复设计可追溯"),
        ("M-INTEGRATION",[integration_ref,wp_refs[2]],"实际本地HTTP错误路径与条数/业务键核对"),
        ("M-UAT",[testing_ref],"13项工程测试通过与模拟UAT接受"),
        ("M-FINAL",[release_ref,handover_ref],"本地fixture运行成功、模拟培训移交和质保安排"),
    ]:
        mref = reg(mid,"milestone",{"milestone_id":mid,"scope":["R1","R2","R3"],"deliverable_refs":deliverables,
            "criteria":[{"id":"CRIT-"+mid,"text":criterion,"state":"pass-simulation","evidence_refs":[test_log_ref,operations_ref,decision_src]}],
            "open_items":[],"origin":"simulation","real_customer_acceptance":False},[contract_ref,plan_ref,*deliverables,test_log_ref,operations_ref,decision_src])
        milestone_refs.append(mref)
        confirmation_refs.append(confirm("CONF-"+mid,mref,["R1","R2","R3",criterion]))
    skill("delivery-milestone-acceptance", [contract_ref,plan_ref,blueprint_ref,testing_ref,release_ref,handover_ref], [*milestone_refs,*confirmation_refs], [decision_src,test_log_ref,operations_ref], "逐阶段绑定五个里程碑交付物、标准及模拟确认，不推断真实验收或付款")
    weekly_ref = reg("WEEKLY","weekly",{"period":"2026-10-06/2026-10-11","as_of":DATE,
        "completed":["模拟合同/启动/调研/蓝图/设计已回读", "13个真实本地测试通过；并发回归通过" + ("，历史缺陷修复证据已读回" if failed_log_ref else "；历史失败日志未提供"), "本地fixture运行、恢复演练和模拟移交", "PLAN/COST原子变更"],
        "next":["质保支持转support-sim，未来2027-10-10核验结束", "真实项目另行获取ERP/生产/安全条件"],
        "milestones":[{"id":mid,"state":"accepted-simulation"} for mid in milestone_ids],
        "risks":["真实ERP兼容性、生产安全、压力指标未验证"], "decisions_required":[], "coverage_gaps":["实际Office/浏览器视觉审核待后续产物生成后执行", "无真实客户/UAT/签署"] + ([] if failed_log_ref else ["历史工程失败日志未提供；仅报告当前回归，不声称历史缺陷关闭"]),
        "internal_cost_summary":summary,"origin":"simulation","sent":False},
        [plan_ref,cost_ref,hours_ref,risks_ref,change_ref,testing_ref,release_ref,handover_ref,*milestone_refs,*confirmation_refs])
    skill("delivery-reporting", [plan_ref,cost_ref,hours_ref,risks_ref,change_ref,*milestone_refs,*confirmation_refs], [weekly_ref], [ledger_ref,test_log_ref,operations_ref,decision_src], "按截止日生成事实/模拟/预测及未查范围分开的内部周报")

    review_data = {"targets":[blueprint_ref,solution_ref,ui_ref,integration_ref,testing_ref,release_ref,handover_ref],
        "verdict":"conditional", "reviewer":"local-structural-and-semantic-rehearsal", "method":"independent-runtime hash/reference readback + local simulation scope/requirement/engineering evidence inspection",
        "findings":[{"id":"F-BOUNDARY", "severity":"major", "status":"open", "resolution_evidence":"", "detail":"必须逐份声明fixture执行不等于生产系统、UAT/培训/合同均为模拟"}],
        "unchecked":["Office rendering/visual layout (not generated yet)","browser UI implementation","real customer identity/signatures","real ERP security/performance"],
        "scope":["exact versions", "scope and traceability", "local fixture results", "simulation boundaries"], "actual_visual_audit_pass":False}
    review_r1 = reg("REVIEW", "review", review_data, [*review_data["targets"],decision_src,operations_ref,test_log_ref])
    # A conditional review must block customer preparation; this is an actual
    # rejected runtime operation, not an assertion written into narrative.
    try:
        runtime.prepare_customer(project,["BLUEPRINT"],out/"rejected-customer-package")
    except ValueError as exc:
        review_rejection = str(exc)
    else:
        raise RuntimeError("Conditional review unexpectedly allowed package")
    check("conditional-review-rejected", not (out/"rejected-customer-package").exists(), review_rejection)
    review_data["verdict"] = "pass"
    review_data["findings"][0].update(status="closed", resolution_evidence="All artifacts/report explicitly bind local-fixture evidence and origin=simulation; no production/customer claim. See SRC-DECISIONS D1-D6 and TEST unchecked.")
    review_data["scope"].append("pass applies only to structural/semantic rehearsal scope; Office/browser visual audit remains unchecked")
    review_ref = reg("REVIEW","review",review_data,[*review_data["targets"],decision_src,operations_ref,test_log_ref],revision=2)
    # No local customer package is emitted here: root generates and reviews the
    # real Office files later. The narrow review pass is not a visual pass.
    check("same-review-corrected", runtime.load_artifact(project,review_ref)["data"]["verdict"] == "pass" and review_r1["artifact_id"] == review_ref["artifact_id"] and review_ref["revision"] == 2, "Conditional review retained in revision1; exact-target revision2 corrects boundary finding")
    skill("delivery-artifact-review", [blueprint_ref,solution_ref,ui_ref,integration_ref,testing_ref,release_ref,handover_ref], [review_r1,review_ref], [decision_src,operations_ref,test_log_ref], "结构/语义范围内真实拒绝→整改→复核；Office及浏览器视觉检查明确未查")
    stage("milestones-reporting-and-review-correction", *milestone_refs,weekly_ref,review_ref)

    settlement_ref = reg("SETTLEMENT-EVIDENCE", "evidence", {"items":[{"id":"SET-1","source_id":ledger_ref["artifact_id"],"locator":"/time_records,/expenses,/total", "content":"模拟账本42审核内部小时×100=4200 + 外包1600 + 采购600 + 差旅200 = 6600；付款条件2400不二次计成本；与runtime forecast=6600一致；无真实财务执行", "read_status":"read"}], "unread_scope":[],"origin":"simulation"}, [ledger_ref,decision_src,hours_ref,cost_ref])
    closure_ref = reg("CLOSURE", "closure", {"origin":"simulation", "as_of":DATE,
        "obligations":[
            {"id":"OB-IMPLEMENT", "title":"R1-R3本地演练交付与模拟最终确认", "category":"implementation", "owner":"pm-sim", "state":"closed", "due_date":DATE, "evidence_refs":[milestone_refs[-1],confirmation_refs[-1],testing_ref,release_ref], "recipient":None, "receipt_refs":[]},
            {"id":"OB-WARRANTY", "title":"一年质保支持义务", "category":"warranty", "owner":"support-sim", "state":"transferred", "due_date":"2027-10-10", "evidence_refs":[contract_ref,handover_ref], "recipient":"support-sim", "receipt_refs":[handover_ref], "support_path":"support-sim -> pm-sim; rehearsal only"}],
        "warranty":{"applicable":True,"reason":"模拟合同C6约定一年质保", "owner":"support-sim", "start_date":DATE,"end_date":"2027-10-10", "terms_refs":[contract_ref],"transfer_refs":[handover_ref],
                    "items":[{"id":"WAR-TRACK", "title":"质保期间支持跟踪与到期复核（尚未到期）", "owner":"support-sim", "state":"open", "evidence_refs":[contract_ref,handover_ref]}]},
        "administration":{"state":"closed","decision_refs":[minutes_ref,confirmation_refs[-1]]},
        "settlement":{"state":"reconciled","evidence_refs":[settlement_ref],"boundary":"supported synthetic ledger reconciliation only; not financial approval, cash, invoice or revenue"},
        "resources":[{"id":"RESOURCE-LOCAL", "owner":"operator-sim", "state":"released", "reason":"temporary fixture cleanup executed by direct_operations finally", "evidence_refs":[operations_ref]},
                     {"id":"RESOURCE-SUPPORT", "owner":"support-sim", "state":"retained", "reason":"保留质保职责到2027-10-10", "evidence_refs":[handover_ref]}],
        "archive":[{"id":"ARCH-"+ref["artifact_id"],"artifact_ref":ref,"owner":"pm-sim","classification":"internal-simulation","retention_until":"2031-10-11"} for ref in [contract_ref,requirements_ref,blueprint_ref,plan_ref,solution_ref,ui_ref,integration_ref,testing_ref,release_ref,handover_ref,weekly_ref]],
        "lessons":[{"id":"LESSON-CONC", "observation":"并发幂等回归是R1必要边界；历史失败日志" + ("已提供并读回" if failed_log_ref else "未提供，不能声明已复现历史失败"), "action":"保留事务锁及当前并发复测证据", "owner":"developer-sim"},
                   {"id":"LESSON-GATES", "observation":"准入、执行、模拟确认、行政结项和质保结束是独立状态", "action":"未来到期和真实项目分别验证", "owner":"pm-sim"}]},
        [contract_ref,requirements_ref,blueprint_ref,plan_ref,solution_ref,ui_ref,integration_ref,testing_ref,release_ref,handover_ref,weekly_ref,minutes_ref,*milestone_refs,*confirmation_refs,settlement_ref,operations_ref])
    skill("delivery-closure-warranty", [contract_ref,plan_ref,cost_ref,hours_ref,risks_ref,testing_ref,release_ref,handover_ref,*milestone_refs,*confirmation_refs,settlement_ref], [closure_ref], [settlement_ref,handover_ref,decision_src,operations_ref], "基于合成账本行政结项并移交一年质保，保留未到期/开放义务")

    profile_ref = reg("PROFILE","profile",{"billing_mode":"fixed","delivery_mode":"staged","terms_refs":[contract_ref],"open_items":[],"streams":[
        {"id":"BILL-1","mode":"fixed","scope_ids":["R1","R2","R3"],"currency":"CNY","amount":12000,"hours":None,"rate":None,"cap":None,"basis":"模拟合同C5固定价；不是收入确认","terms_refs":[contract_ref]}]},[contract_ref])
    form_ref = source("SRC-TEMPLATE-FORM","08-customer-field-spec.json",{"fields":[{"id":"project_title","type":"string","required":True},{"id":"period","type":"string","required":True},{"id":"note","type":"string","required":False}]})
    mapping_ref = reg("TEMPLATE-MAP","template_mapping",{"form_ref":form_ref,"audience":"internal",
        "mappings":[{"id":"MAP-TITLE","target_field":"project_title","source_ref":minutes_ref,"source_pointer":"/title","transform":"identity"},
                    {"id":"MAP-PERIOD","target_field":"period","source_ref":weekly_ref,"source_pointer":"/period","transform":"identity"}],
        "omissions":[{"id":"OMIT-NOTE","target_field":"note","reason":"未提供可选注释"}]},[form_ref,minutes_ref,weekly_ref])
    exchange_data = {"operation_id":"FULL-SIM-DOC-001","system":"local-simulation-fixture","entity":"document","direction":"outbound","record_id":"WEEKLY","external_id":"SIM-EXT-WEEKLY","mapping_ref":mapping_ref,"state":"prepared","receipt_ref":None,"conflicts":[]}
    exchange_r1 = reg("EXCHANGE","exchange",exchange_data,[mapping_ref])
    mapped = runtime.prepare_mapped(project,"EXCHANGE",out/"mapped-candidate.json")
    receipt = {key:exchange_data[key] for key in ("operation_id","system","entity","direction","record_id","external_id")}
    receipt.update(payload_sha256=runtime.reuse.payload_hash({"project_title":TITLE,"period":"2026-10-06/2026-10-11"}),state="applied",origin="simulation")
    receipt_ref = source("SRC-EXCHANGE-RECEIPT","09-simulated-exchange-receipt.json",receipt)
    exchange_data.update(state="reconciled",receipt_ref=receipt_ref)
    exchange_ref = reg("EXCHANGE","exchange",exchange_data,[mapping_ref,receipt_ref],revision=2)
    # Orchestrator itself owns the complete routing journal and reuse helpers.
    skill("delivery-orchestrator", [contract_ref,plan_ref,cost_ref,requirements_ref,blueprint_ref,closure_ref], [profile_ref,mapping_ref,exchange_r1,exchange_ref,closure_ref,weekly_ref], [decision_src,receipt_ref,test_log_ref,operations_ref], "恢复有效集合、组织25技能任务卡及配置/本地模板/交换候选，绝不外部发送")
    expected_skills = {path.parent.name for path in (phase.SUITE/"skills").glob("delivery-*/SKILL.md")}
    check("all-25-skills-routed", len(expected_skills)==25 and {run["skill"] for run in skill_runs}==expected_skills and len(skill_runs)==25, sorted(run["skill"] for run in skill_runs))
    for run in skill_runs:
        for ref in run["input_refs"]+run["output_refs"]+run["evidence_refs"]:
            runtime.check_ref(project,ref)
    check("all-skill-task-refs-readable", all(run["input_refs"] and run["output_refs"] and run["evidence_refs"] for run in skill_runs), "Every25 task has actual exact input/output/evidence refs and package SHA")
    snapshot_final = runtime.snapshot(project)
    validation = runtime.validate(project)
    closure_gate = snapshot_final["gates"]["CLOSURE"]
    check("closure-four-independent-gates", closure_gate["administrative_closed"] and closure_gate["warranty_transferred"] and not closure_gate["warranty_ended"] and not closure_gate["fully_discharged"], closure_gate)
    check("local-release-executed", snapshot_final["gates"]["REL"]["ready"] and not snapshot_final["gates"]["REL"]["ready_to_execute"], snapshot_final["gates"]["REL"])
    check("all-requirements-engineering-covered", {rid for case in cases if case["state"]=="pass" for rid in case["requirement_ids"]}=={"R1","R2","R3"}, "Actual local testlog and operation refs bound per requirement")
    check("complete-runtime-validation", validation["ok"] and not snapshot_final["alerts"], validation)
    stage("administrative-closure-warranty-transferred", closure_ref,profile_ref,mapping_ref,exchange_ref)
    report = {
        "report_version":"0.3.0", "project_id":PROJECT_ID, "project_title":TITLE, "purpose":"simulation",
        "validation":validation, "test_status":{"tests_run":result.testsRun,"failures":len(result.failures),"errors":len(result.errors),"skipped":len(result.skipped),"successful":result.wasSuccessful(),"raw_log":"materials/06-local-engineering-tests.log"},
        "engineering_test_status":{"tests_run":result.testsRun,"successful":result.wasSuccessful(),"build_ref":build,"test_log_ref":test_log_ref,"failed_log_ref":failed_log_ref},
        "sources":sources,"build_ref":build,"skill_runs":skill_runs,"skill_journal":skill_runs,"stage_snapshots":stages,"checks":checks,
        "change_application":application, "cost_summary":runtime.cost_summary(project), "closure_gate":closure_gate,
        "release_gate_snapshots":{"planned":next(stage for stage in stages if stage["stage"]=="release-planned")["gates"]["REL"],"executed":snapshot_final["gates"]["REL"]},
        "historical_defect_evidence_available":bool(failed_log_ref), "historical_defect_gap":None if failed_log_ref else "Historical failure log unavailable; current regression tested; no historical defect closure claimed",
        "review_rejection":review_rejection,"unapproved_change_rejection":rejected_change,"boundary":BOUNDARY,
        "artifacts":[{key:record[key] for key in ("artifact_id","revision","kind","status","health","sha256")} for record in snapshot_final["artifacts"]],
    }
    phase.write_json(out/"report.json",report)
    phase.write_json(out/"snapshot.json",snapshot_final)
    phase.write_json(out/"skill-task-journal.json",skill_runs)
    review_text = """# 全流程演练复核与已知边界

本案例 purpose=simulation。25个技能任务均记录真实SKILL源码SHA、精确输入/输出/证据引用；不是调用名称清单。

- 实际执行13个本地HTTP/SQLite测试。真实并发幂等缺陷 DEF-CONC-001 的失败日志、修复代码SHA、并发回归和全13项复测均已绑定。
- 实际执行创建/读取/重复/冲突/权限/审批/迁移/备份/恢复；本地fixture发布表示启动并运行演练，临时环境已清理，不是生产平台或浏览器应用部署。
- 实际拒绝 proposed 变更，保留旧PLAN/COST；approved 后一次应用两份候选。原始基线、当前批准基线、模拟预测/实际演练日期并列保留。
- 实际 conditional 审查阻止 prepare-customer；同ID修订2只通过结构/语义/边界复核，Office视觉/浏览器UI及真实客户身份仍明确unchecked。后续Office产物须由独立最终审查回读，不能把本次pass扩大到视觉审查。
- 合同、访谈、预算、工时、费用、付款、客户确认、UAT、培训和运维接收均为模拟来源。结算仅证明合成台账4200+1600+600+200=6600且无重复，不认证财务事实或支付。
- 行政结项=true，质保移交=true；质保结束=false，全部义务解除=false。质保2027-10-10到期，WAR-TRACK开放，OB-WARRANTY移交但未解除，support资源保留。
- ERP是无认证loopback资产服务替身。未验证真实ERP、生产安全、压力/可用性SLA、浏览器页面、真实用户能力、真实客户UAT/签章/验收。
- 辅助模板映射仅生成本地JSON，交换收据origin=simulation，不发送网络请求、不创建外部任务、不回写财务或业务系统。
"""
    if not failed_log_ref:
        review_text = review_text.replace("真实并发幂等缺陷 DEF-CONC-001 的失败日志、修复代码SHA、并发回归和全13项复测均已绑定。", "当前代码SHA、并发回归和全13项测试均已绑定；历史失败日志未提供，不声明历史缺陷关闭。")
    (out/"review-findings.md").write_text(review_text, encoding="utf-8")
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out",required=True,type=Path,help="Fresh output directory; never overwritten")
    args = parser.parse_args(argv)
    out = args.out.expanduser().resolve()
    if out.exists():
        parser.error(f"Refusing existing output directory: {out}")
    out.mkdir(parents=True)
    try:
        report = build_case(out)
    except Exception as exc:
        print(f"full delivery verification failed: {exc}",file=sys.stderr)
        return 1
    print(json.dumps({"out":str(out),"project_id":PROJECT_ID,"skills":len(report["skill_runs"]),"tests_run":report["test_status"]["tests_run"],"validation_ok":report["validation"]["ok"]},ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
