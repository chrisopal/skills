#!/usr/bin/env python3
"""Render current candidate outlines and chapter drafts as a portable local report."""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
import re
import zipfile
from pathlib import Path
from urllib.parse import urlparse
from xml.etree import ElementTree

from outline_view import ordered_sections
from writing_checks import inside
from writing_workspace import WritingWorkspace

ROOT = Path(__file__).resolve().parents[1]


def esc(value):
    return html.escape(str(value), quote=True)


def safe_editor_url(value):
    parsed = urlparse(value)
    if (parsed.scheme != 'http' or parsed.hostname != '127.0.0.1' or parsed.username
            or parsed.password or parsed.query or parsed.fragment or parsed.path not in ('', '/')):
        raise ValueError('编辑器地址必须为不带凭据的127.0.0.1本地HTTP地址')
    return value


def outline_html(sections, written_sections=()):
    rows = ordered_sections(sections)
    children = {}
    for row in rows:
        children.setdefault(row.get('parent_id'), []).append(row)

    def branch(parent):
        result = '<ul class="outline">'
        for row in children.get(parent, []):
            label = (f'<span class="number">{esc(row["display_number"])}</span>'
                     f'<span class="title">{esc(row.get("title", ""))}</span>'
                     f'<small>{"已写草稿" if row["id"] in written_sections else "未写"}</small>')
            result += f'<li data-section-id="{esc(row["id"])}">'
            if row['children_count']:
                result += ('<details open><summary class="outline-row outline-summary">'
                           + label + '</summary>' + branch(row['id']) + '</details>')
            else:
                result += '<div class="outline-row outline-leaf">' + label + '</div>'
            result += '</li>'
        return result + '</ul>'
    return branch(None)


def body_html(markdown, title):
    result = []
    for paragraph in markdown.split('\n\n'):
        heading = re.fullmatch(r'#{1,6}\s+([^\n]+)', paragraph.strip())
        if heading:
            if heading[1] != title:
                result.append('<h3>' + esc(heading[1]) + '</h3>')
        elif paragraph.strip():
            result.append('<p>' + esc(paragraph.strip()) + '</p>')
    return ''.join(result)


def response_html(responses, requirements):
    labels = {'satisfied': '拟议满足', 'partial': '部分响应',
              'missing': '未响应', 'unknown': '待确认'}
    return ''.join('<tr><td>' + esc(requirements[r['requirement_id']]['text']) + '</td><td>'
                   + esc(r['response']) + '</td><td>' + esc(labels.get(r.get('fulfillment'), '待复核'))
                   + ('<br>' + esc(r['deviation']) if r.get('deviation') else '') + '</td></tr>'
                   for r in responses)


def documents_current(project, document, project_id):
    project = Path(project).resolve()
    pages = document.get('pages')
    if (document.get('project_id') != project_id or isinstance(pages, bool)
            or not isinstance(pages, int) or pages <= 0):
        return False
    files = {}
    for label, relative in [('writing', 'artifacts/11-technical-content.json'),
                            ('visuals', 'artifacts/13-visuals.json'),
                            ('docx', document.get('docx')), ('pdf', document.get('pdf'))]:
        file = inside(project, relative) if relative else None
        if (not file or not file.is_file()
                or hashlib.sha256(file.read_bytes()).hexdigest() != document.get(label + '_sha256')):
            return False
        files[label] = file
    if files['docx'].suffix.lower() != '.docx' or files['pdf'].suffix.lower() != '.pdf':
        return False
    if not files['pdf'].read_bytes().startswith(b'%PDF-'):
        return False
    try:
        with zipfile.ZipFile(files['docx']) as archive:
            types = ElementTree.fromstring(archive.read('[Content_Types].xml'))
            content_type = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml'
            if not any(node.get('PartName') == '/word/document.xml'
                       and node.get('ContentType') == content_type
                       for node in types.findall('{http://schemas.openxmlformats.org/package/2006/content-types}Override')):
                return False
            body = ElementTree.fromstring(archive.read('word/document.xml'))
            return body.tag == '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}document'
    except (OSError, KeyError, zipfile.BadZipFile, ElementTree.ParseError):
        return False


def render_project(project, editor_url, output='reports/writing-test-report.html'):
    project = Path(project).resolve()
    target = inside(project, output)
    state = WritingWorkspace(project, 'artifacts/08-outline.json',
                             'artifacts/11-technical-content.json').state()
    coverage = state['coverage']
    if not coverage.get('structural_valid'):
        raise ValueError('当前写作依赖无效，先修复再生成报告：' + str(coverage.get('errors')))
    title = state['project']['project_name']
    writing = state['writing']
    chapters = writing['data']['chapters']
    sections = state['outline']['data']['sections']
    nav = outline_html(sections, {c['section_id'] for c in chapters})

    def link(relative):
        source = inside(project, relative)
        if not source.is_file():
            raise ValueError('报告文件不存在：' + str(relative))
        return esc(Path(os.path.relpath(source, target.parent)).as_posix())

    actions = f'<a class="primary" href="{esc(safe_editor_url(editor_url))}">打开章节编辑器</a>'
    document_path = project / 'work/writing-document-result.json'
    document_note = '尚无当前版本文档。'
    if document_path.is_file():
        document = json.loads(document_path.read_text())
        current = documents_current(project, document, state['project']['project_id'])
        if current:
            actions += f'<a href="{link(document["docx"])}">可编辑 Word</a><a href="{link(document["pdf"])}">PDF 工作稿</a>'
            document_note = (f'当前工作稿 {esc(document["pages"])} 页；文档检查：'
                             f'{esc(document.get("visual_qa", "未验收"))}。')
        else:
            document_note = '已有文档的版本、哈希、文件类型或页数记录无效，需重新生成和检查。'
    if (project / 'reports/tender-report.html').is_file():
        actions += f'<a href="{link("reports/tender-report.html")}">招标理解报告</a>'
    req = {r['id']: r for r in state['requirements']['data']['requirements']}
    chapter_html = ''.join(f'<section class="panel"><h2>{esc(c["title"])}</h2>'
                          f'<div class="chapter-body">{body_html(c["body_markdown"], c["title"])}</div></section>'
                          for c in chapters)
    figures = ''
    for figure in state['visuals']['data'].get('figures', []):
        figures += f'<section class="panel"><h2>{esc(figure["title"])}</h2>'
        if figure.get('rendered_path') and inside(project, figure['rendered_path']).suffix.lower() in ('.png', '.jpg', '.jpeg'):
            figures += f'<img alt="{esc(figure.get("alt_text", ""))}" src="{link(figure["rendered_path"])}">'
        figures += f'<p class="muted">{esc(figure.get("caption", ""))}</p>'
        if figure.get('source_path'):
            figures += f'<a href="{link(figure["source_path"])}">可编辑图源</a>'
        figures += '</section>'
    rows = response_html(writing['data'].get('responses', []), req)
    gaps = ''.join('<li>' + esc(gap) + '</li>' for gap in coverage.get('evidence_gaps', []) + coverage.get('unresolved_claims', []))
    visual = state['settings']['visuals']
    config_note = ('配图已启用' if visual['enabled'] else '配图已关闭') + '；概念生图：' + ('宿主工具' if visual['image_mode'] == 'host' else '关闭')
    config_note += f'；模型偏好：{visual["model"] or "由宿主选择"}；比例：{visual["aspect_ratio"]}；最多{visual["max_images"]}张。'
    css = (ROOT / 'assets/ui/writing-report.css').read_text()
    page = f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{esc(title)}｜写作测试</title><style>{css}</style>
<header><small>投标编制 · 目录与写作测试</small><h1>{esc(title)}</h1><span class="tag">候选工作稿 · 未正式采纳</span><div class="actions">{actions}</div></header>
<main><section class="panel"><div class="stats"><div><b>{len(sections)}</b>候选目录节点</div><div><b>{coverage['outline_mapped_count']}/{coverage['requirement_count']}</b>需求已规划</div><div><b>{coverage['written_requirement_count']}</b>需求已关联草稿</div><div><b>{len(coverage['planned_not_written'])}</b>需求尚未写作</div></div><p class="muted">目录映射不代表正文充分响应或已获得评分。</p></section>
<div class="grid"><aside class="panel"><h2>候选目录</h2>{nav}<a href="{link('artifacts/08-outline.md')}">查看全部章节任务卡</a></aside><div>
<section class="panel"><h2>当前工作稿</h2><p>{document_note}</p><p>段落追溯：{'有效' if coverage['trace_state'] == 'current' else '需复核'}；整标内容充分性与正式交付未验收。</p><details><summary>版本与证据记录</summary><p>正文版本 {writing['revision']}；{esc(writing['sha256'])}</p><a href="{link('work/writing-coverage.json')}">覆盖检查</a></details></section>
<section class="panel"><h2>配图配置</h2><p>{esc(config_note)}</p><p class="muted">配置偏好不代表工具可用或图片已生成。当前图表以实际产物为准。</p></section>
{chapter_html}{figures}<section class="panel"><h2>逐项响应</h2><div class="table-scroll"><table><thead><tr><th>招标要求</th><th>拟议响应</th><th>状态</th></tr></thead><tbody>{rows}</tbody></table></div></section>
<section class="panel"><h2>材料与内容缺口</h2><ul>{gaps}</ul></section></div></div></main></html>'''
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(page, encoding='utf-8')
    return target


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, required=True)
    parser.add_argument('--editor-url', required=True)
    parser.add_argument('--out', default='reports/writing-test-report.html')
    args = parser.parse_args()
    print(render_project(args.project, args.editor_url, args.out))


if __name__ == '__main__':
    main()
