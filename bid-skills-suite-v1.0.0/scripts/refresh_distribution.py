#!/usr/bin/env python3
"""Rebuild local ZIP deliverables and their SHA256 manifest from suite sources."""
from __future__ import annotations

import hashlib
import json
import shutil
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Keep standalone installations executable without referring to the suite checkout.
DISTRIBUTED_SCRIPTS = {
    'bid-source-intake': ('extract_sources.py', 'paddle_ocr.py'),
    'bid-evidence-matching': ('knowledge.py', 'bidkit.py', 'extract_sources.py', 'paddle_ocr.py'),
    'bid-project-profile': ('tender_router.py',),
    'bid-outline-planning': ('writing_checks.py', 'outline_view.py'),
    'bid-technical-writing': ('writing_checks.py', 'writing_workspace.py', 'outline_view.py', 'render_writing_report.py'),
    'bid-document-layout': ('build_docx.py', 'convert_pdf.py'),
    'bid-orchestrator': ('knowledge.py', 'bidkit.py', 'extract_sources.py', 'paddle_ocr.py', 'tender_router.py', 'render_report.py', 'writing_checks.py', 'writing_workspace.py', 'outline_view.py', 'render_writing_report.py', 'build_docx.py', 'convert_pdf.py'),
}
DISTRIBUTED_DOCS = {
    'bid-source-intake': ('OCR_SETUP.md', 'TENDER_ROUTING.md', 'EXECUTION_QUALITY.md'),
    'bid-project-profile': ('TENDER_ROUTING.md',),
    'bid-requirements': ('TENDER_ROUTING.md', 'EXECUTION_QUALITY.md'),
    'bid-scoring': ('TENDER_ROUTING.md',),
    'bid-compliance': ('TENDER_ROUTING.md', 'EXECUTION_QUALITY.md'),
    'bid-format-extraction': ('TENDER_ROUTING.md', 'EXECUTION_QUALITY.md'),
    'bid-evidence-matching': ('KNOWLEDGE.md', 'OCR_SETUP.md'),
    'bid-outline-planning': ('WRITING_WORKFLOW.md',),
    'bid-technical-writing': ('KNOWLEDGE.md', 'OCR_SETUP.md', 'WRITING_WORKFLOW.md'),
    'bid-visuals': ('WRITING_WORKFLOW.md',),
    'bid-document-layout': ('WRITING_WORKFLOW.md', 'BID_LAYOUT_TEMPLATES.md'),
    'bid-review-remediation': ('WRITING_WORKFLOW.md',),
    'bid-export-acceptance': ('WRITING_WORKFLOW.md',),
    'bid-orchestrator': ('KNOWLEDGE.md', 'OCR_SETUP.md', 'TENDER_ROUTING.md', 'EXECUTION_QUALITY.md', 'REPORTS.md', 'WRITING_WORKFLOW.md', 'BID_LAYOUT_TEMPLATES.md'),
}
DISTRIBUTED_ASSET_DIRS = {
    'bid-project-profile': ('tender-routing',),
    'bid-technical-writing': ('ui',),
    'bid-document-layout': ('layout-templates',),
    'bid-orchestrator': ('tender-routing', 'ui', 'layout-templates'),
}


def sync_standalone_resources(root=ROOT):
    for directory in (root/'skills').iterdir():
        if (directory/'SKILL.md').is_file():
            shutil.copyfile(root/'scripts/validate_output.py', directory/'scripts/validate_output.py')
    for skill_id, names in DISTRIBUTED_SCRIPTS.items():
        for name in names:
            shutil.copyfile(root / 'scripts' / name, root / 'skills' / skill_id / 'scripts' / name)
    for skill_id, names in DISTRIBUTED_DOCS.items():
        for name in names:
            shutil.copyfile(root / 'docs' / name, root / 'skills' / skill_id / 'references' / name)
    for skill_id, directories in DISTRIBUTED_ASSET_DIRS.items():
        for directory in directories:
            shutil.copytree(root / 'assets' / directory,
                            root / 'skills' / skill_id / 'assets' / directory, dirs_exist_ok=True)
    writing_schema = root / 'skills/bid-technical-writing/assets/output.schema.json'
    for skill_id in ('bid-technical-writing', 'bid-orchestrator'):
        shutil.copyfile(writing_schema, root / 'skills' / skill_id / 'assets/writing-output.schema.json')
    for skill_id in ('bid-technical-writing', 'bid-visuals', 'bid-orchestrator'):
        shutil.copyfile(root / 'assets/writing-settings.example.json',
                        root / 'skills' / skill_id / 'assets/writing-settings.example.json')
    shutil.copyfile(root / 'registry.json', root / 'skills/bid-orchestrator/registry.json')


def distribution_files(directory: Path):
    return sorted(
        path for path in directory.rglob('*')
        if path.is_file() and not path.is_symlink()
        and '__pycache__' not in path.parts and path.suffix != '.pyc'
    )


def main():
    sync_standalone_resources()
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
