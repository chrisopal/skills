"""Print the deck dashboard from job artifacts.

Joins outline.json, slide_prompts.json, slide_specs.json, image_manifest.json
(when present), and lint_report.json (latest if multiple) into the table from
design §5:

    Page  Outline           Intent             Image                Lint
    ────  ────────────────  ─────────────────  ──────────────────   ──────
    01    locked            locked             fully_generated      pass
    ...

Usage:
    python scripts/dashboard.py path/to/job.json
    python scripts/dashboard.py path/to/job.json --json   # machine-readable

The job.json itself is read only to discover the artifacts directory
(`output.directory` field); per-artifact paths can also be passed
explicitly via flags.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from collections import Counter
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parent.parent


def _load_local(name: str, rel_path: str):
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, SKILL_ROOT / rel_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


page_state = _load_local("page_state", "scripts/lib/page_state.py")


def _read_optional(path: Path | None) -> dict | None:
    if path is None or not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _resolve_artifacts_dir(job_path: Path) -> Path:
    if not job_path.exists():
        return job_path.parent
    job = json.loads(job_path.read_text(encoding="utf-8"))
    out_dir = (job.get("output") or {}).get("directory")
    if out_dir:
        return (job_path.parent / out_dir).resolve()
    return (job_path.parent / "artifacts").resolve()


def build_dashboard(
    *,
    outline: dict | None,
    slide_prompts: dict | None,
    slide_specs: dict | None,
    lint_report: dict | None,
) -> dict:
    machine = page_state.PageStateMachine(
        outline=outline, slide_prompts=slide_prompts, slide_specs=slide_specs,
    )
    rows = []
    for page_no in machine.page_numbers():
        layer_status = machine.status_for(page_no)
        lint_entries = []
        if lint_report:
            lint_entries = [
                e for e in lint_report.get("results", []) if e.get("page_no") == page_no
            ]
        severities = [e.get("severity") for e in lint_entries]
        lint_summary = "pass"
        if "fail" in severities:
            lint_summary = f"fail x{severities.count('fail')}"
        elif "warn" in severities:
            lint_summary = f"warn x{severities.count('warn')}"
        rows.append({
            "page_no": page_no,
            "outline_status": layer_status["outline_status"],
            "intent_status": layer_status["intent_status"],
            "image_status": layer_status["image_status"],
            "lint": lint_summary,
        })

    deck_summary = _deck_summary(rows, lint_report)
    return {"rows": rows, "deck_summary": deck_summary}


def _deck_summary(rows: list[dict], lint_report: dict | None) -> dict:
    total_pages = len(rows)
    locked = sum(1 for r in rows if r["intent_status"] == "locked")
    summary: dict = {
        "total_pages": total_pages,
        "locked_intent": locked,
        "needs_rework": sum(1 for r in rows if "needs_rework" in (r["outline_status"], r["intent_status"])),
        "ready_for_render": all(r["intent_status"] == "locked" for r in rows) and total_pages > 0,
    }
    if lint_report:
        deck_level = lint_report.get("deck_level") or []
        per_category = Counter(e.get("category") for e in deck_level)
        summary["deck_lint"] = {
            "fail": sum(1 for e in deck_level if e.get("severity") == "fail"),
            "warn": sum(1 for e in deck_level if e.get("severity") == "warn"),
            "categories": dict(per_category),
        }
    return summary


def format_table(dashboard: dict) -> str:
    rows = dashboard["rows"]
    header = (
        f"{'Page':>4}  {'Outline':<16}  {'Intent':<17}  {'Image':<20}  {'Lint':<10}"
    )
    sep = "─" * 4 + "  " + "─" * 16 + "  " + "─" * 17 + "  " + "─" * 20 + "  " + "─" * 10
    lines = [header, sep]
    for row in rows:
        lines.append(
            f"{row['page_no']:>4}  "
            f"{row['outline_status']:<16}  "
            f"{row['intent_status']:<17}  "
            f"{row['image_status']:<20}  "
            f"{row['lint']:<10}"
        )
    summary = dashboard["deck_summary"]
    lines.append("")
    lines.append(
        f"deck: {summary['total_pages']} page(s), "
        f"{summary['locked_intent']} locked, "
        f"{summary['needs_rework']} needs_rework, "
        f"ready_for_render={summary['ready_for_render']}"
    )
    if "deck_lint" in summary:
        deck = summary["deck_lint"]
        lines.append(
            f"deck lint: fail={deck['fail']} warn={deck['warn']} "
            f"categories={deck['categories']}"
        )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Print PPT job dashboard.")
    parser.add_argument("job", nargs="?", type=Path, help="Path to job.json (auto-resolves artifact paths)")
    parser.add_argument("--outline", type=Path)
    parser.add_argument("--slide-prompts", type=Path)
    parser.add_argument("--slide-specs", type=Path)
    parser.add_argument("--lint-report", type=Path)
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON")
    args = parser.parse_args(argv)

    artifacts_dir = _resolve_artifacts_dir(args.job) if args.job else None
    if artifacts_dir:
        outline_path = args.outline or artifacts_dir / "outline.json"
        prompts_path = args.slide_prompts or artifacts_dir / "slide_prompts.json"
        specs_path = args.slide_specs or artifacts_dir / "slide_specs.json"
        lint_path = args.lint_report or artifacts_dir / "lint_report.json"
    else:
        outline_path = args.outline
        prompts_path = args.slide_prompts
        specs_path = args.slide_specs
        lint_path = args.lint_report

    dashboard = build_dashboard(
        outline=_read_optional(outline_path),
        slide_prompts=_read_optional(prompts_path),
        slide_specs=_read_optional(specs_path),
        lint_report=_read_optional(lint_path),
    )

    if args.json:
        print(json.dumps(dashboard, ensure_ascii=False, indent=2))
    else:
        print(format_table(dashboard))
    return 0


if __name__ == "__main__":
    sys.exit(main())
