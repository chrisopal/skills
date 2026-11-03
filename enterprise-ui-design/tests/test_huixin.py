"""Behavioral invariants for the opt-in Huixin three-layer extension."""
import copy
import itertools
import json
from pathlib import Path
import re
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from resolve_tokens import (load_tokens, resolve_config, validate_tokens,
                            validate_contrast, contrast_ratio, TokenConfigError)
from generate_tokens import render_css


class HuixinLayers(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tokens = load_tokens()

    def test_palette_changes_only_colors_and_color_recipes(self):
        t = self.tokens
        recipes = set(t['layer-contract']['color-recipes'])
        for density in ('standard', 'compact'):
            base = resolve_config(t, profile='huixin', brand='huixin', density=density)
            structural = set(t['profiles']['huixin']['common']) - recipes
            for brand, mode in itertools.product(t['brands'], t['modes']):
                other = resolve_config(t, profile='huixin', brand=brand, theme=mode, density=density)
                for key in structural:
                    self.assertEqual(base['values'][key], other['values'][key], (brand,mode,density,key))
                for section in ('layout', 'components'):
                    # Focus color may change; component shape and all layout recipes may not.
                    a, b = copy.deepcopy(base[section]), copy.deepcopy(other[section])
                    if section == 'components':
                        a['button'].pop('focus'); b['button'].pop('focus')
                    self.assertEqual(a,b,(brand,mode,section))

    def test_canonical_geometry_and_profile_density(self):
        normal=resolve_config(self.tokens,profile='huixin',brand='huixin')
        compact=resolve_config(self.tokens,profile='huixin',brand='huixin',density='compact')
        for key,value in {'font-body':'14px','font-title':'28px','sidebar-width':'232px',
                          'header-height':'70px','layout-page-inset-inline':'28px',
                          'chart-donut-size':'200px','table-row-height':'56px'}.items():
            self.assertEqual(normal['values'][key],value)
        self.assertEqual(normal['components']['button']['height'],'40px')
        self.assertEqual(compact['components']['button']['height'],'32px')
        self.assertEqual(compact['components']['table']['rowHeight'],'44px')
        self.assertEqual(resolve_config(self.tokens,density='compact')['components']['button']['height'],'28px')
        css=render_css(self.tokens)
        self.assertIn('[data-ui-profile="huixin"][data-density="compact"]',css)

    def test_color_in_geometry_and_dimension_in_theme_rejected(self):
        for section,key,value in [('common','radius-panel','#123456'),('modes','light','bad')]:
            t=copy.deepcopy(self.tokens)
            if section=='common':t['profiles']['huixin']['common'][key]=value
            else:t['profiles']['huixin']['modes']['light']['sidebar-width']='240px'
            with self.assertRaises(TokenConfigError):validate_tokens(t)
        t=copy.deepcopy(self.tokens)
        t['profiles']['huixin']['modes']['light']['shadow-panel']='0 6px 22px rgba(0,0,0,0.1)'
        with self.assertRaises(TokenConfigError):validate_tokens(t)

    def test_duplicate_json_and_competing_aliases_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'duplicate.json'
            path.write_text('{"common":{"font-body":"14px","font-body":"12px"}}')
            with self.assertRaises(TokenConfigError):load_tokens(path)
        for key in ('row-height','row-data-height','hx-chart-donut-size'):
            t=copy.deepcopy(self.tokens);t['profiles']['huixin']['common'][key]='52px'
            with self.assertRaises(TokenConfigError):validate_tokens(t)
        self.assertFalse({'row-height', 'row-data-height', 'row-data-height-compact', 'hx-chart-donut-size'}
                         & set(self.tokens['profiles']['huixin']['common']))

    def test_theme_and_density_cannot_take_business_or_framework_ownership(self):
        t=copy.deepcopy(self.tokens)
        t['brands']['violet']['tokens']['success']='#800080'
        with self.assertRaises(TokenConfigError):validate_tokens(t)
        t=copy.deepcopy(self.tokens)
        t['brands']['fourth']=copy.deepcopy(t['brands']['indigo'])
        t['brands']['fourth']['tokens']['focus-ring']='12px solid #354E9E'
        with self.assertRaises(TokenConfigError):validate_tokens(t)
        for value in ({'font-body':'12px'}, {'no-such-token':'4px'}):
            t=copy.deepcopy(self.tokens);t['profiles']['huixin']['densities']['compact']=value
            with self.assertRaises(TokenConfigError):validate_tokens(t)

    def test_declared_pairs_and_every_series_meet_contrast(self):
        warnings = validate_contrast(self.tokens)
        self.assertTrue(any(item['foreground'] == 'border-control' for item in warnings))
        exceptions = {
            (item['profile'], item['theme'], item['foreground'], item['background']): item
            for item in self.tokens['layer-contract']['contrast-exceptions']
        }
        for mode in ('light','dark'):
            v=resolve_config(self.tokens,profile='huixin',brand='huixin',theme=mode)['values']
            for i in range(1,8):
                for surface in ('surface','surface-muted'):
                    ratio = contrast_ratio(v[f'data-series-{i}'], v[surface])
                    if ratio < 3:
                        exception = exceptions[('huixin', mode, f'data-series-{i}', surface)]
                        self.assertGreaterEqual(ratio + 0.0001, exception['approvedRatio'])
                    else:
                        self.assertGreaterEqual(ratio, 3)
        t=copy.deepcopy(self.tokens)
        t['brands']['violet']['tokens']['action-end']='#CCCCEE'
        with self.assertRaises(TokenConfigError):validate_contrast(t)
        t=copy.deepcopy(self.tokens)
        t['profiles']['huixin']['modes']['light']['text-tertiary']='#8194A0'
        with self.assertRaises(TokenConfigError):validate_contrast(t)

    def test_source_palette_and_axis_ownership_are_exact(self):
        light = self.tokens['profiles']['huixin']['modes']['light']
        dark = self.tokens['profiles']['huixin']['modes']['dark']
        self.assertEqual(light['border-control'], '#C3DAE6')
        self.assertEqual(light['border-strong'], '#8CB6C9')
        self.assertEqual(light['text-secondary'], '#637B88')
        self.assertEqual(dark['border-control'], '#406E86')
        self.assertEqual(self.tokens['brands']['huixin']['tokens']['action-end'], '#007F96')
        self.assertEqual(self.tokens['brands']['huixin']['modes']['dark']['action-end'], '#007F96')

    def test_source_sprite_is_byte_identical_to_supplied_v2(self):
        import hashlib
        source = Path('/Users/guojiexie/Downloads/artifact-template-huixin-glass-ui/assets/v2/icons.svg')
        if source.exists():
            digest = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
            self.assertEqual(digest(ROOT / 'assets/huixin-icons.svg'), digest(source))

    def test_style_consumers_use_defined_tokens_and_no_literal_palette(self):
        v=resolve_config(self.tokens,profile='huixin',brand='huixin')['values']
        files=[ROOT/'assets/huixin-framework.css',ROOT/'assets/huixin-components.css',ROOT/'assets/reference-huixin/app.css']
        for path in files:
            if not path.exists(): self.fail(f'missing maintained consumer: {path}')
            css=path.read_text()
            self.assertNotRegex(css,r'#[0-9a-fA-F]{3,8}\b|rgba?\(')
            self.assertFalse(set(re.findall(r'var\(--ui-([\w-]+)',css))-set(v),path.name)

    def test_source_icons_are_reusable_symbols(self):
        import xml.etree.ElementTree as ET
        tree=ET.parse(ROOT/'assets/huixin-icons.svg')
        ids=[e.attrib.get('id') for e in tree.iter() if e.tag.endswith('symbol')]
        self.assertEqual(len(ids),35)
        self.assertEqual(len(ids),len(set(ids)))


if __name__=='__main__': unittest.main()
