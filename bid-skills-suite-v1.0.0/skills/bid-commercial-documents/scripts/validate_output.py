#!/usr/bin/env python3
"""Validate a skill output locally. This does not certify factual correctness."""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

def validate(payload: dict, schema: dict) -> list[str]:
    try:
        from jsonschema import Draft202012Validator, FormatChecker
    except ImportError as exc:
        raise RuntimeError('缺少 jsonschema：python -m pip install "jsonschema>=4.23,<5"') from exc
    Draft202012Validator.check_schema(schema)
    errors = [f"{'.'.join(map(str,e.absolute_path)) or '$'}: {e.message}" for e in Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(payload)]
    if errors:
        return errors
    if payload['status'] == 'ready' and payload['blockers']:
        errors.append('ready 与非空 blockers 冲突')
    def walk(value, path='$'):
        if isinstance(value, dict):
            if value.get('basis_type') == 'explicit' and 'sources' in value and not value['sources']:
                errors.append(path + ': explicit事实必须有来源')
            if value.get('state') in {'accepted','confirmed','accepted_warning','resolved'} and 'confirmation_ref' in value and not value['confirmation_ref']:
                errors.append(path + ': 确认/采纳/关闭必须引用实际确认或复核记录')
            for k,v in value.items():walk(v,path+'.'+k)
        elif isinstance(value,list):
            for i,v in enumerate(value):walk(v,f'{path}[{i}]')
    walk(payload['data'])
    data=payload['data']; skill=payload['skill_id']
    if skill=='bid-source-intake' and data['coverage']=='complete':
        if not data['documents'] or any(x['status']!='parsed' for x in data['documents']):
            errors.append('完整解析必须具有全部已解析原件')
        if any(x['status'] not in {'processed','blank_verified'} for x in data['page_audit']):
            errors.append('完整解析与未处理/待复核页面冲突')
    for key in ('requirements','items','rules','formats','sections','materials','decisions','chapters','forms','figures','findings'):
        items=data.get(key)
        if isinstance(items,list):
            ids=[x.get('id') for x in items if isinstance(x,dict) and 'id' in x]
            if len(ids)!=len(set(ids)):errors.append(f'{key}: ID重复')
    if skill=='bid-evidence-matching':
        mids={m['id'] for m in data['materials']}
        for row in data['selections']:
            if set(row['material_ids'])-mids:errors.append(row['id']+': 素材ID不存在')
            if row['state']=='accepted' and (row['independent_count']<row['required_count'] or not row['material_ids']):
                errors.append(row['id']+': 被接受的选用未满足独立证明数量')
    if skill=='bid-requirements':
        requirement_ids={row['id'] for row in data['requirements']}
        for conflict in data['conflicts']:
            if set(conflict['requirement_ids'])-requirement_ids:
                errors.append(conflict['id']+': 冲突引用不存在的需求ID')
    if skill=='bid-review-remediation' and data['release_recommendation']=='eligible_for_user_release':
        if data['review_scope']!='full' or payload['status']!='ready' or not data['human_approval_ref']:
            errors.append('交付建议必须基于完整范围、ready状态与人工审核记录')
        if any(x['severity']=='blocking' and x['state']!='resolved' for x in data['findings']):errors.append('尚有阻塞项未解决')
        if any(x['state']=='open' for x in data['findings']):errors.append('交付建议仍存在未处置发现')
        if not data['checks'] or any(x['state'] not in {'passed','not_applicable'} for x in data['checks']):errors.append('评审检查未完成')
    return errors

def main() -> int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('file',type=Path)
    p.add_argument('--schema',type=Path,default=Path(__file__).resolve().parents[1]/'assets/output.schema.json')
    args=p.parse_args()
    try:
        payload=json.loads(args.file.read_text(encoding='utf-8'))
        schema=json.loads(args.schema.read_text(encoding='utf-8'))
        errors=validate(payload,schema)
        print(json.dumps({'schema_valid':not errors,'business_acceptance':'NOT_TESTED','errors':errors},ensure_ascii=False,indent=2))
        return 1 if errors else 0
    except (OSError,ValueError,RuntimeError) as exc:
        print(json.dumps({'error':str(exc)},ensure_ascii=False),file=sys.stderr);return 2
if __name__=='__main__':raise SystemExit(main())
