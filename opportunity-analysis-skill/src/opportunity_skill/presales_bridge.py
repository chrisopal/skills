"""Explicit handoff to the installed presales runtime; no parallel PPT renderer."""
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile

from .pipeline import run_manage
from .storage import OpportunitySQLiteAdapter


def runtime(path=None):
    candidates = [Path(path)] if path else [
        Path(__file__).resolve().parents[3] / 'presales-orchestrator/scripts/runtime.py',
        Path(__file__).resolve().parents[3] / 'presales-solution-skills/skills/presales-orchestrator/scripts/runtime.py',
        Path.home() / '.codex/skills/presales-orchestrator/scripts/runtime.py',
    ]
    source = next((p for p in candidates if p.is_file()), None)
    if source is None:
        raise ValueError('presales-orchestrator runtime unavailable; install it or supply --runtime')
    spec = importlib.util.spec_from_file_location('opportunity_presales_runtime', source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def read_detail(db, oid):
    adapter = OpportunitySQLiteAdapter(db)
    try:
        return adapter.get_opportunity_detail(oid)
    finally:
        adapter.close()


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def export_project(db, oid, project, project_id, evidence_ids, requirements, *, audience,
                   purpose='internal-draft', runtime_path=None):
    """Export only selected raw evidence and authored requirements, never sales scores."""
    api = runtime(runtime_path)
    detail = read_detail(db, oid)
    owned = {e['id']: e for e in detail['evidence']}
    if not evidence_ids or len(set(evidence_ids)) != len(evidence_ids) or any(e not in owned for e in evidence_ids):
        raise ValueError('select distinct evidence owned by this opportunity')
    if not isinstance(requirements, list) or not requirements:
        raise ValueError('authored requirements items required')
    items, seen = [], set()
    for item in requirements:
        if not isinstance(item, dict) or not isinstance(item.get('id'), str) or item['id'] in seen or not item['id'].strip():
            raise ValueError('requirements need distinct nonempty IDs')
        refs = item.get('evidence_ids')
        if not isinstance(refs, list) or not refs or any(e not in evidence_ids for e in refs):
            raise ValueError('requirements must cite selected evidence')
        if not isinstance(item.get('statement'), str) or not item['statement'].strip():
            raise ValueError('requirement statement required')
        seen.add(item['id'])
        # Deliberate whitelist: no sales judgment or arbitrary nested payload.
        items.append({k: item[k] for k in ('id', 'statement', 'evidence_ids', 'original_quote',
                      'type', 'stakeholder', 'conditions', 'priority', 'success_standard') if k in item})
    if not isinstance(audience, str) or not audience.strip():
        raise ValueError('audience required')
    project = Path(project).expanduser().resolve()
    api.initialize(project, project_id, purpose)
    source_data = {'opportunity_id': oid, 'customer': detail['account']['company_name'],
                   'evidence': [{'id': eid, 'content': owned[eid]['content'],
                                 'source_name': owned[eid].get('source_name'),
                                 'source_type': owned[eid].get('source_type')} for eid in evidence_ids],
                   'requirements': items, 'business_approval': 'unconfirmed'}
    with tempfile.TemporaryDirectory() as temporary:
        source = Path(temporary) / 'opportunity-handoff.json'
        source.write_text(json.dumps(source_data, ensure_ascii=False, indent=2), encoding='utf-8')
        entry = api.add_source(project, source, 'SRC-OPPORTUNITY', 1)
    def register(aid, kind, data, inputs):
        obj = {'project_id': project_id, 'artifact_id': aid, 'kind': kind, 'revision': 1,
               'status': 'ready', 'inputs': inputs, 'data': data}
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'artifact.json'
            path.write_text(json.dumps(obj, ensure_ascii=False), encoding='utf-8')
            result = api.register(project, path)
        return {'artifact_id': aid, 'sha256': result['sha256']}
    source_binding = {'artifact_id': 'SRC-OPPORTUNITY', 'sha256': entry['sha256']}
    brief = register('BRIEF', 'brief', {'customer': detail['account']['company_name'],
        'audience': audience, 'purpose': purpose, 'authorization': 'local-draft-only',
        'assumptions': ['Customer acceptance, external delivery and product capability remain unconfirmed.']}, [source_binding])
    evidence = register('EV', 'evidence', {'items': [dict(id=eid, source_id='SRC-OPPORTUNITY',
        locator='evidence/' + eid, quote=owned[eid]['content'], evidence_type='customer-statement',
        read_status='read') for eid in evidence_ids]}, [source_binding])
    register('REQ', 'requirements', {'items': items}, [brief, evidence])
    manifest = {'schema_version': 1, 'opportunity_id': oid, 'project_id': project_id,
                'project_config_sha256': digest(api.rooted(project, 'work/project.json')),
                'export_revision': detail['lifecycle']['revision'], 'source': source_binding,
                'evidence_hashes': {eid: hashlib.sha256(owned[eid]['content'].encode()).hexdigest() for eid in evidence_ids},
                'business_approval': 'unconfirmed', 'purpose': purpose}
    api.write_json(api.rooted(project, 'work/opportunity-handoff.json'), manifest, exclusive=True)
    return {'project': str(project), **manifest}


def receive_delivery(db, oid, project, delivery_id, *, artifact_id, version, request_id,
                     expected_revision, actor, document_id='solution', runtime_path=None):
    project = Path(project).expanduser().resolve()
    call = {'opportunity_id': oid, 'project': str(project), 'delivery_id': delivery_id,
            'artifact_id': artifact_id, 'version': version, 'request_id': request_id,
            'expected_revision': expected_revision, 'actor': actor, 'document_id': document_id,
            'runtime_path': str(Path(runtime_path).expanduser().resolve()) if runtime_path else None}
    # Recover the immutable managed receipt before deriving any live file hashes.
    # A replay must still report current validity, even if its presales input changed.
    adapter = OpportunitySQLiteAdapter(db)
    try:
        with adapter.transaction():
            row = adapter.conn.execute('SELECT response_json FROM lifecycle_requests WHERE request_id=?', (request_id,)).fetchone()
            if row:
                receipt = json.loads(row['response_json'])
                original = next((a for a in receipt.get('lifecycle', {}).get('artifacts', [])
                                 if a['id'] == artifact_id), {})
                if original.get('metadata', {}).get('presales_call') != call:
                    raise ValueError('request_id already used with a different presales call')
                receipt['lifecycle'] = adapter.get_lifecycle(oid)
                receipt['current_revision'] = receipt['lifecycle']['revision']
                receipt['idempotent_replay'] = True
                return receipt
    finally:
        adapter.close()
    api = runtime(runtime_path)
    config, index = api.load(project)
    report, objects = api.snapshot(project, config, index)
    manifest_path = api.rooted(project, 'work/opportunity-handoff.json')
    manifest = api.read_json(manifest_path)
    if manifest.get('opportunity_id') != oid or manifest.get('project_id') != config['project_id']:
        raise ValueError('presales handoff belongs to another opportunity/project')
    if manifest.get('purpose') != config.get('purpose') or manifest.get('project_config_sha256') != digest(api.rooted(project, 'work/project.json')):
        raise ValueError('presales project purpose/config changed since handoff')
    detail = read_detail(db, oid)
    owned = {e['id']: e for e in detail['evidence']}
    evidence = manifest['evidence_hashes']
    if not evidence or any(e not in owned or hashlib.sha256(owned[e]['content'].encode()).hexdigest() != sha for e, sha in evidence.items()):
        raise ValueError('handoff evidence missing or changed')
    delivery = objects.get(delivery_id)
    if not delivery or delivery['kind'] != 'delivery' or report['artifacts'][delivery_id]['state'] != 'ready':
        raise ValueError('current valid presales delivery required')
    bound_ids = set()
    def visit(aid):
        if aid in bound_ids:
            return
        bound_ids.add(aid)
        for binding in objects.get(aid, {}).get('inputs', []):
            visit(binding['artifact_id'])
    visit(delivery_id)
    src = manifest['source']
    if src['artifact_id'] not in bound_ids or index['artifacts'][src['artifact_id']]['sha256'] != src['sha256']:
        raise ValueError('delivery must consume the exported opportunity handoff')
    def reviews_for(target_id, mode, independent=False):
        target = index['artifacts'][target_id]
        matches = [(rid, obj['data']) for rid, obj in objects.items() if obj['kind'] == 'review'
            and report['artifacts'][rid]['state'] == 'ready' and obj['data'].get('mode') == mode
            and obj['data'].get('target_id') == target_id and obj['data'].get('target_sha256') == target['sha256']]
        if not matches or any(data['verdict'] != 'pass' for _, data in matches):
            raise ValueError('valid bound passing ' + mode + ' review required')
        if independent and not any(data['method'].startswith('independent-') for _, data in matches):
            raise ValueError('independent content review required')
        for rid, _ in matches:
            visit(rid)
        return [rid for rid, _ in matches]
    content_id = delivery['data']['input_content_id']
    reviews_for(content_id, 'content', independent=True)
    review_ids = reviews_for(delivery_id, 'delivery')
    files = [manifest_path, api.rooted(project, 'work/project.json'), api.rooted(project, 'work/index.json')]
    files += [api.rooted(project, index['artifacts'][aid]['path']) for aid in sorted(bound_ids)]
    data = delivery['data']
    files += [api.rooted(project, data[field]) for field in ('pptx_path', 'pdf_path', 'render_evidence_path')]
    render = api.read_json(api.rooted(project, data['render_evidence_path']))
    files += [api.rooted(project, p['image_path']) for p in render['pages']]
    binding = {'project_path': str(project), 'project_id': config['project_id'],
               'delivery_id': delivery_id, 'delivery_sha256': index['artifacts'][delivery_id]['sha256'],
               'content_id': content_id, 'content_sha256': index['artifacts'][content_id]['sha256'],
               'review_ids': review_ids, 'purpose': config['purpose'], 'business_approval': 'unconfirmed',
               'files': [{'file_path': str(p), 'sha256': digest(p)} for p in dict.fromkeys(files)]}
    return run_manage(db, {'request_id': request_id, 'opportunity_id': oid,
        'expected_revision': expected_revision, 'actor': actor, 'operations': [{
            'type': 'register_artifact', 'artifact_id': artifact_id, 'document_id': document_id,
            'kind': 'solution', 'version': version,
            'file_path': str(api.rooted(project, data['pptx_path'])), 'evidence': list(evidence),
            'metadata': {'source_skill': 'presales-orchestrator', 'presales_binding': binding,
                         'presales_call': call}}]})
