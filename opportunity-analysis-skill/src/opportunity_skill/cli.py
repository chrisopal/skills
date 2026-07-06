from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path
from .confirmation import collect_sales_confirmation_answers
from .extractor import analyze
from .pipeline import run_analyze, run_query, run_detail
from .utils import default_db_path


def _stderr_input(prompt: str) -> str:
    print(prompt, end="", file=sys.stderr, flush=True)
    return sys.stdin.readline()


def main():
    parser = argparse.ArgumentParser(description="Opportunity Analysis Skill CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    p_analyze = sub.add_parser("analyze", help="Analyze input evidence/materials, store to SQLite, render HTML")
    p_analyze.add_argument("--input", required=True, help="Input JSON file")
    p_analyze.add_argument("--db", default=None, help="SQLite db path. Defaults to $SKILL_DATA_DIR/opportunity-analysis/opportunity.db or .skill_data/opportunity-analysis/opportunity.db")
    p_analyze.add_argument("--output-dir", default="outputs/demo", help="Output directory")
    p_analyze.add_argument("--template", default="opportunity_card", help="Template id")
    p_analyze.add_argument("--interactive-confirmation", action="store_true", help="Ask business staff to answer uncertain sales confirmation questions before final scoring")
    p_analyze.add_argument("--confirmation-limit", type=int, default=None, help="Maximum number of confirmation questions to ask interactively")
    p_analyze.add_argument("--answered-by", default="商务负责人", help="Name recorded on interactive confirmation answers")

    p_query = sub.add_parser("query", help="Query opportunities")
    p_query.add_argument("--db", default=None, help="SQLite db path. Defaults to $SKILL_DATA_DIR/opportunity-analysis/opportunity.db or .skill_data/opportunity-analysis/opportunity.db")
    p_query.add_argument("--stage", default=None)
    p_query.add_argument("--risk-level", default=None)
    p_query.add_argument("--min-score", type=int, default=None)
    p_query.add_argument("--company-name", default=None)
    p_query.add_argument("--limit", type=int, default=50)
    p_query.add_argument("--render-html", action="store_true")
    p_query.add_argument("--output-dir", default="outputs/query")

    p_detail = sub.add_parser("detail", help="Render opportunity detail")
    p_detail.add_argument("--db", default=None, help="SQLite db path. Defaults to $SKILL_DATA_DIR/opportunity-analysis/opportunity.db or .skill_data/opportunity-analysis/opportunity.db")
    p_detail.add_argument("--opportunity-id", required=True)
    p_detail.add_argument("--template", default="opportunity_detail")
    p_detail.add_argument("--output-dir", default="outputs/detail")

    args = parser.parse_args()
    db_path = args.db or str(default_db_path())

    if args.command == "analyze":
        input_data = json.loads(Path(args.input).read_text(encoding="utf-8"))
        if args.interactive_confirmation:
            draft = analyze(input_data)
            questions = draft.get("structured_data", {}).get("sales_confirmation_questions", [])
            answers = collect_sales_confirmation_answers(
                questions,
                input_func=_stderr_input,
                output_func=lambda message: print(message, file=sys.stderr),
                answered_by=args.answered_by,
                limit=args.confirmation_limit,
            )
            if answers:
                input_data = dict(input_data)
                input_data["sales_confirmation_answers"] = list(input_data.get("sales_confirmation_answers", [])) + answers
        result = run_analyze(input_data, db_path, args.output_dir, args.template)
        print(json.dumps({"human_summary": result["human_summary"], "storage_result": result["storage_result"], "display_result": {k: v for k, v in result["display_result"].items() if k != "html"}}, ensure_ascii=False, indent=2))

    elif args.command == "query":
        filters = {}
        if args.stage:
            filters["stage"] = args.stage
        if args.risk_level:
            filters["risk_level"] = args.risk_level
        if args.min_score is not None:
            filters["min_score"] = args.min_score
        if args.company_name:
            filters["company_name"] = args.company_name
        query = {"query_type": "opportunity_search", "filters": filters, "sort": {"field": "score", "order": "desc"}, "limit": args.limit}
        result = run_query(db_path, query, args.output_dir, args.render_html)
        print(json.dumps({"count": result["count"], "opportunities": result["opportunities"]}, ensure_ascii=False, indent=2))

    elif args.command == "detail":
        result = run_detail(db_path, args.opportunity_id, args.output_dir, args.template)
        print(json.dumps({"opportunity_id": args.opportunity_id, "output_dir": args.output_dir}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
