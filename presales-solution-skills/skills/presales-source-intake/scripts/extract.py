#!/usr/bin/env python3
"""Extract source text candidates and coverage limits, without business inference."""

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
import zipfile


MAX_BYTES = 64 * 1024 * 1024
W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
IMAGES = {'.png', '.jpg', '.jpeg', '.gif', '.webp', '.tif', '.tiff', '.bmp', '.heic'}


def paragraph_text(element):
    parts = []

    def visit(node):
        if node.tag in {W + 'txbxContent', W + 'del', W + 'moveFrom'}:
            return
        if node.tag == W + 't':
            parts.append(node.text or '')
        elif node.tag == W + 'tab':
            parts.append('\t')
        elif node.tag in {W + 'br', W + 'cr'}:
            parts.append('\n')
        else:
            for child in node:
                visit(child)

    visit(element)
    return ''.join(parts)


def docx_segments(root, part):
    segments = []
    paragraph = 0
    table = 0

    def visit(node, location):
        nonlocal paragraph, table
        if node.tag == W + 'txbxContent':
            return
        if node.tag == W + 'p':
            paragraph += 1
            segments.append({'locator': {'part': part, **location, 'paragraph': paragraph},
                             'text': paragraph_text(node)})
            return
        if node.tag == W + 'tbl':
            table += 1
            number = table
            for row, tr in enumerate(node.findall(W + 'tr'), 1):
                for column, cell in enumerate(tr.findall(W + 'tc'), 1):
                    visit(cell, {**location, 'table': number, 'row': row, 'column': column})
            return
        if node.tag in {W + 'footnote', W + 'endnote'}:
            location = {**location, 'note_id': node.get(W + 'id')}
        for child in node:
            visit(child, location)

    visit(root, {})
    return segments


def extract_docx(source, report):
    report['extractor'] = 'stdlib.zipfile+xml.etree.ElementTree'
    report['visual_review_status'] = 'pending'
    report['warnings'].append('Native text extraction is not a complete visual review; layout, diagrams and page rendering remain unreviewed.')
    coverage = []
    with zipfile.ZipFile(source) as archive:
        entries = archive.infolist()
        if sum(info.file_size for info in entries) > MAX_BYTES:
            raise ValueError('DOCX uncompressed size exceeds the 64 MiB limit')
        names = [info.filename for info in entries]
        if len(names) != len(set(names)):
            raise ValueError('DOCX contains duplicate archive entries')
        for name in names:
            if PurePosixPath(name).is_absolute() or '..' in PurePosixPath(name).parts or '\\' in name:
                raise ValueError('DOCX contains an unsafe archive path')
        if 'word/document.xml' not in names:
            raise ValueError('DOCX is missing word/document.xml')
        if any(name.startswith('word/media/') for name in names):
            coverage.append('Embedded images require visual review; no OCR was performed.')
        if any(name.startswith(('word/embeddings/', 'word/charts/', 'word/diagrams/')) for name in names):
            coverage.append('Embedded objects, charts or diagrams require visual review.')
        parts = [name for name in names if re.fullmatch(r'word/(document|header\d+|footer\d+|footnotes|endnotes)\.xml', name)]
        for part in sorted(parts, key=lambda name: (name != 'word/document.xml', name)):
            payload = archive.read(part)
            declaration_bytes = payload.replace(b'\x00', b'')
            if b'<!DOCTYPE' in declaration_bytes or b'<!ENTITY' in declaration_bytes:
                raise ValueError('XML entity declarations are unsupported')
            root = ET.fromstring(payload)
            tags = {node.tag.rsplit('}', 1)[-1] for node in root.iter()}
            if 'txbxContent' in tags:
                coverage.append(f'{part}: textbox content is omitted; inspect visually.')
            if tags & {'ins', 'del', 'moveFrom', 'moveTo', 'pPrChange', 'rPrChange', 'tblPrChange'}:
                coverage.append(f'{part}: tracked revisions are present; extracted text is not an accepted final revision.')
            if tags & {'drawing', 'pict', 'object', 'altChunk', 'AlternateContent'}:
                coverage.append(f'{part}: drawing or alternate content may be omitted; inspect visually.')
            if tags & {'gridSpan', 'vMerge'}:
                coverage.append(f'{part}: merged table cells use XML cell positions, not rendered grid coordinates.')
            report['segments'].extend(docx_segments(root, part))
    report['warnings'].extend(coverage)
    if not any(segment['text'].strip() for segment in report['segments']):
        report['read_status'] = 'needs_ocr'
        report['warnings'].append('No native text found; inspect the original and use OCR if it contains scanned text.')
    elif coverage:
        report['read_status'] = 'partial'


def extract_pdf(source, report):
    report['extractor'] = 'pdftotext'
    report['visual_review_status'] = 'pending'
    report['warnings'].append('PDF text extraction does not verify visual layout, images, charts or reading order.')
    tool = shutil.which('pdftotext')
    if not tool:
        report['read_status'] = 'partial'
        report['warnings'].append('pdftotext is unavailable; text was not read. Install it or provide a text export; OCR need is unknown.')
        return
    result = subprocess.run([tool, '-layout', '-enc', 'UTF-8', str(source.resolve()), '-'],
                            capture_output=True, timeout=60, check=False)
    if result.returncode:
        raise ValueError('pdftotext failed: ' + result.stderr.decode('utf-8', errors='replace')[:1000])
    if len(result.stdout) > MAX_BYTES:
        raise ValueError('PDF extracted text exceeds the 64 MiB limit')
    pages = result.stdout.decode('utf-8').split('\f')
    if len(pages) > 1 and not pages[-1].strip():
        pages.pop()
    report['segments'] = [{'locator': {'page': page}, 'text': text} for page, text in enumerate(pages, 1)]
    empty = [index for index, text in enumerate(pages, 1) if not text.strip()]
    if empty:
        report['read_status'] = 'needs_ocr' if len(empty) == len(pages) else 'partial'
        report['warnings'].append(f'Pages without native text: {empty}; inspect for blank pages or scans needing OCR.')
    if result.stderr:
        report['warnings'].append('pdftotext warning: ' + result.stderr.decode('utf-8', errors='replace')[:1000])
        if report['read_status'] == 'text_extracted':
            report['read_status'] = 'partial'


def extract(source):
    report = {'filename': source.name, 'hash': None, 'read_status': 'text_extracted',
              'extractor': 'none', 'segments': [], 'warnings': [], 'visual_review_status': 'not_required'}
    try:
        if not source.is_file():
            raise ValueError('Source must be a regular file')
        digest = hashlib.sha256()
        with source.open('rb') as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b''):
                digest.update(chunk)
        report['hash'] = digest.hexdigest()
        report['size_bytes'] = source.stat().st_size
        suffix = source.suffix.lower()
        if suffix in IMAGES:
            report.update(read_status='needs_visual_review', extractor='metadata_only', visual_review_status='pending')
            report['warnings'].append('Image content has not been read; visual review and optional OCR are required.')
        elif suffix == '.pdf':
            extract_pdf(source, report)
        elif suffix == '.docx':
            extract_docx(source, report)
        elif suffix in {'.md', '.txt', '.markdown'}:
            report['extractor'] = 'stdlib.utf-8-lines'
            if source.stat().st_size > MAX_BYTES:
                raise ValueError('Text file exceeds the 64 MiB limit')
            report['segments'] = [{'locator': {'line': number}, 'text': line}
                                  for number, line in enumerate(source.read_text(encoding='utf-8-sig').splitlines(), 1)]
            if not any(segment['text'].strip() for segment in report['segments']):
                report['read_status'] = 'partial'
                report['warnings'].append('No non-whitespace text was found.')
        else:
            report.update(read_status='unsupported', visual_review_status='pending')
            report['warnings'].append(f'Unsupported file type: {suffix or "none"}; original content has not been read.')
    except (OSError, ValueError, zipfile.BadZipFile, ET.ParseError, RuntimeError, subprocess.SubprocessError) as error:
        report['read_status'] = 'error'
        report['warnings'].append(str(error))
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('file', type=Path)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.out.resolve() == args.file.resolve():
            raise ValueError('Output must not be the source file')
        if args.out.is_symlink():
            raise ValueError('Output must not be a symlink')
        report = extract(args.file)
        payload = json.dumps(report, ensure_ascii=False, indent=2) + '\n'
        if args.out.exists():
            if args.out.read_text(encoding='utf-8') != payload:
                raise ValueError('Output already exists with different content; choose a new --out path')
        else:
            args.out.parent.mkdir(parents=True, exist_ok=True)
            with args.out.open('x', encoding='utf-8') as handle:
                handle.write(payload)
        print(json.dumps({'output': str(args.out), 'read_status': report['read_status'],
                          'segments': len(report['segments'])}, ensure_ascii=False))
        return 2 if report['read_status'] in {'error', 'unsupported'} else 0
    except (OSError, ValueError) as error:
        print(f'Extraction refused: {error}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
