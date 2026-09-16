#!/usr/bin/env python3
"""Dispatch Yingzao scripts without changing the caller's output directory."""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True

COMMANDS = {
    'check': 'check_dependencies.py',
    'tokens': 'design_tokens.py',
    'preflight': 'photo_preflight.py',
    'rectify': 'rectify.py',
    'mask': 'subject_mask.py',
    'fit': 'fit_canvas.py',
    'typeset': 'typeset_compose.py',
    'prepare': 'prepare_generation.py',
    'compare': 'make_comparison.py',
    'readback': 'record_readback.py',
}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=COMMANDS)
    parser.add_argument('arguments', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    script = Path(__file__).resolve().parent / COMMANDS[args.command]
    return subprocess.run([sys.executable, '-B', str(script), *args.arguments], check=False).returncode


if __name__ == '__main__':
    raise SystemExit(main())
