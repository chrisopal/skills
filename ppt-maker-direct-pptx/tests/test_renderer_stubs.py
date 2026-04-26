"""Verify every JS renderer stub loads and produces shapes via Node."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

SKILL_ROOT = Path(__file__).resolve().parent.parent
VERIFY_SCRIPT = SKILL_ROOT / "tests" / "_renderer_verify.js"


def _node() -> str | None:
    return shutil.which("node")


@pytest.mark.skipif(_node() is None, reason="node binary not on PATH")
def test_all_renderer_stubs_load_and_render():
    result = subprocess.run(
        [_node(), str(VERIFY_SCRIPT)],
        capture_output=True,
        text=True,
        cwd=SKILL_ROOT,
    )
    assert result.returncode == 0, (
        f"renderer verifier failed (exit {result.returncode})\n"
        f"stdout: {result.stdout}\n"
        f"stderr: {result.stderr}"
    )
    assert "OK 12 renderers verified" in result.stdout
