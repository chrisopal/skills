from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path
from .confirmation import collect_sales_confirmation_answers
from .extractor import analyze
from .pipeline import run_analyze, run_query, run_detail, run_manage
from .storage import OpportunitySQLiteAdapter
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

    for target in (p_analyze, p_query, p_detail):
        target.add_argument('--theme', choices=['light', 'dark'], default='light')
    p_query.add_argument('--template', default='opportunity_list')
    p_query.add_argument('--current-stage', help='Confirmed lifecycle stage ID (legacy --stage filters suggestions)')
    p_query.add_argument('--status', choices=['active', 'paused', 'won', 'lost', 'cancelled'])
    p_manage = sub.add_parser('manage', help='Apply an atomic, evidence-backed lifecycle change')
    p_manage.add_argument('--input', required=True, help='JSON change envelope')
    p_manage.add_argument('--db')
    p_lifecycle = sub.add_parser('lifecycle', help='Read confirmed lifecycle and next action as JSON')
    p_lifecycle.add_argument('--opportunity-id', required=True)
    p_lifecycle.add_argument('--db')

    p_serve = sub.add_parser('serve', help='Open the loopback editing workbench')
    p_serve.add_argument('--db')
    p_serve.add_argument('--port', type=int, default=18768)
    p_export = sub.add_parser('presales-export', help='Export selected evidence and requirements to a new presales project')
    p_export.add_argument('--db')
    p_export.add_argument('--opportunity-id', required=True)
    p_export.add_argument('--project', required=True)
    p_export.add_argument('--project-id', required=True)
    p_export.add_argument('--evidence', action='append', required=True)
    p_export.add_argument('--requirements', required=True, help='JSON array of authored requirements')
    p_export.add_argument('--audience', required=True)
    p_export.add_argument('--purpose', choices=['internal-draft', 'customer-review'], default='internal-draft')
    p_export.add_argument('--runtime', help='Explicit trusted presales runtime.py path')
    p_receive = sub.add_parser('presales-receive', help='Register a reviewed actual presales PPT as a solution version')
    p_receive.add_argument('--db')
    for name in ('opportunity-id', 'project', 'delivery-id', 'artifact-id', 'request-id', 'actor'):
        p_receive.add_argument('--' + name, required=True)
    p_receive.add_argument('--version', type=int, required=True)
    p_receive.add_argument('--expected-revision', type=int, required=True)
    p_receive.add_argument('--document-id', default='solution')
    p_receive.add_argument('--runtime', help='Explicit trusted presales runtime.py path')

    for command, help_text in [('gtm-manage', 'Save GTM research, follow-up or explicit opportunity links'), ('gtm-brief', 'Prepare sourced research tasks from a product and ICP brief')]:
        target = sub.add_parser(command, help=help_text)
        target.add_argument('--input', required=True)
        target.add_argument('--db')
    p_gtm_query = sub.add_parser('gtm-query', help='Read GTM campaigns and actual follow-up analytics')
    p_gtm_query.add_argument('--db')
    p_gtm_query.add_argument('--campaign-id')
    p_gtm_query.add_argument('--as-of')

    args = parser.parse_args()
    db_path = args.db or str(default_db_path())

    if args.command in {'gtm-manage', 'gtm-brief', 'gtm-query'}:
        try:
            from .gtm import GTMStore, search_brief
            if args.command == 'gtm-brief':
                result = search_brief(json.loads(Path(args.input).read_text(encoding='utf-8')))
            else:
                store = GTMStore(db_path)
                try:
                    result = store.manage(json.loads(Path(args.input).read_text(encoding='utf-8'))) if args.command == 'gtm-manage' else store.detail(args.campaign_id, args.as_of) if args.campaign_id else store.campaigns()
                finally:
                    store.close()
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return
        except (ValueError, TypeError, KeyError) as exc:
            parser.exit(2, f"GTM请求失败：{exc}\n")

    if args.command == 'serve':
        from .workbench import serve
        serve(db_path, port=args.port)
        return
    if args.command == 'presales-export':
        from .presales_bridge import export_project
        result = export_project(db_path, args.opportunity_id, args.project, args.project_id,
            args.evidence, json.loads(Path(args.requirements).read_text(encoding='utf-8')),
            audience=args.audience, purpose=args.purpose, runtime_path=args.runtime)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return
    if args.command == 'presales-receive':
        from .presales_bridge import receive_delivery
        result = receive_delivery(db_path, args.opportunity_id, args.project, args.delivery_id,
            artifact_id=args.artifact_id, version=args.version, request_id=args.request_id,
            expected_revision=args.expected_revision, actor=args.actor, document_id=args.document_id,
            runtime_path=args.runtime)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

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
        result = run_analyze(input_data, db_path, args.output_dir, args.template, theme=args.theme)
        print(json.dumps({"human_summary": result["human_summary"], "storage_result": result["storage_result"], "display_result": {k: v for k, v in result["display_result"].items() if k != "html"}}, ensure_ascii=False, indent=2))

    elif args.command == "query":
        filters = {}
        if args.current_stage:
            filters['current_stage_id'] = args.current_stage
        if args.status:
            filters['status'] = args.status
        if args.stage:
            filters["stage"] = args.stage
        if args.risk_level:
            filters["risk_level"] = args.risk_level
        if args.min_score is not None:
            filters["min_score"] = args.min_score
        if args.company_name:
            filters["company_name"] = args.company_name
        query = {"query_type": "opportunity_search", "filters": filters, "sort": {"field": "score", "order": "desc"}, "limit": args.limit}
        result = run_query(db_path, query, args.output_dir, args.render_html, template_id=args.template, theme=args.theme)
        print(json.dumps({"count": result["count"], "opportunities": result["opportunities"]}, ensure_ascii=False, indent=2))

    elif args.command == "detail":
        result = run_detail(db_path, args.opportunity_id, args.output_dir, args.template, theme=args.theme)
        print(json.dumps({"opportunity_id": args.opportunity_id, "output_dir": args.output_dir}, ensure_ascii=False, indent=2))

    elif args.command == 'manage':
        change = json.loads(Path(args.input).read_text(encoding='utf-8'))
        print(json.dumps(run_manage(db_path, change), ensure_ascii=False, indent=2))

    elif args.command == 'lifecycle':
        adapter = OpportunitySQLiteAdapter(db_path)
        try:
            print(json.dumps({'opportunity_id': args.opportunity_id, 'lifecycle': adapter.get_lifecycle(args.opportunity_id)}, ensure_ascii=False, indent=2))
        finally:
            adapter.close()


if __name__ == "__main__":
    main()
