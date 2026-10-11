import importlib.util
from pathlib import Path
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/install.py'
spec = importlib.util.spec_from_file_location('delivery_install', SCRIPT)
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


class InstallTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name).resolve()
        self.source = self.base / 'suite/skills'
        self.destination = self.base / 'installed'
        for name in ('delivery-orchestrator', 'delivery-business-blueprint'):
            directory = self.source / name
            directory.mkdir(parents=True)
            (directory / 'SKILL.md').write_text(name)

    def test_install_and_reuse(self):
        result = installer.install(self.source, self.destination)
        self.assertEqual(result['verified_skills'], 2)
        self.assertEqual(len(result['installed']), 2)
        result = installer.install(self.source, self.destination)
        self.assertEqual(result['installed'], [])

    def test_conflict_no_partial_write(self):
        target = self.destination / 'delivery-orchestrator'
        target.mkdir(parents=True)
        (target/'SKILL.md').write_text('user modification')
        with self.assertRaises(ValueError):
            installer.install(self.source, self.destination)
        self.assertFalse((self.destination/'delivery-business-blueprint').exists())
        self.assertEqual((target/'SKILL.md').read_text(), 'user modification')

    def test_no_symlink_source(self):
        (self.source/'delivery-orchestrator/linked').symlink_to(self.source/'delivery-business-blueprint/SKILL.md')
        with self.assertRaises(ValueError):
            installer.install(self.source, self.destination)

    def test_no_symlink_destination(self):
        self.destination.symlink_to(self.source, target_is_directory=True)
        with self.assertRaises(ValueError):
            installer.install(self.source, self.destination)

    def test_no_self_install(self):
        with self.assertRaises(ValueError):
            installer.install(self.source, self.source.parent/'installed')

    def test_installed_hashes(self):
        installer.install(self.source, self.destination)
        for skill in self.source.iterdir():
            self.assertEqual(installer.manifest(skill), installer.manifest(self.destination/skill.name))


if __name__ == '__main__':
    unittest.main()
