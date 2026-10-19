"""Exercise the downloadable bundle and its extracted installer, not a mock install."""
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from package_portable import build, runtime_files  # noqa: E402


@pytest.fixture(scope='module')
def bundle(tmp_path_factory):
    workspace = tmp_path_factory.mktemp('portable')
    archive = workspace / 'download.zip'
    summary = build(ROOT, archive)
    with zipfile.ZipFile(archive) as package:
        assert package.testzip() is None
        package.extractall(workspace / 'unpacked')
    unpacked = next((workspace / 'unpacked').iterdir())
    return archive, unpacked, summary


def test_all_18_skills_install_with_original_runtime_bytes(bundle, tmp_path):
    _, unpacked, summary = bundle
    assert summary['skills'] == 18
    assert summary['bytes'] < summary['runtime_bytes'] // 2
    destination = tmp_path / 'host' / 'skills'
    command = [sys.executable, str(unpacked / 'install.py'), '--dest', str(destination)]
    subprocess.run(command + ['--dry-run'], check=True, capture_output=True)
    assert not destination.exists()
    subprocess.run(command, check=True, capture_output=True)
    names = {path.name for path in destination.iterdir()}
    assert len(names) == 18
    for name in names:
        source = ROOT.parent / name if name == 'enterprise-diagrams' else ROOT / 'skills' / name
        expected = {path.relative_to(source): path.read_bytes() for path in runtime_files(source)}
        actual = {path.relative_to(destination / name): path.read_bytes()
                  for path in (destination / name).rglob('*') if path.is_file()}
        assert expected == actual
        assert (destination / name / 'SKILL.md').is_file()
    # The installed total controller can start using only its own scripts/resources.
    result = subprocess.run([sys.executable, str(destination / 'bid-orchestrator/scripts/bidkit.py'),
                             '--help'], check=True, capture_output=True, cwd=tmp_path)
    assert b'usage:' in result.stdout
    sentinel = destination / 'bid-orchestrator' / 'my-custom-file.txt'
    sentinel.write_text('keep me')
    result = subprocess.run(command, capture_output=True)
    assert result.returncode == 1
    assert sentinel.read_text() == 'keep me'
    partial = tmp_path / 'existing-host'
    existing = partial / 'enterprise-diagrams'
    existing.mkdir(parents=True)
    result = subprocess.run([sys.executable, str(unpacked / 'install.py'),
                             '--dest', str(partial)], capture_output=True)
    assert result.returncode == 1
    assert list(partial.iterdir()) == [existing]


@pytest.mark.parametrize('agent', ['claude-code', 'workbuddy', 'codex'])
def test_host_defaults_use_isolated_home_and_config_dirs(bundle, tmp_path, agent):
    _, unpacked, _ = bundle
    env = {**os.environ, 'HOME': str(tmp_path), 'CODEX_HOME': str(tmp_path / 'codex-config'),
           'WORKBUDDY_CONFIG_DIR': str(tmp_path / 'buddy-config')}
    subprocess.run([sys.executable, str(unpacked / 'install.py'), '--agent', agent],
                   env=env, check=True, capture_output=True)
    expected = {'claude-code': tmp_path / '.claude/skills',
                'workbuddy': tmp_path / 'buddy-config/skills',
                'codex': tmp_path / 'codex-config/skills'}[agent]
    assert len(list(expected.glob('*/SKILL.md'))) == 18


def test_bundle_is_reproducible_and_carries_checksum(bundle, tmp_path):
    archive, _, _ = bundle
    second = tmp_path / 'second.zip'
    build(ROOT, second)
    assert archive.read_bytes() == second.read_bytes()
    assert archive.with_suffix('.zip.sha256').read_text().split()[0] == hashlib.sha256(
        archive.read_bytes()).hexdigest()


@pytest.mark.parametrize('entry', ['demo/../../escape', 'demo/..\\escape'])
def test_unsafe_archive_rejected_before_any_install(entry, tmp_path):
    spec = importlib.util.spec_from_file_location('portable_install', ROOT / 'assets/portable-install.py')
    installer = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(installer)
    (tmp_path / 'packages').mkdir()
    archive = tmp_path / 'packages/demo.zip'
    with zipfile.ZipFile(archive, 'w') as package:
        package.writestr('demo/SKILL.md', 'demo')
        package.writestr(entry, 'escape')
    manifest = {'skills': [{'id': 'demo', 'archive': 'packages/demo.zip',
                            'sha256': hashlib.sha256(archive.read_bytes()).hexdigest()}]}
    (tmp_path / 'manifest.json').write_text(json.dumps(manifest))
    target = tmp_path / 'target'
    with pytest.raises(ValueError, match='Unsafe'):
        installer.install(tmp_path, target)
    assert not target.exists()
    archive.write_bytes(b'corrupt')
    with pytest.raises(ValueError, match='Checksum'):
        installer.install(tmp_path, target)
    assert not target.exists()


def test_runtime_selection_omits_development_and_cache_files(tmp_path):
    (tmp_path / 'SKILL.md').write_text('skill')
    for name in ('tests/test.py', 'docs/images/demo.png', '.env', 'scripts/__pycache__/a.pyc',
                 'scripts/.env.key', 'scripts/helper.py', 'assets/examples/template.json'):
        target = tmp_path / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text('fixture')
    assert {str(path.relative_to(tmp_path)) for path in runtime_files(tmp_path)} == {
        'SKILL.md', 'scripts/helper.py', 'assets/examples/template.json'}
