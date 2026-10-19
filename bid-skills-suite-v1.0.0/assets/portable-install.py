#!/usr/bin/env python3
"""Install verified, self-contained Skill ZIPs without third-party dependencies."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
import zipfile
from pathlib import Path, PurePosixPath


def verify(root: Path) -> list[tuple[str, Path]]:
    manifest = json.loads((root / 'manifest.json').read_text(encoding='utf-8'))
    packages = []
    seen = set()
    for item in manifest['skills']:
        name = item['id']
        if not name or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in name):
            raise ValueError('Invalid Skill name')
        if name in seen:
            raise ValueError(f'Duplicate Skill: {name}')
        seen.add(name)
        filename = item['archive']
        if PurePosixPath(filename).parts != ('packages', f'{name}.zip'):
            raise ValueError(f'Invalid archive path: {name}')
        archive = root / filename
        if hashlib.sha256(archive.read_bytes()).hexdigest() != item['sha256']:
            raise ValueError(f'Checksum mismatch: {name}')
        with zipfile.ZipFile(archive) as package:
            names = set()
            for member in package.infolist():
                path = PurePosixPath(member.filename)
                if (path.is_absolute() or '..' in path.parts or '\\' in member.filename
                        or not path.parts or path.parts[0] != name
                        or stat.S_ISLNK(member.external_attr >> 16)
                        or member.filename in names):
                    raise ValueError(f'Unsafe archive entry: {name}')
                names.add(member.filename)
            if f'{name}/SKILL.md' not in names or package.testzip() is not None:
                raise ValueError(f'Invalid Skill package: {name}')
        packages.append((name, archive))
    if not packages:
        raise ValueError('No Skills in manifest')
    return packages


def install(root: Path, destination: Path, dry_run: bool = False) -> int:
    packages = verify(root)  # Verify every archive before writing any Skill.
    for name, _ in packages:
        target = destination / name
        if target.exists() or target.is_symlink():
            raise FileExistsError(f'Already exists; back up and move it first: {target}')
    if not dry_run:
        destination.mkdir(parents=True, exist_ok=True)
        for _, archive in packages:
            with zipfile.ZipFile(archive) as package:
                package.extractall(destination)
    print(f'{"Verified" if dry_run else "Installed"}: {len(packages)} Skills -> {destination}')
    return len(packages)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument('--agent', choices=('claude-code', 'workbuddy', 'codex'))
    target.add_argument('--dest', type=Path, help='Custom Skill discovery directory')
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    defaults = {
        'claude-code': Path.home() / '.claude' / 'skills',
        'workbuddy': Path(os.environ.get('WORKBUDDY_CONFIG_DIR') or Path.home() / '.workbuddy') / 'skills',
        'codex': Path(os.environ.get('CODEX_HOME') or Path.home() / '.codex') / 'skills',
    }
    destination = args.dest.expanduser() if args.dest is not None else defaults[args.agent]
    try:
        install(Path(__file__).resolve().parent, destination, args.dry_run)
    except (OSError, ValueError, KeyError, zipfile.BadZipFile) as exc:
        parser.exit(1, f'{exc}\n')


if __name__ == '__main__':
    main()
