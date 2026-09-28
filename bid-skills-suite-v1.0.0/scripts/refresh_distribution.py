#!/usr/bin/env python3
"""Rebuild local ZIP deliverables and their SHA256 manifest from suite sources."""
from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def distribution_files(directory: Path):
    return sorted(
        path for path in directory.rglob('*')
        if path.is_file() and not path.is_symlink()
        and '__pycache__' not in path.parts and path.suffix != '.pyc'
    )


def main():
    registry = json.loads((ROOT / 'registry.json').read_text(encoding='utf-8'))
    destination = ROOT / 'installable-zips'
    destination.mkdir(exist_ok=True)
    for item in registry['skills']:
        skill_id = item['id']
        source = ROOT / 'skills' / skill_id
        archive = destination / f"{item['sequence']:02d}-{skill_id}.zip"
        with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as output:
            for path in distribution_files(source):
                output.write(path, f'{skill_id}/{path.relative_to(source).as_posix()}')
    manifest = ROOT / 'FILES.sha256'
    lines = []
    for path in distribution_files(ROOT):
        if path == manifest:
            continue
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        lines.append(f'{digest}  {path.relative_to(ROOT).as_posix()}')
    manifest.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print(f"rebuilt {len(registry['skills'])} ZIPs and {len(lines)} checksums")


if __name__ == '__main__':
    main()
