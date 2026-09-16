#!/usr/bin/env python3
"""Select a caller-owned Python runtime for scripts with optional dependencies."""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
from collections.abc import Iterable
from pathlib import Path


RUNTIME_OVERRIDE_ENV = "CAP_PYTHON"
HANDOFF_GUARD_ENV = "CAP_RUNTIME_HANDOFF"


def missing_modules(modules: Iterable[str]) -> list[str]:
    """Return top-level import names unavailable in the current interpreter."""
    return [module for module in modules if importlib.util.find_spec(module) is None]


def runtime_candidates(start: Path | None = None) -> list[Path]:
    """Find explicit or caller-workspace virtualenv interpreters, nearest first."""
    candidates: list[Path] = []
    override = os.environ.get(RUNTIME_OVERRIDE_ENV)
    if override:
        candidates.append(Path(override).expanduser())

    current = (start or Path.cwd()).resolve()
    for root in (current, *current.parents):
        candidates.extend((root / ".venv" / "bin" / "python", root / ".venv" / "Scripts" / "python.exe"))

    resolved_current = Path(sys.executable).resolve()
    unique: list[Path] = []
    seen: set[Path] = set()
    for candidate in candidates:
        if not candidate.exists():
            continue
        resolved = candidate.resolve()
        if resolved == resolved_current or resolved in seen:
            continue
        seen.add(resolved)
        unique.append(candidate)
    return unique


def supports_modules(interpreter: Path, modules: Iterable[str]) -> bool:
    """Check a candidate without importing packages into the current process."""
    imports = "; ".join(f"import {module}" for module in modules)
    environment = os.environ.copy()
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    try:
        completed = subprocess.run(
            [str(interpreter), "-c", imports],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            env=environment,
            timeout=15,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return completed.returncode == 0


def ensure_runtime(modules: Iterable[str]) -> None:
    """Re-exec the current command in a compatible caller-owned virtualenv."""
    required = tuple(dict.fromkeys(modules))
    missing = missing_modules(required)
    if not missing:
        return

    if not os.environ.get(HANDOFF_GUARD_ENV):
        for candidate in runtime_candidates():
            if supports_modules(candidate, required):
                environment = os.environ.copy()
                environment[HANDOFF_GUARD_ENV] = "1"
                environment["PYTHONDONTWRITEBYTECODE"] = "1"
                os.execve(
                    str(candidate),
                    [str(candidate), str(Path(sys.argv[0]).resolve()), *sys.argv[1:]],
                    environment,
                )

    names = ", ".join(missing)
    raise SystemExit(
        f"Missing Python modules: {names}. Create a caller-workspace .venv and install "
        "the Skill requirements there, or set CAP_PYTHON to a compatible interpreter."
    )
