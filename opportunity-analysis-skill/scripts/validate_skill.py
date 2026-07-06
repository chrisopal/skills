#!/usr/bin/env python3
from __future__ import annotations

import argparse
import html
import json
import py_compile
import re
import shutil
import sqlite3
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.dont_write_bytecode = True
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from opportunity_skill.pipeline import run_analyze, run_detail, run_query  # noqa: E402
from opportunity_skill.assessment import normalize_rating  # noqa: E402
from opportunity_skill.confirmation import collect_sales_confirmation_answers  # noqa: E402
from opportunity_skill.storage import OpportunitySQLiteAdapter  # noqa: E402
from opportunity_skill.stage_management import infer_opportunity_stage, stage_from_name, stage_names  # noqa: E402
from opportunity_skill.stages.account_profile_extraction import extract_account_profile  # noqa: E402
from opportunity_skill.stages.evidence_normalization import all_text, normalize_input  # noqa: E402
from opportunity_skill.stages.opportunity_analysis import analyze_opportunity  # noqa: E402


def fail(message: str) -> None:
    raise SystemExit(f"VALIDATION FAILED: {message}")


def load_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        fail(f"{path.relative_to(ROOT)} is not valid JSON: {exc}")


def escaped_text(value: object) -> str:
    return html.escape(str(value), quote=True)


def check_json_files() -> None:
    for path in sorted((ROOT / "schemas").glob("*.json")):
        load_json(path)
    for path in sorted((ROOT / "examples").glob("*.json")):
        load_json(path)
    load_json(ROOT / "evaluation" / "test_cases.json")
    print("ok json files")


def clean_local_runtime_artifacts() -> None:
    for pattern in ["src/*.egg-info", "**/__pycache__", "**/*.pyc"]:
        for path in ROOT.glob(pattern):
            if path.is_dir():
                shutil.rmtree(path, ignore_errors=True)
            elif path.exists():
                path.unlink()


def check_python_compile() -> None:
    temp_root = Path(tempfile.mkdtemp(prefix="opportunity-skill-pyc-"))
    try:
        for path in sorted((ROOT / "src").rglob("*.py")) + sorted((ROOT / "scripts").rglob("*.py")):
            pyc_path = temp_root / (path.relative_to(ROOT).as_posix().replace("/", "__") + ".pyc")
            py_compile.compile(str(path), cfile=str(pyc_path), doraise=True)
    finally:
        shutil.rmtree(temp_root, ignore_errors=True)
    print("ok python compile")


def check_template_safety() -> None:
    unsafe = re.compile(r"<\s*script\b|javascript:|\son[a-zA-Z]+\s*=", re.IGNORECASE)
    for path in sorted((ROOT / "display" / "templates").glob("*.html")):
        text = path.read_text(encoding="utf-8")
        if unsafe.search(text):
            fail(f"unsafe HTML pattern in {path.relative_to(ROOT)}")
    print("ok template safety")


def check_stage_modules() -> None:
    raw = {
        "account_hint": "阶段验证有限公司",
        "materials": [
            {
                "type": "meeting_note",
                "name": "阶段拆分验证",
                "content": "客户：阶段验证有限公司。王总（客户-生产负责人）希望做质检自动化升级，现有MES已上线，Q3前完成方案确认，预算已立项。张伟 采购总监 138-1234-5678 zhang.wei@example.com。",
                "confidence": 0.9,
            }
        ],
    }
    evidence = normalize_input(raw)
    if not evidence or evidence[0]["source_type"] != "meeting_note":
        fail("evidence_normalization stage did not wrap materials")
    text = all_text(evidence)
    profile = extract_account_profile(text, raw, evidence)
    if profile["company_name"] != "阶段验证有限公司":
        fail("account_profile_extraction stage did not use account hint")
    if not profile["contacts"] or profile["decision_chain"][0]["status"] != "confirmed":
        fail("account_profile_extraction stage did not produce contacts and decision chain")
    result = analyze_opportunity(raw, evidence, text, profile)
    if "structured_data" not in result or "human_summary" not in result:
        fail("opportunity_analysis stage did not return analysis result")
    for key in ["account", "contacts", "opportunity", "commercial_assessment", "decision_chain", "risks", "next_actions"]:
        if key not in result["structured_data"]:
            fail(f"opportunity_analysis stage missing structured_data.{key}")
    if result["structured_data"]["opportunity"]["core_need"] != "质检自动化升级":
        fail("opportunity_analysis stage did not extract core need")
    print("ok stage modules")


def check_stage_management() -> None:
    expected = [
        "线索识别",
        "客户接触",
        "需求澄清",
        "商机确认",
        "方案共创",
        "预算/立项确认",
        "报价/投标",
        "商务谈判",
        "赢单",
        "丢单",
    ]
    if stage_names() != expected:
        fail(f"stage model order mismatch: {stage_names()}")
    compatibility_checks = {
        "线索": "lead_identified",
        "初步沟通": "customer_contacted",
        "需求确认": "needs_discovery",
        "方案交流": "solution_cocreation",
        "投标/报价": "proposal_bidding",
    }
    for legacy_name, expected_stage_id in compatibility_checks.items():
        stage = stage_from_name(legacy_name)
        if stage is None or stage.stage_id != expected_stage_id:
            fail(f"legacy stage name {legacy_name} should map to {expected_stage_id}, got {stage}")
    result = infer_opportunity_stage({
        "text": "客户希望Q3前完成方案确认，安排技术交流，讨论检测点位和MES对接。",
        "core_need": "质检自动化升级",
        "contacts": [{"name": "王总", "is_requirement_owner": True}],
        "decision_chain": [{"decision_role": "业务需求负责人", "status": "confirmed"}],
        "budget_signal": "预算信息未明确",
        "timeline": "Q3",
    })
    if result["stage_id"] != "solution_cocreation":
        fail(f"solution signals should infer solution_cocreation, got {result}")
    if result["stage"] != "方案共创":
        fail("stage result should keep Chinese stage name")
    if not result["opportunity_confirmed"]:
        fail("solution_cocreation should be a confirmed opportunity")
    if "技术交流" not in "".join(result["stage_signal_hits"]):
        fail("stage signal hits should explain matched signals")
    poc_result = infer_opportunity_stage({
        "text": "客户计划先做POC验证，再评估方案。",
        "core_need": "质检自动化升级",
        "contacts": [{"name": "王总", "is_requirement_owner": True}],
        "decision_chain": [{"decision_role": "业务需求负责人", "status": "confirmed"}],
        "budget_signal": "预算信息未明确",
        "timeline": "时间节点未明确",
    })
    if poc_result["stage_id"] != "solution_cocreation" or poc_result["stage_id"] in {"won", "lost"}:
        fail(f"POC should stay in pre-sales stage instead of terminal stage, got {poc_result}")
    poc_scope_result = infer_opportunity_stage({
        "text": "讨论POC范围和接口对接。",
        "core_need": "质检自动化升级",
        "contacts": [{"name": "王总", "is_requirement_owner": True}],
        "decision_chain": [{"decision_role": "业务需求负责人", "status": "confirmed"}],
        "budget_signal": "预算信息未明确",
        "timeline": "时间节点未明确",
    })
    if poc_scope_result["stage_id"] != "solution_cocreation" or poc_scope_result["stage_id"] in {"won", "lost"}:
        fail(f"POC scope discussion should stay in pre-sales stage instead of terminal stage, got {poc_scope_result}")
    early = infer_opportunity_stage({
        "text": "客户名片已获取，后续再沟通。",
        "core_need": "客户需求待进一步澄清",
        "contacts": [{"name": "张三"}],
        "decision_chain": [],
        "budget_signal": "预算信息未明确",
        "timeline": "时间节点未明确",
    })
    if early["stage_id"] != "customer_contacted" or early["opportunity_confirmed"]:
        fail(f"early contact should not be confirmed opportunity, got {early}")
    for negative_text, contacts in [
        ("项目还未审批通过，客户名片已获取。", [{"name": "李经理"}]),
        ("内部审批通过前暂不启动，客户名片已获取。", [{"name": "李经理"}]),
        ("项目尚未审批通过，后续再沟通。", []),
        ("可能已立项，仍待确认。", []),
        ("若后续预算获批，将安排招标。", []),
        ("如果审批通过，再启动项目。", []),
        ("待审批通过后推进采购。", []),
        ("若内部审批通过，将在Q3启动。", []),
        ("如果项目已立项，再启动。", []),
        ("若预算已批，将推进采购。", []),
        ("待采购计划已确认后再启动。", []),
        ("审批通过后安排采购。", []),
        ("项目审批通过后安排招标。", []),
    ]:
        negative_result = infer_opportunity_stage({
            "text": negative_text,
            "core_need": "客户需求待进一步澄清",
            "contacts": contacts,
            "decision_chain": [],
            "budget_signal": "预算信息未明确",
            "timeline": "时间节点未明确",
        })
        if negative_result["stage_id"] in {"budget_project_confirmed", "proposal_bidding"} or negative_result["opportunity_confirmed"]:
            fail(f"negative approval wording should stay unconfirmed, got {negative_result}")
    positive_budget = infer_opportunity_stage({
        "text": "项目已立项，审批通过，采购计划已明确。",
        "core_need": "客户需求待进一步澄清",
        "contacts": [],
        "decision_chain": [],
        "budget_signal": "预算信息未明确",
        "timeline": "时间节点未明确",
    })
    if positive_budget["stage_id"] != "budget_project_confirmed" or not positive_budget["opportunity_confirmed"]:
        fail(f"explicit positive approval should infer budget_project_confirmed, got {positive_budget}")
    for positive_text, expected_stage_id in [
        ("项目已立项，后续安排采购。", "budget_project_confirmed"),
        ("项目已立项后安排采购。", "budget_project_confirmed"),
        ("合同已签，后续安排交付。", "won"),
        ("合同已签后安排交付。", "won"),
        ("正在招标，客户已发RFP。", "proposal_bidding"),
        ("客户已下PO，后续安排交付。", "won"),
        ("客户已下PO后安排交货。", "won"),
        ("客户PO已确认。", "won"),
        ("PO已下发，安排交货。", "won"),
    ]:
        positive_result = infer_opportunity_stage({
            "text": positive_text,
            "core_need": "客户需求待进一步澄清",
            "contacts": [],
            "decision_chain": [],
            "budget_signal": "预算信息未明确",
            "timeline": "时间节点未明确",
        })
        if positive_result["stage_id"] != expected_stage_id or not positive_result["opportunity_confirmed"]:
            fail(f"positive progress wording should stay confirmed, got {positive_result}")
    print("ok stage management")


def check_confirmation_loop() -> None:
    for text in ["未知", "不确定", "待确定", "待确认", "pending", "tbd"]:
        if normalize_rating(text) != "unknown":
            fail(f"confirmation rating alias {text} did not normalize to unknown")
    prompts = []
    responses = iter(["待确认", "商务还没有拿到客户明确答复"])
    answers = collect_sales_confirmation_answers(
        [
            {
                "id": "q_demo",
                "dimension_id": "customer_purchase_intent",
                "label": "客户购买意向",
                "question": "客户是否已经正式立项？",
            }
        ],
        input_func=lambda prompt: (prompts.append(prompt) or next(responses)),
        output_func=lambda _message: None,
        answered_by="验证商务",
    )
    if answers[0]["rating"] != "unknown" or answers[0]["dimension_id"] != "customer_purchase_intent":
        fail("interactive confirmation did not preserve unknown answer and dimension_id")
    if answers[0]["answered_by"] != "验证商务":
        fail("interactive confirmation did not record answered_by")
    print("ok confirmation loop")


def assert_output_contract(result: dict, source: str) -> None:
    for key in ["human_summary", "structured_data", "storage_result", "display_result"]:
        if key not in result:
            fail(f"{source} missing top-level key {key}")
    structured = result["structured_data"]
    for key in ["account", "contacts", "opportunity", "risks", "next_actions", "decision_chain", "commercial_assessment", "sales_confirmation_questions", "evidence", "missing_information", "evidence_map"]:
        if key not in structured:
            fail(f"{source} missing structured_data.{key}")
    assessment = structured["commercial_assessment"]
    for key in ["win_likelihood_score", "deal_attractiveness_score", "delivery_confidence_score", "overall_opportunity_score", "win_probability", "confidence_level", "dimensions", "questions"]:
        if key not in assessment:
            fail(f"{source} missing commercial_assessment.{key}")
    opportunity = structured["opportunity"]
    for key in ["stage_id", "stage_reason", "stage_confidence", "stage_signal_hits", "opportunity_confirmed"]:
        if key not in opportunity:
            fail(f"{source} missing opportunity.{key}")
    storage = result["storage_result"]
    for key in ["adapter", "saved", "account_id", "opportunity_id", "db_path"]:
        if key not in storage:
            fail(f"{source} missing storage_result.{key}")
    display = result["display_result"]
    for key in ["template_id", "html", "markdown", "html_path", "markdown_path", "rendered_view_id"]:
        if key not in display:
            fail(f"{source} missing display_result.{key}")


def write_tiny_png(path: Path) -> None:
    path.write_bytes(
        bytes.fromhex(
            "89504e470d0a1a0a0000000d4948445200000001000000010802000000907753"
            "de0000000c49444154789c63606060000000040001f61738550000000049454e44ae426082"
        )
    )


def check_legacy_stage_storage_compatibility(temp_root: Path) -> None:
    legacy_dir = temp_root / "legacy-stage"
    legacy_dir.mkdir(parents=True, exist_ok=True)
    db_path = legacy_dir / "legacy.db"

    conn = sqlite3.connect(db_path)
    try:
        conn.executescript(
            """
            PRAGMA foreign_keys = ON;
            CREATE TABLE accounts (
                id TEXT PRIMARY KEY,
                company_name TEXT NOT NULL,
                normalized_name TEXT,
                industry TEXT,
                region TEXT,
                company_size TEXT,
                business_summary TEXT,
                current_systems TEXT,
                key_pain_points TEXT,
                source_confidence REAL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE opportunities (
                id TEXT PRIMARY KEY,
                account_id TEXT NOT NULL,
                name TEXT NOT NULL,
                stage TEXT,
                stage_status TEXT,
                core_need TEXT,
                budget_signal TEXT,
                budget_amount TEXT,
                expected_timeline TEXT,
                win_probability REAL,
                score INTEGER,
                score_level TEXT,
                risk_level TEXT,
                competitors TEXT,
                pain_points TEXT,
                requirements TEXT,
                missing_information TEXT,
                status TEXT DEFAULT 'active',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(account_id) REFERENCES accounts(id)
            );
            """
        )
        conn.execute(
            """
            INSERT INTO accounts (
                id, company_name, normalized_name, industry, region, company_size, business_summary,
                current_systems, key_pain_points, source_confidence, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "acc_legacy",
                "旧库兼容有限公司",
                "旧库兼容",
                "离散制造",
                "苏州",
                "中型",
                "旧库阶段兼容验证",
                "[]",
                "[\"多系统协同\"]",
                0.8,
                "2026-07-07T00:00:00+00:00",
                "2026-07-07T00:00:00+00:00",
            ),
        )
        conn.execute(
            """
            INSERT INTO opportunities (
                id, account_id, name, stage, stage_status, core_need, budget_signal, budget_amount,
                expected_timeline, win_probability, score, score_level, risk_level, competitors,
                pain_points, requirements, missing_information, status, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "opp_legacy",
                "acc_legacy",
                "旧阶段商机",
                "方案交流",
                "active",
                "验证旧阶段映射",
                "预算待确认",
                None,
                "Q4",
                0.45,
                58,
                "medium",
                "medium",
                "[]",
                "[\"现场节拍波动\"]",
                "[\"需要方案讨论\"]",
                "[\"预算批复时间\"]",
                "active",
                "2026-07-07T00:00:00+00:00",
                "2026-07-07T00:00:00+00:00",
            ),
        )
        conn.commit()
    finally:
        conn.close()

    adapter = OpportunitySQLiteAdapter(db_path)
    try:
        columns = {row["name"] for row in adapter.conn.execute("PRAGMA table_info(opportunities)").fetchall()}
        for required in {"stage_id", "stage_reason", "stage_confidence", "stage_signal_hits", "opportunity_confirmed"}:
            if required not in columns:
                fail(f"legacy database migration did not add {required}")
        detail = adapter.get_opportunity_detail("opp_legacy")
        legacy_opportunity = detail.get("opportunity", {})
        if legacy_opportunity.get("stage_id") != "solution_cocreation":
            fail(f"legacy detail did not infer stage_id from old stage name: {legacy_opportunity}")
        if legacy_opportunity.get("stage") != "方案共创":
            fail(f"legacy detail did not normalize canonical stage name: {legacy_opportunity}")
        if legacy_opportunity.get("stage_signal_hits") != []:
            fail(f"legacy detail should default stage_signal_hits to [], got {legacy_opportunity}")
        if legacy_opportunity.get("opportunity_confirmed") is not True:
            fail(f"legacy detail should infer confirmed status from mapped stage, got {legacy_opportunity}")
    finally:
        adapter.close()

    for stage_filter in ["方案交流", "方案共创"]:
        query_result = run_query(
            db_path,
            {"query_type": "opportunity_search", "filters": {"stage": stage_filter}, "limit": 10},
            legacy_dir / f"query-{stage_filter}",
            render_html=False,
        )
        returned_ids = {item.get("id") for item in query_result.get("opportunities", [])}
        if "opp_legacy" not in returned_ids:
            fail(f"legacy database stage filter {stage_filter} did not match old-stage row: {query_result}")
    print("ok legacy stage storage")


def check_evaluation_cases(keep_artifacts: bool = False) -> None:
    cases = load_json(ROOT / "evaluation" / "test_cases.json")
    temp_root = Path(tempfile.mkdtemp(prefix="opportunity-skill-validate-"))
    try:
        first_result = None
        for case in cases:
            case_dir = temp_root / case["name"]
            db_path = case_dir / "opportunity.db"
            output_dir = case_dir / "outputs"
            input_data = load_json(ROOT / case["input"])
            result = run_analyze(input_data, db_path, output_dir)
            assert_output_contract(result, case["name"])
            opportunity = result["structured_data"]["opportunity"]
            expected_stage = stage_from_name(case["expected_stage"])
            actual_stage = stage_from_name(opportunity.get("stage"))
            if expected_stage is None:
                fail(f"{case['name']} expected stage is unknown: {case['expected_stage']}")
            if actual_stage is None:
                fail(f"{case['name']} produced unknown stage name: {opportunity.get('stage')}")
            if opportunity.get("stage_id") != expected_stage.stage_id:
                fail(f"{case['name']} stage_id {opportunity.get('stage_id')} != {expected_stage.stage_id}")
            if actual_stage.stage_id != expected_stage.stage_id:
                fail(f"{case['name']} stage {opportunity['stage']} does not match expected flow {case['expected_stage']}")
            if opportunity.get("stage") != actual_stage.name:
                fail(f"{case['name']} should emit canonical stage name {actual_stage.name}, got {opportunity.get('stage')}")
            if opportunity["score"] < case["expected_min_score"]:
                fail(f"{case['name']} score {opportunity['score']} < {case['expected_min_score']}")
            if not Path(result["display_result"]["html_path"]).exists():
                fail(f"{case['name']} did not write HTML output")
            if not Path(result["display_result"]["markdown_path"]).exists():
                fail(f"{case['name']} did not write Markdown output")
            if not result["structured_data"].get("decision_chain"):
                fail(f"{case['name']} did not produce decision_chain")
            first_result = first_result or result

        if first_result is None:
            fail("no evaluation cases found")
        first_db = Path(first_result["storage_result"]["db_path"])
        query_result = run_query(
            first_db,
            {"query_type": "opportunity_search", "filters": {"min_score": 1}, "sort": {"field": "score", "order": "desc"}, "limit": 10},
            temp_root / "query",
            render_html=True,
        )
        if query_result["count"] < 1:
            fail("query returned no opportunities")
        query_html = query_result.get("display_result", {}).get("html", "")
        if not query_html:
            fail("query HTML render is empty")
        for opportunity in query_result.get("opportunities", []):
            name = opportunity.get("name")
            company = opportunity.get("company_name")
            stage = opportunity.get("stage")
            if name and escaped_text(name) in query_html:
                continue
            if company and stage and escaped_text(company) in query_html and escaped_text(stage) in query_html:
                continue
            fail(f"query HTML did not include returned opportunity {opportunity.get('id')}: {opportunity}")
        legacy_stage_aliases = {
            "lead_identified": "线索",
            "customer_contacted": "初步沟通",
            "needs_discovery": "需求确认",
            "solution_cocreation": "方案交流",
            "proposal_bidding": "投标/报价",
        }
        source_opportunity = first_result["structured_data"].get("opportunity", {})
        legacy_stage_filter = legacy_stage_aliases.get(source_opportunity.get("stage_id"))
        if not legacy_stage_filter:
            fail(f"missing legacy stage alias for validator fixture: {source_opportunity}")
        legacy_stage_query = run_query(
            first_db,
            {"query_type": "opportunity_search", "filters": {"stage": legacy_stage_filter}, "limit": 10},
            temp_root / "query-legacy-stage",
            render_html=False,
        )
        if first_result["storage_result"]["opportunity_id"] not in {item.get("id") for item in legacy_stage_query.get("opportunities", [])}:
            fail(f"legacy stage filter did not match canonical stored opportunity: {legacy_stage_query}")
        detail_result = run_detail(first_db, first_result["storage_result"]["opportunity_id"], temp_root / "detail")
        if "detail" not in detail_result or "display_result" not in detail_result:
            fail("detail result is incomplete")
        detail_opportunity = detail_result["detail"].get("opportunity", {})
        if detail_opportunity.get("stage_id") != source_opportunity.get("stage_id"):
            fail(f"detail result did not reload persisted stage_id: {detail_opportunity}")
        if detail_opportunity.get("stage_reason") != source_opportunity.get("stage_reason"):
            fail(f"detail result did not reload persisted stage_reason: {detail_opportunity}")
        if detail_opportunity.get("opportunity_confirmed") != source_opportunity.get("opportunity_confirmed"):
            fail(f"detail result did not reload persisted opportunity_confirmed: {detail_opportunity}")

        check_legacy_stage_storage_compatibility(temp_root)

        source_image = temp_root / "source-material.png"
        write_tiny_png(source_image)
        archive_result = run_analyze(
            {
                "account_hint": "归档测试有限公司",
                "analysis_goal": "验证原始材料归档",
                "materials": [
                    {
                        "type": "image_ocr",
                        "name": "现场白板照片",
                        "file_path": str(source_image),
                        "content": "客户：归档测试有限公司\n项目：质量检测自动化升级\n王总（客户-生产负责人）提出需求，李经理（客户-项目负责人）负责推进。\n需求：保留原始照片并展示缩略图。",
                        "confidence": 0.9,
                    }
                ],
                "sales_confirmation_answers": [
                    {
                        "dimension_id": "customer_purchase_intent",
                        "rating": "strong",
                        "answer_text": "客户已立项，计划在本季度完成方案评审并进入采购流程。",
                        "answered_by": "商务负责人"
                    },
                    {
                        "dimension_id": "competitors",
                        "rating": "medium",
                        "answer_text": "已知有两家竞争对手，但客户认为我方方案更贴近现场节拍要求。",
                        "answered_by": "商务负责人"
                    }
                ],
            },
            temp_root / "archive" / "opportunity.db",
            temp_root / "archive" / "outputs",
            template_id="opportunity_detail",
        )
        archived_files = archive_result["structured_data"].get("archived_files", [])
        if not archived_files:
            fail("archive case did not record archived_files")
        archived_path = Path(archived_files[0]["archived_path"])
        if not archived_path.exists():
            fail("archive case did not copy source file")
        html = archive_result["display_result"]["html"]
        if "ql-material-card" not in html or "attachments/" not in html:
            fail("archive case did not render material gallery")
        if "决策链识别" not in html:
            fail("archive case did not render decision chain")
        roles = {node.get("decision_role"): node.get("person_name") for node in archive_result["structured_data"].get("decision_chain", [])}
        if roles.get("业务需求负责人") != "王总":
            fail("archive case did not identify customer requirement owner")
        if roles.get("项目推进负责人") != "李经理":
            fail("archive case did not identify customer project owner")
        archive_opportunity = archive_result["structured_data"].get("opportunity", {})
        if archive_opportunity.get("stage_id") not in {"opportunity_confirmed", "solution_cocreation", "budget_project_confirmed"}:
            fail(f"archive case stage_id did not reflect confirmed opportunity flow: {archive_opportunity}")
        if not archive_opportunity.get("opportunity_confirmed"):
            fail("archive case should be marked as confirmed opportunity")
        assessment = archive_result["structured_data"].get("commercial_assessment", {})
        if not assessment.get("questions"):
            fail("archive case did not generate sales confirmation questions")
        dimensions = {item.get("dimension_id"): item for item in assessment.get("dimensions", [])}
        if dimensions.get("customer_purchase_intent", {}).get("evidence_status") != "sales_confirmed":
            fail("archive case did not apply sales confirmation answer")
        if "商务确认评估" not in html or "待商务确认问题" in html:
            fail("archive case commercial assessment section is missing or still renders confirmation-question panel")
        if "ql-radar-chart" not in html or "维度评分雷达" not in html:
            fail("archive case did not render assessment radar chart")
        if "ql-radar-panel" not in html or "竞争对手" not in html:
            fail("archive case did not render dimension-level radar panels")
        if "ql-confirmation-card" in html or "回答格式" in html:
            fail("archive case should not render sales confirmation cards")
        print("ok evaluation cases")
        if keep_artifacts:
            print(f"artifacts kept at {temp_root}")
            temp_root = None
    finally:
        if temp_root is not None:
            shutil.rmtree(temp_root, ignore_errors=True)


def check_distribution_noise() -> None:
    noisy = []
    for pattern in [".skill_data", "outputs", "src/*.egg-info", "**/__pycache__", "**/*.pyc"]:
        noisy.extend(ROOT.glob(pattern))
    noisy = [p for p in noisy if p.exists()]
    if noisy:
        rel = ", ".join(str(p.relative_to(ROOT)) for p in noisy[:8])
        fail(f"runtime artifacts should not be in the skill package: {rel}")
    print("ok distribution noise")


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate the Opportunity Analysis capability package")
    parser.add_argument("--keep-artifacts", action="store_true", help="Keep temporary validation outputs for inspection")
    args = parser.parse_args()
    clean_local_runtime_artifacts()
    check_json_files()
    check_python_compile()
    check_template_safety()
    check_stage_modules()
    check_stage_management()
    check_confirmation_loop()
    check_evaluation_cases(keep_artifacts=args.keep_artifacts)
    check_distribution_noise()
    print("validation passed")


if __name__ == "__main__":
    main()
