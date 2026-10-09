"""Presentation must preserve review evidence and reject stale bindings."""
import copy
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import render_review_report as renderer


class ReviewReportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.project = Path(self.temp.name)
        (self.project/'work').mkdir()
        (self.project/'work/project.json').write_text('{"project_id":"P1"}')
        source = self.project / 'original.txt'
        source.write_text('要求 & 引文 <script>alert(1)</script>')
        sha = hashlib.sha256(source.read_bytes()).hexdigest()
        self.row = {'target_id': 'S1', 'conclusion': 'partial', 'rationale': '当前只部分支撑，仍需补证。',
                    'sources': [{'sha256': sha, 'quote': source.read_text(), 'location': 'L1', 'source_id': 'SRC', 'revision': 1, 'kind': 'synthetic'}],
                    'bid_refs': [{'sha256': sha, 'relative_path': 'original.txt', 'quote': '要求', 'location': 'L1'}],
                    'score_estimate': None, 'finding_ids': ['F1'], 'dimensions': {}, 'dimension_exemptions': {}, 'material_ids': []}
        self.review = {'skill_id': 'bid-review-remediation', 'project_id': 'P1', 'revision': 1,
                       'status': 'blocked', 'summary': '本轮不能交付', 'artifact_id': 'REVIEW',
                       'schema_version': '1.0', 'created_at': '2026-10-09T00:00:00Z',
                       'inputs': [{'artifact_id': 'SOURCE', 'revision': 1, 'relative_path': 'original.txt', 'sha256': sha}],
                       'data': {'review_scope': 'limited', 'release_recommendation': 'blocked',
                                'core_matrix': {'compliance': [], 'materials': [], 'scoring': [self.row]},
                                'findings': [{'id': 'F1', 'severity': 'blocking', 'state': 'open', 'category': 'scoring', 'related_ids': ['S1'], 'evidence': self.row['sources'], 'confirmation_ref': None,
                                              'description': '证据缺口', 'remediation': '补齐再复核'}],
                                'limitations': ['仅本轮输入'], 'checks': [], 'human_approval_ref': None, 'reviewed_inputs_sha256': sha},
                       'warnings': ['未知不是零分'], 'blockers': ['证据缺口未关闭']}
        self.scoring = {'skill_id': 'bid-scoring', 'project_id': 'P1', 'status': 'needs_review',
                        'schema_version': '1.0', 'artifact_id': 'SCORE', 'revision': 1, 'created_at': '2026-10-09T00:00:00Z', 'summary': '原文条件', 'warnings': [], 'blockers': [],
                        'inputs': copy.deepcopy(self.review['inputs']), 'data': {'declared_total': 35, 'arithmetic_findings': [], 'unknowns': [], 'items': [
                            {'id': 'S1', 'node_type': 'scored', 'title': '技术方案', 'max_score': 35,
                             'rule_text': '原文条件', 'parent_id': None, 'aggregation': 'none', 'evidence_requirements': [], 'sources': self.row['sources']}]}}
        self.review_path = self.project / 'review.json'
        self.scoring_path = self.project / 'scoring.json'

    def save(self):
        self.scoring_path.write_text(json.dumps(self.scoring))
        self.review['inputs'] = [i for i in self.review['inputs'] if i['relative_path'] != 'scoring.json'] + [{
            'artifact_id': self.scoring['artifact_id'], 'revision': self.scoring['revision'], 'relative_path': 'scoring.json',
            'sha256': renderer.digest(self.scoring_path)}]
        self.review_path.write_text(json.dumps(self.review))

    def test_preserves_all_rows_findings_and_escaped_evidence_without_mutation(self):
        self.save()
        original = copy.deepcopy(self.review)
        result = renderer.generate(self.project, self.review_path, self.project / 'report.html', self.scoring_path)
        page = (self.project / 'report.html').read_text()
        self.assertEqual(self.review, original)
        for text in ['证据缺口', '补齐再复核', '当前只部分支撑', '35 分', '未知不是零分', '证据缺口未关闭']:
            self.assertIn(text, page)
        self.assertNotIn('<script>alert(1)</script>', page)
        self.assertIn('&lt;script&gt;', page)
        self.assertTrue(result['presentation_only'])
        self.assertIsNone(self.row['score_estimate'])

    def test_rejects_source_change_and_does_not_write_output(self):
        self.save()
        (self.project / 'original.txt').write_text('已修改')
        with self.assertRaisesRegex(ValueError, '输入哈希'):
            renderer.generate(self.project, self.review_path, self.project / 'report.html')
        self.assertFalse((self.project / 'report.html').exists())

    def test_rejects_unfrozen_reference(self):
        self.row['bid_refs'][0]['sha256'] = '0' * 64
        self.save()
        with self.assertRaisesRegex(ValueError, '正文引用版本'):
            renderer.generate(self.project, self.review_path, self.project / 'report.html')

    def test_rejects_mismatched_scoring_leaf_and_missing_matrix(self):
        self.scoring['data']['items'][0]['id'] = 'S2'
        with self.assertRaisesRegex(ValueError, '计分叶子'):
            renderer.build_page(self.review, self.scoring)
        del self.review['data']['core_matrix']['materials']
        with self.assertRaisesRegex(ValueError, '核心矩阵'):
            renderer.build_page(self.review)

    def test_rejects_path_escape_and_overwriting_existing_version(self):
        self.review['inputs'][0]['relative_path'] = '../original.txt'
        self.save()
        with self.assertRaisesRegex(ValueError, '越界'):
            renderer.generate(self.project, self.review_path, self.project / 'report.html')
        self.review['inputs'][0]['relative_path'] = 'original.txt'
        self.save()
        renderer.generate(self.project, self.review_path, self.project / 'report.html')
        with self.assertRaisesRegex(ValueError, '拒绝覆盖'):
            renderer.generate(self.project, self.review_path, self.project / 'report.html')

    def test_rejects_project_identity_unbound_scoring_and_invalid_eligibility(self):
        self.save()
        (self.project/'work/project.json').write_text('{"project_id":"OTHER"}')
        with self.assertRaisesRegex(ValueError, '项目身份'):
            renderer.generate(self.project, self.review_path, self.project/'report.html')
        (self.project/'work/project.json').write_text('{"project_id":"P1"}')
        self.review['inputs'] = self.review['inputs'][:1]
        self.review_path.write_text(json.dumps(self.review))
        with self.assertRaisesRegex(ValueError, '确切版本'):
            renderer.generate(self.project, self.review_path, self.project/'report.html', self.scoring_path)
        self.review['data']['release_recommendation'] = 'eligible_for_user_release'
        self.save()
        with self.assertRaisesRegex(ValueError, '交付建议'):
            renderer.generate(self.project, self.review_path, self.project/'report.html')


if __name__ == '__main__':
    unittest.main()
