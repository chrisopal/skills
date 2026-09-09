#!/usr/bin/env python3
"""Prepare Huixin themes and run bounded, fail-closed delivery commands.

See workflows/profiles/huixin-generate.md. No model calls or dependency installs.
"""

from __future__ import annotations

import argparse
import contextlib
import importlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

from attribution_guard import require_skill_integrity

SKILL_DIR = Path(__file__).resolve().parents[1]
SCRIPTS = SKILL_DIR / "scripts"
BASE_MODULES = {
    "yaml": "PyYAML>=6.0.1", "pptx": "python-pptx>=0.6.21",
    "xlsxwriter": "XlsxWriter>=3.0.0", "PIL": "Pillow>=9.0.0",
    "lxml.etree": "lxml>=4.9.0",
}


def emit(**result: object) -> None:
    print(json.dumps(result, ensure_ascii=False))


def preflight() -> int:
    missing = []
    for module, requirement in BASE_MODULES.items():
        try:
            importlib.import_module(module)
        except ImportError:
            missing.append(requirement)
    compatible = sys.version_info >= (3, 10)
    emit(status="ok" if compatible and not missing else "failed",
         python=sys.executable, python_supported=compatible,
         missing_requirements=missing,
         fix="Use Python 3.10+ and its -m pip install -r requirements-core.txt"
         if missing or not compatible else None)
    return int(bool(missing) or not compatible)


def prepare(args: argparse.Namespace) -> int:
    from project_manager import ProjectManager

    index = json.loads((SKILL_DIR / "templates/decks/decks_index.json").read_text("utf-8"))
    if args.deck not in index or not args.deck.startswith("huixin_"):
        raise ValueError("Select a registered huixin_* deck id; do not pass a filesystem path")
    source = SKILL_DIR / "templates/decks" / args.deck
    spec = source / "design_spec.md"
    if not spec.is_file():
        raise ValueError(f"Missing template spec: {spec}")
    base = Path(args.base_dir).expanduser().resolve()
    if base == SKILL_DIR or SKILL_DIR in base.parents:
        raise ValueError("Use an output directory outside the installed Skill")
    # ProjectManager owns naming, fresh-directory checks and operational logging.
    with contextlib.redirect_stdout(sys.stderr):
        project = Path(ProjectManager().init_project(
            args.name, canvas_format=index[args.deck]["canvas_format"],
            base_dir=str(base), quick_generate=True,
        ))
    templates = project / "templates"
    templates.mkdir()
    shutil.copy2(spec, templates / "design_spec.md")
    for svg in sorted(source.glob("*.svg")):
        shutil.copy2(svg, templates / svg.name)
    for folder in ("images", "icons"):
        if (source / folder).is_dir():
            shutil.copytree(source / folder, project / folder)
    emit(status="ok", project=str(project), deck=args.deck,
         spec=str(templates / "design_spec.md"),
         prototypes=[p.name for p in sorted(templates.glob("*.svg"))])
    return 0


def run_logged(project: Path, stage: str, command: list[str]) -> bool:
    log = project / "validation" / f"huixin_{stage}.log"
    log.parent.mkdir(exist_ok=True)
    with log.open("w", encoding="utf-8") as output:
        result = subprocess.run(command, stdout=output, stderr=subprocess.STDOUT,
                                cwd=project, check=False)
    if result.returncode:
        # Return the relevant tail only; full diagnostics stay outside model context.
        lines = log.read_text("utf-8", errors="replace").splitlines()
        emit(status="failed", stage=stage, exit_code=result.returncode,
             log=str(log), diagnostic="\n".join(lines[-16:])[-4000:])
        return False
    return True


def export(args: argparse.Namespace) -> int:
    project = Path(args.project).expanduser().resolve()
    pages = sorted((project / "svg_output").glob("*.svg"))
    if not pages:
        raise ValueError("No SVG pages: author pages in <project>/svg_output first")
    if args.with_notes:
        missing = [page.stem for page in pages
                   if not (project / "notes" / f"{page.stem}.md").is_file()
                   or not (project / "notes" / f"{page.stem}.md").read_text("utf-8").strip()]
        if missing:
            raise ValueError("Missing non-empty per-page notes; run total_md_split.py: "
                             + ", ".join(missing[:8]))
    target = project / "exports" / "huixin.pptx"
    target.parent.mkdir(exist_ok=True)
    stages = [
        ("svg_check", "svg_quality_checker.py", [str(project), "--quick-generate",
                                                 "--stage", "final", "--json"]),
        ("export", "svg_to_pptx.py", [str(project), "--quick-generate",
                                     "--with-notes" if args.with_notes else "--no-notes",
                                     "-o", str(target)]),
        ("delivery", "pptx_delivery_check.py", [str(target)]),
    ]
    for stage, script, options in stages:
        if not run_logged(project, stage, [sys.executable, str(SCRIPTS / script), *options]):
            return 1
    report = json.loads((project / "validation/huixin_delivery.log").read_text("utf-8"))
    if report["slides"]["count"] != len(pages):
        raise ValueError("Exported slide count differs from the SVG roster; inspect delivery log")
    svg_report = json.loads((project / "validation/svg_quality_report.json").read_text("utf-8"))
    emit(status="ok", pptx=str(target), pages=len(pages),
         delivery_status=report.get("status"),
         svg_summary=svg_report["summary"],
         advisory_count=len(report.get("advisories", [])),
         advisory_codes=list(dict.fromkeys(item.get("code", "unknown")
                                           for item in report.get("advisories", [])))[:5],
         logs=str(project / "validation"))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("preflight", help="Check the selected Python; never install packages")
    setup = commands.add_parser("prepare", help="Initialize a fresh project and copy one theme")
    setup.add_argument("--deck", required=True)
    setup.add_argument("--name", required=True)
    setup.add_argument("--base-dir", required=True)
    delivery = commands.add_parser("export", help="Check SVG, export, audit; stop on any failure")
    delivery.add_argument("project")
    delivery.add_argument("--with-notes", action="store_true")
    args = parser.parse_args()
    require_skill_integrity()
    if sys.version_info < (3, 10) and args.command != "preflight":
        emit(status="failed", diagnostic="Use Python 3.10+ for every command")
        return 1
    try:
        if args.command == "preflight":
            return preflight()
        return prepare(args) if args.command == "prepare" else export(args)
    except (OSError, ValueError, ImportError) as exc:
        emit(status="failed", diagnostic=str(exc))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
