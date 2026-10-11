import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from opportunity_skill.extractor import analyze
from opportunity_skill.storage import OpportunitySQLiteAdapter


class LifecycleTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = OpportunitySQLiteAdapter(Path(self.tmp.name) / 'test.db')
        self.seed = {'materials': [{'evidence_id': 'ev1', 'content': '客户需要 MES 集成，请安排方案交流。'}]}
        self.saved = self.db.save_structured_data(analyze(self.seed), request={'request_id': 'seed'})
        self.oid = self.saved['opportunity_id']

    def tearDown(self):
        self.db.close()
        self.tmp.cleanup()

    def change(self, operations, **kwargs):
        return self.db.manage({'request_id': kwargs.pop('request_id', 'change'), 'opportunity_id': self.oid,
                               'expected_revision': kwargs.pop('expected_revision', 1), 'actor': '销售负责人', 'operations': operations, **kwargs})

    def test_no_invented_history_and_stable_update(self):
        state = self.db.get_opportunity_detail(self.oid)['lifecycle']
        self.assertEqual(state['current_stage_id'], 'lead_identified')
        self.assertEqual(state['history'], [])
        self.db.save_structured_data(analyze(self.seed), request={'request_id': 'update', 'opportunity_id': self.oid, 'expected_revision': 1})
        self.assertEqual(len(self.db.query_opportunities({})), 1)
        self.assertEqual(self.db.get_opportunity_detail(self.oid)['lifecycle']['revision'], 2)

    def test_idempotent_and_conflict_atomicity(self):
        ops = [{'type': 'confirm_fact', 'fact_id': 'contact_established', 'value': True, 'evidence': ['ev1']}, {'type': 'transition', 'to_stage': 'customer_contacted', 'reason': '已沟通', 'evidence': ['ev1']}]
        first = self.change(ops)
        self.assertTrue(self.change(ops)['idempotent_replay'])
        self.assertEqual(first['revision'], 2)
        with self.assertRaises(ValueError):
            self.change(ops, request_id='stale')
        with self.assertRaises(ValueError):
            self.change([{'type': 'add_action', 'title': '跟进', 'owner': '王', 'due_date': '2026-10-12'}, {'type': 'transition', 'to_stage': 'won', 'reason': '成交', 'evidence': ['ev1']}], request_id='fail', expected_revision=2)
        state = self.db.get_opportunity_detail(self.oid)['lifecycle']
        self.assertEqual(state['revision'], 2)
        self.assertEqual(state['actions'], [])
        with self.assertRaises(ValueError):
            self.change([], request_id='change', expected_revision=2)

    def test_evidence_ownership_and_missing(self):
        for ref in ['missing', 'other']:
            if ref == 'other':
                self.db.append_evidence({'evidence_id': ref, 'content': '不属于本商机'})
            with self.assertRaises(ValueError):
                self.change([{'type': 'confirm_fact', 'fact_id': 'need', 'value': 'MES', 'evidence': [ref]}], request_id=ref)

    def test_action_result_pause_resume(self):
        self.change([{'type': 'add_action', 'action_id': 'a1', 'title': '验证接口', 'owner': '李', 'due_date': '2026-10-12'}, {'type': 'set_status', 'status': 'paused', 'reason': '客户延期', 'evidence': ['ev1']}])
        state = self.db.get_opportunity_detail(self.oid)['lifecycle']
        self.assertEqual(state['status'], 'paused')
        self.assertEqual(state['current_stage_id'], 'lead_identified')
        self.assertEqual(state['next_action']['id'], 'a1')
        self.change([{'type': 'set_status', 'status': 'active', 'reason': '客户恢复', 'evidence': ['ev1']}, {'type': 'complete_action', 'action_id': 'a1', 'result': '接口确认', 'evidence': ['ev1']}], request_id='resume', expected_revision=2)
        self.assertIsNone(self.db.get_opportunity_detail(self.oid)['lifecycle']['next_action'])

    def test_contract_requires_file_metadata_signatures_and_hash(self):
        path = Path(self.tmp.name) / 'signed.pdf'
        path.write_bytes(b'simulated signed contract for test')
        artifact = {'type': 'register_artifact', 'artifact_id': 'contract-v1', 'kind': 'contract', 'version': 1, 'file_path': str(path), 'evidence': ['ev1']}
        contract = {'type': 'record_contract', 'artifact_id': 'contract-v1', 'signing_date': '2026-10-11', 'parties': ['客户公司', '供应商公司'], 'amount': 123, 'currency': 'CNY', 'signature_facts': {'customer_signed': True, 'supplier_signed': True}, 'evidence': ['ev1']}
        transition = {'type': 'transition', 'to_stage': 'won', 'reason': '双方签署已登记', 'evidence': ['ev1']}
        self.change([artifact, contract])
        path.write_bytes(b'changed')
        with self.assertRaises(ValueError):
            self.change([transition], request_id='stale-file', expected_revision=2)
        path.write_bytes(b'simulated signed contract for test')
        self.change([transition], request_id='won', expected_revision=2)
        state = self.db.get_opportunity_detail(self.oid)['lifecycle']
        self.assertEqual(state['current_stage_id'], 'won')
        self.assertEqual(state['status'], 'won')
        self.assertEqual(state['history'][0]['from_stage'], 'lead_identified')
        self.assertEqual(state['artifacts'][0]['sha256'], hashlib.sha256(path.read_bytes()).hexdigest())

    def test_new_opportunity_can_share_explicit_account(self):
        saved = self.db.save_structured_data(analyze({'materials': [{'content': '另一个项目'}]}), request={'account_id': self.saved['account_id'], 'request_id': 'new'})
        self.assertNotEqual(saved['opportunity_id'], self.oid)
        self.assertEqual(saved['account_id'], self.saved['account_id'])

    def test_negative_fact_supersedes_and_unknown_optional_budget_does_not_block(self):
        self.change([{'type': 'confirm_fact', 'fact_id': 'budget_confirmed', 'value': 'unknown', 'evidence': ['ev1']},
                     {'type': 'confirm_fact', 'fact_id': 'contact_established', 'value': True, 'evidence': ['ev1']},
                     {'type': 'transition', 'to_stage': 'customer_contacted', 'reason': '沟通确认', 'evidence': ['ev1']}])
        self.change([{'type': 'confirm_fact', 'fact_id': 'contact_established', 'value': False, 'evidence': ['ev1']}], request_id='revoke', expected_revision=2)
        state = self.db.get_lifecycle(self.oid)
        self.assertEqual(state['verification_status'], 'needs_review')
        self.assertEqual(state['facts'][-1]['value'], False)
        with self.assertRaises(ValueError):
            self.change([{'type': 'transition', 'to_stage': 'lead_identified', 'reason': '测试阻塞', 'evidence': ['ev1']}], request_id='blocked', expected_revision=3)

    def test_stale_quote_blocks_negotiation_and_revoked_authorization_blocks_signing(self):
        quote = Path(self.tmp.name) / 'quote.txt'
        negotiation = Path(self.tmp.name) / 'negotiation.txt'
        quote.write_text('quote v1')
        negotiation.write_text('negotiation v1')
        self.change([{'type': 'register_artifact', 'artifact_id': 'quote1', 'kind': 'quote', 'version': 1, 'file_path': str(quote), 'evidence': ['ev1']},
                     {'type': 'confirm_fact', 'fact_id': 'quote_authorized', 'value': True, 'artifact_id': 'quote1', 'evidence': ['ev1']},
                     {'type': 'transition', 'to_stage': 'proposal_bidding', 'reason': '授权已报价', 'evidence': ['ev1']}])
        quote.write_text('changed')
        self.assertEqual(self.db.get_lifecycle(self.oid)['verification_status'], 'needs_review')
        with self.assertRaises(ValueError):
            self.change([{'type': 'register_artifact', 'kind': 'negotiation', 'version': 1, 'file_path': str(negotiation), 'evidence': ['ev1']},
                         {'type': 'transition', 'to_stage': 'commercial_negotiation', 'reason': '进入谈判', 'evidence': ['ev1']}], expected_revision=2, request_id='stale')
        quote.write_text('quote v1')
        self.change([{'type': 'confirm_fact', 'fact_id': 'quote_authorized', 'value': False, 'evidence': ['ev1']}], expected_revision=2, request_id='revoke')
        with self.assertRaises(ValueError):
            self.change([{'type': 'transition', 'to_stage': 'contract_signing', 'reason': '签署', 'evidence': ['ev1']}], expected_revision=3, request_id='sign')

    def test_lost_reopen_preserves_stage_and_reason_history(self):
        self.change([{'type': 'set_status', 'status': 'lost', 'reason': '客户选择其他供应商', 'evidence': ['ev1']}])
        self.change([{'type': 'set_status', 'status': 'active', 'reason': '同一项目重新采购', 'evidence': ['ev1']}], expected_revision=2, request_id='reopen')
        state = self.db.get_lifecycle(self.oid)
        self.assertEqual(state['current_stage_id'], 'lead_identified')
        self.assertEqual(state['status'], 'active')
        self.assertEqual(state['history'], [])
        self.assertEqual(state['status_history'][0]['reason'], '客户选择其他供应商')

    def test_won_handoff_and_stale_file_readback(self):
        path = Path(self.tmp.name) / 'signed.txt'
        path.write_text('signed')
        self.change([{'type': 'register_artifact', 'artifact_id': 'c1', 'kind': 'contract', 'version': 1, 'file_path': str(path), 'evidence': ['ev1']},
                     {'type': 'record_contract', 'artifact_id': 'c1', 'signing_date': '2026-10-11', 'parties': ['客户', '供应商'], 'amount': 0, 'currency': 'CNY', 'signature_facts': {'customer_signed': True, 'supplier_signed': True}, 'evidence': ['ev1']},
                     {'type': 'transition', 'to_stage': 'won', 'reason': '双方签署登记', 'evidence': ['ev1']}])
        self.change([{'type': 'register_artifact', 'kind': 'handoff', 'version': 1, 'file_path': str(path), 'evidence': ['ev1']}], expected_revision=2, request_id='handoff')
        path.write_text('changed after won')
        state = self.db.get_lifecycle(self.oid)
        self.assertEqual(state['status'], 'won')
        self.assertEqual(state['verification_status'], 'needs_review')
        self.assertEqual(len(state['history']), 1)
        self.change([{'type': 'set_status', 'status': 'active', 'reason': '合同更正重新签署', 'evidence': ['ev1']}], expected_revision=3, request_id='reopen')
        self.assertEqual(self.db.get_lifecycle(self.oid)['history'][-1]['from_stage'], 'won')
        self.assertEqual(self.db.get_lifecycle(self.oid)['current_stage_id'], 'contract_signing')

    def test_failed_analysis_rolls_back_all_tables(self):
        before = self.db.conn.execute('SELECT count(*) FROM accounts').fetchone()[0]
        bad = analyze({'materials': [{'evidence_id': 'ev1', 'content': 'different immutable provenance'}]})
        with self.assertRaises(ValueError):
            self.db.save_structured_data(bad, request={'request_id': 'bad', 'opportunity_id': self.oid, 'expected_revision': 1})
        self.assertEqual(self.db.conn.execute('SELECT count(*) FROM accounts').fetchone()[0], before)
        self.assertEqual(self.db.get_lifecycle(self.oid)['revision'], 1)

    def test_legacy_migration_does_not_confirm_old_inferred_stage(self):
        self.db.conn.execute('DELETE FROM opportunity_lifecycle WHERE opportunity_id=?', (self.oid,))
        self.db.conn.commit()
        state = self.db.get_lifecycle(self.oid)
        self.assertEqual(state['current_stage_id'], 'lead_identified')
        self.assertEqual(state['revision'], 0)
        self.assertEqual(state['facts'], [])
        self.assertTrue(state['migration_note'])

    def test_incremental_named_contacts_remap_decision_references(self):
        material = {'materials': [{'evidence_id': 'named', 'content': '客户：华辰装备有限公司。王敏 采购总监参加会议。请安排MES方案交流。'}]}
        first = self.db.save_structured_data(analyze(material), request={**material, 'request_id': 'named-first'})
        contacts = self.db.get_opportunity_detail(first['opportunity_id'])['contacts']
        self.assertTrue(contacts)
        self.db.save_structured_data(analyze(material), request={**material, 'request_id': 'named-update', 'opportunity_id': first['opportunity_id'], 'expected_revision': 1})
        detail = self.db.get_opportunity_detail(first['opportunity_id'])
        self.assertEqual({c['id'] for c in contacts}, {c['id'] for c in detail['contacts']})
        self.assertTrue(all(not n['contact_id'] or n['contact_id'] in {c['id'] for c in detail['contacts']} for n in detail['decision_chain']))

    def test_new_quote_version_needs_fresh_bound_authorization(self):
        path = Path(self.tmp.name) / 'quote.txt'
        path.write_text('quote')
        self.change([{'type': 'register_artifact', 'artifact_id': 'q1', 'kind': 'quote', 'version': 1, 'file_path': str(path), 'evidence': ['ev1']},
                     {'type': 'confirm_fact', 'fact_id': 'quote_authorized', 'value': True, 'artifact_id': 'q1', 'evidence': ['ev1']},
                     {'type': 'register_artifact', 'artifact_id': 'q2', 'kind': 'quote', 'version': 2, 'file_path': str(path), 'evidence': ['ev1']}])
        with self.assertRaises(ValueError):
            self.change([{'type': 'transition', 'to_stage': 'proposal_bidding', 'reason': '报价', 'evidence': ['ev1']}], expected_revision=2, request_id='unauthorized-v2')
        self.change([{'type': 'confirm_fact', 'fact_id': 'quote_authorized', 'value': True, 'artifact_id': 'q2', 'evidence': ['ev1']},
                     {'type': 'transition', 'to_stage': 'proposal_bidding', 'reason': '报价版本2授权确认', 'evidence': ['ev1']}], expected_revision=2, request_id='authorized-v2')

    def test_incomplete_contract_and_missing_files_are_rejected_atomically(self):
        path = Path(self.tmp.name) / 'contract.txt'
        path.write_text('contract')
        artifact = {'type': 'register_artifact', 'artifact_id': 'c1', 'kind': 'contract', 'version': 1, 'file_path': str(path), 'evidence': ['ev1']}
        complete = {'type': 'record_contract', 'artifact_id': 'c1', 'signing_date': '2026-10-11', 'parties': ['客户', '供应商'], 'amount': 100, 'currency': 'CNY', 'signature_facts': {'customer_signed': True, 'supplier_signed': True}, 'evidence': ['ev1']}
        invalid = [dict(complete, signature_facts={'customer_signed': True, 'supplier_signed': False}),
                   dict(complete, parties=['仅一方']), dict(complete, signing_date='unknown'),
                   dict(complete, amount=float('nan'))]
        for index, record in enumerate(invalid):
            with self.subTest(index=index), self.assertRaises(ValueError):
                self.change([artifact, record], request_id='invalid-' + str(index))
            self.assertEqual(self.db.get_lifecycle(self.oid)['revision'], 1)
            self.assertEqual(self.db.get_lifecycle(self.oid)['artifacts'], [])
        with self.assertRaises(ValueError):
            self.change([dict(artifact, file_path=str(path) + '.missing')], request_id='missing-file')

    def test_analysis_request_replay_does_not_duplicate_opportunities_or_revision(self):
        replay = self.db.save_structured_data(analyze(self.seed), request={'request_id': 'seed'})
        self.assertTrue(replay['idempotent_replay'])
        self.assertEqual(replay['opportunity_id'], self.oid)
        self.assertEqual(self.db.get_lifecycle(self.oid)['revision'], 1)
        self.assertEqual(len(self.db.query_opportunities({})), 1)
        with self.assertRaises(ValueError):
            self.db.save_structured_data(analyze({'materials': [{'content': 'changed input'}]}), request={'request_id': 'seed'})

    def test_current_stage_filter_uses_confirmed_lifecycle(self):
        self.assertEqual(self.db.query_opportunities({'filters': {'current_stage_id': 'lead_identified'}})[0]['id'], self.oid)
        self.assertEqual(self.db.query_opportunities({'filters': {'current_stage_id': 'won'}}), [])
