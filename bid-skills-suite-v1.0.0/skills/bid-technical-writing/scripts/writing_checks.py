#!/usr/bin/env python3
"""Check actual draft references and omissions; never certify semantic satisfaction."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def inside(project, path):
    path = Path(path)
    target = (project / path).resolve() if not path.is_absolute() else path.resolve()
    if not target.is_relative_to(project) or target == project:
        raise ValueError('文件路径超出项目范围')
    return target


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
        for key in ['source_path', 'rendered_path']:
            value = figure.get(key)
            if value and not inside(project, value).is_file():
                errors.append(figure['id'] + ': 图表文件缺失 ' + value)
        if figure['state'] in {'rendered', 'reviewed'} and not figure['rendered_path']:
            errors.append(figure['id'] + ': 图表没有渲染文件')
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
    return {'project_id': identity, 'writing_sha256': digest(writing_path),
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
        return 0 if result['structural_valid'] else 1
    except (OSError, ValueError, KeyError) as exc:
        print(json.dumps({'error': str(exc)}, ensure_ascii=False))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
