"""Unified entry point for the master_style system.

Dispatches to the three style input paths:

    python scripts/define_style.py preset --id huixin
        [--override 'color_strategy.primary_green=#1A237E' ...]
    python scripts/define_style.py nl --description "..."
    python scripts/define_style.py reference --file path/to/ref.png

Each subcommand writes a validated master_style.json to --out
(default: artifacts/master_style.json).

Override values are parsed as JSON when possible (so '#1A237E', 14, true,
[ "a","b" ] all work) and fall back to plain string for anything else.
"""

from __future__ import annotations

import argparse
import json
import sys
from importlib import util as _importlib_util
from pathlib import Path
from typing import Callable

SKILL_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUT_PATH = SKILL_ROOT / "artifacts" / "master_style.json"


def _load_local(name: str, path: Path):
    if name in sys.modules:
        return sys.modules[name]
    spec = _importlib_util.spec_from_file_location(name, path)
    module = _importlib_util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


style_inherit = _load_local(
    "style_inherit", SKILL_ROOT / "scripts" / "lib" / "style_inherit.py"
)
style_from_nl = _load_local(
    "style_from_nl", SKILL_ROOT / "scripts" / "style_from_nl.py"
)
style_from_reference = _load_local(
    "style_from_reference", SKILL_ROOT / "scripts" / "style_from_reference.py"
)


def _parse_override(spec: str) -> tuple[str, object]:
    if "=" not in spec:
        raise argparse.ArgumentTypeError(
            f"override must be 'dotted.path=value', got {spec!r}"
        )
    key, _, raw = spec.partition("=")
    key = key.strip()
    raw = raw.strip()
    if not key:
        raise argparse.ArgumentTypeError("override key may not be empty")
    try:
        value: object = json.loads(raw)
    except json.JSONDecodeError:
        value = raw
    return key, value


def _write_master_style(out_path: Path, master_style: dict) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(master_style, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def cmd_preset(args: argparse.Namespace) -> int:
    overrides = dict(args.override or [])
    master_style = style_inherit.inherit_preset(args.id, overrides)
    _write_master_style(args.out, master_style)
    print(
        f"Wrote {args.out}. source={master_style['source']} "
        f"parent={master_style.get('parent_template_id')}"
    )
    return 0


def cmd_nl(args: argparse.Namespace, *, model_caller: Callable | None = None) -> int:
    caller = model_caller or style_from_nl._default_caller_from_env()
    result = style_from_nl.generate_style_from_nl(
        args.description,
        model_caller=caller,
        max_retries=args.max_retries,
    )
    _write_master_style(args.out, result.master_style)
    print(
        f"Wrote {args.out} after {result.attempts} attempt(s). "
        f"source={result.master_style['source']}"
    )
    return 0


def cmd_reference(args: argparse.Namespace, *, vision_caller: Callable | None = None) -> int:
    caller = vision_caller or style_from_reference._default_vision_caller_from_env()
    result = style_from_reference.build_master_style(
        args.file, vision_caller=caller, n_colors=args.n_colors
    )
    _write_master_style(args.out, result.master_style)
    print(
        f"Wrote {args.out}. palette={[c.hex for c in result.palette]} "
        f"source={result.master_style['source']}"
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Define master_style.json via preset, NL, or reference image."
    )
    subparsers = parser.add_subparsers(dest="subcommand", required=True)

    preset = subparsers.add_parser("preset", help="Use a shipped preset (optionally with overrides)")
    preset.add_argument("--id", required=True, help="template_id or alias")
    preset.add_argument(
        "--override",
        action="append",
        type=_parse_override,
        metavar="KEY=VALUE",
        help="Dotted-path override (repeatable)",
    )
    preset.add_argument("--out", type=Path, default=DEFAULT_OUT_PATH)
    preset.set_defaults(func=cmd_preset)

    nl = subparsers.add_parser("nl", help="Generate master_style from a free-text description")
    nl.add_argument("--description", required=True)
    nl.add_argument("--max-retries", type=int, default=style_from_nl.MAX_RETRIES)
    nl.add_argument("--out", type=Path, default=DEFAULT_OUT_PATH)
    nl.set_defaults(func=cmd_nl)

    ref = subparsers.add_parser("reference", help="Extract master_style from a reference image")
    ref.add_argument("--file", type=Path, required=True)
    ref.add_argument("--n-colors", type=int, default=6)
    ref.add_argument("--out", type=Path, default=DEFAULT_OUT_PATH)
    ref.set_defaults(func=cmd_reference)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
