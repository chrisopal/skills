"""Contract tests for offline review rendering; browser visuals are checked separately."""
import hashlib
import json
import re
from pathlib import Path
import tempfile
import unittest
import xml.etree.ElementTree as ET

from render_review_workbench import architecture_graph, build, drawio, markdown, render, validate

TOKENS = {'common': {'brand': '#1677FF'}, 'modes': {'light': {'text': '#000000'}, 'dark': {'text': '#FFFFFF'}}}


class WorkbenchTests(unittest.TestCase):
    def test_untrusted_source_cannot_create_elements(self):
        attack = '</script><script>alert(1)</script><img src=x onerror=alert(1)>'
        pack = {'artifact_header': {'project_id': 'p', 'status': attack}, 'processes': [{'id': 'x', 'level': 1, 'name': attack}]}
        slides = {'slides': [{'slide_id': 'x', 'title': attack, 'supporting_points': [attack]}]}
        page = render(pack, '# Report\n\n' + attack, slides, TOKENS, {})
        self.assertNotIn('<img src=x', page)
        self.assertNotIn('<script>alert(1)', page)
        self.assertIn('&lt;img', page)
        self.assertEqual(page.count('<script'), 2)

    def test_markdown_links_are_safe_and_table_preserved(self):
        result = markdown('[bad](javascript:alert)\n\n|A|B|\n|--|--|\n|1|2|')
        self.assertNotIn('href="javascript:', result)
        self.assertIn('<th>A</th>', result)
        self.assertIn('<td>2</td>', result)

    def test_missing_optional_sources_and_hashes(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            pack, tokens, out = root/'pack.json', root/'tokens.json', root/'index.html'
            pack.write_text(json.dumps({'artifact_header': {'status':'draft', 'human_gate':'pending', 'data_status':'assumed'}}))
            tokens.write_text(json.dumps(TOKENS))
            build(pack, root/'missing.md', None, tokens, out)
            page = out.read_text()
            self.assertIn('未提供报告', page)
            self.assertIn('未提供PPT 内容包', page)
            self.assertIn('assumed', page)
            self.assertIn('pending', page)
            self.assertIn(hashlib.sha256(pack.read_bytes()).hexdigest(), page)
            self.assertIn('"status": "missing"', page)

    def test_invalid_input_preserves_existing_output(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            pack, tokens, out = root/'pack.json', root/'tokens.json', root/'index.html'
            tokens.write_text(json.dumps(TOKENS))
            pack.write_text('{bad')
            out.write_text('previous verified view')
            with self.assertRaises(ValueError):
                build(pack, None, None, tokens, out)
            self.assertEqual(out.read_text(), 'previous verified view')

    def test_process_hierarchy_preserves_all_nodes(self):
        nodes = [{'id':str(i), 'level':i, 'parent_id':str(i-1) if i>1 else None} for i in range(1,5)]
        result = render({'processes':nodes}, '', {}, TOKENS, {})
        self.assertEqual(result.count('data-process-id='), 4)
        nodes[3]['parent_id'] = 'missing'
        with self.assertRaises(ValueError):
            validate({'processes':nodes}, {})

    def test_duplicate_slide_ids_rejected(self):
        with self.assertRaises(ValueError):
            validate({}, {'slides':[{'slide_id':'a'}, {'slide_id':'a'}]})

    def test_drawio_has_exact_source_relationships(self):
        source = {'applications':[{'id':'AA-1','name':'<&>', 'process_ids':['P1'], 'information_ids':['IA1'], 'technology_ids':['TA1']}]}
        model = ET.fromstring(drawio(source))
        edges = model.findall('.//mxCell[@edge="1"]')
        self.assertEqual([(e.attrib['source'], e.attrib['target']) for e in edges], [('AA-1','P1'), ('AA-1','IA1'), ('AA-1','TA1')])
        self.assertTrue(all(e.find('mxGeometry') is not None for e in edges))

    def test_css_tokens_cannot_break_out(self):
        bad = {'common': {'brand': '</style><script>alert(1)</script>'}, 'modes': TOKENS['modes']}
        with self.assertRaises(ValueError):
            render({}, '', {}, bad, {})

    def test_focused_graph_uses_only_explicit_relations(self):
        app = {'id':'AA1', 'name':'应用', 'process_ids':['P1'], 'information_ids':['IA1'], 'technology_ids':['TA1']}
        graph = architecture_graph(app, {'P1':{'name':'订单确认'}, 'IA1':{'name':'订单信息'}, 'TA1':{'name':'运行服务'}})
        self.assertIn('订单确认', graph)
        self.assertIn('订单信息', graph)
        self.assertIn('运行服务', graph)
        self.assertEqual(graph.count('marker-end='), 3)
        self.assertIn('role="img"', graph)
        self.assertIn('未推导域间关系', graph)

    def test_output_cannot_overwrite_input(self):
        with tempfile.TemporaryDirectory() as folder:
            pack, tokens = Path(folder)/'pack.json', Path(folder)/'tokens.json'
            pack.write_text('{}')
            tokens.write_text(json.dumps(TOKENS))
            with self.assertRaises(ValueError):
                build(pack, None, None, tokens, pack)
            self.assertEqual(pack.read_text(), '{}')

    def test_original_downloads_preserve_exact_source_bytes(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            pack, report, tokens, out = root/'pack.json', root/'report.md', root/'tokens.json', root/'index.html'
            raw = b'{ "artifact_header": {"project_id":"p", "artifact_id":"a", "version":"1"} }\r\n'
            pack.write_bytes(raw)
            report.write_text('---\n{"artifact_id":"r","version":"2"}\n---\n# Report')
            tokens.write_text(json.dumps(TOKENS))
            build(pack, report, None, tokens, out)
            payload = json.loads(re.search(r'<script id="review-data" type="application/json">(.*?)</script>', out.read_text()).group(1))
            self.assertEqual(payload['originals']['pack'].encode(), raw)
            self.assertEqual(payload['metadata']['upstream_artifact_ids'], ['a', 'r'])
            self.assertEqual(payload['metadata']['source_versions']['report']['version'], '2')


if __name__ == '__main__':
    unittest.main()
