#!/usr/bin/env python3
"""Render a portable, read-only HTML review of a delivery project snapshot."""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
from pathlib import Path
from typing import Any, Iterable


SCRIPT_DIR = Path(__file__).resolve().parent
ORCHESTRATOR_DIR = SCRIPT_DIR.parent
sys.path.insert(0, str(SCRIPT_DIR))
try:  # Package import when called as a module.
    from . import runtime  # type: ignore
except ImportError:  # Direct script invocation from any working directory.
    try:
        import runtime  # type: ignore
    except ImportError:  # Tests can inject a sibling-compatible module.
        runtime = None  # type: ignore


# Keep the renderer's customer boundary identical to runtime.prepare_customer.
# Review, confirmation, source and finance objects remain internal controls.
PUBLIC_KINDS = frozenset({"kickoff", "discovery", "minutes", "requirements", "blueprint", "plan", "weekly", "milestone"})
STAGES = {
    "costs": "贯穿全程 · 成本", "timesheets": "贯穿全程 · 工时", "source": "原始材料",
    "contract": "S0 交接",
    "kickoff": "S1 启动",
    "discovery": "S2 调研",
    "minutes": "S2 会议纪要",
    "requirements": "S2 需求",
    "blueprint": "S3 蓝图",
    "plan": "S4 计划",
    "risks": "贯穿全程 · 风险质量",
    "change": "贯穿全程 · 变更",
    "weekly": "贯穿全程 · 周报",
    "milestone": "S8 里程碑",
    "confirmation": "S8 确认",
    "review": "交付审阅",
    "evidence": "证据",
}
PRIVATE_KEYS = frozenset(
    {
        "alert",
        "alerts",
        "amount",
        "budget",
        "cost",
        "costs",
        "cost_summary",
        "currency",
        "expense",
        "expenses",
        "internal_labor",
        "provisional_labor",
        "other_incurred",
        "committed_remaining",
        "estimated_remaining",
        "forecast",
        "variance",
        "complete",
        "internal",
        "payment_status",
        "rate",
        "remaining_labor",
        "other_remaining",
        "timesheet",
        "timesheets",
    }
)
PRIVATE_KEYS |= runtime.CUSTOMER_FORBIDDEN_KEYS if runtime is not None else frozenset()

LABELS = {
    "internal": "内部", "customer": "客户", "simulation": "模拟", "ready": "已就绪", "draft": "草稿", "blocked": "受阻",
    "contract": "合同交接", "kickoff": "项目启动", "discovery": "调研计划", "minutes": "会议纪要", "requirements": "需求基线",
    "blueprint": "实施蓝图", "plan": "项目总计划", "weekly": "项目周报", "milestone": "里程碑", "costs": "成本费用",
    "timesheets": "人员工时", "risks": "风险与问题", "change": "变更", "confirmation": "确认记录", "review": "独立审阅", "evidence": "证据",
    "items": "事项", "id": "编号", "title": "名称", "statement": "需求描述", "source_refs": "来源依据", "evidence_refs": "证据引用",
    "target": "目标版本", "targets": "目标版本", "scope": "范围", "owner": "负责人", "status": "状态", "date": "日期", "due": "截止日期",
    "processes": "业务流程", "pages": "页面设计", "fields": "字段设计", "interfaces": "系统接口", "permissions": "权限", "data": "数据",
    "coverage": "需求覆盖", "acceptance_scenarios": "验收场景", "acceptance_criteria": "验收标准", "open_items": "待解决事项",
    "budget": "批准预算", "forecast": "完工预测", "variance": "预测差异", "currency": "币种", "internal_labor": "内部人工",
    "provisional_labor": "暂估人工", "other_incurred": "其他已发生", "committed_remaining": "已承诺剩余", "estimated_remaining": "估计剩余",
    "complete": "数据完整", "gaps": "数据缺口", "reasons": "依据与缺口", "action": "行动", "description": "说明", "requirement_id": "需求编号",
    "design_ids": "设计编号", "name": "名称", "type": "类型", "result": "结果", "summary": "摘要", "decisions": "决定", "actions": "行动项",
}

LABELS.update({'obligations': '合同义务', 'scope_in': '范围内', 'scope_out': '范围外', 'customer_dependencies': '客户配合前提', 'source_id': '来源编号', 'locator': '原文定位', 'acceptance': '验收标准', 'goals': '目标', 'roles': '参与角色', 'role': '角色', 'responsibility': '职责', 'milestones': '里程碑', 'customer_actions': '客户配合事项', 'sessions': '调研安排', 'customer_role': '客户关键人', 'topic': '调研主题', 'questions': '调研问题', 'customer_inputs': '客户提供资料', 'expected_outputs': '预期输出', 'meeting_date': '会议日期', 'participants': '参会人', 'priority': '优先级', 'steps': '步骤', 'requirement_ids': '需求编号', 'outputs': '输出', 'page_id': '页面编号', 'length': '长度', 'required': '必填', 'default': '默认值', 'validation': '校验规则', 'permission': '权限规则', 'source': '原始材料', 'read_only': '只读', 'output': '输出字段', 'allowed_roles': '允许角色', 'denied_roles': '禁止角色', 'condition': '条件', 'errors': '异常处理', 'source_system': '来源系统', 'target_system': '目标系统', 'field_mappings': '字段映射', 'error_contract': '异常约定', 'test_case': '测试用例', 'expected': '预期结果', 'permission_ids': '权限编号', 'work_packages': '工作包', 'baseline_start': '基线开始', 'baseline_finish': '基线完成', 'forecast_finish': '预测完成', 'dependencies': '前置依赖', 'completion_rule': '完成标准', 'period': '报告周期', 'as_of': '截止日期', 'completed': '已完成', 'completion_evidence': '完成依据', 'next': '下一步', 'decisions_required': '待决策事项', 'coverage_gaps': '覆盖缺口', 'artifact_id': '产物编号', 'revision': '版本', 'sha256': '文件指纹', 'state': '业务状态', 'actor': '确认人', 'origin': '依据类型', 'evidence_status': '证据状态', 'amount_basis': '金额口径', 'evidence_note': '证据说明', 'budget_evidence_refs': '预算依据', 'other_remaining': '其他剩余估计', 'other_remaining_evidence_refs': '剩余估计依据', 'category': '类别', 'work_package_id': '工作包编号', 'amount': '金额', 'basis': '估计依据', 'payment_status': '付款状态', 'person': '人员', 'hours': '工时', 'rate': '内部费率', 'resource_type': '资源类型', 'remaining_labor': '剩余人工估计', 'remaining_labor_basis': '剩余人工口径', 'remaining_labor_evidence_refs': '剩余人工依据', 'criteria': '验收条目', 'deliverable_refs': '交付物引用', 'milestone_id': '里程碑编号', 'coverage_summary': '覆盖说明', 'method': '审核方法', 'verdict': '结论', 'reviewer': '审核人', 'findings': '审核发现', 'unchecked': '未核验范围', 'impact': '影响分析', 'reason': '原因', 'affected_ids': '影响对象', 'baseline_refs': '原有效版本', 'replacements': '候选替代版本', 'decision_refs': '决策依据', 'path': '登记路径', 'complete': '计算与已声明证据完整'})


def _esc(value: Any) -> str:
    return html.escape(str(value), quote=True)


def _label(value: Any) -> str:
    if str(value) in LABELS:
        return LABELS[str(value)]
    text = str(value).replace("_", " ").strip()
    return text[:1].upper() + text[1:] if text else "Value"


def _safe_public(value: Any) -> Any:
    """Copy business data while removing cost/private fields for customer HTML."""
    if isinstance(value, dict):
        return {
            str(key): _safe_public(item)
            for key, item in value.items()
            if str(key).lower() not in PRIVATE_KEYS
        }
    if isinstance(value, list):
        return [_safe_public(item) for item in value]
    return value


def _artifacts(snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    raw = snapshot.get("artifacts", [])
    if isinstance(raw, dict):
        result = []
        for artifact_id, item in raw.items():
            if isinstance(item, dict):
                result.append({"artifact_id": artifact_id, **item})
        return result
    return [item for item in raw if isinstance(item, dict)] if isinstance(raw, list) else []


def _effective_ids(snapshot: dict[str, Any]) -> set[str]:
    effective = snapshot.get("effective", {})
    if not isinstance(effective, dict):
        return set()
    ids: set[str] = set()
    for key, value in effective.items():
        ids.add(str(key))
        if isinstance(value, dict):
            if value.get("artifact_id"):
                ids.add(str(value["artifact_id"]))
        elif isinstance(value, str):
            ids.add(value.split("@", 1)[0])
    return ids


def _reference_details(artifact: dict[str, Any]) -> Any:
    for key in ("inputs", "evidence_refs", "source_refs"):
        value = artifact.get(key)
        if value:
            return value
    data = artifact.get("data")
    if isinstance(data, dict):
        for key in ("evidence_refs", "source_refs"):
            value = data.get(key)
            if value:
                return value
    return None


def _load_snapshot(project: Path) -> dict[str, Any]:
    if runtime is None or not hasattr(runtime, "snapshot"):
        raise RuntimeError("delivery-orchestrator runtime.py with snapshot(project) is unavailable")
    value = runtime.snapshot(project)
    if isinstance(value, tuple):
        value = value[0]
    if not isinstance(value, dict):
        raise RuntimeError("runtime.snapshot(project) must return an object")
    return value


def _plain(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    return str(value)


def _render_table(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return ""
    keys: list[str] = []
    for row in rows:
        for key in row:
            if str(key) not in keys:
                keys.append(str(key))
    header = "".join(f"<th scope=\"col\">{_esc(_label(key))}</th>" for key in keys)
    body = []
    for row in rows:
        body.append(
            "<tr>"
            + "".join(f"<td>{_render_inline(row.get(key, ''))}</td>" for key in keys)
            + "</tr>"
        )
    return f'<div class="table-scroll"><table><thead><tr>{header}</tr></thead><tbody>{"".join(body)}</tbody></table></div>'


def _render_inline(value: Any) -> str:
    if value is None:
        return '<span class="muted">未填写</span>'
    if isinstance(value, (dict, list)):
        if isinstance(value, list) and all(not isinstance(item, (dict, list)) for item in value):
            return "、".join(_esc(item) for item in value) or '<span class="muted">无记录</span>'
        return f'<details><summary>查看明细</summary>{_render_value(value)}</details>'
    text = _esc(value)
    return text.replace("\n", "<br>")


def _render_value(value: Any, depth: int = 0) -> str:
    if value is None:
        return '<span class="muted">未填写</span>'
    if isinstance(value, dict):
        parts = []
        for key, item in value.items():
            parts.append(
                f'<div class="field"><dt>{_esc(_label(key))}</dt><dd>{_render_value(item, depth + 1)}</dd></div>'
            )
        return f'<dl class="fields depth-{min(depth, 3)}">{"".join(parts)}</dl>'
    if isinstance(value, list):
        if value and all(isinstance(item, dict) for item in value):
            return _render_table(value)
        items = "".join(f"<li>{_render_value(item, depth + 1)}</li>" for item in value)
        return f"<ul>{items}</ul>" if items else '<span class="muted">无记录</span>'
    text = _esc(value)
    if "\n" in str(value):
        return f'<p class="long-text">{text.replace(chr(10), "<br>")}</p>'
    return text


def _template_summaries(view: str) -> list[dict[str, str]]:
    index = ORCHESTRATOR_DIR / "assets" / "templates" / "index.json"
    if not index.is_file():
        return []
    try:
        raw = json.loads(index.read_text(encoding="utf-8"))
        entries = raw if isinstance(raw, list) else raw.get("templates", raw.get("entries", []))
        result = []
        for item in entries:
            if not isinstance(item, dict):
                continue
            visibility = item.get("visibility", "internal")
            if view == "customer" and visibility != "customer":
                continue
            result.append(
                {
                    "id": str(item.get("id", "")),
                    "title": str(item.get("title", item.get("id", ""))),
                    "visibility": visibility,
                    "format": str(item.get("format", item.get("fmt", ""))),
                    "path": str(item.get("path", "")),
                }
            )
        return result
    except (OSError, json.JSONDecodeError, AttributeError, TypeError):
        return []


def _artifact_html(artifact: dict[str, Any], view: str, effective_ids: set[str]) -> str:
    artifact_id = str(artifact.get("artifact_id", artifact.get("id", "unknown")))
    kind = str(artifact.get("kind", "artifact"))
    stage = STAGES.get(kind, "项目产物")
    classes = "record artifact-record"
    # snapshot resolves exact revision/hash; ID membership alone proves no baseline.
    is_effective = artifact.get("is_effective") is True
    if is_effective:
        classes += " is-effective"
    visibility = str(artifact.get("visibility", ""))
    metadata = [
        ("产物编号", artifact_id),
        ("类型", _label(kind)),
        ("当前候选版本", artifact.get("revision", "未标注")),
        ("状态", _label(artifact.get("status", "未标注"))),
    ]
    if is_effective:
        metadata.append(("基线状态", "当前有效引用"))
    if artifact.get("effective_revision") is not None:
        metadata.append(("已生效版本", artifact.get("effective_revision")))
    if view == "internal":
        metadata.extend(
            [
                ("可见范围", _label(visibility) or "未标注"),
                ("引用健康", artifact.get("health", "未标注")),
                ("Path", artifact.get("path", "未标注")),
                ("SHA-256", artifact.get("sha256", "未标注")),
            ]
        )
    details = _reference_details(artifact)
    evidence = ""
    if details:
        evidence = f'<details class="evidence"><summary>查看来源与版本依据</summary>{_render_value(details)}</details>'
    data = artifact.get("data", {})
    if view == "customer":
        data = _safe_public(data)
    return (
        f'<article id="artifact-{_esc(artifact_id)}" class="{classes}" data-search="{_esc(_plain(artifact))}">'
        f'<div class="record-heading"><div><p class="eyebrow">{_esc(stage)}</p><h2>{_esc(artifact_id)}</h2>'
        f'<p class="kind">{_esc(_label(kind))}</p></div><span class="status status-{_esc(str(artifact.get("status", "unknown")))}">{_esc(_label(artifact.get("status", "未标注")))}</span></div>'
        f'<details class="version-details"><summary>版本与登记信息</summary><dl class="metadata">{"".join(f"<div><dt>{_esc(key)}</dt><dd>{_render_inline(value)}</dd></div>" for key, value in metadata)}</dl></details>'
        f'{evidence}<section class="business-content"><h3>业务内容</h3>{_render_value(data)}</section></article>'
    )


def _section(title: str, content: str, anchor: str, classes: str = "") -> str:
    return f'<section id="{_esc(anchor)}" class="section {classes}"><div class="section-heading"><h2>{_esc(title)}</h2></div>{content}</section>'


def _render_css() -> str:
    return """
:root { --canvas:#F5F7FA; --surface:#FFFFFF; --surface-muted:#EEF1F5; --text:#0B1220; --secondary:#526075; --tertiary:#68758A; --border:#D9DEE7; --border-subtle:#E7EAF0; --brand:#1677FF; --action:#0966D9; --action-hover:#0754B5; --selected:#EDF4FF; --success:#18794E; --warning:#A9650A; --danger:#C32F3F; --font:Inter,-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif; --mono:"JetBrains Mono","SFMono-Regular",Consolas,monospace; }
* { box-sizing:border-box; }
html { scroll-behavior:smooth; }
body { margin:0; background:var(--canvas); color:var(--text); font:14px/1.57 var(--font); }
a { color:var(--action); text-decoration:underline; text-underline-offset:2px; }
a:focus-visible, input:focus-visible { outline:2px solid var(--action); outline-offset:2px; }
.app-shell { min-height:100vh; display:grid; grid-template-columns:220px minmax(0,1fr); }
.sidebar { position:sticky; top:0; align-self:start; height:100vh; overflow:auto; padding:20px 16px; background:var(--surface); border-right:1px solid var(--border); }
.brand { margin:0 0 20px; font-size:16px; font-weight:600; }
.nav-heading { margin:18px 8px 6px; color:var(--tertiary); font-size:12px; text-transform:uppercase; letter-spacing:.04em; }
.nav-list { display:grid; gap:2px; margin:0; padding:0; list-style:none; }
.nav-list a { display:block; min-height:32px; padding:6px 8px; border-left:2px solid transparent; color:var(--secondary); text-decoration:none; border-radius:3px; }
.nav-list a:hover, .nav-list a:focus-visible { color:var(--action); background:var(--selected); border-left-color:var(--brand); }
.main { min-width:0; padding:24px 32px 48px; }
.header { display:flex; flex-wrap:wrap; justify-content:space-between; gap:16px; padding-bottom:20px; border-bottom:1px solid var(--border); }
.header h1 { margin:0; font-size:24px; line-height:1.25; font-weight:600; }
.eyebrow { margin:0 0 4px; color:var(--tertiary); font-size:12px; letter-spacing:.03em; text-transform:uppercase; }
.purpose { margin:8px 0 0; color:var(--secondary); }
.simulation { display:inline-flex; align-items:center; min-height:34px; padding:6px 10px; border:1px solid var(--warning); border-radius:4px; color:var(--warning); font-weight:600; }
.search-row { display:flex; flex-wrap:wrap; align-items:center; gap:12px; padding:16px 0; }
.search-row label { font-weight:600; }
.search-row input { width:min(520px,100%); min-height:34px; padding:6px 10px; border:1px solid var(--border-control,var(--tertiary)); border-radius:4px; background:var(--surface); color:var(--text); font:inherit; }
.count { color:var(--secondary); }
.section { margin-top:32px; }
.section-heading { margin-bottom:12px; }
.section-heading h2 { margin:0; font-size:20px; line-height:1.3; }
.section-heading .eyebrow { margin-bottom:2px; }
.record { margin:0 0 16px; padding:16px 20px; background:var(--surface); border:1px solid var(--border); border-radius:6px; }
.record.is-effective { border-left:3px solid var(--brand); }
.record-heading { display:flex; justify-content:space-between; gap:16px; align-items:start; }
.record h2 { margin:0; font-size:16px; line-height:1.35; }
.record h3 { margin:20px 0 8px; font-size:14px; }
.kind { margin:2px 0 0; color:var(--secondary); font-family:var(--mono); font-size:12px; }
.status { flex:none; display:inline-flex; min-height:28px; align-items:center; padding:4px 8px; border:1px solid var(--border); border-radius:3px; font-size:12px; }
.status-ready { border-color:var(--success); color:var(--success); }
.status-blocked { border-color:var(--danger); color:var(--danger); }
.metadata { display:grid; grid-template-columns:repeat(auto-fit,minmax(160px,1fr)); gap:8px 16px; margin:16px 0 0; padding-top:12px; border-top:1px solid var(--border-subtle); }
.metadata div, .field { min-width:0; }
.metadata dt, .field dt { color:var(--tertiary); font-size:12px; }
.metadata dd, .field dd { margin:0; overflow-wrap:anywhere; }
.fields { display:grid; gap:10px; margin:0; }
.fields .field { padding-bottom:8px; border-bottom:1px solid var(--border-subtle); }
.fields .field:last-child { border-bottom:0; }
.fields.depth-1 { margin-top:4px; padding-left:12px; border-left:2px solid var(--border-subtle); }
.fields.depth-2 { margin-top:4px; padding-left:12px; }
.long-text { white-space:normal; margin:0; overflow-wrap:anywhere; }
.muted { color:var(--tertiary); }
.table-scroll { max-width:100%; overflow-x:auto; border:1px solid var(--border); }
table { width:100%; border-collapse:collapse; min-width:560px; }
th, td { padding:9px 10px; text-align:left; vertical-align:top; border-bottom:1px solid var(--border-subtle); overflow-wrap:anywhere; }
th { background:var(--surface-muted); color:var(--text); font-size:12px; font-weight:600; }
tr:last-child td { border-bottom:0; }
.evidence { padding-top:12px; border-top:1px solid var(--border-subtle); }
.evidence + .business-content { margin-top:8px; }
.summary-grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(160px,1fr)); gap:12px; }
.summary-item { padding:12px 16px; border:1px solid var(--border); background:var(--surface); border-radius:6px; }
.summary-item dt { color:var(--tertiary); font-size:12px; }
.summary-item dd { margin:2px 0 0; font-size:18px; font-weight:600; }
.notice-list { margin:0; padding-left:20px; }
.notice-list li + li { margin-top:4px; }
.hidden-by-search { display:none !important; }
details { margin-top:8px; max-width:100%; } summary { color:var(--action); cursor:pointer; } td { min-width:110px; max-width:380px; } td details { min-width:160px; }
@media (max-width: 768px) { .app-shell { display:block; } .sidebar { position:relative; height:auto; max-height:none; border-right:0; border-bottom:1px solid var(--border); } .nav-list { display:flex; flex-wrap:wrap; gap:4px; } .nav-list a { min-height:30px; } .main { padding:16px; } .record-heading { flex-direction:column; gap:8px; } .metadata { grid-template-columns:1fr 1fr; } }
@media (prefers-color-scheme: dark) { :root { --canvas:#101722; --surface:#182230; --surface-muted:#1D2939; --text:#EDF2F9; --secondary:#B8C5D8; --tertiary:#9AAAC0; --border:#35445A; --border-subtle:#2A384B; --brand:#1677FF; --action:#80B5FF; --action-hover:#A8CDFF; --selected:#1B304D; --success:#74D6A3; --warning:#F5C06B; --danger:#FF939B; } }
@media (prefers-reduced-motion: reduce) { html { scroll-behavior:auto; } }
"""


def render_review(project: str | Path, out: str | Path, view: str = "internal") -> dict[str, Any]:
    if view not in {"internal", "customer"}:
        raise ValueError("view must be internal or customer")
    project_path = Path(project).expanduser().resolve()
    snapshot = _load_snapshot(project_path)
    all_artifacts = _artifacts(snapshot)
    if view == "customer":
        artifacts = [
            {
                key: _safe_public(value)
                for key, value in artifact.items()
                if key not in {"path", "health"}
            }
            for artifact in all_artifacts
            if artifact.get("visibility") == "customer" and artifact.get("kind") in PUBLIC_KINDS
        ]
    else:
        artifacts = all_artifacts
    effective = _effective_ids(snapshot)
    template_items = _template_summaries(view)
    stage_kinds = sorted({str(item.get("kind", "artifact")) for item in artifacts}, key=lambda kind: (STAGES.get(kind, "项目产物"), kind))
    nav_parts = ['<p class="brand">项目交付审阅</p>', '<p class="nav-heading">交付阶段</p><ul class="nav-list">']
    for kind in stage_kinds:
        nav_parts.append(f'<li><a href="#stage-{_esc(kind)}">{_esc(STAGES.get(kind, kind))}</a></li>')
    nav_parts.append('</ul><p class="nav-heading">项目产物</p><ul class="nav-list">')
    for artifact in artifacts:
        artifact_id = str(artifact.get("artifact_id", artifact.get("id", "unknown")))
        nav_parts.append(f'<li><a href="#artifact-{_esc(artifact_id)}">{_esc(artifact_id)}</a></li>')
    nav_parts.append('</ul><p class="nav-heading">配套模板</p><ul class="nav-list">')
    for item in template_items:
        nav_parts.append(f'<li><a href="#template-{_esc(item["id"])}">{_esc(item["title"])}</a></li>')
    nav_parts.append("</ul>")

    stage_sections = []
    for kind in stage_kinds:
        group = [item for item in artifacts if str(item.get("kind", "artifact")) == kind]
        records = "".join(_artifact_html(item, view, effective) for item in group)
        stage_sections.append(_section(STAGES.get(kind, kind), records or '<p class="muted">暂无产物</p>', f"stage-{kind}"))
    templates = "".join(
        f'<article id="template-{_esc(item["id"])}" class="record template-record" data-search="{_esc(_plain(item))}">'
        f'<div class="record-heading"><div><p class="eyebrow">模板</p><h2>{_esc(item["title"])}</h2><p class="kind">{_esc(item["id"])}</p></div>'
        f'<span class="status">{_esc(item["format"])}</span></div>'
        f'<dl class="metadata"><div><dt>可见范围</dt><dd>{_esc(item["visibility"])}</dd></div>'
        + (f'<div><dt>模板路径</dt><dd>{_esc(item["path"])}</dd></div>' if view == "internal" else "")
        + "</dl></article>"
        for item in template_items
    )
    template_section = _section("配套模板", templates or '<p class="muted">暂无模板</p>', "templates")
    if view == "internal":
        cost = snapshot.get("cost_summary")
        alerts = snapshot.get("alerts", [])
        gates = snapshot.get("gates", {})
        cost_html = _render_value(cost) if cost is not None else '<p class="muted">暂无成本摘要</p>'
        alert_html = _render_value(alerts) if alerts else '<p class="muted">暂无告警</p>'
        gate_html = _render_value(gates) if gates else '<p class="muted">暂无门槛信息</p>'
        internal_section = _section(
            "内部管理",
            f'<div class="record"><h3>成本摘要</h3>{cost_html}<h3>提醒</h3>{alert_html}<h3>阶段检查</h3>{gate_html}</div>',
            "internal-controls",
        )
    else:
        internal_section = ""
    purpose = str(snapshot.get("purpose", "未标注"))
    simulation = purpose == "simulation"
    summary = (
        '<div class="summary-grid">'
        f'<dl class="summary-item"><dt>项目产物</dt><dd>{len(artifacts)}</dd></dl>'
        f'<dl class="summary-item"><dt>配套模板</dt><dd>{len(template_items)}</dd></dl>'
        f'<dl class="summary-item"><dt>查看范围</dt><dd>{_esc(_label(view))}</dd></dl>'
        "</div>"
    )
    simulation_banner = '<span class="simulation">SIMULATION · 模拟项目</span>' if simulation else ""
    html_text = f"""<!doctype html>
<html lang="zh-CN">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{_esc(snapshot.get('project_id', project_path.name))} delivery review</title><style>{_render_css()}</style></head>
<body><div class="app-shell"><aside class="sidebar" aria-label="审阅导航">{"".join(nav_parts)}</aside>
<main class="main"><header class="header"><div><p class="eyebrow">项目交付审阅</p><h1>{_esc(snapshot.get('project_id', project_path.name))}</h1><p class="purpose">用途： {_esc(_label(purpose))} · 范围： {_esc(_label(view))}</p></div><div>{simulation_banner}</div></header>
<div class="search-row"><label for="record-search">搜索项目记录</label><input id="record-search" type="search" placeholder="输入编号、业务内容、证据或模板名称" autocomplete="off"><span id="search-count" class="count" aria-live="polite">{len(artifacts) + len(template_items)} 条记录</span></div>
{_section('项目概览', summary, 'overview')}{''.join(stage_sections)}{template_section}{internal_section}
</main></div><script>(function(){{const input=document.getElementById('record-search');const count=document.getElementById('search-count');const records=[...document.querySelectorAll('[data-search]')];function filter(){{const query=input.value.trim().toLocaleLowerCase();let shown=0;records.forEach((record)=>{{const match=!query||record.dataset.search.toLocaleLowerCase().includes(query);record.classList.toggle('hidden-by-search',!match);if(match)shown+=1;}});document.querySelectorAll('main>.section').forEach((section)=>{{const items=[...section.querySelectorAll('[data-search]')];section.classList.toggle('hidden-by-search',items.length>0&&items.every((item)=>item.classList.contains('hidden-by-search')));}});count.textContent=shown+' 条记录';}}input.addEventListener('input',filter);document.querySelectorAll('.sidebar a').forEach((link)=>link.addEventListener('click',()=>{{input.value='';filter();}}));}})();</script></body></html>"""
    output = Path(out).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(html_text, encoding="utf-8")
    return {"out": str(output), "view": view, "project_id": snapshot.get("project_id"), "artifacts": len(artifacts), "templates": len(template_items)}


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project", help="delivery project directory")
    parser.add_argument("--out", required=True, help="HTML output path")
    parser.add_argument("--view", choices=("internal", "customer"), default="internal")
    args = parser.parse_args(argv)
    try:
        result = render_review(args.project, args.out, args.view)
    except (OSError, RuntimeError, ValueError, TypeError, KeyError) as exc:
        print(f"render_review: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
