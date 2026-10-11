import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile


SCRIPT = Path(__file__).resolve().parents[1] / 'skills/presales-source-intake/scripts/extract.py'
NS = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'


class ExtractTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.out = self.root / 'output.json'

    def run_extract(self, source, env=None, out=None):
        result = subprocess.run([sys.executable, str(SCRIPT), str(source), '--out', str(out or self.out)],
                                capture_output=True, text=True, env=env)
        data = json.loads(self.out.read_text()) if self.out.exists() else None
        return result, data

    def docx(self, parts):
        source = self.root / 'sample.docx'
        with zipfile.ZipFile(source, 'w', zipfile.ZIP_DEFLATED) as archive:
            archive.writestr('[Content_Types].xml',
                             '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                             '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
                             '<Default Extension="xml" ContentType="application/xml"/>'
                             '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
                             '</Types>')
            archive.writestr('_rels/.rels',
                             '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                             '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>'
                             '</Relationships>')
            for name, body in parts.items():
                archive.writestr(name, body)
        return source

    def test_docx_preserves_paragraph_table_and_auxiliary_part_locations(self):
        source = self.docx({
            'word/document.xml': f'<w:document xmlns:w="{NS}"><w:body><w:p><w:r><w:t>客户原文</w:t></w:r></w:p><w:tbl><w:tr><w:tc><w:p><w:r><w:t>参数 A</w:t></w:r></w:p></w:tc><w:tc><w:p><w:r><w:t>10</w:t></w:r></w:p></w:tc></w:tr></w:tbl></w:body></w:document>',
            'word/header1.xml': f'<w:hdr xmlns:w="{NS}"><w:p><w:r><w:t>页眉</w:t></w:r></w:p></w:hdr>',
            'word/footer1.xml': f'<w:ftr xmlns:w="{NS}"><w:p><w:r><w:t>页脚</w:t></w:r></w:p></w:ftr>',
            'word/footnotes.xml': f'<w:footnotes xmlns:w="{NS}"><w:footnote w:id="2"><w:p><w:r><w:t>脚注</w:t></w:r></w:p></w:footnote></w:footnotes>',
        })
        result, data = self.run_extract(source)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(data['hash'], hashlib.sha256(source.read_bytes()).hexdigest())
        self.assertEqual(data['filename'], 'sample.docx')
        cells = [s for s in data['segments'] if s['locator'].get('table') == 1]
        self.assertEqual([s['text'] for s in cells], ['参数 A', '10'])
        self.assertEqual([s['locator']['column'] for s in cells], [1, 2])
        self.assertTrue(all(s['locator']['row'] == 1 for s in cells))
        self.assertEqual({s['locator']['part'] for s in data['segments']},
                         {'word/document.xml', 'word/header1.xml', 'word/footer1.xml', 'word/footnotes.xml'})
        self.assertEqual(data['visual_review_status'], 'pending')

    def test_docx_warns_on_images_textboxes_and_revisions(self):
        source = self.docx({'word/document.xml': f'<w:document xmlns:w="{NS}"><w:body><w:p><w:ins><w:r><w:t>修订</w:t></w:r></w:ins><w:txbxContent><w:p><w:r><w:t>框内</w:t></w:r></w:p></w:txbxContent></w:p></w:body></w:document>', 'word/media/image1.png': b'image'})
        result, data = self.run_extract(source)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(data['read_status'], 'partial')
        warnings = ' '.join(data['warnings']).lower()
        for word in ('image', 'textbox', 'revision'):
            self.assertIn(word, warnings)

    def test_corrupt_docx_reports_error_without_fabricated_segments(self):
        source = self.root / 'broken.docx'
        source.write_bytes(b'not a zip')
        result, data = self.run_extract(source)
        self.assertNotEqual(result.returncode, 0)
        self.assertIsNotNone(data, 'Failed extraction must still write a coverage report')
        self.assertEqual(data['read_status'], 'error')
        self.assertEqual(data['segments'], [])

    def test_docx_rejects_uncompressed_bomb(self):
        source = self.docx({'word/document.xml': b' ' * (65 * 1024 * 1024)})
        result, data = self.run_extract(source)
        self.assertNotEqual(result.returncode, 0)
        self.assertIsNotNone(data, 'Limit failure must still write a coverage report')
        self.assertIn('limit', ' '.join(data['warnings']).lower())

    def test_docx_rejects_utf16_entity_declarations(self):
        xml = f'<?xml version="1.0" encoding="UTF-16"?><!DOCTYPE doc [<!ENTITY invented "NOT SOURCE TEXT">]><w:document xmlns:w="{NS}"><w:p><w:r><w:t>&invented;</w:t></w:r></w:p></w:document>'
        source = self.docx({'word/document.xml': xml.encode('utf-16')})
        result, data = self.run_extract(source)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(data['read_status'], 'error')
        self.assertEqual(data['segments'], [])

    def test_malformed_xml_and_unsafe_archive_paths_are_reported(self):
        for parts in ({'word/document.xml': '<broken'},
                      {'word/document.xml': '<document/>', '../escape': 'unsafe'}):
            with self.subTest(parts=parts):
                self.out.unlink(missing_ok=True)
                source = self.docx(parts)
                result, data = self.run_extract(source)
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(data['read_status'], 'error')

    def test_empty_pdf_requires_ocr_and_tool_failure_is_error(self):
        source = self.root / 'scan.pdf'
        source.write_bytes(b'%PDF-1.4\n')
        tool = self.root / 'pdftotext'
        for script, expected, code in (('#!/bin/sh\nprintf "\\f"\n', 'needs_ocr', 0),
                                        ('#!/bin/sh\necho corrupt >&2\nexit 1\n', 'error', 2)):
            with self.subTest(expected=expected):
                self.out.unlink(missing_ok=True)
                tool.write_text(script)
                tool.chmod(0o755)
                result, data = self.run_extract(source, {**os.environ, 'PATH': str(self.root)})
                self.assertEqual(result.returncode, code, result.stderr)
                self.assertEqual(data['read_status'], expected)

    def test_repeat_extraction_is_idempotent_and_invalid_utf8_is_error(self):
        source = self.root / 'notes.txt'
        source.write_text('same input')
        result, _ = self.run_extract(source)
        self.assertEqual(result.returncode, 0, result.stderr)
        before = self.out.stat().st_mtime_ns
        result, _ = self.run_extract(source)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.out.stat().st_mtime_ns, before)
        self.out.unlink()
        source.write_bytes(b'\xff\xfe\x81')
        result, data = self.run_extract(source)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(data['read_status'], 'error')

    def test_markdown_keeps_blank_line_and_line_numbers(self):
        source = self.root / 'notes.md'
        source.write_text('# 标题\n\n原文  10 台\n', encoding='utf-8')
        result, data = self.run_extract(source)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(data['segments'], [
            {'locator': {'line': 1}, 'text': '# 标题'},
            {'locator': {'line': 2}, 'text': ''},
            {'locator': {'line': 3}, 'text': '原文  10 台'}])

    def test_image_is_metadata_only_and_requires_visual_review(self):
        source = self.root / 'scan.png'
        source.write_bytes(b'\x89PNG\r\n\x1a\n')
        result, data = self.run_extract(source)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(data['read_status'], 'needs_visual_review')
        self.assertEqual(data['visual_review_status'], 'pending')
        self.assertEqual(data['segments'], [])

    def test_pdf_missing_tool_reports_partial(self):
        source = self.root / 'sample.pdf'
        source.write_bytes(b'%PDF-1.4\n')
        result, data = self.run_extract(source, {**os.environ, 'PATH': ''})
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(data['read_status'], 'partial')
        self.assertIn('pdftotext', ' '.join(data['warnings']))
        self.assertEqual(data['segments'], [])

    def test_pdf_page_split_retains_empty_pages_and_marks_ocr(self):
        tool = self.root / 'pdftotext'
        tool.write_text('#!/bin/sh\nprintf "page one\\f\\fpage three\\f"\n')
        tool.chmod(0o755)
        source = self.root / 'sample.pdf'
        source.write_bytes(b'%PDF-1.4\n')
        result, data = self.run_extract(source, {**os.environ, 'PATH': str(self.root)})
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual([s['locator']['page'] for s in data['segments']], [1, 2, 3])
        self.assertEqual(data['segments'][1]['text'], '')
        self.assertEqual(data['read_status'], 'partial')
        self.assertIn('OCR', ' '.join(data['warnings']))

    def test_refuses_to_overwrite_source_or_different_output(self):
        source = self.root / 'notes.txt'
        source.write_text('source text')
        result, _ = self.run_extract(source, out=source)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(source.read_text(), 'source text')
        self.out.write_text('{"user": "work"}')
        result, _ = self.run_extract(source)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.out.read_text(), '{"user": "work"}')


if __name__ == '__main__':
    unittest.main()
