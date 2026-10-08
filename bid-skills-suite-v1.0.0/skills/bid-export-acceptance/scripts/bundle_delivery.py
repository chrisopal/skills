#!/usr/bin/env python3
"""Package explicitly accepted output files, excluding internal project data."""
import argparse,json,sys,zipfile
from pathlib import Path
from bidkit import read,release_gate,safe,digest,project_id,ROOT
from validate_output import validate

def bundle(project,review,snapshot,approval,manifest,out):
    release_gate(project,review,snapshot,approval)
    payload=read(manifest);data=payload['data'];confirm=read(approval)
    schema=ROOT/'skills/bid-export-acceptance/assets/output.schema.json'
    if not schema.is_file():schema=ROOT/'assets/delivery.schema.json'
    errors=validate(payload,read(schema))
    if errors:raise ValueError('交付清单结构不合格：'+'; '.join(errors))
    if payload.get('project_id')!=project_id(project):raise ValueError('交付清单项目与工作目录不一致')
    if payload.get('skill_id')!='bid-export-acceptance' or payload.get('status')!='ready' or payload.get('blockers'):raise ValueError('不是已就绪交付清单')
    if data['delivery_status']!='ready' or not data['artifacts'] or data['remaining_actions']:raise ValueError('交付尚未完成')
    if data['signature_state']=='pending':raise ValueError('签署仍待处理')
    if data['user_release_authorization_ref']!=confirm['authorization_ref']:raise ValueError('交付授权引用不一致')
    if data['reviewed_inputs_sha256']!=confirm['snapshot_fingerprint']:raise ValueError('交付清单与输入快照不一致')
    if data['review_artifact_id']!=read(review)['artifact_id']:raise ValueError('交付清单与评审不一致')
    targets=[];names=set();project=Path(project).resolve()
    for entry in data['artifacts']:
        path=safe(project,entry['relative_path'])
        if not path.is_relative_to(project/'deliverables') or path.suffix.lower() not in {'.docx','.pdf'}:raise ValueError('交付只能包含deliverables内明确列出的DOCX/PDF')
        if entry['format']!=path.suffix[1:].lower():raise ValueError('格式声明不一致')
        if entry['text_qa']!='passed' or entry['visual_qa']!='passed':raise ValueError('成稿未完成文本与视觉检查')
        if digest(path)!=entry['sha256'] or path.stat().st_size!=entry['bytes']:raise ValueError('成稿身份变化')
        if path.name in names:raise ValueError('交付文件名重复')
        names.add(path.name);targets.append((path,entry))
    out=Path(out)
    if out.exists():raise ValueError('交付包已存在，拒绝覆盖')
    out.parent.mkdir(parents=True,exist_ok=True)
    try:
        with zipfile.ZipFile(out,'x',zipfile.ZIP_DEFLATED) as z:
            for path,entry in targets:
                content=path.read_bytes()
                import hashlib
                if hashlib.sha256(content).hexdigest()!=entry['sha256']:raise ValueError('打包期间成稿发生变化')
                z.writestr(path.name,content)
            z.writestr('delivery-files.json',json.dumps({'files':[{'filename':p.name,'sha256':e['sha256'],'bytes':e['bytes']} for p,e in targets]},ensure_ascii=False,indent=2))
        release_gate(project,review,snapshot,approval)
    except Exception:
        out.unlink(missing_ok=True);raise
    return {'package':str(out),'sha256':digest(out),'authorization_authenticity':'must be established by actual user/host, not local JSON'}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for x in ('project','review','snapshot','approval','manifest','out'):p.add_argument('--'+x,required=True)
    a=p.parse_args()
    try:print(json.dumps(bundle(a.project,a.review,a.snapshot,a.approval,a.manifest,a.out),ensure_ascii=False));return 0
    except (OSError,ValueError,KeyError) as e:print(str(e),file=sys.stderr);return 2
if __name__=='__main__':raise SystemExit(main())
