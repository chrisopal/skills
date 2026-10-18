#!/usr/bin/env python3
"""Audit schema-v3 ledgers against frozen scope; cannot prove browser truth."""
import argparse
import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path, PureWindowsPath


DIMENSIONS = ('business', 'interaction', 'display', 'layout')
STATUSES = {'PASS', 'FAIL', 'BLOCKED', 'NOT_RUN', 'UNCONFIRMED', 'N/A'}


def nonempty(value):
    return isinstance(value, str) and bool(value.strip())


def string_list(value):
    return isinstance(value, list) and bool(value) and all(nonempty(x) for x in value)


def digest(value):
    return isinstance(value, str) and re.fullmatch(r'[0-9a-fA-F]{64}', value) is not None


def evidence_errors(refs, base, label, errors):
    if not isinstance(refs, list) or not refs:
        errors.append(f'{label}: nonempty evidence list required')
        return
    for ref in refs:
        if not isinstance(ref, dict) or not nonempty(ref.get('path')) or not digest(ref.get('sha256')):
            errors.append(f'{label}: evidence needs path and sha256')
            continue
        name = ref['path']
        path = Path(name)
        windows = PureWindowsPath(name)
        if path.is_absolute() or windows.is_absolute() or windows.drive or '..' in path.parts or '..' in windows.parts:
            errors.append(f'{label}: unsafe evidence path {name}')
            continue
        try:
            resolved = (base / path).resolve()
            if not resolved.is_relative_to(base):
                errors.append(f'{label}: evidence escapes ledger directory {name}')
            elif not resolved.is_file() or resolved.stat().st_size == 0:
                errors.append(f'{label}: missing/empty evidence {name}')
            elif hashlib.sha256(resolved.read_bytes()).hexdigest() != ref['sha256'].lower():
                errors.append(f'{label}: evidence hash mismatch {name}')
        except (OSError, ValueError, RuntimeError) as error:
            errors.append(f'{label}: unreadable evidence {name}: {error}')


def object_array(data, key, errors):
    value = data.get(key)
    if not isinstance(value, list) or any(not isinstance(item, dict) for item in value):
        errors.append(f'{key}: array of objects required')
        return []
    return value


def inventory(pages, controls, errors):
    page_ids, control_ids, required = set(), set(), set()
    for page in pages:
        pid = page.get('id')
        if not nonempty(pid) or pid in page_ids:
            errors.append('invalid or duplicate page ID')
            continue
        page_ids.add(pid)
        if not nonempty(page.get('url')):
            errors.append(f'{pid}: page URL required')
        if page.get('inventoryComplete') is not True:
            errors.append(f'{pid}: inventory incomplete')
        if not string_list(page.get('sourceRefs')):
            errors.append(f'{pid}: inventory sourceRefs required')
    for control in controls:
        cid = control.get('id')
        if not nonempty(cid) or cid in control_ids:
            errors.append('invalid or duplicate control ID')
            continue
        control_ids.add(cid)
        if not nonempty(control.get('page')) or control['page'] not in page_ids:
            errors.append(f'{cid}: unknown page')
        for field in ('name', 'locator', 'kind'):
            if not nonempty(control.get(field)):
                errors.append(f'{cid}: {field} required')
        if not string_list(control.get('sourceRefs')):
            errors.append(f'{cid}: inventory sourceRefs required')
        checks = control.get('checks')
        if not string_list(checks):
            errors.append(f'{cid}: nonempty checks required')
            continue
        if len(checks) != len(set(checks)):
            errors.append(f'{cid}: duplicate checks')
        required.update((cid, check) for check in checks)
        dimensions = control.get('dimensions')
        if not isinstance(dimensions, dict):
            dimensions = {}
        if set(dimensions) != set(DIMENSIONS):
            errors.append(f'{cid}: dimensions must contain business/interaction/display/layout')
        assigned = set()
        for dimension in DIMENSIONS:
            items = dimensions.get(dimension)
            if not string_list(items):
                errors.append(f'{cid}: {dimension} needs check IDs')
            else:
                if assigned.intersection(items) or len(items) != len(set(items)):
                    errors.append(f'{cid}: dimension checks must be distinct; separate assertions may share evidence')
                assigned.update(items)
        if assigned != set(checks):
            errors.append(f'{cid}: dimensions must assign all and only declared checks')
        na = control.get('notApplicable', {})
        if not isinstance(na, dict) or any(key not in checks or not nonempty(reason) for key, reason in na.items()):
            errors.append(f'{cid}: invalid notApplicable checks/reasons')
    for page in pages:
        # Static pages also require cross-control/whole-page layout acceptance.
        layouts = []
        for control in controls:
            dims, na = control.get('dimensions'), control.get('notApplicable', {})
            if (control.get('page') == page.get('id') and control.get('kind') == 'page'
                    and isinstance(dims, dict) and isinstance(na, dict)):
                items = dims.get('layout')
                if string_list(items):
                    layouts.extend(check for check in items if check not in na)
        if not layouts:
            errors.append(f"{page.get('id')}: applicable page-wide layout check required (kind=page)")
    if not pages or not required:
        errors.append('empty inventory cannot pass')
    return required


def scope_errors(data, scope_path, errors):
    """Validate the independent inventory before comparing actual result coverage."""
    if scope_path is None:
        errors.append('scope: frozen manifest required via --scope')
        return None
    try:
        path = Path(scope_path).resolve()
        raw = path.read_bytes()
        scope = json.loads(raw)
    except (OSError, ValueError, RuntimeError) as error:
        errors.append(f'scope: cannot read manifest: {error}')
        return None
    if not isinstance(scope, dict):
        errors.append('scope: manifest must be an object')
        return None
    if data.get('scopeFingerprint') != hashlib.sha256(raw).hexdigest():
        errors.append('scopeFingerprint: must match frozen manifest bytes')
    if type(scope.get('schemaVersion')) is not int or scope['schemaVersion'] != 1:
        errors.append('scope.schemaVersion: 1 required')
    if not nonempty(scope.get('scope')) or scope['scope'] != data.get('scope'):
        errors.append('scope: declared scope differs from manifest')
    expected_build = scope.get('build')
    actual_build = data.get('build')
    expected_build = expected_build if isinstance(expected_build, dict) else {}
    actual_build = actual_build if isinstance(actual_build, dict) else {}
    for field in ('fingerprint', 'runtimeId'):
        valid = digest(expected_build.get(field)) if field == 'fingerprint' else nonempty(expected_build.get(field))
        if not valid or expected_build.get(field) != actual_build.get(field):
            errors.append(f'scope.build.{field}: missing or mismatched target version')
    discovery = scope.get('discovery')
    discovery = discovery if isinstance(discovery, dict) else {}
    if discovery.get('reconciled') is not True:
        errors.append('scope.discovery: source/runtime inventory must be reconciled')
    if not string_list(discovery.get('sourceRefs')):
        errors.append('scope.discovery.sourceRefs required')
    evidence_errors(discovery.get('runtimeEvidence'), path.parent, 'scope runtime inventory', errors)
    pages = object_array(scope, 'pages', errors)
    controls = object_array(scope, 'controls', errors)
    inventory(pages, controls, errors)
    for key, fields in (
        ('pages', ('id', 'url', 'sourceRefs', 'inventoryComplete')),
        ('controls', ('id', 'page', 'name', 'locator', 'kind', 'sourceRefs', 'checks', 'dimensions', 'notApplicable')),
    ):
        def keyed(items):
            return {item['id']: {f: item.get(f, {} if f == 'notApplicable' else None) for f in fields}
                    for item in items if nonempty(item.get('id'))}
        if keyed(object_array(data, key, errors)) != keyed(pages if key == 'pages' else controls):
            errors.append(f'scope: {key} differ from frozen manifest (omitted, added or changed entries)')
    return scope


def audit(data, base, scope_path=None):
    errors = []
    if not isinstance(data, dict):
        return {'verdict': 'INCOMPLETE', 'errors': ['ledger must be an object']}
    base = Path(base).resolve()
    if type(data.get('schemaVersion')) is not int or data['schemaVersion'] != 3:
        errors.append('schemaVersion: 3 required; legacy ledgers must be re-audited')
    if not nonempty(data.get('scope')):
        errors.append('scope: nonempty string required')
    environment = data.get('environment')
    environment = environment if isinstance(environment, dict) else {}
    for field in ('url', 'browser', 'role', 'theme'):
        if not nonempty(environment.get(field)):
            errors.append(f'environment.{field}: nonempty string required')
    viewport = environment.get('viewport')
    viewport = viewport if isinstance(viewport, dict) else {}
    for field in ('width', 'height'):
        if type(viewport.get(field)) is not int or viewport[field] <= 0:
            errors.append(f'environment.viewport.{field}: positive integer required')
    build = data.get('build')
    build = build if isinstance(build, dict) else {}
    if not digest(build.get('fingerprint')):
        errors.append('build.fingerprint: SHA-256 required')
    if not nonempty(build.get('runtimeId')):
        errors.append('build.runtimeId: observed running application version required')
    evidence_errors(build.get('runtimeEvidence'), base, 'build runtime evidence', errors)
    replay = data.get('replay')
    replay = replay if isinstance(replay, dict) else {}
    for field in ('command', 'prerequisites'):
        if not nonempty(replay.get(field)):
            errors.append(f'replay.{field} required')
    for field in ('scripts', 'logs'):
        evidence_errors(replay.get(field), base, f'replay.{field}', errors)
    pages = object_array(data, 'pages', errors)
    controls = object_array(data, 'controls', errors)
    results = object_array(data, 'results', errors)
    required = inventory(pages, controls, errors)
    scope = scope_errors(data, scope_path, errors)
    # Applicability and denominator come from expected scope, never the result list.
    expected_controls = object_array(scope, 'controls', errors) if scope is not None else controls
    expected_required = {(c['id'], check) for c in expected_controls if nonempty(c.get('id'))
                         and string_list(c.get('checks')) for check in c['checks']}
    declared_na = {(c['id'], check): reason for c in expected_controls if nonempty(c.get('id'))
                   and isinstance(c.get('notApplicable', {}), dict)
                   for check, reason in c.get('notApplicable', {}).items()}
    seen, executed = set(), set()
    recorded_statuses = {}
    failed = {(r['control'], r['check']) for r in results if nonempty(r.get('control'))
              and nonempty(r.get('check')) and r.get('status') == 'FAIL'
              and (r['control'], r['check']) in required | expected_required}
    for item in results:
        cid, check, status = item.get('control'), item.get('check'), item.get('status')
        if not nonempty(cid) or not nonempty(check):
            errors.append('invalid result control/check')
            continue
        pair = cid, check
        if pair not in required or pair in seen:
            errors.append(f'{pair}: unexpected or duplicate result')
            continue
        seen.add(pair)
        if not isinstance(status, str) or status not in STATUSES:
            errors.append(f'{pair}: unknown status')
            continue
        recorded_statuses[pair] = status
        if status in ('PASS', 'FAIL') and pair in expected_required and pair not in declared_na:
            executed.add(pair)
        if not nonempty(item.get('preconditions')):
            errors.append(f'{pair}: preconditions required')
        empty_refs_allowed = ((status == 'N/A' and nonempty(item.get('reason')))
                              or (status == 'BLOCKED' and string_list(item.get('missingContracts'))))
        if not string_list(item.get('contractRefs')) and not (empty_refs_allowed and item.get('contractRefs') in (None, [])):
            errors.append(f'{pair}: contractRefs required')
        if (status == 'N/A') != (pair in declared_na):
            errors.append(f'{pair}: applicability differs from frozen scope')
        elif status == 'N/A' and item.get('reason') != declared_na[pair]:
            errors.append(f'{pair}: N/A reason differs from frozen scope')
        if status in {'PASS', 'FAIL'}:
            if not string_list(item.get('steps')):
                errors.append(f'{pair}: actual steps required')
            for field in ('expected', 'actual'):
                if not nonempty(item.get(field)):
                    errors.append(f'{pair}: {field} required')
            evidence_errors(item.get('evidence'), base, str(pair), errors)
        else:
            if not nonempty(item.get('reason')):
                errors.append(f'{pair}: reason required')
            if 'evidence' in item and item['evidence'] != []:
                evidence_errors(item['evidence'], base, str(pair), errors)
        if 'previousFailures' in item:
            evidence_errors(item['previousFailures'], base, f'{pair} previousFailures', errors)
    for pair in sorted((required | expected_required) - seen):
        errors.append(f'{pair}: missing result')
    # Malformed duplicates must not suppress a known failure by list order.
    recorded_statuses.update({pair: 'FAIL' for pair in failed})
    counts = Counter(recorded_statuses.values())
    executed.update(failed.intersection(expected_required) - declared_na.keys())
    applicable = len(expected_required - declared_na.keys())
    if applicable <= 0:
        errors.append('no applicable checks executed')
    incomplete = bool(errors or any(counts[s] for s in ('BLOCKED', 'NOT_RUN', 'UNCONFIRMED')))
    return {'verdict': 'FAIL' if counts['FAIL'] else 'INCOMPLETE' if incomplete else 'PASS',
            'pages': len(pages), 'controls': len(controls), 'assignedChecks': len(expected_required),
            'expectedPages': len(scope['pages']) if scope is not None and isinstance(scope.get('pages'), list) else None,
            'expectedControls': len(expected_controls) if scope is not None else None,
            'applicableChecks': applicable, 'counts': dict(counts),
            'executionCoverage': round(len(executed) / applicable, 4) if applicable > 0 else 0,
            'errors': errors, 'notice': 'Ledger audit only; inspect real browser evidence separately.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('ledger', type=Path)
    parser.add_argument('--scope', type=Path, help='independently frozen scope manifest')
    args = parser.parse_args()
    try:
        path = args.ledger.resolve()
        result = audit(json.loads(path.read_text()), path.parent, args.scope)
    except (OSError, ValueError, RuntimeError) as error:
        print(json.dumps({'verdict': 'INCOMPLETE', 'errors': [str(error)]}))
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result['verdict'] == 'PASS' else 1


if __name__ == '__main__':
    sys.exit(main())
