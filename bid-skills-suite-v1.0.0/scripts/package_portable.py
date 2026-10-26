#!/usr/bin/env python3
"""Build one portable download with individual native Skill ZIPs and an installer."""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXCLUDED = {'.git', '.venv', '__pycache__', '.pytest_cache', '.ruff_cache', '__MACOSX'}


def runtime_files(directory: Path) -> list[Path]:
    result = []
    for path in sorted(directory.rglob('*')):
        relative = path.relative_to(directory)
        if (relative.parts[0] not in {'SKILL.md', 'registry.json', 'agents', 'scripts',
                                      'references', 'assets'}
                or any(part in EXCLUDED or part.startswith('.') for part in relative.parts)
                or path.suffix in {'.pyc', '.pyo'}):
            continue
        if path.is_symlink():
            raise ValueError(f'Runtime symlinks must be resolved before packaging: {path}')
        if path.is_file():
            result.append(path)
    if directory / 'SKILL.md' not in result:
        raise ValueError(f'Missing SKILL.md: {directory}')
    return result


def put(archive: zipfile.ZipFile, name: str, data: bytes) -> None:
    info = zipfile.ZipInfo(name, date_time=(2020, 1, 1, 0, 0, 0))
    info.compress_type = archive.compression
    info.external_attr = 0o100644 << 16
    archive.writestr(info, data, compresslevel=9)


def build(root: Path, out: Path) -> dict:
    registry = json.loads((root / 'registry.json').read_text(encoding='utf-8'))
    sources = [(item['id'], root / 'skills' / item['id']) for item in registry['skills']]
    sources.append(('enterprise-diagrams', root.parent / 'enterprise-diagrams'))
    manifest = {'suite_version': registry['version'], 'package_format': 'skill-root-v2',
                'skills': [], 'runtime_bytes': 0}
    top = f'bid-skills-{registry["version"]}-portable'
    out.parent.mkdir(parents=True, exist_ok=True)
    # Outer ZIP stores already compressed packages to avoid duplicate runtime trees.
    with zipfile.ZipFile(out, 'x', zipfile.ZIP_STORED) as bundle:
        for name, directory in sources:
            files = runtime_files(directory)
            buffer = io.BytesIO()
            with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as skill_zip:
                for path in files:
                    data = path.read_bytes()
                    manifest['runtime_bytes'] += len(data)
                    put(skill_zip, path.relative_to(directory).as_posix(), data)
            data = buffer.getvalue()
            filename = f'packages/{name}.zip'
            manifest['skills'].append({'id': name, 'archive': filename, 'files': len(files),
                                       'sha256': hashlib.sha256(data).hexdigest()})
            put(bundle, f'{top}/{filename}', data)
        for source, target in (('assets/portable-install.py', 'install.py'),
                               ('docs/PORTABLE_INSTALL.md', 'README.md'),
                               ('requirements.txt', 'requirements.txt')):
            put(bundle, f'{top}/{target}', (root / source).read_bytes())
        put(bundle, f'{top}/manifest.json',
            (json.dumps(manifest, ensure_ascii=False, indent=2) + '\n').encode())
    digest = hashlib.sha256(out.read_bytes()).hexdigest()
    out.with_suffix('.zip.sha256').write_text(f'{digest}  {out.name}\n', encoding='utf-8')
    return {'archive': str(out), 'bytes': out.stat().st_size, 'sha256': digest,
            'skills': len(sources), 'runtime_bytes': manifest['runtime_bytes'],
            'files': sum(item['files'] for item in manifest['skills'])}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(build(ROOT, args.out), ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
