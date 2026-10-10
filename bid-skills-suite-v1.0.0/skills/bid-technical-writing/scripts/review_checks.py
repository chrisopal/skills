#!/usr/bin/env python3
"""Prepare unknown item reviews and verify their actual input/evidence bindings.

A reviewer supplies semantic conclusions; this tool never predicts expert scores or approves.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import bidkit

MATERIAL_DIMENSIONS = ('subject', 'validity', 'scope', 'independent_count',
                       'required_pages', 'signature', 'inclusion', 'authenticity')
STAGES = {'scoring': ('04-scoring.json', 'items'),
          'compliance': ('05-compliance.json', 'rules'),
          'materials': ('09-evidence-selection.json', 'selections')}


def load_inputs(project):
    pid = bidkit.project_id(project)
    stages = {}
    files = {}
    for area, (name, key) in STAGES.items():
        rel = 'artifacts/' + name
        payload = bidkit.read(bidkit.safe(project, rel))
        if payload.get('project_id') != pid:
            raise ValueError(name + ': 项目身份不一致')
        rows = payload['data'][key]
        if len({x['id'] for x in rows}) != len(rows):
            raise ValueError(name + ': 上游ID重复')
        stages[area] = {x['id']: x for x in rows
                        if area != 'scoring' or x.get('node_type') == 'scored'}
        files[rel] = bidkit.digest(bidkit.safe(project, rel))
        if area == 'materials':
            stages['material_sources'] = {m['id']: m for m in payload['data']['materials']}
    return stages, files


def prepare(project):
    project = Path(project).resolve()
    stages, _ = load_inputs(project)
    matrix = {}
    for area in STAGES:
        matrix[area] = []
        for ident, upstream in stages[area].items():
            sources = upstream.get('sources', [])
            mids = upstream.get('material_ids', [])
            if area == 'materials':
                sources = [s for mid in mids for s in
                           stages['material_sources'].get(mid, {}).get('sources', [])]
            matrix[area].append({
                'target_id': ident, 'conclusion': 'unknown',
                'rationale': '尚未逐项核验原文条件、正文及完整证明材料。',
                'sources': sources, 'bid_refs': [], 'material_ids': mids,
                'dimensions': {d: 'unknown' for d in MATERIAL_DIMENSIONS}
                              if area == 'materials' else {},
                'dimension_exemptions': {},
                'score_estimate': None, 'finding_ids': [],
            })
    return {'project_id': bidkit.project_id(project), 'status': 'needs_review',
            'core_matrix': matrix, 'semantic_acceptance': 'NOT_RUN',
            'notice': '计划不是评审结论；逐项读原文和证据后填入15-review.data.core_matrix。'}


def reference_text(project, reference):
    path = bidkit.safe(project, reference['relative_path'])
    if not path.is_file() or bidkit.digest(path) != reference['sha256']:
        raise ValueError('正文引用不存在或哈希过期')
    if not reference['relative_path'].startswith('artifacts/'):
        raise ValueError('正文引用必须指向实际artifacts正文，不能引用评审自证')
    if not path.name.startswith(('11-', '12-', '14-')):
        raise ValueError('正文引用不能用需求或评分原文自证响应')
    location = reference['location']
    if path.suffix == '.json':
        if not location.startswith('/'):
            raise ValueError('JSON正文定位必须是具体文本的JSON Pointer')
        value = bidkit.read(path)
        for part in location[1:].split('/'):
            part = part.replace('~1', '/').replace('~0', '~')
            value = value[int(part)] if isinstance(value, list) else value[part]
        if not isinstance(value, str):
            raise ValueError('正文定位必须指向具体文本，不能使用整个JSON自证')
    elif path.suffix in {'.md', '.txt'}:
        match = re.fullmatch(r'L(\d+)(?:-L?(\d+))?', location)
        if not match:
            raise ValueError('文本正文定位必须是实际行号')
        lines = path.read_text(encoding='utf-8').splitlines()
        first, last = int(match[1]), int(match[2] or match[1])
        if not 1 <= first <= last <= len(lines):
            raise ValueError('正文行号超出实际范围')
        value = '\n'.join(lines[first - 1:last])
    else:
        raise ValueError('正文引用仅支持可定位的JSON/Markdown/文本；其他格式由宿主回读')
    if reference['quote'] not in value:
        raise ValueError('正文引用文字不在指定位置')
    return value


def source_text(project, source, cache):
    registry = bidkit.read(bidkit.safe(project, 'inputs/source-registry.json'))
    candidates = [s for s in registry['sources'] if s['source_id'] == source['source_id']
                  and s['revision'] == source['revision']]
    if len(candidates) != 1:
        raise ValueError('证据来源身份不存在或重复')
    registered = candidates[0]
    path = bidkit.safe(project, registered['relative_path'])
    if source['sha256'] != registered['sha256'] or bidkit.digest(path) != source['sha256']:
        raise ValueError('证据原件哈希过期')
    key = (source['source_id'], source['location'])
    if key not in cache:
        if path.suffix.lower() == '.pdf':
            match = re.fullmatch(r'P(\d+)(?:[-–]P?(\d+))?', source['location'])
            if not match:
                raise ValueError('PDF证据需精确页码，图像证据须由宿主OCR核验')
            try:
                import fitz
            except ImportError as exc:
                raise ValueError('PDF原件读取依赖PyMuPDF未配置，需宿主核验，不能自动通过') from exc
            with fitz.open(path) as doc:
                first, last = int(match[1]), int(match[2] or match[1])
                if not 1 <= first <= last <= len(doc):
                    raise ValueError('证据页码超出原件范围')
                cache[key] = '\n'.join(doc[i].get_text() for i in range(first - 1, last))
        elif path.suffix.lower() in {'.md', '.txt'}:
            text = path.read_text(encoding='utf-8')
            match = re.fullmatch(r'L(\d+)(?:-L?(\d+))?', source['location'])
            if match:
                lines = text.splitlines()
                first, last = int(match[1]), int(match[2] or match[1])
                if not 1 <= first <= last <= len(lines):
                    raise ValueError('证据行号超出原件范围')
                text = '\n'.join(lines[first - 1:last])
            elif source['location'] not in {'full_text', '完整Markdown材料（已回读）'}:
                raise ValueError('文本证据需要实际行号或明确full_text')
            cache[key] = text
        else:
            raise ValueError('此证据原件需宿主解析回读，不能自动标核验通过')
    normalize = lambda value: re.sub(r'\s+', '', value)
    if normalize(source['quote']) not in normalize(cache[key]):
        raise ValueError('证据引文不在原件指定位置')


def check(project, review, snapshot_path):
    project = Path(project).resolve()
    errors, blockers, warnings = [], [], []
    from validate_output import validate
    schema_path = bidkit.ROOT / 'skills/bid-review-remediation/assets/output.schema.json'
    if not schema_path.is_file():
        schema_path = bidkit.ROOT / 'assets/review.schema.json'
    schema_errors = validate(review, bidkit.read(schema_path))
    if schema_errors:
        return {'current': False, 'matrix_complete': False, 'errors': schema_errors,
                'release_blockers': ['评审结构无效'], 'warnings': [], 'counts': {},
                'semantic_acceptance': 'NOT_RUN', 'formal_release_ready': False}
    current = bidkit.verify_snapshot(project, snapshot_path)
    if not current['current']:
        errors.append('评审已过期：' + ','.join(current['changed']))
    if review.get('project_id') != bidkit.project_id(project):
        errors.append('评审项目身份不一致')
    data = review.get('data', {})
    if data.get('reviewed_inputs_sha256') != current['fingerprint']:
        errors.append('评审未绑定此输入快照')
    stages, files = load_inputs(project)
    bound = {x['relative_path']: x['sha256'] for x in review.get('inputs', [])}
    for rel, sha in files.items():
        if bound.get(rel) != sha:
            errors.append(rel + ': 评审未绑定当前上游')
    matrix = data.get('core_matrix', {})
    findings = {x['id']: x for x in data.get('findings', [])}
    materials = stages['material_sources']
    fatal_ids = {x['id'] for x in stages['compliance'].values()
                 if x.get('fatal') is True or x.get('kind') in {'qualification', 'rejection'}}
    proof_targets = {x['id'] for x in stages['compliance'].values()
                     if x.get('kind') == 'qualification' or x.get('material_required') is True}
    for rule in stages['compliance'].values():
        if rule.get('kind') == 'rejection' and rule.get('fatal') is not True:
            errors.append(rule['id'] + ': 否决类别与明确后果不一致，须回查原文分类')
    requirements_path = project / 'artifacts/03-requirements.json'
    mandatory_ids = set()
    if requirements_path.is_file():
        requirements = bidkit.read(requirements_path)
        if requirements.get('project_id') != bidkit.project_id(project):
            errors.append('需求矩阵项目身份不一致')
        mandatory_ids = {x['id'] for x in requirements['data']['requirements']
                         if x.get('mandatory') == 'yes'}
        proof_targets |= {x['id'] for x in requirements['data']['requirements']
                          if x.get('mandatory') == 'yes' and x.get('material_required') is True}
        if bound.get('artifacts/03-requirements.json') != bidkit.digest(requirements_path):
            errors.append('需求矩阵未绑定当前评审inputs')
    material_targets = {t for selection in stages['materials'].values()
                        for t in selection.get('target_ids', [])}
    not_applicable_targets = set()
    cache = {}
    for area in STAGES:
        rows = matrix.get(area, [])
        ids = [x.get('target_id') for x in rows]
        if len(ids) != len(set(ids)):
            errors.append(area + ': 逐项结论ID重复')
        missing, extra = set(stages[area]) - set(ids), set(ids) - set(stages[area])
        if missing:
            errors.append(area + ': 漏审 ' + ','.join(sorted(missing)))
        if extra:
            errors.append(area + ': 未知目标 ' + ','.join(sorted(extra)))
        for row in rows:
            ident = row.get('target_id')
            upstream = stages[area].get(ident)
            if upstream is None:
                continue
            if not row.get('rationale', '').strip():
                errors.append(ident + ': 缺少判断理由')
            expected_sources = upstream.get('sources', [])
            mids = row.get('material_ids', [])
            if area == 'materials':
                if set(mids) != set(upstream['material_ids']):
                    errors.append(ident + ': 材料集合与当前选用不一致')
                expected_sources = [s for mid in mids for s in
                                    materials.get(mid, {}).get('sources', [])]
            if not row.get('sources') or any(s not in row['sources'] for s in expected_sources):
                errors.append(ident + ': 缺少完整原文/材料依据')
            for source in row.get('sources', []):
                try:
                    source_text(project, source, cache)
                except (OSError, ValueError, KeyError, IndexError) as exc:
                    errors.append(ident + ': ' + str(exc))
            for mid in mids:
                if mid not in materials:
                    errors.append(ident + ': 材料ID不存在 ' + mid)
            for ref in row.get('bid_refs', []):
                try:
                    reference_text(project, ref)
                    if bound.get(ref['relative_path']) != ref['sha256']:
                        errors.append(ident + ': 正文引用未纳入评审inputs')
                except (OSError, ValueError, KeyError, IndexError) as exc:
                    errors.append(ident + ': ' + str(exc))
            conclusion = row.get('conclusion')
            if conclusion in {'satisfied', 'partial'} and not row.get('bid_refs'):
                errors.append(ident + ': 已响应结论缺少实际正文定位')
            if conclusion not in {'satisfied', 'partial', 'missing', 'unknown', 'not_applicable'}:
                errors.append(ident + ': 结论无效')
            critical = area == 'compliance' and ident in fatal_ids
            if area == 'materials':
                critical = bool(set(upstream.get('target_ids', [])) & (fatal_ids | mandatory_ids))
                dimensions = row.get('dimensions', {})
                if set(dimensions) != set(MATERIAL_DIMENSIONS):
                    errors.append(ident + ': 材料逐维检查不完整')
                exemptions = row.get('dimension_exemptions', {})
                for dimension in MATERIAL_DIMENSIONS:
                    if dimensions.get(dimension) != 'not_applicable':
                        continue
                    exemption = exemptions.get(dimension)
                    if not exemption:
                        errors.append(ident + ': 不适用维度缺少原文适用性复核 ' + dimension)
                        continue
                    path = bidkit.safe(project, exemption['relative_path'])
                    if (not path.is_file() or bidkit.digest(path) != exemption['sha256']
                            or bound.get(exemption['relative_path']) != exemption['sha256']):
                        errors.append(ident + ': 维度适用性复核缺失/过期或未绑定 ' + dimension)
                incomplete = [d for d in MATERIAL_DIMENSIONS
                              if dimensions.get(d) not in {'passed', 'not_applicable'}]
                if incomplete:
                    (blockers if critical else warnings).append(ident + ': 材料未满足 ' + ','.join(incomplete))
                if conclusion == 'satisfied' and incomplete:
                    errors.append(ident + ': 满足结论与材料检查冲突')
                if upstream.get('independent_count', 0) < upstream.get('required_count', 0):
                    (blockers if critical else warnings).append(ident + ': 独立材料数量不足')
                    if conclusion == 'satisfied':
                        errors.append(ident + ': 满足结论与独立数量不足冲突')
                # Pages/files of the same registered original are one evidence item.
                independent = {s['sha256'] for mid in mids for s in
                               materials.get(mid, {}).get('sources', [])}
                if len(independent) < upstream.get('required_count', 0):
                    (blockers if critical else warnings).append(ident + ': 同一证明重复计数')
                    if conclusion == 'satisfied':
                        errors.append(ident + ': 满足结论与重复证明冲突')
                if upstream.get('required_count', 0) > 1:
                    identities = {materials.get(mid, {}).get('independent_evidence_id') for mid in mids}
                    if None in identities or '' in identities:
                        errors.append(ident + ': 多份独立证明需登记合同/证书身份，不能按文件数计')
                    elif len(identities) < upstream['required_count']:
                        (blockers if critical else warnings).append(ident + ': 相同合同/证书身份重复计数')
                        if conclusion == 'satisfied':
                            errors.append(ident + ': 满足结论与独立证明身份冲突')
                if upstream.get('state') != 'accepted':
                    (blockers if critical else warnings).append(ident + ': 选用尚未核实适用')
            if any(s.get('kind') == 'synthetic' for mid in mids
                   for s in materials.get(mid, {}).get('sources', [])):
                blockers.append(ident + ': 模拟材料不能支持正式资格/交付')
            if critical and conclusion != 'satisfied':
                blockers.append(ident + ': 关键条件未满足或仍待核验')
            elif conclusion in {'partial', 'missing', 'unknown'}:
                warnings.append(ident + ': 尚有评分/响应缺口 ' + str(conclusion))
                if area == 'scoring' and conclusion == 'unknown':
                    blockers.append(ident + ': 尚未完成评分条件逐项评审')
            if conclusion != 'satisfied':
                linked = [findings.get(fid) for fid in row.get('finding_ids', [])]
                if not linked or any(f is None or ident not in f.get('related_ids', []) for f in linked):
                    errors.append(ident + ': 非满足结论须关联有依据的发现或适用性复核')
                elif conclusion == 'not_applicable':
                    # N/A requires an actual applicability review, not a blanket skip.
                    valid = True
                    for finding in linked:
                        if finding.get('state') != 'resolved' or not finding.get('confirmation_ref'):
                            errors.append(ident + ': 不适用须有已复核的适用性结论')
                            valid = False
                            continue
                        confirmation = bidkit.safe(project, finding['confirmation_ref'])
                        if (not confirmation.is_file()
                                or bound.get(finding['confirmation_ref']) != bidkit.digest(confirmation)):
                            errors.append(ident + ': 适用性复核记录不存在/过期或未绑定')
                            valid = False
                    if valid:
                        not_applicable_targets.add(ident)
                        blockers = [b for b in blockers if b != ident + ': 关键条件未满足或仍待核验']
            estimate = row.get('score_estimate')
            if estimate is not None:
                maximum = upstream.get('max_score')
                if (area != 'scoring' or isinstance(estimate, bool)
                        or not isinstance(estimate, (float, int)) or estimate < 0
                        or maximum is None or estimate > maximum):
                    errors.append(ident + ': 得分超界或非评分项填写得分')
                else:
                    warnings.append(ident + ': 自评分值需另有原规则计算/假设记录，不代表评委评分')
    for missing_target in sorted(proof_targets - material_targets - not_applicable_targets):
        blockers.append(missing_target + ': 上游漏建资格/必需证明材料选用组')
    from writing_policy import check_project_policy
    try:
        writing_policy = check_project_policy(project)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        writing_policy = {'passed': False, 'blocking_issues': ['写作策略无法检查：' + str(exc)]}
    blockers.extend(writing_policy['blocking_issues'])
    warnings.extend(writing_policy.get('recommendation_issues', []))
    quality_gate = {'quality_gate': 'NOT_RUN', 'errors': [], 'blockers': [],
                    'warnings': [], 'semantic_acceptance': 'NOT_RUN',
                    'binding_ready': False,
                    'notice': '未发现profiles/quality-plan.json；质量闭环未运行。'}
    quality_plan = project / 'profiles/quality-plan.json'
    if quality_plan.is_file():
        quality_ref = data.get('quality_review_ref')
        try:
            if not isinstance(quality_ref, dict):
                raise ValueError('存在质量计划但15评审缺少data.quality_review_ref')
            quality_path = bidkit.safe(project, quality_ref['relative_path'])
            if (not str(quality_ref['relative_path']).startswith('reviews/')
                    or quality_path.name != 'quality-review.json'):
                raise ValueError('质量评审必须是reviews/quality-review.json')
            if not quality_path.is_file() or bidkit.digest(quality_path) != quality_ref['sha256']:
                raise ValueError('15质量评审引用不存在或哈希过期')
            import quality_checks
            quality_gate = quality_checks.check(project, quality_path, quality_plan)
        except (OSError, ValueError, KeyError, TypeError) as exc:
            quality_gate = {'quality_gate': 'BLOCKED', 'errors': [str(exc)],
                            'blockers': [], 'warnings': [],
                            'semantic_acceptance': 'NOT_RUN',
                            'binding_ready': False}
        errors.extend(quality_gate.get('errors', []))
        blockers.extend(quality_gate.get('blockers', []))
        warnings.extend(quality_gate.get('warnings', []))
    return {'current': current['current'], 'matrix_complete': not errors,
            'writing_policy': writing_policy,
            'errors': errors, 'release_blockers': list(dict.fromkeys(blockers)),
            'warnings': list(dict.fromkeys(warnings)),
            'counts': {a: len(stages[a]) for a in STAGES},
            'semantic_acceptance': 'REVIEWER_SUPPLIED_NOT_CERTIFIED_BY_SCRIPT',
            'formal_release_ready': not errors and not blockers,
            'quality_gate': quality_gate.get('quality_gate', 'NOT_RUN'),
            'quality_check': quality_gate}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    p = sub.add_parser('prepare')
    p.add_argument('--project', type=Path, required=True)
    p.add_argument('--out', default='reviews/core-review-plan.json')
    p = sub.add_parser('check')
    p.add_argument('--project', type=Path, required=True)
    p.add_argument('--review', type=Path, required=True)
    p.add_argument('--snapshot', type=Path, required=True)
    p.add_argument('--out')
    args = parser.parse_args()
    try:
        if args.command == 'prepare':
            result = prepare(args.project)
            destination = bidkit.safe(args.project, args.out)
            if destination.exists():
                raise ValueError('拒绝覆盖既有评审计划，请使用新版本')
            if not destination.is_relative_to(args.project.resolve() / 'reviews'):
                raise ValueError('评审计划须放reviews，避免改变输入快照')
            bidkit.atomic(destination, result)
        else:
            result = check(args.project, bidkit.read(args.review), args.snapshot)
            if args.out:
                destination = bidkit.safe(args.project, args.out)
                if not destination.is_relative_to(args.project.resolve() / 'reviews'):
                    raise ValueError('校验回执须放reviews')
                bidkit.atomic(destination, result)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if args.command == 'prepare' or result['formal_release_ready'] else 1
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(json.dumps({'error': str(exc)}, ensure_ascii=False))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
