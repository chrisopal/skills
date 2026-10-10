"""Regression tests for the byte-bound DOCX/PDF export acceptance receipt."""

import base64
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import build_docx  # noqa: E402
import export_checks  # noqa: E402

PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aZ1kAAAAASUVORK5CYII="
)


@unittest.skipUnless(
    importlib.util.find_spec("docx") and importlib.util.find_spec("fitz"),
    "python-docx and PyMuPDF are required",
)
class ExportChecksTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)
        (self.root / "work").mkdir()
        (self.root / "work/project.json").write_text(
            '{"project_id":"EXPORT-TEST"}', encoding="utf-8"
        )
        (self.root / "figure.png").write_bytes(PNG)

    def tearDown(self):
        self.directory.cleanup()

    def spec(self, *, toc=False, expected_fact=True):
        value = {
            "title": "Export Acceptance",
            "subtitle": "Small fixture",
            "expected_facts": (
                [{"id": "deadline", "value": "Deadline: 30 days"}] if expected_fact else []
            ),
            "export_settings": {
                "header": {"text": "", "page_field": False},
                "footer": {"text": "", "page_field": False},
                "cover": {"metadata_rows": [{"label": "Project", "value": "EXPORT-TEST"}]},
                "toc": {"enabled": toc, "title": "Contents", "levels": 2},
            },
            "sections": [
                {
                    "title": "1. Delivery Plan",
                    "level": 1,
                    "paragraphs": ["Body paragraph", "Deadline: 30 days"],
                    "tables": [{"headers": ["Field", "Value"], "rows": [["Status", "Ready"]]}],
                    "images": [{"path": "figure.png", "width_cm": 2, "caption": "Plan figure"}],
                }
            ],
        }
        path = self.root / "document-spec.json"
        path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
        return path

    def build_docx(self, spec_path, name="draft.docx"):
        output = self.root / name
        build_docx.build(spec_path, output, self.root)
        return output

    def build_pdf(self, *, toc=False, include_fact=True, name="draft.pdf", include_image=True):
        import fitz

        output = self.root / name
        document = fitz.open()
        page = document.new_page()
        values = ["Export Acceptance", "Small fixture", "Project", "EXPORT-TEST"]
        if toc:
            values.append("Contents")
            values.append("1. Delivery Plan")
        values += ["1. Delivery Plan", "Body paragraph"]
        if include_fact:
            values.append("Deadline: 30 days")
        values += ["Field", "Value", "Status", "Ready", "Plan figure"]
        y = 60
        for value in values:
            page.insert_text((50, y), value)
            y += 18
        if include_image:
            page.insert_image(fitz.Rect(50, y, 70, y + 20), stream=PNG)
        document.save(output)
        document.close()
        return output

    def test_real_docx_and_pdf_pass_with_counts_and_identity(self):
        spec = self.spec()
        docx = self.build_docx(spec)
        pdf = self.build_pdf()
        receipt = export_checks.inspect(spec, docx, pdf, self.root)
        self.assertTrue(receipt["passed"], receipt["findings"])
        self.assertEqual(receipt["project_id"], "EXPORT-TEST")
        self.assertEqual(receipt["counts"]["docx"]["images"], 1)
        self.assertEqual(receipt["counts"]["pdf"]["pages"], 1)
        self.assertEqual(receipt["visual_qa"], "NOT_RUN")
        self.assertEqual(receipt["coverage"]["docx"]["facts"]["absent"], [])

    def test_missing_heading_image_and_fact_cannot_pass(self):
        spec = self.spec()
        actual_spec = json.loads(spec.read_text(encoding="utf-8"))
        actual_spec["sections"][0]["title"] = "1. Other Plan"
        actual_spec["sections"][0]["images"] = []
        actual_spec["sections"][0]["paragraphs"] = ["Body paragraph"]
        actual = self.root / "actual.json"
        actual.write_text(json.dumps(actual_spec), encoding="utf-8")
        docx = self.build_docx(actual, "missing.docx")
        pdf = self.build_pdf(include_fact=False, include_image=False, name="missing.pdf")
        receipt = export_checks.inspect(spec, docx, pdf, self.root)
        self.assertFalse(receipt["passed"])
        joined = "\n".join(receipt["findings"])
        self.assertIn("章节标题", joined)
        self.assertIn("插图数量", joined)
        self.assertIn("关键事实", joined)

    def test_toc_placeholder_is_explicitly_rejected(self):
        spec = self.spec(toc=True)
        docx = self.build_docx(spec, "toc.docx")
        pdf = self.build_pdf(toc=True, name="toc.pdf")
        receipt = export_checks.inspect(spec, docx, pdf, self.root)
        self.assertFalse(receipt["passed"])
        self.assertTrue(any("目录" in finding for finding in receipt["findings"]))

    def test_verify_receipt_rejects_changed_output_bytes_and_spec(self):
        spec = self.spec()
        docx = self.build_docx(spec)
        pdf = self.build_pdf()
        receipt = export_checks.inspect(spec, docx, pdf, self.root)
        self.assertTrue(receipt["passed"], receipt["findings"])
        pdf.write_bytes(pdf.read_bytes() + b"drift")
        with self.assertRaisesRegex(ValueError, "当前文件未通过|漂移"):
            export_checks.verify_receipt(receipt, spec, docx, pdf, self.root)

    def test_wrong_picture_with_same_count_fails(self):
        import fitz
        spec = self.spec()
        pix = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, 8, 8), False)
        pix.clear_with(0)
        (self.root / 'other.png').write_bytes(pix.tobytes('png'))
        actual = json.loads(spec.read_text())
        actual['sections'][0]['images'][0]['path'] = 'other.png'
        actual_path = self.root / 'actual.json'
        actual_path.write_text(json.dumps(actual))
        receipt = export_checks.inspect(spec, self.build_docx(actual_path), self.build_pdf(), self.root)
        self.assertFalse(receipt['passed'])
        self.assertTrue(any('插图内容' in f for f in receipt['findings']))

    def test_incomplete_spec_cannot_hide_current_outline(self):
        spec = self.spec()
        (self.root / 'artifacts').mkdir()
        (self.root / 'artifacts/08-outline.json').write_text(json.dumps({'data': {'sections': [{'id': 'A'}, {'id': 'B'}]}}))
        (self.root / 'artifacts/11-technical-content.json').write_text(json.dumps({'data': {'chapters': [{'section_id': 'A', 'body_markdown': 'Actual text'}]}}))
        receipt = export_checks.inspect(spec, self.build_docx(spec), self.build_pdf(), self.root)
        self.assertFalse(receipt['passed'])
        self.assertTrue(any('当前目录' in f for f in receipt['findings']))
        self.assertTrue(any('漏当前正文' in f for f in receipt['findings']))

    def test_other_project_artifacts_cannot_pass_receipt(self):
        import hashlib
        spec = self.spec()
        value = json.loads(spec.read_text())
        value['sections'][0]['section_id'] = 'A'
        (self.root / 'artifacts').mkdir()
        inputs = {'08-outline.json': {'data': {'sections': [{'id': 'A'}]}},
                  '11-technical-content.json': {'data': {'chapters': [{'section_id': 'A', 'body_markdown': 'Body paragraph'}]}}}
        value['inputs'] = []
        for name, payload in inputs.items():
            payload['project_id'] = 'OTHER-PROJECT'
            path = self.root / 'artifacts' / name
            path.write_text(json.dumps(payload))
            value['inputs'].append({'relative_path': 'artifacts/'+name, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()})
        spec.write_text(json.dumps(value))
        receipt = export_checks.inspect(spec, self.build_docx(spec), self.build_pdf(), self.root)
        self.assertFalse(receipt['passed'])
        self.assertTrue(any('项目身份不一致' in f for f in receipt['findings']))

    def test_missing_declared_header_footer_and_page_field_fails(self):
        spec = self.spec()
        expected = json.loads(spec.read_text())
        expected['export_settings']['header'] = {'text': 'CONFIDENTIAL HEADER'}
        expected['export_settings']['footer'] = {'text': 'Page ', 'page_field': True, 'page_prefix': '', 'page_suffix': ''}
        docx = self.build_docx(spec)
        spec.write_text(json.dumps(expected))
        receipt = export_checks.inspect(spec, docx, self.build_pdf(), self.root)
        self.assertFalse(receipt['passed'])
        self.assertTrue(any('DOCX缺少声明的header' in f for f in receipt['findings']))
        self.assertTrue(any('PDF第1页缺少声明的页码' in f for f in receipt['findings']))

    def test_internal_signing_trace_cannot_pass_even_when_in_spec(self):
        from docx import Document
        import fitz
        spec = self.spec()
        value = json.loads(spec.read_text())
        trace = 'confirmation_ref: work/test-authorisation.md'
        value['sections'][0]['paragraphs'].append(trace)
        spec.write_text(json.dumps(value))
        docx = self.build_docx(spec)
        pdf = self.build_pdf()
        with fitz.open(pdf) as document:
            document[0].insert_text((50, 700), trace)
            document.saveIncr()
        receipt = export_checks.inspect(spec, docx, pdf, self.root)
        self.assertFalse(receipt['passed'])
        self.assertTrue(any('内部执行信息' in finding for finding in receipt['findings']))

    def test_current_commercial_value_cannot_be_omitted_from_spec(self):
        import hashlib
        spec = self.spec()
        value = json.loads(spec.read_text())
        value['sections'][0]['section_id'] = 'A'
        (self.root / 'artifacts').mkdir()
        inputs = {
            '08-outline.json': {'data': {'sections': [{'id': 'A'}]}},
            '11-technical-content.json': {'data': {'chapters': [{'section_id': 'A', 'body_markdown': 'Body paragraph'}]}},
            '12-commercial-content.json': {'data': {'forms': [{'id': 'F1', 'fields': [{'key': 'Amount', 'value': '650000 yuan'}]}]}},
        }
        value['inputs'] = []
        for name, payload in inputs.items():
            payload['project_id'] = 'EXPORT-TEST'
            path = self.root / 'artifacts' / name
            path.write_text(json.dumps(payload))
            value['inputs'].append({'relative_path': 'artifacts/'+name, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()})
        spec.write_text(json.dumps(value))
        receipt = export_checks.inspect(spec, self.build_docx(spec), self.build_pdf(), self.root)
        self.assertFalse(receipt['passed'])
        self.assertTrue(any('漏商务字段' in finding for finding in receipt['findings']))

    def test_each_partial_current_artifact_is_checked(self):
        import hashlib
        import itertools
        directory = self.root/'artifacts'
        directory.mkdir()
        names = ('08-outline.json', '11-technical-content.json', '12-commercial-content.json')
        payloads = (
            {'sections': [{'id': 'B'}]},
            {'chapters': [{'section_id': 'A', 'body_markdown': 'Required current body'}]},
            {'forms': [{'id': 'F1', 'fields': [{'key': 'Amount', 'value': '650000 yuan'}]}]},
        )
        for count in range(1, 4):
            for indices in itertools.combinations(range(3), count):
                with self.subTest(indices=indices):
                    for old in directory.glob('*.json'):
                        old.unlink()
                    spec = self.spec()
                    value = json.loads(spec.read_text())
                    value['sections'][0]['section_id'] = 'A'
                    value['inputs'] = []
                    for i in indices:
                        path = directory/names[i]
                        path.write_text(json.dumps({'project_id': 'EXPORT-TEST', 'data': payloads[i]}))
                        value['inputs'].append({'relative_path': 'artifacts/'+names[i], 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()})
                    spec.write_text(json.dumps(value))
                    docx = self.build_docx(spec, 'partial-'+''.join(map(str, indices))+'.docx')
                    pdf = self.build_pdf(name='partial-'+''.join(map(str, indices))+'.pdf')
                    receipt = export_checks.inspect(spec, docx, pdf, self.root)
                    self.assertFalse(receipt['passed'])
                    for i in indices:
                        self.assertTrue(any(('当前目录', '漏当前正文', '漏商务字段')[i] in f for f in receipt['findings']), receipt['findings'])

    def test_malformed_current_artifact_returns_failed_receipt(self):
        spec = self.spec()
        (self.root/'artifacts').mkdir()
        (self.root/'artifacts/08-outline.json').write_text('{"data":{}}')
        receipt = export_checks.inspect(spec, self.build_docx(spec), self.build_pdf(), self.root)
        self.assertFalse(receipt['passed'])
        self.assertTrue(any('结构' in f for f in receipt['findings']))

    def test_omitted_page_field_uses_builder_default(self):
        spec = self.spec()
        value = json.loads(spec.read_text())
        value['export_settings']['footer'] = {'text': 'CONF', 'page_field': False}
        spec.write_text(json.dumps(value))
        docx = self.build_docx(spec)
        value['export_settings']['footer'].pop('page_field')
        spec.write_text(json.dumps(value))
        receipt = export_checks.inspect(spec, docx, self.build_pdf(), self.root)
        self.assertFalse(receipt['passed'])
        self.assertTrue(any('PAGE' in f for f in receipt['findings']), receipt['findings'])

    def test_internal_paths_are_rejected_regardless_of_extension(self):
        for i, path in enumerate(('work/attempt.yaml', 'reviews/a.csv', 'artifacts/proof.png', 'profiles/layout.docx')):
            with self.subTest(path=path):
                spec = self.spec()
                value = json.loads(spec.read_text())
                value['sections'][0]['paragraphs'].append(path)
                spec.write_text(json.dumps(value))
                receipt = export_checks.inspect(spec, self.build_docx(spec, 'path'+str(i)+'.docx'), self.build_pdf(name='path'+str(i)+'.pdf'), self.root)
                self.assertFalse(receipt['passed'])
                self.assertTrue(any('内部执行信息' in f for f in receipt['findings']))

    def test_malformed_files_fail_with_machine_findings(self):
        spec = self.spec()
        docx = self.root / "bad.docx"
        pdf = self.root / "bad.pdf"
        docx.write_bytes(b"not a zip")
        pdf.write_bytes(b"not a pdf")
        receipt = export_checks.inspect(spec, docx, pdf, self.root)
        self.assertFalse(receipt["passed"])
        self.assertTrue(any("DOCX格式无效" in finding for finding in receipt["findings"]))
        self.assertTrue(any("PDF格式无效" in finding for finding in receipt["findings"]))


if __name__ == "__main__":
    unittest.main()
