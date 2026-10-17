"""Check the emitted CSS contract, not documentation wording."""
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]


def blocks(css):
    return [(selector.strip(), dict(re.findall(r"--ui-([\w-]+):\s*([^;]+);", body)))
            for selector, body in re.findall(r"([^{}]+)\{([^{}]*)\}", css)]


class TokenContract(unittest.TestCase):
    def setUp(self):
        self.tokens = json.loads((ROOT / "assets/tokens.json").read_text())
        self.rules = blocks((ROOT / "assets/tokens.css").read_text())

    def test_common_and_light_are_emitted(self):
        self.assertEqual(self.rules[0][1], self.tokens["common"] | self.tokens["modes"]["light"])

    def test_dark_changes_only_the_semantic_palette(self):
        dark = next(values for selector, values in self.rules if '[data-theme="dark"]' in selector)
        self.assertEqual(dark, self.tokens["modes"]["dark"])
        self.assertEqual(set(dark), set(self.tokens["modes"]["light"]))

    def test_legacy_component_contract_stays_available(self):
        # Frozen public v1.0 contract: additions are safe; changing old values is
        # an intentional compatibility decision, not an incidental layout edit.
        legacy = json.loads((ROOT / 'tests/fixtures/v1-token-contract.json').read_text())
        for key, value in legacy['common'].items():
            self.assertEqual(self.tokens['common'][key], value, key)
        self.assertEqual(self.tokens['modes'], legacy['modes'])
        for selector, _ in self.rules:
            self.assertIn('html', selector)
            self.assertIn('[data-ui="enterprise"]', selector)

    def test_semantic_color_pairs_retain_readable_contrast(self):
        def luminance(hex_color):
            channels = [int(hex_color[i:i + 2], 16) / 255 for i in (1, 3, 5)]
            linear = [c / 12.92 if c <= .04045 else ((c + .055) / 1.055) ** 2.4 for c in channels]
            return sum(c * w for c, w in zip(linear, (.2126, .7152, .0722)))
        for name, palette in self.tokens["modes"].items():
            palette = self.tokens["common"] | palette
            for foreground, background in (("text", "surface"), ("text-secondary", "surface"),
                                            ("action-text", "surface"), ("on-action", "action-solid")):
                high, low = sorted((luminance(palette[foreground]), luminance(palette[background])), reverse=True)
                self.assertGreaterEqual((high + .05) / (low + .05), 4.5, (name, foreground, background))

    def test_density_is_independent_of_theme_and_preserves_page_hierarchy(self):
        compact = self.tokens['densities']['compact']
        emitted = next(values for selector, values in self.rules if '[data-density="compact"]' in selector)
        self.assertEqual(emitted, compact)
        self.assertNotIn('font-body', compact)
        self.assertNotIn('layout-section-gap', compact)
        self.assertFalse(set(compact) & set(self.tokens['modes']['light']))
        for key, value in compact.items():
            self.assertIn(key, self.tokens['common'])
            self.assertLessEqual(float(value.removesuffix('px')),
                                 float(self.tokens['common'][key].removesuffix('px')))

    def test_reusable_css_has_no_unresolved_variables(self):
        defined = set(self.tokens['common']) | set(self.tokens['modes']['light'])
        for path in (ROOT / 'assets').rglob('*.css'):
            used = set(re.findall(r'var\(--ui-([\w-]+)', path.read_text()))
            self.assertFalse(used - defined, (str(path), used - defined))

    def test_generator_checks_reproducibility_and_detects_stale_output(self):
        generator = ROOT / 'scripts/generate_tokens.py'
        checked = subprocess.run([sys.executable, str(generator), '--check'], capture_output=True, text=True)
        self.assertEqual(checked.returncode, 0, checked.stderr + checked.stdout)
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'tokens.css'
            subprocess.run([sys.executable, str(generator), '--output', str(output)], check=True, capture_output=True)
            self.assertEqual(output.read_bytes(), (ROOT / 'assets/tokens.css').read_bytes())
            output.write_text(output.read_text().replace('--ui-layout-panel-inset: 20px;', '--ui-layout-panel-inset: 99px;'))
            stale = subprocess.run([sys.executable, str(generator), '--output', str(output), '--check'], capture_output=True)
            self.assertNotEqual(stale.returncode, 0)


if __name__ == "__main__":
    unittest.main()
