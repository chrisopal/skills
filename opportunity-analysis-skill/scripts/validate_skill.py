#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import py_compile
import re
import shutil
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.dont_write_bytecode = True
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from opportunity_skill.pipeline import run_analyze, run_detail, run_query  # noqa: E402


def fail(message: str) -> None:
    raise SystemExit(f"VALIDATION FAILED: {message}")


def load_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        fail(f"{path.relative_to(ROOT)} is not valid JSON: {exc}")


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


def assert_output_contract(result: dict, source: str) -> None:
    for key in ["human_summary", "structured_data", "storage_result", "display_result"]:
        if key not in result:
            fail(f"{source} missing top-level key {key}")
    structured = result["structured_data"]
    for key in ["account", "contacts", "opportunity", "risks", "next_actions", "decision_chain", "evidence", "missing_information", "evidence_map"]:
        if key not in structured:
            fail(f"{source} missing structured_data.{key}")
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
            if opportunity["stage"] != case["expected_stage"]:
                fail(f"{case['name']} stage {opportunity['stage']} != {case['expected_stage']}")
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
        detail_result = run_detail(first_db, first_result["storage_result"]["opportunity_id"], temp_root / "detail")
        if "detail" not in detail_result or "display_result" not in detail_result:
            fail("detail result is incomplete")

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
    check_evaluation_cases(keep_artifacts=args.keep_artifacts)
    check_distribution_noise()
    print("validation passed")


if __name__ == "__main__":
    main()
