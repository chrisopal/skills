#!/usr/bin/env python3
"""Run the shared sibling package without installing dependencies."""
from pathlib import Path
import sys


def main() -> None:
    source = Path(__file__).resolve().parents[2] / "opportunity-analysis-skill" / "src"
    if not (source / "opportunity_skill" / "cli.py").is_file():
        raise SystemExit("Missing sibling opportunity-analysis-skill; install all seven opportunity skills together.")
    sys.path.insert(0, str(source))
    sys.dont_write_bytecode = True
    from opportunity_skill.cli import main as run
    run()


if __name__ == "__main__":
    main()
