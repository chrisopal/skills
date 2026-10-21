"""Evidence gate tests: a complete page inventory is not a completed user journey."""
import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('audit_ui', ROOT / 'scripts/audit_ui.py')
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


def case():
    manifest = {'schema': 'enterprise-ui-design/journeys/v1', 'scope': 'simulated-request-review', 'journeys': [{
        'id': 'request', 'role': 'registrar', 'goal': 'submit a request',
        'entry': '/requests?page=2', 'completion': 'read back pending-review result',
        'source': 'simulation contract supplied before execution',
        'branches': [
            {'id': 'normal', 'kind': 'main', 'applicable': True, 'steps': [
                {'id': 'submit', 'surface': 'edit', 'state': 'draft', 'action': 'submit', 'expected': 'pending-review readback'}]},
            {'id': 'timeout', 'kind': 'recovery', 'applicable': True,
             'recovery': {'trigger': 'response timeout', 'safeAction': 'read known operation result before retry',
                          'preservedState': 'request ID and draft', 'resumePoint': 'same request', 'resultCheck': 'query submitted state'},
             'steps': [{'id': 'reconcile', 'surface': 'edit', 'state': 'unknown-result',
                        'action': 'query outcome', 'expected': 'one request, no duplicate'}]},
            {'id': 'review', 'kind': 'handoff', 'applicable': True,
             'handoff': {'fromRole': 'registrar', 'toRole': 'reviewer', 'object': 'same request ID',
                         'entry': '/inbox', 'expectedState': 'pending-review'},
             'steps': [{'id': 'receive', 'surface': 'review', 'state': 'pending',
                        'action': 'open inbox request', 'expected': 'same object and allowed next action'}]}
        ]}]}
    rows = []
    for branch in manifest['journeys'][0]['branches']:
        for step in branch['steps']:
            row = {'journey': 'request', 'branch': branch['id'], 'step': step['id'], 'status': 'Pass',
                   'evidence': ['simulation-observation.json#' + step['id']],
                   'cue': 'visible object and action', 'action': step['action'],
                   'result': step['expected'], 'friction': 'no extra input in this simulation'}
            if branch['kind'] in {'recovery', 'handoff'}:
                row[branch['kind']] = 'observed continuity of same request in simulation'
            rows.append(row)
    report = {'schema': 'enterprise-ui-design/review/v1', 'scope': manifest['scope'], 'journeyCoverage': rows, 'findings': [],
              'conclusions': {k: {'status': 'Pass', 'evidence': ['run.json']} for k in ['technical', 'visual_task', 'behavior']}}
    report['conclusions']['ux'] = {'status': 'Pass', 'evidence': ['walkthrough.md'], 'method': 'simulation'}
    report['userStudy'] = {'status': 'Not tested', 'reason': 'no target users observed', 'participants': 0, 'evidence': [], 'metrics': []}
    return manifest, report


class JourneyEvidence(unittest.TestCase):
    def gate(self, manifest, report):
        fn = getattr(audit, 'journeys', None)
        self.assertTrue(callable(fn), 'missing per-journey gate: page/state coverage cannot certify a workflow')
        return fn(manifest, report)

    def test_complete_simulation_has_bounded_pass_without_human_claim(self):
        manifest, report = case()
        result = self.gate(manifest, report)
        self.assertEqual(result['status'], 'Pass', result)
        self.assertEqual(result['expectedSteps'], 3)
        self.assertIn('human', result['not_claimed'].lower())

    def test_page_passes_do_not_cover_missing_journey_or_ux_evidence(self):
        manifest, report = case()
        manifest['surfaces'] = []
        report['journeyCoverage'] = report['journeyCoverage'][:1]
        self.assertEqual(audit.coverage(manifest, report)['status'], 'Fail')

    def test_independent_ux_conclusion_is_required(self):
        manifest, report = case()
        del report['conclusions']['ux']
        self.assertEqual(self.gate(manifest, report)['status'], 'Fail')

    def test_missing_unknown_or_duplicate_steps_do_not_pass(self):
        manifest, report = case()
        for changed in [report['journeyCoverage'][:-1], report['journeyCoverage'] + [copy.deepcopy(report['journeyCoverage'][0])],
                        report['journeyCoverage'] + [dict(report['journeyCoverage'][0], step='unknown')]]:
            with self.subTest(rows=len(changed)):
                report['journeyCoverage'] = changed
                self.assertEqual(self.gate(manifest, report)['status'], 'Fail')

    def test_failure_cannot_be_hidden_by_later_pass_in_either_order(self):
        manifest, report = case()
        failed = dict(report['journeyCoverage'][0], status='Fail', reason='draft lost')
        for rows in [[failed] + report['journeyCoverage'], report['journeyCoverage'] + [failed]]:
            candidate = copy.deepcopy(report); candidate['journeyCoverage'] = rows
            self.assertEqual(self.gate(manifest, candidate)['status'], 'Fail')

    def test_pass_requires_observation_and_nonempty_evidence_array(self):
        for field, value in [('evidence', []), ('evidence', 'screenshot.png'), ('evidence', [' ']),
                             ('cue', ''), ('action', ''), ('result', ''), ('friction', ''), ('status', 'Looks good')]:
            manifest, report = case(); report['journeyCoverage'][0][field] = value
            self.assertEqual(self.gate(manifest, report)['status'], 'Fail', (field, value))

    def test_recovery_and_handoff_need_contract_and_observation(self):
        for kind in ['recovery', 'handoff']:
            for target in ['manifest', 'observation']:
                manifest, report = case(); index = 1 if kind == 'recovery' else 2
                if target == 'manifest': del manifest['journeys'][0]['branches'][index][kind]
                else: del report['journeyCoverage'][index][kind]
                self.assertEqual(self.gate(manifest, report)['status'], 'Fail', (kind, target))

    def test_not_tested_and_observed_failure_need_reasons_and_block_pass(self):
        for status in ['Not tested', 'Fail']:
            manifest, report = case(); report['journeyCoverage'][0].update(status=status, reason='not observed')
            self.assertEqual(self.gate(manifest, report)['status'], 'Fail')

    def test_na_must_be_predeclared_with_reason_not_used_to_erase_steps(self):
        manifest, report = case(); report['journeyCoverage'][1].update(status='Not applicable', reason='skip timeout')
        self.assertEqual(self.gate(manifest, report)['status'], 'Fail')
        branch = manifest['journeys'][0]['branches'][1]
        branch.update(applicable=False, reason='read-only fixture has no mutations', steps=[])
        report['journeyCoverage'].pop(1)
        self.assertEqual(self.gate(manifest, report)['status'], 'Pass')
        branch['reason'] = ''
        self.assertEqual(self.gate(manifest, report)['status'], 'Fail')

    def test_manifest_cannot_silently_drop_recovery_or_handoff_decision(self):
        manifest, report = case(); manifest['journeys'][0]['branches'].pop()
        self.assertEqual(self.gate(manifest, report)['status'], 'Fail')

    def test_empty_duplicate_and_incomplete_manifest_is_rejected(self):
        for change in ['empty', 'duplicate-journey', 'duplicate-branch', 'duplicate-step', 'empty-role', 'empty-source']:
            manifest, report = case(); flow = manifest['journeys'][0]
            if change == 'empty': manifest['journeys'] = []
            elif change == 'duplicate-journey': manifest['journeys'].append(copy.deepcopy(flow))
            elif change == 'duplicate-branch': flow['branches'].append(copy.deepcopy(flow['branches'][0]))
            elif change == 'duplicate-step': flow['branches'][0]['steps'] *= 2
            elif change == 'empty-role': flow['role'] = ''
            elif change == 'empty-source': flow['source'] = ''
            self.assertEqual(self.gate(manifest, report)['status'], 'Fail', change)

    def test_other_scope_cannot_be_reused_as_this_journey_evidence(self):
        manifest, report = case()
        report['scope'] = 'another-product'
        self.assertEqual(self.gate(manifest, report)['status'], 'Fail')
        del report['scope']
        self.assertEqual(self.gate(manifest, report)['status'], 'Fail')

    def test_open_high_severity_findings_block_ux(self):
        manifest, report = case(); report['findings'] = [{'id': 'UX-03', 'severity': 'P1', 'status': 'open'}]
        self.assertEqual(self.gate(manifest, report)['status'], 'Fail')

    def test_model_review_cannot_claim_measured_human_usability(self):
        manifest, report = case()
        report['userStudy']['metrics'] = [{'name': 'taskSuccessRate', 'value': 100}]
        self.assertEqual(self.gate(manifest, report)['status'], 'Fail')
        report['userStudy']['metrics'] = []
        report['conclusions']['ux']['method'] = 'target-user'
        self.assertEqual(self.gate(manifest, report)['status'], 'Fail')

    def test_actual_user_study_needs_count_source_and_measurement_context(self):
        manifest, report = case(); report['conclusions']['ux']['method'] = 'target-user'
        report['userStudy'] = {'status': 'Observed', 'participants': 2, 'source': 'consented task observation session',
                               'evidence': ['study.json'], 'metrics': [{'name': 'completion', 'value': 1, 'unit': 'of 2 attempts',
                               'definition': 'completed without help', 'context': 'reviewer task, supplied device and data',
                               'evidence': ['study.json#attempts']}]}
        self.assertEqual(self.gate(manifest, report)['status'], 'Pass')
        report['userStudy']['participants'] = True
        self.assertEqual(self.gate(manifest, report)['status'], 'Fail')

    def test_malformed_json_shapes_return_fail_not_traceback(self):
        for manifest, report in [(None, {}), ([], []), ({'scope': 'x', 'journeys': [None]}, {}),
                                 ({'scope': 'x', 'journeys': 'fake'}, {}), (*case()[:1], [])]:
            self.assertEqual(self.gate(manifest, report)['status'], 'Fail')
        for mutate in ['row', 'branches', 'recovery', 'study', 'conclusions']:
            manifest, report = case()
            if mutate == 'row': report['journeyCoverage'] = [None]
            if mutate == 'branches': manifest['journeys'][0]['branches'] = [None]
            if mutate == 'recovery': manifest['journeys'][0]['branches'][1]['recovery'] = []
            if mutate == 'study': report['userStudy'] = []
            if mutate == 'conclusions': report['conclusions'] = []
            self.assertEqual(self.gate(manifest, report)['status'], 'Fail', mutate)

    def test_incompatible_schema_is_not_silently_accepted(self):
        for target in ['manifest', 'report']:
            manifest, report = case()
            obj = manifest if target == 'manifest' else report
            obj['schema'] = 'other-product/v999'
            self.assertEqual(self.gate(manifest, report)['status'], 'Fail')

    def test_closed_critical_finding_requires_repair_and_recheck_evidence(self):
        manifest, report = case()
        finding = {'id': 'UX-03', 'severity': 'P1', 'status': 'closed'}
        report['findings'] = [finding]
        self.assertEqual(self.gate(manifest, report)['status'], 'Fail')
        finding.update(repairLocation='shared draft model', recheck={'status': 'Pass', 'evidence': ['recheck.json#return']})
        self.assertEqual(self.gate(manifest, report)['status'], 'Pass')
        finding['recheck']['evidence'] = []
        self.assertEqual(self.gate(manifest, report)['status'], 'Fail')

    def test_malformed_finding_does_not_disappear_from_verdict(self):
        for finding in [{}, {'id': 'UX-03', 'severity': 'maybe', 'status': 'closed'}]:
            manifest, report = case(); report['findings'] = [finding]
            self.assertEqual(self.gate(manifest, report)['status'], 'Fail')

    def test_reported_count_is_not_presented_as_executed_steps(self):
        manifest, report = case(); report['journeyCoverage'][0].update(status='Not tested', reason='not executed')
        result = self.gate(manifest, report)
        self.assertEqual(result.get('reportedSteps'), 3)
        self.assertEqual(result.get('passedSteps'), 2)
        self.assertNotIn('observedSteps', result)

    def test_cli_invalid_json_returns_structured_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'broken.json'; path.write_text('{')
            result = subprocess.run([sys.executable, str(ROOT / 'scripts/audit_ui.py'), 'journeys',
                                     '--manifest', str(path), '--report', str(path)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 1)
            self.assertTrue(result.stdout, 'invalid input must return structured JSON, not a traceback')
            self.assertEqual(json.loads(result.stdout)['status'], 'Fail')
            self.assertNotIn('Traceback', result.stderr)

    def test_schema_and_method_containers_fail_without_type_errors(self):
        for value in [[], {}, [None]]:
            for field in ['schema', 'method']:
                manifest, report = case()
                if field == 'schema': manifest['schema'] = value
                else: report['conclusions']['ux']['method'] = value
                self.assertEqual(self.gate(manifest, report)['status'], 'Fail')

    def test_cli_accepts_complete_ledger_and_rejects_incomplete(self):
        manifest, report = case()
        with tempfile.TemporaryDirectory() as directory:
            m = Path(directory) / 'manifest.json'; r = Path(directory) / 'report.json'
            m.write_text(json.dumps(manifest)); r.write_text(json.dumps(report))
            cmd = [sys.executable, str(ROOT / 'scripts/audit_ui.py'), 'journeys', '--manifest', str(m), '--report', str(r)]
            good = subprocess.run(cmd, capture_output=True, text=True)
            self.assertEqual(good.returncode, 0, good.stderr)
            self.assertEqual(json.loads(good.stdout)['status'], 'Pass')
            report['journeyCoverage'].pop(); r.write_text(json.dumps(report))
            bad = subprocess.run(cmd, capture_output=True, text=True)
            self.assertEqual(bad.returncode, 1, bad.stderr)
            self.assertEqual(json.loads(bad.stdout)['status'], 'Fail')


if __name__ == '__main__':
    unittest.main()
