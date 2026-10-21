#!/usr/bin/env python3
"""Candidate style scan and evidence-led coverage gate (stdlib, not an AST or visual audit)."""
import argparse
import json
import math
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
    if 'journeys' in manifest:
        errors.extend(journeys(manifest, report)['errors'])
    return {'status': 'Fail' if errors else 'Pass', 'errors': errors,
            'scope': manifest['scope'], 'not_claimed': 'Host migration, human usability or full accessibility certification'}



def _text(value):
    return isinstance(value, str) and bool(value.strip())


def _refs(value):
    return isinstance(value, list) and bool(value) and all(_text(item) for item in value)


def journeys(manifest, report):
    """Reconcile a predeclared journey ledger; references are not proof of their contents."""
    errors = []
    expected = {}

    def required(obj, keys, where):
        if not isinstance(obj, dict) or any(not _text(obj.get(key)) for key in keys):
            errors.append(f'{where}: missing nonempty fields {", ".join(keys)}')
            return False
        return True

    if not isinstance(manifest, dict) or not isinstance(report, dict):
        return {'status': 'Fail', 'errors': ['manifest and report must be objects'], 'expectedSteps': 0,
                'not_claimed': 'Human usability, evidence authenticity or host business acceptance'}
    if manifest.get('schema') not in ('enterprise-ui-design/journeys/v1', 'enterprise-ui-design/surfaces/v1'):
        errors.append('manifest: unsupported journey schema')
    if report.get('schema') != 'enterprise-ui-design/review/v1':
        errors.append('report: unsupported review schema')
    if not _text(manifest.get('scope')):
        errors.append('manifest: scope required')
    if report.get('scope') != manifest.get('scope'):
        errors.append('report: scope must match the independent journey manifest')
    flows = manifest.get('journeys')
    if not isinstance(flows, list) or not flows:
        errors.append('manifest: nonempty journeys required')
        flows = []
    seen_flows = set()
    for flow in flows:
        if not required(flow, ('id', 'role', 'goal', 'entry', 'completion', 'source'), 'journey'):
            continue
        fid = flow['id']
        if fid in seen_flows:
            errors.append(f'{fid}: duplicate journey')
        seen_flows.add(fid)
        branches = flow.get('branches')
        if not isinstance(branches, list) or not branches:
            errors.append(f'{fid}: nonempty branches required')
            continue
        seen_branches, kinds = set(), set()
        for branch in branches:
            if not required(branch, ('id', 'kind'), fid + '/branch'):
                continue
            bid, kind = branch['id'], branch['kind']
            where = f'{fid}/{bid}'
            if bid in seen_branches:
                errors.append(f'{where}: duplicate branch')
            seen_branches.add(bid)
            kinds.add(kind)
            if kind not in {'main', 'recovery', 'handoff'}:
                errors.append(f'{where}: unknown branch kind')
            if type(branch.get('applicable')) is not bool:
                errors.append(f'{where}: applicable must be boolean')
                continue
            if not branch['applicable']:
                if kind == 'main' or not _text(branch.get('reason')) or branch.get('steps') != []:
                    errors.append(f'{where}: only recovery/handoff may be predeclared N/A with reason and empty steps')
                continue
            if kind == 'recovery':
                required(branch.get('recovery'), ('trigger', 'safeAction', 'preservedState', 'resumePoint', 'resultCheck'), where + '/recovery')
            if kind == 'handoff':
                required(branch.get('handoff'), ('fromRole', 'toRole', 'object', 'entry', 'expectedState'), where + '/handoff')
            steps = branch.get('steps')
            if not isinstance(steps, list) or not steps:
                errors.append(f'{where}: applicable branch needs steps')
                continue
            for step in steps:
                if not required(step, ('id', 'surface', 'state', 'action', 'expected'), where + '/step'):
                    continue
                key = (fid, bid, step['id'])
                if key in expected:
                    errors.append(f'{key}: duplicate planned step')
                expected[key] = kind
        if not {'main', 'recovery', 'handoff'} <= kinds:
            errors.append(f'{fid}: declare main, recovery and handoff applicability before execution')
    rows = report.get('journeyCoverage')
    if not isinstance(rows, list):
        errors.append('report: journeyCoverage must be an array')
        rows = []
    seen, passed = set(), set()
    for row in rows:
        if not required(row, ('journey', 'branch', 'step', 'status'), 'observation'):
            continue
        key = (row['journey'], row['branch'], row['step'])
        if key not in expected:
            errors.append(f'{key}: unknown or inapplicable step')
        if key in seen:
            errors.append(f'{key}: duplicate observation; reconcile instead of overwriting')
        seen.add(key)
        status = row['status']
        if status != 'Pass':
            # In-scope steps cannot be waived from the execution report.
            errors.append(f'{key}: {status}; applicable step is not Pass')
            if not _text(row.get('reason')):
                errors.append(f'{key}: non-pass needs reason')
            continue
        passed.add(key)
        if not _refs(row.get('evidence')):
            errors.append(f'{key}: Pass needs a nonempty evidence array')
        required(row, ('cue', 'action', 'result', 'friction'), str(key))
        kind = expected.get(key)
        if kind in {'recovery', 'handoff'}:
            required(row, (kind,), str(key))
    for key in expected.keys() - seen:
        errors.append(f'{key}: Not tested')
    conclusions = report.get('conclusions')
    ux = conclusions.get('ux', {}) if isinstance(conclusions, dict) else {}
    if not isinstance(ux, dict):
        ux = {}
    if ux.get('status') != 'Pass' or not _refs(ux.get('evidence')):
        errors.append('ux: missing independent Pass evidence')
    if ux.get('method') not in ('heuristic', 'simulation', 'runtime', 'target-user'):
        errors.append('ux: declare heuristic, simulation, runtime or target-user method')
    study = report.get('userStudy', {'status': 'Not tested', 'participants': 0, 'metrics': []})
    if not isinstance(study, dict):
        errors.append('userStudy: must be an object')
        study = {}
    if study.get('status') == 'Observed':
        if type(study.get('participants')) is not int or study['participants'] < 1:
            errors.append('userStudy: Observed needs a positive participant count')
        if not _text(study.get('source')) or not _refs(study.get('evidence')):
            errors.append('userStudy: Observed needs source and evidence')
        metrics = study.get('metrics', [])
        if not isinstance(metrics, list):
            errors.append('userStudy: metrics must be an array')
            metrics = []
        for metric in metrics:
            if not required(metric, ('name', 'unit', 'definition', 'context'), 'metric'):
                continue
            value = metric.get('value')
            if type(value) not in {int, float} or not math.isfinite(value) or value < 0 or not _refs(metric.get('evidence')):
                errors.append('metric: needs a finite nonnegative value and evidence')
    else:
        if study.get('status') != 'Not tested' or study.get('participants', 0) != 0 or study.get('metrics') not in ([], None) or study.get('evidence') not in ([], None):
            errors.append('userStudy: unobserved study cannot claim participants, evidence or metrics')
        if ux.get('method') == 'target-user':
            errors.append('ux: target-user method needs an Observed userStudy')
    findings = report.get('findings', [])
    if not isinstance(findings, list):
        errors.append('findings: must be an array')
        findings = []
    for finding in findings:
        if not required(finding, ('id', 'severity', 'status'), 'finding'):
            continue
        if finding['severity'] not in {'P0', 'P1', 'P2', 'P3'}:
            errors.append(f"{finding['id']}: unsupported severity")
        if finding['severity'] in {'P0', 'P1'}:
            if finding['status'] != 'closed':
                errors.append(f"Open {finding['severity']}: {finding['id']}")
            else:
                recheck = finding.get('recheck')
                if not _text(finding.get('repairLocation')) or not isinstance(recheck, dict) or recheck.get('status') != 'Pass' or not _refs(recheck.get('evidence')):
                    errors.append(f"{finding['id']}: closed critical finding needs repair location and Pass recheck evidence")
    return {'status': 'Fail' if errors else 'Pass', 'scope': manifest.get('scope'),
            'expectedSteps': len(expected), 'reportedSteps': len(seen & expected.keys()),
            'passedSteps': len(passed & expected.keys()), 'errors': errors,
            'not_claimed': 'Human usability certification, evidence authenticity, safe backend retry or host business acceptance'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    s = sub.add_parser('scan')
    s.add_argument('paths', type=Path, nargs='+')
    s.add_argument('--baseline', type=Path)
    for command in ('coverage', 'journeys'):
        c = sub.add_parser(command)
        c.add_argument('--manifest', type=Path, required=True)
        c.add_argument('--report', type=Path, required=True)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    if args.command == 'scan':
        files = [file for path in args.paths for file in (path.rglob('*') if path.is_dir() else [path]) if file.is_file()]
        baseline = json.loads(args.baseline.read_text()).get('candidates', []) if args.baseline else []
        result = scan(files, baseline)
    else:
        gate = journeys if args.command == 'journeys' else coverage
        try:
            result = gate(json.loads(args.manifest.read_text()), json.loads(args.report.read_text()))
        except (OSError, json.JSONDecodeError) as exc:
            result = {'status': 'Fail', 'errors': [f'Cannot read audit input: {exc}']}
    content = json.dumps(result, ensure_ascii=False, indent=2) + '\n'
    if args.output:
        args.output.write_text(content)
    else:
        print(content, end='')
    return int(result['status'] == 'Fail')


if __name__ == '__main__':
    raise SystemExit(main())
