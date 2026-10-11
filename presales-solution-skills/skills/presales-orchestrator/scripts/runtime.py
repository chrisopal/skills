#!/usr/bin/env python3
"""Local presales artifact ledger. Structural evidence only; never semantic approval.

Only Python's standard library is used. Run --help for the command surface.
The project index is a local trusted ledger, not a signature or access control system.
"""
import argparse
import copy
import hashlib
import json
import math
import os
from pathlib import Path
import re
import sys
import tempfile
import zipfile
import xml.etree.ElementTree as ET

KINDS = {'brief', 'evidence', 'requirements', 'clarification', 'storyline', 'materials',
         'solution', 'outline', 'content', 'review', 'delivery'}
STATES = {'draft', 'ready', 'blocked'}
ID = re.compile(r'^[A-Za-z][A-Za-z0-9_-]{0,99}$')
HASH = re.compile(r'^[a-f0-9]{64}$')
REF_FIELDS = ('artifact_ids', 'evidence_ids', 'requirement_ids', 'solution_ids', 'material_ids')
DECK_FIELDS = ('deck_id', 'version', 'purpose', 'audience', 'decisions_required', 'language',
               'page_budget', 'duration_minutes', 'theme_profile', 'output_formats', 'story_arc')
SLIDE_FIELDS = ('slide_id', 'section', 'title', 'key_message', 'supporting_points', 'speaker_notes',
                *REF_FIELDS, 'visual_type', 'chart_spec', 'diagram_spec', 'layout_hint',
                'visible_caveats', 'locked_claims', 'review_status', 'appendix')


class Invalid(ValueError):
    """An invalid project, dependency, file or artifact."""


def require(condition, message):
    if not condition:
        raise Invalid(message)


def ident(value):
    require(isinstance(value, str) and ID.fullmatch(value), 'unsafe or missing ID')
    return value


def digest(path):
    hasher = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            hasher.update(chunk)
    return hasher.hexdigest()


def rooted(project, value):
    """Reject traversal and every symlink component, even links pointing inside."""
    require(isinstance(value, (str, Path)), 'path must be a string')
    raw = Path(value)
    require('..' not in raw.parts, 'path traversal is forbidden')
    candidate = raw if raw.is_absolute() else project / raw
    require(candidate.is_relative_to(project), 'path must stay inside project')
    current = project
    require(not current.is_symlink(), 'project symlink is forbidden')
    for part in candidate.relative_to(project).parts:
        current = current / part
        require(not current.is_symlink(), 'symlink paths are forbidden')
    require(candidate.resolve().is_relative_to(project.resolve()), 'path escapes project')
    return candidate


def project_path(value):
    raw = Path(os.path.abspath(value))
    for path in (raw, *raw.parents):
        require(not path.is_symlink(), 'project ancestor symlinks are forbidden; use the canonical path')
    return raw


def read_json(path):
    with path.open(encoding='utf-8') as stream:
        value = json.load(stream)
    require(isinstance(value, dict), 'JSON root must be an object')
    return value


def write_json(path, value, exclusive=False):
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + '\n'
    if exclusive:
        with path.open('x', encoding='utf-8') as stream:
            stream.write(text)
        return
    fd, name = tempfile.mkstemp(prefix='.ledger-', dir=path.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            stream.write(text)
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def load(project):
    config = read_json(rooted(project, 'work/project.json'))
    ident(config.get('project_id'))
    require(config.get('purpose') in ('internal-draft', 'customer-review'), 'invalid project purpose')
    index = read_json(rooted(project, 'work/index.json'))
    require(index.get('project_id') == config['project_id'], 'index project mismatch')
    require(isinstance(index.get('artifacts'), dict), 'invalid artifact index')
    return config, index


def strings(value, label):
    require(isinstance(value, list) and all(isinstance(v, str) for v in value), label + ' must be a string list')


def validate_content(data):
    for field in ('deck_id', 'purpose', 'audience'):
        require(isinstance(data.get(field), str) and data[field].strip(), 'content requires ' + field)
    for field in ('language', 'theme_profile', 'story_arc'):
        if field in data:
            require(isinstance(data[field], str), field + ' must be a string')
    for field in ('decisions_required', 'output_formats'):
        if field in data:
            strings(data[field], field)
    if 'version' in data:
        require(type(data['version']) in (str, int), 'version must be a string or integer')
    if 'page_budget' in data:
        require(type(data['page_budget']) is int and data['page_budget'] > 0, 'page_budget must be a positive integer')
    if 'duration_minutes' in data:
        value = data['duration_minutes']
        require(type(value) in (int, float) and value > 0 and math.isfinite(value), 'duration_minutes must be positive and finite')
    require(isinstance(data.get('slides'), list) and data['slides'], 'content requires slides')
    seen = set()
    for slide in data['slides']:
        require(isinstance(slide, dict), 'invalid slide')
        sid = ident(slide.get('slide_id'))
        require(sid not in seen, 'duplicate slide_id')
        seen.add(sid)
        for field in ('title', 'key_message', 'speaker_notes', 'visual_type', 'review_status'):
            require(isinstance(slide.get(field), str), 'slide requires ' + field)
        for field in ('supporting_points', 'visible_caveats', 'locked_claims', *REF_FIELDS):
            strings(slide.get(field), field)
        for field in ('section', 'layout_hint', 'chart_spec', 'diagram_spec'):
            if field in slide:
                require(isinstance(slide[field], str), field + ' must be a reviewed textual specification')
        if 'appendix' in slide:
            require(type(slide['appendix']) is bool, 'appendix must be boolean')
        for field in REF_FIELDS:
            for reference in slide[field]:
                ident(reference)


def envelope(obj, config):
    require(obj.get('project_id') == config['project_id'], 'cross-project artifact rejected')
    ident(obj.get('artifact_id'))
    require(obj.get('kind') in KINDS, 'unknown artifact kind')
    require(type(obj.get('revision')) is int and obj['revision'] > 0, 'revision must be a positive integer')
    require(obj.get('status') in STATES, 'invalid artifact status')
    require(isinstance(obj.get('data'), dict), 'data must be an object')
    require(isinstance(obj.get('inputs'), list), 'inputs must be a list')
    seen = set()
    for item in obj['inputs']:
        require(isinstance(item, dict), 'invalid input')
        aid = ident(item.get('artifact_id'))
        require(aid not in seen, 'duplicate input')
        seen.add(aid)
        require(isinstance(item.get('sha256'), str) and HASH.fullmatch(item['sha256']), 'invalid input hash')
    if obj['kind'] == 'content':
        validate_content(obj['data'])


def validate_content_artifact_refs(obj, objects, entries, states):
    """Bind artifact IDs only; business requirement/evidence IDs use separate namespaces."""
    references = {aid for slide in obj['data']['slides'] for aid in slide['artifact_ids']}
    if not references:
        return
    reachable = set()
    pending = list(obj['inputs'])
    while pending:
        dependency = pending.pop()
        aid = dependency['artifact_id']
        entry = entries.get(aid)
        require(entry and entry['sha256'] == dependency['sha256'] and states.get(aid) == 'ready',
                'content reference dependency is missing, stale or not ready: ' + aid)
        if aid not in reachable:
            reachable.add(aid)
            pending.extend(objects.get(aid, {}).get('inputs', []))
    missing = sorted(references - reachable)
    require(not missing, 'slide artifact_ids must be bound in the exact-hash dependency graph: ' + ', '.join(missing))


def target_binding(obj, target_id, target_hash, objects, entries):
    require(any(item['artifact_id'] == target_id and item['sha256'] == target_hash for item in obj['inputs']),
            'target must be bound in inputs with exact hash')
    require(target_id in entries and entries[target_id]['sha256'] == target_hash, 'target hash is not current')
    require(target_id in objects, 'target must be an artifact')
    return objects[target_id]


def validate_review(obj, objects, entries, project):
    data = obj['data']
    require(data.get('mode') in ('direction', 'content', 'delivery'), 'invalid review mode')
    require(data.get('verdict') in ('pass', 'conditional', 'fail', 'not_checked'), 'invalid verdict')
    for field in ('method', 'reviewer'):
        require(isinstance(data.get(field), str) and data[field].strip(), 'review requires ' + field)
    for field in ('findings', 'scope', 'unchecked'):
        require(isinstance(data.get(field), list), 'review requires ' + field + ' list')
    target = target_binding(obj, data.get('target_id'), data.get('target_sha256'), objects, entries)
    if data['mode'] == 'content':
        require(target['kind'] in ('content', 'outline', 'solution'), 'content review target kind invalid')
    if data['mode'] == 'delivery':
        require(target['kind'] == 'delivery', 'delivery review requires delivery target')
        require(data.get('file_hashes') == target['data'].get('file_hashes') and data.get('file_hashes'),
                'delivery review must bind current actual file hashes')
        if data['verdict'] == 'pass':
            require(target['data']['native_review']['status'] == 'pass', 'delivery pass requires native_review pass')
            renders, _ = render_evidence(project, target['data'])
            require(all(page['verdict'] == 'pass' for page in renders['pages']), 'delivery pass requires every rendered page reviewed as pass')
    for finding in data['findings']:
        require(isinstance(finding, dict), 'invalid finding')
        ident(finding.get('finding_id'))
        require(finding.get('severity') in ('blocking', 'major', 'minor', 'info'), 'invalid finding severity')
        require(finding.get('status') in ('open', 'closed', 'deferred'), 'invalid finding status')
        if finding['severity'] == 'blocking' and data['verdict'] == 'pass':
            require(finding['status'] == 'closed' and finding.get('resolution_evidence'),
                    'blocking finding requires closure and resolution_evidence')


def render_evidence(project, data):
    evidence = read_json(rooted(project, data['render_evidence_path']))
    for field in ('renderer', 'reviewer'):
        require(isinstance(evidence.get(field), str) and evidence[field].strip(), 'render evidence requires ' + field)
    pages = evidence.get('pages')
    require(isinstance(pages, list) and pages, 'render evidence requires nonempty pages')
    require(len(pages) == len(data.get('page_map', [])), 'render page count differs from page_map')
    hashes = {}
    for number, page in enumerate(pages, 1):
        require(isinstance(page, dict) and type(page.get('page')) is int and page['page'] == number,
                'render pages must be in exact page order')
        relative = page.get('image_path')
        require(isinstance(relative, str) and relative and not Path(relative).is_absolute(), 'render image path must be project-relative')
        path = rooted(project, relative)
        require(path.is_file(), 'render image missing')
        with path.open('rb') as stream:
            header = stream.read(12)
        require(header.startswith(b'\x89PNG\r\n\x1a\n') or header.startswith(b'\xff\xd8\xff'),
                'render evidence supports PNG or JPEG image signatures')
        actual = digest(path)
        require(page.get('sha256') == actual, 'render image hash changed')
        require(page.get('verdict') in ('pass', 'conditional', 'fail', 'not_checked'), 'invalid render verdict')
        require(isinstance(page.get('observations'), str), 'render observations must be a string')
        require(relative not in hashes, 'render pages require distinct image files')
        hashes[relative] = actual
    return evidence, hashes


def file_hashes(project, data):
    hashes = {}
    for field in ('pptx_path', 'pdf_path', 'render_evidence_path'):
        require(isinstance(data.get(field), str) and data[field], 'delivery requires ' + field)
        require(not Path(data[field]).is_absolute(), 'delivery paths must be project-relative')
        path = rooted(project, data[field])
        require(path.is_file(), 'missing delivery file: ' + field)
        hashes[field] = digest(path)
    with rooted(project, data['pdf_path']).open('rb') as stream:
        require(stream.read(5) == b'%PDF-', 'invalid PDF signature; this does not verify PDF layout')
    _, hashes['render_pages'] = render_evidence(project, data)
    return hashes


def validate_delivery(project, obj, objects, entries, registering=False):
    data = obj['data']
    content = target_binding(obj, data.get('input_content_id'), data.get('input_content_sha256'), objects, entries)
    require(content['kind'] == 'content', 'delivery input must be content')
    validate_content(content['data'])
    actual = file_hashes(project, data)
    if registering:
        require('file_hashes' not in data or data['file_hashes'] == actual, 'provided file hashes disagree')
        data['file_hashes'] = actual
    else:
        require(data.get('file_hashes') == actual, 'delivery file hash changed')
    with zipfile.ZipFile(rooted(project, data['pptx_path'])) as archive:
        names = archive.namelist()
        require(len(names) == len(set(names)), 'duplicate PPTX ZIP entries')
        require('[Content_Types].xml' in names, 'not a PPTX package')
        presentation = ET.fromstring(archive.read('ppt/presentation.xml'))
        relationships = ET.fromstring(archive.read('ppt/_rels/presentation.xml.rels'))
        rels = {item.get('Id'): item for item in relationships}
        require(len(rels) == len(relationships), 'duplicate presentation relationship IDs')
        ids = presentation.findall('{http://schemas.openxmlformats.org/presentationml/2006/main}sldIdLst/'
                                   '{http://schemas.openxmlformats.org/presentationml/2006/main}sldId')
        slides = []
        for item in ids:
            rel = rels.get(item.get('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id'))
            require(rel is not None and rel.get('TargetMode') != 'External', 'missing or external slide relationship')
            require(rel.get('Type', '').endswith('/slide'), 'invalid slide relationship type')
            target = rel.get('Target', '')
            require(re.fullmatch(r'slides/slide[1-9][0-9]*\.xml', target), 'invalid slide target')
            path = 'ppt/' + target
            ET.fromstring(archive.read(path))
            slides.append(path)
        require(slides and len(slides) == len(set(slides)), 'empty or repeated presentation slides')
    expected = [{'slide_id': slide['slide_id'], 'page': n} for n, slide in enumerate(content['data']['slides'], 1)]
    require(data.get('page_map') == expected, 'page_map must match content IDs and order exactly')
    require(len(slides) == len(expected), 'PPTX slide count differs from content/page_map')
    native = data.get('native_review')
    require(isinstance(native, dict), 'delivery requires native_review')
    require(native.get('status') in ('pass', 'conditional', 'fail', 'not_checked'), 'invalid native_review status')
    for field in ('method', 'reviewer'):
        require(isinstance(native.get(field), str) and native[field], 'native_review requires ' + field)


def snapshot(project, config, index):
    """Recompute actual hashes and dependency validity; never trust a cached ready."""
    entries = index['artifacts']
    objects, errors = {}, {aid: [] for aid in entries}
    for aid, entry in entries.items():
        try:
            ident(aid)
            require(isinstance(entry, dict), 'invalid index entry')
            path = rooted(project, entry['path'])
            require(path.is_file(), 'registered file missing')
            require(digest(path) == entry['sha256'], 'registered file hash changed')
            if entry.get('kind') != 'source':
                obj = read_json(path)
                envelope(obj, config)
                require(obj['artifact_id'] == aid and obj['kind'] == entry['kind'] and obj['revision'] == entry['revision'],
                        'artifact identity differs from index')
                objects[aid] = obj
        except (Invalid, OSError, KeyError, ValueError, TypeError) as exc:
            errors[aid].append(str(exc))
    for aid, obj in objects.items():
        try:
            if obj['kind'] == 'review':
                validate_review(obj, objects, entries, project)
            elif obj['kind'] == 'delivery':
                validate_delivery(project, obj, objects, entries)
        except (Invalid, OSError, KeyError, ValueError, TypeError, zipfile.BadZipFile, ET.ParseError) as exc:
            errors[aid].append(str(exc))
    states, visiting = {}, set()

    def visit(aid):
        if aid in states:
            return states[aid]
        if aid in visiting:
            errors[aid].append('dependency cycle')
            return 'stale'
        visiting.add(aid)
        obj = objects.get(aid)
        for dependency in obj['inputs'] if obj else []:
            other = dependency['artifact_id']
            if other not in entries:
                errors[aid].append('broken reference: ' + other)
            elif entries[other]['sha256'] != dependency['sha256']:
                errors[aid].append('input hash changed: ' + other)
            elif visit(other) != 'ready':
                errors[aid].append('input unavailable: ' + other)
        if obj and obj['kind'] == 'content':
            try:
                validate_content_artifact_refs(obj, objects, entries, states)
            except Invalid as exc:
                errors[aid].append(str(exc))
        visiting.remove(aid)
        states[aid] = 'stale' if errors[aid] else obj['status'] if obj else 'ready'
        return states[aid]

    for aid in entries:
        visit(aid)
    result = dict(project_id=config['project_id'], purpose=config['purpose'],
                  ok=all(value == 'ready' for value in states.values()),
                  validation_scope='structure-and-file-integrity-only', business_approval='unconfirmed',
                  artifacts={aid: dict(state=states[aid], errors=errors[aid], **entries[aid]) for aid in entries})
    return result, objects


def reject_cycle(aid, inputs, objects):
    def reaches(start, seen):
        if start == aid:
            return True
        if start in seen or start not in objects:
            return False
        return any(reaches(item['artifact_id'], seen | {start}) for item in objects[start]['inputs'])
    require(not any(reaches(item['artifact_id'], set()) for item in inputs), 'dependency cycle rejected')


def initialize(project, project_id, purpose):
    ident(project_id)
    require(not project.exists() or not any(project.iterdir()), 'init requires a new or empty project')
    project.mkdir(parents=True, exist_ok=True)
    for name in ('inputs', 'work', 'artifacts', 'assets', 'reviews', 'deliverables'):
        rooted(project, name).mkdir()
    config = dict(project_id=project_id, purpose=purpose, schema_version=1)
    write_json(rooted(project, 'work/project.json'), config, exclusive=True)
    write_json(rooted(project, 'work/index.json'), dict(project_id=project_id, artifacts={}), exclusive=True)
    return config


def add_source(project, file, aid, revision):
    config, index = load(project)
    ident(aid)
    require(aid.startswith('SRC-'), 'source ID must start with SRC-')
    require(revision > 0, 'revision must be positive')
    prior = index['artifacts'].get(aid)
    require(not prior or prior['kind'] == 'source', 'ID already belongs to artifact')
    require(not prior or revision > prior['revision'], 'source revision must increase; frozen snapshots are never overwritten')
    original = Path(file)
    require(original.is_file() and not original.is_symlink(), 'source must be a regular non-symlink file')
    suffix = original.suffix if re.fullmatch(r'\.[A-Za-z0-9]{1,12}', original.suffix) else '.bin'
    target = rooted(project, f'inputs/{aid}/r{revision}{suffix}')
    target.parent.mkdir(parents=True, exist_ok=True)
    with original.open('rb') as source, target.open('xb') as destination:
        for chunk in iter(lambda: source.read(1024 * 1024), b''):
            destination.write(chunk)
    target.chmod(0o444)
    entry = dict(kind='source', revision=revision, path=str(target.relative_to(project)), sha256=digest(target))
    index['artifacts'][aid] = entry
    write_json(rooted(project, 'work/index.json'), index)
    return dict(artifact_id=aid, **entry)


def register(project, file):
    config, index = load(project)
    obj = read_json(Path(file))
    envelope(obj, config)
    aid = obj['artifact_id']
    prior = index['artifacts'].get(aid)
    require(not prior or prior['kind'] == obj['kind'], 'artifact kind cannot change')
    require(not prior or obj['revision'] > prior['revision'], 'revision must increase')
    report, objects = snapshot(project, config, index)
    for dependency in obj['inputs']:
        entry = report['artifacts'].get(dependency['artifact_id'])
        require(entry and entry['sha256'] == dependency['sha256'] and entry['state'] == 'ready', 'input is missing, stale or not ready')
    reject_cycle(aid, obj['inputs'], objects)
    if obj['kind'] == 'content':
        validate_content_artifact_refs(obj, objects, index['artifacts'],
                                       {key: value['state'] for key, value in report['artifacts'].items()})
    if obj['kind'] == 'review':
        validate_review(obj, objects, index['artifacts'], project)
    elif obj['kind'] == 'delivery':
        validate_delivery(project, obj, objects, index['artifacts'], registering=True)
    directory = 'reviews' if obj['kind'] == 'review' else 'artifacts'
    target = rooted(project, f'{directory}/{aid}/r{obj["revision"]}.json')
    write_json(target, obj, exclusive=True)
    entry = dict(kind=obj['kind'], revision=obj['revision'], path=str(target.relative_to(project)), sha256=digest(target))
    index['artifacts'][aid] = entry
    write_json(rooted(project, 'work/index.json'), index)
    return dict(artifact_id=aid, **entry)


def prepare(project, aid, output):
    config, index = load(project)
    report, objects = snapshot(project, config, index)
    require(aid in objects and objects[aid]['kind'] == 'content', 'content not found')
    require(report['artifacts'][aid]['state'] == 'ready', 'content is stale or not ready')
    sha = index['artifacts'][aid]['sha256']
    reviews = []
    for rid, obj in objects.items():
        if obj['kind'] != 'review' or report['artifacts'][rid]['state'] != 'ready':
            continue
        data = obj['data']
        if data['mode'] == 'content' and data['target_id'] == aid and data['target_sha256'] == sha:
            reviews.append((rid, data))
    require(reviews, 'current content has no valid bound review')
    require(all(data['verdict'] == 'pass' for _, data in reviews), 'current review is not pass')
    require(any(data['method'].startswith('independent-') for _, data in reviews), 'independent review required; self-check is not approval')
    destination = rooted(project, output)
    require(not destination.exists() or destination.is_dir() and not any(destination.iterdir()), 'output must be an empty directory')
    content = objects[aid]['data']
    slides = [{key: copy.deepcopy(slide[key]) for key in SLIDE_FIELDS if key in slide} for slide in content['slides']]
    # No nested private dictionaries or arbitrary assets are exported: this is a text bridge.
    for slide in slides:
        for key in ('chart_spec', 'diagram_spec'):
            if key in slide:
                require(isinstance(slide[key], str), key + ' must be reviewed textual specification for export')
    deck = {field: copy.deepcopy(content[field]) for field in DECK_FIELDS if field in content}
    lines = ['# ' + content['deck_id'], '', 'Project use scope: ' + config['purpose'],
             'Business approval: unconfirmed', '']
    for field, value in deck.items():
        lines += [field + ': ' + (json.dumps(value, ensure_ascii=False) if isinstance(value, list) else str(value))]
    lines.append('')
    for slide in slides:
        lines += ['## ' + slide['slide_id'] + ' — ' + slide['title'], '', slide['key_message'], '']
        for field in ('supporting_points', 'visible_caveats', 'locked_claims', *REF_FIELDS):
            lines += ['### ' + field, *['- ' + value for value in slide[field]], '']
        for field in ('section', 'speaker_notes', 'visual_type', 'chart_spec', 'diagram_spec', 'layout_hint', 'review_status', 'appendix'):
            if field in slide:
                lines += ['### ' + field, str(slide[field]), '']
    handoff = dict(schema_version=1, project_id=config['project_id'], purpose=config['purpose'],
                   business_approval='unconfirmed', content_id=aid, content_sha256=sha,
                   review_ids=[rid for rid, _ in reviews], deck=deck, slides=slides,
                   permissions='Layout changes only; preserve facts, visible caveats and locked claims. Return substantive changes to content authoring.')
    destination.mkdir(parents=True, exist_ok=True)
    markdown = rooted(project, destination / 'content.md')
    with markdown.open('x', encoding='utf-8') as stream:
        stream.write('\n'.join(lines))
    handoff['markdown_sha256'] = digest(markdown)
    write_json(rooted(project, destination / 'handoff.json'), handoff, exclusive=True)
    return dict(output=str(destination), content_sha256=sha, purpose=config['purpose'], business_approval='unconfirmed')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    init = commands.add_parser('init')
    init.add_argument('project')
    init.add_argument('--project-id', required=True)
    init.add_argument('--purpose', choices=['internal-draft', 'customer-review'], required=True)
    source = commands.add_parser('source')
    source.add_argument('project')
    source.add_argument('file')
    source.add_argument('--id', required=True)
    source.add_argument('--revision', type=int, default=1)
    add = commands.add_parser('register')
    add.add_argument('project')
    add.add_argument('file')
    for name in ('status', 'validate'):
        commands.add_parser(name).add_argument('project')
    ppt = commands.add_parser('prepare-ppt')
    ppt.add_argument('project')
    ppt.add_argument('content_id')
    ppt.add_argument('--out', required=True)
    args = parser.parse_args(argv)
    try:
        project = project_path(args.project)
        if args.command == 'init':
            result = initialize(project, args.project_id, args.purpose)
        elif args.command == 'source':
            result = add_source(project, args.file, args.id, args.revision)
        elif args.command == 'register':
            result = register(project, args.file)
        elif args.command == 'prepare-ppt':
            result = prepare(project, args.content_id, args.out)
        else:
            config, index = load(project)
            result, _ = snapshot(project, config, index)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result.get('ok', True) else 1
    except (Invalid, OSError, ValueError, KeyError, TypeError, zipfile.BadZipFile, ET.ParseError) as exc:
        print(json.dumps(dict(ok=False, error=str(exc)), ensure_ascii=False))
        return 1


if __name__ == '__main__':
    sys.exit(main())
