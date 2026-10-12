"""Persisted review closure and explicit artifact provenance regressions."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from opportunity_skill.extractor import analyze
from opportunity_skill.lifecycle import read_lifecycle
from opportunity_skill.storage import OpportunitySQLiteAdapter


class ReviewLineageTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / 'review.db'
        self.db = OpportunitySQLiteAdapter(self.path)
        saved = self.db.save_structured_data(analyze({'materials': [
            {'evidence_id': 'ev', 'content': '客户要求追溯接口，请修订方案后确认。'}]}),
            request={'request_id': 'seed'})
        self.oid = saved['opportunity_id']
        self.request = 0

    def tearDown(self):
        self.db.close()
        self.tmp.cleanup()

    def state(self):
        return self.db.get_lifecycle(self.oid)

    def change(self, *operations, request_id=None):
        self.request += 1
        return self.db.manage({'request_id': request_id or f'change-{self.request}',
            'opportunity_id': self.oid, 'expected_revision': self.state()['revision'],
            'actor': '售前负责人', 'operations': list(operations)})

    def binding(self, artifact_id):
        artifact = next(a for a in self.state()['artifacts'] if a['id'] == artifact_id)
        return {'artifact_id': artifact_id, 'sha256': artifact['sha256']}

    def artifact(self, artifact_id, kind, dependencies=(), version=1, document_id=None):
        path = Path(self.tmp.name) / (artifact_id + '.txt')
        path.write_text('simulated ' + artifact_id)
        return {'type': 'register_artifact', 'artifact_id': artifact_id, 'kind': kind,
            'document_id': document_id or kind, 'version': version, 'file_path': str(path),
            'dependencies': list(dependencies), 'evidence': ['ev']}

    def chain(self, include_negotiation=True, include_handoff=True):
        self.change(self.artifact('s1', 'solution'))
        self.change(self.artifact('q1', 'quote', [self.binding('s1')]), self.authorize())
        if include_negotiation:
            self.change(self.artifact('n1', 'negotiation', [self.binding('q1')]))
        dependencies = [self.binding('q1')]
        if include_negotiation:
            dependencies.append(self.binding('n1'))
        self.change(self.artifact('c1', 'contract', dependencies))
        if include_handoff:
            self.change(self.artifact('h1', 'handoff', [self.binding('c1')]))

    def review(self, blocking=True, review_id='RV-01'):
        return {'type': 'record_review', 'review_id': review_id, 'title': '补充接口验收边界',
            'requirement_ids': ['REQ-01', 'REQ-02'], 'artifact_id': 's1', 'owner': '王敏',
            'due_date': '2026-10-20', 'blocking': blocking, 'evidence': ['ev']}

    def resolve(self, artifact_id='s1'):
        return {'type': 'resolve_review', 'review_id': 'RV-01', 'artifact_id': artifact_id,
            'resolution': '已逐项修订并由客户确认', 'evidence': ['ev']}

    def transition(self, stage):
        return {'type': 'transition', 'to_stage': stage, 'reason': '有来源的阶段推进', 'evidence': ['ev']}

    def authorize(self):
        return {'type': 'confirm_fact', 'fact_id': 'quote_authorized', 'value': True,
            'artifact_id': 'q1', 'evidence': ['ev']}

    def test_review_persists_across_restart_and_replays_without_audit_duplication(self):
        self.change(self.artifact('s1', 'solution'))
        revision = self.state()['revision']
        operation = self.review()
        receipt = self.change(operation, request_id='review-once')
        replay = self.db.manage({'request_id': 'review-once', 'opportunity_id': self.oid,
            'expected_revision': revision, 'actor': '售前负责人', 'operations': [operation]})
        self.assertTrue(replay['idempotent_replay'])
        self.assertEqual(receipt['revision'], replay['revision'])
        self.db.close()
        self.db = OpportunitySQLiteAdapter(self.path)
        review = self.state()['reviews'][0]
        self.assertEqual(review['requirement_ids'], ['REQ-01', 'REQ-02'])
        self.assertEqual(review['owner'], '王敏')
        self.assertEqual(len(review['history']), 1)
        self.assertEqual(review['verification_status'], 'needs_review')

    def test_open_review_allows_solution_remediation_but_blocks_all_commercial_targets(self):
        self.change(self.artifact('s1', 'solution'), self.review(),
            {'type': 'confirm_fact', 'fact_id': 'solution_scope', 'value': '追溯接口', 'evidence': ['ev']},
            self.transition('solution_cocreation'))
        self.change(self.artifact('q1', 'quote', [self.binding('s1')]), self.authorize())
        for stage in ['proposal_bidding', 'commercial_negotiation', 'contract_signing', 'won']:
            with self.subTest(stage=stage), self.assertRaisesRegex(ValueError, 'blocking review'):
                self.change(self.transition(stage))
        self.change(self.resolve(), self.transition('proposal_bidding'))
        self.assertEqual(self.state()['verification_status'], 'current')

    def test_nonblocking_review_does_not_gate_commercial_progress(self):
        self.change(self.artifact('s1', 'solution'), self.review(blocking=False))
        self.change(self.artifact('q1', 'quote', [self.binding('s1')]), self.authorize(),
                    self.transition('proposal_bidding'))
        self.assertEqual(self.state()['current_stage_id'], 'proposal_bidding')
        self.assertEqual(self.state()['verification_status'], 'needs_review')

    def test_resolved_review_reopens_with_audit_and_fresh_evidence(self):
        self.change(self.artifact('s1', 'solution'), self.review(), self.resolve())
        self.db.close()
        self.db = OpportunitySQLiteAdapter(self.path)
        self.assertEqual(self.state()['reviews'][0]['verification_status'], 'current')
        self.change({'type': 'reopen_review', 'review_id': 'RV-01', 'reason': '客户新增反例', 'evidence': ['ev']})
        review = self.state()['reviews'][0]
        self.assertEqual(review['status'], 'open')
        self.assertEqual(review['closure']['resolution'], '已逐项修订并由客户确认')
        self.assertEqual(review['history'][-1]['reason'], '客户新增反例')
        self.change(self.resolve())
        self.assertEqual(len(self.state()['reviews'][0]['history']), 4)

    def test_solution_replacement_requires_revalidation_and_keeps_original_closure(self):
        self.change(self.artifact('s1', 'solution'), self.review(), self.resolve())
        self.change(self.artifact('s2', 'solution', version=2))
        review = self.state()['reviews'][0]
        self.assertEqual(review['status'], 'resolved')
        self.assertEqual(review['verification_status'], 'needs_review')
        self.assertEqual(review['closure']['artifact_id'], 's1')
        with self.assertRaises(ValueError):
            self.change(self.resolve('s1'))
        self.change(self.resolve('s2'))
        review = self.state()['reviews'][0]
        self.assertEqual(review['verification_status'], 'current')
        self.assertEqual(review['history'][1]['artifact_id'], 's1')
        self.assertEqual(review['closure']['artifact_id'], 's2')

    def test_changed_or_missing_solution_breaks_review_hash_binding(self):
        self.change(self.artifact('s1', 'solution'), self.review(), self.resolve())
        path = Path(self.tmp.name) / 's1.txt'
        for mode in ['changed', 'missing']:
            with self.subTest(mode=mode):
                path.write_text('changed') if mode == 'changed' else path.unlink()
                self.assertEqual(self.state()['reviews'][0]['verification_status'], 'needs_review')
                with self.assertRaises(ValueError):
                    self.change(self.resolve())
        self.assertEqual(self.state()['reviews'][0]['closure']['artifact_id'], 's1')

    def test_invalid_review_batch_rolls_back_artifact_review_revision_and_receipt(self):
        before = self.state()
        with self.assertRaises(ValueError):
            self.change(self.artifact('s1', 'solution'), self.review(),
                {**self.resolve(), 'evidence': ['foreign']}, request_id='invalid-batch')
        self.assertEqual(self.state(), before)
        self.assertIsNone(self.db.conn.execute('SELECT request_id FROM lifecycle_requests WHERE request_id=?', ('invalid-batch',)).fetchone())
        self.change(self.artifact('s1', 'solution'), self.review(), self.resolve(), request_id='invalid-batch')
        self.assertEqual(self.state()['reviews'][0]['verification_status'], 'current')

    def test_review_rejects_duplicate_and_invalid_fields(self):
        self.change(self.artifact('s1', 'solution'))
        for fields in [{'owner': ''}, {'due_date': 'unknown'}, {'blocking': 'true'},
                       {'requirement_ids': []}, {'artifact_id': 'foreign'}, {'evidence': ['foreign']}]:
            with self.subTest(fields=fields), self.assertRaises(ValueError):
                self.change({**self.review(), **fields})
        self.change(self.review())
        with self.assertRaises(ValueError):
            self.change(self.review())

    def test_chain_depth_invalidates_on_solution_tamper_and_file_removal(self):
        self.chain()
        path = Path(self.tmp.name) / 's1.txt'
        for mode in ['changed', 'missing']:
            with self.subTest(mode=mode):
                path.write_text('tampered') if mode == 'changed' else path.unlink()
                artifacts = {a['id']: a for a in self.state()['artifacts']}
                self.assertEqual(artifacts['s1']['validity'], 'stale_or_missing')
                for artifact_id in ['q1', 'n1', 'c1', 'h1']:
                    self.assertEqual(artifacts[artifact_id]['validity'], 'dependency_invalid')
                self.assertEqual(self.state()['verification_status'], 'needs_review')

    def test_same_hash_replacement_invalidates_downstream_by_artifact_identity(self):
        self.chain()
        replacement = self.artifact('s2', 'solution', version=2)
        Path(replacement['file_path']).write_text('simulated s1')
        self.change(replacement)
        artifacts = {a['id']: a for a in self.state()['artifacts']}
        self.assertEqual(artifacts['s1']['sha256'], artifacts['s2']['sha256'])
        self.assertEqual(artifacts['s1']['validity'], 'superseded')
        self.assertEqual(artifacts['h1']['validity'], 'dependency_invalid')

    def test_dependencies_reject_missing_wrong_kind_hash_duplicate_and_unbound(self):
        self.change(self.artifact('s1', 'solution'))
        binding = self.binding('s1')
        invalid = [[], [{'artifact_id': 'foreign', 'sha256': binding['sha256']}],
                   [{**binding, 'sha256': '0' * 64}], [binding, binding], 's1']
        before = self.state()
        for dependencies in invalid:
            operation = self.artifact('q1', 'quote')
            operation['dependencies'] = dependencies
            with self.subTest(dependencies=dependencies), self.assertRaises(ValueError):
                self.change(operation)
            self.assertEqual(self.state(), before)
        with self.assertRaises(ValueError):
            self.change(self.artifact('n1', 'negotiation', [binding]))
        self.change(self.artifact('q1', 'quote', [binding]))
        with self.assertRaises(ValueError):
            self.change(self.artifact('q2', 'quote', [self.binding('q1')], version=2))

    def test_superseded_and_transitively_invalid_dependencies_rejected(self):
        self.change(self.artifact('s1', 'solution'))
        self.change(self.artifact('q1', 'quote', [self.binding('s1')]))
        self.change(self.artifact('s2', 'solution', version=2))
        with self.assertRaises(ValueError):
            self.change(self.artifact('q2', 'quote', [self.binding('s1')], version=2))
        with self.assertRaises(ValueError):
            self.change(self.artifact('n1', 'negotiation', [self.binding('q1')]))

    def test_direct_purchase_contract_allows_no_negotiation_and_handoff_requires_contract(self):
        self.chain(include_negotiation=False, include_handoff=False)
        with self.assertRaises(ValueError):
            self.change(self.artifact('h1', 'handoff'))
        self.change(self.artifact('h1', 'handoff', [self.binding('c1')]))
        self.assertEqual(self.state()['verification_status'], 'current')
        self.assertFalse(any(a['kind'] == 'negotiation' for a in self.state()['artifacts']))

    def test_existing_negotiation_cannot_be_omitted_or_bound_to_another_quote(self):
        self.change(self.artifact('s1', 'solution'))
        self.change(self.artifact('q1', 'quote', [self.binding('s1')]))
        self.change(self.artifact('n1', 'negotiation', [self.binding('q1')]))
        with self.assertRaises(ValueError):
            self.change(self.artifact('c1', 'contract', [self.binding('q1')]))
        self.change(self.artifact('q2', 'quote', [self.binding('s1')], version=2))
        with self.assertRaises(ValueError):
            self.change(self.artifact('c1', 'contract', [self.binding('q2'), self.binding('n1')]))

    def test_contract_cannot_mix_independent_current_quote_and_negotiation_documents(self):
        self.change(self.artifact('s1', 'solution'))
        self.change(self.artifact('q1', 'quote', [self.binding('s1')], document_id='quote-A'))
        self.change(self.artifact('q2', 'quote', [self.binding('s1')], document_id='quote-B'))
        self.change(self.artifact('n1', 'negotiation', [self.binding('q1')]))
        with self.assertRaisesRegex(ValueError, 'differs from negotiated quote'):
            self.change(self.artifact('c1', 'contract', [self.binding('q2'), self.binding('n1')]))
        self.change(self.artifact('c1', 'contract', [self.binding('q1'), self.binding('n1')]))
        self.assertEqual(self.state()['artifacts'][-1]['validity'], 'valid')

    def test_won_fact_and_history_preserved_when_upstream_changes(self):
        self.chain(include_handoff=False)
        self.change({'type': 'record_contract', 'artifact_id': 'c1', 'signing_date': '2026-10-12',
            'parties': ['客户', '供应商'], 'amount': 10, 'currency': 'CNY',
            'signature_facts': {'customer_signed': True, 'supplier_signed': True}, 'evidence': ['ev']},
            self.transition('won'))
        before = deepcopy(self.state())
        (Path(self.tmp.name) / 's1.txt').write_text('modified after simulated signing')
        after = self.state()
        self.assertEqual(after['status'], 'won')
        self.assertEqual(after['history'], before['history'])
        self.assertEqual(after['contracts'], before['contracts'])
        self.assertEqual(after['verification_status'], 'needs_review')
        with self.assertRaises(ValueError):
            self.change(self.artifact('h1', 'handoff', [self.binding('c1')]))

    def test_legacy_unbound_data_remains_readable_without_fabricating_bindings(self):
        self.chain(include_negotiation=False, include_handoff=False)
        row = self.db.conn.execute('SELECT state_json FROM opportunity_lifecycle WHERE opportunity_id=?', (self.oid,)).fetchone()
        raw = json.loads(row[0])
        raw.pop('reviews')
        for artifact in raw['artifacts']:
            artifact.pop('dependencies')
        self.db.conn.execute('UPDATE opportunity_lifecycle SET state_json=? WHERE opportunity_id=?', (json.dumps(raw), self.oid))
        self.db.conn.commit()
        state = self.state()
        self.assertEqual(state['reviews'], [])
        self.assertEqual([a['validity'] for a in state['artifacts']], ['valid', 'unbound', 'unbound'])
        self.assertTrue(all('dependencies' not in a for a in state['artifacts']))
        with self.assertRaises(ValueError):
            self.change(self.authorize(), self.transition('proposal_bidding'))
        self.assertEqual(self.state()['revision'], raw['revision'])

    def test_cycle_or_dangling_dependency_in_legacy_state_is_readable_and_invalid(self):
        self.chain(include_negotiation=False, include_handoff=False)
        for mode in ['cycle', 'missing']:
            raw = self.state()
            if mode == 'cycle':
                raw['artifacts'][0]['dependencies'] = [self.binding('c1')]
            else:
                raw['artifacts'][1]['dependencies'] = [{'artifact_id': 'missing', 'sha256': '0' * 64}]
            result = read_lifecycle(raw)
            self.assertNotEqual(result['artifacts'][-1]['validity'], 'valid')
            self.assertEqual(result['verification_status'], 'needs_review')

    def signed_contract(self, artifact_id='c1'):
        return {'type': 'record_contract', 'artifact_id': artifact_id, 'signing_date': '2026-10-12',
            'parties': ['客户', '供应商'], 'amount': 10, 'currency': 'CNY',
            'signature_facts': {'customer_signed': True, 'supplier_signed': True}, 'evidence': ['ev']}

    def test_unapproved_parallel_quote_cannot_drive_negotiation_signing_or_won(self):
        self.change(self.artifact('s1', 'solution'))
        self.change(self.artifact('q1', 'quote', [self.binding('s1')], document_id='quote-A'),
                    self.authorize(), self.transition('proposal_bidding'))
        self.change(self.artifact('qb', 'quote', [self.binding('s1')], document_id='quote-B'))
        self.change(self.artifact('nb', 'negotiation', [self.binding('qb')]))
        self.change(self.artifact('cb', 'contract', [self.binding('qb'), self.binding('nb')]))
        for operation in [self.transition('commercial_negotiation'), self.transition('contract_signing'),
                          self.signed_contract('cb')]:
            before = self.state()
            with self.subTest(operation=operation), self.assertRaisesRegex(ValueError, 'authorized quote'):
                self.change(operation)
            self.assertEqual(self.state(), before)
        # A valid authorized alternative must never mask the actual unapproved signed artifact.
        self.change(self.artifact('na', 'negotiation', [self.binding('q1')], document_id='negotiation-A'))
        self.change(self.artifact('ca', 'contract', [self.binding('q1'), self.binding('na')], document_id='contract-A'))
        self.change(self.transition('contract_signing'))
        with self.assertRaisesRegex(ValueError, 'authorized quote'):
            self.change(self.signed_contract('cb'))
        self.change(self.signed_contract('ca'), self.transition('won'))
        self.assertEqual(self.state()['status'], 'won')

    def test_authorization_change_invalidates_exact_current_stage_binding(self):
        self.chain(include_handoff=False)
        self.change(self.transition('commercial_negotiation'))
        self.change(self.artifact('qb', 'quote', [self.binding('s1')], document_id='quote-B'))
        self.change(self.artifact('nb', 'negotiation', [self.binding('qb')], document_id='negotiation-B'))
        self.change({**self.authorize(), 'artifact_id': 'qb'})
        state = self.state()
        self.assertEqual(state['verification_status'], 'needs_review')
        self.assertEqual(state['history'][-1]['artifact_id'], 'n1')
        self.assertTrue(any('authorized quote' in blocker for blocker in state['blockers']))
        with self.assertRaises(ValueError):
            self.change(self.transition('contract_signing'))
        # Re-register the same current document to repair its quote lineage;
        # an unrelated negotiation-B must not silently replace negotiation-A.
        self.change(self.artifact('n2', 'negotiation', [self.binding('qb')], version=2))
        self.assertEqual(self.state()['verification_status'], 'needs_review')  # old contract still needs repair
        self.assertEqual(self.state()['blockers'], [])
        self.change(self.artifact('c2', 'contract', [self.binding('qb'), self.binding('n2')], version=2))
        self.change(self.transition('contract_signing'))
        self.assertEqual(self.state()['verification_status'], 'current')

    def test_noncommercial_backward_remediation_ignores_obsolete_commercial_gates(self):
        self.change(self.artifact('s1', 'solution'),
            {'type': 'confirm_fact', 'fact_id': 'solution_scope', 'value': '接口范围', 'evidence': ['ev']})
        self.change(self.artifact('q1', 'quote', [self.binding('s1')]), self.authorize(),
                    self.transition('proposal_bidding'))
        self.change(self.artifact('s2', 'solution', version=2))
        self.change(self.transition('solution_cocreation'))
        state = self.state()
        self.assertEqual(state['current_stage_id'], 'solution_cocreation')
        self.assertEqual(state['history'][-1]['from_stage'], 'proposal_bidding')
        self.assertFalse(any('quote authorization' in blocker for blocker in state['blockers']))
        with self.assertRaises(ValueError):
            self.change(self.transition('proposal_bidding'))
        self.change(self.artifact('q2', 'quote', [self.binding('s2')], version=2),
            {**self.authorize(), 'artifact_id': 'q2'}, self.transition('proposal_bidding'))
        self.assertEqual(self.state()['verification_status'], 'current')

    def test_backward_remediation_checks_target_facts_and_forward_checks_current_facts(self):
        self.change({'type': 'confirm_fact', 'fact_id': 'contact_established', 'value': True, 'evidence': ['ev']},
                    self.transition('customer_contacted'))
        self.change({'type': 'confirm_fact', 'fact_id': 'contact_established', 'value': False, 'evidence': ['ev']},
                    {'type': 'confirm_fact', 'fact_id': 'need_confirmed', 'value': True, 'evidence': ['ev']})
        with self.assertRaises(ValueError):
            self.change(self.transition('needs_discovery'))
        self.change(self.transition('lead_identified'))
        self.assertEqual(self.state()['verification_status'], 'needs_review')
        self.assertTrue(any('contact_established' in b for b in self.state()['blockers']))
        self.change({'type': 'confirm_fact', 'fact_id': 'contact_established', 'value': True, 'evidence': ['ev']})
        self.change(self.artifact('s1', 'solution'), self.artifact('s2', 'solution', version=2))
        self.change(self.artifact('q1', 'quote', [self.binding('s2')]), self.authorize(),
                    self.transition('proposal_bidding'))
        with self.assertRaisesRegex(ValueError, 'solution_scope'):
            self.change(self.transition('solution_cocreation'))

    def test_registered_core_unknown_or_negative_facts_block_commercial_progress(self):
        self.chain(include_handoff=False)
        self.change(self.transition('commercial_negotiation'))
        for fact_id, value in [('need_confirmed', False), ('continue_intent', 'unknown'),
                               ('solution_scope', 'unknown')]:
            with self.subTest(fact_id=fact_id):
                self.change({'type': 'confirm_fact', 'fact_id': fact_id, 'value': value, 'evidence': ['ev']})
                self.assertEqual(self.state()['verification_status'], 'needs_review')
                with self.assertRaisesRegex(ValueError, fact_id):
                    self.change(self.transition('contract_signing'))
                positive = '已核验范围' if fact_id == 'solution_scope' else True
                self.change({'type': 'confirm_fact', 'fact_id': fact_id, 'value': positive, 'evidence': ['ev']})
        self.change(self.signed_contract(), self.transition('won'))
        self.assertEqual(self.state()['status'], 'won')

    def test_review_cannot_close_against_an_unrelated_solution_document(self):
        self.change(self.artifact('s1', 'solution', document_id='solution-A'), self.review())
        self.change(self.artifact('sb', 'solution', document_id='solution-B'))
        with self.assertRaisesRegex(ValueError, 'same solution document'):
            self.change(self.resolve('sb'))
        self.assertEqual(self.state()['reviews'][0]['status'], 'open')
        self.change(self.artifact('sa2', 'solution', version=2, document_id='solution-A'))
        self.change(self.resolve('sa2'))
        self.assertEqual(self.state()['reviews'][0]['verification_status'], 'current')

    def test_register_self_reference_and_batch_forward_reference_roll_back(self):
        operation = self.artifact('s1', 'solution')
        operation['dependencies'] = [{'artifact_id': 's1', 'sha256': hashlib.sha256(Path(operation['file_path']).read_bytes()).hexdigest()}]
        with self.assertRaises(ValueError):
            self.change(operation)
        self.assertEqual(self.state()['artifacts'], [])
