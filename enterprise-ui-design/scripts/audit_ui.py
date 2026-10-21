#!/usr/bin/env python3
"""Candidate style scan and evidence-led coverage gate (stdlib, not an AST or visual audit)."""
import argparse
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
STATUSES = {'Pass', 'Fail', 'Not tested', 'Not applicable'}
PATTERNS = {
    'literal-color': re.compile(r'#[0-9a-fA-F]{3,8}\b|rgba?\(|hsla?\('),
    'palette-consumption': re.compile(r'var\(--(?:blue|teal|purple|red)-\d+|(?:bg|text|border|ring)-(?:blue|teal|purple|red)-\d+'),
}


def scan(paths, baseline=()):
    """CSS/SCSS/module files, HTML styles and JS/TS style candidates only; no parsing claim."""
    candidates = []
    known = {(item['file'], item['kind'], item['source']) for item in baseline}
    for path in paths:
        if path.suffix not in {'.css', '.scss', '.html', '.js', '.jsx', '.ts', '.tsx'}:
            continue
        if path.name in {'tokens.css', 'design-config.js', 'design-system.js'}:
            continue  # definitions/generated registry/adapter are not business consumption
        if any(part in {'node_modules', 'vendor', 'third_party'} for part in path.parts):
            continue
        for line_number, line in enumerate(path.read_text().splitlines(), 1):
            # JS colors unrelated to styles are still candidates requiring human triage.
            for kind, pattern in PATTERNS.items():
                if pattern.search(line):
                    item = {'file': str(path), 'line': line_number, 'kind': kind, 'source': line.strip()}
                    item['origin'] = 'existing-debt' if (item['file'], kind, item['source']) in known else 'new-candidate'
                    candidates.append(item)
    return {'status': 'Candidates' if candidates else 'Pass', 'method': 'text candidates; manual triage required',
            'supported': ['CSS/SCSS/CSS Modules', 'HTML inline style candidates', 'JS/TS style-object candidates', 'Tailwind literal class candidates'],
            'not_supported': ['AST classification', 'computed/template class strings', 'Sass evaluation', 'third-party internals', 'whole-site usability'],
            'candidates': candidates}


def coverage(manifest, report):
    errors = []
    expected = {(surface['id'], state) for surface in manifest['surfaces'] for state in surface['states']}
    evidence = {}
    for row in report.get('coverage', []):
        key = (row.get('surface'), row.get('state'))
        if key not in expected:
            errors.append(f'{key}: unknown surface/state')
        if key in evidence:
            errors.append(f'{key}: duplicate coverage; preserve and reconcile observations explicitly')
        else:
            evidence[key] = row
    for surface in manifest['surfaces']:
        for state in surface['states']:
            row = evidence.get((surface['id'], state))
            if not row:
                errors.append(f"{surface['id']}/{state}: Not tested")
                continue
            if row.get('status') not in STATUSES:
                errors.append(f"{surface['id']}/{state}: invalid status")
            elif row['status'] != 'Pass' and not row.get('reason'):
                errors.append(f"{surface['id']}/{state}: non-pass needs reason")
            if row.get('status') == 'Pass' and not row.get('evidence'):
                errors.append(f"{surface['id']}/{state}: Pass needs evidence")
            if row.get('status') in {'Fail', 'Not tested'}:
                errors.append(f"{surface['id']}/{state}: {row['status']}")
    for finding in report.get('findings', []):
        if finding.get('severity') in {'P0', 'P1'} and finding.get('status') != 'closed':
            errors.append(f"Open {finding['severity']}: {finding.get('id')}")
    for category in ('technical', 'visual_task', 'behavior'):
        result = report.get('conclusions', {}).get(category, {})
        if result.get('status') != 'Pass' or not result.get('evidence'):
            errors.append(f'{category}: missing independent Pass evidence')
    return {'status': 'Fail' if errors else 'Pass', 'errors': errors,
            'scope': manifest['scope'], 'not_claimed': 'Host migration, human usability or full accessibility certification'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    s = sub.add_parser('scan')
    s.add_argument('paths', type=Path, nargs='+')
    s.add_argument('--baseline', type=Path)
    c = sub.add_parser('coverage')
    c.add_argument('--manifest', type=Path, required=True)
    c.add_argument('--report', type=Path, required=True)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    if args.command == 'scan':
        files = [file for path in args.paths for file in (path.rglob('*') if path.is_dir() else [path]) if file.is_file()]
        baseline = json.loads(args.baseline.read_text()).get('candidates', []) if args.baseline else []
        result = scan(files, baseline)
    else:
        result = coverage(json.loads(args.manifest.read_text()), json.loads(args.report.read_text()))
    content = json.dumps(result, ensure_ascii=False, indent=2) + '\n'
    if args.output:
        args.output.write_text(content)
    else:
        print(content, end='')
    return int(result['status'] == 'Fail')


if __name__ == '__main__':
    raise SystemExit(main())
