"""Delivered source integrity is independent of the registry original."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('delivery_full_auditor',
    Path(__file__).resolve().parents[1] / 'scripts/audit_full_delivery.py')
auditor = importlib.util.module_from_spec(spec)
spec.loader.exec_module(auditor)


class SourceCopyAuditTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        (self.root/'raw').mkdir()
        self.source = self.root/'raw/source-ENG-CODE-r1.py'
        self.source.write_text('approved = True\n')
        self.artifact = self.root/'raw/ENG-CODE-r1.json'
        self.artifact.write_text(json.dumps({'data':{'sha256':auditor.sha(self.source)}}))
        self.entry = {'path':'raw/ENG-CODE-r1.json', 'source_file':'raw/source-ENG-CODE-r1.py'}

    def test_delivered_original_matches(self):
        self.assertTrue(auditor.copied_source_valid(self.root,self.entry))

    def test_valid_source_artifact_cannot_hide_modified_delivered_source(self):
        self.source.write_text('approved = False\n')
        self.assertFalse(auditor.copied_source_valid(self.root,self.entry))

    def test_external_source_path_is_rejected_even_when_hash_matches(self):
        outside = self.root/'outside.py'
        outside.write_bytes(self.source.read_bytes())
        self.assertFalse(auditor.copied_source_valid(self.root/'raw',
            {'path':'ENG-CODE-r1.json', 'source_file':'../outside.py'}))

    def test_missing_delivered_source_is_rejected(self):
        self.source.unlink()
        self.assertFalse(auditor.copied_source_valid(self.root,self.entry))
