#!/usr/bin/env python3
"""Conservative native extraction. Images/scans are flagged, never silently accepted."""
from __future__ import annotations
import argparse, hashlib, json, sys
from datetime import datetime, timezone
from pathlib import Path

def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for c in iter(lambda:f.read(1024*1024),b''):h.update(c)
    return h.hexdigest()

def extract(project: Path, project_id: str) -> dict:
    project=project.resolve();registry=json.loads((project/'inputs/source-registry.json').read_text(encoding='utf-8'))
    actual_project_id=json.loads((project/'work/project.json').read_text(encoding='utf-8')).get('project_id')
    if not actual_project_id or project_id!=actual_project_id:raise ValueError('请求项目ID与工作目录不一致')
    docs=[];blocks=[];audit=[];warnings=[];blockers=[]
    for entry in registry['sources']:
        rel=Path(entry['relative_path']);path=(project/rel).resolve();sid=entry['source_id'];review=False
        if rel.is_absolute() or '..' in rel.parts or not path.is_relative_to(project):raise ValueError('来源路径越界')
        if sha(path)!=entry['sha256'] or path.stat().st_size!=entry['bytes']:raise ValueError('原件身份变更：'+sid)
        row={'source_id':sid,'filename':path.name,'relative_path':rel.as_posix(),'sha256':entry['sha256'],'bytes':entry['bytes'],'role':entry['role'],'revision':entry['revision'],'duplicate_group':None,'status':'parsed'}
        block_index=[0]
        def add(text,loc,page=None):
            if text.strip():
                block_index[0]+=1
                blocks.append({'block_id':f'{sid}-B{block_index[0]:05d}','source_id':sid,'location':loc,'page':page,'text':text,'method':'native'})
        try:
            if path.suffix.lower() in {'.md','.txt'}:
                for i,line in enumerate(path.read_text(encoding='utf-8-sig').splitlines(),1):add(line,f'L{i}')
            elif path.suffix.lower()=='.docx':
                from docx import Document
                from docx.text.paragraph import Paragraph
                from docx.table import Table
                doc=Document(path)
                for i,child in enumerate(doc.element.body,1):
                    if child.tag.endswith('}p'):add(Paragraph(child,doc).text,f'body[{i}]/paragraph')
                    elif child.tag.endswith('}tbl'):
                        table=Table(child,doc)
                        for r,row_cells in enumerate(table.rows,1):
                            for c,cell in enumerate(row_cells.cells,1):add(cell.text,f'body[{i}]/table/r{r}/c{c}')
                seen=set()
                for section in doc.sections:
                    for part in (section.header,section.footer):
                        if id(part._element) in seen:continue
                        seen.add(id(part._element))
                        for i,p in enumerate(part.paragraphs,1):add(p.text,f'{part._element.tag.split("}")[-1]}/p{i}')
                review=True;warnings.append(sid+': DOCX页码依赖渲染，原生提取不保证文本框、修订、批注及复杂合并表完整，需复核。')
            elif path.suffix.lower()=='.pdf':
                import fitz
                with fitz.open(path) as doc:
                    if doc.needs_pass:raise ValueError('加密PDF需要人工提供可读取版本')
                    for i,page in enumerate(doc,1):
                        text=page.get_text('text');images=bool(page.get_images(full=True))
                        needs=images or len(text.strip())<30 or '\ufffd' in text
                        review=review or needs
                        add(text,f'P{i}',i)
                        audit.append({'source_id':sid,'page':i,'status':'needs_review' if needs else 'processed','method':'native','note':'含图片／文字稀少／编码异常，需视觉或OCR复核' if needs else '已抽取文字层，仍须按任务核对表格和关键参数'})
                if review:warnings.append(sid+': 本脚本未执行OCR，不得把扫描或图像区域标为已完整读取。')
            else:raise ValueError('此脚本不支持该格式；请使用已授权宿主工具或保留原件后受控转换')
            if not any(b['source_id']==sid for b in blocks):review=True;warnings.append(sid+': 没有提取到有效文字')
            if review:row['status']='needs_review'
        except (ImportError,OSError,ValueError,RuntimeError) as exc:
            row['status']='failed';blockers.append(sid+': '+str(exc))
        docs.append(row)
    complete=bool(docs) and all(d['status']=='parsed' for d in docs)
    if not docs:blockers.append('未注册任何来源')
    return {'schema_version':'1.0','skill_id':'bid-source-intake','project_id':project_id,'artifact_id':'ART-01-NATIVE','revision':1,'created_at':datetime.now(timezone.utc).isoformat(),'status':'blocked' if blockers else 'needs_review','inputs':[],'summary':'原生抽取结果；人工未核验，尚不是业务验收通过。','data':{'documents':docs,'blocks':blocks,'page_audit':audit,'coverage':'complete' if complete else 'partial'},'warnings':warnings,'blockers':blockers}

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--project',type=Path,required=True);p.add_argument('--project-id',required=True);p.add_argument('--out',type=Path,required=True);args=p.parse_args()
    try:
        if args.out.exists():raise ValueError('输出已存在，请使用新的产物版本文件名')
        result=extract(args.project,args.project_id);args.out.parent.mkdir(parents=True,exist_ok=True)
        with args.out.open('x',encoding='utf-8') as out:json.dump(result,out,ensure_ascii=False,indent=2)
        print(json.dumps({'output':str(args.out),'status':result['status'],'coverage':result['data']['coverage']},ensure_ascii=False));return 1 if result['blockers'] else 0
    except (OSError,ValueError,KeyError) as exc:print(str(exc),file=sys.stderr);return 2
if __name__=='__main__':raise SystemExit(main())
