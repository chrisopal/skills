#!/usr/bin/env python3
"""Validate the shipped skill layout and local references without dependencies."""
import ast
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
EXPECTED = {
    'presales-orchestrator', 'presales-source-intake', 'presales-requirements',
    'presales-clarification', 'presales-storyline', 'presales-material-matching',
    'presales-solution-design', 'presales-outline-planning',
    'presales-content-authoring', 'presales-solution-review',
}


def validate():
    errors = []
    actual = {p.name for p in (ROOT / 'skills').iterdir() if p.is_dir()}
    if actual != EXPECTED:
        errors.append(f'skill roster differs: {actual ^ EXPECTED}')
    for name in sorted(EXPECTED):
        path = ROOT / 'skills' / name / 'SKILL.md'
        if not path.exists():
            errors.append(f'missing {path}')
            continue
        text = path.read_text(encoding='utf-8')
        header = re.match(r'^---\n(.*?)\n---\n', text, re.S)
        if not header or f'name: {name}' not in header[1] or not re.search(r'^description: .+', header[1], re.M):
            errors.append(f'invalid frontmatter: {name}')
        metadata = path.parent / 'agents/openai.yaml'
        if not metadata.exists() or f'${name}' not in metadata.read_text(encoding='utf-8'):
            errors.append(f'missing invocation metadata: {name}')
    for path in ROOT.rglob('*'):
        if '__pycache__' in path.parts or not path.is_file():
            continue
        if path.suffix == '.md':
            text = path.read_text(encoding='utf-8')
            if text.count('```') % 2:
                errors.append(f'unclosed fence: {path}')
            for link in re.findall(r'\]\(([^)]+)\)', text):
                if link.startswith(('http:', 'https:', '#')):
                    continue
                target = path.parent / link.split('#', 1)[0]
                if not target.exists():
                    errors.append(f'broken link: {path}: {link}')
                elif not target.resolve().is_relative_to(ROOT):
                    errors.append(f'nonportable link: {path}: {link}')
        elif path.suffix == '.py':
            try:
                ast.parse(path.read_text(encoding='utf-8'), filename=str(path))
            except SyntaxError as exc:
                errors.append(str(exc))
        elif path.suffix == '.json':
            try:
                json.loads(path.read_text(encoding='utf-8'))
            except ValueError as exc:
                errors.append(f'{path}: {exc}')
    return errors


if __name__ == '__main__':
    findings = validate()
    print(json.dumps({'ok': not findings, 'skills': len(EXPECTED), 'errors': findings}, ensure_ascii=False, indent=2))
    sys.exit(bool(findings))
