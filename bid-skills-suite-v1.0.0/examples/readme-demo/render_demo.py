#!/usr/bin/env python3
"""Build documentation views from the published synthetic output snapshot.

This presents existing outputs; it does not run an agent, review a bid, or export Word.
Run from any directory with Python 3.10+; no additional dependencies are needed.
"""
from __future__ import annotations

import html
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SUITE = ROOT.parents[1]
sys.path.insert(0, str(SUITE / "scripts"))
from outline_view import ordered_sections
from render_writing_report import body_html, outline_html


def esc(value):
    return html.escape(str(value), quote=True)


def data(relative):
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))["data"]


CSS = """+:root{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI','PingFang SC',sans-serif;color:#0b1220;background:#f5f7fa;font-size:14px;line-height:1.65}
*{box-sizing:border-box}body{margin:0}a{color:#0966d9;text-decoration:none}a:hover{text-decoration:underline}
header{position:sticky;top:0;background:#fff;border-bottom:1px solid #d9dee7;padding:14px 32px;z-index:2;display:flex;justify-content:space-between;align-items:center;gap:16px}
header strong{font-size:16px}header span,.muted{color:#526075}nav{position:fixed;top:62px;bottom:0;width:220px;background:#fff;border-right:1px solid #d9dee7;padding:20px 16px;overflow:auto}
nav a{display:block;padding:8px 12px;margin-bottom:4px;color:#526075;border-radius:4px}nav a.active{background:#edf4ff;color:#0966d9;font-weight:600}
main{margin-left:220px;padding:28px 32px;max-width:1500px}h1{font-size:24px;line-height:1.4;margin:0 0 8px}h2{font-size:16px;margin:0 0 12px}h3{font-size:15px;margin:20px 0 8px}p{margin:8px 0 12px}
.lead{margin-bottom:20px}.panel{background:#fff;border:1px solid #d9dee7;border-radius:6px;padding:20px;margin-bottom:20px}.notice{border-left:3px solid #a9650a;background:#fff9eb;padding:10px 16px;margin:16px 0;color:#73480b}
.facts{display:grid;grid-template-columns:repeat(4,1fr);gap:20px}.facts b{display:block;font-size:24px;line-height:1.4;font-weight:600}.facts span{color:#526075;font-size:13px}
table{border-collapse:collapse;width:100%}th,td{border-bottom:1px solid #e7eaf0;padding:10px 12px;text-align:left;vertical-align:top}th{background:#f5f7fa;font-size:13px;color:#526075}code{font-family:ui-monospace,monospace;font-size:12px;overflow-wrap:anywhere}
.tag{display:inline-block;border:1px solid #d9dee7;border-radius:3px;padding:1px 7px;font-size:12px;color:#526075}.amber{color:#a9650a;border-color:#edd4a5;background:#fff9eb}.links{display:flex;gap:20px;flex-wrap:wrap;margin:12px 0}
.two{display:grid;grid-template-columns:1fr 1fr;gap:20px}.figure{display:block;width:100%;height:420px;object-fit:contain;background:#fff}.paper{width:100%;display:block;border:1px solid #d9dee7}.source{white-space:pre-wrap;font:14px/1.8 inherit;max-width:980px}.chapter{max-width:920px}.chapter p{white-space:pre-line}
.outline{list-style:none;padding:0;margin:0}.outline .outline{padding-left:28px;border-left:1px solid #d9dee7;margin-left:12px}.outline-row{display:flex;align-items:center;gap:12px;padding:10px 8px;border-bottom:1px solid #e7eaf0}.outline .number{font-variant-numeric:tabular-nums;min-width:32px;color:#526075}.outline .title{flex:1}.outline small{color:#68758a}.outline summary{cursor:pointer}.outline summary:before{content:'▾';color:#68758a}.outline-leaf{padding-left:28px}
@media(max-width:900px){nav{position:static;width:auto;border-right:0;display:flex;flex-wrap:wrap;padding:8px}nav a{padding:4px 8px}header{position:static;padding:12px 16px;display:block}main{margin:0;padding:16px}.facts{grid-template-columns:repeat(2,1fr)}.two{grid-template-columns:1fr}.figure{height:auto}.panel{overflow:auto}}
"""


def page(name, title, subtitle, content):
    pages = [("index", "案例与输入"), ("outline", "目录与任务卡"),
             ("writing", "章节草稿"), ("visuals", "流程图与界面图"), ("export", "Word / PDF 样稿")]
    nav = "".join(f'<a class="{"active" if name == key else ""}" href="{key}.html">{label}</a>'
                  for key, label in pages)
    nav += '<a href="reports/tender-report.html">招标理解报告 ↗</a><a href="reports/repair-review-report.html">逐项评审报告 ↗</a>'
    text = f'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><link rel="icon" href="data:,"><title>{esc(title)} · 模拟案例</title><style>{CSS}</style></head>
<body><header><strong>投标编制 Skill · 输出示例</strong><span>青禾园区事件闭环平台 · 全部为模拟资料</span></header><nav aria-label="示例导航">{nav}</nav><main>
<div class="lead"><h1>{esc(title)}</h1><p class="muted">{esc(subtitle)}</p></div>{content}
<p class="muted">此页面仅展示已保存的示例产物，不执行写作或评审。章节为候选稿，未正式采纳；不用于真实投标。</p></main></body></html>'''
    (ROOT / f"{name}.html").write_text(text, encoding="utf-8")


def main():
    source = (ROOT / "inputs/tender.md").read_text(encoding="utf-8")
    page("index", "从一份模拟招标文件开始", "单一标包 · 软件集成 + 一年运维服务 · 原文和输出均可下载核对", f'''
<section class="panel facts"><div><b>100 万元</b><span>模拟采购预算</span></div><div><b>60 天</b><span>实施期（日历日）</span></div><div><b>12 条</b><span>抽取后的原子需求</span></div><div><b>100 分</b><span>9 个计分叶子合计</span></div></section>
<div class="notice">演示范围：完成招标理解、目录、4.1 单章候选稿、两张配图及六页 Word/PDF 样稿。其余章节未写，企业材料缺失，评审保持阻塞。</div>
<section class="panel"><h2>模拟输入原文</h2><div class="links"><a href="inputs/tender.md">Markdown 原文</a><a href="inputs/SRC-001-模拟招标文件.docx">DOCX 原件</a><a href="reports/tender-report.html">查看解析报告 →</a></div><div class="source">{esc(source)}</div></section>''')
    outline = data("artifacts/08-outline.json")["sections"]
    writing = data("artifacts/11-technical-content.json")
    task = next(row for row in ordered_sections(outline) if row["id"] == "SEC-4-1")
    page("outline", "强制目录 → 章节任务卡", "保留原文强制结构，再把需求、评分条件、材料和配图要求映射到章节", f'''
<div class="two"><section class="panel"><h2>候选目录 · 9 个节点</h2>{outline_html(outline, ["SEC-4-1"])}</section><section class="panel"><h2>4.1 事件闭环管理 · 任务卡</h2>
<p><span class="tag amber">仅本章已有候选稿</span></p><h3>本章需要写什么</h3><p>{esc(task["task"])}</p>
<h3>关联需求</h3><p>{esc(' / '.join(task['requirement_ids']))}</p><h3>关联评分</h3><p>{esc(' / '.join(task['scoring_ids']))} · 共 25 分（原文最高分）</p>
<h3>需要的证明与配图</h3><ul>{''.join('<li>'+esc(v)+'</li>' for v in task['evidence_needed']+task['visuals_needed'])}</ul>
<p class="muted">目录覆盖不等于正文充分响应，也不等于已经得分。</p><a href="artifacts/08-outline.json">查看实际目录 JSON</a></section></div>''')
    chapter = writing["chapters"][0]
    body = "\n\n".join(p for p in chapter["body_markdown"].split("\n\n") if not p.startswith("!["))
    chapter_html = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", body_html(body, chapter['title']))
    page("writing", "按任务卡编写可追溯的章节", "候选正文 · 4.1 事件闭环管理 · 关联 R2 / R3 / R4", f'''
<div class="notice">正文尚未采纳。设计机制与承诺需要真实能力证据；不能把生成内容或示意图当成已实现系统的证明。</div>
<section class="panel chapter"><div class="links"><a href="artifacts/11-chapter-4.1.md">下载实际 Markdown 草稿</a><a href="artifacts/11-technical-content.json">正文与逐项响应 JSON</a><a href="visuals.html">查看本章配图 →</a></div>{chapter_html}</section>''')
    page("visuals", "技术图与系统界面图分别生成", "技术图使用可编辑 JSON + SVG；界面设计示意使用宿主实际生图工具", '''
<div class="two"><section class="panel"><h2>六状态流转 · 含复核退回</h2><img class="figure" src="assets/fig-4.1-event-flow.svg" alt="事件登记、派发、接单、处置、复核、归档流程图，复核不通过退回处置">
<p class="muted">enterprise-diagrams · SVG 矢量图 · 与 R2 状态和退回路径逐项对应。</p><div class="links"><a href="assets/fig-4.1-event-flow.svg">SVG</a><a href="assets/fig-4.1-event-flow.diagram.json">可编辑 JSON 图源</a></div></section>
<section class="panel"><h2>事件复核 · 界面设计示意</h2><img class="figure" src="assets/fig-4.1-ui.r3.png" alt="宿主原生生图生成的事件复核界面设计示意，非实际系统截图">
<p class="muted">WorkBuddy 原生 ImageGen 实际生成的 r3 图片。已检查复核通过/退回处置、退回原因与日志提示。</p><a href="assets/fig-4.1-ui.r3.png">查看原图</a></section></div>
<div class="notice">两张图均为响应设计示意，不证明系统已实现。Draw.io、Mermaid 等现有引擎仍可配置；SVG 主题可选 reference、blue、teal、green、slate、monochrome。</div>''')
    page("export", "可编辑 Word 与实际渲染的 PDF", "六页单章样稿 · 九条目录链接 · 两张嵌入图片 · 非整本投标文件", '''
<section class="panel"><h2>下载并检查实际文件</h2><div class="links"><a href="deliverables/chapter-4.1-sample.docx">下载 Word 样稿</a><a href="deliverables/chapter-4.1-sample.pdf">打开 PDF 样稿</a><a href="deliverables/SHA256SUMS">文件校验值</a></div>
<p>样稿包括封面、已刷新的目录、章节正文、流程图和界面示意图。Mac Word 已保存重开并检查目录跳转；PDF 经 LibreOffice 转换后逐页检查。</p>
<p class="muted">分享版 Word 仅移除了修改者元数据，文档 XML 与媒体不变；PDF 与已检查版本一致。格式检查通过不代表资格、材料或评分已通过。</p></section>
<div class="two"><section class="panel"><h2>目录页 · PDF 第 2 页</h2><img class="paper" src="assets/pdf-page-2.png" alt="实际PDF目录页，九条目录及页码"></section><section class="panel"><h2>配图页 · PDF 第 6 页</h2><img class="paper" src="assets/pdf-page-6.png" alt="实际PDF第六页，界面设计示意及图注"></section></div>''')
    print("Built five documentation views from the synthetic output snapshot.")


if __name__ == "__main__":
    main()
