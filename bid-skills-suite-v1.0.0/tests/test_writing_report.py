import hashlib
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from render_writing_report import outline_html, safe_editor_url, response_html, documents_current


class WritingReportTests(unittest.TestCase):
    def test_nested_order_numbers_and_all_ids_are_preserved(self):
        sections = [
            {'id': 'a', 'parent_id': None, 'number': '一', 'title': '资格'},
            {'id': 'b', 'parent_id': None, 'number': '二', 'title': '技术'},
            {'id': 'a1', 'parent_id': 'a', 'number': '一.1', 'title': '证明'},
            {'id': 'b1', 'parent_id': 'b', 'number': '二.1', 'title': '方案'},
            {'id': 'b11', 'parent_id': 'b1', 'number': '二.1.1', 'title': '集成'},
        ]
        rendered = outline_html(sections, {'b11'})
        self.assertLess(rendered.index('证明'), rendered.index('技术'))
        self.assertIn('1.1', rendered)
        self.assertIn('2.1.1', rendered)
        self.assertNotIn('一.1', rendered)
        self.assertEqual(rendered.count('<details open>'), 3)
        self.assertEqual(rendered.count('data-section-id='), 5)
        self.assertIn('已写草稿', rendered)

    def test_untrusted_title_and_id_are_escaped(self):
        rendered = outline_html([{'id': '<bad>', 'parent_id': None,
                                  'number': '1', 'title': '<script>alert(1)</script>'}])
        self.assertNotIn('<script>', rendered)
        self.assertIn('&lt;script&gt;', rendered)
        self.assertIn('&lt;bad&gt;', rendered)

    def test_editor_url_remains_local_and_has_no_embedded_credentials(self):
        self.assertEqual(safe_editor_url('http://127.0.0.1:8767/'), 'http://127.0.0.1:8767/')
        for url in ('javascript:alert(1)', 'https://evil.test/', 'http://user:key@127.0.0.1:8767/',
                    'http://127.0.0.1:8767/?token=secret'):
            with self.subTest(url=url), self.assertRaises(ValueError):
                safe_editor_url(url)

    def test_response_state_and_limit_are_not_replaced_by_a_default(self):
        rendered = response_html([{'requirement_id': 'R1', 'response': '拟实施',
                                  'fulfillment': 'partial', 'deviation': '接口待核验'}],
                                 {'R1': {'text': '联动要求'}})
        self.assertIn('部分响应', rendered)
        self.assertIn('接口待核验', rendered)
        self.assertNotIn('待复核', rendered)

    def document_fixture(self, project):
        (project / 'artifacts').mkdir()
        for path in ('11-technical-content.json', '13-visuals.json'):
            (project / 'artifacts' / path).write_text('{}')
        with zipfile.ZipFile(project / 'draft.docx', 'w') as archive:
            archive.writestr('[Content_Types].xml',
                '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
                '</Types>')
            archive.writestr('word/document.xml',
                '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"/>')
        (project / 'draft.pdf').write_bytes(b'%PDF-1.7\n%%EOF\n')
        document = {'project_id': 'P1', 'docx': 'draft.docx', 'pdf': 'draft.pdf', 'pages': 1}
        for label, path in (('writing', 'artifacts/11-technical-content.json'),
                            ('visuals', 'artifacts/13-visuals.json'),
                            ('docx', 'draft.docx'), ('pdf', 'draft.pdf')):
            document[label + '_sha256'] = hashlib.sha256((project / path).read_bytes()).hexdigest()
        return document

    def test_documents_require_current_inputs_and_project(self):
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp)
            document = self.document_fixture(project)
            self.assertTrue(documents_current(project, document, 'P1'))
            self.assertFalse(documents_current(project, document, 'P2'))
            (project / 'artifacts/11-technical-content.json').write_text('{"revision":2}')
            self.assertFalse(documents_current(project, document, 'P1'))

    def test_documents_reject_wrong_extensions_even_with_matching_hashes(self):
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp)
            document = self.document_fixture(project)
            for kind in ('docx', 'pdf'):
                file = project / document[kind]
                wrong = file.with_suffix('.txt')
                wrong.write_bytes(file.read_bytes())
                with self.subTest(kind=kind):
                    self.assertFalse(documents_current(project, {**document, kind: wrong.name}, 'P1'))

    def test_documents_reject_fake_content_even_with_matching_hashes(self):
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp)
            document = self.document_fixture(project)
            for kind in ('docx', 'pdf'):
                original = (project / document[kind]).read_bytes()
                (project / document[kind]).write_bytes(b'not a document')
                altered = {**document, kind + '_sha256': hashlib.sha256(b'not a document').hexdigest()}
                with self.subTest(kind=kind):
                    self.assertFalse(documents_current(project, altered, 'P1'))
                (project / document[kind]).write_bytes(original)
            with zipfile.ZipFile(project / 'draft.docx', 'w') as archive:
                archive.writestr('word/document.xml', '<document/>')
            document['docx_sha256'] = hashlib.sha256((project / 'draft.docx').read_bytes()).hexdigest()
            self.assertFalse(documents_current(project, document, 'P1'))

    def test_documents_require_positive_integer_page_count(self):
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp)
            document = self.document_fixture(project)
            for pages in (None, 0, -1, True, '6', 1.5):
                with self.subTest(pages=pages):
                    self.assertFalse(documents_current(project, {**document, 'pages': pages}, 'P1'))


if __name__ == '__main__':
    unittest.main()
