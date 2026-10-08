"""Run the bundled new engine and audit actual SVG/PNG and style changes."""
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import diagram_tools
from diagram_fixtures import corpus

class EnterpriseDiagramTests(unittest.TestCase):
    def test_reference_corpus_real_cli_renders_and_retains_source(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            for name,spec in corpus().items():
                with self.subTest(name=name):
                    source=root/(name+'.diagram.json')
                    source.write_text(json.dumps(spec,ensure_ascii=False))
                    before=diagram_tools.digest(source)
                    receipt=diagram_tools.render(root,source,root/(name+'.svg'),'blueprint',base_sha256=before)
                    xml=ET.parse(root/(name+'.svg')).getroot()
                    self.assertEqual(receipt['engine'],'blueprint')
                    self.assertEqual(receipt['source_sha256'],before)
                    self.assertEqual(receipt['diagram_style']['theme'],'reference')
                    self.assertEqual(receipt['diagram_style']['layout'],spec['layout'])
                    self.assertEqual(len(receipt['diagram_style']['nodes']),len(spec['nodes']))
                    self.assertTrue(all(e['safe'] for e in receipt['diagram_style']['edges']))
                    self.assertGreater(len(list(xml.iter())),len(spec['nodes']))
                    self.assertEqual(diagram_tools.digest(source),before)

    def test_each_palette_changes_output_geometry_stays_stable(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); geometry=None; hashes=set()
            for theme in ('reference','blue','teal','green','slate','monochrome'):
                spec=corpus()['flow-branch'];spec['theme']=theme
                source=root/(theme+'.diagram.json');source.write_text(json.dumps(spec))
                value=diagram_tools.render(root,source,root/(theme+'.svg'),'blueprint',base_sha256=diagram_tools.digest(source))
                if geometry is None:geometry=value['diagram_style']['nodes']
                self.assertEqual(geometry,value['diagram_style']['nodes'])
                hashes.add(value['output_sha256'])
            self.assertEqual(len(hashes),6)

    def test_invalid_spec_does_not_publish_and_theme_change_is_stale(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);source=root/'bad.diagram.json'
            spec=corpus()['flow-branch'];spec['edges'][0]['to']='missing'
            source.write_text(json.dumps(spec))
            with self.assertRaises(diagram_tools.DiagramError):
                diagram_tools.render(root,source,root/'bad.svg','blueprint',base_sha256=diagram_tools.digest(source))
            self.assertFalse((root/'bad.svg').exists())
            self.assertFalse((root/'bad.svg.receipt.json').exists())
            spec=corpus()['flow-branch'];source.write_text(json.dumps(spec));before=diagram_tools.digest(source)
            spec['theme']='teal';source.write_text(json.dumps(spec))
            with self.assertRaisesRegex(diagram_tools.DiagramError,'版本冲突'):
                diagram_tools.render(root,source,root/'changed.svg','blueprint',base_sha256=before)

    def test_oversized_png_is_blocked_before_raster_allocation(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);source=root/'large.diagram.json'
            spec=corpus()['long-text'];spec['nodes']=spec['nodes'][:1];spec['nodes'][0]['row']=128;spec['edges']=[]
            source.write_text(json.dumps(spec))
            with self.assertRaisesRegex(diagram_tools.DiagramError,'过大'):
                diagram_tools.render(root,source,root/'large.png','blueprint',base_sha256=diagram_tools.digest(source))
            self.assertFalse((root/'large.png').exists())

    @unittest.skipUnless(importlib.util.find_spec('cairosvg'), 'Host has no optional CairoSVG')
    def test_png_is_real_and_missing_rasterizer_is_explicit_failure(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);source=root/'events.diagram.json'
            source.write_text(json.dumps(corpus()['sequence-self']))
            receipt=diagram_tools.render(root,source,root/'events.png','blueprint',base_sha256=diagram_tools.digest(source))
            self.assertEqual((root/'events.png').read_bytes()[:8],b'\x89PNG\r\n\x1a\n')
            self.assertIn('cairosvg',receipt['raster_command'])
            with patch.object(diagram_tools.importlib.util,'find_spec',return_value=None):
                with self.assertRaisesRegex(diagram_tools.DiagramError,'CairoSVG'):
                    diagram_tools.render(root,source,root/'missing.png','blueprint',base_sha256=diagram_tools.digest(source))
            self.assertFalse((root/'missing.png').exists())
            self.assertFalse((root/'missing.png.receipt.json').exists())

    def test_expected_theme_is_bound_before_render_and_recorded(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); source = root/'theme.diagram.json'
            spec = corpus()['flow-branch']; spec['theme'] = 'slate'
            source.write_text(json.dumps(spec))
            with patch.object(diagram_tools.subprocess, 'run') as runner:
                with self.assertRaisesRegex(diagram_tools.DiagramError, '计划不一致'):
                    diagram_tools.render(root, source, root/'wrong.svg', 'blueprint',
                        base_sha256=diagram_tools.digest(source), expected_theme='green')
                runner.assert_not_called()
            self.assertFalse((root/'wrong.svg').exists())
            receipt = diagram_tools.render(root, source, root/'correct.svg', 'blueprint',
                base_sha256=diagram_tools.digest(source), expected_theme='slate')
            self.assertEqual(receipt['expected_theme'], 'slate')
            self.assertEqual(receipt['diagram_style']['theme'], 'slate')

    def test_invalid_json_is_explicit_failure_without_output(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); source = root/'invalid.diagram.json'
            source.write_text('{invalid')
            with self.assertRaisesRegex(diagram_tools.DiagramError, '有效'):
                diagram_tools.render(root, source, root/'invalid.svg', 'blueprint',
                    base_sha256=diagram_tools.digest(source))
            self.assertFalse((root/'invalid.svg').exists())
