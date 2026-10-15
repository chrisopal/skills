import hashlib
from pathlib import Path
import tempfile
import unittest

from opportunity_skill.pipeline import run_analyze, run_detail, run_manage, run_query
from opportunity_skill.storage import OpportunitySQLiteAdapter


class IncrementalWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.db = self.root / 'project.db'
        first = run_analyze({'request_id': 'create', 'owner': '原负责人',
            'materials': [{'evidence_id': 'ev1', 'content': '联系人：王敏，业务负责人。客户需要工单管理方案。'}],
            'sales_confirmation_answers': [{'dimension_id': 'customer_relationship', 'rating': 'strong',
                'answer_text': '王总支持我们', 'answered_by': 'Alice'}]}, self.db)
        self.oid = first['storage_result']['opportunity_id']

    def tearDown(self):
        self.temp.cleanup()

    def manage(self, operations, request_id='change', expected_revision=1):
        return run_manage(self.db, {'opportunity_id': self.oid, 'request_id': request_id,
            'actor': '主管', 'expected_revision': expected_revision, 'operations': operations})

    def test_incremental_preserves_confirmation_owner_and_current_projections(self):
        before = run_detail(self.db, self.oid)['detail']
        second = run_analyze({'request_id': 'update', 'opportunity_id': self.oid, 'expected_revision': 1,
            'materials': [{'evidence_id': 'ev2', 'content': '# 模拟跟进与结果\n业务负责人王敏安排下周开会讨论方案。'}]}, self.db)
        detail = second['structured_data']
        self.assertEqual(detail['lifecycle']['owner'], '原负责人')
        self.assertEqual(detail['sales_confirmation_answers'][0]['answer_text'], '王总支持我们')
        self.assertEqual(detail['sales_confirmation_answers'][0]['answered_by'], 'Alice')
        self.assertEqual(len(detail['decision_chain']), len(before['decision_chain']))
        self.assertEqual({c['name'] for c in detail['contacts']}, {'王敏'})
        self.assertEqual(len(detail['risks']), len(before['risks']))
        self.assertEqual(len(detail['next_actions']), len(before['next_actions']))
        third = run_analyze({'request_id': 'revise-answer', 'opportunity_id': self.oid, 'expected_revision': 2,
            'sales_confirmation_answers': [{'dimension_id': 'customer_relationship', 'rating': 'unknown',
                'answer_text': '不知道', 'answered_by': 'Bob'}]}, self.db)
        self.assertEqual(third['structured_data']['sales_confirmation_answers'][0]['answered_by'], 'Bob')
        dimension = next(d for d in third['structured_data']['commercial_assessment']['dimensions'] if d['dimension_id'] == 'customer_relationship')
        self.assertEqual(dimension['evidence_status'], 'needs_sales_confirmation')

    def test_owner_reassignment_keeps_actual_history(self):
        result = self.manage([{'type': 'set_owner', 'owner': '新负责人', 'reason': '区域调整'}])
        self.assertEqual(result['lifecycle']['owner'], '新负责人')
        history = result['lifecycle']['owner_history']
        self.assertEqual(history[-1]['from_owner'], '原负责人')
        self.assertEqual(history[-1]['actor'], '主管')
        self.assertEqual(history[-1]['reason'], '区域调整')

    def test_query_exports_real_detail_navigation(self):
        output = self.root / 'query'
        query = run_query(self.db, {}, output, render_html=True)
        path = query['opportunities'][0]['detail_url']
        self.assertTrue((output / path).is_file())
        self.assertIn(path, query['display_result']['html'])

    def test_explicit_null_owner_is_rejected_atomically(self):
        with self.assertRaises(ValueError):
            run_analyze({'request_id': 'null-owner', 'opportunity_id': self.oid,
                'expected_revision': 1, 'owner': None}, self.db)
        adapter = OpportunitySQLiteAdapter(self.db)
        try:
            self.assertEqual(adapter.get_lifecycle(self.oid)['revision'], 1)
        finally:
            adapter.close()

    def test_export_links_only_to_registered_bytes_and_replay_refreshes_state(self):
        source = self.root / '方案 空格.md'
        source.write_text('registered solution', encoding='utf-8')
        operations = [{'type': 'register_artifact', 'artifact_id': 's1', 'kind': 'solution', 'version': 1,
            'file_path': str(source), 'evidence': ['ev1']}, {'type': 'confirm_fact', 'fact_id': 'solution_scope', 'artifact_id': 's1',
            'value': '工单管理', 'evidence': ['ev1']}, {'type': 'transition', 'to_stage': 'solution_cocreation',
            'reason': '方案已核验', 'evidence': ['ev1']}]
        self.manage(operations)
        exported = run_detail(self.db, self.oid, self.root / 'views')['detail']['lifecycle']['artifacts'][0]
        target = self.root / 'views' / exported['relative_path']
        self.assertTrue(target.is_file())
        self.assertEqual(hashlib.sha256(target.read_bytes()).hexdigest(), exported['sha256'])
        self.manage([{'type': 'set_owner', 'owner': '负责人二', 'reason': '转派'}], 'transfer', 2)
        source.write_text('changed bytes')
        replay = self.manage(operations)
        self.assertTrue(replay['idempotent_replay'])
        self.assertEqual(replay['revision'], 2)
        self.assertEqual(replay['current_revision'], 3)
        self.assertEqual(replay['lifecycle']['verification_status'], 'needs_review')
        stale = run_detail(self.db, self.oid, self.root / 'stale')['detail']['lifecycle']['artifacts'][0]
        self.assertNotIn('relative_path', stale)


if __name__ == '__main__':
    unittest.main()
