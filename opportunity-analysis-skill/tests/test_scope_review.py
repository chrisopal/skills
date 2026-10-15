"""Range confirmation and explicit content read-back are versioned attestations."""
from copy import deepcopy
import unittest
import json
from pathlib import Path
import subprocess
import importlib.util

import test_review_lineage as fixtures
from opportunity_skill.lifecycle import apply_operations, read_lifecycle


class ScopeReviewTests(unittest.TestCase):
    setUp = fixtures.ReviewLineageTests.setUp
    tearDown = fixtures.ReviewLineageTests.tearDown
    state = fixtures.ReviewLineageTests.state
    change = fixtures.ReviewLineageTests.change
    binding = fixtures.ReviewLineageTests.binding
    artifact = fixtures.ReviewLineageTests.artifact
    authorize = fixtures.ReviewLineageTests.authorize
    transition = fixtures.ReviewLineageTests.transition
    def scope(self, artifact_id='s1', value='国内30账号、V1范围'):
        return {'type': 'confirm_fact', 'fact_id': 'solution_scope', 'artifact_id': artifact_id,
                'value': value, 'evidence': ['ev']}

    def reviewed(self, artifact_id, kind, dependencies=(), version=1, scope_version=1):
        return {**self.artifact(artifact_id, kind, dependencies, version),
                'scope_review': {'scope_version': scope_version, 'summary': '已回读正文，核对范围、版本和商业前提'}}

    def test_scope_requires_explicit_current_solution_and_owned_evidence(self):
        self.change(self.artifact('s1', 'solution'))
        for fields in [{'artifact_id': None}, {'artifact_id': 'foreign'}, {'evidence': ['foreign']}]:
            before = self.state()
            with self.assertRaises(ValueError):
                self.change({**self.scope(), **fields})
            self.assertEqual(self.state(), before)
        self.change(self.scope())
        fact = self.state()['facts'][-1]
        self.assertEqual(fact['sha256'], self.binding('s1')['sha256'])
        self.assertEqual(fact['verification_status'], 'current')
        self.change(self.artifact('s2', 'solution', version=2))
        state = self.state()
        self.assertEqual(state['facts'][-1]['verification_status'], 'needs_review')
        self.assertEqual(state['current_stage_id'], 'lead_identified')
        with self.assertRaises(ValueError):
            self.change(self.scope())

    def test_unreviewed_quote_and_scope_bypass_are_rejected_atomically(self):
        self.change(self.artifact('s1', 'solution'), self.scope())
        before = self.state()
        for review in [None, {}, {'scope_version': 0, 'summary': '已读'},
                       {'scope_version': True, 'summary': '已读'}, {'scope_version': 1, 'summary': ' '}]:
            op = self.artifact('q1', 'quote', [self.binding('s1')])
            op.pop('scope_review', None)
            if review is not None:
                op['scope_review'] = review
            with self.subTest(review=review), self.assertRaises(ValueError):
                self.change(op)
            self.assertEqual(self.state(), before)
        self.change(self.reviewed('q1', 'quote', [self.binding('s1')]), self.authorize(), self.transition('proposal_bidding'))
        self.assertEqual(self.state()['verification_status'], 'current')

    def test_scope_reconfirmation_invalidates_review_even_for_same_solution(self):
        self.change(self.artifact('s1', 'solution'), self.scope())
        self.change(self.reviewed('q1', 'quote', [self.binding('s1')]), self.authorize(), self.transition('proposal_bidding'))
        self.change(self.scope(value='改为20账号，范围发生变化'))
        state = self.state()
        self.assertEqual(state['current_stage_id'], 'proposal_bidding')
        self.assertEqual(state['artifacts'][-1]['validity'], 'dependency_invalid')
        with self.assertRaises(ValueError):
            self.change(self.transition('commercial_negotiation'))
        self.change(self.reviewed('q2', 'quote', [self.binding('s1')], version=2, scope_version=2),
                    {**self.authorize(), 'artifact_id': 'q2'})
        self.assertEqual(self.state()['verification_status'], 'current')
        self.assertEqual(self.state()['artifacts'][-2]['scope_review']['scope_version'], 1)

    def test_other_current_solution_cannot_borrow_scope_confirmation(self):
        self.change(self.artifact('s1', 'solution'), self.scope(),
                    self.artifact('other', 'solution', document_id='alternative'))
        with self.assertRaisesRegex(ValueError, 'scope'):
            self.change(self.reviewed('q1', 'quote', [self.binding('other')]))

    def test_legacy_facts_and_reviews_are_not_inferred(self):
        self.change(self.artifact('s1', 'solution'), self.scope())
        self.change(self.reviewed('q1', 'quote', [self.binding('s1')]), self.authorize())
        raw = deepcopy(self.state())
        raw['facts'][0].pop('artifact_id')
        self.assertEqual(read_lifecycle(raw)['facts'][0]['verification_status'], 'needs_review')
        raw = deepcopy(self.state())
        raw['artifacts'][-1].pop('scope_review')
        self.assertEqual(read_lifecycle(raw)['artifacts'][-1]['validity'], 'unbound')
        with self.assertRaises(ValueError):
            apply_operations(raw, [self.transition('won')], '验证员', {'ev'})

    def test_replay_preserves_attestation_but_reports_current_invalidation(self):
        self.change(self.artifact('s1', 'solution'), self.scope())
        op = self.reviewed('q1', 'quote', [self.binding('s1')])
        revision = self.state()['revision']
        receipt = self.change(op, request_id='reviewed-quote')
        self.change(self.scope(value='范围增加验收前提'))
        replay = self.db.manage({'request_id': 'reviewed-quote', 'opportunity_id': self.oid,
            'expected_revision': revision, 'actor': '售前负责人', 'operations': [op]})
        self.assertTrue(replay['idempotent_replay'])
        self.assertEqual(replay['revision'], receipt['revision'])
        self.assertEqual(replay['lifecycle']['artifacts'][-1]['validity'], 'dependency_invalid')
        self.assertEqual(len(self.state()['artifacts']), 2)

    def test_scope_file_tamper_and_unknown_cannot_satisfy_commercial_gate(self):
        self.change(self.artifact('s1', 'solution'), self.scope())
        self.change(self.reviewed('q1', 'quote', [self.binding('s1')]), self.authorize())
        source = Path(self.tmp.name) / 's1.txt'
        source.write_text('different content')
        self.assertEqual(self.state()['facts'][0]['verification_status'], 'needs_review')
        with self.assertRaises(ValueError):
            self.change(self.transition('proposal_bidding'))
        source.write_text('simulated s1')
        self.change({**self.scope(), 'value': 'unknown'})
        self.assertEqual(self.state()['facts'][-1]['status'], 'unresolved')
        with self.assertRaises(ValueError):
            self.change(self.transition('proposal_bidding'))

    def test_browser_error_translation_keeps_actual_prerequisite_text(self):
        source = Path(__file__).resolve().parents[1] / 'display/workbench/workbench.js'
        script = """
const fs = require('fs'), vm = require('vm');
const source = fs.readFileSync(process.argv[1], 'utf8');
vm.runInThisContext(source.slice(source.indexOf('  function readableBlocker'), source.indexOf('  async function api')));
console.log(JSON.stringify(JSON.parse(process.argv[2]).map(readableError)));
"""
        messages = ['resolve lifecycle blockers before transition: fact unresolved, missing or negative: solution_scope; solution scope confirmation is stale or unbound; artifact superseded: SOL-2; current artifact does not match latest authorized quote: contract',
                    'artifact content review must reference the current solution scope version',
                    'won requires a recorded signed contract']
        result = subprocess.run(['node', '-e', script, str(source), json.dumps(messages)],
                                capture_output=True, text=True, check=True)
        translated = json.loads(result.stdout)
        self.assertIn('待确认：方案范围确认', translated[0])
        self.assertIn('成果已被新版本替代：SOL-2', translated[0])
        self.assertNotIn('contract', translated[0])
        self.assertNotIn('artifact superseded', translated[0])
        self.assertIn('当前方案范围版本', translated[1])
        self.assertIn('已签署合同', translated[2])
        self.assertNotIn('solution_scope', ''.join(translated))

    @unittest.skipUnless(importlib.util.find_spec('jsonschema'), 'optional schema validation tool unavailable')
    def test_public_schema_rejects_missing_scope_bindings_and_dependent_handoff_review(self):
        import jsonschema
        schema = json.loads((Path(__file__).resolve().parents[1] / 'schemas/manage.schema.json').read_text())
        def validate(op):
            jsonschema.validate({'request_id': 'r', 'opportunity_id': 'o', 'expected_revision': 1,
                'actor': '验证员', 'operations': [op]}, schema)
        validate(self.scope())
        validate({**self.scope(), 'value': ' UNKNOWN ', 'artifact_id': 's1'})
        validate({'type': 'confirm_fact', 'fact_id': 'solution_scope', 'value': '未知', 'evidence': ['ev']})
        for op in [{**self.scope(), 'value': True},
                   {'type': 'confirm_fact', 'fact_id': 'solution_scope', 'value': '范围', 'evidence': ['ev']},
                   {'type': 'confirm_fact', 'fact_id': 'quote_authorized', 'value': True, 'evidence': ['ev']},
                   {'type': 'register_artifact', 'kind': 'handoff', 'version': 1, 'file_path': '/file',
                    'evidence': ['ev'], 'dependencies': [{'artifact_id': 'c1', 'sha256': '0' * 64}]}]:
            with self.subTest(op=op), self.assertRaises(jsonschema.ValidationError):
                validate(op)
