"""User-facing runner and explicit visual readback contracts."""
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/run.py'


class RunTests(unittest.TestCase):
    def call(self, *args):
        return subprocess.run([sys.executable, str(SCRIPT), *map(str, args)], capture_output=True, text=True)

    def test_forwards_catalog_commands_and_exit_status(self):
        result = self.call('tokens', 'validate')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('Valid:', result.stdout)
        self.assertNotEqual(self.call('tokens', 'invalid-command').returncode, 0)

    def test_readback_requires_all_visual_observations(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            image = root / 'poster.png'
            Image.new('RGB', (20, 20), 'red').save(image)
            observations = root / 'observations.json'
            observations.write_text(json.dumps({'subject': {'status': 'pass', 'evidence': 'Roof preserved'}}))
            result = self.call('readback', '--image', image, '--observations', observations,
                               '--output', root / 'readback.md')
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse((root / 'readback.md').exists())
            data = {key: {'status': 'pass', 'evidence': 'Inspected visible ' + key}
                    for key in ('subject', 'background', 'glyphs', 'interaction', 'reference')}
            data['glyphs'] = {'status': 'uncertain', 'evidence': 'Small text needs manual confirmation'}
            observations.write_text(json.dumps(data))
            result = self.call('readback', '--image', image, '--observations', observations,
                               '--output', root / 'readback.md')
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            report = (root / 'readback.md').read_text()
            self.assertIn(hashlib.sha256(image.read_bytes()).hexdigest(), report)
            self.assertIn('uncertain', report)
            self.assertIn('manual confirmation', report)

    def test_readback_refuses_to_overwrite_input(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            image = root / 'poster.png'
            Image.new('RGB', (20, 20), 'red').save(image)
            original = image.read_bytes()
            observations = root / 'observations.json'
            observations.write_text(json.dumps({key: {'status': 'pass', 'evidence': 'Visible'}
                for key in ('subject', 'background', 'glyphs', 'interaction', 'reference')}))
            result = self.call('readback', '--image', image, '--observations', observations, '--output', image)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(image.read_bytes(), original)

    def test_series_manifest_requires_series_readback(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            image = root / 'poster.png'
            Image.new('RGB', (20, 20), 'red').save(image)
            manifest = root / 'manifest.json'
            manifest.write_text(json.dumps({'call_signature': 'example', 'series': {'spec': {'series_id': 'city'}}}))
            observations = root / 'observations.json'
            data = {key: {'status': 'pass', 'evidence': 'Observed visible details'}
                    for key in ('subject', 'background', 'glyphs', 'interaction', 'reference')}
            observations.write_text(json.dumps(data))
            args = ('readback', '--image', image, '--observations', observations,
                    '--manifest', manifest, '--output', root / 'readback.md')
            result = self.call(*args)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('series', result.stderr)
            data['series'] = {'status': 'issue', 'evidence': 'Palette differs from the agreed warm white'}
            observations.write_text(json.dumps(data))
            result = self.call(*args)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('Palette differs', (root / 'readback.md').read_text())


if __name__ == '__main__':
    unittest.main()
