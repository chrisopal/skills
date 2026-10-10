"""Real bound-review regression fixtures; these never certify tender semantics."""
import sys
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import bidkit
import quality_checks
import review_actions
import test_quality_checks as quality_fixture


class ReviewActionsTest(unittest.TestCase):
    def setUp(self):
        fixture = quality_fixture.QualityChecksTests()
        fixture.setUp()
        self.addCleanup(fixture.tearDown)
        self.project = fixture.project
        self.plan = fixture.plan
        self.review = fixture.review
        self.plan['conditions'][0]['description'] = '正文说明异常处理流程和验收方法'
        self.review['conditions'][0].update(conclusion='partial', rationale='正文缺少异常处理流程')
        writing = bidkit.read(self.project / 'artifacts/11-technical-content.json')
        writing.update(revision=1)
        writing['data']['chapters'][0]['section_id'] = 'CH-1'
        writing['data']['chapters'].append({'id': 'CH2', 'section_id': 'CH-2', 'body': '另一个章节'})
        bidkit.atomic(self.project / 'artifacts/11-technical-content.json', writing)
        bidkit.atomic(self.project / 'artifacts/08-outline.json', {'data': {'sections': [
            {'id': 'CH-1', 'title': '技术方案', 'scoring_ids': ['S1']},
            {'id': 'CH-2', 'title': '实施计划', 'scoring_ids': []}]}})
        self.refresh_review()
        self.service = review_actions.ReviewActionService(self.project)

    def refresh_review(self):
        sha = bidkit.digest(self.project / 'artifacts/11-technical-content.json')
        for row in self.plan['facts']:
            for ref in row.get('body_refs', []): ref['sha256'] = sha
        for row in self.review['conditions']:
            for ref in row.get('body_refs', []): ref['sha256'] = sha
        for row in self.review['facts']:
            for ref in row.get('body_refs', []): ref['sha256'] = sha
        bidkit.atomic(self.project / 'profiles/quality-plan.json', self.plan)
        self.review['plan_ref']['sha256'] = bidkit.digest(self.project / 'profiles/quality-plan.json')
        bidkit.atomic(self.project / 'reviews/quality-review.json', self.review)
        self.assertEqual(quality_checks.check(self.project)['errors'], [])

    def payload(self, action='repair', scope='chapter', section_id='CH-1'):
        w = bidkit.read(self.project / 'artifacts/11-technical-content.json')
        return {'action': action, 'scope': scope, 'section_id': section_id,
                'expected_revision': w['revision'],
                'expected_sha256': bidkit.digest(self.project / 'artifacts/11-technical-content.json'),
                'request_id': str(uuid.uuid4())}

    def create(self, **kwargs): return self.service.request(self.payload(**kwargs))

    def mutate(self, index=0, body=' 补充异常回滚流程及验收测试。'):
        w = bidkit.read(self.project / 'artifacts/11-technical-content.json')
        w['data']['chapters'][index]['body'] += body
        w['revision'] += 1
        bidkit.atomic(self.project / 'artifacts/11-technical-content.json', w)

    def evidence(self, req, **overrides):
        data = {'project_id': 'TEST-QUALITY', 'request_id': req['request_id'],
                'tool_or_agent': 'TEST host', 'performed_actions': ['TEST 修改目标正文并重评']}
        data.update(overrides)
        bidkit.atomic(self.project / 'work/action-evidence.json', data)
        return 'work/action-evidence.json'

    def assert_error(self, code, fn, *args):
        with self.assertRaises(review_actions.ReviewActionError) as caught: fn(*args)
        self.assertEqual(caught.exception.code, code)

    def test_create_claim_uses_single_current_review_binding(self):
        req = self.create()
        self.assertEqual(req['status'], 'awaiting_host')
        self.assertNotEqual(self.service.view()['latest_request']['status'], 'stale')
        self.assertEqual(self.service.claim(req['request_id'])['status'], 'claimed')
        self.assertIn(str(self.project), req['prompt'])
        self.assertEqual(self.service.view()['host_execution'], 'manual_handoff')

    def test_uuid_replay_is_idempotent_but_conflicting_reuse_rejected(self):
        payload = self.payload(); req = self.service.request(payload)
        self.assertEqual(self.service.request(payload), req)
        payload['action'] = 'rewrite'
        self.assert_error('request_conflict', self.service.request, payload)

    def test_duplicate_click_with_new_uuid_is_rejected(self):
        self.create()
        self.assert_error('duplicate_active', self.create)

    def test_missing_and_stale_reviews_block_request(self):
        (self.project / 'reviews/quality-review.json').unlink()
        self.assert_error('missing_review', self.create)
        self.refresh_review(); self.mutate()
        self.assert_error('stale_review', self.create)

    def test_claim_detects_changed_body_and_upstream(self):
        req = self.create()
        (self.project / 'assets/changed.txt').write_text('new input')
        self.assert_error('stale_request', self.service.claim, req['request_id'])
        self.assertEqual(self.service.view()['latest_request']['status'], 'stale')

    def test_cas_invalid_scope_and_unsafe_uuid(self):
        for change, code in [({'expected_revision': 0}, 'stale_write'),
                             ({'request_id': '../bad'}, 'invalid_input'),
                             ({'action': 'execute-shell'}, 'invalid_input')]:
            payload = self.payload(); payload.update(change)
            self.assert_error(code, self.service.request, payload)

    def test_evidence_qualification_is_not_rewritable(self):
        self.plan['conditions'][0]['kind'] = 'evidence'
        self.review['conditions'][0]['rationale'] = '缺少真实企业资质原件'
        self.refresh_review()
        for action in ['repair', 'rewrite', 'improve']:
            req = self.create(action=action)
            self.assertEqual(req['status'], 'needs_input')
            self.assert_error('requires_input', self.service.claim, req['request_id'])

    def test_passing_chapter_can_be_rewritten_or_improved(self):
        self.review['conditions'][0]['conclusion'] = 'satisfied'; self.refresh_review()
        for action in ['rewrite', 'improve']:
            self.assertEqual(self.create(action=action)['status'], 'awaiting_host')

    def test_finish_requires_claim_and_actual_target_body_change(self):
        req = self.create(); ev = self.evidence(req)
        self.assert_error('invalid_state', self.service.finish, req['request_id'], ev)
        self.service.claim(req['request_id'])
        self.assert_error('no_content_change', self.service.finish, req['request_id'], ev)
        self.mutate(index=1); self.refresh_review()
        self.assert_error('scope_changed', self.service.finish, req['request_id'], ev)

    def test_revision_only_is_not_body_change(self):
        req = self.create(); self.service.claim(req['request_id'])
        w = bidkit.read(self.project / 'artifacts/11-technical-content.json'); w['revision'] += 1
        bidkit.atomic(self.project / 'artifacts/11-technical-content.json', w)
        self.assert_error('no_content_change', self.service.finish, req['request_id'], self.evidence(req))

    def test_finish_requires_well_formed_host_evidence(self):
        req = self.create(); self.service.claim(req['request_id'])
        for override in [{'performed_actions': 'not-list'}, {'tool_or_agent': ' '},
                         {'request_id': str(uuid.uuid4())}, {'project_id': 'OTHER'}]:
            self.assert_error('invalid_evidence', self.service.finish, req['request_id'], self.evidence(req, **override))
        self.assert_error('path_traversal', self.service.finish, req['request_id'], '../evidence.json')

    def test_old_review_cannot_complete_changed_draft(self):
        req = self.create(); self.service.claim(req['request_id']); self.mutate()
        self.assert_error('stale_review', self.service.finish, req['request_id'], self.evidence(req))

    def test_two_rounds_persist_and_new_uuid_does_not_reset_limit(self):
        req = self.create(); ev = self.evidence(req)
        for index in [1, 2]:
            self.service.claim(req['request_id']); self.mutate(body=f' 第{index}轮异常处置。')
            self.refresh_review()
            result = self.service.finish(req['request_id'], ev)
            self.assertEqual(len(result['attempts']), index)
            self.assertNotIn('formal_release_ready', result)
        self.assertEqual(result['status'], 'attempts_exhausted')
        self.assert_error('attempts_exhausted', self.create)

    def test_shared_write_lock_and_no_shell_execution(self):
        with patch('subprocess.run', side_effect=AssertionError('must not spawn')):
            req = self.create(); self.service.claim(req['request_id'])
        self.assertTrue((self.project / 'work/.writing-workspace.lock').exists())

    def test_different_actions_cannot_claim_same_chapter_concurrently(self):
        repair = self.create(); improve = self.create(action='improve')
        self.service.claim(repair['request_id'])
        self.assert_error('duplicate_active', self.service.claim, improve['request_id'])

    def test_unknown_section_rejected(self):
        payload = self.payload(section_id='NO-SECTION')
        self.assert_error('not_found', self.service.request, payload)

    def test_core_closed_findings_are_not_active(self):
        core = self.project / 'reviews/15-review.json'
        bidkit.atomic(core, {'data': {'findings': [{'id': 'OLD', 'state': 'closed', 'severity': 'blocking'}]}})
        bidkit.atomic(self.project / 'reviews/current-snapshot.json', {})
        with patch('review_checks.check', return_value={'current': True, 'errors': [], 'release_blockers': ['TEST business blocker']}):
            findings, _, _ = review_actions._current_reviews(self.project)
        self.assertNotIn('OLD', [f['id'] for f in findings])


if __name__ == '__main__': unittest.main()
