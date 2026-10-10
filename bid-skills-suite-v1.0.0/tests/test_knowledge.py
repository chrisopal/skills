"""Project knowledge tests; host responses here are synthetic protocol fixtures."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import bidkit
import knowledge
from refresh_distribution import distribution_files


class KnowledgeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.project = self.root / 'project'
        bidkit.init_project(self.project, 'TEST-KNOWLEDGE')

    def host_result(self):
        return {
            'project_id': 'TEST-KNOWLEDGE', 'provider': 'synthetic-host',
            'tool_name': 'synthetic_search', 'retrieval_ref': 'TEST-CALL-001',
            'query': '设备运维', 'retrieved_at': '2026-10-07T12:00:00+08:00',
            'permission_scope': 'TEST-COMPANY / authorized project documents',
            'results': [{
                'document_id': 'DOC-001', 'title': '合成设备运维说明',
                'source_ref': 'https://example.invalid/doc/1', 'revision': 'r2',
                'location': '第 2 节', 'text': '设备运维包括巡检、保养和故障处理。',
            }],
        }

    def import_host(self, value=None):
        source = self.root / 'response.json'
        source.write_text(json.dumps(value or self.host_result(), ensure_ascii=False))
        return knowledge.import_host(self.project, source)

    def test_continuous_chinese_query_recovers_separated_relevant_terms(self):
        source = self.root / 'supplier.md'
        source.write_text('支持工单管理，提供事件闭环处理。', encoding='utf-8')
        knowledge.add_local(self.project, source, title='平台功能说明')
        result = knowledge.search(self.project, '工单管理事件闭环')
        self.assertEqual(result['total_matches'], 1)
        self.assertIn('工单', result['matches'][0]['matched_terms'])
        self.assertEqual(result['mode'], 'local_keyword')
        self.assertEqual(knowledge.search(self.project, '财务税务核算报表')['total_matches'], 0)

    def test_punctuation_only_query_cannot_claim_retrieval(self):
        with self.assertRaises(ValueError):
            knowledge.search(self.project, '。。。！？')

    def test_local_file_is_preserved_and_wiki_keeps_location(self):
        source = self.root / 'supplier.md'
        source.write_text('# 产品资料\n设备运维支持巡检。\n', encoding='utf-8')
        result = knowledge.add_local(self.project, source, title='产品资料', subject='测试企业')
        index = knowledge.load_index(self.project)
        entry = index['entries'][0]
        self.assertEqual(result['entries_added'], 1)
        self.assertEqual((self.project / entry['source']['relative_path']).read_bytes(), source.read_bytes())
        self.assertEqual(entry['subject'], '测试企业')
        page = self.project / f"artifacts/knowledge/wiki/{entry['id']}.md"
        self.assertIn('L2', page.read_text())
        self.assertIn('设备运维支持巡检', page.read_text())
        self.assertEqual(entry['status'], 'needs_review')

    def test_local_extraction_does_not_include_tender_as_supplier_knowledge(self):
        tender = self.root / 'tender.md'
        tender.write_text('TENDER-ONLY-SECRET')
        bidkit.register_source(self.project, tender, 'main')
        supplier = self.root / 'supplier.md'
        supplier.write_text('SUPPLIER-ONLY')
        knowledge.add_local(self.project, supplier)
        index = knowledge.load_index(self.project)
        content = bidkit.read(self.project / index['entries'][0]['content']['relative_path'])
        self.assertNotIn('TENDER-ONLY-SECRET', json.dumps(content))

    def test_host_result_saved_with_provenance_and_no_auto_acceptance(self):
        self.import_host()
        index = knowledge.load_index(self.project)
        entry = index['entries'][0]
        self.assertEqual(entry['provider'], 'synthetic-host')
        self.assertEqual(entry['document_revision'], 'r2')
        self.assertEqual(entry['status'], 'needs_review')
        source = bidkit.read(self.project / entry['source']['relative_path'])
        self.assertEqual(source['retrieval_ref'], 'TEST-CALL-001')
        self.assertEqual(source['results'][0]['text'], self.host_result()['results'][0]['text'])

    def test_unknown_host_document_revision_stays_unknown(self):
        response = self.host_result()
        response['results'][0]['revision'] = None
        self.import_host(response)
        self.assertIsNone(knowledge.load_index(self.project)['entries'][0]['document_revision'])

    def test_host_project_mismatch_rejected_without_writes(self):
        response = self.host_result()
        response['project_id'] = 'OTHER'
        with self.assertRaisesRegex(ValueError, '项目'):
            self.import_host(response)
        self.assertFalse((self.project / 'artifacts/knowledge/index.json').exists())

    def test_host_missing_provenance_rejected(self):
        response = self.host_result()
        del response['permission_scope']
        with self.assertRaises(ValueError):
            self.import_host(response)

    def test_host_empty_results_saved_as_empty_not_no_requirements(self):
        response = self.host_result()
        response['results'] = []
        result = self.import_host(response)
        index = knowledge.load_index(self.project)
        self.assertEqual(result['entries_added'], 0)
        self.assertEqual(index['imports'][0]['result_count'], 0)
        self.assertEqual(len(index['entries']), 0)
        self.assertIn('没有已登记知识条目', (self.project / 'artifacts/knowledge/wiki/index.md').read_text())

    def test_host_unexpected_fields_are_not_silently_imported(self):
        response = self.host_result()
        response['api_key'] = 'TEST-SECRET-NOT-REAL'
        with self.assertRaises(ValueError):
            self.import_host(response)

    def test_credential_bearing_provenance_rejected_before_writing(self):
        for field, value in (
            ('source_ref', 'https://user:TOPSECRET@example.invalid/doc'),
            ('source_ref', 'https://example.invalid/doc?api_key=TOPSECRET'),
            ('source_ref', 'https://example.invalid/doc?X-Amz-Signature=TOPSECRET'),
            ('retrieval_ref', 'call?access_token=TOPSECRET'),
            ('location', 'page 1\nAuthorization: Bearer TOPSECRET'),
        ):
            with self.subTest(field=field):
                response = self.host_result()
                target = response if field == 'retrieval_ref' else response['results'][0]
                target[field] = value
                with self.assertRaises(ValueError) as raised:
                    self.import_host(response)
                self.assertNotIn('TOPSECRET', str(raised.exception))
                self.assertFalse((self.project / 'inputs/knowledge').exists())

    def test_untrusted_titles_cannot_embed_markdown_images_in_wiki(self):
        response = self.host_result()
        response['results'][0]['title'] = 'Report ![tracking](https://example.invalid/pixel)'
        response['results'][0]['location'] = '![tracking](https://example.invalid/pixel)'
        self.import_host(response)
        page = next((self.project / 'artifacts/knowledge/wiki').glob('K-*.md')).read_text()
        index = (self.project / 'artifacts/knowledge/wiki/index.md').read_text()
        self.assertNotIn('Report ![tracking]', page)
        self.assertNotIn('Report ![tracking]', index)
        self.assertIn('<pre>位置：![tracking](https://example.invalid/pixel)</pre>', page)

    def test_missing_ocr_configuration_does_not_register_or_copy_source(self):
        source = self.root / 'supplier.md'
        source.write_text('测试材料')
        with patch.dict(os.environ, {}, clear=True), self.assertRaises(RuntimeError):
            knowledge.add_local(self.project, source, ocr='paddle-service')
        self.assertEqual(bidkit.read(self.project / 'inputs/source-registry.json')['sources'], [])
        self.assertFalse((self.project / 'artifacts/knowledge/index.json').exists())

    def test_search_keeps_reference_and_reports_no_match(self):
        self.import_host()
        hits = knowledge.search(self.project, '设备运维', limit=5)
        self.assertEqual(len(hits['matches']), 1)
        self.assertEqual(hits['matches'][0]['location'], '第 2 节')
        self.assertEqual(hits['matches'][0]['status'], 'needs_review')
        self.assertEqual(knowledge.search(self.project, 'unrelated', limit=5)['matches'], [])

    def test_changed_saved_source_blocks_search_and_wiki_rebuild(self):
        self.import_host()
        index = knowledge.load_index(self.project)
        (self.project / index['entries'][0]['source']['relative_path']).write_text('changed')
        with self.assertRaisesRegex(ValueError, '变化'):
            knowledge.search(self.project, '设备')
        with self.assertRaises(ValueError):
            knowledge.build_wiki(self.project)

    def test_changed_content_blocks_search(self):
        self.import_host()
        entry = knowledge.load_index(self.project)['entries'][0]
        (self.project / entry['content']['relative_path']).write_text('{}')
        with self.assertRaises(ValueError):
            knowledge.search(self.project, '设备')

    def test_cross_project_index_rejected(self):
        self.import_host()
        index = knowledge.load_index(self.project)
        index['project_id'] = 'OTHER'
        bidkit.atomic(self.project / 'artifacts/knowledge/index.json', index)
        with self.assertRaisesRegex(ValueError, '项目'):
            knowledge.load_index(self.project)

    def test_knowledge_change_invalidates_existing_release_snapshot(self):
        self.import_host()
        bidkit.snapshot(self.project, 'reviews/snapshot.json')
        response = self.host_result()
        response['results'][0]['text'] = '设备运维增加状态监测。'
        response['results'][0]['revision'] = 'r3'
        self.import_host(response)
        self.assertFalse(bidkit.verify_snapshot(self.project, self.project / 'reviews/snapshot.json')['current'])
        self.assertEqual(knowledge.load_index(self.project)['revision'], 2)

    def test_wiki_can_be_rebuilt_without_changing_sources(self):
        self.import_host()
        index = knowledge.load_index(self.project)
        original_hash = bidkit.digest(self.project / index['entries'][0]['source']['relative_path'])
        (self.project / 'artifacts/knowledge/wiki/index.md').unlink()
        knowledge.build_wiki(self.project)
        self.assertEqual(original_hash, bidkit.digest(self.project / index['entries'][0]['source']['relative_path']))

    def test_unsafe_source_path_rejected(self):
        self.import_host()
        index = knowledge.load_index(self.project)
        index['entries'][0]['content']['relative_path'] = '../outside.json'
        bidkit.atomic(self.project / 'artifacts/knowledge/index.json', index)
        with self.assertRaises(ValueError):
            knowledge.search(self.project, '设备')

    def test_wiki_symlink_cannot_write_outside_project(self):
        self.import_host()
        outside = self.root / 'outside.md'
        outside.write_text('KEEP')
        target = self.project / 'artifacts/knowledge/wiki/index.md'
        target.unlink()
        target.symlink_to(outside)
        with self.assertRaises(ValueError):
            knowledge.build_wiki(self.project)
        self.assertEqual(outside.read_text(), 'KEEP')

    def test_standalone_packages_execute_knowledge_import(self):
        source = self.root / 'supplier.md'
        source.write_text('独立安装的设备运维资料。', encoding='utf-8')
        for sequence, name in ((9, 'bid-evidence-matching'), (17, 'bid-orchestrator')):
            with self.subTest(skill=name):
                install = self.root / name
                package = self.root / f'{sequence:02d}-{name}.zip'
                source_dir = ROOT / 'skills' / name
                with zipfile.ZipFile(package, 'w') as archive:
                    for path in distribution_files(source_dir):
                        archive.write(path, f'{name}/{path.relative_to(source_dir).as_posix()}')
                with zipfile.ZipFile(package) as archive:
                    archive.extractall(install)
                script = install / name / 'scripts/knowledge.py'
                result = subprocess.run(
                    [sys.executable, str(script), 'add-local', '--project', str(self.project),
                     '--file', str(source)], cwd=install, capture_output=True, text=True,
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(json.loads(result.stdout)['entries_added'], 1)


if __name__ == '__main__':
    unittest.main()
