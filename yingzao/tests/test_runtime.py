#!/usr/bin/env python3
"""Regression tests for caller-owned virtualenv discovery and handoff."""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

import _runtime  # noqa: E402


class RuntimeBootstrapTests(unittest.TestCase):
    def test_nearest_workspace_virtualenv_is_discovered(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            nested = root / "project" / "output" / "run"
            interpreter = root / "project" / ".venv" / "bin" / "python"
            nested.mkdir(parents=True)
            interpreter.parent.mkdir(parents=True)
            interpreter.write_text("", encoding="utf-8")

            with patch.dict(os.environ, {_runtime.RUNTIME_OVERRIDE_ENV: ""}, clear=False):
                candidates = _runtime.runtime_candidates(nested)

            self.assertEqual(candidates[0].resolve(), interpreter.resolve())

    def test_candidate_module_probe_is_deterministic(self) -> None:
        self.assertTrue(_runtime.supports_modules(Path(sys.executable), ("json", "pathlib")))
        self.assertFalse(
            _runtime.supports_modules(Path(sys.executable), ("cap_module_that_does_not_exist",))
        )

    def test_missing_runtime_hands_off_instead_of_continuing(self) -> None:
        candidate = Path("/tmp/cap-test-python")
        with (
            patch.object(_runtime, "missing_modules", return_value=["numpy"]),
            patch.object(_runtime, "runtime_candidates", return_value=[candidate]),
            patch.object(_runtime, "supports_modules", return_value=True),
            patch.object(_runtime.os, "execve", side_effect=SystemExit("handoff")) as execve,
            patch.dict(os.environ, {_runtime.HANDOFF_GUARD_ENV: ""}, clear=False),
        ):
            with self.assertRaisesRegex(SystemExit, "handoff"):
                _runtime.ensure_runtime(("numpy",))

        self.assertEqual(execve.call_args.args[0], str(candidate))
        self.assertEqual(execve.call_args.args[2][_runtime.HANDOFF_GUARD_ENV], "1")


if __name__ == "__main__":
    unittest.main()
