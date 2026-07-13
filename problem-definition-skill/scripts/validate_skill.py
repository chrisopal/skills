from __future__ import annotations
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]


def fail(message: str) -> None:
    raise SystemExit(f"VALIDATION FAILED: {message}")


def validate_json() -> None:
    for path in ROOT.rglob("*.json"):
        try:
            json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            fail(f"invalid JSON {path.relative_to(ROOT)}: {exc}")


def validate_python() -> None:
    for path in ROOT.rglob("*.py"):
        if any(part in {".venv", "__pycache__"} for part in path.parts):
            continue
        try:
            compile(path.read_text(encoding="utf-8"), str(path), "exec")
        except (SyntaxError, UnicodeDecodeError) as exc:
            fail(f"invalid Python {path.relative_to(ROOT)}: {exc}")


def validate_templates() -> None:
    forbidden = [r"<script\b", r"\son\w+\s*=", r"javascript:"]
    for path in (ROOT / "display/templates").glob("*.html"):
        text = path.read_text(encoding="utf-8").lower()
        for pattern in forbidden:
            if re.search(pattern, text):
                fail(f"unsafe template content in {path.name}: {pattern}")


def validate_distribution() -> None:
    forbidden_names = {"outputs", ".skill_data", "__pycache__"}
    for path in ROOT.rglob("*"):
        if any(part in forbidden_names for part in path.parts):
            fail(f"distribution artifact found: {path.relative_to(ROOT)}")
        if path.suffix in {".pyc", ".db"} or path.name.endswith(".egg-info"):
            fail(f"distribution artifact found: {path.relative_to(ROOT)}")


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_schema(instance: Any, schema_name: str, label: str) -> None:
    schema_path = ROOT / "schemas" / schema_name
    errors = sorted(
        Draft202012Validator(load_json(schema_path)).iter_errors(instance),
        key=lambda error: list(error.absolute_path),
    )
    if not errors:
        return
    error = errors[0]
    location = ".".join(str(part) for part in error.absolute_path) or "<root>"
    fail(f"{label} does not match {schema_name} at {location}: {error.message}")


def run_command(command: list[str], env: dict[str, str], label: str) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(command, cwd=ROOT, env=env, text=True, capture_output=True)
    if result.returncode != 0:
        fail(f"{label} failed: {result.stderr.strip()}")
    return result


def parse_stdout(result: subprocess.CompletedProcess[str], label: str) -> dict[str, Any]:
    try:
        return json.loads(result.stdout.strip().splitlines()[-1])
    except (IndexError, json.JSONDecodeError) as exc:
        fail(f"{label} did not return JSON: {exc}")


def run_runtime() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        db = tmp_path / "problem.db"
        out = tmp_path / "out"
        env = os.environ.copy()
        env["PYTHONPATH"] = str(ROOT / "src")
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        test_cases = load_json(ROOT / "evaluation/test_cases.json")
        if not isinstance(test_cases, list) or not test_cases:
            fail("evaluation/test_cases.json must contain at least one test case")
        test_case = test_cases[0]
        input_path = ROOT / test_case["input"]
        input_payload = load_json(input_path)
        validate_schema(input_payload, "input.schema.json", "example input")
        analyze_cmd = [
            sys.executable, "-m", "problem_definition_skill.cli", "analyze",
            "--input", str(input_path),
            "--db", str(db), "--output-dir", str(out),
        ]
        payload = parse_stdout(run_command(analyze_cmd, env, "analyze runtime"), "analyze runtime")
        validate_schema(payload, "output.schema.json", "analyze output")
        for required in ("storage_result", "display_result"):
            if required not in payload:
                fail(f"analyze output missing {required}")
        problem_definition = payload["structured_data"]["problem_definition"]
        for field in test_case.get("expected", []):
            container = payload["structured_data"] if field == "clarification_questions" else problem_definition
            if field not in container:
                fail(f"evaluation case {test_case.get('name', '<unnamed>')} missing {field}")
        problem_id = payload["storage_result"]["problem_definition_id"]
        for required in (out / "result.json", out / "problem_definition_card.html", out / "problem_definition.md"):
            if not required.exists():
                fail(f"missing runtime output: {required.name}")
        if load_json(out / "result.json") != payload:
            fail("analyze stdout does not match result.json")

        query = run_command([
            sys.executable, "-m", "problem_definition_skill.cli", "query", "--db", str(db),
            "--keyword", "质检", "--render-html", "--output-dir", str(tmp_path / "query")
        ], env, "query runtime")
        if parse_stdout(query, "query runtime").get("count") != 1:
            fail("query runtime returned an unexpected number of rows")
        for required in (tmp_path / "query" / "query_result.json", tmp_path / "query" / "query_result.html"):
            if not required.exists():
                fail(f"missing query output: {required.name}")

        for template in sorted((ROOT / "display/templates").glob("*.html")):
            output_dir = tmp_path / template.stem
            detail = run_command([
                sys.executable, "-m", "problem_definition_skill.cli", "detail", "--db", str(db),
                "--problem-definition-id", problem_id, "--template", template.stem,
                "--output-dir", str(output_dir),
            ], env, f"detail runtime for {template.name}")
            detail_payload = parse_stdout(detail, f"detail runtime for {template.name}")
            if detail_payload.get("template_id") != template.stem:
                fail(f"detail runtime rendered the wrong template for {template.name}")
            if not (output_dir / template.name).exists():
                fail(f"missing detail output: {template.name}")

        unsafe_name = '<img src=x onerror="alert(1)">'
        unsafe_input = tmp_path / "unsafe_input.json"
        unsafe_input.write_text(json.dumps({"case_name": unsafe_name, "text": "需要质检改造"}), encoding="utf-8")
        unsafe_db = tmp_path / "unsafe.db"
        run_command([
            sys.executable, "-m", "problem_definition_skill.cli", "analyze", "--input", str(unsafe_input),
            "--db", str(unsafe_db), "--output-dir", str(tmp_path / "unsafe-analyze"),
        ], env, "unsafe analyze runtime")
        unsafe_query_dir = tmp_path / "unsafe-query"
        run_command([
            sys.executable, "-m", "problem_definition_skill.cli", "query", "--db", str(unsafe_db),
            "--render-html", "--output-dir", str(unsafe_query_dir),
        ], env, "unsafe query runtime")
        unsafe_html = (unsafe_query_dir / "query_result.html").read_text(encoding="utf-8")
        if unsafe_name in unsafe_html or "&lt;img src=x onerror=&quot;alert(1)&quot;&gt;" not in unsafe_html:
            fail("query HTML did not escape user-controlled values")

        invalid_input = tmp_path / "invalid_input.json"
        invalid_input.write_text(json.dumps({"case_name": "missing evidence"}), encoding="utf-8")
        invalid = subprocess.run([
            sys.executable, "-m", "problem_definition_skill.cli", "analyze", "--input", str(invalid_input),
            "--db", str(tmp_path / "invalid.db"), "--output-dir", str(tmp_path / "invalid-output"),
        ], cwd=ROOT, env=env, text=True, capture_output=True)
        if invalid.returncode == 0 or "Invalid analyze input" not in invalid.stderr:
            fail("analyze accepted an input that violates input.schema.json")


def main() -> None:
    validate_json()
    validate_distribution()
    validate_python()
    validate_templates()
    run_runtime()
    print("VALIDATION PASSED")


if __name__ == "__main__":
    main()
