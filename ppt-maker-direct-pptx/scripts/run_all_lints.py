"""Lint orchestrator: runs the gate-appropriate lint passes and emits lint_report.json.

Gate map (per design §6):

  gate_4  → schema lint over outline + page_count match
  gate_5  → schema lint over slide_prompts + content quality (LLM optional)
  gate_7  → schema lint over slide_specs + geometry + style consistency

The orchestrator:

  1. Loads requested artifacts.
  2. Runs the appropriate lint scripts.
  3. Writes a unified lint_report.json that validates against
     `assets/schemas/lint_report.schema.json`.
  4. Exits 0 (no warns/fails), 1 (warn-only), or 2 (any fails).
  5. When --update-state is passed, flips each fail-tagged page's
     intent_status (or outline_status) to "needs_rework" so the page
     state machine routes the user back through that page.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

SKILL_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_REPORT_PATH = SKILL_ROOT / "artifacts" / "lint_report.json"


def _load_local(name: str, rel_path: str):
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, SKILL_ROOT / rel_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


lint_common = _load_local("lint_common", "scripts/lib/lint_common.py")
lint_schema = _load_local("lint_schema", "scripts/lint_schema.py")
lint_geometry = _load_local("lint_geometry", "scripts/lint_geometry.py")
lint_style = _load_local("lint_style", "scripts/lint_style.py")
lint_content = _load_local("lint_content", "scripts/lint_content.py")


GATES = ("gate_4", "gate_5", "gate_7")


def _now_iso() -> str:
    return datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read(path: Path | None) -> dict | None:
    if path is None:
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def run(
    *,
    gate: str,
    outline: dict | None = None,
    slide_prompts: dict | None = None,
    slide_specs: dict | None = None,
    master_style: dict | None = None,
    requirement: dict | None = None,
    audience: str | None = None,
    content_caller: Callable | None = None,
) -> dict:
    if gate not in GATES:
        raise ValueError(f"unknown gate: {gate!r}, must be one of {GATES}")

    expected_page_count = None
    if requirement:
        expected_page_count = requirement.get("page_count")
    if not audience and requirement:
        audience = requirement.get("target_audience") or requirement.get("audience")

    results: list = []

    if gate == "gate_4":
        results.extend(lint_schema.lint_artifacts(
            outline=outline,
            expected_page_count=expected_page_count,
        ))
    elif gate == "gate_5":
        results.extend(lint_schema.lint_artifacts(slide_prompts=slide_prompts))
        if slide_prompts is not None:
            results.extend(lint_content.lint_content(
                slide_prompts,
                audience=audience,
                model_caller=content_caller,
            ))
    elif gate == "gate_7":
        results.extend(lint_schema.lint_artifacts(
            outline=outline,
            slide_prompts=slide_prompts,
            slide_specs=slide_specs,
            expected_page_count=expected_page_count,
        ))
        if slide_specs is not None:
            results.extend(lint_geometry.lint_geometry(
                slide_specs, master_style=master_style,
            ))
            results.extend(lint_style.lint_style(
                slide_specs, master_style=master_style,
            ))

    per_page, deck = lint_common.split_results(results)
    return {
        "ts": _now_iso(),
        "gate": gate,
        "results": [r.to_result_dict() for r in per_page],
        "deck_level": [r.to_deck_dict() for r in deck],
    }


def update_page_state(
    *,
    report: dict,
    outline_path: Path | None,
    slide_prompts_path: Path | None,
) -> int:
    """Flip outline_status / intent_status to needs_rework on every page that
    has a fail in the report. Returns the number of state mutations made.
    """

    fail_pages: set[int] = {
        r["page_no"] for r in report.get("results", [])
        if r.get("severity") == "fail" and isinstance(r.get("page_no"), int)
    }
    mutations = 0

    if fail_pages and slide_prompts_path and slide_prompts_path.exists():
        data = json.loads(slide_prompts_path.read_text(encoding="utf-8"))
        for slide in data.get("slides", []):
            if slide.get("page_no") in fail_pages and slide.get("intent_status") != "needs_rework":
                slide["intent_status"] = "needs_rework"
                mutations += 1
        slide_prompts_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if fail_pages and outline_path and outline_path.exists():
        data = json.loads(outline_path.read_text(encoding="utf-8"))
        for slide in data.get("slides", []):
            if slide.get("page_no") in fail_pages and slide.get("outline_status") != "needs_rework":
                slide["outline_status"] = "needs_rework"
                mutations += 1
        outline_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    return mutations


def report_exit_code(report: dict) -> int:
    has_fail = any(r["severity"] == "fail" for r in report.get("results", []))
    has_fail = has_fail or any(r["severity"] == "fail" for r in report.get("deck_level", []))
    if has_fail:
        return 2
    has_warn = any(r["severity"] == "warn" for r in report.get("results", []))
    has_warn = has_warn or any(r["severity"] == "warn" for r in report.get("deck_level", []))
    return 1 if has_warn else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run lint pipeline for a given gate.")
    parser.add_argument("--gate", required=True, choices=GATES)
    parser.add_argument("--outline", type=Path)
    parser.add_argument("--slide-prompts", type=Path)
    parser.add_argument("--slide-specs", type=Path)
    parser.add_argument("--master-style", type=Path)
    parser.add_argument("--requirement", type=Path)
    parser.add_argument("--audience", type=str)
    parser.add_argument("--out", type=Path, default=DEFAULT_REPORT_PATH)
    parser.add_argument("--update-state", action="store_true",
                        help="Flip fail-tagged pages to needs_rework in their artifacts")
    parser.add_argument("--skip-content-judge", action="store_true")
    args = parser.parse_args(argv)

    requirement = _read(args.requirement)
    content_caller = None
    if not args.skip_content_judge and (args.audience or (requirement and (
        requirement.get("target_audience") or requirement.get("audience")
    ))):
        try:
            from style_from_nl import _default_caller_from_env  # type: ignore
            content_caller = _default_caller_from_env()
        except Exception:
            content_caller = None  # offline mode silently disables LLM judge

    report = run(
        gate=args.gate,
        outline=_read(args.outline),
        slide_prompts=_read(args.slide_prompts),
        slide_specs=_read(args.slide_specs),
        master_style=_read(args.master_style),
        requirement=requirement,
        audience=args.audience,
        content_caller=content_caller,
    )

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if args.update_state:
        mutated = update_page_state(
            report=report,
            outline_path=args.outline,
            slide_prompts_path=args.slide_prompts,
        )
        if mutated:
            print(f"flipped {mutated} page status field(s) to needs_rework")

    exit_code = report_exit_code(report)
    print(
        f"gate={args.gate} fails={sum(1 for r in report['results'] + report['deck_level'] if r['severity'] == 'fail')} "
        f"warns={sum(1 for r in report['results'] + report['deck_level'] if r['severity'] == 'warn')} "
        f"-> exit {exit_code}"
    )
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
