#!/usr/bin/env python3
"""Render a source-bound, offline HTML report for a tender analysis project.

The workflow state is the only index accepted by this renderer.  Every file it
names is checked for containment, identity, revision, and SHA-256 before any
content is used.  This keeps a report from silently mixing a current project
with a stale artifact in ``work/history``.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
import re
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote


WORKFLOW_REL = "work/17-workflow-state.json"
REQUIRED_STAGES = (
    "bid-source-intake",
    "bid-project-profile",
    "bid-requirements",
    "bid-scoring",
    "bid-compliance",
    "bid-format-extraction",
)
STALE_STATES = {"stale", "not_started", "in_progress", "pending", "blocked", "failed"}

CATEGORY_LABELS = {
    "qualification": "资格条件",
    "delivery": "交付与范围",
    "functional": "功能需求",
    "integration": "集成与数据",
    "security": "安全与权限",
    "performance": "性能与环境",
    "implementation": "实施与服务",
    "service": "服务与运维",
    "quality": "质量与验收",
    "acceptance": "验收与交付",
    "commercial": "商务条件",
    "technical": "技术与架构",
    "performance_risk": "履约风险",
    "other": "其他",
}
COMPLIANCE_LABELS = {
    "qualification": "资格条件",
    "rejection": "明确否决",
    "submission": "提交要求",
    "performance": "履约风险",
    "performance_risk": "履约风险",
    "delivery": "交付要求",
}
BASIS_LABELS = {
    "explicit": ("原文明示", "blue"),
    "derived": ("推导", "amber"),
    "inferred": ("推导", "amber"),
    "proposal": ("建议", "muted"),
    "suggested": ("建议", "muted"),
    "advisory": ("建议", "muted"),
    "unknown": ("未知", "amber"),
}
LOT_LABELS = {"single": "单一标包", "multiple": "多个标包", "unknown": "标包待确认"}
TEMPLATE_LABELS = {
    "construction": "工程施工",
    "hardware_supply": "硬件供货",
    "software_integration": "软件开发与系统集成",
    "service_outsourcing": "服务与外包",
}


class ReportInputError(ValueError):
    """Raised when an analysis project cannot be safely rendered."""


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ReportInputError(f"无法读取JSON：{path.name}：{exc}") from exc
    if not isinstance(value, dict):
        raise ReportInputError(f"JSON顶层必须是对象：{path}")
    return value


def _inside(project: Path, relative_path: str, label: str, *, must_exist: bool = True) -> Path:
    if not isinstance(relative_path, str) or not relative_path.strip():
        raise ReportInputError(f"{label}缺少relative_path")
    candidate = Path(relative_path)
    if candidate.is_absolute() or ".." in candidate.parts:
        raise ReportInputError(f"{label}路径越界：{relative_path}")
    root = project.resolve()
    target = (project / candidate).resolve()
    try:
        target.relative_to(root)
    except ValueError as exc:
        raise ReportInputError(f"{label}路径越界：{relative_path}") from exc
    if must_exist and not target.is_file():
        raise ReportInputError(f"{label}文件不存在：{relative_path}")
    return target


def _artifact_index(workflow: dict, project: Path, cache: dict[str, str]) -> tuple[dict, dict[str, dict], dict[str, str], str]:
    for key in ("project_id", "artifact_id", "revision", "inputs", "data"):
        if key not in workflow:
            raise ReportInputError(f"17-workflow-state缺少{key}")
    project_id = workflow["project_id"]
    if not isinstance(project_id, str) or not project_id:
        raise ReportInputError("17-workflow-state项目ID无效")
    inputs = workflow["inputs"]
    if not isinstance(inputs, list) or not inputs:
        raise ReportInputError("17-workflow-state.inputs为空，不能生成同源报告")
    indexed: dict[str, dict] = {}
    seen_paths: set[str] = set()
    for entry in inputs:
        if not isinstance(entry, dict):
            raise ReportInputError("17-workflow-state.inputs包含非对象")
        rel = entry.get("relative_path")
        if rel in seen_paths:
            raise ReportInputError(f"17-workflow-state.inputs重复路径：{rel}")
        seen_paths.add(rel)
        path = _inside(project, rel, "workflow input")
        actual = cache.setdefault(rel, sha256(path))
        if actual != entry.get("sha256"):
            raise ReportInputError(f"输入哈希不匹配：{rel}")
        if not isinstance(entry.get("artifact_id"), str) or not isinstance(entry.get("revision"), int):
            raise ReportInputError(f"输入身份不完整：{rel}")
        indexed[rel] = {**entry, "actual_sha256": actual}

    stages = workflow.get("data", {}).get("stages")
    if not isinstance(stages, list):
        raise ReportInputError("17-workflow-state.data.stages缺失，拒绝任意选择旧版本")
    stage_paths: dict[str, str] = {}
    for stage in stages:
        if not isinstance(stage, dict) or not isinstance(stage.get("skill_id"), str):
            continue
        skill_id = stage["skill_id"]
        if skill_id not in REQUIRED_STAGES:
            continue
        if skill_id not in REQUIRED_STAGES:
            continue
        if skill_id in stage_paths:
            raise ReportInputError(f"workflow stages重复skill：{skill_id}")
        if stage.get("state") in STALE_STATES or not isinstance(stage.get("artifact_path"), str):
            raise ReportInputError(f"当前stage未完成或已失效：{skill_id}")
        stage_paths[skill_id] = stage["artifact_path"]
    selected: dict[str, str] = {}
    for skill_id in REQUIRED_STAGES:
        stage_path = stage_paths.get(skill_id)
        if stage_path not in indexed:
            raise ReportInputError(f"workflow stage未登记当前产物：{skill_id} -> {stage_path}")
        selected[skill_id] = stage_path
    route_candidates = []
    for rel, entry in indexed.items():
        if not rel.lower().endswith(".json"):
            continue
        candidate = _json(_inside(project, rel, "workflow route candidate"))
        payloads = [candidate]
        if isinstance(candidate.get("data"), dict):
            payloads.append(candidate["data"])
        is_route = candidate.get("skill_id") == "bid-project-profile" and any(
            "classification" in payload and "intake_sha256" in payload for payload in payloads
        )
        if is_route:
            route_candidates.append(rel)
    if len(route_candidates) != 1:
        raise ReportInputError("workflow inputs中路由产物必须唯一")
    return workflow, indexed, selected, route_candidates[0]


def _check_artifact_identity(data: dict, entry: dict, workflow: dict, rel: str) -> None:
    if data.get("project_id") != workflow["project_id"]:
        raise ReportInputError(f"产物项目ID不一致：{rel}")
    if data.get("artifact_id") != entry["artifact_id"]:
        raise ReportInputError(f"产物ID不一致：{rel}")
    if data.get("revision") != entry["revision"]:
        raise ReportInputError(f"产物revision不一致：{rel}")


def _check_nested_inputs(data: dict, project: Path, cache: dict[str, str]) -> None:
    for item in data.get("inputs", []):
        if not isinstance(item, dict):
            raise ReportInputError("产物inputs包含非对象")
        rel = item.get("relative_path")
        path = _inside(project, rel, "产物input")
        actual = cache.setdefault(rel, sha256(path))
        if actual != item.get("sha256"):
            raise ReportInputError(f"产物input哈希不匹配：{rel}")
        if path.suffix.lower() == ".json":
            referenced = _json(path)
            if "artifact_id" in referenced and referenced.get("artifact_id") != item.get("artifact_id"):
                raise ReportInputError(f"产物input身份不一致：{rel}")
            if "revision" in referenced and referenced.get("revision") != item.get("revision"):
                raise ReportInputError(f"产物inputrevision不一致：{rel}")
            if "project_id" in referenced and data.get("project_id") != referenced.get("project_id"):
                raise ReportInputError(f"产物input项目ID不一致：{rel}")


def _load_project(project: Path) -> dict:
    project = project.expanduser().resolve()
    if not project.is_dir():
        raise ReportInputError(f"项目目录不存在：{project}")
    cache: dict[str, str] = {}
    workflow_path = _inside(project, WORKFLOW_REL, "workflow state")
    workflow_hash = sha256(workflow_path)
    workflow = _json(workflow_path)
    workflow, index, selected, route_rel = _artifact_index(workflow, project, cache)
    artifacts: dict[str, dict] = {}
    selected_paths = {**selected, "routing": route_rel}
    for skill_id, rel in selected_paths.items():
        entry = index[rel]
        data = _json(_inside(project, rel, "artifact"))
        _check_artifact_identity(data, entry, workflow, rel)
        if data.get("status") in STALE_STATES:
            raise ReportInputError(f"产物状态已失效或未完成：{rel}")
        _check_nested_inputs(data, project, cache)
        artifacts[skill_id] = data

    intake = artifacts["bid-source-intake"]
    documents = intake.get("data", {}).get("documents", [])
    source_docs: dict[str, dict] = {}
    for document in documents:
        source_id = document.get("source_id")
        if not isinstance(source_id, str) or source_id in source_docs:
            raise ReportInputError(f"原件source_id重复或无效：{source_id}")
        rel = document.get("relative_path")
        source_path = _inside(project, rel, f"原件{source_id}")
        actual = cache.setdefault(rel, sha256(source_path))
        if actual != document.get("sha256"):
            raise ReportInputError(f"原件哈希不匹配：{rel}")
        if document.get("bytes") is not None and document["bytes"] != source_path.stat().st_size:
            raise ReportInputError(f"原件字节数不匹配：{rel}")
        source_docs[source_id] = {**document, "actual_sha256": actual}
    if not source_docs:
        raise ReportInputError("01-source-intake没有原件身份")

    route = artifacts["routing"]
    if route.get("intake_sha256") != cache[selected["bid-source-intake"]]:
        raise ReportInputError("路由未绑定当前01原件产物")
    inventory = route.get("source_inventory")
    if not isinstance(inventory, list) or not inventory:
        raise ReportInputError("路由缺少原件身份清单")
    inventory_ids = {item.get("source_id") for item in inventory if isinstance(item, dict)}
    if inventory_ids != set(source_docs):
        raise ReportInputError("路由原件清单与01原件清单不一致")
    for item in inventory:
        source_id = item.get("source_id")
        doc = source_docs.get(source_id)
        if doc is None or item.get("sha256") != doc["actual_sha256"] or item.get("relative_path") != doc.get("relative_path"):
            raise ReportInputError(f"路由原件身份不一致：{source_id}")
        if item.get("revision") != doc.get("revision"):
            raise ReportInputError(f"路由原件revision不一致：{source_id}")
    if route.get("classification", {}).get("project_id") not in (None, workflow["project_id"]):
        raise ReportInputError("路由分类项目ID不一致")

    return {
        "project": project,
        "workflow": workflow,
        "workflow_hash": workflow_hash,
        "index": index,
        "artifacts": artifacts,
        "selected_paths": selected_paths,
        "source_docs": source_docs,
        "cache": cache,
    }


def _text(value: object, fallback: str = "待补") -> str:
    if value is None or value == "":
        return fallback
    if isinstance(value, bool):
        return "是" if value else "否"
    if isinstance(value, (list, tuple)):
        return "、".join(_text(item, fallback) for item in value) if value else fallback
    if isinstance(value, dict):
        return "；".join(f"{_text(k)}：{_text(v)}" for k, v in value.items()) if value else fallback
    return str(value)


def _esc(value: object, fallback: str = "待补") -> str:
    return html.escape(_text(value, fallback), quote=True)


def _analysis_copy(value: object) -> str:
    """Make generated notes readable; never apply this to literal source quotes."""
    text = re.sub(r"^(?:needs_review|draft|blocked)[:：]\s*", "", _text(value))
    for field, label in (("template_path", "模板文件路径"), ("reference", "参考格式")):
        text = re.sub(rf"(?<![A-Za-z0-9_]){field}(?![A-Za-z0-9_])", label, text)
    return text


def _status_label(status: object) -> str:
    return {"needs_review": "待业务复核", "ready": "已生成，待业务复核", "approved": "待业务复核", "passed": "待业务复核", "not_started": "未执行", "blocked": "受阻", "pending": "待处理"}.get(str(status), _text(status))


def _badge(label: object, tone: str = "muted") -> str:
    return f'<span class="badge {html.escape(tone)}">{_esc(label)}</span>'


def _basis(value: object) -> tuple[str, str]:
    return BASIS_LABELS.get(str(value), ("未知", "amber"))


def _link(output: Path, project: Path, rel: str, label: object) -> str:
    target = _inside(project, rel, "source link")
    relative = os.path.relpath(target, output.parent).replace(os.sep, "/")
    href = quote(relative, safe="/:@-._~")
    return f'<a href="{html.escape(href, quote=True)}">{_esc(label)}</a>'


def _sources(item: dict, source_docs: dict[str, dict], project: Path, output: Path) -> str:
    refs = item.get("sources") or item.get("evidence") or []
    if not refs:
        return '<span class="pending">原文位置待补</span>'
    result = []
    for ref in refs:
        if not isinstance(ref, dict):
            continue
        source = source_docs.get(ref.get("source_id"))
        location = _esc(ref.get("location"), "位置待补")
        if source:
            target = _inside(project, source["relative_path"], "source link")
            relative = os.path.relpath(target, output.parent).replace(os.sep, "/")
            href = quote(relative, safe="/:@-._~")
            page = re.search(r"(?:^|[^a-z])p(?:age)?[ -]?(\d+)", str(ref.get("location", "")), re.I)
            if target.suffix.lower() == ".pdf" and page:
                href += f"#page={page.group(1)}"
            source_label = f'<a href="{html.escape(href, quote=True)}">{_esc(source.get("filename", ref.get("source_id")))}</a>'
        else:
            source_label = _esc(ref.get("source_id"), "原件待补")
        quote_text = _esc(ref.get("quote"), "未附原文摘录")
        result.append(f'<span class="source-ref">{source_label} · {location}<span class="quote">{quote_text}</span></span>')
    return "".join(result) or '<span class="pending">原文位置待补</span>'


def _facts(profile: dict, routing: dict) -> tuple[str, str, str]:
    data = profile.get("data", {})
    facts = data.get("key_facts") or []
    cards = []
    identifiers = []
    if data.get("buyer"):
        cards.append(f'<div class="fact fact-buyer"><dt>招标人</dt><dd>{_esc(data.get("buyer"))}</dd></div>')
    for item in facts:
        if not isinstance(item, dict):
            continue
        if "编号" in str(item.get("key", "")):
            identifiers.append(f'<div><dt>{_esc(item.get("key"))}</dt><dd>{_esc(item.get("value"))}</dd></div>')
            continue
        cards.append(f'<div class="fact"><dt>{_esc(item.get("key"))}</dt><dd>{_esc(item.get("value"))}</dd></div>')
    if not cards:
        cards.append('<div class="empty">基础事实待补</div>')
    deadline_rows = []
    for item in data.get("deadlines") or []:
        if isinstance(item, dict):
            deadline_rows.append(f'<div><strong>{_esc(item.get("event"))}</strong><span>{_esc(item.get("raw_value"))}</span></div>')
    lot = routing.get("classification", {}).get("lot_structure") or routing.get("lots")
    return "".join(cards), "".join(deadline_rows) or f'<div><strong>标包结构</strong><span>{_esc(LOT_LABELS.get(lot, "标包待确认"))}</span></div>', "".join(identifiers)


def _render_requirements(requirements: list, source_docs: dict, project: Path, output: Path) -> tuple[str, dict]:
    groups: dict[str, list] = {}
    for req in requirements:
        if isinstance(req, dict):
            groups.setdefault(str(req.get("category") or "other"), []).append(req)
    chunks = []
    for category, rows in groups.items():
        body = []
        for req in rows:
            rid = _esc(req.get("id"), "需求")
            search_values = [req.get(k, "") for k in ("id", "category", "text", "conditions", "acceptance")]
            search_values.extend(source.get("quote", "") for source in req.get("sources", []) if isinstance(source, dict))
            search = _esc(" ".join(str(value) for value in search_values)).lower()
            cond = req.get("conditions") or []
            basis_label, basis_tone = _basis(req.get("basis_type"))
            body.append(
                f'<article class="requirement" data-category="{_esc(category)}" data-search="{search}"><div class="req-head"><span class="req-id">{rid}</span>'
                f'{_badge(basis_label, basis_tone)}<strong>{_esc(req.get("text"))}</strong></div><details class="req-detail"><summary>查看条件、验收和原文</summary><dl>'
                f'<div><dt>条件</dt><dd>{_esc(cond)}</dd></div><div><dt>验收</dt><dd>{_esc(req.get("acceptance"))}</dd></div>'
                f'<div><dt>原文</dt><dd>{_sources(req, source_docs, project, output)}</dd></div></dl></details></article>'
            )
        chunks.append(f'<section class="req-group"><h3>{_esc(CATEGORY_LABELS.get(category, category))}<small>{len(rows)} 条</small></h3>{"".join(body)}</section>')
    return "".join(chunks), {"total": len(requirements), "categories": {k: len(v) for k, v in groups.items()}}


def _render_scores(scoring: dict, source_docs: dict, project: Path, output: Path) -> tuple[str, dict]:
    data = scoring.get("data", {})
    items = data.get("items") or []
    declared = data.get("declared_total")
    parent_map = {item.get("id"): item.get("parent_id") for item in items if isinstance(item, dict)}

    def depth(item_id: object) -> int:
        seen = set()
        level = 0
        parent = parent_map.get(item_id)
        while parent and parent not in seen and level < 8:
            seen.add(parent)
            level += 1
            parent = parent_map.get(parent)
        return level

    rows = []
    for item in items:
        score = item.get("max_score")
        value = "待补" if score is None else _text(score)
        width = 0 if not isinstance(score, (int, float)) or not isinstance(declared, (int, float)) or declared <= 0 else min(100, max(0, score / declared * 100))
        rows.append(f'<article class="score-row" style="--score-depth:{depth(item.get("id"))}"><div class="score-top"><span class="req-id">{_esc(item.get("id"), "评分")}</span><strong>{_esc(item.get("title"))}</strong><b>{html.escape(value)} 分</b></div><div class="score-bar"><i style="width:{width:.1f}%"></i></div><p>{_esc(item.get("rule_text"))}</p><div class="source-line">{_sources(item, source_docs, project, output)}</div></article>')
    total_text = _text(declared) if declared is not None else "待补"
    note = "实际得分待企业资料、报价及演示核验。"
    score_rows = "".join(rows) or '<div class="empty">评分规则待补</div>'
    return f'<div class="score-summary"><span>规则满分</span><strong>{html.escape(total_text)} 分</strong><em>{html.escape(note)}</em></div>{score_rows}', {"nodes": len(items), "declared_total": declared}


def _render_compliance(compliance: dict, source_docs: dict, project: Path, output: Path) -> tuple[str, int]:
    groups: dict[str, list] = {}
    for rule in compliance.get("data", {}).get("rules", []) or []:
        if isinstance(rule, dict):
            groups.setdefault(str(rule.get("kind") or "other"), []).append(rule)
    chunks = []
    for kind, rows in groups.items():
        body = []
        for rule in rows:
            fatal = "明确否决" if rule.get("fatal") is True else "待核验"
            body.append(f'<article class="compliance-row"><div class="req-head"><span class="req-id">{_esc(rule.get("id"), "规则")}</span>{_badge(fatal, "red" if fatal == "明确否决" else "amber")}<strong>{_esc(rule.get("condition"))}</strong></div><dl><div><dt>后果</dt><dd>{_esc(rule.get("consequence"))}</dd></div><div><dt>行动</dt><dd>{_esc(rule.get("required_action"))}</dd></div><div><dt>责任/时点</dt><dd>{_esc(rule.get("responsible_role"))} · {_esc(rule.get("due_text"))}</dd></div><div><dt>原文</dt><dd>{_sources(rule, source_docs, project, output)}</dd></div></dl></article>')
        chunks.append(f'<section class="req-group"><h3>{_esc(COMPLIANCE_LABELS.get(kind, kind))}<small>{len(rows)} 条</small></h3>{"".join(body)}</section>')
    return "".join(chunks) or '<div class="empty">合规规则待补</div>', sum(len(v) for v in groups.values())


def _render_formats(formats: list, source_docs: dict, project: Path, output: Path) -> tuple[str, int]:
    groups = [("mandatory", "强制/必须核验", "blue"), ("reference", "参考/不能自动升级为必交", "muted"), ("unknown", "适用性待确认", "amber")]
    sections = []
    for strength, title, tone in groups:
        rows = [item for item in formats if isinstance(item, dict) and item.get("strength") == strength]
        if not rows:
            continue
        content = []
        for item in rows:
            content.append(f'<article class="format-row"><div class="req-head"><span class="req-id">{_esc(item.get("id"), "格式")}</span>{_badge(title, tone)}<strong>{_esc(item.get("title"))}</strong></div><p>{_esc(item.get("original_text"))}</p><div class="source-line">{_sources(item, source_docs, project, output)}</div></article>')
        sections.append(f'<section class="format-group"><h3>{html.escape(title)}<small>{len(rows)} 条</small></h3>{"".join(content)}</section>')
    return "".join(sections) or '<div class="empty">格式规则待补</div>', len(formats)


def _all_notes(bundle: dict) -> list[str]:
    notes: list[str] = []
    workflow = bundle["workflow"]
    for value in [workflow.get("summary"), *(workflow.get("warnings") or []), *(workflow.get("blockers") or [])]:
        if value:
            notes.append(str(value))
    for artifact in bundle["artifacts"].values():
        for value in [*(artifact.get("warnings") or []), *(artifact.get("blockers") or []), *(artifact.get("data", {}).get("unknowns") or [])]:
            if value:
                notes.append(str(value))
    for conflict in bundle["artifacts"]["bid-requirements"].get("data", {}).get("conflicts", []) or []:
        if isinstance(conflict, dict):
            notes.append(f'{conflict.get("id", "冲突")}: {conflict.get("description", "待澄清")}')
    seen = set()
    return [note for note in notes if not (note in seen or seen.add(note))]


def _safe_json_for_html(value: object) -> str:
    payload = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    return payload.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026").replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")


CLASSIC_CSS = r"""
:root{--blue:#1769aa;--blue-weak:#eaf3fb;--ink:#172b4d;--muted:#667085;--line:#e4e7ec;--paper:#fff;--canvas:#f5f7fa;--amber:#a15c00;--amber-bg:#fff6df;--red:#a63b32;--red-bg:#fff0ee}*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:var(--canvas);color:var(--ink);font:14px/1.65 -apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif}a{color:var(--blue);text-decoration:none}a:hover,a:focus-visible{text-decoration:underline}.shell{display:grid;grid-template-columns:230px minmax(0,1fr);min-height:100vh}.sidebar{position:sticky;top:0;height:100vh;padding:28px 18px;background:#f8fafc;border-right:1px solid var(--line)}.brand{font-weight:750;font-size:16px;letter-spacing:.02em}.brand small{display:block;color:var(--muted);font-size:11px;font-weight:500;margin-top:2px}.nav{display:grid;gap:5px;margin-top:28px}.nav a{display:block;padding:8px 10px;border-radius:6px;color:#475467}.nav a:hover,.nav a:focus-visible{background:#eaf3fb;color:var(--blue)}main{width:min(1180px,100%);margin:0 auto;padding:40px 48px 80px}.hero{padding:8px 0 28px;border-bottom:1px solid var(--line)}.eyebrow{color:var(--blue);font-size:12px;font-weight:700;letter-spacing:.08em}.hero h1{font-size:30px;line-height:1.3;margin:8px 0 10px;letter-spacing:-.03em}.hero p{max-width:800px;margin:0;color:var(--muted)}.statusbar{display:flex;flex-wrap:wrap;gap:10px;margin-top:18px}.badge{display:inline-flex;align-items:center;border-radius:999px;padding:2px 9px;font-size:12px;white-space:nowrap;font-weight:650}.badge.blue{color:var(--blue);background:var(--blue-weak)}.badge.amber{color:var(--amber);background:var(--amber-bg)}.badge.red{color:var(--red);background:var(--red-bg)}.badge.muted{color:#536071;background:#eef1f4}.section{margin-top:38px;scroll-margin-top:24px}.section>h2{font-size:20px;margin:0 0 14px;letter-spacing:-.02em}.section>h2 small,.req-group h3 small,.format-group h3 small{float:right;color:var(--muted);font-size:12px;font-weight:500}.panel{background:var(--paper);border:1px solid var(--line);border-radius:10px;padding:20px;box-shadow:0 1px 2px #10182808}.facts{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:1px;background:var(--line);border:1px solid var(--line);border-radius:8px;overflow:hidden}.fact{background:var(--paper);padding:15px}.fact dt{color:var(--muted);font-size:12px}.fact dd{margin:5px 0 0;font-weight:650;overflow-wrap:anywhere}.timeline{display:grid;gap:8px;margin-top:18px}.timeline div{display:flex;gap:18px;padding-bottom:8px;border-bottom:1px solid #f0f2f5}.timeline strong{min-width:160px}.timeline span{color:var(--muted)}.twocol{display:grid;grid-template-columns:1fr 1fr;gap:16px}.metric{font-size:30px;font-weight:750;color:var(--blue)}.metric-label{display:block;color:var(--muted);font-size:12px}.callout{border-left:3px solid var(--blue);background:var(--blue-weak);padding:12px 14px;color:#274c6c}.callout.amber{border-color:#df9b22;background:var(--amber-bg);color:#6e4a0d}.group-stack{display:grid;gap:18px}.req-group,.format-group{margin-top:18px}.req-group:first-child,.format-group:first-child{margin-top:0}.req-group h3,.format-group h3{font-size:15px;margin:0 0 8px;padding-bottom:8px;border-bottom:1px solid var(--line)}.requirement,.compliance-row,.format-row,.score-row{border-bottom:1px solid #eef0f3;padding:14px 0}.requirement:last-child,.compliance-row:last-child,.format-row:last-child,.score-row:last-child{border-bottom:0}.req-head{display:flex;align-items:flex-start;gap:9px}.req-head strong{flex:1;font-weight:600;min-width:0;overflow-wrap:anywhere}.req-id{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:12px;color:var(--muted);white-space:nowrap}.req-detail{margin:9px 0 0 78px}.req-detail dl,.compliance-row dl{display:grid;gap:7px;margin:0}.req-detail dl>div,.compliance-row dl>div{display:grid;grid-template-columns:76px minmax(0,1fr);gap:10px}.req-detail dt,.compliance-row dt{color:var(--muted);font-size:12px}.req-detail dd,.compliance-row dd{margin:0;overflow-wrap:anywhere}.source-ref{display:block;margin-top:2px}.quote{display:block;color:#667085;font-size:12px;margin-left:1em;white-space:pre-wrap}.pending{color:var(--amber)}.score-summary{display:flex;align-items:baseline;gap:18px;padding:12px 0 16px}.score-summary strong{font-size:26px}.score-summary em{color:var(--muted);font-style:normal}.score-top{display:flex;gap:10px;align-items:baseline}.score-top strong{flex:1}.score-top b{color:var(--blue);white-space:nowrap}.score-bar{height:7px;border-radius:99px;background:#edf1f5;margin:8px 0}.score-bar i{display:block;height:100%;border-radius:inherit;background:var(--blue)}.score-row p,.format-row p{margin:5px 0;color:#475467;overflow-wrap:anywhere}.source-line{font-size:12px}.searchbar{display:flex;gap:10px;margin-bottom:15px}.searchbar input{width:100%;border:1px solid #cbd5e1;border-radius:7px;padding:10px 12px;font:inherit;background:#fff}.searchbar input:focus-visible{outline:3px solid #b9dcf8;outline-offset:1px}.search-count{align-self:center;color:var(--muted);white-space:nowrap;font-size:12px}.trace{display:grid;gap:8px}.trace details{border:1px solid var(--line);border-radius:7px;background:#fafbfc;padding:10px 12px}.trace summary{cursor:pointer;font-weight:600}.trace code{font:12px/1.5 ui-monospace,SFMono-Regular,Menlo,monospace;overflow-wrap:anywhere;color:#475467}.empty{color:var(--muted);padding:10px 0}.footer{margin-top:42px;padding-top:16px;border-top:1px solid var(--line);font-size:12px;color:var(--muted)}@media(max-width:800px){.shell{display:block}.sidebar{position:static;height:auto;padding:15px 18px;border-right:0;border-bottom:1px solid var(--line)}.nav{display:flex;flex-wrap:wrap;gap:3px;margin-top:10px}.nav a{padding:4px 7px;font-size:12px}main{padding:27px 18px 60px}.hero h1{font-size:24px}.facts{grid-template-columns:repeat(2,minmax(0,1fr))}.twocol{grid-template-columns:1fr}.req-detail{margin-left:0}.req-detail dl>div,.compliance-row dl>div{grid-template-columns:65px minmax(0,1fr)}.score-summary{display:block}.score-summary strong{display:block}.timeline strong{min-width:105px}}@media print{body{background:#fff;font-size:10pt}.shell{display:block}.sidebar{display:none}main{width:auto;padding:0}.panel{box-shadow:none;break-inside:avoid}.section{margin-top:20px}.requirement,.compliance-row,.format-row,.score-row{break-inside:avoid}.req-detail{display:block}.searchbar{display:none}a{color:inherit;text-decoration:none}.footer{margin-top:20px}}
"""


def _enterprise_css() -> str:
    assets = Path(__file__).resolve().parents[1] / "assets" / "ui"
    tokens = _json(assets / "enterprise-tokens.json")

    def variables(values: dict) -> str:
        return ";".join(f"--report-{key}:{value}" for key, value in values.items()) + ";"

    common = variables(tokens["common"])
    light = variables(tokens["modes"]["light"])
    dark = variables(tokens["modes"]["dark"])
    return (
        f'html[data-ui="enterprise"]{{{common}{light}}}'
        f'html[data-ui="enterprise"][data-theme="dark"]{{{dark}}}'
        f'@media(prefers-color-scheme:dark){{html[data-ui="enterprise"][data-theme="system"]{{{dark}}}}}'
        f'@media print{{html[data-ui="enterprise"][data-theme]{{{light}}}}}'
        + (assets / "report-enterprise.css").read_text(encoding="utf-8")
    )


JS = r"""
(function(){const input=document.querySelector('#requirement-search');const selector=document.querySelector('#requirement-category');const count=document.querySelector('#requirement-count');if(!input||!selector)return;const rows=[...document.querySelectorAll('.requirement')];const groups=[...document.querySelectorAll('#requirements .req-group')];function update(){const q=input.value.trim().toLowerCase();const category=selector.value;let n=0;rows.forEach(row=>{const show=(!q||row.dataset.search.includes(q))&&(!category||row.dataset.category===category);row.hidden=!show;if(show)n++;});groups.forEach(group=>{group.hidden=!group.querySelector('.requirement:not([hidden])');});count.textContent=`显示 ${n} / ${rows.length} 条`+(n?'':' · 没有匹配结果');}input.addEventListener('input',update);selector.addEventListener('change',update);update();})();
(function(){
const theme=document.querySelector('#report-theme');
const classic=document.querySelector('#classic-style');
if(theme&&classic)theme.addEventListener('change',()=>{
    const legacy=theme.value==='classic';
    document.documentElement.dataset.ui=legacy?'classic':'enterprise';
    document.documentElement.dataset.theme=legacy?'light':theme.value;
    classic.media=legacy?'all':'not all';
});
const print=document.querySelector('#report-print');
if(print)print.addEventListener('click',()=>window.print());
const navigation=[...document.querySelectorAll('.nav a')];
function mark(){
    const hash=window.location.hash||'#overview';
    navigation.forEach(link=>{if(link.getAttribute('href')===hash)link.setAttribute('aria-current','location');else link.removeAttribute('aria-current');});
}
window.addEventListener('hashchange',mark);mark();
})();
(function(){
let previous=[];
window.addEventListener('beforeprint',()=>{
    previous=[...document.querySelectorAll('.requirement,.req-group,details')].map(el=>({el,hidden:el.hidden,open:el.open}));
    previous.forEach(({el})=>{el.hidden=false;if(el.tagName==='DETAILS')el.open=true;});
});
window.addEventListener('afterprint',()=>{
    previous.forEach(({el,hidden,open})=>{el.hidden=hidden;if(el.tagName==='DETAILS')el.open=open;});
    previous=[];
});
})();
"""


def render_html(bundle: dict, output: Path) -> tuple[str, dict]:
    project = bundle["project"]
    workflow = bundle["workflow"]
    artifacts = bundle["artifacts"]
    profile = artifacts["bid-project-profile"]
    routing = artifacts["routing"]
    requirements = artifacts["bid-requirements"].get("data", {}).get("requirements") or []
    scoring = artifacts["bid-scoring"]
    compliance = artifacts["bid-compliance"]
    formats = artifacts["bid-format-extraction"].get("data", {}).get("formats") or []
    source_docs = bundle["source_docs"]
    facts, deadlines, identifiers = _facts(profile, routing)
    req_html, req_meta = _render_requirements(requirements, source_docs, project, output)
    score_html, score_meta = _render_scores(scoring, source_docs, project, output)
    compliance_html, compliance_count = _render_compliance(compliance, source_docs, project, output)
    formats_html, format_count = _render_formats(formats, source_docs, project, output)
    notes = _all_notes(bundle)
    conflicts = artifacts["bid-requirements"].get("data", {}).get("conflicts") or []
    unknowns = []
    for artifact in artifacts.values():
        unknowns.extend(artifact.get("data", {}).get("unknowns") or [])
    unknowns.extend(workflow.get("data", {}).get("pending_decisions") or [])
    trace_rows = []
    for rel, entry in sorted(bundle["index"].items()):
        trace_rows.append(f'<div><strong>{_esc(rel)}</strong><span>产物 { _esc(entry.get("artifact_id")) } · revision { _esc(entry.get("revision")) } · <code>{_esc(entry.get("actual_sha256"))}</code></span></div>')
    source_rows = []
    for source_id, source in source_docs.items():
        source_rows.append(f'<div><strong>{_esc(source_id)} · {_esc(source.get("filename"))}</strong><span>{_esc(source.get("relative_path"))} · revision {_esc(source.get("revision"))} · <code>{_esc(source.get("actual_sha256"))}</code></span></div>')
    note_html = "".join(f"<li>{_esc(note)}</li>" for note in notes) or "<li>无新增说明</li>"
    conflict_html = "".join(f'<article class="format-row"><div class="req-head"><span class="req-id">{_esc(c.get("id"), "冲突")}</span>{_badge("待澄清", "amber")}<strong>{_esc(c.get("description"))}</strong></div><p>{_esc(_analysis_copy(c.get("resolution")))}</p></article>' for c in conflicts if isinstance(c, dict)) or '<div class="empty">未提取冲突；不代表业务已确认。</div>'
    unknown_html = "".join(f"<li>{_esc(item)}</li>" for item in dict.fromkeys(_analysis_copy(x) for x in unknowns if x)) or "<li>待补</li>"
    data_for_js = {"requirements": [{"id": r.get("id"), "category": r.get("category"), "text": r.get("text")} for r in requirements if isinstance(r, dict)]}
    category_options = '<option value="">全部类别</option>' + "".join(
        f'<option value="{_esc(category)}">{_esc(CATEGORY_LABELS.get(category, category))}</option>' for category in req_meta["categories"]
    )
    title = profile.get("data", {}).get("project_name") or workflow.get("project_id")
    lot_structure = routing.get("classification", {}).get("lot_structure") or routing.get("lot_structure")
    lot_label = LOT_LABELS.get(lot_structure, "标包待确认")
    template_labels = [TEMPLATE_LABELS.get(category, category) for category in routing.get("selected_template_categories", [])]
    first_source = next(iter(source_docs.values()))
    original_action = _link(output, project, first_source["relative_path"], "查看原件")
    original_action = original_action.replace('<a ', '<a class="report-action" ', 1)
    identifiers_html = f'<details class="identifiers"><summary>项目与标段编号</summary><dl class="identifier-list">{identifiers}</dl></details>' if identifiers else ""
    html_doc = f'''<!doctype html>
<html lang="zh-CN" data-ui="enterprise" data-theme="system"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="color-scheme" content="light dark"><link rel="icon" href="data:,"><title>{_esc(title)} · 招标处理结果</title><style>{_enterprise_css()}</style><style id="classic-style" media="not all">{CLASSIC_CSS}.score-row{{padding-left:calc(var(--score-depth,0) * 18px)}}</style></head>
<body class="report"><div class="shell"><aside class="sidebar"><div class="brand">招标处理结果</div><nav class="nav" aria-label="报告目录"><a href="#overview">项目概览</a><a href="#classification">分类与模板</a><a href="#scoring">评分规则</a><a href="#requirements">需求矩阵</a><a href="#compliance">合规与履约</a><a href="#formats">格式与模板</a><a href="#clarifications">冲突与待澄清</a><a href="#trace">溯源详情</a></nav></aside>
<div class="workspace"><div class="report-topbar"><span class="document-kind">招标理解报告</span><div class="toolbar" role="group" aria-label="报告操作"><button id="report-print" class="report-action primary" type="button">打印报告</button>{original_action}<label class="theme-field" for="report-theme">外观<select id="report-theme" class="theme-select"><option value="system">跟随系统</option><option value="light">浅色</option><option value="dark">深色</option><option value="classic">原版浅色</option></select></label></div></div>
<main class="report-main"><header class="hero"><div class="title-row"><h1>{_esc(title)}</h1>{_badge("待业务复核", "amber")}</div><details class="report-scope"><summary>分析范围与待确认</summary><p>仅分析所提供招标文件。企业资格、实际得分和正式响应范围尚未核验或确认。</p><p>{_esc(routing.get("summary") or profile.get("summary"))}</p></details></header>
<section id="overview" class="section"><h2>项目概览</h2><div class="facts">{facts}</div>{identifiers_html}<div class="panel timeline">{deadlines}</div></section>
<section id="classification" class="section"><h2>分类与模板</h2><div class="panel"><dl class="classification-grid"><div><dt>标包结构</dt><dd>{_esc(lot_label)}</dd></div><div><dt>选用模板类别</dt><dd>{_esc(template_labels, "待补")}</dd></div></dl><div class="callout amber">进入响应前确认类别与标包范围；通用模板不自动成为必交材料。</div></div></section>
<section id="scoring" class="section"><h2>评分规则 <small>{score_meta["nodes"]} 个层级节点</small></h2><div class="panel">{score_html}</div></section>
<section id="requirements" class="section"><h2>需求矩阵 <small>{req_meta["total"]} 条</small></h2><div class="panel"><div class="searchbar"><label class="filter-field" for="requirement-search">搜索需求<input id="requirement-search" class="filter-input" type="search" placeholder="编号、原文、条件或验收说明" aria-label="搜索需求"></label><label class="filter-field" for="requirement-category">需求类别<select id="requirement-category" class="filter-select" aria-label="按需求类别筛选">{category_options}</select></label><span id="requirement-count" class="search-count" role="status" aria-live="polite"></span></div>{req_html}</div></section>
<section id="compliance" class="section"><h2>合规与履约 <small>{compliance_count} 条规则</small></h2><div class="panel"><div class="callout amber">企业资料尚未提供，资格及要求满足性待核验。</div><div class="group-stack">{compliance_html}</div></div></section>
<section id="formats" class="section"><h2>格式与模板 <small>{format_count} 条</small></h2><div class="panel"><div class="group-stack">{formats_html}</div></div></section>
<section id="clarifications" class="section"><h2>原文冲突与待澄清</h2><div class="twocol"><div class="panel"><h3>冲突</h3>{conflict_html}</div><div class="panel"><h3>待补/待确认</h3><ul>{unknown_html}</ul></div></div></section>
<section id="trace" class="section"><h2>溯源详情</h2><div class="panel trace"><details><summary>文件与版本信息</summary><p>项目ID：{_esc(workflow.get("project_id"))}<br>产物ID：{_esc(workflow.get("artifact_id"))}<br>版本：{_esc(workflow.get("revision"))}<br>分析版本时间：{_esc(workflow.get("created_at"))}</p></details><details><summary>分析产物与校验值</summary><div class="timeline">{"".join(trace_rows)}</div></details><details><summary>原件与校验值</summary><div class="timeline">{"".join(source_rows)}</div></details><details><summary>处理说明</summary><ul>{note_html}</ul></details><details><summary>生成检查</summary><p>已核对当前输入版本、文件校验值及原件关联。输入变化后需要重新生成报告。</p></details></div></section>
</main></div></div><script type="application/json" id="report-data">{_safe_json_for_html(data_for_js)}</script><script>{JS}</script></body></html>'''
    meta = {"requirements": req_meta, "scores": score_meta, "compliance": compliance_count, "formats": format_count}
    return html_doc, meta


def _write_atomic(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(content)
        os.replace(temp_name, path)
    except Exception:
        try:
            os.unlink(temp_name)
        except OSError:
            pass
        raise


def generate(project: str | Path, out: str | Path = "reports/tender-report.html", *, overwrite: bool = False) -> dict:
    project_path = Path(project).expanduser().resolve()
    bundle = _load_project(project_path)
    output = _inside(project_path, str(out), "报告输出", must_exist=False)
    if output.suffix.lower() != ".html":
        raise ReportInputError("报告输出必须是.html文件")
    manifest = output.with_name(output.stem + ".manifest.json")
    if (output.exists() or manifest.exists()) and not overwrite:
        raise FileExistsError(f"输出已存在，使用--overwrite或指定新路径：{output}")
    backups: list[str] = []
    if overwrite and (output.exists() or manifest.exists()):
        history = output.parent / "history"
        history.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        for previous in (output, manifest):
            if not previous.exists():
                continue
            candidate = history / f"{previous.stem}.{stamp}{previous.suffix}"
            suffix = 1
            while candidate.exists():
                candidate = history / f"{previous.stem}.{stamp}.{suffix}{previous.suffix}"
                suffix += 1
            shutil.copy2(previous, candidate)
            backups.append(candidate.relative_to(project_path).as_posix())
    document, counts = render_html(bundle, output)
    _write_atomic(output, document)
    generated_at = datetime.now(timezone.utc).isoformat()
    manifest_data = {
        "schema_version": "1.0",
        "status": bundle["workflow"].get("status", "needs_review"),
        "report_status": "generated_needs_review",
        "generated_at": generated_at,
        "project_id": bundle["workflow"]["project_id"],
        "workflow": {"relative_path": WORKFLOW_REL, "artifact_id": bundle["workflow"].get("artifact_id"), "revision": bundle["workflow"].get("revision"), "sha256": bundle["workflow_hash"]},
        "inputs": [{"artifact_id": entry["artifact_id"], "revision": entry["revision"], "relative_path": rel, "sha256": entry["actual_sha256"], "bytes": _inside(project_path, rel, "manifest input").stat().st_size} for rel, entry in sorted(bundle["index"].items())],
        "source_documents": [{"source_id": source_id, "revision": source.get("revision"), "relative_path": source.get("relative_path"), "sha256": source["actual_sha256"], "bytes": _inside(project_path, source["relative_path"], "manifest source").stat().st_size} for source_id, source in sorted(bundle["source_docs"].items())],
        "counts": counts,
        "previous_output_backups": backups,
        "report": {"relative_path": output.relative_to(project_path).as_posix(), "sha256": sha256(output), "bytes": output.stat().st_size},
    }
    _write_atomic(manifest, json.dumps(manifest_data, ensure_ascii=False, indent=2) + "\n")
    return manifest_data


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="从当前17-workflow-state生成离线招标HTML处理报告")
    parser.add_argument("--project", required=True, help="真实项目目录")
    parser.add_argument("--out", default="reports/tender-report.html", help="相对项目目录的HTML输出路径")
    parser.add_argument("--overwrite", action="store_true", help="明确允许覆盖同名HTML及manifest")
    args = parser.parse_args(argv)
    try:
        manifest = generate(args.project, args.out, overwrite=args.overwrite)
    except (ReportInputError, FileExistsError) as exc:
        parser.error(str(exc))
    print(json.dumps({"status": manifest["report_status"], "report": manifest["report"], "manifest": str(Path(args.out).with_suffix(".manifest.json"))}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
