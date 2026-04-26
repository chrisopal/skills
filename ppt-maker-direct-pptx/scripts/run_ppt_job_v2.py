"""Seven-gate orchestrator for the v2 direct-pptx flow.

This orchestrator does NOT subsume run_ppt_job.py — it composes the new
phase-3..6 helpers (style, catalog, wireframe, lint, state machine, dashboard)
into a single CLI for users (or smoke tests) who want to drive a job through
the new flow:

    1. requirement                   -- validate inputs + lock requirement
    2. style                         -- preset / nl / reference (Phase 3)
    3. style_preview (NEW)           -- pattern catalog render (Phase 4)
    4. outline                       -- outline lint + lock pages (Phases 5/6)
    5. intent                        -- intent lint + per-page wireframes
    6. image_plan (NEW)              -- mutate placeholder.status batch
    7. pre_render (NEW)              -- geometry + style lint, dashboard

`render` is the terminal step (run_ppt_job.py / assemble_pptx.py do the heavy
PPTX assembly; this file stops short of calling them so it stays unit-testable).

Usage:
    python scripts/run_ppt_job_v2.py path/to/job.json --gate gate_4
    python scripts/run_ppt_job_v2.py path/to/job.json --next      # auto-pick next gate
    python scripts/run_ppt_job_v2.py path/to/job.json --auto-approve   # walk to end

State is persisted in job["v2_gates"][<gate>] = {"status": "pending|done|fail",
"summary": "...", "ts": "..."}.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SKILL_ROOT = Path(__file__).resolve().parent.parent

GATES = (
    "gate_1_requirement",
    "gate_2_style",
    "gate_3_style_preview",
    "gate_4_outline",
    "gate_5_intent",
    "gate_6_image_plan",
    "gate_7_pre_render",
)

REQUIRED_REQUIREMENT_FIELDS = (
    "topic",
    "target_audience",
    "purpose",
    "page_count",
    "key_points",
)


def _load_local(name: str, rel_path: str):
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, SKILL_ROOT / rel_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


run_all_lints = _load_local("run_all_lints", "scripts/run_all_lints.py")
render_pattern_catalog = _load_local("render_pattern_catalog", "scripts/render_pattern_catalog.py")
render_wireframe = _load_local("render_wireframe", "scripts/render_wireframe.py")
dashboard_mod = _load_local("dashboard", "scripts/dashboard.py")
page_state = _load_local("page_state", "scripts/lib/page_state.py")
style_inherit = _load_local("style_inherit", "scripts/lib/style_inherit.py")


def _now_iso() -> str:
    return datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _resolve_artifacts_dir(job_path: Path, job: dict) -> Path:
    out_dir = (job.get("output") or {}).get("directory")
    if out_dir:
        return (job_path.parent / out_dir).resolve()
    return (job_path.parent / "artifacts").resolve()


def _read(path: Path) -> dict | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


@dataclass
class GateOutcome:
    gate: str
    status: str  # "done" | "fail" | "pending"
    summary: str = ""
    detail: dict | None = None


# ---------------------------------------------------------------------------
# gate runners
# ---------------------------------------------------------------------------


def _gate_1_requirement(job: dict, *_args) -> GateOutcome:
    requirement = job.get("requirement") or job
    missing = [
        field for field in REQUIRED_REQUIREMENT_FIELDS
        if not requirement.get(field)
    ]
    if missing:
        return GateOutcome(
            gate="gate_1_requirement",
            status="fail",
            summary=f"missing required fields: {', '.join(missing)}",
        )
    return GateOutcome(
        gate="gate_1_requirement",
        status="done",
        summary="all 5 required fields present",
    )


def _gate_2_style(job: dict, artifacts_dir: Path, *_args) -> GateOutcome:
    """Either uses an existing artifacts/master_style.json or auto-applies a
    preset specified by job["template_id"] (or alias)."""

    master_style_path = artifacts_dir / "master_style.json"
    existing = _read(master_style_path)
    if existing and existing.get("template_id"):
        return GateOutcome(
            gate="gate_2_style",
            status="done",
            summary=f"using existing master_style template_id={existing['template_id']}",
        )
    template = job.get("template_id") or job.get("style") or job.get("template_name")
    if not template:
        return GateOutcome(
            gate="gate_2_style",
            status="fail",
            summary="no template_id/style/template_name on job and no master_style.json on disk",
        )
    try:
        master_style = style_inherit.inherit_preset(template)
    except style_inherit.UnknownPresetError as exc:
        return GateOutcome(gate="gate_2_style", status="fail", summary=str(exc))
    _write(master_style_path, master_style)
    return GateOutcome(
        gate="gate_2_style",
        status="done",
        summary=f"wrote master_style.json from preset {master_style['template_id']}",
    )


def _gate_3_style_preview(job: dict, artifacts_dir: Path, *_args) -> GateOutcome:
    master_style = _read(artifacts_dir / "master_style.json")
    if not master_style:
        return GateOutcome(gate="gate_3_style_preview", status="fail",
                           summary="master_style.json missing — run gate_2 first")
    target = render_pattern_catalog.render_catalog(
        master_style, out_dir=artifacts_dir / "pattern_catalog",
    )
    return GateOutcome(
        gate="gate_3_style_preview",
        status="done",
        summary=f"pattern catalog ready at {target}",
    )


def _gate_4_outline(job: dict, artifacts_dir: Path, *_args) -> GateOutcome:
    outline = _read(artifacts_dir / "outline.json")
    if not outline:
        return GateOutcome(gate="gate_4_outline", status="fail",
                           summary="outline.json missing")
    requirement = job.get("requirement") or job
    report = run_all_lints.run(
        gate="gate_4", outline=outline, requirement=requirement,
    )
    has_fail = any(r["severity"] == "fail" for r in report["results"] + report["deck_level"])
    return GateOutcome(
        gate="gate_4_outline",
        status="fail" if has_fail else "done",
        summary=f"schema lint: {len(report['results'])} per-page result(s)",
        detail=report,
    )


def _gate_5_intent(job: dict, artifacts_dir: Path, *_args) -> GateOutcome:
    slide_prompts = _read(artifacts_dir / "slide_prompts.json")
    if not slide_prompts:
        return GateOutcome(gate="gate_5_intent", status="fail",
                           summary="slide_prompts.json missing")
    report = run_all_lints.run(gate="gate_5", slide_prompts=slide_prompts)
    has_fail = any(r["severity"] == "fail" for r in report["results"] + report["deck_level"])
    # Render wireframes for each pattern-mode slide
    wireframes_dir = artifacts_dir / "wireframes"
    wireframes_dir.mkdir(parents=True, exist_ok=True)
    rendered = 0
    for slide in slide_prompts.get("slides", []):
        if not slide.get("pattern_id"):
            continue
        result = render_wireframe.render_wireframe(slide)
        if result.svg:
            (wireframes_dir / f"page-{slide['page_no']:02d}.svg").write_text(
                result.svg, encoding="utf-8",
            )
            rendered += 1
    return GateOutcome(
        gate="gate_5_intent",
        status="fail" if has_fail else "done",
        summary=f"intent lint + {rendered} wireframe(s)",
        detail=report,
    )


def _gate_6_image_plan(job: dict, artifacts_dir: Path, *_args) -> GateOutcome:
    slide_specs = _read(artifacts_dir / "slide_specs.json")
    if not slide_specs:
        return GateOutcome(gate="gate_6_image_plan", status="fail",
                           summary="slide_specs.json missing — build it before image plan")
    counts = {"pending": 0, "placeholder": 0, "skipped": 0, "generated": 0, "regenerating": 0}
    total = 0
    for slide in slide_specs.get("slides", []):
        for placeholder in slide.get("image_placeholders", []) or []:
            status = placeholder.get("status", "placeholder")
            counts[status] = counts.get(status, 0) + 1
            total += 1
    return GateOutcome(
        gate="gate_6_image_plan",
        status="done",
        summary=f"{total} placeholder(s) — counts={counts}",
        detail={"counts": counts},
    )


def _gate_7_pre_render(job: dict, artifacts_dir: Path, *_args) -> GateOutcome:
    outline = _read(artifacts_dir / "outline.json")
    slide_prompts = _read(artifacts_dir / "slide_prompts.json")
    slide_specs = _read(artifacts_dir / "slide_specs.json")
    master_style = _read(artifacts_dir / "master_style.json")
    if not slide_specs:
        return GateOutcome(gate="gate_7_pre_render", status="fail",
                           summary="slide_specs.json missing")
    report = run_all_lints.run(
        gate="gate_7",
        outline=outline,
        slide_prompts=slide_prompts,
        slide_specs=slide_specs,
        master_style=master_style,
    )
    _write(artifacts_dir / "lint_report.json", report)
    has_fail = any(r["severity"] == "fail" for r in report["results"] + report["deck_level"])
    db = dashboard_mod.build_dashboard(
        outline=outline, slide_prompts=slide_prompts,
        slide_specs=slide_specs, lint_report=report,
    )
    summary = (
        f"deck ready_for_render={db['deck_summary']['ready_for_render']}, "
        f"locked_intent={db['deck_summary']['locked_intent']}/"
        f"{db['deck_summary']['total_pages']}"
    )
    return GateOutcome(
        gate="gate_7_pre_render",
        status="fail" if has_fail else "done",
        summary=summary,
        detail={"dashboard": db, "lint": report},
    )


_RUNNERS = {
    "gate_1_requirement": _gate_1_requirement,
    "gate_2_style": _gate_2_style,
    "gate_3_style_preview": _gate_3_style_preview,
    "gate_4_outline": _gate_4_outline,
    "gate_5_intent": _gate_5_intent,
    "gate_6_image_plan": _gate_6_image_plan,
    "gate_7_pre_render": _gate_7_pre_render,
}


def next_gate(job: dict) -> str | None:
    history = job.get("v2_gates") or {}
    for gate in GATES:
        if history.get(gate, {}).get("status") != "done":
            return gate
    return None


def run_gate(gate: str, job: dict, job_path: Path) -> GateOutcome:
    if gate not in _RUNNERS:
        raise ValueError(f"unknown gate: {gate!r}")
    artifacts_dir = _resolve_artifacts_dir(job_path, job)
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    outcome = _RUNNERS[gate](job, artifacts_dir)
    history = job.setdefault("v2_gates", {})
    history[gate] = {
        "status": outcome.status,
        "summary": outcome.summary,
        "ts": _now_iso(),
    }
    _write(job_path, job)
    return outcome


def run_until_failure(job: dict, job_path: Path, *, target_gate: str | None = None) -> list[GateOutcome]:
    out: list[GateOutcome] = []
    for gate in GATES:
        if target_gate and gate != target_gate:
            if (job.get("v2_gates") or {}).get(gate, {}).get("status") == "done":
                continue
        outcome = run_gate(gate, job, job_path)
        out.append(outcome)
        if outcome.status == "fail":
            break
        if target_gate and gate == target_gate:
            break
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="7-gate v2 direct-pptx orchestrator.")
    parser.add_argument("job", type=Path)
    parser.add_argument("--gate", choices=GATES, help="Run only this gate")
    parser.add_argument("--next", action="store_true", help="Run the next pending gate")
    parser.add_argument("--auto-approve", action="store_true",
                        help="Walk through every remaining gate, stopping on the first fail")
    args = parser.parse_args(argv)

    job_path = args.job.expanduser().resolve()
    job = _read(job_path) or {}

    if args.gate:
        outcome = run_gate(args.gate, job, job_path)
        print(f"[{outcome.gate}] {outcome.status}: {outcome.summary}")
        return 0 if outcome.status == "done" else 2

    if args.auto_approve:
        outcomes = run_until_failure(job, job_path)
        for outcome in outcomes:
            print(f"[{outcome.gate}] {outcome.status}: {outcome.summary}")
        return 0 if outcomes and outcomes[-1].status == "done" else 2

    if args.next:
        gate = next_gate(job)
        if gate is None:
            print("all gates done")
            return 0
        outcome = run_gate(gate, job, job_path)
        print(f"[{outcome.gate}] {outcome.status}: {outcome.summary}")
        return 0 if outcome.status == "done" else 2

    parser.error("specify one of --gate, --next, or --auto-approve")
    return 1


if __name__ == "__main__":
    sys.exit(main())
