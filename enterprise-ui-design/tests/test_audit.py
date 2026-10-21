import importlib.util
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('audit_ui', Path(__file__).resolve().parents[1] / 'scripts/audit_ui.py')
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


class AuditEvidence(unittest.TestCase):
    def test_absent_and_evidenceless_states_do_not_pass(self):
        manifest = {'scope': 'fixture', 'surfaces': [{'id': 'edit', 'states': ['invalid', 'saved']}]}
        self.assertEqual(audit.coverage(manifest, {})['status'], 'Fail')
        report = {'coverage': [{'surface': 'edit', 'state': s, 'status': 'Pass'} for s in ['invalid', 'saved']]}
        self.assertEqual(audit.coverage(manifest, report)['status'], 'Fail')

    def test_critical_findings_cannot_be_offset_by_passes(self):
        manifest = {'scope': 'fixture', 'surfaces': []}
        report = {'conclusions': {key: {'status': 'Pass', 'evidence': 'run.json'} for key in ['technical', 'visual_task', 'behavior']},
                  'findings': [{'id': 'SYS-01', 'severity': 'P1', 'status': 'open'}]}
        self.assertEqual(audit.coverage(manifest, report)['status'], 'Fail')
        report['findings'][0]['status'] = 'closed'
        self.assertEqual(audit.coverage(manifest, report)['status'], 'Pass')

    def test_na_needs_reason_and_independent_conclusions(self):
        manifest = {'scope': 'fixture', 'surfaces': [{'id': 'auth', 'states': ['sso']}]}
        report = {'coverage': [{'surface': 'auth', 'state': 'sso', 'status': 'Not applicable'}]}
        result = audit.coverage(manifest, report)
        self.assertEqual(result['status'], 'Fail')
        self.assertTrue(any('reason' in error for error in result['errors']))

    def test_scan_distinguishes_definition_consumption_and_debt(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'tokens.css').write_text(':root { --ui-brand: #1677ff; }')
            (root / 'page.css').write_text('.action { color: #1677ff; }')
            (root / 'page.tsx').write_text('const style = { color: "#1677ff" };')
            first = audit.scan(list(root.iterdir()))
            self.assertEqual(len(first['candidates']), 2)
            second = audit.scan(list(root.iterdir()), first['candidates'])
            self.assertTrue(all(item['origin'] == 'existing-debt' for item in second['candidates']))

    def test_duplicate_or_unknown_observations_cannot_hide_failures(self):
        manifest = {'scope': 'fixture', 'surfaces': [{'id': 'edit', 'states': ['saved']}]}
        report = {'coverage': [
            {'surface': 'edit', 'state': 'saved', 'status': 'Fail', 'reason': 'save broke'},
            {'surface': 'edit', 'state': 'saved', 'status': 'Pass', 'evidence': ['run.json']}],
            'conclusions': {key: {'status': 'Pass', 'evidence': ['run.json']} for key in ['technical', 'visual_task', 'behavior']}}
        for rows in [report['coverage'], list(reversed(report['coverage']))]:
            report['coverage'] = rows
            result = audit.coverage(manifest, report)
            self.assertEqual(result['status'], 'Fail')
            self.assertTrue(any('duplicate' in error for error in result['errors']))
        report['coverage'] = [{'surface': 'other', 'state': 'saved', 'status': 'Pass', 'evidence': ['run.json']}]
        self.assertTrue(any('unknown' in error for error in audit.coverage(manifest, report)['errors']))


if __name__ == '__main__':
    unittest.main()
