#!/usr/bin/env python3
"""Mechanical content checks only. Always requires a separate visual review."""
import argparse,hashlib,json,re,sys,zipfile
from pathlib import Path
from xml.etree import ElementTree

def inspect(path):
    content=path.read_bytes();notes=[]
    if path.suffix.lower()=='.docx':
        with zipfile.ZipFile(path) as z:
            if 'word/document.xml' not in z.namelist():raise ValueError('不是有效DOCX包')
            texts=[]
            for name in z.namelist():
                if name.startswith('word/') and name.endswith('.xml'):
                    root=ElementTree.fromstring(z.read(name))
                    texts.extend(''.join(n.text or '' for n in p.iter() if n.tag.endswith('}t'))
                                 for p in root.iter() if p.tag.endswith('}p'))
                    if name.endswith('comments.xml'):notes.append('仍包含批注部件，需审查')
                    if any(n.tag.endswith('}del') or n.tag.endswith('}ins') for n in root.iter()):notes.append('仍有修订记录，需审查')
            text='\n'.join(texts);pages=None
    elif path.suffix.lower()=='.pdf':
        import fitz
        with fitz.open(path) as doc:
            pages=len(doc);text='\n'.join(page.get_text() for page in doc)
            if not text.strip():notes.append('没有可检查文字层，需视觉复核/OCR而非自动通过')
    else:raise ValueError('仅支持DOCX/PDF')
    for token in ('REPLACE_ME','[[TODO','【内部','\ue200','\ufffd','\u2eda'):
        if token in text:notes.append('检测到需复核的内部占位或异常字符：'+repr(token))
    compact = re.sub(r'\s+', '', text)
    if (re.search(r'confirmation_ref|reviewed_inputs_sha256|body_markdown', compact)
            or re.search(r'(?<![A-Za-z0-9_/])(?:work|reviews|artifacts|profiles)/\s*'
                         r'[A-Za-z0-9_./\-\u4e00-\u9fff]+', text)):
        notes.append('检测到内部执行信息，须改为对外文案并保留独立审计记录')
    if re.search(r'§[A-Za-z0-9][A-Za-z0-9_.:-]*§',text):notes.append('疑似内部页码探针泄漏')
    return {'file':path.name,'sha256':hashlib.sha256(content).hexdigest(),'bytes':len(content),'pages':pages,'extracted_chars':len(text),'mechanical_check':'passed' if not notes else 'needs_review','visual_qa':'NOT_RUN','findings':sorted(set(notes))}

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('file',type=Path);a=p.parse_args()
    try:result=inspect(a.file);print(json.dumps(result,ensure_ascii=False,indent=2));return 0 if not result['findings'] else 1
    except (ImportError,OSError,ValueError,zipfile.BadZipFile,ElementTree.ParseError) as e:print(str(e),file=sys.stderr);return 2
if __name__=='__main__':raise SystemExit(main())
