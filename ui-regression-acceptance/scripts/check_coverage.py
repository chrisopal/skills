#!/usr/bin/env python3
"""Audit a UI acceptance ledger, not the truth of browser evidence. Stdlib only."""
import json
import sys
from collections import Counter
from pathlib import Path


def audit(data, base):
    errors = []
    if not isinstance(data, dict):
        return {'verdict': 'INCOMPLETE', 'errors': ['ledger must be an object']}
    for key in ('scope', 'environment'):
        if not isinstance(data.get(key), str) or not data[key].strip():
            errors.append(f'{key}: nonempty string required')
    pages = data.get('pages', [])
    controls = data.get('controls', [])
    results = data.get('results', [])
    if any(not isinstance(items, list) or any(not isinstance(x, dict) for x in items)
           for items in (pages, controls, results)):
        return {'verdict': 'INCOMPLETE', 'errors': ['pages/controls/results must be arrays of objects']}
    page_ids, control_ids, required, seen = set(), set(), set(), set()
    for page in pages:
        pid = page.get('id')
        if not isinstance(pid, str) or not pid or pid in page_ids:
            errors.append('invalid or duplicate page ID')
            continue
        page_ids.add(pid)
        if page.get('inventoryComplete') is not True:
            errors.append(f'{pid}: inventory incomplete')
    for control in controls:
        cid = control.get('id')
        if not isinstance(cid, str) or not cid or cid in control_ids:
            errors.append('invalid or duplicate control ID')
            continue
        control_ids.add(cid)
        if control.get('page') not in page_ids:
            errors.append(f'{cid}: unknown page')
        checks = control.get('checks')
        if not isinstance(checks, list) or not checks or any(not isinstance(c, str) or not c for c in checks):
            errors.append(f'{cid}: nonempty checks required')
            continue
        if len(checks) != len(set(checks)):
            errors.append(f'{cid}: duplicate checks')
        required.update((cid, check) for check in checks)
    for page in pages:
        if not any(c.get('page') == page.get('id') for c in controls) and not page.get('noControlsReason'):
            errors.append(f"{page.get('id')}: page has no control inventory or explicit reason")
    counts = Counter()
    allowed = {'PASS', 'FAIL', 'BLOCKED', 'NOT_RUN', 'UNCONFIRMED', 'N/A'}
    for item in results:
        cid, check, status = item.get('control'), item.get('check'), item.get('status')
        if not isinstance(cid, str) or not isinstance(check, str):
            errors.append('invalid result control/check')
            continue
        pair = cid, check
        if pair not in required or pair in seen:
            errors.append(f'{pair}: unexpected or duplicate result')
            continue
        seen.add(pair)
        if not isinstance(status, str) or status not in allowed:
            errors.append(f'{pair}: unknown status')
            continue
        counts[status] += 1
        if status in {'PASS', 'FAIL'}:
            if not isinstance(item.get('steps'), list) or not item['steps'] or any(not isinstance(s, str) or not s.strip() for s in item['steps']):
                errors.append(f'{pair}: actual steps required')
            for field in ('expected', 'actual'):
                if not isinstance(item.get(field), str) or not item[field].strip():
                    errors.append(f'{pair}: {field} required')
            evidence = item.get('evidence')
            if not isinstance(evidence, list) or not evidence:
                errors.append(f'{pair}: evidence required')
            else:
                for ref in evidence:
                    if not isinstance(ref, str) or not ref:
                        errors.append(f'{pair}: invalid evidence path')
                        continue
                    path = base / ref
                    if not path.is_file() or path.stat().st_size == 0:
                        errors.append(f'{pair}: missing/empty evidence {ref}')
        elif not isinstance(item.get('reason'), str) or not item['reason'].strip():
            errors.append(f'{pair}: reason required')
    for pair in sorted(required - seen):
        errors.append(f'{pair}: missing result')
    if not pages or not required:
        errors.append('empty inventory cannot pass')
    applicable = len(required) - counts['N/A']
    if applicable == 0:
        errors.append('no applicable checks executed')
    incomplete = bool(errors or any(counts[s] for s in ('BLOCKED', 'NOT_RUN', 'UNCONFIRMED')))
    return {'verdict': 'FAIL' if counts['FAIL'] else 'INCOMPLETE' if incomplete else 'PASS',
            'pages': len(page_ids), 'controls': len(control_ids), 'assignedChecks': len(required),
            'counts': dict(counts), 'executionCoverage': round((counts['PASS'] + counts['FAIL']) / applicable, 4) if applicable else 0,
            'errors': errors, 'notice': 'Ledger audit only; inspect real browser evidence separately.'}


def main():
    try:
        path = Path(sys.argv[1]).resolve()
        result = audit(json.loads(path.read_text()), path.parent)
    except (IndexError, OSError, ValueError) as error:
        print(json.dumps({'verdict': 'INCOMPLETE', 'errors': [str(error)]}))
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result['verdict'] == 'PASS' else 1


if __name__ == '__main__':
    sys.exit(main())
