"""Project explicit process relationships into reusable enterprise-diagrams specs."""
import base64
import hashlib
import html
import importlib.util
import json
from pathlib import Path

DEFAULT_ENGINE = Path(__file__).resolve().parents[2] / 'enterprise-diagrams/scripts/diagram_svg.py'


def load_engine(path=None):
    path = Path(path or DEFAULT_ENGINE).resolve()
    if path.is_dir():
        path = path / 'scripts/diagram_svg.py'
    if not path.is_file():
        raise ValueError(f'Enterprise Diagrams renderer missing: {path}; provide --diagram-engine')
    module_spec = importlib.util.spec_from_file_location('review_enterprise_diagrams', path)
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    return module.render_svg


def specs_for_processes(processes):
    """Hierarchy order controls placement only; never derive execution edges from it."""
    lookup = {p['id']: p for p in processes}
    children = {}
    for p in processes:
        children.setdefault(p.get('parent_id'), []).append(p)
    execution_edges = set()
    for p in processes:
        if p['level'] != 4:
            continue
        for field, inverse in [('downstream_process_ids', 'upstream_process_ids'), ('upstream_process_ids', 'downstream_process_ids')]:
            refs = p.get(field, [])
            if not isinstance(refs, list) or any(not isinstance(ref, str) for ref in refs):
                raise ValueError(f'{p["id"]}: {field} must be a list of IDs')
            for ref in refs:
                if ref not in lookup or lookup[ref].get('level') != 4:
                    raise ValueError(f'{p["id"]}: invalid related L4 process {ref}')
                other = lookup[ref]
                if inverse in other and p['id'] not in other[inverse]:
                    raise ValueError(f'Inconsistent execution relationship: {p["id"]} / {ref}')
                execution_edges.add((p['id'], ref) if field == 'downstream_process_ids' else (ref, p['id']))

    def node(p, row, col, span=1):
        return {'id': p['id'], 'title': p.get('name', p['id']),
                'description': f'{p["id"]}\n状态：{p.get("status", "未提供状态")}', 'badge': f'L{p["level"]}',
                'row': row, 'col': col, 'span': span, 'role': 'primary' if p['level'] == 1 else 'process'}

    def spec(title, nodes, edges, layout, subtitle):
        return {'version': '1.0', 'title': title, 'subtitle': subtitle, 'layout': layout,
                'theme': 'blue', 'width': 1100, 'nodes': nodes, 'edges': edges}

    domains = []
    for root in children.get(None, []):
        nodes, edges, members = [], [], []
        def visit(p, col):
            members.append(p)
            width = 0
            for child in children.get(p['id'], []):
                width += visit(child, col + width)
                edges.append({'from': p['id'], 'to': child['id'], 'label': '包含'})
            width = max(1, width)
            nodes.append(node(p, p['level'] - 1, col, width))
            return width
        visit(root, 0)
        hierarchy = spec(root.get('name', root['id']) + ' · 四级流程归属', nodes, edges,
                         'layered', '包含关系 · 不表示执行先后；节点保留源状态')
        flows = []
        for parent in (p for p in members if p['level'] == 3):
            steps = children.get(parent['id'], [])
            flow_edges, endpoints = [], {p['id']: p for p in steps}
            local_ids = set(endpoints)
            for source, target in sorted(execution_edges):
                if source in local_ids or target in local_ids:
                    endpoints[source] = lookup[source]
                    endpoints[target] = lookup[target]
                    flow_edges.append({'from': source, 'to': target, 'label': '后续'})
            if not steps:
                continue
            flow_nodes = [node(p, 0, i) for i, p in enumerate(endpoints.values())]
            for flow_node in flow_nodes:
                if flow_node['id'] not in local_ids:
                    flow_node['description'] += '\n外部流程'
            flows.append({'process_id': parent['id'], 'spec': spec(
                parent.get('name', parent['id']) + ' · L4 执行关系', flow_nodes, flow_edges,
                'network', '仅显示底稿明确记录的上下游关系；无连线表示未提供执行关系')})
        domains.append({'process_id': root['id'], 'name': root.get('name', root['id']),
                        'spec': hierarchy, 'flows': flows})
    return domains


def render_process_diagrams(processes, engine_path=None):
    domains = specs_for_processes(processes)
    if not domains:
        return []
    renderer = load_engine(engine_path)
    for domain in domains:
        for item in [domain] + domain['flows']:
            item['rendered'] = renderer(item['spec'])
            if not all(e.get('safe') is True for e in item['rendered']['edges']):
                raise ValueError('Enterprise Diagrams reported an unsafe process edge')
            digest = hashlib.sha256(item['process_id'].encode()).hexdigest()[:12]
            item['file_stem'] = ('hierarchy-' if item is domain else 'flow-') + digest
    return domains


def diagram_files(domains, source_header):
    """Keep engine-compatible specs separate from the artifact manifest."""
    files, entries = {}, []
    for domain in domains:
        for item in [domain] + domain['flows']:
            stem = item['file_stem']
            files[stem + '.json'] = json.dumps(item['spec'], ensure_ascii=False, indent=2) + '\n'
            files[stem + '.svg'] = item['rendered']['svg']
            entries.append({'process_id': item['process_id'], 'spec': stem + '.json', 'svg': stem + '.svg',
                            'warnings': item['rendered'].get('warnings', [])})
    files['manifest.json'] = json.dumps({'artifact_header': {
        'artifact_id': source_header.get('project_id', 'unknown') + '-BA-process-diagrams-001',
        'artifact_type': 'process-diagram-projection', 'project_id': source_header.get('project_id', 'unknown'),
        'version': '1.0.0', 'status': 'draft', 'architecture_domains': ['BA'],
        'generated_by': {'skill_name': 'enterprise-diagrams', 'skill_version': '1.0.0', 'tool': 'process_diagrams.py'},
        'upstream_artifact_ids': [source_header['artifact_id']] if source_header.get('artifact_id') else [],
        'upstream_version': source_header.get('version'), 'evidence_ids': source_header.get('evidence_ids', []),
        'assumption_ids': source_header.get('assumption_ids', []), 'data_status': source_header.get('data_status', '未提供'),
        'review': {'reviewer': '未指定', 'decision': 'not-reviewed'}}, 'diagrams': entries}, ensure_ascii=False, indent=2) + '\n'
    return files


def diagrams_html(domains):
    esc = lambda value: html.escape(str(value), quote=True)
    def figure(item):
        encoded = base64.b64encode(item['rendered']['svg'].encode()).decode()
        stem = item['file_stem']
        return (f'<figure class="process-figure"><div class="process-diagram-scroll" tabindex="0" aria-label="{esc(item["spec"]["title"])}">'
                f'<img class="process-diagram" src="data:image/svg+xml;base64,{encoded}" alt="{esc(item["spec"]["title"])}"></div>'
                f'<figcaption><span>{esc(item["spec"]["title"])}</span><span class="diagram-actions">'
                f'<button class="btn" data-process-download="{stem}.json">下载图源 JSON</button>'
                f'<button class="btn" data-process-download="{stem}.svg">下载 SVG</button></span></figcaption></figure>')
    result = ['<p class="notice">层级图箭头表示包含；执行图仅显示已记录的后续关系，不把目录顺序视为执行顺序。</p>']
    for index, domain in enumerate(domains):
        result.append(f'<details class="process-domain" {"open" if index == 0 else ""}><summary>{esc(domain["name"])}</summary>')
        result.append(figure(domain))
        for flow in domain['flows']:
            result.append(figure(flow))
            if not flow['spec']['edges']:
                result.append('<p class="notice">未提供后续执行关系，未推导连线。</p>')
        result.append('</details>')
    return ''.join(result)
