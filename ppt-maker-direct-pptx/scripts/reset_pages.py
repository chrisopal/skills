"""Reset pages to needs_rework on outline_status or intent_status.

Usage:
    python scripts/reset_pages.py --pages 4 --layer intent
        --slide-prompts artifacts/slide_prompts.json
        [--reason "user wants different layout"]

Pages currently in `locked` or `pending_review` move to `needs_rework`.
Pages in `draft` are left alone (you can't rework what hasn't been started).
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


def reset_pages(machine, *, pages: list[int], layer: str, reason: str = "") -> int:
    layer_field = "outline_status" if layer == "outline" else "intent_status"
    transitions = 0
    for page_no in pages:
        current = machine.status_for(page_no).get(layer_field, "draft")
        if current in ("locked", "pending_review"):
            machine.transition(
                page_no, layer_field, "needs_rework",
                reason=reason or "reset_pages",
            )
            transitions += 1
    return transitions


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Reset pages back to needs_rework.")
    parser.add_argument("--pages", required=True, help="Page list, e.g. 4 or 4,5-7")
    parser.add_argument("--layer", required=True, choices=("outline", "intent"))
    parser.add_argument("--outline", type=Path)
    parser.add_argument("--slide-prompts", type=Path)
    parser.add_argument("--reason", default="")
    args = parser.parse_args(argv)

    machine = page_state.load_machine(
        outline_path=args.outline, slide_prompts_path=args.slide_prompts,
    )
    transitions = reset_pages(
        machine, pages=_parse_pages(args.pages), layer=args.layer, reason=args.reason,
    )
    page_state.persist_machine(
        machine, outline_path=args.outline, slide_prompts_path=args.slide_prompts,
    )
    print(f"reset {transitions} page(s) on layer {args.layer} to needs_rework")
    return 0


if __name__ == "__main__":
    sys.exit(main())
