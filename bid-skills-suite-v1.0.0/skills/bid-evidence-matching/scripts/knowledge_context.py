#!/usr/bin/env python3
"""Prepare chapter knowledge and bind exact source quotes to persisted prose.

Integrity checks do not certify truth, semantic fulfillment or owner approval.
New material flags affected reference packs; this module never edits prose.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date, datetime, timezone
from pathlib import Path

import bidkit
import knowledge

CITATIONS = 'artifacts/knowledge/citations.json'
WRITING = 'artifacts/11-technical-content.json'
OUTLINE = 'artifacts/08-outline.json'
EVIDENCE = 'artifacts/09-evidence-selection.json'


def _id(value):
    if not isinstance(value, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}', value):
        raise ValueError('章节ID无效')
    return value


def _field(entry, name):
    field = entry.get('material', {}).get('fields', {}).get(name)
    if not isinstance(field, dict) or field.get('needs_verification') is True:
        return None
    return field.get('value')


def _constraints(entry, criteria):
    reasons = []
    material = entry.get('material', {})
    checked_fields = {'person'} & set(criteria)
    if 'valid_on' in criteria:
        checked_fields.update(('valid_from', 'valid_until'))
    if 'social_months' in criteria:
        checked_fields.add('social_months')
    for name in sorted(checked_fields):
        field = material.get('fields', {}).get(name, {})
        if field.get('needs_verification') is True:
            reasons.append(name + '归一化值待核对，不能通过硬条件')
    for name in ('subject', 'category', 'person'):
        if name not in criteria:
            continue
        actual = entry.get('subject') if name == 'subject' else (
            material.get('category') if name == 'category' else _field(entry, name))
        if actual != criteria[name]:
            reasons.append(name + '不符或未确认')
    if 'valid_on' in criteria:
        valid_on = date.fromisoformat(criteria['valid_on'])
        until, start = _field(entry, 'valid_until'), _field(entry, 'valid_from')
        try:
            if until is None or date.fromisoformat(str(until)) < valid_on:
                reasons.append('要求日期内有效性不足或未确认')
            if start is not None and date.fromisoformat(str(start)) > valid_on:
                reasons.append('要求日期尚未生效')
        except ValueError:
            reasons.append('材料有效日期格式待核对')
    if 'social_months' in criteria:
        actual = _field(entry, 'social_months')
        if not isinstance(actual, list) or not set(criteria['social_months']).issubset(actual):
            reasons.append('社保月份未覆盖要求或未确认')
    return reasons


def _validate_criteria(criteria):
    if not isinstance(criteria, dict) or set(criteria) - {
            'subject', 'category', 'person', 'valid_on', 'social_months'}:
        raise ValueError('筛选条件只支持主体、类别、人员、有效日期及社保月份')
    for name in ('subject', 'category', 'person', 'valid_on'):
        if name in criteria and (not isinstance(criteria[name], str) or not criteria[name].strip()):
            raise ValueError(name + '必须为非空文本')
    if 'valid_on' in criteria:
        date.fromisoformat(criteria['valid_on'])
    if 'social_months' in criteria:
        months = criteria['social_months']
        if not isinstance(months, list) or not months:
            raise ValueError('社保月份需为非空月份列表')
        for month in months:
            if not isinstance(month, str) or not re.fullmatch(r'\d{4}-\d{2}', month):
                raise ValueError('社保月份使用YYYY-MM')
            date.fromisoformat(month + '-01')


def _entry_fingerprint(entry):
    return bidkit.canonical({key: entry.get(key) for key in (
        'id', 'subject', 'material', 'source', 'content', 'document_revision', 'connection_id',
        'connection_revision')})


def _host_timestamp(project, entry):
    content = bidkit.read(bidkit.safe(project, entry['content']['relative_path']))
    stamp = content.get('audit', {}).get('host_call', {}).get('retrieved_at')
    if not isinstance(stamp, str):
        return None
    value = datetime.fromisoformat(stamp.replace('Z', '+00:00'))
    return value if value.tzinfo is not None else None


def _candidates(project, query, criteria, limit):
    index = knowledge.load_index(project)
    knowledge.validate_index(project, index)
    entries = {entry['id']: entry for entry in index['entries']}
    host_times = {entry['id']: _host_timestamp(project, entry)
                  for entry in entries.values() if entry.get('connection_id')}
    newest = {}
    for entry in entries.values():
        stamp = host_times.get(entry['id'])
        if stamp is not None:
            key = (entry['connection_id'], entry.get('connection_revision'),
                   entry['document_id'], entry['source_ref'])
            newest[key] = max(stamp, newest.get(key, stamp))
    pre_excluded = {entry['id']: _constraints(entry, criteria) for entry in entries.values()}
    eligible = {ident for ident, reasons in pre_excluded.items() if not reasons}
    matches = knowledge.search(project, query, limit=100, entry_ids=eligible)['matches']
    candidates = []
    excluded = [{'knowledge_id': ident, 'reasons': reasons}
                for ident, reasons in pre_excluded.items() if reasons]
    for match in matches:
        entry = entries[match['id']]
        reasons = _constraints(entry, criteria)
        connection_id = entry.get('connection_id')
        if connection_id:
            from knowledge_connections import status
            state = status(project, connection_id)
            if not state['usable']:
                reasons.append('知识库当前状态需要重新检索或授权核对：' + state['state'])
            if entry.get('connection_revision') != state['revision']:
                reasons.append('该材料来自已变更的连接配置，需重新检索')
            stamp = host_times[entry['id']]
            if stamp is None or not -300 <= (datetime.now(timezone.utc) - stamp).total_seconds() <= state['max_age_hours'] * 3600:
                reasons.append('该文档快照已过期或检索时间未确认，其他检索不能续期')
            invalid_before = state.get('invalid_before')
            if stamp is not None and invalid_before and stamp < datetime.fromisoformat(invalid_before):
                reasons.append('该文档快照早于权限失败，需单独重新检索')
            key = (connection_id, entry.get('connection_revision'), entry['document_id'], entry['source_ref'])
            if stamp is not None and stamp < newest[key]:
                reasons.append('该文档已有更新检索快照，旧快照不再用于写作')
        if reasons:
            excluded.append({'knowledge_id': entry['id'], 'reasons': reasons})
            continue
        if len(candidates) >= limit:
            continue
        material = entry.get('material', {})
        candidates.append({
            'knowledge_id': entry['id'], 'title': entry['title'],
            'location': match['location'], 'quote': match['excerpt'],
            'quote_truncated': match['excerpt_truncated'], 'source': entry['source'],
            'content': entry['content'], 'source_ref': entry['source_ref'],
            'category': material.get('category', 'unknown'),
            'kind': material.get('kind', 'unknown'), 'subject': entry.get('subject'),
            'simulation': material.get('simulation', False),
            'entry_fingerprint': _entry_fingerprint(entry),
            'connection_id': connection_id, 'evidence_state': 'candidate',
            'independent_evidence_id': _field(entry, 'contract_id') or
                                       _field(entry, 'independent_evidence_id'),
        })
    return candidates, excluded


def prepare(project, section_id, query, *, criteria=None, limit=10, outline_path=OUTLINE):
    project = Path(project).resolve()
    _id(section_id)
    criteria = criteria or {}
    _validate_criteria(criteria)
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 100:
        raise ValueError('候选数量需为1到100')
    with knowledge.writer(project):
        outline_file = bidkit.safe(project, outline_path)
        outline = bidkit.read(outline_file)
        if section_id not in {row['id'] for row in outline['data']['sections']}:
            raise ValueError('目录中不存在该章节')
        candidates, excluded = _candidates(project, query, criteria, limit)
        value = {'schema_version': '1.0', 'project_id': bidkit.project_id(project),
                 'section_id': section_id, 'query': query, 'criteria': criteria,
                 'limit': limit, 'created_at': bidkit.now(),
                 'index_revision': knowledge.load_index(project)['revision'],
                 'outline': knowledge.reference(project, outline_file, 'outline'),
                 'candidates': candidates, 'excluded': excluded,
                 'gaps': [] if candidates else ['未取得满足当前检索条件的材料；需补料或调整检索。'],
                 'notice': '候选与引用均不认证真实性、完整证明、评分满足或材料所有者采纳。'}
        name = 'KP-' + bidkit.canonical(value)[:20]
        value['relative_path'] = f'artifacts/knowledge/packs/{name}.json'
        target = bidkit.safe(project, value['relative_path'])
        bidkit.atomic(target, value)
        return value


def _valid_pack(project, pack):
    errors = []
    if pack.get('project_id') != bidkit.project_id(project):
        return ['参考包项目身份不符']
    try:
        outline = bidkit.safe(project, pack['outline']['relative_path'])
        if bidkit.digest(outline) != pack['outline']['sha256']:
            errors.append('目录已变化，需重新准备章节参考包')
        current, _ = _candidates(project, pack['query'], pack['criteria'], pack['limit'])
        if current != pack['candidates']:
            errors.append('相关材料或适用条件已变化，需重新选材')
    except (ValueError, OSError, KeyError, TypeError) as exc:
        errors.append(str(exc))
    return errors


def _accepted_material(project, candidate, material_id):
    if not material_id:
        raise ValueError('证明引用必须关联09中已采纳的material_id，不能直接采纳检索候选')
    path = bidkit.safe(project, EVIDENCE)
    selection = bidkit.read(path)
    if selection.get('project_id') != bidkit.project_id(project):
        raise ValueError('09材料选用项目身份不符')
    materials = [row for row in selection['data']['materials'] if row['id'] == material_id]
    if len(materials) != 1:
        raise ValueError('09中不存在唯一的证明材料记录')
    source = candidate['source']
    if not any(row.get('source_id') == source['artifact_id']
               and row.get('sha256') == source['sha256']
               for row in materials[0].get('sources', [])):
        raise ValueError('09证明材料与当前知识原件不一致')
    if not any(row.get('state') == 'accepted' and material_id in row.get('material_ids', [])
               for row in selection['data']['selections']):
        raise ValueError('09证明材料尚未采纳')
    return knowledge.reference(project, path, 'evidence-selection')


def bind(project, chapter_id, pack_path, usages, *, writing_path=WRITING):
    project = Path(project).resolve()
    _id(chapter_id)
    if not isinstance(usages, list) or not usages:
        raise ValueError('请明确采用的原文、位置与对应正文')
    with knowledge.writer(project):
        pack_file = bidkit.safe(project, pack_path)
        pack = bidkit.read(pack_file)
        errors = _valid_pack(project, pack)
        if errors:
            raise ValueError('；'.join(errors))
        writing = bidkit.read(bidkit.safe(project, writing_path))
        if writing.get('project_id') != bidkit.project_id(project):
            raise ValueError('正文项目身份不符')
        chapters = [row for row in writing['data']['chapters'] if row['id'] == chapter_id]
        if len(chapters) != 1 or chapters[0]['section_id'] != pack['section_id']:
            raise ValueError('正文与章节参考包不对应')
        chapter = chapters[0]
        citations = []
        for usage in usages:
            if (not isinstance(usage, dict) or set(usage) - {'material_id'} != {
                    'knowledge_id', 'location', 'source_quote', 'claim', 'purpose'}):
                raise ValueError('引用需包含知识ID、原文位置、原文、正文和用途')
            if usage['purpose'] not in {'reference', 'evidence'}:
                raise ValueError('引用用途为reference或evidence')
            if any(not isinstance(usage[key], str) or not usage[key].strip() for key in usage):
                raise ValueError('引用字段不能为空')
            candidate = next((row for row in pack['candidates']
                              if row['knowledge_id'] == usage['knowledge_id']
                              and row['location'] == usage['location']), None)
            if candidate is None:
                raise ValueError('引用不在本章候选中')
            content = bidkit.read(bidkit.safe(project, candidate['content']['relative_path']))
            blocks = [block for block in content['blocks'] if block['location'] == usage['location']]
            if not any(usage['source_quote'] in block['text'] for block in blocks):
                raise ValueError('引用原文不在保存的来源位置')
            if usage['claim'] not in chapter['body_markdown']:
                raise ValueError('引用所对应的内容不在当前正文')
            if usage['purpose'] == 'evidence' and candidate['kind'] != 'evidence':
                raise ValueError('技术参考或未知材料不能作为证明引用')
            acceptance = (_accepted_material(project, candidate, usage.get('material_id'))
                          if usage['purpose'] == 'evidence' else None)
            citations.append({**usage, 'evidence_selection': acceptance,
                              'source': candidate['source'], 'content': candidate['content'],
                              'source_ref': candidate['source_ref'],
                              'simulation': candidate['simulation'], 'evidence_state': 'candidate'})
        file = bidkit.safe(project, CITATIONS)
        value = bidkit.read(file) if file.exists() else {
            'schema_version': '1.0', 'project_id': bidkit.project_id(project), 'revision': 0,
            'chapters': []}
        if value['project_id'] != bidkit.project_id(project):
            raise ValueError('章节引用与项目身份不符')
        record = {'chapter_id': chapter_id, 'section_id': chapter['section_id'],
                  'writing_path': writing_path, 'body_sha256': bidkit.canonical(chapter['body_markdown']),
                  'pack': knowledge.reference(project, pack_file, pack_file.stem),
                  'citations': citations, 'recorded_at': bidkit.now()}
        value['chapters'] = [row for row in value['chapters'] if row['chapter_id'] != chapter_id]
        value['chapters'].append(record)
        value['revision'] += 1
        bidkit.atomic(file, value)
        return record


def check(project, *, writing_path=WRITING):
    project = Path(project).resolve()
    path = bidkit.safe(project, CITATIONS)
    if not path.exists():
        return {'valid': True, 'state': 'not_configured', 'bound_chapters': 0,
                'affected_sections': [], 'errors': [], 'warnings': []}
    value = bidkit.read(path)
    errors, warnings, affected = [], [], set()
    simulated, proof_candidates = 0, 0
    if value.get('project_id') != bidkit.project_id(project):
        errors.append('章节引用项目身份不符')
    writing = bidkit.read(bidkit.safe(project, writing_path))
    if writing.get('project_id') != bidkit.project_id(project):
        errors.append('正文项目身份不符')
    chapters = {row['id']: row for row in writing['data']['chapters']}
    for record in value['chapters']:
        local_errors = []
        chapter = chapters.get(record['chapter_id'])
        if (chapter is None or chapter['section_id'] != record['section_id']
                or bidkit.canonical(chapter['body_markdown']) != record['body_sha256']
                or record['writing_path'] != writing_path):
            local_errors.append('正文已变化或章节绑定不符，需重核知识引用')
        try:
            pack_file = bidkit.safe(project, record['pack']['relative_path'])
            if bidkit.digest(pack_file) != record['pack']['sha256']:
                local_errors.append('章节参考包已变化')
            else:
                pack = bidkit.read(pack_file)
                local_errors.extend(_valid_pack(project, pack))
                for citation in record['citations']:
                    candidate = next((row for row in pack['candidates']
                                      if row['knowledge_id'] == citation['knowledge_id']
                                      and row['location'] == citation['location']), None)
                    if candidate is None or candidate['source'] != citation['source']:
                        local_errors.append('引用来源与参考包不一致')
                        continue
                    if citation['purpose'] not in {'reference', 'evidence'}:
                        local_errors.append('引用用途无效')
                    if citation['purpose'] == 'evidence' and candidate['kind'] != 'evidence':
                        local_errors.append('参考资料不能充当证明材料')
                    if citation['purpose'] == 'evidence':
                        acceptance = _accepted_material(project, candidate, citation.get('material_id'))
                        if acceptance != citation.get('evidence_selection'):
                            local_errors.append('09选用记录已变化，需重核证明引用')
                    if citation['simulation'] != candidate['simulation']:
                        local_errors.append('引用模拟标识与材料不一致')
                    content = bidkit.read(bidkit.safe(project, candidate['content']['relative_path']))
                    if not any(citation['source_quote'] in block['text'] for block in content['blocks']
                               if block['location'] == citation['location']):
                        local_errors.append('引用原文已不匹配')
                    if chapter and citation['claim'] not in chapter['body_markdown']:
                        local_errors.append('引用正文不存在')
                    if citation['simulation']:
                        simulated += 1
                        warnings.append(record['section_id'] + '：采用模拟材料，仅供测试')
                    if citation['purpose'] == 'evidence':
                        proof_candidates += 1
                        warnings.append(record['section_id'] + '：证明引用仍需09核验完整原件及所有者确认')
        except (OSError, ValueError, KeyError, TypeError) as exc:
            local_errors.append(str(exc))
        if local_errors:
            affected.add(record['section_id'])
            errors.extend(record['section_id'] + '：' + error for error in local_errors)
    return {'valid': not errors, 'state': 'valid' if not errors else 'needs_review',
            'bound_chapters': len(value['chapters']), 'affected_sections': sorted(affected),
            'errors': errors, 'warnings': sorted(set(warnings)),
            'simulated_citations': simulated, 'evidence_citations': proof_candidates,
            'business_acceptance': 'NOT_TESTED'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, required=True)
    sub = parser.add_subparsers(dest='command', required=True)
    prep = sub.add_parser('prepare')
    prep.add_argument('--section', required=True)
    prep.add_argument('--query', required=True)
    prep.add_argument('--criteria', type=Path)
    prep.add_argument('--limit', type=int, default=10)
    binding = sub.add_parser('bind')
    binding.add_argument('--chapter', required=True)
    binding.add_argument('--pack', required=True)
    binding.add_argument('--usages', type=Path, required=True)
    binding.add_argument('--writing', default=WRITING)
    verify = sub.add_parser('check')
    verify.add_argument('--writing', default=WRITING)
    args = parser.parse_args()
    try:
        if args.command == 'prepare':
            value = prepare(args.project, args.section, args.query,
                            criteria=bidkit.read(args.criteria) if args.criteria else None,
                            limit=args.limit)
        elif args.command == 'bind':
            value = bind(args.project, args.chapter, args.pack, bidkit.read(args.usages),
                         writing_path=args.writing)
        else:
            value = check(args.project, writing_path=args.writing)
        print(json.dumps(value, ensure_ascii=False, indent=2))
        return 0 if value.get('valid', True) else 1
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
