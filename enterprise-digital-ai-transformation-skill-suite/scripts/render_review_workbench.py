#!/usr/bin/env python3
"""Build an offline, read-only consulting review workbench from explicit sources."""
import argparse
import hashlib
import html
import json
import re
import tempfile
from pathlib import Path
import xml.etree.ElementTree as ET
from process_diagrams import diagram_files, diagrams_html, render_process_diagrams

ASSETS = Path(__file__).resolve().parents[1] / "shared/assets/review-workbench"
LABELS = dict(zip(
    "id name owner status state level parent_id purpose trigger inputs outputs end_condition control_points information_ids application_ids technology_ids process_ids kpi_ids evidence_ids design_assumptions as_is_issue target_change formula unit baseline target source guardrail period grain baseline_period target_period data_owner exclusion incentive lifecycle authoritative_application quality_rule access retention service_boundary retirement deployment nfr failure_mode security cost_note decision boundary escalation from to object semantic direction frequency failure entry exit transition fte depends_on wave_id success work_packages architecture_domains gap_ids amount year cost benefit net cumulative".split(),
    "编号 名称 负责人 状态 架构状态 层级 上级 目的 触发条件 输入 输出 完成条件 控制点 信息对象 应用服务 技术服务 流程 绩效指标 证据 设计假设 现状问题 目标变化 计算口径 单位 基线 目标 来源 约束 周期 粒度 基线期间 目标期间 数据负责人 排除规则 激励边界 生命周期 权威应用 质量规则 访问权限 保留规则 服务边界 退役策略 部署位置 非功能要求 故障处理 安全要求 成本说明 决策 授权边界 升级路径 起点 终点 信息对象 语义 方向 频率 失败恢复 进入条件 退出条件 过渡架构 人力投入 前置依赖 波次 成功标准 工作包 架构域 差距 金额 年份 支出 收益 净现金 累计现金".split()))


def esc(value):
    return html.escape(str(value), quote=True)


def safe_json(value):
    return json.dumps(value, ensure_ascii=False).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")


def record(value):
    if isinstance(value, dict):
        return '<dl class="fields">' + ''.join(f'<dt>{esc(LABELS.get(k, k))}</dt><dd>{record(v)}</dd>' for k, v in value.items()) + '</dl>'
    if isinstance(value, list):
        return '<ul class="values">' + ''.join(f'<li>{record(v)}</li>' for v in value) + '</ul>' if value else '<span class="muted">无记录</span>'
    return esc('未提供' if value is None else value)


def disclosure(label, value):
    return f'<details class="source"><summary>{esc(label)}</summary>{record(value)}</details>'


def collection(title, items):
    content = ''.join(disclosure(item.get('name', item.get('decision', item.get('id', f'记录 {i + 1}'))), item) for i, item in enumerate(items))
    return f'<h2>{esc(title)}</h2>{content or empty(title)}'


def empty(label):
    return f'<p class="notice">未提供{esc(label)}，未生成替代内容。</p>'


def table(items, columns):
    if not items:
        return empty('记录')
    return '<div class="table-wrap"><table><thead><tr>' + ''.join(f'<th scope="col">{esc(label)}</th>' for key, label in columns) + '</tr></thead><tbody>' + ''.join('<tr>' + ''.join(f'<td>{record(item.get(key))}</td>' for key, label in columns) + '</tr>' for item in items) + '</tbody></table></div>'


def inline(text):
    text = esc(text)
    def link(m):
        url = html.unescape(m[2])
        return f'<a href="{esc(url)}" rel="noreferrer">{m[1]}</a>' if url.startswith(('https://', 'http://')) else m[0]
    text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', link, text)
    text = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', text)
    return re.sub(r'`([^`]+)`', r'<code>\1</code>', text)


def markdown(text):
    """Small safe Markdown subset; unknown syntax remains visible literal text."""
    result, paragraph, table = [], [], []
    def flush():
        if paragraph:
            result.append('<p>' + '<br>'.join(inline(x) for x in paragraph) + '</p>')
            paragraph.clear()
        if table:
            rows = [r for r in table if not re.fullmatch(r'[\s|:\-]+', r)]
            result.append('<div class="table-wrap"><table>' + ''.join('<tr>' + ''.join(f'<{"th" if i == 0 else "td"}>{inline(c.strip())}</{"th" if i == 0 else "td"}>' for c in row.strip('|').split('|')) + '</tr>' for i, row in enumerate(rows)) + '</table></div>')
            table.clear()
    if text.startswith('---\n') and '\n---' in text[4:]:
        metadata, text = text[4:].split('\n---', 1)
        try:
            result.append(disclosure('报告版本与证据', json.loads(metadata)))
        except json.JSONDecodeError:
            result.append(disclosure('报告头部原文', metadata))
    for line in text.splitlines():
        if line.startswith('|'):
            if paragraph:
                flush()
            table.append(line)
        elif not line.strip():
            flush()
        elif re.match(r'^#{1,6} ', line):
            flush()
            level = min(len(line.split(' ')[0]), 4)
            result.append(f'<h{level}>{inline(line[level + 1:])}</h{level}>')
        else:
            if table:
                flush()
            paragraph.append(line)
    flush()
    return ''.join(result)


def validate(pack, slides):
    if not isinstance(pack, dict) or not isinstance(slides, dict):
        raise ValueError('Pack and slides must be JSON objects')
    for key in ('processes', 'applications', 'information_objects', 'technology_services', 'kpis', 'organization_decisions', 'waves', 'initiatives', 'integrations'):
        if not isinstance(pack.get(key, []), list) or any(not isinstance(x, dict) for x in pack.get(key, [])):
            raise ValueError(f'{key} must contain objects')
    if not isinstance(slides.get('slides', []), list) or any(not isinstance(s, dict) for s in slides.get('slides', [])):
        raise ValueError('slides must contain objects')
    nodes = pack.get('processes', [])
    by_id = {p.get('id'): p for p in nodes}
    if len(by_id) != len(nodes) or (nodes and None in by_id):
        raise ValueError('Process IDs must be present and unique')
    for p in nodes:
        level, parent = p.get('level'), p.get('parent_id')
        if level not in (1, 2, 3, 4) or (level == 1 and parent is not None):
            raise ValueError('Process must use L1-L4 hierarchy')
        if level != 1 and (parent not in by_id or by_id[parent].get('level') != level - 1):
            raise ValueError('Missing parent or invalid process hierarchy')
    ids = [s.get('slide_id') for s in slides.get('slides', [])]
    if len(set(ids)) != len(ids) or any(not isinstance(x, str) or not x for x in ids):
        raise ValueError('Slide IDs must be present and unique')


def process_tree(nodes):
    children = {}
    for node in nodes:
        children.setdefault(node.get('parent_id'), []).append(node)
    def branch(parent):
        return ''.join(f'<details class="process-node" data-process-id="{esc(n["id"])}"><summary><span class="tag">L{n["level"]}</span> {esc(n.get("name", n["id"]))} <span class="muted">{esc(n.get("status", "未提供状态"))}</span></summary><div class="branch">{disclosure("流程明细 · " + n["id"], n)}{branch(n["id"])}</div></details>' for n in children.get(parent, []))
    return branch(None) or empty('流程')


def architecture_graph(app, lookup):
    """A focused AA graph; group boxes enumerate every endpoint of each edge type."""
    groups = [('BA · 支撑流程', '支撑', app.get('process_ids', [])), ('IA · 处理信息对象', '处理', app.get('information_ids', [])), ('TA · 依赖技术服务', '依赖', app.get('technology_ids', []))]
    lines = []
    for title, relation, ids in groups:
        entries = []
        for node_id in ids:
            name = lookup.get(node_id, {}).get('name', '引用未解析')
            entries.append(node_id)
            entries.extend(name[i:i + 16] for i in range(0, len(name), 16))
            entries.append('')
        lines.append(entries or ['未提供关系'])
    height = 238 + max(len(items) for items in lines) * 24
    graph = [f'<div class="graph-scroll"><svg class="architecture-graph" viewBox="0 0 1080 {height}" role="img" aria-labelledby="graph-title graph-desc"><title id="graph-title">{esc(app.get("name", app["id"]))}的4A追溯图</title><desc id="graph-desc">箭头由AA应用发出：支撑所列BA流程、处理所列IA对象、依赖所列TA技术服务。所有端点来自该应用源记录，未推导域间关系。</desc><defs><marker id="arrow" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M0 0L8 4L0 8Z" fill="currentColor"/></marker></defs>']
    graph.append('<rect class="graph-box hub" x="340" y="16" width="400" height="80" rx="4"/>')
    graph.append(f'<text class="graph-label" x="540" y="45" text-anchor="middle">AA · {esc(app["id"])}</text><text class="graph-label" x="540" y="74" text-anchor="middle">{esc(app.get("name", ""))}</text>')
    for i, ((title, relation, ids), entries) in enumerate(zip(groups, lines)):
        x = 20 + i * 360
        center = x + 160
        graph.append(f'<path class="graph-edge" d="M540 96 V120 H{center} V174" marker-end="url(#arrow)"/><text class="graph-relation" x="{center + 12}" y="153">{relation}</text><rect class="graph-box" x="{x}" y="180" width="320" height="{height - 200}" rx="4"/><text class="graph-label" x="{x + 16}" y="211">{title}</text>')
        for row, text in enumerate(entries):
            graph.append(f'<text class="graph-node" x="{x + 16}" y="{242 + row * 24}">{esc(text)}</text>')
    graph.append('</svg></div>')
    return ''.join(graph)


def architecture(pack):
    lookup = {n['id']: n for key in ('processes', 'information_objects', 'applications', 'technology_services') for n in pack.get(key, []) if 'id' in n}
    rows = []
    for app in pack.get('applications', []):
        lanes = [('BA · 支撑流程', app.get('process_ids', [])), ('IA · 处理信息', app.get('information_ids', [])), ('AA · 应用服务', [app['id']]), ('TA · 依赖技术', app.get('technology_ids', []))]
        row = '<article class="trace"><h3>' + esc(app.get('name', app['id'])) + '</h3><div class="trace-grid">'
        for label, ids in lanes:
            row += f'<div class="trace-lane"><h4>{esc(label)}</h4>' + ''.join(disclosure(lookup.get(i, {}).get('name', i), lookup.get(i, {'id': i, 'status': '引用未解析'})) for i in ids) + '</div>'
        rows.append(row + '</div><p class="muted">关系：AA 支撑 BA，AA 处理 IA，AA 依赖 TA。来源：应用服务的 process_ids / information_ids / technology_ids。</p></article>')
    apps = pack.get('applications', [])
    graph = '<h2>To-Be · 单应用跨域关系图</h2>' + architecture_graph(apps[0], lookup) if apps else ''
    return graph + '<h2>To-Be · 全部目标追溯</h2>' + (''.join(rows) or empty('目标架构')) + collection('跨应用集成关系', pack.get('integrations', [])) + '<h2>As-Is · 现状独立视图</h2>' + record(pack.get('as_is', {})) + '<h2>AI 横向视图</h2>' + record(pack.get('ai_overlay', {}))


def drawio(pack):
    """One page per application, with exact source edges and editable nodes."""
    root = ET.Element('mxfile', host='offline-review-workbench')
    lookup = {n['id']: n for key in ('processes', 'information_objects', 'applications', 'technology_services') for n in pack.get(key, []) if 'id' in n}
    for index, app in enumerate(pack.get('applications', [])):
        page = ET.SubElement(root, 'diagram', id=f'page-{index}', name=app.get('name', app['id']))
        model = ET.SubElement(page, 'mxGraphModel', adaptiveColors='auto')
        cells = ET.SubElement(model, 'root')
        ET.SubElement(cells, 'mxCell', id='0')
        ET.SubElement(cells, 'mxCell', id='1', parent='0')
        # Three spokes on separate sides of the AA hub; no implied BA/IA edges.
        groups = [(0, app.get('process_ids', []), 'BA'), (2, app.get('information_ids', []), 'IA'), (4, app.get('technology_ids', []), 'TA'), (1, [app['id']], 'AA')]
        for col, ids, domain in groups:
            for row, node_id in enumerate(ids):
                node = lookup.get(node_id, {'name': '引用未解析'})
                value = f'{domain}: {node.get("name", node_id)}\n{node_id}\n{node.get("status", "未提供状态")}'
                cell = ET.SubElement(cells, 'mxCell', id=node_id, value=value, vertex='1', parent='1', style='rounded=0;whiteSpace=wrap;html=0;')
                ET.SubElement(cell, 'mxGeometry', x=str(col * 180 + 40), y=str(row * 120 + 40), width='140', height='80', **{'as': 'geometry'})
        for field, label in [('process_ids', '支撑'), ('information_ids', '处理'), ('technology_ids', '依赖')]:
            for edge_index, target in enumerate(app.get(field, [])):
                cell = ET.SubElement(cells, 'mxCell', id=f'e-{field}-{edge_index}', source=app['id'], target=target, value=label, edge='1', parent='1', style='edgeStyle=orthogonalEdgeStyle;html=0;')
                ET.SubElement(cell, 'mxGeometry', relative='1', **{'as': 'geometry'})
    return ET.tostring(root, encoding='unicode')


def token_css(tokens):
    blocks = []
    for selector, mapping in [(':root', tokens['common'])] + [(f'[data-theme="{mode}"]', tokens['modes'][mode]) for mode in ('light', 'dark')]:
        values = []
        for key, value in mapping.items():
            if not re.fullmatch(r'[a-z0-9-]+', key) or not isinstance(value, str) or re.search(r'[;{}<>\\]|url\s*\(|@', value, re.I):
                raise ValueError('Unsafe CSS token')
            values.append(f'--ui-{key}:{value}')
        blocks.append(selector + '{' + ';'.join(values) + '}')
    return '\n'.join(blocks)


def render(pack, report, slides, tokens, sources, originals=None, process_diagrams=None):
    validate(pack, slides)
    process_diagrams = render_process_diagrams(pack.get('processes', [])) if process_diagrams is None else process_diagrams
    header = pack.get('artifact_header', {})
    title = next((line[2:] for line in report.splitlines() if line.startswith('# ')), '企业转型规划审阅')
    report_header = {}
    if report.startswith('---\n') and '\n---' in report[4:]:
        try:
            report_header = json.loads(report[4:].split('\n---', 1)[0])
        except json.JSONDecodeError:
            pass
    versions = {'pack': header, 'report': report_header, 'slides': {k: slides[k] for k in ('deck_id', 'version', 'mode', 'approval_ref', 'upstream_business_approval') if k in slides}}
    upstream_ids = [v for v in (header.get('artifact_id'), report_header.get('artifact_id'), slides.get('deck_id')) if isinstance(v, str)]
    metadata = {'artifact_id': header.get('project_id', 'unknown') + '-cross-cutting-review-001', 'artifact_type': 'consulting-review-workbench', 'project_id': header.get('project_id', 'unknown'), 'version': '1.0.0', 'status': 'draft', 'generated_by': {'skill_name': 'enterprise-ui-design', 'skill_version': '1.0.0', 'tool': 'render_review_workbench.py'}, 'upstream_artifact_ids': upstream_ids, 'upstream_artifact': header, 'source_versions': versions, 'sources': sources, 'evidence_ids': header.get('evidence_ids', []), 'assumption_ids': header.get('assumption_ids', []), 'review': {'reviewer': '未指定', 'decision': 'not-reviewed'}, 'human_gate': '未由本视图批准', 'theme_version': tokens.get('meta', {}).get('version', '未提供'), 'presentation_override': '企业蓝灰审阅主题；不修改源PPT主题或内容'}
    nav = [('report', '规划报告'), ('process', '四级流程'), ('architecture', '4A 架构'), ('organization', '组织绩效'), ('investment', '投资路线图'), ('slides', 'PPT 审阅')]
    originals = originals or {}
    downloads = '<div class="toolbar">' + ''.join(f'<button class="btn" data-download-source="{key}">{label}</button>' for key, label in [('report', '下载原始报告 Markdown'), ('pack', '下载原始规划底稿 JSON'), ('slides', '下载原始PPT内容包 JSON')] if key in originals) + '</div>'
    views = {'report': downloads + f'<article class="report">{markdown(report) if report else empty("报告")}</article>' + disclosure('来源与版本', metadata) + disclosure('人工 Gate 原始状态', pack.get('gates', {}))}
    views['process'] = f'<h1>四级流程 <span class="tag">{len(pack.get("processes", []))} 个节点</span></h1>' + (diagrams_html(process_diagrams) if process_diagrams else empty('流程图')) + '<details class="source process-details"><summary>全部流程字段与层级明细</summary><div class="toolbar"><button class="btn" id="expand-tree">展开全部层级</button><button class="btn" id="collapse-tree">收起全部层级</button></div>' + process_tree(pack.get('processes', [])) + '</details>'
    views['architecture'] = '<h1>4A 架构</h1><button class="btn" id="download-diagram">下载可编辑关系图 .drawio</button>' + architecture(pack)
    views['organization'] = '<h1>组织与绩效</h1><h2>决策责任矩阵</h2>' + table(pack.get('organization_decisions', []), [('decision', '决策'), ('A', '最终负责 A'), ('R', '执行负责 R'), ('boundary', '授权边界')]) + collection('完整 RACI 与升级路径', pack.get('organization_decisions', [])) + '<h2>KPI 基线与目标</h2>' + table(pack.get('kpis', []), [('name', '指标'), ('baseline', '基线'), ('target', '目标'), ('unit', '单位'), ('owner', '负责人'), ('status', '状态')]) + collection('KPI 计算口径、数据来源与约束', pack.get('kpis', []))
    financials = pack.get('financials', {})
    views['investment'] = '<h1>投资与路线图</h1><h2>波次与进入、退出条件</h2>' + table(pack.get('waves', []), [('name', '波次'), ('entry', '进入条件'), ('exit', '退出条件'), ('fte', '人力 FTE')]) + collection('过渡架构与波次明细', pack.get('waves', [])) + collection('转型举措', pack.get('initiatives', [])) + '<h2>年度现金评价 · ' + esc(financials.get('unit', '单位未提供')) + '</h2>' + table(financials.get('annual_cash_flow', []), [('year', '年份'), ('cost', '支出'), ('benefit', '收益'), ('net', '净现金'), ('cumulative', '累计现金')]) + record({k: v for k, v in financials.items() if k not in ('costs', 'benefits', 'annual_cash_flow', 'scenarios')}) + collection('情景假设与现金评价', financials.get('scenarios', [])) + disclosure('支出逐项依据', financials.get('costs', [])) + disclosure('收益逐项依据', financials.get('benefits', []))
    previews = []
    for slide in slides.get('slides', []):
        sid = slide['slide_id']
        previews.append(f'<article class="slide-review" data-slide-id="{esc(sid)}"><div class="slide-canvas"><p class="slide-meta">{esc(sid)} · {esc(slide.get("section", ""))} · {esc(slide.get("review_status", "未提供状态"))}</p><h2>{esc(slide.get("title", ""))}</h2><p class="key-message">{esc(slide.get("key_message", ""))}</p><ul class="slide-points">' + ''.join(f'<li>{esc(p)}</li>' for p in slide.get('supporting_points', [])) + f'</ul><p class="qualifier">{esc(slide.get("visible_qualifier", ""))}</p></div>' + disclosure('页面全部字段与来源', slide) + f'<label class="note-label">{esc(sid)} 审阅意见<textarea class="review-note" data-note-id="{esc(sid)}" rows="3" placeholder="记录修改意见；不会批准内容或启动图片生成"></textarea></label></article>')
    views['slides'] = '<h1>PPT 逐页审阅</h1><p class="notice">HTML 内容排版示意，使用企业蓝灰审阅主题。此视图不生成或批准最终图片PPT；审阅意见不构成人工 Gate 批准。</p><div class="toolbar"><label>审阅人 <input id="reviewer" autocomplete="name"></label><button class="btn primary" id="export-notes">导出审阅意见 JSON</button><span id="save-status" role="status"></span></div>' + (''.join(previews) or empty('PPT 内容包')) + disclosure('演示文稿版本、来源与审批原始状态', {k: v for k, v in slides.items() if k != 'slides'})
    data = {'metadata': metadata, 'slide_ids': [s['slide_id'] for s in slides.get('slides', [])], 'diagram': drawio(pack), 'originals': originals, 'process_diagram_files': diagram_files(process_diagrams, header)}
    notice = f'来源状态：{header.get("mode", "未提供模式")} / {header.get("data_status", "未提供数据状态")} / {header.get("status", "未提供版本状态")} · 人工 Gate：{header.get("human_gate", "未提供")}'
    return '<!doctype html><html lang="zh-CN" data-theme="light"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'unsafe-inline\'; script-src \'unsafe-inline\'; connect-src \'none\'; img-src data:; base-uri \'none\'; form-action \'none\'"><title>' + esc(title) + '</title><style>' + token_css(tokens) + ASSETS.joinpath('workbench.css').read_text() + '</style></head><body><a class="skip" href="#main">跳到内容</a><header class="topbar"><span>咨询过程审阅</span><button class="btn" id="theme-toggle" aria-pressed="false">切换深色</button></header><div class="shell"><nav aria-label="阅读视图">' + ''.join(f'<a href="#{key}" data-view="{key}">{label}</a>' for key, label in nav) + '</nav><main id="main" tabindex="-1"><p class="provenance">' + esc(notice) + '</p>' + ''.join(f'<section id="{key}" class="view" aria-label="{label}" {"" if key == "report" else "hidden"}>{views[key]}</section>' for key, label in nav) + '</main></div><script id="review-data" type="application/json">' + safe_json(data) + '</script><script>' + ASSETS.joinpath('workbench.js').read_text() + '</script></body></html>'


def build(pack_path, report_path, slides_path, tokens_path, out, diagram_engine=None):
    sources = {}
    originals = {}
    def load(path, label, optional=False, json_format=True):
        if not path or not Path(path).is_file():
            if not optional:
                raise ValueError(f'Missing required input: {label}')
            sources[label] = {'status': 'missing', 'path': str(path or '')}
            return {} if json_format else ''
        raw = Path(path).read_bytes()
        sources[label] = {'path': str(Path(path).resolve()), 'sha256': hashlib.sha256(raw).hexdigest(), 'status': 'provided'}
        if label != 'tokens':
            originals[label] = raw.decode('utf-8')
        return json.loads(raw) if json_format else raw.decode('utf-8')
    pack = load(pack_path, 'pack')
    report = load(report_path, 'report', True, False)
    slides = load(slides_path, 'slides', True)
    tokens = load(tokens_path, 'tokens')
    validate(pack, slides)
    process_diagrams = render_process_diagrams(pack.get('processes', []), diagram_engine)
    output = render(pack, report, slides, tokens, sources, originals, process_diagrams)
    out = Path(out)
    if out.resolve() in {Path(p).resolve() for p in (pack_path, report_path, slides_path, tokens_path) if p}:
        raise ValueError('Output must not overwrite an input')
    out.parent.mkdir(parents=True, exist_ok=True)
    if process_diagrams:
        files = diagram_files(process_diagrams, pack.get('artifact_header', {}))
        diagrams_dir = out.parent / 'diagrams'
        # Refuse to overwrite edited or previously approved diagram artifacts.
        for name, content in files.items():
            target = diagrams_dir / name
            if target.exists() and target.read_text(encoding='utf-8') != content:
                raise ValueError(f'Diagram output exists with different content: {target}; use a new output directory')
        diagrams_dir.mkdir(exist_ok=True)
        for name, content in files.items():
            target = diagrams_dir / name
            if not target.exists():
                target.write_text(content, encoding='utf-8')
    with tempfile.NamedTemporaryFile('w', encoding='utf-8', dir=out.parent, delete=False) as tmp:
        tmp.write(output)
        temporary = Path(tmp.name)
    temporary.replace(out)
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pack', required=True, type=Path)
    parser.add_argument('--report', type=Path)
    parser.add_argument('--slides', type=Path)
    parser.add_argument('--tokens', required=True, type=Path)
    parser.add_argument('--out', required=True, type=Path)
    parser.add_argument('--diagram-engine', type=Path, help='Explicit enterprise-diagrams skill directory or diagram_svg.py path')
    args = parser.parse_args()
    try:
        print(build(args.pack, args.report, args.slides, args.tokens, args.out, args.diagram_engine))
    except (ValueError, OSError, KeyError, TypeError) as exc:
        parser.exit(1, f'Render failed: {exc}\n')


if __name__ == '__main__':
    main()
