import importlib.util
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("opportunity_install", ROOT / "scripts" / "install.py")
installer = importlib.util.module_from_spec(spec)


class DistributionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec.loader.exec_module(installer)

    def test_install_preserves_all_seven_skills_and_runtime(self):
        with tempfile.TemporaryDirectory() as temp:
            dest = Path(temp) / "skills"
            result = installer.install(dest)
            self.assertEqual(len(result["installed"]), 7)
            run = dest / "opportunity-orchestrator" / "scripts" / "run.py"
            completed = subprocess.run([sys.executable, str(run), "--help"], capture_output=True, text=True)
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertIn("analyze", completed.stdout)
            self.assertEqual(len(installer.install(dest)["unchanged"]), 7)

    def test_conflict_preflight_does_not_overwrite_or_partially_install(self):
        with tempfile.TemporaryDirectory() as temp:
            dest = Path(temp)
            conflict = dest / "opportunity-negotiation"
            conflict.mkdir()
            sentinel = conflict / "SKILL.md"
            sentinel.write_text("user-owned skill", encoding="utf-8")
            with self.assertRaises(FileExistsError):
                installer.install(dest)
            self.assertEqual(sentinel.read_text(), "user-owned skill")
            self.assertFalse((dest / "opportunity-analysis-skill").exists())

    def test_missing_source_preflight_leaves_destination_untouched(self):
        with tempfile.TemporaryDirectory() as source, tempfile.TemporaryDirectory() as target:
            with self.assertRaises(FileNotFoundError):
                installer.install(Path(target), source_root=Path(source))
            self.assertEqual(list(Path(target).iterdir()), [])

    def test_export_excludes_generated_caches_and_databases(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "SKILL.md").write_text("skill")
            (root / "record.db").write_text("private")
            (root / "output").mkdir()
            (root / "output" / "report.html").write_text("generated")
            (root / "__pycache__").mkdir()
            (root / "__pycache__" / "x.pyc").write_bytes(b"cache")
            self.assertEqual(list(installer.source_files(root)), [Path("SKILL.md")])


if __name__ == "__main__":
    unittest.main()
