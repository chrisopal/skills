import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

MODULE_PATH = Path(__file__).resolve().parents[1] / 'scripts/diagram_tools.py'
spec = importlib.util.spec_from_file_location('diagram_tools', MODULE_PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class DiagramToolsTests(unittest.TestCase):
    def test_routes_types_and_preserves_user_selection(self):
        available = {name: {'available': True} for name in ('drawio', 'plantuml', 'mermaid')}
        self.assertEqual(module.plan({}, 'architecture', available)['engine'], 'drawio')
        self.assertEqual(module.plan({}, 'sequence', available)['engine'], 'plantuml')
        self.assertEqual(module.plan({}, 'flow', available)['engine'], 'mermaid')
        self.assertEqual(module.plan({}, 'flow', available, complex_flow=True)['engine'], 'drawio')
        self.assertEqual(module.plan({'diagram_engine': 'mermaid'}, 'architecture', available)
                         ['engine'], 'mermaid')

    def test_unavailable_explicit_tool_is_blocked_auto_records_fallback(self):
        available = {'drawio': {'available': False}, 'mermaid': {'available': True}}
        self.assertEqual(module.plan({'diagram_engine': 'drawio'}, 'architecture', available)
                         ['status'], 'blocked')
        result = module.plan({}, 'architecture', available)
        self.assertEqual(result['engine'], 'mermaid')
        self.assertTrue(result['fallback_reason'])

    def test_blueprint_selection_keeps_theme_and_existing_auto_rules(self):
        available = {name: {'available': True} for name in ('drawio', 'plantuml', 'mermaid', 'blueprint')}
        for kind, layout in [('architecture', 'layered'), ('network', 'network'),
                             ('flow', 'flow'), ('sequence', 'sequence'), ('swimlane', 'swimlane')]:
            result = module.plan({'diagram_engine': 'blueprint', 'diagram_theme': 'green',
                'architecture_layers': 8}, kind, available)
            self.assertEqual(result['engine'], 'blueprint')
            self.assertEqual(result['diagram_theme'], 'green')
            self.assertEqual(result['layout_template'], layout)
        self.assertEqual(module.plan({}, 'architecture', available)['engine'], 'drawio')
        self.assertEqual(module.plan({'diagram_engine': 'drawio'}, 'architecture', available)['engine'], 'drawio')

    def test_render_publishes_valid_file_and_receipt_without_changing_source(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = root / 'diagram.mmd'
            source.write_text('flowchart LR\n A-->B', encoding='utf-8')
            original = module.digest(source)
            def run(command, **kwargs):
                target = Path(command[command.index('-o') + 1])
                target.write_text('<svg xmlns="http://www.w3.org/2000/svg" width="10" '
                                  'height="10"><text>测试</text></svg>', encoding='utf-8')
                return type('Result', (), {'returncode': 0, 'stdout': b'', 'stderr': b''})()
            with patch.object(module, 'command_for', return_value=['mmdc']), \
                    patch.object(module.subprocess, 'run', side_effect=run):
                result = module.render(root, source, root / 'result.svg', 'mermaid',
                                       base_sha256=original)
            self.assertEqual(module.digest(source), original)
            self.assertEqual(result['state'], 'rendered')
            receipt = json.loads((root / 'result.svg.receipt.json').read_text())
            self.assertEqual(receipt['source_sha256'], original)
            self.assertEqual(receipt['output_sha256'], module.digest(root / 'result.svg'))

    def test_missing_output_and_changed_source_are_not_published(self):
        for change in (False, True):
            with self.subTest(change=change), tempfile.TemporaryDirectory() as folder:
                root = Path(folder)
                source = root / 'diagram.mmd'
                source.write_text('flowchart LR\n A-->B')
                original = module.digest(source)
                def run(command, **kwargs):
                    if change:
                        source.write_text('flowchart LR\n A-->C')
                        Path(command[command.index('-o') + 1]).write_text('<svg/>')
                    return type('Result', (), {'returncode': 0, 'stdout': b'', 'stderr': b''})()
                with patch.object(module, 'command_for', return_value=['mmdc']), \
                        patch.object(module.subprocess, 'run', side_effect=run), \
                        self.assertRaises(module.DiagramError):
                    module.render(root, source, root / 'result.svg', 'mermaid',
                                  base_sha256=original)
                self.assertFalse((root / 'result.svg').exists())
                self.assertFalse((root / 'result.svg.receipt.json').exists())

    def test_refuses_overwrite_escape_and_stale_hash_before_tool_call(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder) / 'project'
            root.mkdir()
            source = root / 'diagram.mmd'
            source.write_text('flowchart LR\n A-->B')
            target = root / 'result.svg'
            target.write_text('preserve existing bytes')
            with patch.object(module.subprocess, 'run') as run:
                for output, base in ((target, None), (root.parent / 'escape.svg', None),
                                     (root / 'new.svg', '0' * 64)):
                    with self.assertRaises(module.DiagramError):
                        module.render(root, source, output, 'mermaid', base_sha256=base)
                run.assert_not_called()
            self.assertEqual(target.read_text(), 'preserve existing bytes')

    def test_png_and_svg_validation_and_plantuml_error_diagram(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / 'bad.svg'
            for content in ('<html>error</html>', '<svg><text>Syntax Error?</text></svg>',
                            '<svg/>', '<svg width="10" height="10"/>'):
                target.write_text(content)
                with self.assertRaises(module.DiagramError):
                    module.validate_image(target, 'plantuml')
            target = Path(folder) / 'bad.png'
            target.write_bytes(b'not a png')
            with self.assertRaises(module.DiagramError):
                module.validate_image(target, 'drawio')
            target.write_bytes(b'\x89PNG\r\n\x1a\n' + b'\0'*8 + b'\0\0\0\1'*2 + b'\0'*9)
            with self.assertRaises(module.DiagramError):
                module.validate_image(target, 'drawio')

    def test_invalid_layout_layers_and_missing_base_are_rejected(self):
        for settings in ({'layout_template': 'bogus'}, {'architecture_layers': 0},
                         {'architecture_layers': True}, {'architecture_layers': '4'}):
            with self.assertRaises(module.DiagramError):
                module.plan(settings, 'architecture')
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = root / 'diagram.mmd'
            source.write_text('flowchart LR\n A-->B')
            with patch.object(module.subprocess, 'run') as run:
                for base in (None, '', 'ABC', 'A'*64):
                    with self.assertRaises(module.DiagramError):
                        module.render(root, source, root/'out.svg', 'mermaid', base_sha256=base)
                run.assert_not_called()

    def test_source_change_during_validation_is_not_published(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = root / 'diagram.mmd'
            source.write_text('flowchart LR\n A-->B')
            base = module.digest(source)
            def run(command, **kwargs):
                snapshot = Path(command[command.index('-i')+1])
                self.assertNotEqual(snapshot, source)
                self.assertEqual(module.digest(snapshot), base)
                Path(command[command.index('-o')+1]).write_text('mock output')
                return type('Result', (), {'returncode': 0, 'stdout': b'', 'stderr': b''})()
            def validate(*args):
                source.write_text('flowchart LR\n A-->C')
            with patch.object(module, 'command_for', return_value=['mmdc']), \
                    patch.object(module.subprocess, 'run', side_effect=run), \
                    patch.object(module, 'validate_image', side_effect=validate), \
                    self.assertRaises(module.DiagramError):
                module.render(root, source, root/'out.svg', 'mermaid', base_sha256=base)
            self.assertFalse((root/'out.svg').exists())
            self.assertFalse((root/'out.svg.receipt.json').exists())


if __name__ == '__main__':
    unittest.main()
