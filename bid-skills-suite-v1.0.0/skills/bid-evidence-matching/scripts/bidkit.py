#!/usr/bin/env python3
"""Local file utilities for Bid Skills. No model calls, auto approvals or uploads."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
import shutil
import sys
import tempfile
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SCOPES=('inputs','artifacts','assets','profiles')

def now():return datetime.now(timezone.utc).isoformat()
def read(path):return json.loads(Path(path).read_text(encoding='utf-8'))
def project_id(project):
    value=read(Path(project)/'work/project.json').get('project_id')
    if not isinstance(value,str) or not value.strip():raise ValueError('项目元数据缺少project_id')
    return value
def digest(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda:stream.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()
def canonical(value):return hashlib.sha256(json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def atomic(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    fd,tmp=tempfile.mkstemp(prefix='.'+path.name,dir=path.parent)
    try:
        with os.fdopen(fd,'w',encoding='utf-8') as out:json.dump(value,out,ensure_ascii=False,indent=2);out.write('\n')
        os.replace(tmp,path)
    finally:
        if os.path.exists(tmp):os.unlink(tmp)
def safe(root,relative):
    root=Path(root).resolve();p=Path(relative)
    if p.is_absolute() or '..' in p.parts:raise ValueError('路径必须在项目内：'+str(relative))
    result=(root/p).resolve()
    if not result.is_relative_to(root):raise ValueError('路径或符号链接越界')
    return result

def init_project(project,project_id):
    project=Path(project)
    if project.exists() and any(project.iterdir()):raise ValueError('目标目录非空，拒绝覆盖')
    project.mkdir(parents=True,exist_ok=True)
    for d in (*SCOPES,'reviews','deliverables','confirmations','work'): (project/d).mkdir()
    atomic(project/'work/project.json',{'project_id':project_id,'created_at':now(),'mode':'full','notes':'单写入者工作目录；不提供用户鉴权或数据库级并发控制。'})
    atomic(project/'inputs/source-registry.json',{'sources':[]})
    (project/'.gitignore').write_text('*\n!.gitignore\n',encoding='utf-8')
    return {'created':str(project.resolve()),'project_id':project_id}

def register_source(project,file,role):
    project=Path(project).resolve();file=Path(file).resolve()
    if not file.is_file():raise ValueError('原件不存在')
    registry=project/'inputs/source-registry.json'
    if not registry.is_file():raise ValueError('先执行init')
    lock=project/'work/.register.lock'
    try:fd=os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
    except FileExistsError:raise ValueError('已有注册进程；确认无活动进程后人工检查锁')
    dest=None;created=False
    try:
        os.close(fd);data=read(registry)
        sid=f"SRC-{len(data['sources'])+1:03d}"
        filename=sid+'-'+file.name
        dest=safe(project,'inputs/'+filename)
        if dest.exists():raise ValueError('目标文件已存在')
        with file.open('rb') as src,dest.open('xb') as out:
            created=True
            shutil.copyfileobj(src,out)
        row={'source_id':sid,'revision':1,'relative_path':dest.relative_to(project).as_posix(),'sha256':digest(dest),'bytes':dest.stat().st_size,'role':role,'registered_at':now()}
        data['sources'].append(row);atomic(registry,data)
        return row
    except Exception:
        if created and dest is not None and dest.exists():dest.unlink()
        raise
    finally:lock.unlink(missing_ok=True)

def scan_content(project):
    project=Path(project).resolve();files=[]
    for scope in SCOPES:
        directory=safe(project,scope)
        if not directory.is_dir():raise ValueError('缺少内容目录：'+scope)
        for path in sorted(directory.rglob('*')):
            if path.is_symlink():raise ValueError('内容快照不接收符号链接：'+str(path))
            if path.is_file():
                files.append({'relative_path':path.relative_to(project).as_posix(),'sha256':digest(path),'bytes':path.stat().st_size})
    return files

def snapshot(project,out):
    project=Path(project).resolve();target=safe(project,out)
    if any(target.is_relative_to(project/x) for x in SCOPES):raise ValueError('快照必须写入reviews或work，不能写入被覆盖内容目录')
    files=scan_content(project)
    if not files:raise ValueError('没有可记录内容')
    value={'schema_version':'1.0','project_id':project_id(project),'created_at':now(),'scopes':list(SCOPES),'files':files,'fingerprint':canonical(files)}
    atomic(target,value);return value

def verify_snapshot(project,snapshot_path):
    saved=read(snapshot_path)
    if saved.get('project_id')!=project_id(project):raise ValueError('快照项目与工作目录不一致')
    if saved.get('scopes')!=list(SCOPES):raise ValueError('快照范围与工具约定不一致')
    if canonical(saved.get('files'))!=saved.get('fingerprint'):raise ValueError('快照自身指纹不匹配')
    current=scan_content(project)
    old={x['relative_path']:x['sha256'] for x in saved['files']};new={x['relative_path']:x['sha256'] for x in current}
    changed=sorted(k for k in set(old)|set(new) if old.get(k)!=new.get(k))
    return {'current':not changed,'changed':changed,'fingerprint':saved['fingerprint'],'scope_note':'covers inputs/artifacts/assets/profiles, including newly added files'}

def scoring_check(payload):
    data=payload.get('data',payload);items=data['items'];errors=[];manual=[]
    by={x['id']:x for x in items}
    if len(by)!=len(items):errors.append('重复评分ID')
    for row in items:
        parent=row['parent_id']
        if parent and parent not in by:errors.append(row['id']+': 父ID不存在')
        seen=set();cur=row
        while cur and cur['parent_id']:
            if cur['id'] in seen:errors.append(row['id']+': 层级循环');break
            seen.add(cur['id']);cur=by.get(cur['parent_id'])
        children=[x for x in items if x['parent_id']==row['id']]
        if row['node_type']=='scored' and children:errors.append(row['id']+': 计分叶子含子项')
        if row['node_type']=='rollup':
            if not children:errors.append(row['id']+': 汇总节点无子项')
            elif row['aggregation']=='sum' and row['max_score'] is not None and all(c['max_score'] is not None for c in children):
                if sum(Decimal(str(c['max_score'])) for c in children)!=Decimal(str(row['max_score'])):errors.append(row['id']+': 直接子项合计不一致')
            else:manual.append(row['id']+': 非简单加和或分值未知，需按原文核验')
    roots=[x for x in items if not x['parent_id']]
    total=data.get('declared_total')
    if any(x['aggregation'] in {'max','capped','manual'} for x in items):
        manual.append('含非加和规则，总分需要按原文人工核验')
    elif total is not None and roots and all(x['max_score'] is not None for x in roots):
        if sum(Decimal(str(x['max_score'])) for x in roots)!=Decimal(str(total)):errors.append('根项最高分合计与声明总分不一致（需核验是否允许加总）')
    else:manual.append('总分或根项分值未完整，不能自动核对')
    return {'arithmetic_valid':not errors,'errors':errors,'manual_checks':manual,'business_acceptance':'NOT_TESTED'}

def coverage_check(requirements,scoring,compliance,outline):
    req=read(requirements)['data']['requirements'];score=read(scoring)['data']['items'];comp=read(compliance)['data']['rules'];sections=read(outline)['data']['sections']
    ids={x['id'] for x in sections};errors=[]
    if len(ids)!=len(sections):errors.append('重复章节ID')
    by={x['id']:x for x in sections}
    for x in sections:
        if x['parent_id'] and x['parent_id'] not in ids:errors.append(x['id']+': 父章节不存在')
        seen=set();cur=x
        while cur and cur['parent_id']:
            if cur['id'] in seen:errors.append(x['id']+': 目录循环');break
            seen.add(cur['id']);cur=by.get(cur['parent_id'])
    required={x['id'] for x in req if x['mandatory']=='yes'}|{x['id'] for x in score if x['node_type']=='scored'}|{x['id'] for x in comp if x['fatal'] is True or x['kind']=='qualification'}
    mapped={i for x in sections for key in ('requirement_ids','scoring_ids','compliance_ids') for i in x[key]}
    known={x['id'] for x in req+score+comp}
    missing=sorted(required-mapped);unknown=sorted(mapped-known)
    if missing:errors.append('必需映射缺失：'+','.join(missing))
    if unknown:errors.append('映射ID不存在：'+','.join(unknown))
    return {'mapping_valid':not errors,'errors':errors,'missing':missing,'note':'只检查ID映射，不判断正文是否真正满足或客户目录是否完整。'}

def compose_profiles(paths,out):
    profiles=[read(p) for p in paths];seen=set()
    for x in profiles:
        key=(x['type'],x['id'])
        if key in seen:raise ValueError('重复配置：'+str(key))
        seen.add(key)
        if x.get('readiness')!='seed_requires_project_validation':raise ValueError('本版只接受明确标记的配置种子')
    result={'schema_version':'1.0','profiles':profiles,'merge_policy':'namespaced_no_override','status':'needs_review','notes':['各命名空间并列保留；冲突必须人工裁决。','规则种子不形成项目事实、不替代适用法规核验。']}
    atomic(out,result);return result

def release_gate(project,review_path,snapshot_path,approval_path):
    expected_project_id=project_id(project)
    current=verify_snapshot(project,snapshot_path)
    if not current['current']:raise ValueError('评审已过期：'+','.join(current['changed']))
    review=read(review_path);d=review.get('data',{})
    from validate_output import validate
    schema_file=ROOT/'skills/bid-review-remediation/assets/output.schema.json'
    if not schema_file.is_file():schema_file=ROOT/'assets/review.schema.json'
    schema_errors=validate(review,read(schema_file))
    if schema_errors:raise ValueError('评审结构不合格：'+'; '.join(schema_errors))
    if review.get('skill_id')!='bid-review-remediation':raise ValueError('不是评审产物')
    if review.get('project_id')!=expected_project_id:raise ValueError('评审项目与工作目录不一致')
    if review.get('status')!='ready' or review.get('blockers'):raise ValueError('评审尚未ready')
    if d.get('review_scope')!='full' or d.get('release_recommendation')!='eligible_for_user_release':raise ValueError('不具备完整交付建议')
    if d.get('reviewed_inputs_sha256')!=current['fingerprint']:raise ValueError('评审未绑定此快照')
    if not d.get('human_approval_ref'):raise ValueError('缺人工评审确认引用')
    if any(x.get('state')=='open' or (x.get('severity')=='blocking' and x.get('state')!='resolved') for x in d.get('findings',[])):raise ValueError('尚有未解决或未处置发现')
    checks=d.get('checks',[])
    if not checks or any(x.get('state') not in {'passed','not_applicable'} for x in checks):raise ValueError('评审检查未全部完成')
    approval=read(approval_path)
    if approval.get('project_id')!=expected_project_id:raise ValueError('确认记录项目与工作目录不一致')
    for k in ('actor','decided_at','authorization_ref'):
        if not str(approval.get(k) or '').strip():raise ValueError('确认记录缺字段：'+k)
    if approval.get('decision')!='approved' or approval.get('review_sha256')!=digest(review_path) or approval.get('snapshot_fingerprint')!=current['fingerprint']:raise ValueError('确认记录不对应当前评审和输入')
    return {'mechanical_gate':'passed','authorization_authenticity':'NOT_VERIFIED_BY_OFFLINE_TOOL','notice':'本地JSON不能认证签批人身份；真实授权须由宿主审计或实际用户确认。'}

def main():
    parser=argparse.ArgumentParser(description=__doc__);sub=parser.add_subparsers(dest='command',required=True)
    p=sub.add_parser('init');p.add_argument('--project',required=True);p.add_argument('--project-id',required=True)
    p=sub.add_parser('register-source');p.add_argument('--project',required=True);p.add_argument('--file',required=True);p.add_argument('--role',choices=['main','technical','commercial','clarification','addendum','supplier','unknown'],default='unknown')
    p=sub.add_parser('snapshot');p.add_argument('--project',required=True);p.add_argument('--out',default='reviews/input-snapshot.json')
    p=sub.add_parser('verify-snapshot');p.add_argument('--project',required=True);p.add_argument('--snapshot',required=True)
    p=sub.add_parser('scoring-check');p.add_argument('--file',required=True)
    p=sub.add_parser('coverage-check');[p.add_argument('--'+x,required=True) for x in ('requirements','scoring','compliance','outline')]
    p=sub.add_parser('compose-profiles');p.add_argument('--packs',nargs='+',required=True);p.add_argument('--out',required=True)
    p=sub.add_parser('check-release');[p.add_argument('--'+x,required=True) for x in ('project','review','snapshot','approval')]
    p=sub.add_parser('impact');p.add_argument('--skill-id',required=True)
    args=parser.parse_args()
    try:
        if args.command=='init':result=init_project(args.project,args.project_id)
        elif args.command=='register-source':result=register_source(args.project,args.file,args.role)
        elif args.command=='snapshot':result=snapshot(args.project,args.out)
        elif args.command=='verify-snapshot':result=verify_snapshot(args.project,args.snapshot)
        elif args.command=='scoring-check':result=scoring_check(read(args.file))
        elif args.command=='coverage-check':result=coverage_check(args.requirements,args.scoring,args.compliance,args.outline)
        elif args.command=='compose-profiles':result=compose_profiles(args.packs,args.out)
        elif args.command=='check-release':result=release_gate(args.project,args.review,args.snapshot,args.approval)
        elif args.command=='impact':
            registry=read(ROOT/'registry.json');children={x['id']:set() for x in registry['skills']}
            if args.skill_id not in children:raise ValueError('未知skill_id')
            for x in registry['skills']:
                for dep in x['depends_on']:children[dep].add(x['id'])
            pending=list(children[args.skill_id]);affected=set()
            while pending:
                x=pending.pop()
                if x not in affected:affected.add(x);pending.extend(children[x])
            result={'changed':args.skill_id,'recheck_skills':sorted(affected),'state_mutated':False}
        print(json.dumps(result,ensure_ascii=False,indent=2))
        if result.get('current') is False or result.get('arithmetic_valid') is False or result.get('mapping_valid') is False:return 1
        return 0
    except (OSError,ValueError,KeyError,TypeError) as exc:
        print(json.dumps({'error':str(exc)},ensure_ascii=False),file=sys.stderr);return 2
if __name__=='__main__':raise SystemExit(main())
