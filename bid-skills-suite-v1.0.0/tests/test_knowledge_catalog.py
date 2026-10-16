"""Material classification and rebuildable Wiki coverage."""
import json
import hashlib
import tempfile
import unittest
import zipfile
from pathlib import Path

import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import bidkit  # noqa: E402
import knowledge  # noqa: E402


class KnowledgeCatalogTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.project = self.root / 'project'
        bidkit.init_project(self.project, 'TEST-CATALOG')

    def test_text_material_card_and_duplicate_are_rebuildable(self):
        metadata = {
            'kind': 'evidence',
            'tags': ['营业执照', '主体'],
            'fields': {'统一社会信用代码': {'value': '9133', 'location': 'text'}},
            'simulation': True,
            'classification_method': 'manual',
        }
        result = knowledge.add_text(self.project, '企业名称：示例公司，统一社会信用代码：9133', title='主体资料',
                                    category='enterprise', metadata=metadata)
        self.assertEqual(result['entries_added'], 1)
        duplicate = knowledge.add_text(self.project, '企业名称：示例公司，统一社会信用代码：9133', title='主体资料',
                                       category='enterprise', metadata=metadata)
        self.assertEqual(duplicate['status'], 'duplicate')
        index = knowledge.load_index(self.project)
        material = index['entries'][0]['material']
        self.assertEqual(material['category'], 'enterprise')
        self.assertTrue(material['simulation'])
        page = (self.project / 'artifacts/knowledge/wiki' / f"{index['entries'][0]['id']}.md").read_text()
        catalog = (self.project / 'artifacts/knowledge/wiki/index.md').read_text()
        self.assertIn('企业基础资质', page)
        self.assertIn('text', page)
        self.assertIn('分类索引', catalog)

    def test_wiki_shows_declared_subject_separately_from_title(self):
        result = knowledge.add_text(self.project, '技术方案', title='无主体标题',
                                    subject='甲企业<测试>', category='technical')
        page = (self.project / knowledge.WIKI / f"{result['ids'][0]}.md").read_text()
        index = (self.project / knowledge.WIKI / 'index.md').read_text()
        self.assertIn('主体：甲企业&lt;测试&gt;', page)
        self.assertIn('甲企业&lt;测试&gt;', index)

    def test_wiki_original_links_escape_filename_url_characters(self):
        source = self.root / 'contract (#1).md'
        source.write_text('模拟技术参考', encoding='utf-8')
        result = knowledge.add_local(self.project, source)
        page = (self.project / knowledge.WIKI / f"{result['ids'][0]}.md").read_text()
        self.assertIn('contract%20%28%231%29.md', page)

    def test_uploaded_bitmap_has_original_preview_without_claiming_ocr(self):
        import base64
        file = self.root / 'scan.png'
        file.write_bytes(base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jRZkAAAAASUVORK5CYII='))
        result = knowledge.add_local(self.project, file)
        page = (self.project / knowledge.WIKI / f"{result['ids'][0]}.md").read_text()
        self.assertIn('![原件预览；图中文字仍须核验]', page)
        self.assertIn('需显式--ocr', page)

    def test_folder_reports_symlink_partial_without_following_it(self):
        folder = self.root / 'materials'
        folder.mkdir()
        (folder / 'ok.md').write_text('本地技术参考', encoding='utf-8')
        outside = self.root / 'outside.md'
        outside.write_text('不应被读取', encoding='utf-8')
        (folder / 'link.md').symlink_to(outside)
        result = knowledge.add_folder(self.project, folder, category='technical')
        self.assertEqual(result['status'], 'partial')
        self.assertEqual(result['entries_added'], 1)
        self.assertTrue(any(item['status'] == 'failed' for item in result['results']))
        self.assertNotIn('不应被读取', json.dumps(knowledge.load_index(self.project), ensure_ascii=False))

    def test_candidate_cannot_be_accepted_and_source_tampering_is_rejected(self):
        with self.assertRaises(ValueError):
            knowledge.add_text(self.project, '候选', metadata={'status': 'accepted'})
        knowledge.add_text(self.project, '可核验来源', category='technical')
        entry = knowledge.load_index(self.project)['entries'][0]
        (self.project / entry['source']['relative_path']).write_text('被篡改', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, '变化'):
            knowledge.build_wiki(self.project)

    def test_legacy_entry_without_material_reads_as_unknown(self):
        knowledge.add_text(self.project, '旧材料')
        index = knowledge.load_index(self.project)
        index['entries'][0].pop('material')
        bidkit.atomic(self.project / knowledge.INDEX, index)
        self.assertEqual(knowledge.load_index(self.project)['entries'][0].get('material'), None)
        knowledge.build_wiki(self.project)
        page = next((self.project / knowledge.WIKI).glob('K-*.md')).read_text()
        self.assertIn('待分类 (unknown)', page)

    def test_table_block_is_rendered_as_markdown_table(self):
        knowledge.add_text(self.project, '表格来源', category='technical')
        index = knowledge.load_index(self.project)
        entry = index['entries'][0]
        content_path = self.project / entry['content']['relative_path']
        content = bidkit.read(content_path)
        content['blocks'] = [{
            'location': '第1页',
            'table': {'headers': ['项目', '值'], 'rows': [['版本', 'V1']]},
        }]
        bidkit.atomic(content_path, content)
        entry['content']['sha256'] = bidkit.digest(content_path)
        bidkit.atomic(self.project / knowledge.INDEX, index)
        knowledge.build_wiki(self.project)
        page = (self.project / knowledge.WIKI / f"{entry['id']}.md").read_text()
        self.assertIn('| 项目 | 值 |', page)

    def test_host_connection_and_audit_metadata_are_retained(self):
        source = self.root / 'host.json'
        source.write_text(json.dumps({
            'project_id': 'TEST-CATALOG', 'provider': 'host', 'tool_name': 'search',
            'retrieval_ref': 'call-1', 'query': '技术',
            'retrieved_at': '2026-10-16T12:00:00+08:00',
            'permission_scope': 'enterprise-docs',
            'results': [{'document_id': 'D1', 'title': '技术资料', 'source_ref': 'doc:D1',
                         'revision': '1', 'location': 'P1', 'text': '技术参考'}],
        }), encoding='utf-8')
        knowledge.import_host(self.project, source, connection_id='conn-1', connection_revision=2,
                              category='technical', metadata={'trace': 'call-1'})
        entry = knowledge.load_index(self.project)['entries'][0]
        self.assertEqual(entry['connection_id'], 'conn-1')
        self.assertEqual(entry['connection_revision'], 2)
        self.assertFalse(entry['content']['relative_path'].startswith('inputs/'))
        self.assertEqual(bidkit.read(self.project / entry['content']['relative_path'])['audit']['host_metadata']['trace'], 'call-1')

    def test_keyword_suggestion_is_transparent_and_host_category_wins(self):
        result = knowledge.add_text(self.project, '营业执照\n统一社会信用代码：9133', title='主体资料')
        entry = knowledge.load_index(self.project)['entries'][0]
        self.assertEqual(result['status'], 'needs_review')
        self.assertEqual(entry['material']['category'], 'enterprise')
        self.assertEqual(entry['material']['classification_method'], 'keyword_suggestion')
        self.assertEqual(entry['material']['kind'], 'unknown')

        low = knowledge.add_text(self.project, '合同', title='普通资料')
        low_entry = knowledge.load_index(self.project)['entries'][1]
        self.assertEqual(low['status'], 'needs_review')
        self.assertEqual(low_entry['material']['category'], 'unknown')
        self.assertEqual(low_entry['material']['classification_method'], 'keyword_suggestion')

        explicit = knowledge.add_text(self.project, '营业执照\n统一社会信用代码：9999',
                                      title='技术说明', category='technical')
        explicit_entry = knowledge.load_index(self.project)['entries'][2]
        self.assertEqual(explicit['status'], 'needs_review')
        self.assertEqual(explicit_entry['material']['category'], 'technical')
        self.assertEqual(explicit_entry['material']['classification_method'], 'manual')

    def test_simulation_marker_overrides_false_and_field_values_need_real_quotes(self):
        result = knowledge.add_text(
            self.project, '模拟样例日期：2026年1月', title='测试数据',
            category='technical', metadata={
                'simulation': False,
                'fields': {'valid_on': {'value': '2026-01-01', 'location': 'text',
                                         'quote': '2026年1月'}},
            })
        entry = knowledge.load_index(self.project)['entries'][0]
        self.assertEqual(result['status'], 'needs_review')
        self.assertTrue(entry['material']['simulation'])
        self.assertTrue(entry['material']['fields']['valid_on']['needs_verification'])
        with self.assertRaisesRegex(ValueError, '位置'):
            knowledge.add_text(
                self.project, '社会保险：2026-01', title='人员', category='personnel',
                metadata={'fields': {'social_months': {'value': ['2026-02'], 'location': 'text'}}})
        with self.assertRaisesRegex(ValueError, '不存在'):
            knowledge.add_text(
                self.project, '社会保险：2026-01', title='人员2', category='personnel',
                metadata={'fields': {'social_months': {'value': ['2026-01'], 'location': 'P99'}}})

    def test_reclassify_updates_index_only_and_keeps_note_separate(self):
        knowledge.add_text(self.project, '技术方案和技术参数', title='方案')
        before = knowledge.load_index(self.project)
        entry = before['entries'][0]
        content_before = (self.project / entry['content']['relative_path']).read_bytes()
        result = knowledge.reclassify(self.project, entry['id'], category='historical',
                                      note='人工确认：属于历史模板')
        after = knowledge.load_index(self.project)
        self.assertEqual(result['status'], 'reclassified')
        self.assertEqual(after['entries'][0]['material']['category'], 'historical')
        self.assertEqual(after['entries'][0]['material']['classification_method'], 'manual')
        self.assertGreater(after['revision'], before['revision'])
        self.assertEqual((self.project / entry['content']['relative_path']).read_bytes(), content_before)
        self.assertTrue(after['entries'][0]['classification_notes'][0]['is_note'])
        page = (self.project / knowledge.WIKI / f"{entry['id']}.md").read_text()
        self.assertIn('[备注] 人工确认：属于历史模板', page)

    def test_subject_and_title_are_part_of_duplicate_identity(self):
        first = knowledge.add_text(self.project, '同一段文字', title='甲公司材料', subject='甲公司')
        second = knowledge.add_text(self.project, '同一段文字', title='乙公司材料', subject='乙公司')
        duplicate = knowledge.add_text(self.project, '同一段文字', title='甲公司材料', subject='甲公司')
        self.assertEqual(first['entries_added'], 1)
        self.assertEqual(second['entries_added'], 1)
        self.assertEqual(duplicate['status'], 'duplicate')
        self.assertEqual(len(knowledge.load_index(self.project)['entries']), 2)

    def test_local_second_duplicate_rolls_back_new_registration(self):
        source = self.root / 'generic.txt'
        source.write_text('营业执照\n统一社会信用代码：9133', encoding='utf-8')
        first = knowledge.add_local(self.project, source)
        registry_before = bidkit.read(self.project / 'inputs/source-registry.json')
        duplicate = knowledge.add_local(self.project, source)
        self.assertEqual(first['entries_added'], 1)
        self.assertEqual(duplicate['status'], 'duplicate')
        self.assertEqual(bidkit.read(self.project / 'inputs/source-registry.json'), registry_before)
        self.assertEqual(len(knowledge.load_index(self.project)['entries']), 1)

    def test_pptx_field_failure_removes_only_its_generated_assets(self):
        existing = self.root / 'existing.md'
        existing.write_text('既有来源', encoding='utf-8')
        registered = bidkit.register_source(self.project, existing, 'supplier')
        pptx = self.root / 'with-image.pptx'
        with zipfile.ZipFile(pptx, 'w') as package:
            package.writestr(
                'ppt/slides/slide1.xml',
                '<p:sld xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">'
                '<p:cSld><p:spTree/></p:cSld></p:sld>',
            )
            package.writestr(
                'ppt/slides/_rels/slide1.xml.rels',
                '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                '<Relationship Id="rId1" '
                'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" '
                'Target="../media/image1.png"/></Relationships>',
            )
            package.writestr('ppt/media/image1.png', b'fake-image')
        assets_dir = self.project / 'assets' / 'knowledge'
        assets_dir.mkdir(parents=True)
        sentinel = assets_dir / f'{registered["source_id"]}-existing.png'
        sentinel.write_bytes(b'keep')
        with self.assertRaisesRegex(ValueError, '原文位置不存在'):
            knowledge.add_local(
                self.project, pptx, category='technical',
                metadata={'fields': {'version': {'value': 'V1', 'location': 'P99'}}},
            )
        self.assertEqual(
            bidkit.read(self.project / 'inputs/source-registry.json')['sources'],
            [registered],
        )
        self.assertTrue(sentinel.is_file())
        self.assertFalse(any(assets_dir.glob('SRC-002-*')))

    def test_local_field_mismatch_rolls_back_registered_source(self):
        source = self.root / 'personnel.txt'
        source.write_text('社保月份：2026-01', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, '不在原文位置'):
            knowledge.add_local(
                self.project, source, subject='甲公司', category='personnel',
                metadata={'fields': {'social_months': {'value': ['2026-02'], 'location': 'L1'}}})
        self.assertEqual(bidkit.read(self.project / 'inputs/source-registry.json')['sources'], [])
        self.assertFalse((self.project / 'artifacts/knowledge/index.json').exists())

    def test_failed_docx_pptx_parse_rolls_back_only_new_source(self):
        existing = self.root / 'existing.md'
        existing.write_text('既有来源', encoding='utf-8')
        registered = bidkit.register_source(self.project, existing, 'supplier')
        registry_before = bidkit.read(self.project / 'inputs/source-registry.json')
        input_before = sorted(path.relative_to(self.project).as_posix()
                              for path in (self.project / 'inputs').iterdir())

        for suffix in ('.docx', '.pptx'):
            with self.subTest(suffix=suffix):
                broken = self.root / f'broken{suffix}'
                broken.write_bytes(b'not a valid office package')
                with self.assertRaisesRegex(ValueError, '解析失败'):
                    knowledge.add_local(self.project, broken, title=broken.name)
                self.assertEqual(bidkit.read(self.project / 'inputs/source-registry.json'), registry_before)
                self.assertEqual(
                    sorted(path.relative_to(self.project).as_posix()
                           for path in (self.project / 'inputs').iterdir()),
                    input_before,
                )
                self.assertTrue((self.project / registered['relative_path']).is_file())

    def test_legacy_format_and_unread_scan_are_kept_with_gaps(self):
        legacy = self.root / 'legacy.doc'
        legacy.write_bytes(b'old binary format')
        legacy_result = knowledge.add_local(self.project, legacy)
        legacy_entry = knowledge.load_index(self.project)['entries'][0]
        self.assertEqual(legacy_result['status'], 'blocked')
        self.assertEqual(legacy_entry['status'], 'blocked')
        self.assertTrue((self.project / legacy_entry['source']['relative_path']).is_file())
        legacy_content = bidkit.read(self.project / legacy_entry['content']['relative_path'])
        self.assertIn('原件已按来源登记保留', '\n'.join(legacy_content['warnings']))

        scan = self.root / 'scan.png'
        scan.write_bytes(b'not-decoded-image')
        scan_result = knowledge.add_local(self.project, scan)
        scan_entry = knowledge.load_index(self.project)['entries'][1]
        self.assertEqual(scan_result['entries_added'], 1)
        self.assertEqual(scan_entry['status'], 'needs_review')
        scan_content = bidkit.read(self.project / scan_entry['content']['relative_path'])
        self.assertTrue(any('需显式--ocr' in warning for warning in scan_content['warnings']))
        self.assertTrue((self.project / scan_entry['source']['relative_path']).is_file())

    def test_asset_hash_is_validated_and_wiki_uses_page_relative_link(self):
        knowledge.add_text(self.project, '原图材料', title='原图')
        index = knowledge.load_index(self.project)
        entry = index['entries'][0]
        asset_path = self.project / 'assets' / 'knowledge' / 'figure.svg'
        asset_path.parent.mkdir(parents=True)
        asset_bytes = b'<svg><rect width="1" height="1"/></svg>'
        asset_path.write_bytes(asset_bytes)
        content_path = self.project / entry['content']['relative_path']
        content = bidkit.read(content_path)
        content['blocks'].append({
            'location': '原图', 'text': '[嵌入图片：figure.svg]', 'content_kind': 'asset',
            'asset': {'relative_path': 'assets/knowledge/figure.svg',
                      'sha256': hashlib.sha256(asset_bytes).hexdigest(), 'bytes': len(asset_bytes)},
        })
        content['blocks'].append({'location': '备注', 'text': '讲解者备注', 'is_note': True})
        bidkit.atomic(content_path, content)
        entry['content']['sha256'] = bidkit.digest(content_path)
        bidkit.atomic(self.project / knowledge.INDEX, index)
        knowledge.build_wiki(self.project)
        page = (self.project / knowledge.WIKI / f"{entry['id']}.md").read_text()
        self.assertIn('[原图：原图](../../../assets/knowledge/figure.svg)', page)
        self.assertIn('备注（非正文）', page)
        self.assertIn('../../../inputs/knowledge/', page)
        self.assertIn('../content/', page)
        asset_path.write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError, '原图'):
            knowledge.validate_index(self.project)

    def test_wiki_escapes_user_text_as_source_data(self):
        knowledge.add_text(self.project, '<script>alert(1)</script>', title='普通文字')
        entry = knowledge.load_index(self.project)['entries'][0]
        page = (self.project / knowledge.WIKI / f"{entry['id']}.md").read_text()
        self.assertNotIn('<script>', page)
        self.assertIn('&lt;script&gt;alert(1)&lt;/script&gt;', page)


if __name__ == '__main__':
    unittest.main()
