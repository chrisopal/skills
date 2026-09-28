"""Deterministic scanner tests. These do not evaluate model editorial quality."""
from __future__ import annotations
import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / 'scripts' / 'audit_inventory.py'
spec = importlib.util.spec_from_file_location('audit_inventory', MODULE_PATH)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class InventoryTests(unittest.TestCase):
    def test_toc_entries_are_not_body_chapters(self):
        result = module.inventory('# 全书目录\n1. 第1章 入门\n2. 第2章 实践\n# 第1章 入门\n正文\n')
        self.assertEqual(result['chapter_count'], 1)
        self.assertEqual(result['sections'][0]['start_line'], 4)

    def test_fenced_heading_is_not_a_chapter(self):
        result = module.inventory('```text\n# 第99章 示例\n```\n# 第1章 正文\n')
        self.assertEqual([s['id'] for s in result['sections']], [1])
        self.assertEqual(result['fence_count'], 1)

    def test_four_appendices_counted_from_body(self):
        text = '# 全书目录\n- 附录一\n- 附录二\n- 附录三\n' + '\n'.join('# 附录' + n + ' 正文' for n in '一二三四')
        result = module.inventory(text)
        self.assertEqual(result['appendix_count'], 4)

    def test_exact_section_ranges(self):
        result = module.inventory('# 第1章 一\n文字\n\n# 第2章 二\n文字\n# 附录一 三\n文字')
        self.assertEqual([(s['start_line'], s['end_line']) for s in result['sections']], [(1,3),(4,5),(6,7)])

    def test_block_phrase_counts_are_separate(self):
        result = module.inventory('# 第1章 实际\n实际核对\n|实际|核对|\n```text\n实际核对\n```\n')
        counts = result['phrase_counts_by_block_type']['实际']
        self.assertEqual(counts['narrative'], 1)
        self.assertEqual(counts['table'], 1)
        self.assertEqual(counts['code_or_prompt'], 1)
        self.assertEqual(counts['heading'], 1)

    def test_unclosed_fence_reported(self):
        result = module.inventory('# 第1章 一\n```text\n示例')
        self.assertEqual(len(result['unclosed_fences']), 1)
        self.assertFalse(result['unclosed_fences'][0]['closed'])

    def test_tilde_fence(self):
        result = module.inventory('~~~text\n# 第90章 示例\n~~~\n# 第1章 正文')
        self.assertEqual(result['chapter_count'], 1)
        self.assertEqual(result['unclosed_fences'], [])

    def test_shorter_marker_does_not_close_long_fence(self):
        result = module.inventory('````text\n```\n# 第90章 示例\n````\n# 第1章 正文')
        self.assertEqual(result['chapter_count'], 1)
        self.assertEqual(result['fence_count'], 1)
        self.assertEqual(result['unclosed_fences'], [])

    def test_url_and_signed_reference_not_exported(self):
        text = '# 第1章 [章节](https://example.test/private)\n![图](https://example.test/a?code=PRIVATE_TOKEN)\n正文 [资料](https://example.test/private)\n'
        result = module.inventory(text)
        payload = json.dumps(result, ensure_ascii=False)
        self.assertNotIn('PRIVATE_TOKEN', payload)
        self.assertNotIn('https://example.test/', payload)
        self.assertNotIn('a?code=', payload)
        self.assertEqual(result['sections'][0]['image_reference_count'], 1)

    def test_attachment_and_image_are_not_missing_verdicts(self):
        result = module.inventory('# 第1章 一\n\\[练习包\\.zip\\]\n![Image](https://example.test/img)\n')
        self.assertEqual(result['sections'][0]['attachment_placeholder_count'], 1)
        self.assertEqual(result['sections'][0]['image_reference_count'], 1)
        self.assertNotIn('missing', result['sections'][0])

    def test_inventory_does_not_assert_editorial_read(self):
        result = module.inventory('# 第1章 一\n正文')
        self.assertEqual(result['sections'][0]['coverage_status'], 'inventoried_not_editorially_read')
        self.assertNotIn('score', result)

    def test_same_source_output_rejected_without_change(self):
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp)/'source.md'
            original = '# 第1章 一\n正文'.encode()
            source.write_bytes(original)
            with self.assertRaises(ValueError):
                module.run(source, source)
            self.assertEqual(source.read_bytes(), original)

    def test_existing_output_rejected_without_change(self):
        with tempfile.TemporaryDirectory() as temp:
            source, out = Path(temp)/'source.md', Path(temp)/'out.json'
            source.write_text('# 第1章 一\n正文', encoding='utf-8')
            out.write_text('preserve-me', encoding='utf-8')
            with self.assertRaises(FileExistsError):
                module.run(source, out)
            self.assertEqual(out.read_text(), 'preserve-me')

    def test_utf8_bom_and_hash(self):
        with tempfile.TemporaryDirectory() as temp:
            source, out = Path(temp)/'source.md', Path(temp)/'out.json'
            raw = b'\xef\xbb\xbf' + '# 第1章 一\n正文'.encode()
            source.write_bytes(raw)
            result = module.run(source, out)
            self.assertEqual(result['chapter_count'], 1)
            self.assertEqual(result['source_sha256'], hashlib.sha256(raw).hexdigest())
            self.assertEqual(json.loads(out.read_text(encoding='utf-8'))['chapter_count'], 1)
            self.assertEqual(source.read_bytes(), raw)

    def test_source_text_is_never_executed(self):
        with tempfile.TemporaryDirectory() as temp:
            marker = Path(temp)/'must-not-exist'
            text = f'# 第1章 一\n```python\nfrom pathlib import Path\nPath({str(marker)!r}).touch()\n```\n'
            result = module.inventory(text)
            self.assertEqual(result['fence_count'], 1)
            self.assertFalse(marker.exists())

    def test_empty_document(self):
        result = module.inventory('')
        self.assertEqual(result['chapter_count'], 0)
        self.assertEqual(result['appendix_count'], 0)
        self.assertIsNone(result['chapter_han_median'])

if __name__ == '__main__':
    unittest.main(verbosity=2)
