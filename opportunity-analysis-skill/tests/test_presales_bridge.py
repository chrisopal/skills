"""Cross-suite tests use explicitly synthetic PPT fixtures, never a visual approval."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

from opportunity_skill.pipeline import run_analyze, run_detail
from opportunity_skill.presales_bridge import export_project, receive_delivery, runtime


class PresalesBridgeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.db = self.root / 'opportunity.db'
        self.oid = run_analyze({'request_id': 'create', 'account_hint': '案例客户',
            'materials': [{'evidence_id': 'EV1', 'content': '客户需要工单管理，方案待评审。'}]}, self.db)['storage_result']['opportunity_id']
        self.project = self.root / 'presales'

    def export(self, **changes):
        options = dict(db=self.db, oid=self.oid, project=self.project, project_id='CASE',
            evidence_ids=['EV1'], requirements=[{'id': 'REQ-1', 'statement': '工单管理', 'evidence_ids': ['EV1']}],
            audience='内部售前')
        options.update(changes)
        return export_project(**options)

    def prepared(self):
        self.export()
        # Reuse the presales suite's declared synthetic ZIP/PDF/image fixtures.
        source = Path(__file__).resolve().parents[2] / 'presales-solution-skills/tests/test_runtime.py'
        spec = importlib.util.spec_from_file_location('synthetic_presales_fixtures', source)
        fixtures = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(fixtures)
        helper = fixtures.RuntimeTests()
        helper.root, helper.project = self.root, self.project
        config, index = runtime().load(self.project)
        src = {'artifact_id': 'SRC-OPPORTUNITY', 'sha256': index['artifacts']['SRC-OPPORTUNITY']['sha256']}
        def register(obj):
            obj['project_id'] = 'CASE'
            path = self.root / 'registration.json'
            path.write_text(json.dumps(obj), encoding='utf-8')
            return runtime().register(self.project, path)
        content = register(helper.content([src]))
        register(helper.review(content))
        helper.files()
        delivery = register(helper.delivery(content))
        data = json.loads((self.project / delivery['path']).read_text())['data']
        register(helper.review(delivery, mode='delivery', file_hashes=data['file_hashes']))
        return content, delivery

    def receive(self, **changes):
        options = dict(db=self.db, oid=self.oid, project=self.project, delivery_id='DELIVERY-1',
            artifact_id='SOL-PPT', version=1, request_id='receive', expected_revision=1, actor='内部售前')
        options.update(changes)
        return receive_delivery(**options)

    def test_whitelist_handoff_is_real_presales_project(self):
        manifest = self.export()
        api = runtime()
        config, index = api.load(self.project)
        report, objects = api.snapshot(self.project, config, index)
        self.assertTrue(report['ok'])
        exported = (self.project / index['artifacts']['SRC-OPPORTUNITY']['path']).read_text()
        self.assertNotIn('commercial_assessment', exported)
        self.assertNotIn('competitors', exported)
        self.assertEqual(objects['REQ']['data']['items'][0]['evidence_ids'], ['EV1'])
        self.assertEqual(manifest['business_approval'], 'unconfirmed')

    def test_foreign_evidence_and_missing_runtime_fail_without_project_creation(self):
        with self.assertRaises(ValueError):
            self.export(evidence_ids=['foreign'])
        self.assertFalse(self.project.exists())
        with self.assertRaises(ValueError):
            self.export(runtime_path=self.root / 'absent.py')
        self.assertFalse(self.project.exists())

    def test_receive_real_files_replay_and_upstream_invalidation(self):
        self.prepared()
        result = self.receive()
        self.assertEqual(result['revision'], 2)
        artifact = run_detail(self.db, self.oid)['detail']['lifecycle']['artifacts'][0]
        self.assertEqual(artifact['validity'], 'valid')
        self.assertTrue(artifact['file_path'].endswith('.pptx'))
        self.assertEqual(artifact['metadata']['presales_binding']['business_approval'], 'unconfirmed')
        self.assertTrue(self.receive()['idempotent_replay'])
        index = self.project / 'work/index.json'
        index.write_text(index.read_text() + '\n')
        state = run_detail(self.db, self.oid)['detail']['lifecycle']
        self.assertEqual(state['artifacts'][0]['validity'], 'dependency_invalid')
        self.assertEqual(state['revision'], 2)
        replay = self.receive()
        self.assertTrue(replay['idempotent_replay'])
        self.assertEqual(replay['lifecycle']['artifacts'][0]['validity'], 'dependency_invalid')
        with self.assertRaises(ValueError):
            self.receive(actor='another actor')

    def test_changed_purpose_cannot_relabel_internal_delivery(self):
        self.prepared()
        path = self.project / 'work/project.json'
        config = json.loads(path.read_text())
        config['purpose'] = 'customer-review'
        path.write_text(json.dumps(config))
        with self.assertRaises(ValueError):
            self.receive()
        self.assertEqual(run_detail(self.db, self.oid)['detail']['lifecycle']['revision'], 1)

    def test_changed_delivery_and_other_opportunity_do_not_write(self):
        self.prepared()
        with self.assertRaises(ValueError):
            self.receive(oid='foreign')
        (self.project / 'deliverables/deck.pdf').write_bytes(b'%PDF-1.4 changed')
        with self.assertRaises(ValueError):
            self.receive()
        self.assertEqual(run_detail(self.db, self.oid)['detail']['lifecycle']['revision'], 1)

    def test_missing_current_review_cannot_receive(self):
        self.prepared()
        index_path = self.project / 'work/index.json'
        index = json.loads(index_path.read_text())
        del index['artifacts']['REVIEW-delivery']
        index_path.write_text(json.dumps(index))
        with self.assertRaises(ValueError):
            self.receive()
        self.assertEqual(run_detail(self.db, self.oid)['detail']['lifecycle']['revision'], 1)
