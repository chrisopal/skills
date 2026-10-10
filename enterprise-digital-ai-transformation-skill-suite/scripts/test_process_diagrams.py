"""Diagram relationship and reusable-engine integration contracts."""
import json
from pathlib import Path
import tempfile
import unittest
import xml.etree.ElementTree as ET

from process_diagrams import DEFAULT_ENGINE, diagram_files, diagrams_html, render_process_diagrams, specs_for_processes
from render_review_workbench import build


def fixture():
    return [
        {'id': 'domain', 'name': '订单交付', 'level': 1, 'parent_id': None, 'status': 'assumed'},
        {'id': 'process', 'name': '订单处理', 'level': 2, 'parent_id': 'domain'},
        {'id': 'activity', 'name': '订单确认', 'level': 3, 'parent_id': 'process'},
        {'id': 'second', 'name': '确认结果', 'level': 4, 'parent_id': 'activity'},
        {'id': 'first', 'name': '检查输入', 'level': 4, 'parent_id': 'activity'},
    ]


class ProcessDiagramTests(unittest.TestCase):
    def test_hierarchy_edges_are_parent_containment_not_sequence(self):
        nodes = fixture()
        diagram = specs_for_processes(nodes)[0]
        self.assertEqual({n['id'] for n in diagram['spec']['nodes']}, {n['id'] for n in nodes})
        self.assertEqual({(e['from'], e['to'], e['label']) for e in diagram['spec']['edges']},
                         {(n['parent_id'], n['id'], '包含') for n in nodes if n['parent_id']})
        self.assertEqual(diagram['flows'][0]['spec']['edges'], [])
        self.assertTrue(all(n['badge'] in ('L1', 'L2', 'L3', 'L4') for n in diagram['spec']['nodes']))
        self.assertIn('状态：assumed', next(n for n in diagram['spec']['nodes'] if n['id'] == 'domain')['description'])

    def test_explicit_order_wins_over_input_order_and_is_deduplicated(self):
        nodes = fixture()
        nodes[-1]['downstream_process_ids'] = ['second', 'second']
        nodes[-2]['upstream_process_ids'] = ['first']
        edges = specs_for_processes(nodes)[0]['flows'][0]['spec']['edges']
        self.assertEqual(edges, [{'from': 'first', 'to': 'second', 'label': '后续'}])

    def test_upstream_only_relation_is_supported(self):
        nodes = fixture()
        nodes[-2]['upstream_process_ids'] = ['first']
        self.assertEqual(specs_for_processes(nodes)[0]['flows'][0]['spec']['edges'][0]['from'], 'first')

    def test_dangling_and_contradictory_relations_fail(self):
        nodes = fixture()
        nodes[-1]['downstream_process_ids'] = ['missing']
        with self.assertRaisesRegex(ValueError, 'invalid related L4'):
            specs_for_processes(nodes)
        nodes[-1]['downstream_process_ids'] = ['second']
        nodes[-2]['upstream_process_ids'] = []
        with self.assertRaisesRegex(ValueError, 'Inconsistent'):
            specs_for_processes(nodes)

    def test_cross_parent_reference_keeps_external_endpoint(self):
        nodes = fixture()
        nodes.extend([{'id': 'other-activity', 'level': 3, 'parent_id': 'process'},
                      {'id': 'external', 'level': 4, 'parent_id': 'other-activity'}])
        nodes[-3]['downstream_process_ids'] = ['external']
        flow = specs_for_processes(nodes)[0]['flows'][0]['spec']
        self.assertIn('external', {n['id'] for n in flow['nodes']})
        self.assertEqual(flow['edges'], [{'from': 'first', 'to': 'external', 'label': '后续'}])

    def test_missing_engine_is_explicit_and_does_not_write_output(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            pack, tokens, out = root/'pack.json', root/'tokens.json', root/'index.html'
            pack.write_text(json.dumps({'processes': fixture()}))
            tokens.write_text(json.dumps({'common': {}, 'modes': {'light': {}, 'dark': {}}}))
            out.write_text('old output')
            with self.assertRaisesRegex(ValueError, '--diagram-engine'):
                build(pack, None, None, tokens, out, root/'missing.py')
            self.assertEqual(out.read_text(), 'old output')
            self.assertFalse((root/'diagrams').exists())

    @unittest.skipUnless(DEFAULT_ENGINE.is_file(), 'Sibling enterprise-diagrams not installed')
    def test_real_engine_svg_is_safe_isolated_and_sources_are_editable(self):
        nodes = fixture()
        nodes[0]['name'] = '<script>订单</script>'
        nodes[-1]['downstream_process_ids'] = ['second']
        domains = render_process_diagrams(nodes)
        for item in [domains[0]] + domains[0]['flows']:
            self.assertTrue(all(e['safe'] for e in item['rendered']['edges']))
            root = ET.fromstring(item['rendered']['svg'])
            self.assertEqual(root.tag, '{http://www.w3.org/2000/svg}svg')
            self.assertIsNone(root.find('.//{http://www.w3.org/2000/svg}script'))
        page = diagrams_html(domains)
        self.assertEqual(page.count('data:image/svg+xml;base64,'), 2)
        self.assertNotIn('<svg', page)
        self.assertNotIn('<script>订单', page)
        files = diagram_files(domains, {'project_id': 'p', 'data_status': 'assumed'})
        manifest = json.loads(files['manifest.json'])
        self.assertEqual(manifest['artifact_header']['data_status'], 'assumed')
        schema = json.loads((Path(__file__).resolve().parents[1] / 'shared/schemas/artifact-header.schema.json').read_text())
        self.assertTrue(set(schema['required']) <= manifest['artifact_header'].keys())
        self.assertEqual(manifest['artifact_header']['architecture_domains'], ['BA'])
        self.assertEqual(len(manifest['diagrams']), 2)
        for item in manifest['diagrams']:
            self.assertEqual(json.loads(files[item['spec']])['theme'], 'blue')


if __name__ == '__main__':
    unittest.main()
