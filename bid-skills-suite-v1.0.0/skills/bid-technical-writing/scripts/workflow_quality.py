#!/usr/bin/env python3
"""Local capability preflight and live, bounded host remediation plans. No model calls."""
from __future__ import annotations

import argparse
import importlib.util
import json
import shutil
from pathlib import Path

import bidkit
from writing_policy import check_project_policy


def preflight(project, host_file=None, required=(), font_file=None):
    project = Path(project).resolve()
    capabilities = {}
    for name, module in (('docx', 'docx'), ('pdf', 'fitz'), ('schema', 'jsonschema')):
        available = importlib.util.find_spec(module) is not None
        capabilities[name] = {'status': 'available' if available else 'unavailable',
                              'evidence': 'python module: ' + module}
    binary = shutil.which('soffice') or shutil.which('libreoffice')
    capabilities['pdf_export'] = {'status': 'available' if binary else 'unavailable',
                                  'evidence': binary or 'no installed LibreOffice command'}
    capabilities['font'] = {'status': 'available' if font_file and Path(font_file).is_file()
                            else 'not_checked', 'evidence': str(font_file or 'font file not specified')}
    for name in ('ocr', 'host_images', 'host_agents', 'host_knowledge'):
        capabilities[name] = {'status': 'not_checked', 'evidence': 'requires actual host discovery'}
    binding = None
    if host_file:
        path = bidkit.safe(project, host_file)
        value = bidkit.read(path)
        if value.get('project_id') != bidkit.project_id(project):
            raise ValueError('宿主能力记录项目不一致')
        for name, item in value.get('capabilities', {}).items():
            if name not in ('ocr', 'host_images', 'host_agents', 'host_knowledge'):
                raise ValueError('未知宿主能力：' + name)
            if set(item) != {'status', 'evidence'} or item['status'] not in {
                    'available', 'unavailable', 'not_checked'} or not str(item['evidence']).strip():
                raise ValueError('宿主能力需明确状态及实际发现依据')
            capabilities[name] = item
        binding = {'relative_path': host_file, 'sha256': bidkit.digest(path)}
    if set(required) - capabilities.keys():
        raise ValueError('未知必需能力')
    missing = [name for name in required if capabilities[name]['status'] != 'available']
    return {'project_id': bidkit.project_id(project), 'checked_at': bidkit.now(),
            'capabilities': capabilities, 'host_discovery': binding, 'missing_required': missing,
            'passed': not missing, 'execution_verified': False,
            'notice': '可发现不等于调用成功；宿主声明不认证远端权限或模型效果。'}


def live_findings(project):
    project = Path(project).resolve()
    findings = []
    policy = check_project_policy(project)
    if policy.get('status') == 'NOT_CONFIGURED':
        findings.append({'id': 'POLICY:configuration', 'section_ids': [],
                         'reason': '写作检查未配置，需保存实际章节/配图要求后重新检查。',
                         'blocking': True, 'skill': 'bid-orchestrator'})
    for row in policy['chapters']:
        for number, reason in enumerate(row.get('blocking_issues', [])):
            kind = 'ui' if '界面图' in reason else 'length'
            findings.append({'id': f"POLICY:{row['section_id']}:{kind}:{number}",
                             'section_ids': [row['section_id']], 'reason': reason,
                             'blocking': True, 'skill': 'bid-visuals' if kind == 'ui'
                             else 'bid-technical-writing'})
    quality_path = project / 'profiles/quality-plan.json'
    quality = None
    if quality_path.is_file():
        import quality_checks
        quality = quality_checks.check(project)
        for number, action in enumerate(quality.get('actions', [])):
            item = dict(action)
            item.setdefault('id', 'QUALITY:' + str(item.get('row_id') or item.get('target_id', number)))
            item.setdefault('section_ids', [])
            item.setdefault('reason', item.get('message', '质量条件需复核'))
            item.setdefault('blocking', True)
            item.setdefault('skill', 'bid-review-remediation')
            findings.append(item)
        if (quality.get('errors') or quality.get('release_blockers')) and not quality.get('actions'):
            findings.append({'id': 'QUALITY:contract', 'section_ids': [], 'blocking': True,
                             'skill': 'bid-review-remediation',
                             'reason': '; '.join(quality.get('errors', []) + quality.get('release_blockers', []))})
    return findings, {'writing_policy': policy, 'quality': quality}


def plan(project, out='work/remediation-plan.json', max_attempts=2):
    project = Path(project).resolve()
    if isinstance(max_attempts, bool) or not 1 <= max_attempts <= 10:
        raise ValueError('最大整改轮次为1—10')
    destination = bidkit.safe(project, out)
    if destination.exists():
        raise ValueError('整改计划已存在，请回读status，不覆盖尝试历史')
    findings, _ = live_findings(project)
    value = {'project_id': bidkit.project_id(project), 'created_at': bidkit.now(),
             'max_attempts': max_attempts, 'attempts': [], 'tasks': findings,
             'base_inputs': bidkit.scan_content(project),
             'state': 'needs_remediation' if findings else 'checks_clear',
             'notice': '宿主执行实际修改；状态回读不代表已派发Agent、语义通过或正式交付。'}
    bidkit.atomic(destination, value)
    return value


def status(project, plan_file='work/remediation-plan.json'):
    project = Path(project).resolve()
    value = bidkit.read(bidkit.safe(project, plan_file))
    if value.get('project_id') != bidkit.project_id(project):
        raise ValueError('整改计划项目不一致')
    current, checks = live_findings(project)
    pending = {item['id'] for item in current}
    resolved = [row['id'] for row in value['tasks'] if row['id'] not in pending]
    # Fresh checks control status. Stored "resolved" declarations are never trusted.
    state = ('checks_clear' if not current else 'attempts_exhausted'
             if len(value['attempts']) >= value['max_attempts'] else 'needs_remediation')
    return {'project_id': value['project_id'], 'state': state, 'pending': current,
            'resolved_ids': resolved, 'attempts': len(value['attempts']),
            'max_attempts': value['max_attempts'], 'checks': checks,
            'semantic_acceptance': 'REQUIRES_HOST_REVIEW', 'formal_release_ready': False}


def record_attempt(project, plan_file='work/remediation-plan.json', evidence_file=None):
    project = Path(project).resolve()
    path = bidkit.safe(project, plan_file)
    value = bidkit.read(path)
    current = status(project, plan_file)
    if len(value['attempts']) >= value['max_attempts']:
        raise ValueError('整改次数已用尽，保留阻塞，不自动放宽门禁')
    if not evidence_file:
        raise ValueError('需要实际宿主执行记录')
    evidence = bidkit.safe(project, evidence_file)
    log = bidkit.read(evidence)
    if (log.get('project_id') != value['project_id'] or not log.get('performed_actions')
            or not log.get('tool_or_agent')):
        raise ValueError('执行记录需匹配项目、实际宿主和已执行操作')
    inputs = bidkit.scan_content(project)
    previous = value['attempts'][-1]['result_inputs'] if value['attempts'] else value['base_inputs']
    if inputs == previous:
        raise ValueError('项目输入未变化，不能把建议当成已整改')
    value['attempts'].append({'number': len(value['attempts']) + 1, 'recorded_at': bidkit.now(),
                              'evidence': {'relative_path': evidence_file, 'sha256': bidkit.digest(evidence)},
                              'result_inputs': inputs, 'pending_ids': [x['id'] for x in current['pending']]})
    value['state'] = current['state']
    bidkit.atomic(path, value)
    return status(project, plan_file)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('preflight', 'plan', 'status', 'record-attempt'))
    parser.add_argument('--project', required=True)
    parser.add_argument('--host-capabilities')
    parser.add_argument('--require', action='append', default=[])
    parser.add_argument('--font-file')
    parser.add_argument('--out')
    parser.add_argument('--plan', default='work/remediation-plan.json')
    parser.add_argument('--max-attempts', type=int, default=2)
    parser.add_argument('--evidence')
    args = parser.parse_args()
    try:
        if args.command == 'preflight':
            result = preflight(args.project, args.host_capabilities, args.require, args.font_file)
        elif args.command == 'plan':
            result = plan(args.project, args.out or args.plan, args.max_attempts)
        elif args.command == 'status':
            result = status(args.project, args.plan)
        else:
            result = record_attempt(args.project, args.plan, args.evidence)
        if args.out and args.command != 'plan':
            bidkit.atomic(bidkit.safe(args.project, args.out), result)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(json.dumps({'error': str(exc)}, ensure_ascii=False))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
