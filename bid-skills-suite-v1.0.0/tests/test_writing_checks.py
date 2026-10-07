"""Writing checks distinguish directory mapping from actual draft coverage."""
import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import writing_checks


class WritingChecksTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.project = Path(self.tmp.name)
        (self.project / 'artifacts').mkdir()
        self.demo = ROOT / 'examples/smart-factory-demo/artifacts'
        self.files = {}
        for number in [3, 4, 5, 6, 8, 9, 10, 11, 13]:
            source = next(self.demo.glob(f'{number:02d}-*.json'))
            payload = json.loads(source.read_text())
            payload['inputs'] = []
            payload['project_id'] = 'TEST-WRITING'
            if number == 13:
                for figure in payload['data']['figures']:
                    figure.update(source_path=None, rendered_path=None, state='specified')
            self.files[number] = self.project / 'artifacts' / source.name
            self.files[number].write_text(json.dumps(payload))

    def check(self):
        return writing_checks.check_project(self.project, self.files[8], self.files[11])

    def change(self, number, mutate):
        payload = json.loads(self.files[number].read_text())
        mutate(payload['data'])
        self.files[number].write_text(json.dumps(payload))

    def test_semantic_acceptance_is_not_implied(self):
        result = self.check()
        self.assertTrue(result['structural_valid'], result['errors'])
        self.assertEqual(result['semantic_acceptance'], 'NOT_TESTED')

    def test_mapping_does_not_equal_written_response(self):
        self.change(11, lambda d: d.update(chapters=[], responses=[]))
        result = self.check()
        self.assertTrue(result['planned_not_written'])
        self.assertTrue(result['missing_responses'])

    def test_parent_scoring_binding_means_started_not_accepted(self):
        outline = json.loads(self.files[8].read_text())
        writing = json.loads(self.files[11].read_text())
        section = next(s for s in outline['data']['sections']
                       if s['id'] == writing['data']['chapters'][0]['section_id'])
        section['scoring_ids'] = []
        parent = dict(section, id='PARENT', parent_id=None, scoring_ids=['S-001'])
        section['parent_id'] = 'PARENT'
        outline['data']['sections'].append(parent)
        self.files[8].write_text(json.dumps(outline))
        result = self.check()
        self.assertIn('S-001', result['scoring_started'])
        self.assertIn('S-001', result['scoring_pending_review'])
        self.assertEqual(result['semantic_acceptance'], 'NOT_TESTED')

    def test_unknown_chapter_requirement_is_error(self):
        self.change(11, lambda d: d['chapters'][0]['requirement_ids'].append('UNKNOWN'))
        self.assertFalse(self.check()['structural_valid'])

    def test_unknown_response_chapter_is_error(self):
        self.change(11, lambda d: d['responses'][0]['chapter_ids'].append('UNKNOWN'))
        self.assertFalse(self.check()['structural_valid'])

    def test_body_change_invalidates_paragraph_trace(self):
        writing = json.loads(self.files[11].read_text())
        chapter = writing['data']['chapters'][0]
        trace = {'writing_sha256': writing_checks.digest(self.files[11]), 'links': [
            {'chapter_id': chapter['id'], 'requirement_id': chapter['requirement_ids'][0],
             'body_quote': chapter['body_markdown']}]}
        (self.project / 'artifacts/11-writing-trace.json').write_text(json.dumps(trace))
        self.change(11, lambda d: d['chapters'][0].update(body_markdown='Changed draft'))
        self.assertEqual(self.check()['trace_state'], 'stale')

    def test_upstream_hash_change_is_error(self):
        payload = json.loads(self.files[11].read_text())
        payload['inputs'] = [{'artifact_id': 'X', 'revision': 1,
            'relative_path': self.files[8].relative_to(self.project).as_posix(),
            'sha256': '0' * 64}]
        self.files[11].write_text(json.dumps(payload))
        self.assertFalse(self.check()['structural_valid'])

    def test_response_copied_into_body_cannot_prove_paragraph_trace(self):
        writing = json.loads(self.files[11].read_text())
        response = writing['data']['responses'][0]
        chapter = next(c for c in writing['data']['chapters'] if c['id'] in response['chapter_ids'])
        chapter['body_markdown'] += '\n\n' + response['response']
        self.files[11].write_text(json.dumps(writing))
        trace = {'writing_sha256': writing_checks.digest(self.files[11]), 'links': [
            {'chapter_id': chapter['id'], 'requirement_id': response['requirement_id'],
             'body_quote': response['response']}]}
        (self.project / 'artifacts/11-writing-trace.json').write_text(json.dumps(trace))
        result = self.check()
        self.assertFalse(result['structural_valid'])
        self.assertIn('段落追溯不能用响应全文或纯需求原文自证', result['errors'])
        self.assertIn(response['requirement_id'], result['written_without_paragraph_trace'])

    def test_original_requirement_alone_cannot_prove_paragraph_trace(self):
        writing = json.loads(self.files[11].read_text())
        chapter = writing['data']['chapters'][0]
        requirement_id = chapter['requirement_ids'][0]
        requirements = json.loads(self.files[3].read_text())['data']['requirements']
        quote = next(r['text'] for r in requirements if r['id'] == requirement_id)
        chapter['body_markdown'] += '\n\n' + quote
        self.files[11].write_text(json.dumps(writing))
        trace = {'writing_sha256': writing_checks.digest(self.files[11]), 'links': [
            {'chapter_id': chapter['id'], 'requirement_id': requirement_id, 'body_quote': quote}]}
        (self.project / 'artifacts/11-writing-trace.json').write_text(json.dumps(trace))
        self.assertFalse(self.check()['structural_valid'])

    def test_raw_classification_json_is_hashed_without_inventing_envelope(self):
        source = self.project / 'classification.json'
        source.write_text(json.dumps({'project_id': 'TEST-WRITING', 'decision': 'proposal'}))
        payload = json.loads(self.files[11].read_text())
        payload['inputs'] = [{'artifact_id': 'CLASSIFICATION', 'revision': 1,
                             'relative_path': 'classification.json',
                             'sha256': writing_checks.digest(source)}]
        self.files[11].write_text(json.dumps(payload))
        self.assertTrue(self.check()['structural_valid'])

    def test_other_project_cannot_supply_requirements(self):
        payload = json.loads(self.files[3].read_text())
        payload['project_id'] = 'OTHER'
        self.files[3].write_text(json.dumps(payload))
        self.assertFalse(self.check()['structural_valid'])

    def test_outside_project_path_is_rejected(self):
        with self.assertRaises(ValueError):
            writing_checks.check_project(self.project, ROOT / 'registry.json', self.files[11])

    def test_rendered_missing_figure_is_error(self):
        self.change(13, lambda d: d['figures'][0].update(state='rendered',
                     rendered_path='assets/missing.png'))
        self.assertFalse(self.check()['structural_valid'])

    def test_duplicate_response_is_error(self):
        self.change(11, lambda d: d['responses'].append(copy.deepcopy(d['responses'][0])))
        self.assertFalse(self.check()['structural_valid'])


if __name__ == '__main__':
    unittest.main()
