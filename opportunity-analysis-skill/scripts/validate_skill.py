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
    for key in ["account", "contacts", "opportunity", "risks", "next_actions", "evidence", "missing_information", "evidence_map"]:
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
    check_json_files()
    check_python_compile()
    check_template_safety()
    check_evaluation_cases(keep_artifacts=args.keep_artifacts)
    check_distribution_noise()
    print("validation passed")


if __name__ == "__main__":
    main()
