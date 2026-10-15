"""Run actual isolated Skill packages without an adjacent suite checkout."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "tests"))
import bidkit
from core_review_fixture import populate


class StandaloneAIScoringTests(unittest.TestCase):
    def test_prepare_check_render_and_stale_rejection_in_isolated_packages(self):
        for number, skill in [(11, "bid-technical-writing"), (15, "bid-review-remediation"),
                              (17, "bid-orchestrator")]:
            with self.subTest(skill=skill), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                with zipfile.ZipFile(ROOT / f"installable-zips/{number:02d}-{skill}.zip") as archive:
                    archive.extractall(root)
                project = root / "project"
                bidkit.init_project(project, "TEST-ONLY-INSTALL")
                populate(project)
                script = root / skill / "scripts/ai_scoring.py"
                env = dict(os.environ)
                env.pop("PYTHONPATH", None)

                status = subprocess.run(
                    [sys.executable, str(root / skill / "scripts/ai_scoring_actions.py"),
                     "status", "--project", str(project)], cwd=root, env=env,
                    capture_output=True, text=True)
                self.assertEqual(status.returncode, 0, status.stdout + status.stderr)
                self.assertEqual(json.loads(status.stdout)["host_execution"], "manual_handoff")

                def run(*args):
                    return subprocess.run([sys.executable, str(script), *args,
                                           "--project", str(project)], cwd=root,
                                          env=env, capture_output=True, text=True)

                prepared = run("prepare", "--out", "reviews/test-plan.json")
                self.assertEqual(prepared.returncode, 0, prepared.stderr)
                artifact = json.loads(prepared.stdout)["artifact"]
                self.assertEqual(artifact["semantic_evaluation"], "NOT_RUN")
                self.assertIsNone(artifact["rows"][0]["simulated_score"])
                plan = project / "reviews/test-plan.json"
                checked = run("check", "--scoring", str(plan))
                self.assertEqual(checked.returncode, 0, checked.stdout + checked.stderr)
                rendered = run("render", "--scoring", str(plan), "--out", "reports/test.html")
                self.assertEqual(rendered.returncode, 0, rendered.stdout + rendered.stderr)
                page = (project / "reports/test.html").read_text()
                self.assertIn("空评分计划", page)
                self.assertIn("招标原文", page)
                self.assertIn("full_text", page)
                (project / "artifacts/new-input.txt").write_text("TEST ONLY changed input")
                stale = run("check", "--scoring", str(plan))
                self.assertEqual(stale.returncode, 1)
                self.assertTrue(any("快照过期" in error for error in json.loads(stale.stdout)["errors"]))


if __name__ == "__main__":
    unittest.main()
