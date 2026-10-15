#!/usr/bin/env python3
"""Render a read-only review report from current, source-bound review JSON.

This is a presentation tool, not a review or release gate. It uses only the
given core matrix and findings; it never calculates scores or closes issues.
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
from pathlib import Path
from validate_output import validate

ROOT = Path(__file__).resolve().parents[1]


CONCLUSIONS = {
    'satisfied': ('满足', 'ok'), 'partial': ('部分支撑', 'pending'),
    'missing': ('缺失', 'risk'), 'not_met': ('未满足', 'risk'),
    'unknown': ('待核验', 'pending'), 'not_applicable': ('不适用', 'neutral'),
}
GROUPS = {'compliance': '资格与合规', 'materials': '关键材料', 'scoring': '评分条件'}
SEVERITIES = {'blocking': '阻塞', 'warning': '风险', 'advisory': '建议'}
STATES = {'open': '未关闭', 'resolved': '已复核', 'accepted_warning': '已接受风险'}
RECOMMENDATIONS = {'blocked': '暂不能建议正式交付', 'needs_review': '仍需复核',
                   'eligible_for_user_release': '可交用户决定正式交付', 'draft_only': '仅供内部工作稿使用'}

CSS = '''
:root{--ink:#24323e;--muted:#61717b;--line:#dbe2e5;--accent:#23584d;
 --risk:#9b4438;--pending:#805f22;--body:18px;--label:16px}
*{box-sizing:border-box}body{margin:0;background:#edf1f0;color:var(--ink);
 font:var(--body)/1.65 "PingFang SC","Microsoft YaHei",Arial,sans-serif}
main{width:min(960px,100%);margin:28px auto;background:white;padding:40px}
h1,h2,h3,p{margin:0}h1{font-size:28px;line-height:1.35;font-weight:600}
h2{font-size:22px;line-height:1.5;font-weight:600}h3{font-size:18px;line-height:1.6;font-weight:600}
.eyebrow,.meta,.label,.tag,summary,thead{font-size:var(--label)}
.eyebrow{color:var(--accent);letter-spacing:.08em;margin-bottom:8px}
.meta{color:var(--muted);margin-top:8px}.notice{padding:14px 18px;margin:22px 0;
 background:#f5f7f6;border-left:3px solid var(--accent)}
.section{padding:28px 0;border-bottom:1px solid var(--line)}.section:last-child{border:0}
.section-head{display:flex;gap:12px;align-items:baseline;justify-content:space-between;margin-bottom:16px}
.section-head .meta{margin:0}.decision{padding:18px 20px;background:#f8f4ef;border-left:3px solid #a37c46;
 margin-bottom:20px}.decision h2{margin-bottom:6px}.decision p{color:#66584a}
.counts{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-bottom:22px}
.count{border-top:2px solid var(--line);padding-top:10px}.count .label{color:var(--muted)}
.count strong{font-size:22px;font-weight:600;margin-right:6px}
table{border-collapse:collapse;width:100%;table-layout:fixed}th,td{text-align:left;vertical-align:top;
 padding:12px 10px;border-bottom:1px solid var(--line);overflow-wrap:anywhere}
th{color:var(--muted);font-weight:500;background:#f7f9f8}.matrix th:nth-child(1){width:21%}
.matrix th:nth-child(3){width:19%}.row-id{color:var(--muted);font-size:var(--label)}
.tag{display:inline-block;font-weight:500;white-space:nowrap}.risk{color:var(--risk)}
.pending{color:var(--pending)}.ok{color:var(--accent)}.neutral{color:var(--muted)}
.item{padding:20px 0;border-top:1px solid var(--line)}.item:first-of-type{border-top:0;padding-top:0}
.item-head{display:flex;align-items:baseline;justify-content:space-between;gap:12px;margin-bottom:12px}
.item-head .meta{margin:0}.field{display:grid;grid-template-columns:88px minmax(0,1fr);gap:12px;margin-top:12px}
.label{color:var(--muted);font-weight:500}.field p{overflow-wrap:anywhere}
details{margin-top:14px}summary{color:var(--accent);cursor:pointer}details[open] summary{margin-bottom:10px}
.evidence{padding:12px 14px;background:#f7f9f8;margin-top:8px;overflow-wrap:anywhere}
.evidence .meta{margin-top:4px}.issue-list{margin:0;padding-left:22px}.issue-list li{margin:8px 0}
.foot{margin-top:18px;color:var(--muted);font-size:var(--label)}
@media(max-width:700px){main{margin:0;padding:24px}.section-head{display:block}
 .section-head .meta{margin-top:6px}.matrix th:nth-child(1){width:22%}.matrix th:nth-child(3){width:20%}
 .field{grid-template-columns:80px minmax(0,1fr);gap:8px}}
@page{size:A4;margin:18mm 17mm}
@media print{body{background:white;--body:10.5pt;--label:9.5pt;line-height:1.55}
 main{width:auto;margin:0;padding:0}h1{font-size:19pt}h2{font-size:14pt}h3{font-size:11pt}
 .count strong{font-size:14pt}.section{padding:16pt 0}.item{padding:12pt 0}
 .section-head,.item-head,h1,h2,h3,summary{break-after:avoid}
 .decision,.counts,.notice,.evidence,.field,tr{break-inside:avoid}
 thead{display:table-header-group}tfoot{display:table-footer-group}
 #scoring{break-before:page}.item{break-inside:avoid}details,details>*{display:block!important}
 summary{cursor:default}details{margin-top:9pt}.meta,.foot{color:#53616a}
 *{-webkit-print-color-adjust:exact;print-color-adjust:exact}}
'''


def esc(value):
    return html.escape(str(value), quote=True)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inside(project, relative):
    if not isinstance(relative, str) or not relative.strip():
        raise ValueError('输入路径缺失')
    rel = Path(relative)
    path = (project / rel).resolve()
    if rel.is_absolute() or '..' in rel.parts or not path.is_relative_to(project):
        raise ValueError('输入路径越界：' + relative)
    if not path.is_file():
        raise ValueError('输入不存在：' + relative)
    return path


def load_bound(project, path, skill_id):
    data = json.loads(path.read_text(encoding='utf-8'))
    if data.get('skill_id') != skill_id:
        raise ValueError('报告技能身份不匹配')
    schema = ROOT / 'skills' / skill_id / 'assets/output.schema.json'
    if not schema.is_file():
        filename = 'scoring.schema.json' if skill_id == 'bid-scoring' else 'review.schema.json'
        if skill_id == 'bid-review-remediation' and ROOT.name == skill_id:
            filename = 'output.schema.json'
        schema = ROOT / 'assets' / filename
    errors = validate(data, json.loads(schema.read_text(encoding='utf-8')))
    if errors:
        raise ValueError('报告结构或业务状态矛盾：' + '; '.join(errors))
    metadata = project / 'work/project.json'
    if metadata.is_file() and json.loads(metadata.read_text()).get('project_id') != data.get('project_id'):
        raise ValueError('报告与项目身份不一致')
    if data.get('status') in {'stale', 'superseded', 'invalid'}:
        raise ValueError('报告版本已失效')
    if not data.get('inputs'):
        raise ValueError('报告没有冻结输入')
    frozen = set()
    for item in data['inputs']:
        source = inside(project, item['relative_path'])
        if digest(source) != item['sha256']:
            raise ValueError('输入哈希已变化：' + item['relative_path'])
        frozen.add(item['sha256'])
    rows = [row for group in data.get('data', {}).get('core_matrix', {}).values() for row in group]
    rows += data.get('data', {}).get('findings', []) + data.get('data', {}).get('items', [])
    for row in rows:
        for ref in row.get('bid_refs', []):
            if digest(inside(project, ref['relative_path'])) != ref['sha256'] or ref['sha256'] not in frozen:
                raise ValueError('正文引用版本不属于冻结输入')
        for source in row.get('sources', row.get('evidence', [])):
            if source.get('sha256') not in frozen:
                raise ValueError('引文来源不属于冻结输入')
    return data


def tag(conclusion):
    label, color = CONCLUSIONS.get(conclusion, ('待核验', 'pending'))
    return f'<span class="tag {color}">{esc(label)}</span>'


def evidence_html(row):
    blocks = []
    for source in row.get('sources', row.get('evidence', [])):
        blocks.append(f'<div class="evidence"><p>{esc(source.get("quote", ""))}</p>'
                      f'<p class="meta">来源：{esc(source.get("source_id", ""))} · '
                      f'{esc(source.get("location", ""))}</p></div>')
    for ref in row.get('bid_refs', []):
        blocks.append(f'<div class="evidence"><p>{esc(ref.get("quote", ""))}</p>'
                      f'<p class="meta">现稿：{esc(ref.get("relative_path", ""))} · '
                      f'{esc(ref.get("location", ""))}</p></div>')
    if not blocks:
        blocks.append('<p class="meta">本行没有可回读引文，需补充核验依据。</p>')
    return '<details><summary>查看原文、现稿与证据定位</summary>' + ''.join(blocks) + '</details>'


def build_page(review, scoring=None, title='标书评审报告'):
    data = review['data']
    matrix = data.get('core_matrix')
    if not isinstance(matrix, dict) or any(not isinstance(matrix.get(k), list) for k in GROUPS):
        raise ValueError('评审缺少三张核心矩阵，不能用空页面掩盖未审范围')
    findings = data.get('findings', [])
    by_id = {f['id']: f for f in findings}
    if len(by_id) != len(findings):
        raise ValueError('问题ID重复')
    metadata = {i['id']: i for i in (scoring or {}).get('data', {}).get('items', [])}
    for group, rows in matrix.items():
        ids = [r['target_id'] for r in rows]
        if len(ids) != len(set(ids)):
            raise ValueError('矩阵目标重复：' + group)
        for row in rows:
            if row.get('conclusion') not in CONCLUSIONS:
                raise ValueError('评审结论无效')
            if any(fid not in by_id for fid in row.get('finding_ids', [])):
                raise ValueError('矩阵引用了不存在的问题')
    if scoring:
        leaves = {i['id'] for i in metadata.values() if i.get('node_type') == 'scored'}
        if leaves != {r['target_id'] for r in matrix['scoring']}:
            raise ValueError('评分计分叶子与评审矩阵不一致')
    total = sum(len(matrix[k]) for k in GROUPS)
    open_count = sum(f.get('state') not in {'closed', 'resolved'} for f in findings)
    blocking = sum(f.get('severity') == 'blocking' and f.get('state') not in {'closed', 'resolved'} for f in findings)
    recommendation = data.get('release_recommendation', 'needs_review')
    decision = RECOMMENDATIONS.get(recommendation, '交付建议需复核')
    synthetic = any(s.get('kind') == 'synthetic' for rows in matrix.values()
                    for r in rows for s in r.get('sources', []))
    scope = '限定范围评审' if data.get('review_scope') == 'limited' else '以本轮登记输入为评审范围'
    if synthetic:
        scope += ' · 合成演示资料'
    top = (f'<header><p class="eyebrow">投标工作稿 · 评审记录</p><h1>{esc(title)}</h1>'
           f'<p class="meta">{esc(scope)} · 第 {esc(review.get("revision", ""))} 版</p></header>')
    overview = f'<section class="section" id="overview"><div class="decision"><h2>{esc(decision)}</h2>'
    overview += '<p>以下结论只对应当前输入。评分覆盖状态与实际得分分开记录。</p></div>'
    overview += f'<div class="counts"><div class="count"><p class="label">逐项结论</p><p><strong>{total}</strong>项</p></div>'
    overview += f'<div class="count"><p class="label">未关闭问题</p><p><strong>{open_count}</strong>项</p></div>'
    overview += f'<div class="count"><p class="label">阻塞问题</p><p><strong>{blocking}</strong>项</p></div></div>'
    overview += '<div class="section-head"><h2>评审概览</h2><p class="meta">资格、材料与评分分别判断</p></div>'
    overview += '<table class="matrix"><thead><tr><th>类别</th><th>核验对象</th><th>当前结论</th></tr></thead><tbody>'
    for group in GROUPS:
        for row in matrix[group]:
            item = metadata.get(row['target_id'], {})
            sources = row.get('sources', [])
            label = item.get('title') or (sources[0].get('quote') if sources else None) or row['target_id']
            overview += f'<tr><td>{GROUPS[group]}</td><td>{esc(label)}</td><td>{tag(row["conclusion"])}</td></tr>'
    overview += '</tbody></table><p class="foot">缺失、部分支撑和待核验仍需处理；整改建议不等于问题已关闭。</p></section>'
    sections = []
    for group in ('scoring', 'compliance', 'materials'):
        heading = '评分项逐项评审' if group == 'scoring' else GROUPS[group] + '逐项评审'
        section = f'<section class="section" id="{group}"><div class="section-head"><h2>{heading}</h2>'
        if group == 'scoring':
            section += '<p class="meta">原文最高分 ≠ 已得分</p>'
        section += '</div>'
        if group == 'scoring' and (synthetic or data.get('review_scope') == 'limited'):
            section += f'<p class="meta">{esc(scope)}</p>'
        for row in matrix[group]:
            item = metadata.get(row['target_id'], {})
            section += f'<article class="item"><div class="item-head"><h3>{esc(item.get("title", row["target_id"]))}</h3>'
            section += tag(row['conclusion']) + '</div>'
            if item:
                maximum = item.get('max_score')
                if maximum is not None:
                    section += f'<p class="meta">原文最高分 {esc(maximum)} 分</p>'
                section += f'<div class="field"><p class="label">评分条件</p><p>{esc(item.get("rule_text", ""))}</p></div>'
            section += f'<div class="field"><p class="label">本轮判断</p><p>{esc(row.get("rationale", ""))}</p></div>'
            linked = [by_id[f] for f in row.get('finding_ids', [])]
            actions = list(dict.fromkeys(f.get('remediation', '') for f in linked if f.get('remediation')))
            if actions:
                section += '<details><summary>整改安排与问题跟踪</summary><ul class="issue-list">'
                section += ''.join(f'<li>{esc(a)}</li>' for a in actions) + '</ul></details>'
            section += evidence_html(row) + '</article>'
        if not matrix[group]:
            section += '<p>本轮没有登记此类逐项结论；须结合实际评审范围复核。</p>'
        sections.append(section + '</section>')
    issue_section = '<section class="section" id="findings"><div class="section-head"><h2>问题与整改记录</h2></div>'
    for f in findings:
        issue_section += '<article class="item"><div class="item-head">'
        issue_section += f'<h3>{esc(f["id"])} · {esc(SEVERITIES.get(f.get("severity"), "待判断"))}</h3>'
        issue_section += f'<span class="tag neutral">{esc(STATES.get(f.get("state"), "待复核"))}</span></div>'
        issue_section += f'<p>{esc(f.get("description", ""))}</p>'
        issue_section += f'<div class="field"><p class="label">整改</p><p>{esc(f.get("remediation", ""))}</p></div>'
        issue_section += evidence_html(f) + '</article>'
    issue_section += '</section>'
    checks = '<section class="section"><h2>复核记录</h2><table><thead><tr><th>检查</th><th>记录</th></tr></thead><tbody>'
    for check in data.get('checks', []):
        state = {'passed': '已检查', 'failed': '发现缺口', 'unknown': '待核验', 'not_applicable': '不适用'}.get(check.get('state'), '待核验')
        checks += f'<tr><td>{esc(check.get("area", ""))}<p class="meta">{state}</p></td><td>{esc(check.get("note", ""))}</td></tr>'
    checks += '</tbody></table></section>'
    limitations = '<section class="section"><h2>范围与版本</h2><p class="meta">' + esc(review['summary']) + '</p>'
    limitations += '<ul class="issue-list">' + ''.join(f'<li>{esc(v)}</li>' for v in data.get('limitations', [])) + '</ul>'
    for heading, key in (('当前阻塞', 'blockers'), ('提醒', 'warnings')):
        if review.get(key):
            limitations += f'<h3>{heading}</h3><ul class="issue-list">' + ''.join(f'<li>{esc(v)}</li>' for v in review[key]) + '</ul>'
    limitations += '<p class="foot">排版工具只呈现既有评审数据。输入哈希检查不代替逐项业务复核、真实性认证或正式交付授权。</p></section>'
    return ('<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>{esc(title)}</title><style>{CSS}</style></head><body><main>' + top + overview +
            ''.join(sections) + issue_section + checks + limitations + '</main></body></html>')


def generate(project, review_path, output, scoring_path=None, title='标书评审报告'):
    project = project.expanduser().resolve()
    review = load_bound(project, review_path, 'bid-review-remediation')
    scoring = load_bound(project, scoring_path, 'bid-scoring') if scoring_path else None
    if scoring and review.get('project_id') != scoring.get('project_id'):
        raise ValueError('评分与评审项目不同')
    if scoring:
        relative = scoring_path.resolve().relative_to(project).as_posix()
        matching = [i for i in review['inputs'] if i['relative_path'] == relative]
        if len(matching) != 1 or any(matching[0].get(k) != scoring.get(k) for k in ('artifact_id', 'revision')) or matching[0]['sha256'] != digest(scoring_path):
            raise ValueError('评分产物不是评审冻结的确切版本')
    if output.exists():
        raise ValueError('请使用新的输出版本，拒绝覆盖已有报告')
    page = build_page(review, scoring, title)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(page, encoding='utf-8')
    return {'output': str(output), 'sha256': digest(output), 'review_sha256': digest(review_path),
            'presentation_only': True, 'semantic_review': 'NOT_RUN', 'visual_qa': 'NOT_RUN'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, required=True)
    parser.add_argument('--review', type=Path, required=True)
    parser.add_argument('--scoring', type=Path)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--title', default='标书评审报告')
    args = parser.parse_args()
    print(json.dumps(generate(args.project, args.review, args.out, args.scoring, args.title), ensure_ascii=False))


if __name__ == '__main__':
    main()
