#!/usr/bin/env python3
"""Convert a DOCX using an installed LibreOffice in an isolated profile."""
from __future__ import annotations
import argparse,json,shutil,subprocess,sys,tempfile
from pathlib import Path

def convert(source:Path,target:Path,timeout:int=120):
    if source.suffix.lower()!='.docx' or not source.is_file():raise ValueError('请输入存在的DOCX文件')
    if target.exists():raise ValueError('拒绝覆盖已有PDF')
    binary=shutil.which('soffice') or shutil.which('libreoffice')
    if not binary:raise ValueError('未检测到LibreOffice；请使用宿主Word/PDF导出工具，本脚本不自动安装软件')
    with tempfile.TemporaryDirectory(prefix='bid-pdf-') as work:
        work=Path(work);profile=(work/'profile').resolve().as_uri()
        result=subprocess.run([binary,f'-env:UserInstallation={profile}','--headless','--convert-to','pdf','--outdir',str(work),str(source.resolve())],capture_output=True,text=True,timeout=timeout,check=False)
        pdf=work/(source.stem+'.pdf')
        if result.returncode!=0 or not pdf.is_file() or not pdf.read_bytes().startswith(b'%PDF-'):raise ValueError('转换失败：'+(result.stderr or result.stdout)[-1500:])
        target.parent.mkdir(parents=True,exist_ok=True)
        with pdf.open('rb') as src,target.open('xb') as out:shutil.copyfileobj(src,out)
    return {'output':str(target),'status':'generated_needs_qa','visual_qa':'NOT_RUN'}

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--input',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--timeout',type=int,default=120);a=p.parse_args()
    try:print(json.dumps(convert(a.input,a.out,a.timeout),ensure_ascii=False));return 0
    except (OSError,ValueError,subprocess.TimeoutExpired) as e:print(str(e),file=sys.stderr);return 2
if __name__=='__main__':raise SystemExit(main())
