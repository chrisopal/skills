import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / 'scripts' / 'install.py'


class InstallTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.suite = self.root / 'suite'
        (self.suite / 'scripts').mkdir(parents=True)
        if SCRIPT.exists():
            shutil.copy2(SCRIPT, self.suite / 'scripts/install.py')
        for name in ('presales-a', 'presales-b'):
            skill = self.suite / 'skills' / name
            skill.mkdir(parents=True)
            (skill / 'SKILL.md').write_text('../presales-b/SKILL.md\n', encoding='utf-8')
        self.dest = self.root / 'installed'

    def run_install(self, dest=None, env=None):
        command = [sys.executable, str(self.suite / 'scripts/install.py')]
        if dest is not False:
            command += ['--dest', str(dest or self.dest)]
        return subprocess.run(command, capture_output=True, text=True, env=env)

    def test_copies_siblings_and_is_idempotent(self):
        first = self.run_install()
        self.assertEqual(first.returncode, 0, first.stderr)
        link = self.dest / 'presales-a/SKILL.md'
        self.assertEqual(link.read_text(), '../presales-b/SKILL.md\n')
        self.assertTrue((link.parent / '../presales-b/SKILL.md').is_file())
        before = link.stat().st_mtime_ns
        self.assertEqual(self.run_install().returncode, 0)
        self.assertEqual(link.stat().st_mtime_ns, before)

    def test_default_respects_codex_home_without_changing_config(self):
        home = self.root / 'custom-codex'
        home.mkdir()
        (home / 'config.toml').write_text('existing = true\n')
        result = self.run_install(False, {**os.environ, 'CODEX_HOME': str(home)})
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((home / 'skills/presales-a/SKILL.md').exists())
        self.assertEqual((home / 'config.toml').read_text(), 'existing = true\n')

    def test_conflict_preflight_never_installs_earlier_sibling(self):
        existing = self.dest / 'presales-b'
        existing.mkdir(parents=True)
        (existing / 'SKILL.md').write_text('user work')
        result = self.run_install()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('--dest', result.stderr)
        self.assertFalse((self.dest / 'presales-a').exists())
        self.assertEqual((existing / 'SKILL.md').read_text(), 'user work')

    def test_ignores_generated_cache_files(self):
        cache = self.suite / 'skills/presales-a/__pycache__'
        cache.mkdir()
        (cache / 'x.pyc').write_bytes(b'generated')
        result = self.run_install()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse((self.dest / 'presales-a/__pycache__').exists())

    def test_rejects_source_symlink(self):
        (self.suite / 'skills/presales-a/escape').symlink_to(self.root)
        self.assertNotEqual(self.run_install().returncode, 0)
        self.assertFalse(self.dest.exists())

    def test_rejects_target_symlink_and_symlink_ancestor(self):
        real = self.root / 'real'
        real.mkdir()
        self.dest.symlink_to(real, target_is_directory=True)
        for destination in (self.dest, self.dest / 'child'):
            self.assertNotEqual(self.run_install(destination).returncode, 0)
        self.assertEqual(list(real.iterdir()), [])

    def test_rejects_nested_target_symlink_without_writing(self):
        target = self.dest / 'presales-b'
        target.mkdir(parents=True)
        (target / 'SKILL.md').symlink_to(self.suite / 'skills/presales-b/SKILL.md')
        self.assertNotEqual(self.run_install().returncode, 0)
        self.assertFalse((self.dest / 'presales-a').exists())

    def test_rejects_non_directory_destination_and_source_containment(self):
        self.dest.write_text('keep')
        self.assertNotEqual(self.run_install().returncode, 0)
        self.assertEqual(self.dest.read_text(), 'keep')
        nested = self.suite / 'skills/presales-a/nested'
        self.assertNotEqual(self.run_install(nested).returncode, 0)
        self.assertFalse(nested.exists())


if __name__ == '__main__':
    unittest.main()
