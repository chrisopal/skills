#!/usr/bin/env python3
"""Read-only Markdown inventory for editorial planning, not a quality classifier.
Only the named UTF-8 file is read. No network, link fetching or manuscript code execution.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import re
from pathlib import Path
from collections import Counter
from statistics import median
from typing import Any

HAN = re.compile(r'[\u4e00-\u9fff]')
HEADING = re.compile(r'^(#{1,6})\s+(.+?)\s*$')
CHAPTER = re.compile(r'^第\s*(\d+)\s*章\s*(.*)$')
APPENDIX = re.compile(r'^附录\s*([一二三四五六七八九十]+|\d+)\s*(.*)$')
FENCE = re.compile(r'^\s{0,3}(`{3,}|~{3,})(.*)$')
PHRASES = ['回读', '重新读取', '核对', '哈希', 'SHA-256', '复跑', '待确认', '不等于', '实际', '可复用写法', '最值得', '值得注意', '值得停下来', '最有价值', '最有帮助', '真正的价值', '重点聚焦']

def normalized(text: str) -> str:
    return re.sub(r'\\([\\`*_{}\[\]()#+\-.!>])', r'\1', text)

def visible_text(line: str) -> str:
    line = re.sub(r'!\[[^\]]*\]\([^\n]*\)', '', line)
    line = re.sub(r'\[([^\]]+)\]\([^\n]*?\)', r'\1', line)
    # Do not export authcodes, signed URLs or other raw URLs in the inventory.
    line = re.sub(r'https?://\S+', '', line)
    return normalized(line)

def classify_lines(text: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    lines = text.splitlines()
    records: list[dict[str, Any]] = []
    blocks: list[dict[str, Any]] = []
    active: dict[str, Any] | None = None
    for number, line in enumerate(lines, 1):
        match = FENCE.match(line)
        if active is not None:
            closing = bool(match and match.group(1)[0] == active['marker']
                           and len(match.group(1)) >= active['length']
                           and not match.group(2).strip())
            kind = 'fence' if closing else 'code_or_prompt'
            if closing:
                active['end_line'] = number
                active['closed'] = True
                blocks.append(active)
                active = None
            else:
                active['han_count'] += len(HAN.findall(line))
        elif match:
            active = {'start_line': number, 'end_line': None, 'marker': match.group(1)[0],
                      'length': len(match.group(1)), 'info': visible_text(match.group(2).strip()),
                      'han_count': 0, 'closed': False}
            kind = 'fence'
        elif not line.strip():
            kind = 'blank'
        elif re.match(r'^\s*!\[', line):
            kind = 'image_reference'
        elif re.match(r'^\s*\\?\[.+?\\?\]\s*$', line):
            kind = 'attachment_placeholder'
        elif HEADING.match(line):
            kind = 'heading'
        elif line.lstrip().startswith('|'):
            kind = 'table'
        else:
            kind = 'narrative'
        records.append({'line': number, 'kind': kind, 'text': line})
    if active is not None:
        active['end_line'] = len(lines)
        blocks.append(active)
    return records, blocks

def inventory(text: str, source_name: str = 'manuscript.md') -> dict[str, Any]:
    records, blocks = classify_lines(text)
    sections: list[dict[str, Any]] = []
    for r in records:
        if r['kind'] != 'heading':
            continue
        h = HEADING.match(r['text'])
        assert h is not None
        if len(h.group(1)) != 1:
            continue
        title = visible_text(h.group(2))
        c, a = CHAPTER.match(title), APPENDIX.match(title)
        if c or a:
            sections.append({'type': 'chapter' if c else 'appendix',
                             'id': int(c.group(1)) if c else a.group(1),
                             'title': title, 'start_line': r['line']})
    for i, s in enumerate(sections):
        s['end_line'] = sections[i+1]['start_line'] - 1 if i+1 < len(sections) else len(records)
        subset = records[s['start_line']-1:s['end_line']]
        by_kind: Counter[str] = Counter()
        for r in subset:
            by_kind[r['kind']] += len(HAN.findall(visible_text(r['text'])))
        own_blocks = [b for b in blocks if s['start_line'] <= b['start_line'] <= s['end_line']]
        s.update(han_by_block_type=dict(by_kind), han_count=sum(by_kind.values()),
                 code_or_prompt_blocks=len(own_blocks),
                 longest_code_or_prompt_han=max((b['han_count'] for b in own_blocks), default=0),
                 subheading_count=sum(r['kind']=='heading' for r in subset)-1,
                 image_reference_count=sum(r['kind']=='image_reference' for r in subset),
                 attachment_placeholder_count=sum(r['kind']=='attachment_placeholder' for r in subset),
                 coverage_status='inventoried_not_editorially_read')
    phrase_counts: dict[str, dict[str, int]] = {}
    for phrase in PHRASES:
        count: Counter[str] = Counter()
        for r in records:
            n = visible_text(r['text']).count(phrase)
            if n: count[r['kind']] += n
        phrase_counts[phrase] = dict(count)
    chapters = [s for s in sections if s['type']=='chapter']
    return {'schema_version': '1.1.0', 'source_name': source_name,
            'line_count': len(records), 'raw_han_count': len(HAN.findall(text)),
            'chapter_count': len(chapters), 'appendix_count': len(sections)-len(chapters),
            'chapter_han_median': median([s['han_count'] for s in chapters]) if chapters else None,
            'fence_count': len(blocks), 'unclosed_fences': [b for b in blocks if not b['closed']],
            'sections': sections, 'phrase_counts_by_block_type': phrase_counts,
            'limits': ['Counts are navigation cues, not quality or AI-authorship scores.',
                       'Code blocks include prompts as well as program code.',
                       'References are not fetched; their presence does not establish availability.',
                       'This lightweight scanner is not a full CommonMark parser.',
                       'Editorial read coverage must be recorded separately by the actual reader.']}

def run(source: Path, output: Path) -> dict[str, Any]:
    source = source.resolve(strict=True)
    output = output.resolve()
    if source == output:
        raise ValueError('Output must not overwrite the source.')
    raw = source.read_bytes()
    text = raw.decode('utf-8-sig')
    result = inventory(text, source.name)
    result['source_sha256'] = hashlib.sha256(raw).hexdigest()
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('x', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
        f.write('\n')
    return result

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    try:
        r = run(args.source, args.output)
    except (OSError, UnicodeError, ValueError) as exc:
        parser.exit(2, f'Inventory failed: {type(exc).__name__}: {exc}\n')
    print(f"Inventoried {r['chapter_count']} chapters and {r['appendix_count']} appendices. "
          'No editorial verdict generated.')

if __name__ == '__main__':
    main()
