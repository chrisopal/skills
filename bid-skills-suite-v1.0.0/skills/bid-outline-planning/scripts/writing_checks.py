#!/usr/bin/env python3
"""Check actual draft references and omissions; never certify semantic satisfaction."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from writing_policy import assess_chapters


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def inside(project, path):
    path = Path(path)
    target = (project / path).resolve() if not path.is_absolute() else path.resolve()
    if not target.is_relative_to(project) or target == project:
        raise ValueError('文件路径超出项目范围')
    return target


_RENDER_ENGINES = {'drawio': '.drawio', 'plantuml': '.puml', 'mermaid': '.mmd', 'blueprint': '.diagram.json'}
_RENDER_RECORD_FIELDS = {
    'engine', 'source_sha256', 'output_sha256', 'receipt_path', 'receipt_sha256',
    'base_source_sha256', 'cas_result',
}
_SHA256 = re.compile(r'^[a-f0-9]{64}$')


def _relative(project, path):
    return path.resolve().relative_to(project).as_posix()


def _check_render_record(project, figure, source, rendered, errors):
    figure_id = figure['id']
    record = figure.get('render_record')
    if not isinstance(record, dict) or set(record) != _RENDER_RECORD_FIELDS:
        errors.append(figure_id + ': render_record 字段不完整或包含未知字段')
        return
    source_rel = _relative(project, source)
    rendered_rel = _relative(project, rendered)
    engine = record['engine']
    if engine not in _RENDER_ENGINES:
        errors.append(figure_id + ': render_record.engine 无效')
    expected_suffix = _RENDER_ENGINES.get(engine)
    if expected_suffix and not source.name.lower().endswith(expected_suffix):
        errors.append(figure_id + ': render_record.engine 与图源扩展名不一致')
    for field in ('source_sha256', 'output_sha256', 'receipt_sha256', 'base_source_sha256'):
        if not isinstance(record[field], str) or not _SHA256.fullmatch(record[field]):
            errors.append(figure_id + ': render_record.' + field + ' 无效')
    if record['cas_result'] != 'matched':
        errors.append(figure_id + ': render_record.cas_result 必须为 matched')
    try:
        receipt = inside(project, record['receipt_path'])
    except (TypeError, ValueError):
        errors.append(figure_id + ': render_record.receipt_path 越出项目范围')
        return
    if not receipt.is_file():
        errors.append(figure_id + ': render receipt 缺失 ' + str(record['receipt_path']))
        return
    actual_source_sha = digest(source)
    actual_output_sha = digest(rendered)
    actual_receipt_sha = digest(receipt)
    if record['source_sha256'] != actual_source_sha:
        errors.append(figure_id + ': 图源哈希与 render_record 不一致')
    if record['output_sha256'] != actual_output_sha:
        errors.append(figure_id + ': 成图哈希与 render_record 不一致')
    if record['receipt_sha256'] != actual_receipt_sha:
        errors.append(figure_id + ': receipt 哈希与 render_record 不一致')
    try:
        receipt_value = json.loads(receipt.read_text(encoding='utf-8'))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        errors.append(figure_id + ': render receipt 不是有效 JSON')
        return
    if not isinstance(receipt_value, dict):
        errors.append(figure_id + ': render receipt 顶层必须是对象')
        return
    expected = {
        'engine': engine,
        'source_path': source_rel,
        'output_path': rendered_rel,
        'source_sha256': record['source_sha256'],
        'output_sha256': record['output_sha256'],
        'base_source_sha256': record['base_source_sha256'],
        'cas_result': record['cas_result'],
    }
    for field, value in expected.items():
        if receipt_value.get(field) != value:
            errors.append(figure_id + ': render receipt 的 ' + field + ' 与记录不一致')
    if receipt_value.get('state') != 'rendered':
        errors.append(figure_id + ': render receipt 未记录实际渲染状态')
    if engine == 'blueprint':
        style = receipt_value.get('diagram_style')
        try:
            specification = json.loads(source.read_text(encoding='utf-8'))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            specification = None
        if (not isinstance(style, dict) or not isinstance(specification, dict)
                or style.get('theme') != specification.get('theme', 'reference')
                or style.get('layout') != specification.get('layout')
                or not isinstance(style.get('nodes'), list)
                or not isinstance(style.get('edges'), list)
                or not isinstance(specification.get('nodes'), list)
                or not isinstance(specification.get('edges'), list)
                or len(style['nodes']) != len(specification.get('nodes', []))
                or len(style['edges']) != len(specification.get('edges', []))
                or any(not isinstance(edge, dict) or edge.get('safe') is not True
                       for edge in style['edges'])):
            errors.append(figure_id + ': 新图表实际样式与JSON源不一致或缺失布局记录')
        expected_theme = receipt_value.get('expected_theme')
        if expected_theme is not None and (not isinstance(style, dict) or style.get('theme') != expected_theme):
            errors.append(figure_id + ': 新图表实际主题与计划不一致')


def check_project(project, outline_path, writing_path, visuals_path=None):
    project = Path(project).resolve()
    outline_path = inside(project, outline_path)
    writing_path = inside(project, writing_path)
    errors, warnings, visited = [], [], set()
    project_file = project / 'work/project.json'
    identity = json.loads(project_file.read_text())['project_id'] if project_file.exists() else None

    def load(path):
        nonlocal identity
        path = inside(project, path)
        value = json.loads(path.read_text(encoding='utf-8'))
        if identity is None:
            identity = value.get('project_id')
        if value.get('project_id') != identity:
            errors.append(path.name + ': 项目身份不一致')
        if path not in visited:
            visited.add(path)
            for ref in value.get('inputs', []):
                try:
                    source = inside(project, ref['relative_path'])
                    if not source.is_file() or digest(source) != ref['sha256']:
                        errors.append('输入缺失或已过期: ' + ref['relative_path'])
                        continue
                    if source.suffix == '.json':
                        upstream = load(source)
                        if 'artifact_id' in upstream and upstream['artifact_id'] != ref['artifact_id']:
                            errors.append(source.name + ': 输入产物身份不一致')
                        if 'revision' in upstream and upstream['revision'] != ref['revision']:
                            errors.append(source.name + ': 输入版本不一致')
                except (OSError, ValueError, KeyError) as exc:
                    errors.append('输入校验失败: ' + str(exc))
        return value

    def stage(number, required=False):
        paths = sorted((project / 'artifacts').glob(f'{number:02d}-*.json'))
        paths = [p for p in paths if 'trace' not in p.name]
        if not paths:
            if required:
                errors.append(f'缺少{number:02d}阶段产物')
            return {'data': {}}
        if len(paths) > 1:
            errors.append(f'{number:02d}当前产物不唯一，需明确当前版本')
        return load(paths[0])

    outline, writing = load(outline_path), load(writing_path)
    requirements = stage(3, True)['data'].get('requirements', [])
    scoring = stage(4, True)['data'].get('items', [])
    compliance = stage(5, True)['data'].get('rules', [])
    formats = stage(6)['data'].get('formats', [])
    evidence = stage(9)['data']
    design = stage(10)['data'].get('decisions', [])
    visuals = load(inside(project, visuals_path)) if visuals_path else stage(13)
    sections = outline['data']['sections']
    chapters = writing['data']['chapters']
    responses = writing['data']['responses']
    req_ids = {r['id'] for r in requirements}
    section_by = {s['id']: s for s in sections}
    chapter_by = {c['id']: c for c in chapters}
    material_by = {m['id']: m for m in evidence.get('materials', [])}
    accepted_materials = {m for s in evidence.get('selections', [])
                          if s['state'] == 'accepted' for m in s['material_ids']}
    design_ids = {d['id'] for d in design}
    known_sets = {'requirement_ids': req_ids, 'scoring_ids': {s['id'] for s in scoring},
                  'compliance_ids': {c['id'] for c in compliance},
                  'format_ids': {f['id'] for f in formats}}
    mapped = {key: set() for key in known_sets}
    if len(section_by) != len(sections) or len(chapter_by) != len(chapters):
        errors.append('章节ID重复')
    for section in sections:
        seen, node = set(), section
        while node.get('parent_id'):
            if node['id'] in seen:
                errors.append(section['id'] + ': 目录循环')
                break
            seen.add(node['id'])
            if node['parent_id'] not in section_by:
                errors.append(section['id'] + ': 父章节不存在')
                break
            node = section_by[node['parent_id']]
        for key, known in known_sets.items():
            refs = set(section.get(key, []))
            mapped[key].update(refs)
            if refs - known:
                errors.append(section['id'] + ': 不存在的映射 ' + ','.join(sorted(refs - known)))
    written, evidence_gaps = set(), []
    for chapter in chapters:
        section = section_by.get(chapter['section_id'])
        if section is None:
            errors.append(chapter['id'] + ': 目录章节不存在')
            continue
        refs = set(chapter['requirement_ids'])
        written.update(refs)
        if refs - req_ids or refs - set(section['requirement_ids']):
            errors.append(chapter['id'] + ': 需求不存在或未绑定此目录章节')
        if set(chapter['design_ids']) - design_ids:
            errors.append(chapter['id'] + ': 设计ID不存在')
        for material in chapter['evidence_ids']:
            if material not in material_by:
                errors.append(chapter['id'] + ': 证明材料不存在 ' + material)
            elif material not in accepted_materials:
                evidence_gaps.append(chapter['id'] + ': 素材尚未采纳 ' + material)
        if not chapter['body_markdown'].strip():
            errors.append(chapter['id'] + ': 正文为空')
        if chapter['state'] == 'accepted' and not chapter['confirmation_ref']:
            errors.append(chapter['id'] + ': 缺真实采纳记录')
    response_ids = []
    for response in responses:
        rid = response['requirement_id']
        response_ids.append(rid)
        if rid not in req_ids:
            errors.append('响应引用不存在的需求: ' + rid)
        for cid in response['chapter_ids']:
            if cid not in chapter_by or rid not in chapter_by[cid]['requirement_ids']:
                errors.append(rid + ': 响应的正文章节不存在或没有此需求绑定')
        if response['fulfillment'] in {'satisfied', 'partial'} and not response['chapter_ids']:
            errors.append(rid + ': 响应没有实际正文')
    if len(set(response_ids)) != len(response_ids):
        errors.append('需求响应重复')
    for figure in visuals['data'].get('figures', []):
        if figure['section_id'] not in section_by:
            errors.append(figure['id'] + ': 图表章节不存在')
        paths = {}
        for key in ['source_path', 'rendered_path']:
            value = figure.get(key)
            if value:
                try:
                    paths[key] = inside(project, value)
                except (TypeError, ValueError):
                    errors.append(figure['id'] + ': 图表路径越出项目范围 ' + str(value))
                else:
                    if not paths[key].is_file():
                        errors.append(figure['id'] + ': 图表文件缺失 ' + value)
        if figure['state'] in {'rendered', 'reviewed'} and not figure['rendered_path']:
            errors.append(figure['id'] + ': 图表没有渲染文件')
        source = paths.get('source_path')
        rendered = paths.get('rendered_path')
        native_source = source and (source.suffix.lower() in {'.drawio', '.puml'}
                                    or source.name.lower().endswith('.diagram.json'))
        if (figure['state'] in {'rendered', 'reviewed'} and native_source
                and not figure.get('render_record')):
            errors.append(figure['id'] + ': rendered/reviewed 的原生图源缺少 render_record')
        elif (figure['state'] in {'rendered', 'reviewed'} and source
              and not figure.get('render_record')):
            warnings.append(figure['id'] + ': 历史图源没有CLI render_record，不能声称通过CLI审计')
        if figure.get('render_record') and source and rendered and source.is_file() and rendered.is_file():
            _check_render_record(project, figure, source, rendered, errors)
    trace_path = project / 'artifacts/11-writing-trace.json'
    trace_state, traced = 'missing', set()
    response_text = {r['requirement_id']: ''.join(r['response'].split()) for r in responses}
    requirement_text = {r['id']: ''.join(r['text'].split()) for r in requirements}
    if trace_path.exists():
        trace = json.loads(trace_path.read_text(encoding='utf-8'))
        if trace.get('writing_sha256') != digest(writing_path):
            trace_state = 'stale'
            warnings.append('正文已变化，段落追溯待重新复核')
        else:
            trace_state = 'current'
            for link in trace.get('links', []):
                chapter = chapter_by.get(link['chapter_id'])
                quote = ''.join(link['body_quote'].split())
                if quote and quote in {
                    response_text.get(link['requirement_id']),
                    requirement_text.get(link['requirement_id']),
                }:
                    errors.append('段落追溯不能用响应全文或纯需求原文自证')
                elif (not chapter or link['requirement_id'] not in chapter['requirement_ids']
                        or not link['body_quote']
                        or link['body_quote'] not in chapter['body_markdown']):
                    errors.append('段落追溯不存在或与正文不一致')
                else:
                    traced.add(link['requirement_id'])
    score_leaves = {s['id'] for s in scoring if s['node_type'] == 'scored'}
    submitted = {c['id'] for c in compliance
                 if c['fatal'] is True or c['kind'] in {'qualification', 'submission'}}
    unmapped = sorted((req_ids - mapped['requirement_ids'])
                      | (score_leaves - mapped['scoring_ids'])
                      | (submitted - mapped['compliance_ids']))
    if unmapped:
        warnings.append('仍有目录未映射项')
    evidence_gaps.extend(evidence.get('gaps', []))
    score_context = set()
    for chapter in chapters:
        node = section_by.get(chapter['section_id'])
        seen = set()
        while node and node['id'] not in seen:
            seen.add(node['id'])
            score_context.update(node.get('scoring_ids', []))
            node = section_by.get(node.get('parent_id'))
    scoring_started = score_leaves & score_context
    settings_path = inside(project, 'work/writing-settings.json')
    settings = json.loads(settings_path.read_text(encoding='utf-8')) if settings_path.is_file() else {}
    try:
        policy = assess_chapters(project, sections, chapters, scoring, requirements,
                                 visuals['data'].get('figures', []), settings)
    except (ValueError, TypeError) as exc:
        policy = {'passed': False, 'chapters': [], 'blocking_issues': [str(exc)],
                  'recommendation_issues': [], 'semantic_acceptance': 'NOT_TESTED'}
    return {'project_id': identity, 'writing_sha256': digest(writing_path),
            'writing_policy': policy, 'writing_policy_valid': policy['passed'],
            'structural_valid': not errors, 'errors': errors, 'warnings': warnings,
            'requirement_count': len(req_ids), 'outline_mapped_count': len(req_ids & mapped['requirement_ids']),
            'written_requirement_count': len(req_ids & written), 'response_count': len(set(response_ids)),
            'unmapped': unmapped, 'planned_not_written': sorted(mapped['requirement_ids'] - written),
            'missing_responses': sorted(req_ids - set(response_ids)),
            'unwritten_scoring': sorted(score_leaves - scoring_started),
            'scoring_started': sorted(scoring_started),
            'scoring_pending_review': sorted(score_leaves),
            'evidence_gaps': evidence_gaps, 'unresolved_claims': writing['data']['unresolved_claims'],
            'trace_state': trace_state, 'written_without_paragraph_trace': sorted(written - traced),
            'semantic_acceptance': 'NOT_TESTED',
            'note': '结构检查和原文定位不证明正文语义满足；未写作、缺材料和待确认项必须逐项复核。'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, required=True)
    parser.add_argument('--outline', type=Path, default=Path('artifacts/08-outline.json'))
    parser.add_argument('--writing', type=Path, default=Path('artifacts/11-technical-content.json'))
    parser.add_argument('--visuals', type=Path)
    parser.add_argument('--out', type=Path)
    args = parser.parse_args()
    try:
        result = check_project(args.project, args.outline, args.writing, args.visuals)
        text = json.dumps(result, ensure_ascii=False, indent=2)
        if args.out:
            out = inside(args.project.resolve(), args.out)
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(text + '\n', encoding='utf-8')
        print(text)
        return 0 if result['structural_valid'] and result['writing_policy_valid'] else 1
    except (OSError, ValueError, KeyError) as exc:
        print(json.dumps({'error': str(exc)}, ensure_ascii=False))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
