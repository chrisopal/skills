"""Schema lint pass: validate the three artifact JSONs and check structural invariants.

Runs at gate 4 (outline) and gate 5 (slide_prompts) and gate 7 (slide_specs).
Failures are deterministic JSON-Schema violations or structural mismatches:
- artifact failing schema validation -> per-page fail
- duplicate page_no within a file
- mismatched page_count between requirement and outline
- pattern_id referenced in slide_prompts but unknown to the registry
- image_placeholder.status set to a stale value
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path
from typing import Iterable

from jsonschema import Draft202012Validator

SKILL_ROOT = Path(__file__).resolve().parent.parent
SCHEMAS_DIR = SKILL_ROOT / "assets" / "schemas"
PATTERNS_DIR = SKILL_ROOT / "assets" / "patterns"


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
registry_mod = _load_local("pattern_registry", "scripts/lib/pattern_registry.py")


def _schema_for(filename: str) -> dict:
    schema_path = SCHEMAS_DIR / filename.replace(".json", ".schema.json")
    return json.loads(schema_path.read_text(encoding="utf-8"))


def _validate(file_label: str, artifact: dict, schema: dict) -> list:
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(artifact), key=lambda e: list(e.path))
    out = []
    for err in errors:
        # Try to attribute to a page_no when the path traverses slides[N].
        page_no = None
        path = list(err.path)
        if path and path[0] == "slides" and len(path) >= 2:
            try:
                idx = int(path[1])
                page_no = artifact.get("slides", [])[idx].get("page_no")
            except (ValueError, IndexError, AttributeError, TypeError):
                page_no = None
        rule = f"{file_label}.schema:" + ".".join(str(p) for p in path) if path else f"{file_label}.schema"
        out.append(lint_common.LintResult(
            category="schema",
            rule=rule,
            severity="fail",
            detail=err.message,
            page_no=page_no,
        ))
    return out


def _check_duplicate_page_nos(file_label: str, slides: list[dict]) -> list:
    seen: dict[int, int] = {}
    out = []
    for slide in slides:
        page_no = slide.get("page_no")
        if not isinstance(page_no, int):
            continue
        if page_no in seen:
            out.append(lint_common.LintResult(
                category="schema",
                rule=f"{file_label}.duplicate_page_no",
                severity="fail",
                detail=f"page_no {page_no} appears more than once",
                page_no=page_no,
            ))
        else:
            seen[page_no] = 1
    return out


def _check_pattern_ids(slide_prompts: dict, registry) -> list:
    out = []
    for slide in slide_prompts.get("slides", []):
        pattern_id = slide.get("pattern_id")
        if not pattern_id:
            continue
        if pattern_id not in registry:
            out.append(lint_common.LintResult(
                category="schema",
                rule="slide_prompts.unknown_pattern_id",
                severity="fail",
                detail=f"pattern_id {pattern_id!r} not in registry",
                page_no=slide.get("page_no"),
            ))
    return out


def _check_image_status(slide_specs: dict) -> list:
    valid = {"pending", "placeholder", "generated", "skipped", "regenerating"}
    out = []
    for slide in slide_specs.get("slides", []):
        page_no = slide.get("page_no")
        for placeholder in slide.get("image_placeholders", []):
            status = placeholder.get("status")
            if status is not None and status not in valid:
                out.append(lint_common.LintResult(
                    category="schema",
                    rule="slide_specs.invalid_image_status",
                    severity="fail",
                    detail=f"image_placeholder.status={status!r} not in {sorted(valid)}",
                    page_no=page_no,
                ))
    return out


def _check_page_count(outline: dict, expected: int | None) -> list:
    if expected is None:
        return []
    actual = len(outline.get("slides", []))
    if actual != expected:
        return [lint_common.LintResult(
            category="schema",
            rule="outline.page_count_mismatch",
            severity="fail",
            detail=f"requirement page_count={expected} but outline has {actual} slides",
        )]
    return []


def lint_artifacts(
    *,
    outline: dict | None = None,
    slide_prompts: dict | None = None,
    slide_specs: dict | None = None,
    expected_page_count: int | None = None,
    patterns_dir: Path = PATTERNS_DIR,
) -> list:
    results: list = []
    if outline is not None:
        results.extend(_validate("outline", outline, _schema_for("outline.json")))
        results.extend(_check_duplicate_page_nos("outline", outline.get("slides", [])))
        results.extend(_check_page_count(outline, expected_page_count))
    if slide_prompts is not None:
        results.extend(_validate("slide_prompts", slide_prompts, _schema_for("slide_prompts.json")))
        results.extend(_check_duplicate_page_nos("slide_prompts", slide_prompts.get("slides", [])))
        registry = registry_mod.PatternRegistry(patterns_dir)
        results.extend(_check_pattern_ids(slide_prompts, registry))
    if slide_specs is not None:
        results.extend(_validate("slide_specs", slide_specs, _schema_for("slide_specs.json")))
        results.extend(_check_duplicate_page_nos("slide_specs", slide_specs.get("slides", [])))
        results.extend(_check_image_status(slide_specs))
    return results


def _read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run schema-class lint over artifact JSONs.")
    parser.add_argument("--outline")
    parser.add_argument("--slide-prompts")
    parser.add_argument("--slide-specs")
    parser.add_argument("--expected-page-count", type=int)
    args = parser.parse_args(argv)

    results = lint_artifacts(
        outline=_read(Path(args.outline)) if args.outline else None,
        slide_prompts=_read(Path(args.slide_prompts)) if args.slide_prompts else None,
        slide_specs=_read(Path(args.slide_specs)) if args.slide_specs else None,
        expected_page_count=args.expected_page_count,
    )
    fails = [r for r in results if r.severity == "fail"]
    print(json.dumps({
        "results": [r.to_result_dict() for r in results],
        "summary": {"fail": len(fails), "total": len(results)},
    }, ensure_ascii=False, indent=2))
    return 0 if not fails else 2


if __name__ == "__main__":
    sys.exit(main())
