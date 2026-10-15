"""Real loopback HTTP seams for the host-mediated scoring workspace."""
import json
import threading
import unittest
import urllib.error
import urllib.request
import uuid

import test_ai_scoring_actions as fixture
import bidkit
from writing_workspace import WritingWorkspace, create_server


class AIScoringHTTPTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixture.AIScoringActionsTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.tearDown)
        self.project = self.fixture.project
        writing = bidkit.read(self.project / 'artifacts/11-technical-content.json')
        writing['skill_id'] = 'bid-technical-writing'
        bidkit.atomic(self.project / 'artifacts/11-technical-content.json', writing)
        bidkit.atomic(self.project / 'artifacts/08-outline.json', {
            'project_id': 'TEST-AI-ACTIONS', 'skill_id': 'bid-outline-planning',
            'data': {'sections': [{'id': 'SEC-1', 'title': '技术方案'}]}})
        workspace = WritingWorkspace(self.project, 'artifacts/08-outline.json',
                                     'artifacts/11-technical-content.json')
        self.server = create_server(workspace)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self.close_server)
        self.base = f'http://127.0.0.1:{self.server.server_port}'

    def close_server(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)

    def request(self, path, payload=None, headers=None):
        request = urllib.request.Request(
            self.base + path,
            data=json.dumps(payload).encode() if payload is not None else None,
            headers={'Content-Type': 'application/json', **(headers or {})})
        try:
            response = urllib.request.urlopen(request, timeout=5)
        except urllib.error.HTTPError as error:
            response = error
        with response:
            body = response.read().decode()
            return response.status, body

    def score_request(self):
        revision, digest = self.fixture.cas()
        payload = {'action': 'score', 'request_id': str(uuid.uuid4()),
                   'expected_revision': revision, 'expected_sha256': digest}
        status, body = self.request('/api/ai-scoring', payload)
        self.assertEqual(status, 200, body)
        return payload, json.loads(body)['request']

    def test_empty_draft_and_completion_are_distinct_over_http(self):
        status, body = self.request('/api/ai-scoring')
        self.assertEqual(status, 200)
        self.assertIsNone(json.loads(body)['latest_report'])
        payload, request = self.score_request()
        status, body = self.request('/api/ai-scoring', payload)
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body)['request']['request_id'], request['request_id'])
        status, body = self.request('/api/ai-scoring/report')
        self.assertEqual(status, 409)
        self.assertEqual(json.loads(body)['error']['code'], 'invalid_report')
        self.fixture.service.claim(request['request_id'])
        self.fixture.completed_report(self.project / request['report_relative_path'])
        self.fixture.service.finish(request['request_id'], self.fixture.evidence(request))
        status, body = self.request('/api/ai-scoring/report')
        self.assertEqual(status, 200, body)
        self.assertIn('AI 模拟专家评分', body)
        self.assertIn('/api/file?path=', body)
        (self.project / 'assets/new.txt').write_text('changed input')
        status, body = self.request('/api/ai-scoring/report')
        self.assertEqual(status, 409)

    def test_origin_cas_and_arbitrary_report_are_rejected(self):
        status, _ = self.request('/api/ai-scoring', headers={'Origin': 'https://example.com'})
        self.assertEqual(status, 403)
        revision, digest = self.fixture.cas()
        payload = {'action': 'score', 'request_id': str(uuid.uuid4()),
                   'expected_revision': revision + 1, 'expected_sha256': digest}
        status, body = self.request('/api/ai-scoring', payload)
        self.assertEqual(status, 409)
        self.assertEqual(json.loads(body)['error']['code'], 'stale_write')
        _, request = self.score_request()
        self.fixture.service.claim(request['request_id'])
        self.fixture.completed_report(self.project / request['report_relative_path'])
        self.fixture.service.finish(request['request_id'], self.fixture.evidence(request))
        status, body = self.request('/api/ai-scoring/report?path=../outside.html')
        self.assertEqual(status, 409)
        self.assertEqual(json.loads(body)['error']['code'], 'invalid_report')


if __name__ == '__main__':
    unittest.main()
