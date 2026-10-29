"""Check the emitted CSS contract, not documentation wording."""
import json
import copy
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]

sys.path.insert(0, str(ROOT / "scripts"))
from resolve_tokens import (  # noqa: E402
    TokenConfigError,
    build_runtime_config,
    resolve_config,
    validate_contrast,
    validate_ownership,
)

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

    def test_all_profile_series_meet_non_text_contrast(self):
        def lum(color):
            c = [int(color[i:i+2], 16) / 255 for i in (1, 3, 5)]
            return sum((v / 12.92 if v <= .04045 else ((v + .055) / 1.055) ** 2.4) * w
                       for v, w in zip(c, (.2126, .7152, .0722)))
        for name, profile in self.tokens['profiles'].items():
            for theme in profile['supported-themes']:
                palette = resolve_config(self.tokens, profile=name, theme=theme)['values']
                for key, value in palette.items():
                    if not key.startswith('data-series-'):
                        continue
                    for surface in ('surface', 'surface-muted'):
                        a, b = sorted([lum(value), lum(palette[surface])])
                        self.assertGreaterEqual((b + .05) / (a + .05), 3,
                                                (name, theme, key, surface))

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

    def test_density_selector_can_override_profile_values_in_css(self):
        density_selector = next(selector for selector, _ in self.rules
                                if '[data-density="compact"]' in selector)
        self.assertIn('[data-ui-profile]', density_selector)
        self.assertIn(':not([data-ui-profile])', density_selector)

        profile_selector = next(selector for selector, _ in self.rules
                                if 'data-ui-profile="precision"' in selector)
        # Every selector branch has the html element; counting attributes is
        # enough to prove compact density is not weaker than profile overrides.
        density_specificity = max(branch.count('[') for branch in density_selector.split(','))
        profile_specificity = max(branch.count('[') for branch in profile_selector.split(','))
        self.assertGreaterEqual(density_specificity, profile_specificity)

    def test_profiles_are_explicit_and_unsupported_themes_fall_back(self):
        profiles = self.tokens['profiles']
        self.assertEqual(profiles['enterprise']['supported-themes'], ['light', 'dark'])
        self.assertEqual(profiles['analytics']['supported-themes'], ['dark'])
        self.assertEqual(profiles['analytics']['fallback'], 'enterprise')
        analytics = next(values for selector, values in self.rules
                         if 'data-ui-profile="analytics"' in selector)
        self.assertEqual(analytics, profiles['analytics']['modes']['dark'])
        self.assertNotIn('data-ui-profile="analytics"][data-theme="light"',
                         (ROOT / 'assets' / 'tokens.css').read_text())

    def test_explicit_light_wins_over_legacy_dark_class(self):
        css = (ROOT / 'assets/tokens.css').read_text()
        for selector, _ in self.rules:
            for branch in selector.split(','):
                if 'html.dark' in branch:
                    self.assertIn(':not([data-theme="light"])', branch)

    def test_role_typography_and_state_tokens_are_additive(self):
        common = self.tokens['common']
        self.assertEqual(common['font-body'], '14px')
        self.assertEqual(common['weight-metric'], '700')
        self.assertEqual(common['font-variant-data'], 'tabular-nums')
        self.assertNotEqual(common['weight-metric'], '800')
        for key in ('state-success', 'state-warning', 'state-danger', 'state-info', 'focus-ring'):
            self.assertIn(key, common)
        self.assertTrue(common['state-success'].startswith('var(--ui-'))

    def test_analytics_pairs_meet_contrast_threshold(self):
        def luminance(hex_color):
            channels = [int(hex_color[i:i + 2], 16) / 255 for i in (1, 3, 5)]
            linear = [c / 12.92 if c <= .04045 else ((c + .055) / 1.055) ** 2.4 for c in channels]
            return sum(c * w for c, w in zip(linear, (.2126, .7152, .0722)))

        palette = self.tokens['common'] | self.tokens['profiles']['analytics']['modes']['dark']
        for foreground, background in (('text', 'surface'), ('text-secondary', 'surface'),
                                       ('action-text', 'surface'), ('on-action', 'action-solid')):
            high, low = sorted((luminance(palette[foreground]), luminance(palette[background])), reverse=True)
            self.assertGreaterEqual((high + .05) / (low + .05), 4.5,
                                    (foreground, background))

    def test_profile_cascade_keeps_density_separate(self):
        css = (ROOT / 'assets' / 'tokens.css').read_text()
        profile_selector = next(selector for selector, _ in self.rules
                                if 'data-ui-profile="analytics"' in selector)
        density_selector = next(selector for selector, _ in self.rules
                                if '[data-density="compact"]' in selector)
        self.assertNotIn('data-density', profile_selector)
        self.assertNotIn('data-ui-profile="analytics"', density_selector)
        self.assertIn('Profile cascade: enterprise base -> theme -> optional profile -> density.', css)

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

    def test_precision_is_observable_without_changing_body_size(self):
        enterprise = resolve_config(self.tokens, profile='enterprise', theme='light')
        precision = resolve_config(self.tokens, profile='precision', theme='light')
        self.assertEqual(precision['values']['font-body'], '14px')
        self.assertEqual(precision['values']['font-title'], '24px')
        self.assertNotEqual(precision['values']['weight-page-title'], enterprise['values']['weight-page-title'])
        self.assertNotEqual(precision['values']['radius-panel'], enterprise['values']['radius-panel'])
        self.assertNotEqual(precision['values']['layout-section-gap'], enterprise['values']['layout-section-gap'])
        self.assertNotEqual(precision['values']['surface-muted'], enterprise['values']['surface-muted'])

    def test_explicit_brand_owns_action_semantics_but_not_status_or_series(self):
        analytics = resolve_config(self.tokens, profile='analytics', theme='dark')
        teal = resolve_config(self.tokens, brand='teal', profile='analytics', theme='dark')
        self.assertEqual(analytics['values']['action-text'], '#95B7FF')
        self.assertNotEqual(teal['values']['action-text'], analytics['values']['action-text'])
        self.assertEqual(teal['values']['success'], analytics['values']['success'])
        self.assertEqual(teal['values']['data-series-1'], analytics['values']['data-series-1'])
        broken = copy.deepcopy(self.tokens)
        broken['brands']['teal']['tokens']['success'] = '#00FF00'
        with self.assertRaises(TokenConfigError):
            validate_ownership(broken)

    def test_runtime_contains_every_axis_combination_and_contrast_passes(self):
        runtime = build_runtime_config(self.tokens)
        self.assertEqual(len(runtime['combinations']), 5 * 4 * 2 * 2)
        self.assertEqual(runtime['defaults']['effective'], {
            'brand': 'blue', 'profile': 'enterprise', 'theme': 'light', 'density': 'standard'
        })
        self.assertTrue(any(
            item['requested']['profile'] == 'analytics'
            and item['requested']['theme'] == 'light'
            and item['effective']['profile'] == 'enterprise'
            for item in runtime['combinations']
        ))
        validate_contrast(self.tokens)


if __name__ == "__main__":
    unittest.main()
