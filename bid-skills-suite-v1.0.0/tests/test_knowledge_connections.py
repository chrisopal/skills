"""The host bridge is exercised with explicitly synthetic tool responses."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import bidkit
import knowledge
import knowledge_connections as connections


class ConnectionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.project = self.root / 'project'
        bidkit.init_project(self.project, 'KB-TEST')
        connections.configure(self.project, 'team', provider='synthetic-host',
                              resource_ref='https://example.invalid/wiki/team',
                              tool_name='synthetic_search', permission_scope='TEST-TEAM',
                              allowed_sources=['https://example.invalid/docs'])

    def response(self, request):
        return {'request_id': request['request_id'],
                'resource_ref': request['resource_ref'], 'outcome': 'success',
                'host_result': {
                    'project_id': 'KB-TEST', 'provider': 'synthetic-host',
                    'tool_name': 'synthetic_search', 'retrieval_ref': 'SYNTHETIC-CALL',
                    'query': request['query'], 'retrieved_at': bidkit.now(),
                    'permission_scope': 'TEST-TEAM',
                    'results': [{'document_id': 'D1', 'title': '模拟技术参考',
                                 'source_ref': 'https://example.invalid/docs/d1',
                                 'revision': 'r1', 'location': '第1节',
                                 'text': '模拟资料：工单状态可按事件跟踪。'}]}}

    def ingest(self, request, response):
        path = self.root / 'response.json'
        path.write_text(json.dumps(response, ensure_ascii=False))
        return connections.ingest(self.project, request['relative_path'], path)

    def test_configuration_is_not_a_successful_host_call(self):
        self.assertEqual(connections.status(self.project, 'team')['state'], 'configured')
        request = connections.request(self.project, 'team', '工单闭环')
        result = self.ingest(request, self.response(request))
        self.assertFalse(result['host_call_verified'])
        self.assertEqual(knowledge.load_index(self.project)['entries'][0]['connection_id'], 'team')
        self.assertEqual(connections.status(self.project, 'team')['state'], 'snapshot_saved')

    def test_scope_escape_and_deceptive_url_rejected_before_import(self):
        for url in ('https://example.invalid/other/d1',
                    'https://example.invalid/docs-evil/d1',
                    'https://example.invalid/docs/../other/d1'):
            request = connections.request(self.project, 'team', '工单闭环')
            response = self.response(request)
            response['host_result']['results'][0]['source_ref'] = url
            with self.assertRaises(ValueError):
                self.ingest(request, response)
        self.assertEqual(knowledge.load_index(self.project)['entries'], [])

    def test_scope_query_tool_and_project_must_match_actual_request(self):
        for key, value in [('query', '其他查询'), ('tool_name', 'other'),
                           ('project_id', 'OTHER'), ('permission_scope', 'OTHER')]:
            request = connections.request(self.project, 'team', '工单闭环')
            response = self.response(request)
            response['host_result'][key] = value
            with self.assertRaises(ValueError):
                self.ingest(request, response)

    def test_empty_result_and_permission_failure_are_distinct(self):
        request = connections.request(self.project, 'team', '无命中')
        response = self.response(request)
        response['host_result']['results'] = []
        self.assertEqual(self.ingest(request, response)['entries_added'], 0)
        request = connections.request(self.project, 'team', '受限资料')
        response = {'request_id': request['request_id'], 'resource_ref': request['resource_ref'],
                    'outcome': 'permission_denied', 'message': '合成权限失败测试'}
        self.ingest(request, response)
        self.assertEqual(connections.status(self.project, 'team')['state'], 'permission_denied')
        self.assertFalse(connections.status(self.project, 'team')['usable'])

    def test_reconfigured_connection_rejects_old_request(self):
        request = connections.request(self.project, 'team', '工单闭环')
        connections.configure(self.project, 'team', provider='synthetic-host',
                              resource_ref='https://example.invalid/wiki/new',
                              tool_name='synthetic_search', permission_scope='TEST-NEW',
                              allowed_sources=['https://example.invalid/newdocs'])
        with self.assertRaisesRegex(ValueError, '连接.*变更'):
            self.ingest(request, self.response(request))

    def test_credentials_are_not_configuration(self):
        with self.assertRaises(ValueError):
            connections.configure(self.project, 'bad', provider='host',
                                  resource_ref='https://example.invalid/?access_token=SECRET',
                                  tool_name='search', permission_scope='TEAM', allowed_sources=[])

    def test_sensitive_query_is_rejected_before_persisting_request(self):
        config = (self.project / connections.CONFIG).read_bytes()
        for query in ('工单\nAuthorization: Bearer SYNTHETIC-SECRET', 'Bearer SYNTHETIC-SECRET'):
            with self.assertRaises(ValueError):
                connections.request(self.project, 'team', query)
        self.assertEqual((self.project / connections.CONFIG).read_bytes(), config)
        self.assertFalse((self.project / 'inputs/knowledge/requests').exists())

    def test_new_search_does_not_renew_other_document_snapshot(self):
        from datetime import datetime, timedelta, timezone
        from unittest.mock import patch
        import knowledge_context as context
        bidkit.atomic(self.project / context.OUTLINE, {'data': {'sections': [{'id': 'SEC-1'}]}})
        first = connections.request(self.project, 'team', 'OLD-UNIQUE')
        response = self.response(first)
        response['host_result']['results'][0]['text'] = 'OLD-UNIQUE 原文'
        first_id = self.ingest(first, response)['ids'][0]
        future = datetime.now(timezone.utc) + timedelta(hours=25)
        # Advance the clock, then retrieve an unrelated document on the same connection.
        with patch.object(bidkit, 'now', return_value=future.isoformat()), patch.object(connections, 'datetime') as clock:
            clock.now.return_value = future
            clock.fromisoformat.side_effect = datetime.fromisoformat
            second = connections.request(self.project, 'team', 'NEW-UNIQUE')
            response = self.response(second)
            response['host_result']['results'][0].update(document_id='D2', text='NEW-UNIQUE 原文',
                                                       source_ref='https://example.invalid/docs/d2')
            self.ingest(second, response)
            with patch.object(context, 'datetime') as context_clock:
                context_clock.now.return_value = future
                context_clock.fromisoformat.side_effect = datetime.fromisoformat
                pack = context.prepare(self.project, 'SEC-1', 'OLD-UNIQUE')
                self.assertNotIn(first_id, [row['knowledge_id'] for row in pack['candidates']])
                self.assertTrue(any('快照已过期' in reason for row in pack['excluded'] for reason in row['reasons']))

    def test_permission_failure_requires_individual_document_refresh(self):
        import knowledge_context as context
        bidkit.atomic(self.project / context.OUTLINE, {'data': {'sections': [{'id': 'SEC-1'}]}})
        first = connections.request(self.project, 'team', '工单')
        first_id = self.ingest(first, self.response(first))['ids'][0]
        denied = connections.request(self.project, 'team', '受限资料')
        self.ingest(denied, {'request_id': denied['request_id'], 'resource_ref': denied['resource_ref'],
                             'outcome': 'permission_denied', 'message': '模拟撤权'})
        second = connections.request(self.project, 'team', '其他工单')
        response = self.response(second)
        response['host_result']['results'][0].update(document_id='D2', source_ref='https://example.invalid/docs/d2')
        self.ingest(second, response)
        pack = context.prepare(self.project, 'SEC-1', '工单')
        self.assertNotIn(first_id, [row['knowledge_id'] for row in pack['candidates']])
        self.assertTrue(any('权限失败' in reason for row in pack['excluded'] for reason in row['reasons']))


if __name__ == '__main__':
    unittest.main()
