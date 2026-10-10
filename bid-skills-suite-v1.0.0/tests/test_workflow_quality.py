import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import bidkit
import workflow_quality


class WorkflowQualityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.project = Path(self.temp.name) / 'project'
        bidkit.init_project(self.project, 'TEST-FLOW')

    def test_unchecked_host_capability_cannot_satisfy_requirement(self):
        result = workflow_quality.preflight(self.project, required=['host_images'])
        self.assertFalse(result['passed'])
        self.assertEqual(result['missing_required'], ['host_images'])
        self.assertFalse(result['execution_verified'])

    def test_host_discovery_is_bound_to_current_file(self):
        rel = 'work/host.json'
        bidkit.atomic(self.project / rel, {'project_id': 'TEST-FLOW', 'capabilities': {
            'host_agents': {'status': 'available', 'evidence': 'actual session tool catalog'}}})
        result = workflow_quality.preflight(self.project, rel, ['host_agents'])
        self.assertTrue(result['passed'])
        self.assertEqual(result['host_discovery']['sha256'], bidkit.digest(self.project / rel))
        bidkit.atomic(self.project / rel, {'project_id': 'OTHER'})
        with self.assertRaises(ValueError):
            workflow_quality.preflight(self.project, rel)

    def test_unconfigured_project_cannot_claim_quality_clear(self):
        result = workflow_quality.plan(self.project)
        self.assertEqual(result['state'], 'needs_remediation')
        self.assertEqual(result['tasks'][0]['id'], 'POLICY:configuration')

    def test_attempt_requires_real_change_and_fresh_status_not_declared_closure(self):
        issue = {'id': 'GAP-1', 'section_ids': ['SEC-1'], 'reason': '缺图', 'blocking': True}
        with patch.object(workflow_quality, 'live_findings', return_value=([issue], {})):
            workflow_quality.plan(self.project, max_attempts=1)
            evidence = 'work/action.json'
            bidkit.atomic(self.project / evidence, {'project_id': 'TEST-FLOW',
                'tool_or_agent': 'TEST-host', 'performed_actions': ['补入实际图片']})
            with self.assertRaises(ValueError):
                workflow_quality.record_attempt(self.project, evidence_file=evidence)
            (self.project / 'assets/image.txt').write_text('TEST change, not image proof')
            result = workflow_quality.record_attempt(self.project, evidence_file=evidence)
            self.assertEqual(result['state'], 'attempts_exhausted')
            self.assertEqual(len(result['pending']), 1)
        with patch.object(workflow_quality, 'live_findings', return_value=([], {})):
            result = workflow_quality.status(self.project)
            self.assertEqual(result['resolved_ids'], ['GAP-1'])
            self.assertEqual(result['state'], 'checks_clear')
            self.assertFalse(result['formal_release_ready'])

    def test_plan_refuses_overwriting_attempt_history(self):
        workflow_quality.plan(self.project)
        with self.assertRaises(ValueError):
            workflow_quality.plan(self.project)


if __name__ == '__main__':
    unittest.main()
