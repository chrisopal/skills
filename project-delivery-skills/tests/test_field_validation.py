import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'skills/delivery-orchestrator/scripts/field_validation.py'
spec = importlib.util.spec_from_file_location('field_validation_test', SCRIPT)
field = importlib.util.module_from_spec(spec)
spec.loader.exec_module(field)
FIXTURE = ROOT / 'tests/fixtures/field-inputs/manifest.json'


class FieldValidationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.out = Path(self.temp.name) / 'case'

    def claims(self, case=None):
        case = case or self.out
        receipt = json.loads((case / 'intake.json').read_text())
        source = receipt['sources'][0]
        claim = dict(id='C1', statement='合同范围需依来源审核', source_refs=[dict(source['ref'], locator='L3-L3', quote=source['lines'][2])])
        field.runtime.atomic_json(case / 'claims.json', dict(claims=[claim], open_items=['签署页尚未提供']))
        return claim

    def test_frozen_inputs_support_independent_source_quote_audit(self):
        result = field.prepare(FIXTURE, self.out)
        self.assertEqual(result['material_origin'], 'simulation')
        self.assertEqual(result['source_count'], 3)
        self.claims()
        check = field.audit(self.out)
        self.assertTrue(check['technical_pass'])
        self.assertEqual(check['semantic_verdict'], 'requires-independent-review')
        self.assertFalse(check['customer_accepted'])
        self.assertFalse(check['actual_material_validation'])
        self.assertFalse(field.runtime.read_registry(self.out / 'project')['effective'])

    def test_invented_quote_and_wrong_revision_fail(self):
        field.prepare(FIXTURE, self.out)
        claim = self.claims()
        claim['source_refs'][0]['quote'] = '客户已经签字验收'
        field.runtime.atomic_json(self.out / 'claims.json', dict(claims=[claim], open_items=[]))
        self.assertFalse(field.audit(self.out)['technical_pass'])
        claim['source_refs'][0]['revision'] = 99
        field.runtime.atomic_json(self.out / 'claims.json', dict(claims=[claim], open_items=[]))
        self.assertIn('Invalid source reference', str(field.audit(self.out)['errors']))

    def test_extracted_copy_tampering_is_detected(self):
        field.prepare(FIXTURE, self.out)
        self.claims()
        (self.out / 'extracted/SRC-CONTRACT.txt').write_text('altered')
        self.assertIn('Extraction changed', str(field.audit(self.out)['errors']))

    def test_refuses_overwrite(self):
        field.prepare(FIXTURE, self.out)
        with self.assertRaises(ValueError):
            field.prepare(FIXTURE, self.out)

    def test_unread_attachment_and_missing_roles_remain_visible(self):
        root = Path(self.temp.name)
        (root / 'audio.mp3').write_bytes(b'not-transcribed')
        manifest = dict(project_id='ACTUAL-INPUT', material_origin='actual', authorization_note='test only', redaction_note='test',
                        materials=[dict(id='SRC-AUDIO', role='discovery', path='audio.mp3')])
        field.runtime.atomic_json(root / 'manifest.json', manifest)
        result = field.prepare(root / 'manifest.json', self.out)
        self.assertEqual(result['unread'], ['SRC-AUDIO'])
        self.assertEqual(result['missing_roles'], ['contract', 'technical_agreement'])
        self.assertEqual(field.runtime.read_project(self.out / 'project')['purpose'], 'internal')
        # Explicit origin selection does not authenticate material provenance.
        self.assertFalse(json.loads((self.out / 'intake.json').read_text())['semantic_reviewed'])

    def test_requires_authority_origin_and_unique_sources(self):
        root = Path(self.temp.name)
        (root / 'one.md').write_text('原文')
        manifest = dict(project_id='P', material_origin='simulation', redaction_note='test',
                        materials=[dict(id='SRC', role='contract', path='one.md')])
        field.runtime.atomic_json(root / 'manifest.json', manifest)
        with self.assertRaises(ValueError):
            field.prepare(root / 'manifest.json', self.out)
        self.assertFalse(self.out.exists())
        manifest['authorization_note'] = 'test'
        manifest['materials'] *= 2
        field.runtime.atomic_json(root / 'manifest.json', manifest)
        with self.assertRaises(ValueError):
            field.prepare(root / 'manifest.json', self.out)


if __name__=='__main__':
    unittest.main()
