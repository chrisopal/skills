"""Synthetic audit records test the gate, never certify browser execution."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/check_coverage.py'
SPEC = importlib.util.spec_from_file_location('coverage_checker', SCRIPT)
CHECKER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CHECKER)


class CoverageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        proof = self.base / 'proof.txt'
        proof.write_text('SYNTHETIC checker test evidence, no browser execution')
        self.evidence = [{'path': proof.name, 'sha256': hashlib.sha256(proof.read_bytes()).hexdigest()}]
        self.data = {
            'schemaVersion': 3, 'scope': 'Both business pages',
            'build': {'fingerprint': 'a' * 64, 'runtimeId': 'test-build', 'runtimeEvidence': self.evidence},
            'environment': {'url': 'http://localhost', 'browser': 'synthetic', 'role': 'admin',
                            'theme': 'light', 'viewport': {'width': 1280, 'height': 800}},
            'replay': {'command': 'synthetic command, never executed', 'prerequisites': 'synthetic setup',
                       'scripts': self.evidence, 'logs': self.evidence},
            'pages': [], 'controls': [], 'results': [],
        }
        for pid in ('orders', 'settings'):
            self.data['pages'].append({'id': pid, 'url': '/' + pid, 'inventoryComplete': True,
                                       'sourceRefs': ['src/routes.ts#' + pid]})
            for kind in ('page', 'number'):
                cid = pid + '.' + kind
                checks = list(CHECKER.DIMENSIONS)
                self.data['controls'].append({
                    'id': cid, 'page': pid, 'kind': kind, 'name': cid, 'locator': cid,
                    'sourceRefs': ['src/' + pid + '.vue#' + kind], 'checks': checks,
                    'dimensions': {d: [d] for d in checks}, 'notApplicable': {},
                })
                for check in checks:
                    self.data['results'].append({
                        'control': cid, 'check': check, 'status': 'PASS', 'preconditions': 'synthetic ready',
                        'contractRefs': ['contract#' + check], 'steps': ['synthetic step'],
                        'expected': 'synthetic expected', 'actual': 'synthetic expected', 'evidence': self.evidence,
                    })
        self.scope = {
            'schemaVersion': 1, 'scope': self.data['scope'],
            'build': {'fingerprint': 'a' * 64, 'runtimeId': 'test-build'},
            'discovery': {'sourceRefs': ['src/routes.ts'], 'runtimeEvidence': self.evidence, 'reconciled': True},
            'pages': copy.deepcopy(self.data['pages']), 'controls': copy.deepcopy(self.data['controls']),
        }
        self.freeze_scope()

    def freeze_scope(self):
        self.scope_path = self.base / 'scope.json'
        self.scope_path.write_text(json.dumps(self.scope, ensure_ascii=False))
        self.data['scopeFingerprint'] = hashlib.sha256(self.scope_path.read_bytes()).hexdigest()

    def audit(self):
        (self.base / 'coverage.json').write_text(json.dumps(self.data))
        run = subprocess.run([sys.executable, str(SCRIPT), str(self.base / 'coverage.json'),
                              '--scope', str(self.scope_path)], capture_output=True, text=True)
        self.assertIn(run.returncode, (0, 1, 2), run.stderr)
        self.assertFalse(run.stderr, run.stderr)
        return json.loads(run.stdout)

    def assert_incomplete(self, text):
        result = self.audit()
        self.assertEqual(result['verdict'], 'INCOMPLETE', result)
        self.assertTrue(any(text in error for error in result['errors']), result)

    def test_complete_manifest_and_ledger_pass(self):
        result = self.audit()
        self.assertEqual(result['verdict'], 'PASS', result)
        self.assertEqual(result['executionCoverage'], 1.0)

    def test_omitted_page_cannot_shrink_denominator(self):
        self.data['pages'].pop()
        self.data['controls'] = self.data['controls'][:2]
        self.data['results'] = self.data['results'][:8]
        self.assert_incomplete('scope')
        self.assertEqual(self.audit()['executionCoverage'], 0.5)

    def test_omitted_control_cannot_pass(self):
        cid = self.data['controls'].pop()['id']
        self.data['results'] = [r for r in self.data['results'] if r['control'] != cid]
        self.assert_incomplete('scope')

    def test_check_cannot_be_removed_from_both_ledger_lists(self):
        c = self.data['controls'][0]
        c['checks'].remove('business')
        c['dimensions']['business'] = ['interaction']
        self.data['results'] = [r for r in self.data['results'] if (r['control'], r['check']) != (c['id'], 'business')]
        self.assert_incomplete('scope')

    def test_one_check_cannot_stand_for_four_dimensions(self):
        for container in (self.data, self.scope):
            c = container['controls'][0]
            c['checks'] = ['interaction']
            c['dimensions'] = {d: ['interaction'] for d in CHECKER.DIMENSIONS}
        self.data['results'] = [r for r in self.data['results'] if r['control'] != 'orders.page' or r['check'] == 'interaction']
        self.freeze_scope()
        self.assert_incomplete('dimension')

    def test_page_layout_instance_is_required_even_in_manifest(self):
        for container in (self.data, self.scope):
            container['controls'] = [c for c in container['controls'] if c['id'] != 'orders.page']
        self.data['results'] = [r for r in self.data['results'] if r['control'] != 'orders.page']
        self.freeze_scope()
        self.assert_incomplete('page-wide layout')

    def test_na_cannot_hide_an_applicable_check(self):
        self.data['results'][0].update(status='N/A', reason='unimportant')
        self.assert_incomplete('applicability')

    def test_declared_na_is_excluded_from_execution_denominator(self):
        self.scope['controls'][0]['notApplicable'] = {'business': 'page container has no business value'}
        self.data['controls'][0]['notApplicable'] = copy.deepcopy(self.scope['controls'][0]['notApplicable'])
        self.data['results'][0].update(status='N/A', reason='page container has no business value', contractRefs=[])
        self.freeze_scope()
        result = self.audit()
        self.assertEqual(result['verdict'], 'PASS', result)
        self.assertEqual(result['applicableChecks'], 15)

    def test_missing_contract_can_be_blocked_without_fake_reference(self):
        self.data['results'][0].update(status='BLOCKED', contractRefs=[],
                                       missingContracts=['quantity lower bound'], reason='requirement unavailable')
        result = self.audit()
        self.assertEqual(result['verdict'], 'INCOMPLETE', result)
        self.assertEqual(result['errors'], [])

    def test_not_run_retains_incomplete_verdict(self):
        self.data['results'][0].update(status='NOT_RUN', reason='not executed')
        result = self.audit()
        self.assertEqual(result['verdict'], 'INCOMPLETE')
        self.assertLess(result['executionCoverage'], 1)

    def test_fail_wins_over_incomplete(self):
        self.data['results'][0]['status'] = 'FAIL'
        self.data['results'][1].update(status='BLOCKED', reason='depends on failure')
        self.assertEqual(self.audit()['verdict'], 'FAIL')

    def test_tampered_scope_rejected(self):
        self.scope_path.write_text(self.scope_path.read_text() + '\n')
        self.assert_incomplete('scopeFingerprint')

    def test_build_mismatch_rejected(self):
        self.data['build']['fingerprint'] = 'b' * 64
        self.assert_incomplete('scope')

    def test_runtime_version_evidence_required(self):
        self.data['build'].pop('runtimeEvidence')
        self.assert_incomplete('runtime')

    def test_runtime_version_must_match_frozen_target(self):
        self.data['build']['runtimeId'] = 'old-build'
        self.assert_incomplete('runtimeId')

    def test_replay_script_command_and_log_are_required(self):
        for field in ('command', 'scripts', 'logs', 'prerequisites'):
            with self.subTest(field=field):
                saved = self.data['replay'].pop(field)
                self.assert_incomplete('replay')
                self.data['replay'][field] = saved

    def test_source_runtime_reconciliation_required(self):
        self.scope['discovery']['reconciled'] = False
        self.freeze_scope()
        self.assert_incomplete('reconciled')

    def test_wrong_hash_missing_empty_and_unsafe_paths(self):
        for path, digest in [('missing', 'a' * 64), ('empty', hashlib.sha256(b'').hexdigest()),
                             ('../outside.txt', 'a' * 64), ('/tmp/outside.txt', 'a' * 64),
                             ('C:\\outside.txt', 'a' * 64), ('proof.txt', 'b' * 64)]:
            with self.subTest(path=path):
                (self.base / 'empty').touch()
                self.data['results'][0]['evidence'] = [{'path': path, 'sha256': digest}]
                self.assertEqual(self.audit()['verdict'], 'INCOMPLETE')

    def test_symlink_outside_evidence_directory_rejected(self):
        with tempfile.TemporaryDirectory() as outside:
            target = Path(outside) / 'evidence'
            target.write_text('outside')
            (self.base / 'link').symlink_to(target)
            self.data['results'][0]['evidence'] = [{'path': 'link', 'sha256': hashlib.sha256(target.read_bytes()).hexdigest()}]
            self.assert_incomplete('escapes')

    def test_previous_failure_evidence_is_validated(self):
        self.data['results'][0]['previousFailures'] = [{'path': 'lost.txt', 'sha256': 'a' * 64}]
        self.assert_incomplete('previousFailures')

    def test_duplicate_and_missing_results_rejected(self):
        self.data['results'][-1] = copy.deepcopy(self.data['results'][0])
        self.assert_incomplete('duplicate')
        self.assertLess(self.audit()['executionCoverage'], 1)

    def test_duplicate_failure_is_preserved_in_both_orders(self):
        for failure_first in (False, True):
            with self.subTest(failure_first=failure_first):
                original = copy.deepcopy(self.data['results'])
                duplicate = copy.deepcopy(original[0])
                duplicate['status'] = 'FAIL'
                self.data['results'].insert(0 if failure_first else len(original), duplicate)
                result = self.audit()
                self.assertEqual(result['verdict'], 'FAIL', result)
                self.assertEqual(result['counts']['FAIL'], 1)
                self.assertEqual(sum(result['counts'].values()), 16)
                self.assertEqual(result['executionCoverage'], 1)
                self.assertTrue(any('duplicate' in e for e in result['errors']))
                self.data['results'] = original

    def test_legacy_v2_does_not_pass_new_gate(self):
        self.data['schemaVersion'] = 2
        self.assert_incomplete('schemaVersion')

    def test_missing_scope_does_not_pass(self):
        self.scope_path.unlink()
        self.assert_incomplete('scope')

    def test_malformed_json_and_structures_return_diagnostics(self):
        cases = [[], None, {'pages': [{}]}, {'schemaVersion': 3, 'controls': [None]}]
        for case in cases:
            with self.subTest(case=case):
                original = self.data
                self.data = case
                self.assertEqual(self.audit()['verdict'], 'INCOMPLETE')
                self.data = original


if __name__ == '__main__':
    unittest.main()
