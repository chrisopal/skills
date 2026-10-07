#!/usr/bin/env python3
"""Check local skill metadata, schemas, template examples, links, and safe bundle contents."""
from __future__ import annotations
import json,re,sys,zipfile
from pathlib import Path
import yaml
from validate_output import validate
from refresh_distribution import DISTRIBUTED_SCRIPTS, DISTRIBUTED_DOCS, DISTRIBUTED_ASSET_DIRS
ROOT=Path(__file__).resolve().parents[1]

def check_installable_zips(root, registry):
    directory=root/'installable-zips'
    archives=sorted(directory.glob('*.zip')) if directory.is_dir() else []
    if not archives:return []
    errors=[]
    expected={f"{item['sequence']:02d}-{item['id']}.zip" for item in registry['skills']}
    if {p.name for p in archives}!=expected:errors.append('单技能ZIP集合与registry不一致')
    for archive in archives:
        skill_id=archive.stem.split('-',1)[-1]
        source=root/'skills'/skill_id
        if not source.is_dir():continue
        files={f'{skill_id}/{p.relative_to(source).as_posix()}':p.read_bytes() for p in source.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc'}
        try:
            with zipfile.ZipFile(archive) as z:
                names=z.namelist()
                if len(names)!=len(set(names)) or set(names)!=set(files):errors.append(archive.name+': 文件清单与技能目录不一致');continue
                if any(z.read(name)!=content for name,content in files.items()):errors.append(archive.name+': 内容与技能目录不一致')
        except (OSError,zipfile.BadZipFile) as exc:errors.append(archive.name+': 无法读取 '+str(exc))
    return errors

def check(root=ROOT):
    errors=[];count=0
    registry=json.loads((root/'registry.json').read_text(encoding='utf-8'))
    skills=list((root/'skills').glob('*/SKILL.md'))
    if len(skills)!=17 or len(registry['skills'])!=17:errors.append('技能数量不是17')
    for file in skills:
        text=file.read_text(encoding='utf-8')
        try:meta=yaml.safe_load(text.split('---',2)[1])
        except Exception as e:errors.append(str(file)+': YAML错误 '+str(e));continue
        unsupported=set(meta)-{'name','description','license','allowed-tools','metadata'}
        if unsupported:errors.append(str(file)+': Codex不支持的frontmatter字段 '+','.join(sorted(unsupported)))
        name=meta.get('name','')
        if name!=file.parent.name or not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*',name) or len(name)>64:errors.append(str(file)+': name不合格')
        if not 1<=len(meta.get('description',''))<=1024:errors.append(name+': description长度不合格')
        if len(meta.get('compatibility',''))>500:errors.append(name+': compatibility过长')
        if any(not isinstance(v,str) for v in meta.get('metadata',{}).values()):errors.append(name+': metadata值必须是字符串')
        if len(text.splitlines())>500:errors.append(name+': SKILL.md超过500行')
        for link in re.findall(r'\]\(([^)]+)\)',text):
            if not link.startswith(('https://','http://','#')) and not (file.parent/link.split('#')[0]).is_file():errors.append(name+': 无效本地链接 '+link)
        schema=json.loads((file.parent/'assets/output.schema.json').read_text())
        for item in ('output.template.json','example.output.json'):
            count+=1
            payload=json.loads((file.parent/'assets'/item).read_text())
            errors.extend(name+'/'+item+': '+e for e in validate(payload,schema))
        for required in ('references/playbook.md','references/output-contract.md','references/evidence-and-safety.md','assets/report.template.md','tests/cases.json','scripts/validate_output.py'):
            if not (file.parent/required).is_file():errors.append(name+': 缺文件 '+required)
    if any(p.suffix.lower() in {'.ttf','.otf','.ttc','.woff','.woff2'} for p in root.rglob('*') if p.is_file()):errors.append('不允许打包字体文件')
    if any(p.is_symlink() for p in root.rglob('*')):errors.append('不允许打包符号链接')
    for skill_id, scripts in DISTRIBUTED_SCRIPTS.items():
        for script in scripts:
            local=root/'skills'/skill_id/'scripts'/script
            if not local.is_file() or (root/'scripts'/script).read_bytes()!=local.read_bytes():errors.append(skill_id+': 独立安装脚本与套件脚本不一致 '+script)
    for skill_id, docs in DISTRIBUTED_DOCS.items():
        for doc in docs:
            local=root/'skills'/skill_id/'references'/doc
            if not local.is_file() or (root/'docs'/doc).read_bytes()!=local.read_bytes():errors.append(skill_id+': 独立安装说明与套件说明不一致 '+doc)
    for skill_id, directories in DISTRIBUTED_ASSET_DIRS.items():
        for directory in directories:
            canonical=root/'assets'/directory
            local=root/'skills'/skill_id/'assets'/directory
            source_files={p.relative_to(canonical):p.read_bytes() for p in canonical.rglob('*') if p.is_file()}
            local_files={p.relative_to(local):p.read_bytes() for p in local.rglob('*') if p.is_file()}
            if source_files!=local_files:errors.append(skill_id+': 独立安装资源与套件资源不一致 '+directory)
    errors.extend(check_installable_zips(root,registry))
    return {'skills':len(skills),'schema_documents_validated':count,'errors':errors,'passed':not errors,'real_model_e2e':'NOT_RUN'}

def main():
    result=check();print(json.dumps(result,ensure_ascii=False,indent=2));return 0 if result['passed'] else 1
if __name__=='__main__':raise SystemExit(main())
