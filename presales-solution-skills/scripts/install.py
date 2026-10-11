#!/usr/bin/env python3
"""Copy sibling presales skills without replacing an existing installation."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile


IGNORED = {'__pycache__', '.DS_Store', '.pytest_cache', '.mypy_cache', '.ruff_cache', '.git'}


def check_path(path):
    """Reject links in the path, including links to otherwise valid directories."""
    for component in (path, *path.parents):
        if component.is_symlink():
            raise ValueError(f'Symlink paths are not supported: {component}')
        if component != path and component.exists() and not component.is_dir():
            raise ValueError(f'Parent is not a directory: {component}')


def digest(path):
    value = hashlib.sha256()
    with path.open('rb') as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b''):
            value.update(chunk)
    return value.hexdigest()


def manifest(root):
    check_path(root)
    if not root.is_dir():
        raise ValueError(f'Not a directory: {root}')
    entries = {}

    def visit(directory):
        for item in sorted(directory.iterdir()):
            if item.is_symlink():
                raise ValueError(f'Symlink content is not supported: {item}')
            if item.name in IGNORED or item.suffix in {'.pyc', '.pyo'}:
                continue
            relative = item.relative_to(root).as_posix()
            if item.is_dir():
                entries[relative] = None
                visit(item)
            elif item.is_file():
                entries[relative] = digest(item)
            else:
                raise ValueError(f'Non-regular content is not supported: {item}')

    visit(root)
    return entries


def install(source, destination):
    source = source.expanduser().absolute()
    destination = destination.expanduser().absolute()
    check_path(source)
    check_path(destination)
    if destination.resolve().is_relative_to(source.parent.resolve()):
        raise ValueError('Destination cannot be inside the source suite; choose another --dest directory')
    if destination.exists() and not destination.is_dir():
        raise ValueError(f'Destination is not a directory: {destination}')
    skills = sorted(source.glob('presales-*'))
    if not skills:
        raise ValueError(f'No presales skills found in {source}')
    snapshots = {}
    new = []
    for skill in skills:
        snapshots[skill.name] = manifest(skill)
        if 'SKILL.md' not in snapshots[skill.name]:
            raise ValueError(f'Skill is missing SKILL.md: {skill}')
        target = destination / skill.name
        if target.exists() or target.is_symlink():
            if manifest(target) != snapshots[skill.name]:
                raise ValueError(f'Existing skill differs: {target}. Choose a new empty --dest directory; no files were replaced.')
        else:
            new.append(skill)

    # All conflicts have been checked before the first destination write.
    destination.mkdir(parents=True, exist_ok=True)
    installed = []
    with tempfile.TemporaryDirectory(prefix='.presales-install-', dir=destination) as staging:
        staging = Path(staging)
        for skill in new:
            staged = staging / skill.name
            staged.mkdir()
            for relative, checksum in snapshots[skill.name].items():
                target = staged / relative
                if checksum is None:
                    target.mkdir(parents=True, exist_ok=True)
                else:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(skill / relative, target, follow_symlinks=False)
            if manifest(staged) != snapshots[skill.name]:
                raise ValueError(f'Hash verification failed: {skill.name}')
        for skill in skills:
            if manifest(skill) != snapshots[skill.name]:
                raise ValueError(f'Source changed during install: {skill.name}')
            target = destination / skill.name
            if skill in new:
                if target.exists() or target.is_symlink():
                    raise ValueError(f'Destination changed during install: {target}; choose a new --dest directory')
            elif manifest(target) != snapshots[skill.name]:
                raise ValueError(f'Destination changed during install: {target}')
        for skill in new:
            (staging / skill.name).rename(destination / skill.name)
            installed.append(skill.name)
    # Read back every installed or reused file, not just copy command status.
    for skill in skills:
        if manifest(destination / skill.name) != snapshots[skill.name]:
            raise ValueError(f'Installed hash verification failed: {skill.name}')
    return {'destination': str(destination), 'installed': installed,
            'unchanged': [p.name for p in skills if p.name not in installed],
            'verified_skills': len(skills)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    default = Path(os.environ.get('CODEX_HOME', str(Path.home() / '.codex'))) / 'skills'
    parser.add_argument('--dest', type=Path, default=default, help='Destination skills directory (default: $CODEX_HOME/skills or ~/.codex/skills)')
    args = parser.parse_args()
    try:
        result = install(Path(__file__).absolute().parents[1] / 'skills', args.dest)
    except (OSError, ValueError) as error:
        print(f'Install refused: {error}', file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
