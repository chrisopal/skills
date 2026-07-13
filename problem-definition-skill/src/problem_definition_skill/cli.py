from __future__ import annotations
import argparse
from html import escape
import json
import os
from pathlib import Path
from typing import Any
from jsonschema import Draft202012Validator
from .analyzer import analyze
from .repository import Repository
from .renderer import markdown, render

ROOT = Path(__file__).resolve().parents[2]


def validate_contract(instance: Any, schema_name: str, label: str) -> None:
    schema_path = ROOT / "schemas" / schema_name
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    errors = sorted(
        Draft202012Validator(schema).iter_errors(instance),
        key=lambda error: list(error.absolute_path),
    )
    if not errors:
        return
    error = errors[0]
    location = ".".join(str(part) for part in error.absolute_path) or "<root>"
    raise SystemExit(f"Invalid {label} at {location}: {error.message}")


def default_db_path() -> Path:
    base = os.environ.get("SKILL_DATA_DIR")
    if base:
        return Path(base) / "problem-definition" / "problem_definition.db"
    return Path.cwd() / ".skill_data" / "problem-definition" / "problem_definition.db"


def write_outputs(result: dict, out: Path, template_id: str) -> dict:
    out.mkdir(parents=True, exist_ok=True)
    html = render(result, str(ROOT / "display/templates"), template_id)
    md = markdown(result)
    html_path = out / f"{template_id}.html"
    markdown_path = out / "problem_definition.md"
    result_path = out / "result.json"
    html_path.write_text(html, encoding="utf-8")
    markdown_path.write_text(md, encoding="utf-8")
    result_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return {
        "template_id": template_id,
        "html": html,
        "markdown": md,
        "html_path": str(html_path),
        "markdown_path": str(markdown_path),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="problem-definition")
    sub = parser.add_subparsers(dest="cmd", required=True)

    analyze_parser = sub.add_parser("analyze")
    analyze_parser.add_argument("--input", required=True)
    analyze_parser.add_argument("--db")
    analyze_parser.add_argument("--output-dir", default="/tmp/problem-definition-demo")
    analyze_parser.add_argument("--template", default="problem_definition_card")

    query_parser = sub.add_parser("query")
    query_parser.add_argument("--db")
    query_parser.add_argument("--keyword")
    query_parser.add_argument("--limit", type=int, default=20)
    query_parser.add_argument("--render-html", action="store_true")
    query_parser.add_argument("--output-dir", default="/tmp/problem-definition-query")

    detail_parser = sub.add_parser("detail")
    detail_parser.add_argument("--problem-definition-id", required=True)
    detail_parser.add_argument("--db")
    detail_parser.add_argument("--template", default="problem_definition_card")
    detail_parser.add_argument("--output-dir", default="/tmp/problem-definition-detail")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    db_path = Path(args.db) if args.db else default_db_path()
    repo = Repository(str(db_path), str(ROOT / "storage/sqlite/schema.sql"))

    if args.cmd == "analyze":
        payload = json.loads(Path(args.input).read_text(encoding="utf-8"))
        validate_contract(payload, "input.schema.json", "analyze input")
        result = analyze(payload)
        validate_contract(result, "output.schema.json", "analysis output")
        problem_definition_id = repo.save(result)
        output_dir = Path(args.output_dir)
        display_result = write_outputs(result, output_dir, args.template)
        envelope = {
            **result,
            "storage_result": {
                "adapter": "sqlite", "saved": True, "problem_definition_id": problem_definition_id,
                "db_path": str(db_path),
            },
            "display_result": display_result,
        }
        (output_dir / "result.json").write_text(json.dumps(envelope, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(envelope, ensure_ascii=False))
        return

    if args.cmd == "query":
        validate_contract(
            {"keyword": args.keyword, "limit": args.limit},
            "query.schema.json",
            "query",
        )
        rows = repo.query(args.keyword, args.limit)
        out = Path(args.output_dir)
        out.mkdir(parents=True, exist_ok=True)
        (out / "query_result.json").write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
        if args.render_html:
            cards = "\n".join(
                "<li><strong>{}</strong><br>{}</li>".format(
                    escape(str(row["case_name"])),
                    escape(str(row["decision_problem"])),
                )
                for row in rows
            )
            (out / "query_result.html").write_text(f"<!doctype html><meta charset='utf-8'><ul>{cards}</ul>", encoding="utf-8")
        print(json.dumps({"count": len(rows), "db_path": str(db_path)}, ensure_ascii=False))
        return

    result = repo.get_detail(args.problem_definition_id)
    if result is None:
        raise SystemExit(f"Problem definition not found: {args.problem_definition_id}")
    display_result = write_outputs(result, Path(args.output_dir), args.template)
    print(json.dumps({"problem_definition_id": args.problem_definition_id, **display_result}, ensure_ascii=False))


if __name__ == "__main__":
    main()
