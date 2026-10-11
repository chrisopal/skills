#!/usr/bin/env python3
"""Local, single-writer delivery records. Does not run an Agent or authenticate approvals."""
import argparse
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sys
import tempfile

KINDS = {'source', 'evidence', 'contract', 'kickoff', 'discovery', 'minutes',
         'requirements', 'blueprint', 'plan', 'timesheets', 'costs', 'risks',
         'change', 'weekly', 'milestone', 'confirmation', 'review'}
PUBLIC_KINDS = {'kickoff', 'discovery', 'minutes', 'requirements', 'blueprint',
                'plan', 'weekly', 'milestone'}
CUSTOMER_FORBIDDEN_KEYS = frozenset({'internal_rate', 'salary', 'margin', 'internal_notes', 'secret', 'access_token', 'password'})
SINGLETON = {'requirements', 'blueprint', 'plan', 'timesheets', 'costs', 'risks'}
PROJECT_DIRECTORIES = (
    '01-contract-handover', '02-initiation', '03-plan', '04-discovery',
    '05-requirements-blueprint', '06-design', '07-development-integration',
    '08-quality-uat', '09-go-live-handover', '10-project-control',
    '11-milestone-acceptance', '12-closure-warranty', 'internal-finance',
    'customer-deliverables', 'archive',
)
REFERENCE_KEYS = {'target', 'targets', 'deliverable_refs', 'baseline_refs',
                  'replacements', 'decision_refs', 'evidence_refs', 'source_refs'}
REQUIRED = {
    'evidence': ('items', 'unread_scope'),
    'contract': ('obligations', 'scope_in', 'scope_out', 'customer_dependencies'),
    'kickoff': ('goals', 'roles', 'milestones', 'customer_actions', 'open_items'),
    'discovery': ('sessions',),
    'minutes': ('meeting_date', 'participants', 'decisions', 'actions', 'open_items'),
    'requirements': ('items', 'open_items'),
    'blueprint': ('processes', 'pages', 'fields', 'interfaces', 'acceptance_scenarios', 'coverage', 'open_items'),
    'plan': ('work_packages', 'milestones'),
    'timesheets': ('items', 'remaining_labor'),
    'costs': ('currency', 'budget', 'items', 'other_remaining'),
    'risks': ('items',),
    'change': ('state', 'reason', 'affected_ids', 'baseline_refs', 'replacements', 'decision_refs', 'impact'),
    'weekly': ('period', 'as_of', 'completed', 'next', 'milestones', 'risks', 'decisions_required', 'coverage_gaps'),
    'milestone': ('milestone_id', 'scope', 'deliverable_refs', 'criteria', 'open_items'),
    'confirmation': ('target', 'state', 'actor', 'role', 'date', 'scope', 'evidence_refs', 'origin', 'open_items'),
    'review': ('targets', 'verdict', 'reviewer', 'method', 'findings', 'unchecked', 'scope'),
}


def now():
    return datetime.now(timezone.utc).isoformat()


def customer_fields(value, reject=False):
    """Shared recursive credential/internal field boundary; prose still needs review."""
    if isinstance(value, dict):
        if reject and CUSTOMER_FORBIDDEN_KEYS & {str(k).lower() for k in value}:
            raise ValueError('Internal/credential field in customer content')
        return {k: customer_fields(v, reject) for k, v in value.items()
                if str(k).lower() not in CUSTOMER_FORBIDDEN_KEYS}
    if isinstance(value, list):
        return [customer_fields(v, reject) for v in value]
    return value


def cost_reference(item):
    refs = {str(item[key]).strip() for key in ('external_ref', 'travel_or_expense_ref', 'procurement_ref') if item.get(key)}
    if len(refs) > 1:
        raise ValueError('Conflicting logical cost references; use one aggregate stable item')
    return next(iter(refs), item['id'])


def identifier(value):
    if not isinstance(value, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,79}', value):
        raise ValueError('IDs must be 1-80 ASCII letters, numbers, underscores or hyphens')
    return value


def root_path(project):
    root = Path(project).expanduser().resolve()
    if not root.is_dir():
        raise ValueError(f'Project not found: {root}')
    return root


def confined(project, relative):
    root = root_path(project)
    rel = Path(relative)
    if rel.is_absolute() or '..' in rel.parts:
        raise ValueError('Project-relative path required')
    path = root / rel
    for part in (path, *path.parents):
        if part == root:
            break
        if part.is_symlink():
            raise ValueError(f'Symlink project content is not supported: {part}')
    if not path.resolve().is_relative_to(root):
        raise ValueError('Path escapes project')
    return path


def project_path(project):
    return confined(project, '00-control/project.json')


def read_project(project):
    value = json.loads(project_path(project).read_text(encoding='utf-8'))
    identifier(value['project_id'])
    if value.get('purpose') not in {'internal', 'simulation'}:
        raise ValueError('Unknown project purpose')
    return value


def read_registry(project):
    value = json.loads(confined(project, '00-control/registry.json').read_text(encoding='utf-8'))
    if value['project_id'] != read_project(project)['project_id']:
        raise ValueError('Registry project mismatch')
    return value


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n').encode('utf-8')


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def atomic_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, prefix='.delivery-', delete=False) as stream:
        temp = Path(stream.name)
        stream.write(encoded(value))
        stream.flush()
        os.fsync(stream.fileno())
    try:
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)


def init_project(project, project_id, purpose='internal', currency='CNY'):
    identifier(project_id)
    if purpose not in {'internal', 'simulation'} or not re.fullmatch('[A-Z]{3}', currency):
        raise ValueError('Invalid purpose or currency')
    root = Path(project).expanduser().resolve()
    if root.exists() and (not root.is_dir() or any(root.iterdir())):
        raise ValueError('Initialization requires a new or empty directory')
    root.mkdir(parents=True, exist_ok=True)
    info = {'project_id': project_id, 'purpose': purpose, 'currency': currency, 'created_at': now()}
    atomic_json(project_path(root), info)
    atomic_json(confined(root, '00-control/registry.json'),
                {'project_id': project_id, 'version': 1, 'artifacts': {}, 'effective': {}, 'changes': {}})
    for directory in PROJECT_DIRECTORIES:
        (root / directory).mkdir()
    label = '模拟项目，不是客户证据' if purpose == 'simulation' else '内部项目工作区'
    (root / 'README.md').write_text(f'# {project_id}\n\n{label}。状态以运行工具回读为准。\n\n'
        '阶段目录保存可阅读成果；原件快照和版本登记在 00-control。后续阶段目录仅预留，不代表已实现或完成。\n'
        'internal-finance 保留内部工时、费率和成本；目录名不是权限控制。对客包仅从明确白名单生成，禁止打包项目根目录。\n', encoding='utf-8')
    return info


def ref_key(ref):
    ref = canonical_ref(ref)
    return (ref['artifact_id'], ref['revision'], ref['sha256'])


def canonical_ref(value):
    if not isinstance(value, dict):
        raise ValueError('Artifact reference must be an object')
    aid = identifier(value.get('artifact_id'))
    rev = value.get('revision')
    checksum = value.get('sha256')
    if isinstance(rev, bool) or not isinstance(rev, int) or rev < 1:
        raise ValueError('Reference revision must be a positive integer')
    if not isinstance(checksum, str) or not re.fullmatch('[0-9a-f]{64}', checksum):
        raise ValueError('Reference requires a complete SHA-256')
    return {'artifact_id': aid, 'revision': rev, 'sha256': checksum}


def artifact_path(project, ref):
    ref = canonical_ref(ref)
    return confined(project, f"00-control/artifacts/{ref['artifact_id']}/r{ref['revision']:06d}.json")


def latest_ref(project, aid):
    identifier(aid)
    entry = read_registry(project)['artifacts'].get(aid)
    if entry is None:
        raise ValueError(f'Unknown artifact: {aid}')
    return canonical_ref(dict(entry, artifact_id=aid))


def load_artifact(project, ref):
    ref = canonical_ref(ref)
    registry = read_registry(project)
    entry = registry['artifacts'].get(ref['artifact_id'])
    if not entry or ref['revision'] > entry['revision']:
        raise ValueError(f'Unregistered revision: {ref["artifact_id"]}')
    path = artifact_path(project, ref)
    if not path.is_file() or digest(path) != ref['sha256']:
        raise ValueError(f'Artifact missing or changed: {ref["artifact_id"]} r{ref["revision"]}')
    result = json.loads(path.read_text(encoding='utf-8'))
    if (result['project_id'] != registry['project_id'] or result['artifact_id'] != ref['artifact_id']
            or result['revision'] != ref['revision']):
        raise ValueError('Artifact identity mismatch')
    if result['kind'] == 'source':
        source_path = confined(project, result['data']['path'])
        if not source_path.is_file() or digest(source_path) != result['data']['sha256']:
            raise ValueError(f'Source snapshot missing or changed: {ref["artifact_id"]}')
    return result


def check_ref(project, ref, selection=None, seen=None):
    """Check exact pinned content; selection additionally checks dependency freshness."""
    seen = set() if seen is None else seen
    key = ref_key(ref)
    if key in seen:
        raise ValueError('Circular artifact dependency')
    value = load_artifact(project, ref)
    seen = seen | {key}
    exempt = {ref_key(x) for x in value['data'].get('baseline_refs', [])} if value['kind'] == 'change' else set()
    for dep in value['inputs']:
        current = selection.get(dep['artifact_id']) if selection is not None else None
        if current is not None and ref_key(dep) != ref_key(current) and ref_key(dep) not in exempt:
            raise ValueError(f'Stale dependency: {value["artifact_id"]} → {dep["artifact_id"]}')
        check_ref(project, dep, None if ref_key(dep) in exempt else selection, seen)
    return value


def number(value, label, unknown=False):
    if value is None and unknown:
        return None
    if isinstance(value, bool):
        raise ValueError(f'{label} must be numeric')
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise ValueError(f'{label} must be numeric') from None
    if not result.is_finite() or result < 0:
        raise ValueError(f'{label} must be finite and nonnegative')
    return result


def rows(data, key, required=()):
    items = data.get(key)
    if not isinstance(items, list):
        raise ValueError(f'{key} must be a list')
    ids = set()
    for item in items:
        if not isinstance(item, dict) or any(k not in item for k in ('id', *required)):
            raise ValueError(f'{key} item requires id and {required}')
        if not isinstance(item['id'], str) or not item['id'] or item['id'] in ids:
            raise ValueError(f'Duplicate/invalid item ID in {key}')
        ids.add(item['id'])
    return items


def walk_refs(value, key=None):
    if isinstance(value, dict):
        if key in REFERENCE_KEYS and 'artifact_id' in value:
            yield canonical_ref(value)
        else:
            for name, child in value.items():
                yield from walk_refs(child, name)
    elif isinstance(value, list):
        for child in value:
            yield from walk_refs(child, key)


def validate_payload(project, value, registry):
    if not isinstance(value, dict) or value.get('project_id') != registry['project_id']:
        raise ValueError('Artifact project_id must match project')
    identifier(value.get('artifact_id'))
    rev = value.get('revision')
    if isinstance(rev, bool) or not isinstance(rev, int) or rev < 1:
        raise ValueError('revision must be a positive integer')
    kind = value.get('kind')
    if kind not in KINDS or value.get('visibility') not in {'internal', 'customer'}:
        raise ValueError('Unknown kind or visibility')
    if value.get('status') not in {'draft', 'ready', 'blocked'}:
        raise ValueError('Unknown artifact status')
    data = value.get('data')
    if not isinstance(data, dict) or any(k not in data for k in REQUIRED.get(kind, ())):
        raise ValueError(f'Missing {kind} data fields: {REQUIRED.get(kind, ())}')
    if kind != 'source' and value['status'] == 'ready' and re.search(r'\{\{[^}]+\}\}', json.dumps(data)):
        raise ValueError('Ready artifact contains template placeholders')
    if not isinstance(value.get('inputs'), list):
        raise ValueError('inputs must be a list of exact artifact references')
    closure = set()

    def collect(ref):
        item = check_ref(project, ref)
        closure.add(ref_key(ref))
        for child in item['inputs']:
            if ref_key(child) not in closure:
                collect(child)

    for ref in value['inputs']:
        if ref['artifact_id'] == value['artifact_id']:
            raise ValueError('Artifact cannot depend on its own revisions')
        collect(ref)
    for ref in walk_refs(data):
        if ref_key(ref) not in closure:
            raise ValueError(f'Business reference is not bound in inputs: {ref["artifact_id"]}')
    if kind in SINGLETON:
        for aid, entry in registry['artifacts'].items():
            if aid != value['artifact_id'] and entry['kind'] == kind:
                raise ValueError(f'{kind} already has a master ledger: {aid}')
    if kind == 'requirements':
        rows(data, 'items', ('statement', 'source_refs', 'acceptance', 'priority'))
        if value['status'] == 'ready' and not data['items']:
            raise ValueError('Ready requirements need actual items')
    elif kind == 'evidence':
        rows(data, 'items', ('source_id', 'locator', 'content', 'read_status'))
    elif kind == 'contract':
        rows(data, 'obligations', ('statement', 'source_id', 'locator', 'acceptance'))
    elif kind == 'discovery':
        rows(data, 'sessions', ('customer_role', 'date', 'topic', 'questions', 'customer_inputs', 'expected_outputs', 'owner', 'status'))
    elif kind == 'plan':
        packages = rows(data, 'work_packages', ('title', 'owner', 'baseline_start', 'baseline_finish', 'forecast_finish', 'dependencies', 'requirement_ids', 'completion_rule', 'status'))
        ids = {x['id'] for x in packages}
        graph = {x['id']: x['dependencies'] for x in packages}
        if any(not isinstance(ds, list) or any(d not in ids for d in ds) for ds in graph.values()):
            raise ValueError('Plan dependency is missing from work packages')
        def visit(aid, stack):
            if aid in stack:
                raise ValueError('Circular work-package dependency')
            for dep in graph[aid]:
                visit(dep, stack | {aid})
        for aid in graph:
            visit(aid, set())
    elif kind == 'blueprint':
        all_ids = set()
        for group in ('processes', 'pages', 'fields', 'interfaces', 'acceptance_scenarios'):
            items = rows(data, group)
            if value['status'] == 'ready' and not items and not data.get('not_applicable', {}).get(group):
                raise ValueError(f'Blueprint {group} is empty without an applicability reason')
            for item in items:
                if item['id'] in all_ids:
                    raise ValueError('Blueprint object IDs must be unique')
                all_ids.add(item['id'])
        reqs = set()
        for key in closure:
            upstream = load_artifact(project, dict(zip(('artifact_id', 'revision', 'sha256'), key)))
            if upstream['kind'] == 'requirements':
                reqs.update(x['id'] for x in upstream['data']['items'])
        covered = set()
        for row in data['coverage']:
            if row.get('requirement_id') not in reqs or not row.get('design_ids') or not set(row['design_ids']) <= all_ids:
                raise ValueError('Invalid requirement/design coverage mapping')
            covered.add(row['requirement_id'])
        expected = set(data.get('scope_requirement_ids', reqs))
        if value['status'] == 'ready' and (not reqs or not expected <= covered):
            raise ValueError('Blueprint requirement coverage is incomplete')
    elif kind == 'timesheets':
        daily = {}
        for item in rows(data, 'items', ('person', 'date', 'work_package_id', 'hours', 'rate', 'resource_type', 'status')):
            hours = number(item['hours'], 'hours', True)
            number(item['rate'], 'rate', True)
            if item['resource_type'] not in {'internal', 'outsourced'} or item['status'] not in {'submitted', 'approved'}:
                raise ValueError('Unknown timesheet resource_type/status')
            key = item['person'], item['date']
            daily[key] = daily.get(key, Decimal(0)) + (hours or Decimal(0))
            if daily[key] > 24:
                raise ValueError('Daily hours exceed 24 for one person')
        number(data['remaining_labor'], 'remaining_labor', True)
    elif kind == 'costs':
        if data['currency'] != read_project(project)['currency']:
            raise ValueError('Cost currency must match project; convert with documented basis first')
        number(data['budget'], 'budget', True)
        number(data['other_remaining'], 'other_remaining', True)
        external = set()
        prior_ref = registry['artifacts'].get(value['artifact_id'])
        prior_items = load_artifact(project, prior_ref)['data']['items'] if prior_ref else []
        prior_owners = {cost_reference(item): item['id'] for item in prior_items}
        prior_by_id = {item['id']: item for item in prior_items}
        if not set(prior_by_id) <= {item['id'] for item in data['items']}:
            raise ValueError('Cost ledger cannot remove stable items; record an evidenced zero correction instead')
        for item in rows(data, 'items', ('category', 'work_package_id', 'state', 'amount', 'basis', 'payment_status')):
            number(item['amount'], 'amount', True)
            if item['category'] not in {'travel', 'purchase', 'outsourcing', 'other'} or item['state'] not in {'estimate', 'committed', 'incurred'}:
                raise ValueError('Costs use non-labor categories and estimate/committed/incurred states')
            ref = cost_reference(item)
            if item['id'] in prior_by_id and cost_reference(prior_by_id[item['id']]) != ref:
                raise ValueError('Stable cost item logical reference cannot change or be removed')
            if ref in external or (ref in prior_owners and prior_owners[ref] != item['id']):
                raise ValueError('Duplicate logical cost reference; revise one stable cost item')
            external.add(ref)
    elif kind == 'risks':
        for item in rows(data, 'items', ('type', 'title', 'owner', 'status', 'action', 'due', 'evidence_refs')):
            if item['type'] not in {'risk', 'issue', 'quality'} or item['status'] not in {'open', 'closed'}:
                raise ValueError('Unknown risk/issue/quality status')
            if item['status'] == 'closed' and not item['evidence_refs']:
                raise ValueError('Closing risk/issue/quality item requires evidence')
    elif kind == 'confirmation':
        if data['state'] not in {'accepted', 'conditional', 'rejected'} or data['origin'] not in {'actual', 'simulation'}:
            raise ValueError('Invalid confirmation state/origin')
        if data['origin'] == 'simulation' and read_project(project)['purpose'] != 'simulation':
            raise ValueError('Simulation confirmation is invalid for a real project')
        if any(not data[k] for k in ('actor', 'role', 'date', 'scope', 'evidence_refs')):
            raise ValueError('Confirmation needs actor, role, date, scope and actual evidence reference')
        if data['state'] == 'accepted' and data['open_items']:
            raise ValueError('Accepted confirmation cannot hide unresolved conditions; use conditional')
    elif kind == 'review':
        if data['verdict'] not in {'pass', 'conditional', 'fail'} or not data['targets'] or not data['reviewer'] or not data['scope']:
            raise ValueError('Review requires targets, verdict, reviewer and scope')
        for finding in data['findings']:
            if data['verdict'] == 'pass' and finding.get('severity') in {'major', 'blocking'} and finding.get('status') != 'closed':
                raise ValueError('Pass review has unresolved major/blocking findings')
            if finding.get('status') == 'closed' and not finding.get('resolution_evidence'):
                raise ValueError('Closed finding needs resolution evidence')
    elif kind == 'change':
        if data['state'] not in {'proposed', 'approved', 'rejected'}:
            raise ValueError('Invalid change state')
        if data['state'] == 'approved' and not data['decision_refs']:
            raise ValueError('Approved change needs decision evidence')


def register(project, value):
    if isinstance(value, (str, Path)):
        value = json.loads(Path(value).read_text(encoding='utf-8'))
    registry = read_registry(project)
    validate_payload(project, value, registry)
    aid = value['artifact_id']
    prior = registry['artifacts'].get(aid)
    payload = encoded(value)
    checksum = hashlib.sha256(payload).hexdigest()
    ref = {'artifact_id': aid, 'revision': value['revision'], 'sha256': checksum}
    if prior and value['revision'] == prior['revision'] and prior['sha256'] == checksum:
        load_artifact(project, ref)
        return ref
    if value['revision'] != (prior['revision'] + 1 if prior else 1):
        raise ValueError('Revision must increment by one; immutable revisions cannot be overwritten')
    if prior and prior['kind'] != value['kind']:
        raise ValueError('Artifact kind cannot change between revisions')
    path = artifact_path(project, ref)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() != payload:
            raise ValueError('Conflicting orphan artifact; preserve it for recovery')
    else:
        with path.open('xb') as stream:
            stream.write(payload)
    registry['artifacts'][aid] = dict(ref, kind=value['kind'])
    atomic_json(confined(project, '00-control/registry.json'), registry)
    load_artifact(project, ref)
    return ref


def source(project, file, aid):
    identifier(aid)
    original = Path(file).expanduser().resolve()
    if not original.is_file():
        raise ValueError('Source must be a readable regular file')
    registry = read_registry(project)
    prior = registry['artifacts'].get(aid)
    checksum = digest(original)
    if prior:
        oldref = canonical_ref(dict(prior, artifact_id=aid))
        old = load_artifact(project, oldref)
        if old['kind'] != 'source':
            raise ValueError('Source ID already belongs to another kind')
        if old['data']['sha256'] == checksum:
            return oldref
    rev = prior['revision'] + 1 if prior else 1
    suffix = original.suffix if re.fullmatch(r'\.[A-Za-z0-9]{1,10}', original.suffix) else '.bin'
    relative = f'00-control/sources/{aid}-r{rev:06d}{suffix}'
    destination = confined(project, relative)
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists() and digest(destination) != checksum:
        raise ValueError('Source snapshot already exists with different contents')
    if not destination.exists():
        with original.open('rb') as src, destination.open('xb') as dst:
            shutil.copyfileobj(src, dst)
    if digest(destination) != checksum:
        raise ValueError('Source changed during copy')
    return register(project, dict(project_id=registry['project_id'], artifact_id=aid, revision=rev,
                                  kind='source', visibility='internal', status='ready', inputs=[],
                                  data={'name': original.name, 'path': relative, 'sha256': checksum}))


def selection_for(project, registry, effective=False):
    selected = {aid: canonical_ref(dict(entry, artifact_id=aid)) for aid, entry in registry['artifacts'].items()}
    if effective:
        selected.update(registry['effective'])
    # Source updates always require downstream reassessment, even under an old baseline.
    return selected


def activate(project, artifact_ids):
    registry = read_registry(project)
    updated = dict(registry['effective'])
    for aid in artifact_ids:
        ref = latest_ref(project, aid)
        value = check_ref(project, ref)
        if value['status'] != 'ready' or value['kind'] in {'source', 'review', 'confirmation', 'change'}:
            raise ValueError('Only ready business artifacts can be activated')
        if aid in updated and ref_key(updated[aid]) != ref_key(ref):
            raise ValueError('Existing effective artifact must be revised through apply-change')
        updated[aid] = ref
    selected = selection_for(project, registry, True)
    selected.update(updated)
    for ref in updated.values():
        check_ref(project, ref, selected)
    registry['effective'] = updated
    atomic_json(confined(project, '00-control/registry.json'), registry)
    return updated


def apply_change(project, change_id):
    registry = read_registry(project)
    ref = latest_ref(project, change_id)
    key = f'{change_id}:{ref["revision"]}'
    if key in registry['changes']:
        receipt = registry['changes'][key]
        if receipt['change'] != ref:
            raise ValueError('Applied change content mismatch')
        for candidate in receipt['replacements']:
            check_ref(project, candidate)
        return receipt
    value = check_ref(project, ref)
    data = value['data']
    if value['kind'] != 'change' or value['status'] != 'ready' or data['state'] != 'approved' or not data['decision_refs']:
        raise ValueError('Change must be ready and approved with bound decision evidence')
    replacements = {x['artifact_id']: canonical_ref(x) for x in data['replacements']}
    if not replacements or set(replacements) != set(data['affected_ids']) or len(replacements) != len(data['replacements']):
        raise ValueError('Affected IDs and unique replacements must agree')
    baselines = {x['artifact_id']: canonical_ref(x) for x in data['baseline_refs']}
    existing = set(replacements) & set(registry['effective'])
    if set(baselines) != existing or any(baselines[aid] != registry['effective'][aid] for aid in existing):
        raise ValueError('Change baseline no longer matches effective objects')
    for candidate in replacements.values():
        obj = check_ref(project, candidate)
        if obj['status'] != 'ready' or obj['kind'] in {'source', 'review', 'confirmation', 'change'}:
            raise ValueError('Change replacements must be ready business objects')
        if candidate != latest_ref(project, candidate['artifact_id']):
            raise ValueError('Change replacement is no longer the latest candidate')
    updated = dict(registry['effective'], **replacements)
    selected = selection_for(project, registry, True)
    selected.update(updated)
    for candidate in updated.values():
        check_ref(project, candidate, selected)
    receipt = {'state': 'effective', 'change': ref, 'replacements': list(replacements.values()), 'applied_at': now()}
    registry['effective'] = updated
    registry['changes'][key] = receipt
    atomic_json(confined(project, '00-control/registry.json'), registry)
    return receipt


def validate(project):
    registry = read_registry(project)
    current_errors, effective_errors = [], []
    latest = selection_for(project, registry)
    for aid, ref in latest.items():
        try:
            check_ref(project, ref, latest)
        except (ValueError, OSError, KeyError, TypeError) as exc:
            current_errors.append(f'{aid}: {exc}')
    selected = selection_for(project, registry, True)
    for aid, ref in registry['effective'].items():
        try:
            check_ref(project, ref, selected)
        except (ValueError, OSError, KeyError, TypeError) as exc:
            effective_errors.append(f'{aid}: {exc}')
    return {'ok': not current_errors and not effective_errors, 'effective_ok': not effective_errors,
            'errors': current_errors, 'effective_errors': effective_errors,
            'artifacts': len(latest), 'effective': len(registry['effective'])}


def cost_summary(project):
    registry = read_registry(project)
    selected = selection_for(project, registry, True)
    # Financial observations are current facts; an approved budget remains pinned separately.
    for aid, entry in registry['artifacts'].items():
        if entry['kind'] in {'timesheets', 'costs'}:
            selected[aid] = canonical_ref(dict(entry, artifact_id=aid))
    data_by_kind = {}
    gaps = []
    for aid, ref in selected.items():
        if registry['artifacts'][aid]['kind'] in {'timesheets', 'costs'}:
            try:
                obj = check_ref(project, ref, selected)
                data_by_kind[obj['kind']] = obj['data']
                if obj['data'].get('evidence_status') == 'incomplete_business_evidence':
                    gaps.append(f'{aid}: business evidence incomplete; amounts are assumptions')
            except (ValueError, OSError, KeyError, TypeError):
                gaps.append(f'{aid}: financial source is stale or unreadable')
    labor = provisional = actual = committed = estimates = Decimal(0)
    hours = data_by_kind.get('timesheets')
    expenses = data_by_kind.get('costs')
    if not hours:
        gaps.append('Timesheet ledger missing')
    else:
        for item in hours['items']:
            if item['resource_type'] != 'internal':
                if not expenses or not any(cost['category'] == 'outsourcing' and cost['work_package_id'] == item['work_package_id']
                                           for cost in expenses['items']):
                    gaps.append(f'{item["id"]}: outsourced work has no cost estimate/settlement item')
                continue
            amount_hours = number(item['hours'], 'hours', True)
            rate = number(item['rate'], 'rate', True)
            if amount_hours is None or rate is None:
                gaps.append(f'{item["id"]}: hours/rate unknown')
                continue
            amount = amount_hours * rate
            labor += amount
            if item['status'] != 'approved':
                provisional += amount
                gaps.append(f'{item["id"]}: unapproved hours included provisionally')
        remaining = number(hours['remaining_labor'], 'remaining_labor', True)
        if remaining is None:
            gaps.append('Remaining labor estimate unknown')
        else:
            estimates += remaining
    budget = None
    if not expenses:
        gaps.append('Cost ledger missing')
    else:
        budget = number(expenses['budget'], 'budget', True)
        for aid, baseline in registry['effective'].items():
            if registry['artifacts'][aid]['kind'] == 'costs':
                try:
                    approved_budget = number(check_ref(project, baseline)['data']['budget'], 'budget', True)
                    if budget != approved_budget:
                        gaps.append('Proposed budget differs from approved baseline; approved budget used')
                    budget = approved_budget
                except (ValueError, OSError, KeyError, TypeError):
                    budget = None
                    gaps.append('Approved budget baseline unreadable')
        if budget is None:
            gaps.append('Budget unknown')
        for item in expenses['items']:
            amount = number(item['amount'], 'amount', True)
            if amount is None:
                gaps.append(f'{item["id"]}: expense amount unknown')
            elif item['state'] == 'incurred':
                actual += amount
            elif item['state'] == 'committed':
                committed += amount
            else:
                estimates += amount
        remaining = number(expenses['other_remaining'], 'other_remaining', True)
        if remaining is None:
            gaps.append('Other remaining estimate unknown')
        else:
            estimates += remaining
    forecast = labor + actual + committed + estimates
    money = lambda v: None if v is None else str(v.quantize(Decimal('0.01')))
    return dict(currency=read_project(project)['currency'], internal_labor=money(labor),
                provisional_labor=money(provisional), other_incurred=money(actual),
                committed_remaining=money(committed), estimated_remaining=money(estimates),
                forecast=money(forecast), budget=money(budget), variance=money(forecast-budget) if budget is not None else None,
                complete=not gaps, gaps=gaps)


def matching_records(project, target, kind):
    registry = read_registry(project)
    selected = selection_for(project, registry)
    matches = []
    for aid, entry in registry['artifacts'].items():
        if entry['kind'] != kind:
            continue
        try:
            record = check_ref(project, latest_ref(project, aid), selected)
        except (ValueError, OSError, KeyError, TypeError):
            continue
        targets = record['data'].get('targets', [record['data'].get('target')])
        if any(isinstance(x, dict) and ref_key(x) == ref_key(target) for x in targets):
            matches.append(record)
    return matches


def confirmed(project, target, blueprint=False):
    reasons = []
    records = matching_records(project, target, 'confirmation')
    if any(x['status'] == 'ready' and x['data']['state'] in {'conditional', 'rejected'} for x in records):
        reasons.append('Unresolved conditional/rejected confirmation for this version')
    accepted = [x for x in records if x['data']['state'] == 'accepted' and x['status'] == 'ready']
    if read_project(project)['purpose'] != 'simulation':
        accepted = [x for x in accepted if x['data']['origin'] == 'actual']
    if not accepted:
        reasons.append('Missing accepted confirmation for this exact version')
    if blueprint and accepted:
        required = {'processes', 'pages', 'fields', 'permissions', 'interfaces', 'data', 'acceptance'}
        if not any(required <= set(x['data']['scope']) for x in accepted):
            reasons.append('Implementation blueprint confirmation scope is incomplete')
    return {'ready': not reasons, 'reasons': reasons}


def snapshot(project):
    registry = read_registry(project)
    info = read_project(project)
    selected = selection_for(project, registry)
    artifacts = []
    alerts = []
    gates = {}
    for aid, ref in selected.items():
        try:
            obj = load_artifact(project, ref)
            try:
                check_ref(project, ref, selected)
                health = 'current'
            except (ValueError, OSError, KeyError, TypeError) as exc:
                health = 'stale'
                alerts.append(f'{aid}: {exc}')
            artifacts.append(dict(artifact_id=aid, revision=ref['revision'], kind=obj['kind'],
                                  visibility=obj['visibility'], status=obj['status'], health=health,
                                  path=artifact_path(project, ref).relative_to(root_path(project)).as_posix(),
                                  data=obj['data'], sha256=ref['sha256'],
                                  is_effective=registry['effective'].get(aid) == ref,
                                  effective_revision=registry['effective'].get(aid, {}).get('revision')))
            if obj['kind'] in {'blueprint', 'milestone'}:
                gate = confirmed(project, ref, obj['kind'] == 'blueprint')
                if health != 'current' or obj['status'] != 'ready':
                    gate = {'ready': False, 'reasons': gate['reasons'] + ['Artifact is stale or not ready']}
                gates[obj['kind']] = gate
        except (ValueError, OSError, KeyError, TypeError) as exc:
            alerts.append(f'{aid}: {exc}')
    for kind in ('blueprint', 'milestone'):
        gates.setdefault(kind, {'ready': False, 'reasons': [f'{kind} artifact missing']})
    validation = validate(project)
    alerts.extend(validation['effective_errors'])
    return dict(project_id=info['project_id'], purpose=info['purpose'], artifacts=artifacts,
                effective=registry['effective'], cost_summary=cost_summary(project),
                alerts=list(dict.fromkeys(alerts)), gates=gates)


def prepare_customer(project, artifact_ids, out, mode='discussion'):
    if mode not in {'discussion', 'confirmed'} or not artifact_ids:
        raise ValueError('Select artifacts and discussion/confirmed mode')
    info = read_project(project)
    registry = read_registry(project)
    selected = selection_for(project, registry)
    ready = []
    for aid in dict.fromkeys(artifact_ids):
        ref = latest_ref(project, aid)
        obj = check_ref(project, ref, selected)
        if obj['kind'] not in PUBLIC_KINDS or obj['visibility'] != 'customer' or obj['status'] != 'ready':
            raise ValueError(f'{aid}: not an eligible customer business artifact')
        reviews = matching_records(project, ref, 'review')
        if any(r['status'] == 'ready' and r['data']['verdict'] != 'pass' for r in reviews):
            raise ValueError(f'{aid}: unresolved fail/conditional review; revise that review after remediation')
        if not any(r['status'] == 'ready' and r['data']['verdict'] == 'pass'
                   and r['data']['method'].startswith('independent-') for r in reviews):
            raise ValueError(f'{aid}: missing current independent pass review')
        if mode == 'confirmed' and not confirmed(project, ref, obj['kind'] == 'blueprint')['ready']:
            raise ValueError(f'{aid}: customer confirmation missing/incomplete')
        customer_fields(obj['data'], reject=True)
        ready.append((ref, obj))
    destination = Path(out).expanduser().resolve()
    if destination.exists():
        raise ValueError('Customer package output already exists; choose a new directory')
    if destination.is_relative_to(root_path(project) / '00-control'):
        raise ValueError('Package cannot overwrite project control records')
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.delivery-pack-', dir=destination.parent) as staging:
        staging = Path(staging)
        files = []
        for ref, obj in ready:
            name = f'{ref["artifact_id"]}-r{ref["revision"]}.json'
            public = dict(project_id=info['project_id'], artifact_id=obj['artifact_id'], revision=obj['revision'],
                          kind=obj['kind'], purpose=info['purpose'], package_mode=mode, data=obj['data'])
            (staging / name).write_bytes(encoded(public))
            files.append(dict(name=name, sha256=digest(staging / name), source=ref))
        label = '模拟案例，不代表真实客户确认。' if info['purpose'] == 'simulation' else '本地准备包，未发送。'
        label += ' 讨论稿。' if mode == 'discussion' else ' 确认依据详见内部登记；本工具不认证签署者身份。'
        (staging / 'README.md').write_text(f'# {info["project_id"]}\n\n{label}\n', encoding='utf-8')
        manifest = dict(project_id=info['project_id'], purpose=info['purpose'], mode=mode, files=files,
                        sent=False, prepared_at=now())
        (staging / 'manifest.json').write_bytes(encoded(manifest))
        for file in files:
            if digest(staging / file['name']) != file['sha256']:
                raise ValueError('Package readback failed')
        staging.rename(destination)
    return dict(manifest, output=str(destination))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    init = sub.add_parser('init')
    init.add_argument('project', type=Path)
    init.add_argument('--project-id', required=True)
    init.add_argument('--purpose', choices=['internal', 'simulation'], default='internal')
    init.add_argument('--currency', default='CNY')
    src = sub.add_parser('source')
    src.add_argument('project', type=Path)
    src.add_argument('file', type=Path)
    src.add_argument('--id', required=True)
    reg = sub.add_parser('register')
    reg.add_argument('project', type=Path)
    reg.add_argument('file', type=Path)
    for command in ('status', 'validate'):
        sub.add_parser(command).add_argument('project', type=Path)
    act = sub.add_parser('activate')
    act.add_argument('project', type=Path)
    act.add_argument('ids', nargs='+')
    change = sub.add_parser('apply-change')
    change.add_argument('project', type=Path)
    change.add_argument('change_id')
    pack = sub.add_parser('prepare-customer')
    pack.add_argument('project', type=Path)
    pack.add_argument('--ids', nargs='+', required=True)
    pack.add_argument('--out', type=Path, required=True)
    pack.add_argument('--mode', choices=['discussion', 'confirmed'], default='discussion')
    args = parser.parse_args()
    try:
        if args.command == 'init':
            result = init_project(args.project, args.project_id, args.purpose, args.currency)
        elif args.command == 'source':
            result = source(args.project, args.file, args.id)
        elif args.command == 'register':
            result = register(args.project, args.file)
        elif args.command == 'status':
            result = snapshot(args.project)
        elif args.command == 'validate':
            result = validate(args.project)
        elif args.command == 'activate':
            result = activate(args.project, args.ids)
        elif args.command == 'apply-change':
            result = apply_change(args.project, args.change_id)
        else:
            result = prepare_customer(args.project, args.ids, args.out, args.mode)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1 if args.command == 'validate' and not result['ok'] else 0
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f'Delivery operation refused: {exc}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
