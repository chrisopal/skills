"""Batch-lock pages on outline_status or intent_status.

Usage:
    python scripts/lock_pages.py --pages 1,2,3 --layer intent
        --slide-prompts artifacts/slide_prompts.json
        [--reason "approved at gate 5"]

The script transitions every listed page through pending_review (if needed)
into locked. Illegal transitions (e.g. trying to lock an intent before its
outline is locked) raise IllegalTransitionError so the caller doesn't
silently get a partial result.
"""

from __future__ import annotations

import argparse
import importlib.util
import sys
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


def _parse_pages(spec: str) -> list[int]:
    out: list[int] = []
    for chunk in spec.split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        if "-" in chunk:
            lo, hi = (int(x) for x in chunk.split("-", 1))
            out.extend(range(lo, hi + 1))
        else:
            out.append(int(chunk))
    return out


def lock_pages(machine, *, pages: list[int], layer: str, reason: str = "") -> int:
    layer_field = "outline_status" if layer == "outline" else "intent_status"
    transitions_made = 0
    for page_no in pages:
        current = machine.status_for(page_no).get(layer_field, "draft")
        if current == "locked":
            continue
        if current == "draft":
            machine.transition(page_no, layer_field, "pending_review", reason=reason or "lock_pages: pre-lock")
            current = "pending_review"
        if current == "needs_rework":
            machine.transition(page_no, layer_field, "pending_review", reason=reason or "lock_pages: rework->review")
            current = "pending_review"
        if current == "pending_review":
            machine.transition(page_no, layer_field, "locked", reason=reason or "lock_pages")
            transitions_made += 1
    return transitions_made


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Batch-lock pages on outline or intent layer.")
    parser.add_argument("--pages", required=True, help="Page list, e.g. 1,2,3 or 1-5,7")
    parser.add_argument("--layer", required=True, choices=("outline", "intent"))
    parser.add_argument("--outline", type=Path)
    parser.add_argument("--slide-prompts", type=Path)
    parser.add_argument("--reason", default="")
    args = parser.parse_args(argv)

    machine = page_state.load_machine(
        outline_path=args.outline, slide_prompts_path=args.slide_prompts,
    )
    transitions = lock_pages(
        machine, pages=_parse_pages(args.pages), layer=args.layer, reason=args.reason,
    )
    page_state.persist_machine(
        machine, outline_path=args.outline, slide_prompts_path=args.slide_prompts,
    )
    print(f"locked {transitions} page(s) on layer {args.layer}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
