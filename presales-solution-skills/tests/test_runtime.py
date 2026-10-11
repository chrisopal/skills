"""Black-box runtime tests; all fixtures are synthetic, never customer evidence."""
import json
import base64
import hashlib
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile

RUNTIME = Path(__file__).resolve().parents[1] / 'skills/presales-orchestrator/scripts/runtime.py'


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.project = self.root / 'project'
        self.cli('init', self.project, '--project-id', 'DEMO', '--purpose', 'internal-draft')

    def cli(self, *args, ok=True):
        result = subprocess.run([sys.executable, str(RUNTIME), *map(str, args)], capture_output=True, text=True)
        if ok:
            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        else:
            self.assertNotEqual(result.returncode, 0, result.stdout)
        return json.loads(result.stdout) if result.stdout.strip().startswith('{') else result.stderr

    def source(self):
        path = self.root / 'input.txt'
        path.write_text('synthetic source', encoding='utf-8')
        return self.cli('source', self.project, path, '--id', 'SRC-1')

    def envelope(self, aid, kind, inputs=(), data=None, revision=1):
        return dict(project_id='DEMO', artifact_id=aid, kind=kind, revision=revision,
                    inputs=[dict(artifact_id=x['artifact_id'], sha256=x['sha256']) for x in inputs],
                    status='ready', data={} if data is None else data)

    def register(self, obj, ok=True):
        path = self.root / 'registration.json'
        path.write_text(json.dumps(obj), encoding='utf-8')
        return self.cli('register', self.project, path, ok=ok)

    def content(self, inputs=(), revision=1):
        return self.envelope('CONTENT-1', 'content', inputs, dict(deck_id='DECK-1', purpose='discussion', audience='team',
            slides=[dict(slide_id='SLIDE-1', title='A title', key_message='A message', supporting_points=['A point'],
                         visible_caveats=['Synthetic only'], locked_claims=['No promise'], speaker_notes='Notes',
                         visual_type='text', review_status='pending', requirement_ids=[], solution_ids=[],
                         evidence_ids=[], material_ids=[], artifact_ids=[])],
            internal_log='DO NOT EXPORT', language='zh-CN', page_budget=1, duration_minutes=5, theme_profile='simple'), revision)

    def review(self, target, mode='content', revision=1, **changes):
        data = dict(mode=mode, target_id=target['artifact_id'], target_sha256=target['sha256'], verdict='pass',
                    method='independent-source-readback', reviewer='reviewer-1', findings=[], scope=['synthetic'], unchecked=[])
        data.update(changes)
        return self.envelope('REVIEW-' + mode, 'review', [target], data, revision)

    def prepared(self):
        src = self.source()
        content = self.register(self.content([src]))
        review = self.register(self.review(content))
        return src, content, review

    def files(self, count=1):
        directory = self.project / 'deliverables'
        directory.mkdir(exist_ok=True)
        pptx = directory / 'deck.pptx'
        with zipfile.ZipFile(pptx, 'w') as archive:
            archive.writestr('[Content_Types].xml', '<Types/>')
            ids = ''.join(f'<p:sldId id="{255+n}" r:id="rId{n}"/>' for n in range(1, count+1))
            rels = ''.join(f'<Relationship Id="rId{n}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide" Target="slides/slide{n}.xml"/>' for n in range(1, count+1))
            archive.writestr('ppt/presentation.xml', '<p:presentation xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><p:sldIdLst>' + ids + '</p:sldIdLst></p:presentation>')
            archive.writestr('ppt/_rels/presentation.xml.rels', '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">' + rels + '</Relationships>')
            for n in range(1, count + 1):
                archive.writestr(f'ppt/slides/slide{n}.xml', '<p:sld xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"/>')
        (directory / 'deck.pdf').write_bytes(b'%PDF-1.4\nsynthetic fixture')
        image = directory / 'page1.png'
        image.write_bytes(base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jXioAAAAASUVORK5CYII='))
        render = dict(renderer='synthetic-fixture', reviewer='fixture-author', pages=[dict(page=1,
            image_path='deliverables/page1.png', sha256=hashlib.sha256(image.read_bytes()).hexdigest(),
            verdict='pass', observations='Synthetic structure fixture; no actual visual claim')])
        (directory / 'render.json').write_text(json.dumps(render), encoding='utf-8')

    def delivery(self, content):
        return self.envelope('DELIVERY-1', 'delivery', [content], dict(pptx_path='deliverables/deck.pptx',
            pdf_path='deliverables/deck.pdf', input_content_id=content['artifact_id'], input_content_sha256=content['sha256'],
            page_map=[dict(slide_id='SLIDE-1', page=1)], render_evidence_path='deliverables/render.json',
            native_review=dict(status='pass', method='synthetic-fixture', reviewer='fixture-author')))

    def test_init_preserves_existing_project(self):
        self.cli('init', self.project, '--project-id', 'OTHER', '--purpose', 'internal-draft', ok=False)
        self.assertEqual(self.cli('status', self.project)['project_id'], 'DEMO')

    def test_source_is_frozen_and_not_overwritten(self):
        source = self.source()
        frozen = self.project / source['path']
        self.assertEqual(frozen.read_text(), 'synthetic source')
        self.assertEqual(frozen.stat().st_mode & 0o222, 0)
        self.cli('source', self.project, self.root / 'input.txt', '--id', 'SRC-1', ok=False)
        (self.root / 'input.txt').write_text('outside changed')
        self.cli('validate', self.project)

    def test_source_tamper_transitively_stales_content_and_review(self):
        src, content, review = self.prepared()
        frozen = self.project / src['path']
        frozen.chmod(0o644)
        frozen.write_text('tampered')
        result = self.cli('status', self.project, ok=False)
        for aid in (src['artifact_id'], content['artifact_id'], review['artifact_id']):
            self.assertEqual(result['artifacts'][aid]['state'], 'stale')
        self.cli('prepare-ppt', self.project, content['artifact_id'], '--out', self.project / 'handoff', ok=False)

    def test_revision_invalidates_old_review(self):
        src, content, _ = self.prepared()
        revised = self.content([src], revision=2)
        revised['data']['slides'][0]['title'] = 'Changed'
        current = self.register(revised)
        self.assertNotEqual(content['sha256'], current['sha256'])
        self.cli('prepare-ppt', self.project, current['artifact_id'], '--out', self.project / 'handoff', ok=False)
        self.register(self.review(current, revision=2))
        self.cli('prepare-ppt', self.project, current['artifact_id'], '--out', self.project / 'handoff')

    def test_review_old_hash_unbound_or_blocking_never_approves(self):
        content = self.register(self.content())
        review = self.review(content)
        review['inputs'] = []
        self.register(review, ok=False)
        review = self.review(content, target_sha256='0' * 64)
        self.register(review, ok=False)
        review = self.review(content, findings=[dict(finding_id='FIND-1', severity='blocking', status='open')])
        self.register(review, ok=False)
        review = self.review(content, findings=[dict(finding_id='FIND-1', severity='blocking', status='closed')])
        self.register(review, ok=False)

    def test_nonpassing_and_selfcheck_review_do_not_unlock(self):
        content = self.register(self.content())
        self.register(self.review(content, verdict='conditional'))
        self.cli('prepare-ppt', self.project, content['artifact_id'], '--out', self.project / 'handoff', ok=False)
        self.register(self.review(content, revision=2, method='self-check'))
        self.cli('prepare-ppt', self.project, content['artifact_id'], '--out', self.project / 'handoff', ok=False)

    def test_content_missing_safety_fields_or_duplicate_ids_rejected(self):
        for field in ('slide_id', 'visible_caveats', 'locked_claims', 'requirement_ids', 'visual_type', 'review_status'):
            content = self.content()
            del content['data']['slides'][0][field]
            self.register(content, ok=False)
        content = self.content()
        content['data']['slides'] *= 2
        self.register(content, ok=False)

    def test_cross_project_broken_reference_and_cycle_rejected(self):
        obj = self.envelope('REQ-1', 'requirements')
        obj['project_id'] = 'OTHER'
        self.register(obj, ok=False)
        obj['project_id'] = 'DEMO'
        obj['inputs'] = [dict(artifact_id='MISSING', sha256='0' * 64)]
        self.register(obj, ok=False)
        first = self.register(self.envelope('REQ-1', 'requirements'))
        second = self.register(self.envelope('SOL-1', 'solution', [first]))
        self.register(self.envelope('REQ-1', 'requirements', [second], revision=2), ok=False)

    def test_traversal_and_symlink_escape_rejected(self):
        source_file = self.root / 'source.txt'
        source_file.write_text('fixture')
        self.cli('source', self.project, source_file, '--id', '../escape', ok=False)
        content = self.register(self.content())
        self.register(self.review(content))
        self.cli('prepare-ppt', self.project, content['artifact_id'], '--out', self.root / 'escape', ok=False)
        (self.project / 'linked').symlink_to(self.root, target_is_directory=True)
        self.cli('prepare-ppt', self.project, content['artifact_id'], '--out', self.project / 'linked/out', ok=False)
        (self.project / 'inputs').rmdir()
        (self.project / 'inputs').symlink_to(self.root, target_is_directory=True)
        self.cli('source', self.project, source_file, '--id', 'SRC-X', ok=False)

    def test_external_artifact_edit_detected(self):
        content = self.register(self.content())
        path = self.project / content['path']
        path.write_text(path.read_text().replace('A title', 'Injected'))
        result = self.cli('validate', self.project, ok=False)
        self.assertEqual(result['artifacts']['CONTENT-1']['state'], 'stale')

    def test_ppt_missing_page_wrong_order_and_external_path_rejected(self):
        _, content, _ = self.prepared()
        self.files(2)
        self.register(self.delivery(content), ok=False)
        self.files(1)
        delivery = self.delivery(content)
        delivery['data']['page_map'][0]['slide_id'] = 'SLIDE-OTHER'
        self.register(delivery, ok=False)
        delivery = self.delivery(content)
        delivery['data']['pdf_path'] = '../outside.pdf'
        self.register(delivery, ok=False)

    def test_delivery_hashes_and_review_invalidate_after_file_tamper(self):
        _, content, _ = self.prepared()
        self.files()
        delivery = self.register(self.delivery(content))
        data = json.loads((self.project / delivery['path']).read_text())['data']
        self.register(self.review(delivery, mode='delivery'), ok=False)
        self.register(self.review(delivery, mode='delivery', file_hashes=data['file_hashes']))
        (self.project / 'deliverables/deck.pdf').write_bytes(b'%PDF-1.4\nchanged')
        result = self.cli('validate', self.project, ok=False)
        self.assertEqual(result['artifacts']['DELIVERY-1']['state'], 'stale')
        self.assertEqual(result['artifacts']['REVIEW-delivery']['state'], 'stale')

    def test_source_revision_stales_chain_and_rebuild_recovers(self):
        src, content, _ = self.prepared()
        original = self.root / 'input.txt'
        original.write_text('revised synthetic source')
        current_source = self.cli('source', self.project, original, '--id', 'SRC-1', '--revision', '2')
        self.assertTrue((self.project / src['path']).exists())
        status = self.cli('status', self.project, ok=False)
        self.assertEqual(status['artifacts']['CONTENT-1']['state'], 'stale')
        updated = self.register(self.content([current_source], revision=2))
        self.register(self.review(updated, revision=2))
        self.cli('validate', self.project)
        self.cli('prepare-ppt', self.project, updated['artifact_id'], '--out', self.project / 'recovered')

    def test_output_conflicts_and_nested_private_fields_rejected(self):
        _, content, _ = self.prepared()
        output = self.project / 'handoff'
        self.cli('prepare-ppt', self.project, content['artifact_id'], '--out', output)
        self.cli('prepare-ppt', self.project, content['artifact_id'], '--out', output, ok=False)
        bad = self.content(revision=2)
        bad['data']['slides'][0]['layout_hint'] = {'private_notes': 'secret'}
        self.register(bad, ok=False)

    def test_ppt_presentation_relationships_must_match_actual_slides(self):
        _, content, _ = self.prepared()
        self.files()
        path = self.project / 'deliverables/deck.pptx'
        with zipfile.ZipFile(path, 'w') as archive:
            archive.writestr('[Content_Types].xml', '<Types/>')
            archive.writestr('ppt/slides/slide1.xml', '<slide/>')
        self.register(self.delivery(content), ok=False)

    def test_slide_artifact_reference_must_exist(self):
        content = self.content()
        content['data']['slides'][0]['artifact_ids'] = ['REQ-MISSING']
        self.register(content, ok=False)

    def test_slide_artifact_reference_must_be_bound_in_dependency_graph(self):
        self.register(self.envelope('REQ-UNBOUND', 'requirements'))
        content = self.content()
        content['data']['slides'][0]['artifact_ids'] = ['REQ-UNBOUND']
        self.register(content, ok=False)

    def test_slide_artifact_reference_accepts_transitive_and_distinct_business_ids(self):
        source = self.source()
        evidence = self.register(self.envelope('EVIDENCE-1', 'evidence', [source]))
        requirements = self.register(self.envelope('REQUIREMENTS-1', 'requirements', [evidence]))
        content = self.content([requirements])
        content['data']['slides'][0].update(artifact_ids=['REQUIREMENTS-1', 'EVIDENCE-1', 'SRC-1'],
            requirement_ids=['REQ-BUSINESS-1'], evidence_ids=['EV-BUSINESS-1'])
        registered = self.register(content)
        self.register(self.review(registered))
        self.cli('validate', self.project)
        self.cli('prepare-ppt', self.project, registered['artifact_id'], '--out', self.project / 'transitive')

    def test_referenced_artifact_revision_stales_content_and_review(self):
        requirements = self.register(self.envelope('REQUIREMENTS-1', 'requirements'))
        solution = self.register(self.envelope('SOLUTION-1', 'solution', [requirements]))
        content = self.content([solution])
        content['data']['slides'][0]['artifact_ids'] = ['REQUIREMENTS-1']
        registered = self.register(content)
        self.register(self.review(registered))
        self.register(self.envelope('REQUIREMENTS-1', 'requirements', revision=2))
        result = self.cli('status', self.project, ok=False)
        for aid in ('SOLUTION-1', 'CONTENT-1', 'REVIEW-content'):
            self.assertEqual(result['artifacts'][aid]['state'], 'stale')
        self.cli('prepare-ppt', self.project, registered['artifact_id'], '--out', self.project / 'stale', ok=False)
        content['revision'] = 2
        self.register(content, ok=False)

    def test_eight_direct_slide_artifact_references_remain_valid(self):
        dependencies = [self.register(self.envelope(f'ART-{n}', 'requirements')) for n in range(1, 9)]
        content = self.content(dependencies)
        content['data']['slides'][0]['artifact_ids'] = [item['artifact_id'] for item in dependencies]
        registered = self.register(content)
        self.register(self.review(registered))
        self.cli('validate', self.project)
        self.cli('prepare-ppt', self.project, registered['artifact_id'], '--out', self.project / 'eight')

    def test_handoff_retains_page_references_and_deck_metadata(self):
        artifact = self.register(self.envelope('ART-1', 'requirements'))
        content_data = self.content([artifact])
        content_data['data']['slides'][0].update(section='Approach', requirement_ids=['REQ-1'], solution_ids=['SOL-1'],
            evidence_ids=['EV-1'], material_ids=['MAT-1'], artifact_ids=['ART-1'])
        content = self.register(content_data)
        self.register(self.review(content))
        output = self.project / 'metadata'
        self.cli('prepare-ppt', self.project, content['artifact_id'], '--out', output)
        markdown = (output / 'content.md').read_text()
        for text in ('REQ-1', 'SOL-1', 'EV-1', 'MAT-1', 'ART-1', 'Approach', 'pending', 'discussion',
                     'zh-CN', 'page_budget', 'duration_minutes', 'simple'):
            self.assertIn(text, markdown)
        handoff = json.loads((output / 'handoff.json').read_text())
        self.assertEqual(handoff['deck']['purpose'], 'discussion')
        self.assertEqual(handoff['deck']['duration_minutes'], 5)
        bad = self.content(revision=2)
        bad['data']['page_budget'] = 'many'
        self.register(bad, ok=False)

    def test_delivery_requires_pdf_and_real_render_files(self):
        _, content, _ = self.prepared()
        self.files()
        evidence = self.project / 'deliverables/render.json'
        good = evidence.read_text()
        for invalid in ('{}', '{"pages": []}', 'not json'):
            evidence.write_text(invalid)
            self.register(self.delivery(content), ok=False)
        evidence.write_text(good)
        image = self.project / 'deliverables/page1.png'
        image.write_bytes(b'changed image')
        self.register(self.delivery(content), ok=False)
        self.files()
        (self.project / 'deliverables/deck.pdf').write_text('Not a PDF')
        self.register(self.delivery(content), ok=False)

    def test_delivery_pass_needs_native_and_render_pass(self):
        _, content, _ = self.prepared()
        self.files()
        for revision, status in enumerate(('not_checked', 'fail', 'conditional'), 1):
            data = self.delivery(content)
            data['revision'] = revision
            data['data']['native_review']['status'] = status
            delivery = self.register(data)
            hashes = json.loads((self.project / delivery['path']).read_text())['data']['file_hashes']
            self.register(self.review(delivery, mode='delivery', file_hashes=hashes), ok=False)
        render_path = self.project / 'deliverables/render.json'
        render = json.loads(render_path.read_text())
        render['pages'][0]['verdict'] = 'not_checked'
        render_path.write_text(json.dumps(render))
        data = self.delivery(content)
        data['revision'] = 4
        delivery = self.register(data)
        hashes = json.loads((self.project / delivery['path']).read_text())['data']['file_hashes']
        self.register(self.review(delivery, mode='delivery', file_hashes=hashes), ok=False)

    def test_render_image_tamper_stales_delivery_and_review(self):
        _, content, _ = self.prepared()
        self.files()
        delivery = self.register(self.delivery(content))
        hashes = json.loads((self.project / delivery['path']).read_text())['data']['file_hashes']
        self.assertIn('render_pages', hashes)
        self.assertIn('deliverables/page1.png', hashes['render_pages'])
        self.register(self.review(delivery, mode='delivery', file_hashes=hashes))
        (self.project / 'deliverables/page1.png').write_bytes(b'tampered')
        status = self.cli('status', self.project, ok=False)
        self.assertEqual(status['artifacts']['DELIVERY-1']['state'], 'stale')
        self.assertEqual(status['artifacts']['REVIEW-delivery']['state'], 'stale')

    def test_project_ancestor_symlink_rejected(self):
        alias = self.root / 'alias'
        alias.symlink_to(self.root, target_is_directory=True)
        self.cli('init', alias / 'new-project', '--project-id', 'OTHER', '--purpose', 'internal-draft', ok=False)

    def test_successful_handoff_exports_only_whitelist(self):
        _, content, _ = self.prepared()
        output = self.project / 'handoff'
        self.cli('prepare-ppt', self.project, content['artifact_id'], '--out', output)
        markdown = (output / 'content.md').read_text()
        self.assertIn('Synthetic only', markdown)
        self.assertIn('No promise', markdown)
        self.assertNotIn('DO NOT EXPORT', markdown)
        handoff = json.loads((output / 'handoff.json').read_text())
        self.assertEqual(handoff['content_sha256'], content['sha256'])
        self.assertEqual(handoff['business_approval'], 'unconfirmed')
        self.assertEqual(handoff['purpose'], 'internal-draft')
        self.assertNotIn('internal_log', json.dumps(handoff))
        self.cli('validate', self.project)


if __name__ == '__main__':
    unittest.main()
