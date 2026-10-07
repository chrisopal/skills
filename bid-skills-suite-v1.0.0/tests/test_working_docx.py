"""Customer body typography must survive actual DOCX generation."""
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import build_docx


@unittest.skipUnless(importlib.util.find_spec('docx'), 'Declared optional python-docx not installed')
class WorkingDocxTests(unittest.TestCase):
    def test_customer_font_and_spacing(self):
        from docx import Document
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            spec = {'title': 'Test draft', 'style': {'body_size_pt': 12,
                    'body_line_spacing': 1.5, 'body_east_asia_font': 'SimSun'},
                    'sections': [{'title': 'Chapter', 'paragraphs': ['中文正文']} ]}
            (root / 'spec.json').write_text(json.dumps(spec))
            build_docx.build(root / 'spec.json', root / 'draft.docx', root)
            doc = Document(root / 'draft.docx')
            self.assertEqual(doc.styles['Normal'].font.size.pt, 12)
            self.assertEqual(doc.styles['Normal'].paragraph_format.line_spacing, 1.5)
            self.assertIn('中文正文', '\n'.join(p.text for p in doc.paragraphs))

    def test_invalid_style_fails_before_output(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root/'spec.json').write_text(json.dumps({'title':'draft','sections':[],
                                                     'style':{'body_size_pt': -1}}))
            with self.assertRaises(ValueError):
                build_docx.build(root/'spec.json', root/'draft.docx', root)
            self.assertFalse((root/'draft.docx').exists())

    def test_response_column_widths_survive_in_grid_and_cells(self):
        from docx import Document
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            spec = {'title': '响应表', 'sections': [{'title': '逐项响应', 'tables': [
                {'headers': ['要求', '响应', '状态'], 'rows': [['原文', '较长响应', '待核验']],
                 'widths_cm': [4, 9, 3]}]}]}
            (root/'spec.json').write_text(json.dumps(spec))
            build_docx.build(root/'spec.json', root/'draft.docx', root)
            table = Document(root/'draft.docx').tables[0]
            self.assertFalse(table.autofit)
            for row in table.rows:
                self.assertGreater(row.cells[1].width, row.cells[0].width * 2)
            spec['sections'][0]['tables'][0]['widths_cm'] = [4, 20, 3]
            (root/'invalid.json').write_text(json.dumps(spec))
            with self.assertRaises(ValueError):
                build_docx.build(root/'invalid.json', root/'invalid.docx', root)
            self.assertFalse((root/'invalid.docx').exists())


if __name__ == '__main__':
    unittest.main()
