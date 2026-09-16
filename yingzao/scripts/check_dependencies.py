#!/usr/bin/env python3
"""Check runtime dependencies without installing or mutating the environment."""

from __future__ import annotations

import importlib
import sys

sys.dont_write_bytecode = True

from _runtime import ensure_runtime


REQUIRED = {
    "PIL": "Pillow",
    "numpy": "numpy",
    "cv2": "opencv-python-headless",
    "fontTools": "fonttools",
}

ensure_runtime(REQUIRED)


def main() -> int:
    missing: list[str] = []
    for module, package in REQUIRED.items():
        try:
            loaded = importlib.import_module(module)
        except ImportError:
            missing.append(package)
            print(f"MISSING  {package} (import {module})")
            continue
        version = getattr(loaded, "__version__", "unknown")
        print(f"OK       {package} {version}")
    if missing:
        print(
            "Install the declared dependencies from requirements.txt in an isolated environment.",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
