"""Exercise real persisted chapter text and provenance rather than matching labels."""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import bidkit
import knowledge
import knowledge_context as context


class ContextTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.project = self.root / 'project'
        bidkit.init_project(self.project, 'CITATION-TEST')
        self.add('工单平台.md', '模拟资料：工单支持派单、处理、复核和关闭。')
        bidkit.atomic(self.project / 'artifacts/08-outline.json', {
            'data': {'sections': [{'id': 'SEC-1', 'title': '工单闭环'}]}})
        bidkit.atomic(self.project / 'artifacts/11-technical-content.json', {
            'project_id': 'CITATION-TEST', 'revision': 1, 'data': {'chapters': [
                {'id': 'CH-1', 'section_id': 'SEC-1',
                 'body_markdown': '【模拟测试】工单按派单、处理、复核和关闭推进。'}]}})

    def add(self, name, text):
        file = self.root / name
        file.write_text(text, encoding='utf-8')
        return knowledge.add_local(self.project, file, subject='测试企业')

    def bind(self):
        pack = context.prepare(self.project, 'SEC-1', '工单')
        citation = pack['candidates'][0]
        usages = [{'knowledge_id': citation['knowledge_id'], 'location': citation['location'],
                   'source_quote': citation['quote'], 'claim': '工单按派单、处理、复核和关闭推进',
                   'purpose': 'reference'}]
        return context.bind(self.project, 'CH-1', pack['relative_path'], usages)

    def test_binding_records_exact_source_and_visible_claim_without_changing_body(self):
        file = self.project / 'artifacts/11-technical-content.json'
        before = file.read_bytes()
        self.bind()
        self.assertEqual(before, file.read_bytes())
        result = context.check(self.project)
        self.assertTrue(result['valid'])
        self.assertEqual(result['bound_chapters'], 1)
        citations = bidkit.read(self.project / context.CITATIONS)['chapters'][0]['citations']
        self.assertIn('派单', citations[0]['source_quote'])

    def test_unsupported_quote_and_claim_cannot_become_citations(self):
        pack = context.prepare(self.project, 'SEC-1', '工单')
        candidate = pack['candidates'][0]
        for quote, claim in [('达到100%准确率', '工单'),
                             (candidate['quote'], '已服务一百家客户')]:
            with self.assertRaises(ValueError):
                context.bind(self.project, 'CH-1', pack['relative_path'], [{
                    'knowledge_id': candidate['knowledge_id'], 'location': candidate['location'],
                    'source_quote': quote, 'claim': claim, 'purpose': 'reference'}])

    def test_editing_body_invalidates_old_citations(self):
        self.bind()
        file = self.project / 'artifacts/11-technical-content.json'
        value = bidkit.read(file)
        value['data']['chapters'][0]['body_markdown'] += ' 新增承诺。'
        bidkit.atomic(file, value)
        result = context.check(self.project)
        self.assertFalse(result['valid'])
        self.assertIn('SEC-1', result['affected_sections'])

    def test_new_related_material_marks_only_related_reference_pack(self):
        self.bind()
        self.add('财务.md', '模拟财务资料：年度审计与现金流。')
        self.assertTrue(context.check(self.project)['valid'])
        self.add('工单补充.md', '模拟工单升级资料：增加超时升级。')
        result = context.check(self.project)
        self.assertFalse(result['valid'])
        self.assertEqual(result['affected_sections'], ['SEC-1'])

    def test_missing_material_stays_a_gap_and_unknown_section_rejected(self):
        pack = context.prepare(self.project, 'SEC-1', '不存在的社保证明')
        self.assertEqual(pack['candidates'], [])
        self.assertTrue(pack['gaps'])
        with self.assertRaises(ValueError):
            context.prepare(self.project, 'OTHER', '工单')

    def test_subject_hard_filter_does_not_accept_other_company(self):
        pack = context.prepare(self.project, 'SEC-1', '工单', criteria={'subject': '其他企业'})
        self.assertEqual(pack['candidates'], [])
        self.assertTrue(pack['excluded'])

    def test_unverified_normalized_dates_cannot_pass_hard_filter(self):
        file = self.root / '期限.md'
        text = '模拟工单证书有效期原文：二〇二六年十二月'
        file.write_text(text, encoding='utf-8')
        result = knowledge.add_local(self.project, file, subject='测试企业', metadata={
            'fields': {'valid_until': {'value': '2099-12-31', 'location': 'L1',
                                      'quote': '二〇二六年十二月'}}})
        entry = next(row for row in knowledge.load_index(self.project)['entries']
                     if row['id'] == result['ids'][0])
        self.assertTrue(entry['material']['fields']['valid_until']['needs_verification'])
        pack = context.prepare(self.project, 'SEC-1', '工单',
                               criteria={'valid_on': '2098-01-01'})
        self.assertEqual(pack['candidates'], [])
        reasons = '；'.join(reason for row in pack['excluded'] for reason in row['reasons'])
        self.assertIn('归一化值待核对', reasons)

    def test_proof_citation_requires_accepted_source_bound_material(self):
        file = self.root / '执照.md'
        file.write_text('测试企业营业执照与统一社会信用代码 TEST ONLY', encoding='utf-8')
        result = knowledge.add_local(self.project, file, subject='测试企业', category='enterprise')
        pack = context.prepare(self.project, 'SEC-1', '营业执照')
        candidate = next(row for row in pack['candidates'] if row['knowledge_id'] == result['ids'][0])
        usage = {'knowledge_id': candidate['knowledge_id'], 'location': candidate['location'],
                 'source_quote': candidate['quote'], 'claim': '工单', 'purpose': 'evidence'}
        with self.assertRaisesRegex(ValueError, 'material_id'):
            context.bind(self.project, 'CH-1', pack['relative_path'], [usage])
        evidence = {'project_id': 'CITATION-TEST', 'data': {
            'materials': [{'id': 'M1', 'sources': [{'source_id': candidate['source']['artifact_id'],
                                                   'sha256': candidate['source']['sha256']}]}],
            'selections': [{'id': 'SEL1', 'material_ids': ['M1'], 'state': 'candidate'}]}}
        bidkit.atomic(self.project / context.EVIDENCE, evidence)
        usage['material_id'] = 'M1'
        with self.assertRaisesRegex(ValueError, '尚未采纳'):
            context.bind(self.project, 'CH-1', pack['relative_path'], [usage])
        evidence['data']['selections'][0]['state'] = 'accepted'
        bidkit.atomic(self.project / context.EVIDENCE, evidence)
        context.bind(self.project, 'CH-1', pack['relative_path'], [usage])
        self.assertTrue(context.check(self.project)['valid'])
        evidence['data']['selections'][0]['state'] = 'candidate'
        bidkit.atomic(self.project / context.EVIDENCE, evidence)
        self.assertFalse(context.check(self.project)['valid'])

    def test_tampered_reference_pack_is_rejected(self):
        result = self.bind()
        path = self.project / result['pack']['relative_path']
        value = bidkit.read(path)
        value['query'] = '改写查询'
        bidkit.atomic(path, value)
        self.assertFalse(context.check(self.project)['valid'])


if __name__ == '__main__':
    unittest.main()
