from __future__ import annotations
import html
import math
import json
import re
from urllib.parse import quote, urlsplit
from pathlib import Path
from typing import Any

from .stage_management import STAGE_DEFINITIONS, stage_by_id, stage_from_name

ROOT = Path(__file__).resolve().parents[2]
TEMPLATE_DIR = ROOT / "display" / "templates"
CSS_PATH = ROOT / "display" / "css" / "default.css"


def esc(value: Any) -> str:
    if value is None:
        return "待确认"
    return html.escape(str(value), quote=True)


def li(items: list[Any]) -> str:
    if not items:
        return "<li class='ql-empty'>暂无</li>"
    return "".join(f"<li>{esc(x)}</li>" for x in items)


def table_rows(rows: list[dict[str, Any]], fields: list[str]) -> str:
    if not rows:
        return f"<tr><td colspan='{len(fields)}'>暂无</td></tr>"
    out = []
    for row in rows:
        out.append("<tr>" + "".join(f"<td>{esc(row.get(f))}</td>" for f in fields) + "</tr>")
    return "".join(out)


def compact(value: Any, limit: int = 160) -> str:
    text = "" if value is None else str(value)
    text = " ".join(text.split())
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "..."


def replace_tokens(template: str, mapping: dict[str, Any]) -> str:
    return re.sub(r"\{\{([^{}]+)\}\}", lambda match: str(mapping.get(match.group(1), match.group(0))), template)


class SkillDisplayRenderer:
    def __init__(self, template_dir: str | Path | None = None):
        self.template_dir = Path(template_dir) if template_dir else TEMPLATE_DIR
        self.css = CSS_PATH.read_text(encoding="utf-8") if CSS_PATH.exists() else ""

    def render(self, template_id: str, data: dict[str, Any], output_format: str = "html", *, theme: str = "light", profile: str = "enterprise") -> dict[str, str]:
        if template_id == "opportunity_detail":
            html_body = self._render_opportunity_detail(data)
        elif template_id == "customer_profile":
            html_body = self._render_customer_profile(data)
        elif template_id == "opportunity_list":
            html_body = self._render_list(data)
        elif template_id == "opportunity_kanban":
            html_body = self._render_kanban(data)
        elif template_id == "risk_table":
            html_body = self._render_risk_table(data)
        elif template_id == "next_action_list":
            html_body = self._render_next_actions(data)
        else:
            html_body = self._render_opportunity_card(data)
        if template_id in {"opportunity_card", "customer_profile", "risk_table", "next_action_list"}:
            html_body = "<div class='ql-page'><header class='ql-topbar'><span class='ql-breadcrumb'>QILIN · 企灵 / 商机工作区</span></header><main class='ql-main'>" + html_body + "</main></div>"
        theme = "dark" if theme == "dark" else "light"
        profile = "legacy" if profile == "legacy" else "enterprise"
        css = (CSS_PATH.parent / "legacy.css").read_text(encoding="utf-8") if profile == "legacy" else self.css
        full_html = (
            "<!doctype html>\n"
            f"<html lang='zh-CN' data-ui='{profile}' data-theme='{theme}'>\n"
            "<head>\n"
            "<meta charset='utf-8'>\n"
            "<meta name='viewport' content='width=device-width, initial-scale=1'>\n"
            f"<title>{esc(data.get('opportunity', {}).get('name') or '企灵商机工作区')}</title>\n"
            f"<style>{css}</style>\n"
            "</head>\n"
            f"<body class='ql-app'>{html_body}</body>\n"
            "</html>"
        )
        markdown = self.to_markdown(data)
        return {"html": full_html, "markdown": markdown, "template_id": template_id}

    def _render_opportunity_card(self, data: dict[str, Any]) -> str:
        tpl = (self.template_dir / "opportunity_card.html").read_text(encoding="utf-8")
        account = data.get("account", {})
        opp = dict(data.get("opportunity", {}))
        lifecycle = self._lifecycle(data)
        assessment = data.get("commercial_assessment", {}) or {}
        probability = opp.get("win_probability")
        opp["win_probability_percent"] = f"{round(probability * 100)}%" if isinstance(probability, (int, float)) else "待评估"
        mapping = {
            "opportunity.name": esc(opp.get("name")),
            "lifecycle.summary": self._lifecycle_summary(data),
            "account.company_name": esc(account.get("company_name")),
            "account.industry": esc(account.get("industry")),
            "account.region": esc(account.get("region")),
            "opportunity.score_level": esc(opp.get("score_level")),
            "opportunity.score_level_tag": f"<span class='ql-tag'>等级 {esc(opp['score_level'])}</span>" if opp.get("score_level") else "",
            "opportunity.score_level_note": f"{esc(opp['score_level'])}级商机" if opp.get("score_level") else "",
            "opportunity.score": esc(opp.get("score")),
            "opportunity.stage": esc(self._stage_label(lifecycle.get("current_stage_id"))),
            "opportunity.stage_reason": esc(opp.get("stage_reason")),
            "opportunity.stage_confidence_label": esc(self._confidence_label(opp.get("stage_confidence"))),
            "opportunity.stage_confirmed_label": esc("待确认" if not lifecycle.get("current_stage_id") else self._opportunity_confirmed_label({"stage_id": lifecycle.get("current_stage_id")})),
            "opportunity.stage_path": self._stage_path(lifecycle),
            "opportunity.risk_level": esc(opp.get("risk_level")),
            "opportunity.risk_label": esc(self._risk_label(opp.get("risk_level"))),
            "opportunity.win_probability_percent": esc(opp.get("win_probability_percent")),
            "opportunity.core_need": esc(opp.get("core_need")),
            "opportunity.budget_signal": esc(opp.get("budget_signal")),
            "opportunity.budget_amount": esc(opp.get("budget_amount")),
            "opportunity.expected_timeline": esc(opp.get("expected_timeline")),
            "evidence.count": esc(len(data.get("evidence", []))),
            "assessment.confidence_level": esc(self._confidence_label(assessment.get("confidence_level"))),
            "assessment.confirmation_note": esc(self._assessment_confirmation_note(assessment)),
            "assessment.win_probability_note": esc(self._win_probability_note(assessment)),
            "pain_points_list": li(opp.get("pain_points", [])),
            "requirements_list": li(opp.get("requirements", [])),
            "next_actions_list": self._action_items(lifecycle.get("actions") or data.get("next_actions", [])),
            "missing_information_list": li(opp.get("missing_information", []) or data.get("missing_information", [])),
        }
        return replace_tokens(tpl, mapping)

    def _render_opportunity_detail(self, data: dict[str, Any]) -> str:
        card = self._render_opportunity_card(data)
        tpl = (self.template_dir / "opportunity_detail.html").read_text(encoding="utf-8")
        opp = dict(data.get("opportunity", {}))
        lifecycle = self._lifecycle(data)
        mapping = {
            "opportunity_card": card,
            "lifecycle.sections": self._lifecycle_sections(data),
            "account.company_name": esc(data.get("account", {}).get("company_name")),
            "account.business_summary": esc(data.get("account", {}).get("business_summary")),
            "opportunity.stage": esc(self._stage_label(lifecycle.get("current_stage_id"))),
            "opportunity.stage_reason": esc(opp.get("stage_reason")),
            "opportunity.stage_confidence_label": esc(self._confidence_label(opp.get("stage_confidence"))),
            "opportunity.stage_confirmed_label": esc("待确认" if not lifecycle.get("current_stage_id") else self._opportunity_confirmed_label({"stage_id": lifecycle.get("current_stage_id")})),
            "opportunity.stage_path": self._stage_path(lifecycle),
            "contacts.count": esc(len(data.get("contacts", []))),
            "decision_chain.summary": esc(self._decision_chain_summary(data.get("decision_chain", []))),
            "assessment.summary": esc(self._assessment_summary(data.get("commercial_assessment", {}))),
            "assessment.win_likelihood_score": esc(data.get("commercial_assessment", {}).get("win_likelihood_score")),
            "assessment.deal_attractiveness_score": esc(data.get("commercial_assessment", {}).get("deal_attractiveness_score")),
            "assessment.delivery_confidence_score": esc(data.get("commercial_assessment", {}).get("delivery_confidence_score")),
            "assessment.unanswered_critical_count": esc(data.get("commercial_assessment", {}).get("unanswered_critical_count")),
            "assessment_radar_chart": self._assessment_radar_chart(data.get("commercial_assessment", {})),
            "assessment_dimension_bars": self._assessment_dimension_bars(data.get("commercial_assessment", {}).get("dimensions", [])),
            "assessment_dimension_rows": self._assessment_dimension_rows(data.get("commercial_assessment", {}).get("dimensions", [])),
            "missing.count": esc(len(data.get("opportunity", {}).get("missing_information", []))),
            "evidence.count": esc(len(data.get("evidence", []))),
            "materials.count": esc(len(self._collect_archived_files(data))),
            "pain_points_list": li(data.get("opportunity", {}).get("pain_points", [])),
            "next_actions_list": self._action_items(lifecycle.get("actions") or data.get("next_actions", [])),
            "missing_information_list": li(data.get("opportunity", {}).get("missing_information", [])),
            "contacts_rows": self._contacts_rows(data.get("contacts", [])),
            "decision_chain_map": self._decision_chain_map(data.get("decision_chain", []), opp),
            "decision_chain_rows": self._decision_chain_rows(data.get("decision_chain", [])),
            "risks_rows": self._risk_rows(data.get("risks", [])),
            "evidence_list": self._evidence_items(data.get("evidence", [])),
            "material_gallery": self._material_gallery(data),
        }
        return replace_tokens(tpl, mapping)

    def _render_customer_profile(self, data: dict[str, Any]) -> str:
        tpl = (self.template_dir / "customer_profile.html").read_text(encoding="utf-8")
        account = data.get("account", {})
        mapping = {
            "account.company_name": esc(account.get("company_name")),
            "account.industry": esc(account.get("industry")),
            "account.region": esc(account.get("region")),
            "account.company_size": esc(account.get("company_size")),
            "account.business_summary": esc(account.get("business_summary")),
            "current_systems_list": li(account.get("current_systems", [])),
            "pain_points_list": li(account.get("key_pain_points", [])),
        }
        return replace_tokens(tpl, mapping)

    def _render_risk_table(self, data: dict[str, Any]) -> str:
        tpl = (self.template_dir / "risk_table.html").read_text(encoding="utf-8")
        return replace_tokens(tpl, {"risks_rows": self._risk_rows(data.get("risks", []))})

    def _render_next_actions(self, data: dict[str, Any]) -> str:
        tpl = (self.template_dir / "next_action_list.html").read_text(encoding="utf-8")
        return replace_tokens(tpl, {"next_actions_list": self._action_items(self._lifecycle(data).get("actions") or data.get("next_actions", []))})

    def _query_records(self, data: dict[str, Any]) -> list[dict[str, Any]]:
        records = data.get("opportunities", [])
        return records if isinstance(records, list) else []

    def _record_data(self, record: dict[str, Any]) -> dict[str, Any]:
        return record if isinstance(record.get("opportunity"), dict) else {**record, "opportunity": record}

    def _record_title(self, record: dict[str, Any]) -> str:
        data = self._record_data(record)
        opp = data["opportunity"]
        title = esc(opp.get("name"))
        url = self._safe_url(record.get("detail_url") or opp.get("detail_url") or record.get("url"))
        return f"<a class='ql-link' href='{esc(url)}'>{title} →</a>" if url else title

    def _render_list(self, data: dict[str, Any]) -> str:
        rows = []
        for record in self._query_records(data):
            item = self._record_data(record)
            opp = item["opportunity"]
            life = self._lifecycle(item)
            action = self._next_action(life)
            values = [self._record_title(record), esc(opp.get("company_name") or item.get("account", {}).get("company_name")),
                      esc(life.get("owner") or life.get("owner_name") or opp.get("owner") or opp.get("owner_name")),
                      esc(self._stage_label(life.get("current_stage_id"))), esc(self._stage_label(life.get("suggested_stage_id"))),
                      esc(self._status_label(life.get("status"))), esc(action.get("action_title") or action.get("title")),
                      esc(action.get("due_date") or action.get("due_at")), esc(self._blockers(item)), esc(opp.get("score"))]
            rows.append("<tr>" + "".join(f"<td>{value}</td>" for value in values) + "</tr>")
        tpl = (self.template_dir / "opportunity_list.html").read_text(encoding="utf-8")
        return replace_tokens(tpl, {"list_rows": "".join(rows) or "<tr><td colspan='10' class='ql-empty'>暂无商机</td></tr>",
                                    "summary.count": len(rows), "query.summary": esc(self._query_summary(data.get("query", {})))})

    def _render_kanban(self, data: dict[str, Any]) -> str:
        records = self._query_records(data)
        buckets: dict[str, list[dict[str, Any]]] = {stage.stage_id: [] for stage in self._pipeline_stages()}
        buckets.update({"unconfirmed": [], "paused": [], "lost": [], "cancelled": []})
        confirmed_count = 0
        for record in records:
            item = self._record_data(record)
            life = self._lifecycle(item)
            stage_id = life.get("current_stage_id") or "unconfirmed"
            if life.get("status") in {"paused", "lost", "cancelled"}:
                stage_id = life["status"]
            buckets.setdefault(str(stage_id), []).append(record)
            if life.get("current_stage_id") and self._opportunity_confirmed_label({"stage_id": life["current_stage_id"]}) == "已确认商机":
                confirmed_count += 1
        columns = []
        for stage_id, items in buckets.items():
            if stage_id in {"unconfirmed", "paused", "lost", "cancelled"} and not items:
                continue
            cards = []
            for record in items:
                item = self._record_data(record)
                life = self._lifecycle(item)
                opp = item["opportunity"]
                cards.append("<article class='kanban-card'>" + f"<h3>{self._record_title(record)}</h3>"
                             + f"<p class='kanban-account'>{esc(opp.get('company_name') or item.get('account', {}).get('company_name'))}</p>"
                             + self._lifecycle_summary(item)
                             + f"<div class='ql-record-score'>评分 {esc(opp.get('score'))} · 风险 {esc(self._risk_label(opp.get('risk_level')))} · {esc('尚未确认商机' if not life.get('current_stage_id') else self._opportunity_confirmed_label({'stage_id': life['current_stage_id']}))}</div>"
                             + "</article>")
            label = self._status_label(stage_id) if stage_id in {"paused", "lost", "cancelled"} else self._stage_label(stage_id)
            columns.append(f"<section class='kanban-col'><div class='kanban-col-head'><h2>{esc(label)}</h2><span>{len(items)}</span></div>"
                           + "<div class='kanban-card-list'>" + ("".join(cards) or "<div class='kanban-empty'>暂无商机</div>") + "</div></section>")
        tpl = (self.template_dir / "opportunity_kanban.html").read_text(encoding="utf-8")
        return replace_tokens(tpl, {"kanban_columns": "".join(columns), "query.summary": esc(self._query_summary(data.get("query", {}))),
                                    "summary.count": len(records), "summary.confirmed": confirmed_count})

    def _safe_url(self, value: Any) -> str:
        if not value:
            return ""
        raw = str(value).strip()
        if any(ord(char) < 32 for char in raw) or raw.startswith("//") or "\\" in raw:
            return ""
        if urlsplit(raw).scheme.lower() not in {"", "http", "https", "file"}:
            return ""
        return quote(raw, safe="/:._-%#?=&")

    def _pipeline_stages(self) -> list[Any]:
        return [stage for stage in STAGE_DEFINITIONS if stage.stage_id not in {"lost", "cancelled", "paused"}]

    def _stage_label(self, stage_id: Any) -> str:
        if not stage_id or stage_id == "unconfirmed":
            return "待确认"
        stage = stage_by_id(str(stage_id))
        if stage:
            return stage.name
        return {"contract_signing": "合同签署", "signed": "已签单"}.get(str(stage_id), str(stage_id))

    def _lifecycle(self, data: dict[str, Any]) -> dict[str, Any]:
        value = data.get("lifecycle")
        if isinstance(value, dict):
            return value
        if "current_stage_id" in data:
            return data
        opp = data.get("opportunity", {})
        suggested = self._resolve_stage_definition(opp)
        return {"current_stage_id": None, "suggested_stage_id": suggested.stage_id if suggested else opp.get("stage"),
                "status": "unconfirmed", "revision": None, "actions": data.get("next_actions", []), "history": []}

    def _next_action(self, life: dict[str, Any]) -> dict[str, Any]:
        if "next_action" in life:
            selected = life["next_action"]
            return selected if isinstance(selected, dict) else ({"title": selected} if selected else {})
        pending = [action for action in life.get("actions", []) or [] if action.get("status") not in {"completed", "done", "cancelled"}]
        return min(pending, key=lambda action: (action.get("due_date") or action.get("due_at") or "9999", action.get("created_at") or "")) if pending else {}

    def _blockers(self, data: dict[str, Any]) -> str:
        life = self._lifecycle(data)
        values = life.get("blockers", []) if "blockers" in life else data.get("opportunity", {}).get("missing_information") or []
        if isinstance(values, list):
            return "；".join(self._blocker_label(value) for value in values)
        return str(values)

    def _fact_label(self, fact_id: Any) -> str:
        return {"contact_established": "客户接触已建立", "need_confirmed": "客户需求已确认", "requirement_owner": "需求负责人", "continue_intent": "继续推进意愿", "solution_scope": "方案范围", "budget_confirmed": "预算已确认", "quote_authorized": "报价已授权"}.get(str(fact_id), "自定义事实")

    def _kind_label(self, kind: Any) -> Any:
        return {"solution": "解决方案", "proposal": "方案", "quote": "报价", "negotiation": "谈判纪要", "contract": "合同", "handoff": "交接包"}.get(str(kind), kind)

    def _blocker_label(self, value: Any) -> str:
        text = str(value)
        if text.startswith("fact unresolved, missing or negative: "):
            return "待确认：" + self._fact_label(text.rsplit(": ", 1)[-1])
        if text.startswith("current artifact stale or missing: "):
            return str(self._kind_label(text.rsplit(": ", 1)[-1])) + "文件已变更或缺失"
        return {"quote authorization is stale or unbound": "报价授权已过期或未绑定当前版本", "signed contract record missing": "缺少已签署合同登记", "signed contract stale, missing or superseded": "签署合同文件已变更、缺失或被新版本替代"}.get(text, text)

    def _lifecycle_summary(self, data: dict[str, Any]) -> str:
        life = self._lifecycle(data)
        opp = data.get("opportunity", {})
        action = self._next_action(life)
        fields = [("当前阶段", self._stage_label(life.get("current_stage_id"))), ("建议阶段", self._stage_label(life.get("suggested_stage_id"))),
                  ("状态", self._status_label(life.get("status"))), ("负责人", life.get("owner") or life.get("owner_name") or opp.get("owner") or opp.get("owner_name")),
                  ("下一行动", action.get("action_title") or action.get("title")), ("期限", action.get("due_date") or action.get("due_at")),
                  ("阻塞", self._blockers(data) or "暂无已登记阻塞"), ("版本", life.get("revision")), ("文件状态", self._file_status(life))]
        if life.get("close_reason"):
            fields.append(("结束原因", life["close_reason"]))
        return "<dl class='ql-lifecycle-summary'>" + "".join(f"<div><dt>{label}</dt><dd>{esc(value)}</dd></div>" for label, value in fields) + "</dl>"

    def _file_status(self, life: dict[str, Any]) -> str:
        if not life.get("artifacts"):
            return "未登记"
        if any(artifact.get("validity") in {"stale_or_missing", "invalid"} or artifact.get("valid") is False for artifact in life["artifacts"]):
            return "需复核"
        if life.get("verification_status") == "current":
            return "文件未变更"
        return "需复核"

    def _record_details(self, records: Any, empty: str) -> str:
        if not records:
            return f"<p class='ql-empty'>{esc(empty)}</p>"
        if isinstance(records, dict):
            records = [records]
        labels = {"from_stage": "原阶段", "to_stage": "新阶段", "from_stage_id": "原阶段", "to_stage_id": "新阶段", "at": "时间", "created_at": "时间", "actor": "操作者", "time": "时间", "reason": "理由", "evidence_ids": "证据", "evidence": "证据", "id": "编号", "artifact_id": "成果编号", "kind": "类型", "type": "类型", "version": "版本", "status": "状态", "valid": "有效性", "validity": "有效性", "invalid_reason": "失效原因", "document_id": "文档编号", "metadata": "成果信息", "validity_reason": "有效性说明", "sha256": "文件校验", "title": "名称", "name": "名称", "value": "事实", "result": "结果", "signed_at": "签署时间", "signed_file": "签署文件", "fact_id": "事实编号", "signing_date": "签署日期", "amount": "合同金额", "currency": "币种", "verification_scope": "核验范围", "parties": "签约主体", "signature_facts": "签署登记", "relative_path": "归档文件", "archive_path": "归档文件", "archived_path": "归档文件", "file_path": "文件", "path": "文件", "url": "链接"}
        output = []
        for record in records:
            if not isinstance(record, dict):
                output.append(f"<li>{esc(record)}</li>")
                continue
            fields = []
            audit_fields = []
            if record.get("fact_id"):
                fields.append(f"<div><dt>事项</dt><dd>{esc(self._fact_label(record['fact_id']))}</dd></div>")
            for key, value in record.items():
                if value is None:
                    continue
                if key in {"from_stage", "to_stage", "from_stage_id", "to_stage_id"}:
                    value = self._stage_label(value)
                elif key in {"status", "validity"}:
                    value = self._status_label(value)
                elif key in {"kind", "type"}:
                    value = self._kind_label(value)
                elif key == "currency":
                    value = {"CNY": "人民币（CNY）", "USD": "美元（USD）", "EUR": "欧元（EUR）"}.get(str(value), value)
                elif key == "verification_scope" and value == "Recorded signature facts; no legal or signature authenticity verification.":
                    value = "仅登记签署事实；签名真实性与法律效力未核验。"
                elif key == "parties" and isinstance(value, list):
                    value = "；".join(str(party) for party in value)
                elif isinstance(value, bool):
                    value = "是" if value else "否"
                elif isinstance(value, (list, dict)):
                    value = json.dumps(value, ensure_ascii=False)
                shown = esc(value)
                if key == "signature_facts" and isinstance(record[key], dict):
                    signatures = record[key]
                    summary = "；".join(label + ("已登记签署" if signatures.get(field) is True else "待登记") for field, label in [("customer_signed", "客户："), ("supplier_signed", "供应商：")])
                    fields.append(f"<div><dt>签署登记</dt><dd>{esc(summary)}</dd></div>")
                if key in {"file_path", "path", "url", "signed_file"}:
                    target_path = record.get("relative_path") or record.get("archive_path") or record.get("archived_path") or value
                    link = self._safe_url(target_path) if not str(target_path).startswith("/") else ""
                    label = Path(str(value)).name if key in {"file_path", "path", "signed_file"} else str(value)
                    shown = f"<a class='ql-link' href='{esc(link)}'>{esc(label)} ↗</a>" if link else esc(label)
                    if str(value).startswith("/"):
                        audit_fields.append(f"<div><dt>源文件路径</dt><dd>{esc(value)}</dd></div>")
                target = audit_fields if key in {"id", "fact_id", "artifact_id", "document_id", "sha256", "evidence", "evidence_ids", "metadata", "signature_facts", "relative_path", "archive_path", "archived_path"} or (isinstance(record.get(key), (list, dict)) and key != "parties") else fields
                target.append(f"<div><dt>{esc(labels.get(key, key))}</dt><dd>{shown}</dd></div>")
            audit_html = ""
            if audit_fields:
                audit_html = "<details class='ql-disclosure ql-record-audit'><summary>编号与证据</summary><dl class='ql-record-fields'>" + "".join(audit_fields) + "</dl></details>"
            invalid = record.get("validity") in {"superseded", "stale_or_missing", "invalid"} or record.get("valid") is False or record.get("status") in {"stale", "invalid"}
            output.append(("<li class='ql-record-invalid'>" if invalid else "<li>") + "<dl class='ql-record-fields'>" + "".join(fields) + "</dl>" + audit_html + "</li>")
        return "<ul class='ql-record-list'>" + "".join(output) + "</ul>"

    def _lifecycle_sections(self, data: dict[str, Any]) -> str:
        life = self._lifecycle(data)
        sections = [("history", "阶段历史", "暂无正式阶段变更"), ("facts", "已登记事实", "暂无已登记事实"),
                    ("artifacts", "版本成果", "暂无版本成果"), ("contracts", "合同与签署", "暂无合同记录")]
        if life.get("status_history"):
            sections.append(("status_history", "状态变更", "暂无状态变更"))
        return "".join(f"<section id='{key}' class='ql-panel'><div class='ql-panel-header'><h2 class='ql-panel-title'>{label}</h2></div>"
                       + "<div class='ql-panel-body'>" + self._record_details(life.get(key), empty) + "</div></section>" for key, label, empty in sections)

    def _resolve_stage_definition(self, opportunity: dict[str, Any]) -> Any:
        stage_id = opportunity.get("stage_id")
        if stage_id:
            stage_def = stage_by_id(str(stage_id))
            if stage_def is not None:
                return stage_def
        return stage_from_name(opportunity.get("stage"))

    def _query_summary(self, query: dict[str, Any]) -> str:
        filters = query.get("filters", {}) if isinstance(query, dict) else {}
        parts = []
        for key, label in [("stage", "阶段"), ("risk_level", "风险"), ("company_name", "客户"), ("min_score", "最低分")]:
            if filters.get(key) is not None:
                parts.append(f"{label}:{filters.get(key)}")
        return " / ".join(parts) if parts else "全部"

    def _risk_class(self, risk: Any) -> str:
        value = str(risk or "").lower()
        if value in {"high", "medium", "low"}:
            return value
        return "medium"

    def _risk_label(self, risk: Any) -> str:
        mapping = {"high": "高", "medium": "中", "low": "低"}
        return mapping.get(str(risk), "待确认")

    def _opportunity_confirmed_label(self, opportunity: dict[str, Any]) -> str:
        value = opportunity.get("opportunity_confirmed")
        if value is None:
            stage_id = opportunity.get("stage_id")
            stage_def = stage_by_id(str(stage_id)) if stage_id else None
            if stage_def is None:
                stage_def = stage_from_name(opportunity.get("stage"))
            value = bool(stage_def and stage_def.is_opportunity_confirmed)
        elif isinstance(value, str):
            value = value.strip().lower() in {"true", "1", "yes", "y"}
        else:
            value = bool(value)
        return "已确认商机" if value else "尚未确认商机"

    def _stage_path(self, lifecycle: dict[str, Any]) -> str:
        current_id = lifecycle.get("current_stage_id")
        parts = []
        for stage in self._pipeline_stages():
            current = stage.stage_id == current_id
            classes = "ql-stage-step ql-stage-step-current" if current else "ql-stage-step ql-stage-step-future"
            if stage.stage_id == "opportunity_confirmed":
                classes += " ql-stage-confirmed-marker"
            parts.append(f"<div class='{classes}'><span class='ql-stage-dot' aria-hidden='true'></span><strong>{esc(stage.name)}</strong></div>")
        if current_id and not stage_by_id(str(current_id)):
            parts.append(f"<div class='ql-stage-step ql-stage-step-current ql-stage-step-unmapped'><strong>{esc(current_id)}</strong></div>")
        return "".join(parts)

    def _action_items(self, actions: list[dict[str, Any]]) -> str:
        if not actions:
            return "<li class='ql-empty'>暂无行动</li>"
        out = []
        for a in actions:
            evidence = a.get("completion_evidence_ids") or a.get("evidence_ids") or a.get("evidence")
            if isinstance(evidence, (list, dict)):
                evidence = json.dumps(evidence, ensure_ascii=False)
            out.append("<li>" + f"<strong>{esc(a.get('action_title') or a.get('title'))}</strong> "
                       + f"<span class='ql-tag'>{esc(self._status_label(a.get('status') or 'open'))}</span>"
                       + "<dl class='ql-record-fields'>"
                       + f"<div><dt>负责人</dt><dd>{esc(a.get('owner') or a.get('owner_name'))}</dd></div>"
                       + f"<div><dt>期限</dt><dd>{esc(a.get('due_date') or a.get('due_at'))}</dd></div>"
                       + f"<div><dt>优先级</dt><dd>{esc(self._priority_label(a.get('priority')))}</dd></div>"
                       + f"<div><dt>依据</dt><dd>{esc(a.get('reason'))}</dd></div>"
                       + f"<div><dt>结果</dt><dd>{esc(a.get('result'))}</dd></div>"
                       + f"<div><dt>完成证据</dt><dd>{esc(evidence)}</dd></div></dl></li>")
        return "".join(out)

    def _priority_label(self, priority: Any) -> str:
        mapping = {"high": "高", "medium": "中", "low": "低"}
        return mapping.get(str(priority), esc(priority))

    def _contacts_rows(self, contacts: list[dict[str, Any]]) -> str:
        if not contacts:
            return "<tr><td colspan='8'>暂无</td></tr>"
        rows = []
        for c in contacts:
            fallback_status = "confirmed" if c.get("is_requirement_owner") else "missing"
            status = self._status_label(c.get("confirmation_status") or fallback_status)
            rows.append(
                "<tr>"
                f"<td>{esc(c.get('name'))}</td>"
                f"<td>{esc(c.get('title'))}</td>"
                f"<td>{esc(c.get('department'))}</td>"
                f"<td>{esc(c.get('role_in_opportunity'))}</td>"
                f"<td>{esc(c.get('responsibility_scope'))}</td>"
                f"<td>{status}</td>"
                f"<td>{esc(c.get('phone'))}</td>"
                f"<td>{esc(c.get('email'))}</td>"
                "</tr>"
            )
        return "".join(rows)

    def _decision_chain_summary(self, nodes: list[dict[str, Any]]) -> str:
        if not nodes:
            return "待识别"
        confirmed = sum(1 for n in nodes if n.get("status") == "confirmed")
        return f"已确认 {confirmed}/{len(nodes)} 个节点"

    def _decision_chain_rows(self, nodes: list[dict[str, Any]]) -> str:
        if not nodes:
            return "<tr><td colspan='5'>暂无</td></tr>"
        rows = []
        for node in nodes:
            status = "已确认" if node.get("status") == "confirmed" else "待补充"
            person = node.get("person_name") or "待确认"
            title = node.get("title")
            person_text = f"{esc(person)}<br/><span class='ql-muted-text'>{esc(title)}</span>" if title else esc(person)
            rows.append(
                "<tr>"
                f"<td>{esc(node.get('decision_role'))}</td>"
                f"<td>{person_text}</td>"
                f"<td><span class='ql-tag {self._influence_class(node.get('influence_level'))}'>{esc(self._influence_label(node.get('influence_level')))}</span></td>"
                f"<td>{esc(node.get('responsibility_scope'))}</td>"
                f"<td><strong>{status}</strong><br/><span class='ql-muted-text'>{esc(node.get('next_step'))}</span></td>"
                "</tr>"
            )
        return "".join(rows)

    def _decision_chain_map(self, nodes: list[dict[str, Any]], opportunity: dict[str, Any]) -> str:
        if not nodes:
            return "<div class='ql-decision-map-empty'>暂无决策链节点</div>"
        by_role = {str(node.get("decision_role")): node for node in nodes}

        def node_for(role: str, fallback_influence: str, fallback_scope: str) -> dict[str, Any]:
            node = dict(by_role.get(role, {}))
            node.setdefault("decision_role", role)
            node.setdefault("status", "missing")
            node.setdefault("influence_level", fallback_influence)
            node.setdefault("responsibility_scope", fallback_scope)
            return node

        root = node_for("最终决策人/关键拍板人", "high", "项目优先级、预算审批、最终决策")
        business_owner = node_for("业务需求负责人", "high", "业务痛点、验收指标和现场使用要求")
        project_owner = node_for("项目推进负责人", "high", "项目计划、跨部门协同、方案落地")
        technical_owner = node_for("技术评估负责人", "medium", "技术可行性、检测点位、设备选型")
        integration_owner = node_for("IT/系统集成负责人", "medium", "MES对接、系统集成、安全与上线")
        procurement_owner = node_for("采购/商务负责人", "medium", "预算区间、商务流程、合同推进")

        def card(node: dict[str, Any], role_class: str) -> str:
            status = "confirmed" if node.get("status") == "confirmed" else "missing"
            status_text = "已确认" if status == "confirmed" else "待确认"
            person = node.get("person_name") or "待确认"
            influence = self._influence_label(node.get("influence_level"))
            concern = compact(node.get("responsibility_scope"), 42)
            return (
                f"<article class='ql-decision-node ql-decision-node-{esc(status)} {role_class}'>"
                "<div class='ql-decision-node-main'>"
                "<span class='ql-decision-avatar' aria-hidden='true'>●</span>"
                "<div>"
                f"<strong>{esc(node.get('decision_role'))}</strong>"
                f"<p>{esc(person)}</p>"
                "<div class='ql-decision-badges'>"
                f"<em>{esc(status_text)}</em>"
                f"<em>{esc(influence)}影响</em>"
                "</div>"
                "</div>"
                "</div>"
                f"<small>关注：{esc(concern)}</small>"
                "</article>"
            )

        return (
            "<div class='ql-decision-map ql-decision-tree'>"
            "<svg class='ql-decision-tree-lines' viewBox='0 0 1000 560' preserveAspectRatio='none' aria-hidden='true'>"
            "<path d='M500 112 V162 H250 V200'/>"
            "<path d='M500 162 H750 V200'/>"
            "<path d='M250 310 V352'/>"
            "<path d='M250 462 V498 H145'/>"
            "<path d='M250 498 H355'/>"
            "</svg>"
            + card(root, "ql-decision-root")
            + "<div class='ql-decision-lane ql-decision-lane-business'>业务线</div>"
            + "<div class='ql-decision-lane ql-decision-lane-procurement'>交付/采购线</div>"
            + card(business_owner, "ql-decision-business-owner")
            + card(project_owner, "ql-decision-project-owner")
            + card(technical_owner, "ql-decision-technical-owner")
            + card(integration_owner, "ql-decision-integration-owner")
            + card(procurement_owner, "ql-decision-procurement-owner")
            + "</div>"
        )

    def _influence_class(self, influence: Any) -> str:
        if influence == "high":
            return "orange"
        if influence == "medium":
            return "green"
        return ""

    def _influence_label(self, influence: Any) -> str:
        mapping = {"high": "高", "medium": "中", "low": "低"}
        return mapping.get(str(influence), "待确认")

    def _assessment_summary(self, assessment: dict[str, Any]) -> str:
        if not assessment:
            return "待评估"
        confidence = self._confidence_label(assessment.get("confidence_level"))
        unanswered = assessment.get("unanswered_critical_count", 0)
        return f"可信度 {confidence}，{unanswered} 个关键问题待商务确认"

    def _assessment_confirmation_note(self, assessment: dict[str, Any]) -> str:
        if not assessment:
            return "待商务确认"
        score = assessment.get("assessment_confidence_score")
        unanswered = assessment.get("unanswered_critical_count", 0)
        return f"可信度{score}，关键待确认{unanswered}项"

    def _win_probability_note(self, assessment: dict[str, Any]) -> str:
        if not assessment:
            return "基于初始材料估算"
        return "由商务评估维度折算，回答关键问题后重算"

    def _confidence_label(self, level: Any) -> str:
        mapping = {"high": "高", "medium": "中", "low": "低"}
        return mapping.get(str(level), "待确认")

    def _category_label(self, category: Any) -> str:
        mapping = {
            "win_likelihood": "赢单可能性",
            "deal_attractiveness": "商机价值",
            "delivery_confidence": "交付信心",
        }
        return mapping.get(str(category), esc(category))

    def _rating_label(self, rating: Any) -> str:
        mapping = {"strong": "强", "medium": "中", "weak": "弱", "unknown": "未知"}
        return mapping.get(str(rating), "未知")

    def _assessment_radar_chart(self, assessment: dict[str, Any]) -> str:
        if not assessment:
            return "<div class='ql-empty'>暂无评估数据</div>"
        dimensions = assessment.get("dimensions", []) or []
        if not dimensions:
            return "<div class='ql-empty'>暂无维度评分</div>"
        score_by_category = {
            "win_likelihood": assessment.get("win_likelihood_score"),
            "deal_attractiveness": assessment.get("deal_attractiveness_score"),
            "delivery_confidence": assessment.get("delivery_confidence_score"),
        }
        order = ["win_likelihood", "deal_attractiveness", "delivery_confidence"]
        panels = []
        for category in order:
            items = [d for d in dimensions if d.get("category") == category]
            if not items:
                continue
            panels.append(self._dimension_radar_panel(category, int(score_by_category.get(category) or 0), items))
        return "<div class='ql-radar-stack'>" + "".join(panels) + "</div>"

    def _dimension_radar_panel(self, category: str, category_score: int, dimensions: list[dict[str, Any]]) -> str:
        priority = {"P0": 0, "P1": 1, "P2": 2}
        items = sorted(dimensions, key=lambda x: (priority.get(x.get("priority"), 9), x.get("label") or ""))
        center = (220.0, 195.0)
        radius = 104.0
        label_radius = 154.0
        count = len(items)

        def point(index: int, value_radius: float) -> tuple[float, float]:
            angle = -math.pi / 2 + (2 * math.pi * index / max(count, 1))
            return (
                center[0] + math.cos(angle) * value_radius,
                center[1] + math.sin(angle) * value_radius,
            )

        def polygon_for(scale: float) -> str:
            return " ".join(f"{x:.1f},{y:.1f}" for x, y in (point(i, radius * scale) for i in range(count)))

        rings = "".join(f"<polygon points='{polygon_for(scale)}' class='ql-radar-ring'/>" for scale in (1.0, 0.66, 0.33))
        spokes = "".join(
            f"<line x1='{center[0]:.1f}' y1='{center[1]:.1f}' x2='{point(i, radius)[0]:.1f}' y2='{point(i, radius)[1]:.1f}' class='ql-radar-spoke'/>"
            for i in range(count)
        )
        data_points = [
            point(i, radius * (max(0, min(int(item.get("score") or 0), 100)) / 100))
            for i, item in enumerate(items)
        ]
        data_polygon = " ".join(f"{x:.1f},{y:.1f}" for x, y in data_points)
        points = "".join(f"<circle cx='{x:.1f}' cy='{y:.1f}' r='3.6' class='ql-radar-point'/>" for x, y in data_points)

        def label_tspans(label: Any, score: int, x: float, y: float, anchor: str) -> str:
            text = compact(label, 10)
            if len(text) <= 5:
                lines = [f"{text} {score}"]
            else:
                lines = [text[:5], f"{text[5:]} {score}"]
            start_y = y - 7 if len(lines) > 1 else y
            spans = [
                f"<tspan x='{x:.1f}' y='{start_y:.1f}'>{esc(lines[0])}</tspan>"
            ]
            for line in lines[1:]:
                spans.append(f"<tspan x='{x:.1f}' dy='15'>{esc(line)}</tspan>")
            return f"<text text-anchor='{anchor}'>" + "".join(spans) + "</text>"

        labels = []
        for i, item in enumerate(items):
            x, y = point(i, label_radius)
            anchor = "middle"
            if x < center[0] - 18:
                anchor = "end"
                x = max(x, 72.0)
            elif x > center[0] + 18:
                anchor = "start"
                x = min(x, 368.0)
            score = int(item.get("score") or 0)
            labels.append(label_tspans(item.get("label"), score, x, y, anchor))
        return (
            "<section class='ql-radar-panel'>"
            "<div class='ql-radar-panel-head'>"
            f"<strong>{esc(self._category_label(category))}</strong>"
            f"<span>概况 {esc(category_score)}分</span>"
            "</div>"
            f"<svg class='ql-radar-chart' viewBox='0 0 440 390' role='img' aria-label='{esc(self._category_label(category))}维度评分雷达图'>"
            + rings
            + spokes
            + f"<polygon points='{data_polygon}' class='ql-radar-area'/>"
            + points
            + "<g class='ql-radar-labels'>"
            + "".join(labels)
            + "</g>"
            + "</svg>"
            "</section>"
        )

    def _assessment_dimension_bars(self, dimensions: list[dict[str, Any]]) -> str:
        if not dimensions:
            return "<div class='ql-empty'>暂无维度评分</div>"
        priority = {"P0": 0, "P1": 1, "P2": 2}
        rows = []
        for item in sorted(dimensions, key=lambda x: (priority.get(x.get("priority"), 9), x.get("category") or "", x.get("dimension_id") or "")):
            score = max(0, min(100, int(item.get("score") or 0)))
            status = self._evidence_status_label(item.get("evidence_status"))
            rows.append(
                "<div class='ql-dimension-bar'>"
                "<div class='ql-dimension-bar-head'>"
                f"<strong>{esc(item.get('label'))}</strong>"
                f"<span>{esc(score)}分 · {esc(status)}</span>"
                "</div>"
                "<div class='ql-bar-track' aria-hidden='true'>"
                f"<span style='width:{score}%'></span>"
                "</div>"
                "</div>"
            )
        return "".join(rows)

    def _evidence_status_label(self, status: Any) -> str:
        mapping = {
            "needs_sales_confirmation": "待商务确认",
            "sales_confirmed": "商务已确认",
            "inferred": "材料推断",
            "confirmed": "材料确认",
        }
        return mapping.get(str(status), "待确认")

    def _assessment_dimension_rows(self, dimensions: list[dict[str, Any]]) -> str:
        if not dimensions:
            return "<tr><td colspan='5'>暂无</td></tr>"
        rows = []
        priority = {"P0": 0, "P1": 1, "P2": 2}
        for item in sorted(dimensions, key=lambda x: (priority.get(x.get("priority"), 9), x.get("category") or "", x.get("dimension_id") or "")):
            rating = item.get("rating") or "unknown"
            status = "待商务确认" if item.get("evidence_status") == "needs_sales_confirmation" else ("商务已确认" if item.get("evidence_status") == "sales_confirmed" else "材料推断")
            rows.append(
                "<tr>"
                f"<td><strong>{esc(item.get('label'))}</strong><br/><span class='ql-muted-text'>{esc(status)}</span></td>"
                f"<td>{esc(self._category_label(item.get('category')))}</td>"
                f"<td><span class='ql-tag rating-{esc(rating)}'>{esc(self._rating_label(rating))}</span><br/><span class='ql-muted-text'>{esc(item.get('score'))}分</span></td>"
                f"<td>{esc(item.get('rationale'))}</td>"
                f"<td>{esc(item.get('question'))}" + (f"<br/><strong>已记录回答</strong><br/>{esc(item.get('answer'))}" if item.get("answer") else "") + "</td>"
                "</tr>"
            )
        return "".join(rows)

    def _risk_rows(self, risks: list[dict[str, Any]]) -> str:
        if not risks:
            return "<tr><td colspan='4'>暂无</td></tr>"
        rows = []
        for r in risks:
            level = esc(self._risk_class(r.get("risk_level")))
            rows.append(
                "<tr>"
                f"<td><span class='ql-tag risk-{level}'>{esc(self._risk_label(r.get('risk_level')))}</span></td>"
                f"<td>{esc(self._risk_type_label(r.get('risk_type')))}</td>"
                f"<td>{esc(r.get('description'))}</td>"
                f"<td>{esc(r.get('mitigation'))}</td>"
                "</tr>"
            )
        return "".join(rows)

    def _risk_type_label(self, risk_type: Any) -> str:
        mapping = {
            "budget": "预算",
            "decision_chain": "决策链",
            "delivery": "交付",
            "competition": "竞争",
            "timeline": "时间",
        }
        return mapping.get(str(risk_type), esc(risk_type))

    def _localized_level_text(self, value: Any) -> str:
        text = "" if value is None else str(value)
        replacements = {
            "high": "高",
            "medium": "中",
            "low": "低",
            "confirmed": "已确认",
            "missing": "待补充",
        }
        for source, target in replacements.items():
            text = text.replace(source, target)
        return text

    def _evidence_items(self, evidence: list[dict[str, Any]]) -> str:
        if not evidence:
            return "<li class='ql-empty'>暂无</li>"
        out = []
        for ev in evidence:
            file_count = len(ev.get("archived_files", []) or [])
            badge = f"<span class='ql-file-badge'>{file_count} 个原始文件</span>" if file_count else ""
            out.append(
                "<li>"
                f"<strong>{esc(ev.get('source_name'))}</strong>"
                f"{badge}"
                f"<details class='ql-disclosure'><summary>{esc(compact(ev.get('content'), 100))}</summary><p>{esc(ev.get('content'))}</p></details>"
                "</li>"
            )
        return "".join(out)

    def _collect_archived_files(self, data: dict[str, Any]) -> list[dict[str, Any]]:
        files: list[dict[str, Any]] = []
        seen = set()
        for item in data.get("archived_files", []) or []:
            key = item.get("id") or item.get("sha256") or item.get("archived_path")
            if key and key not in seen:
                seen.add(key)
                files.append(item)
        for ev in data.get("evidence", []) or []:
            for item in ev.get("archived_files", []) or []:
                key = item.get("id") or item.get("sha256") or item.get("archived_path")
                if key and key not in seen:
                    seen.add(key)
                    files.append(item)
        return files

    def _material_gallery(self, data: dict[str, Any]) -> str:
        files = self._collect_archived_files(data)
        if not files:
            return "<div class='ql-material-empty'>暂无归档材料</div>"
        cards = []
        for item in files:
            href = item.get("relative_path") or item.get("archived_path") or item.get("original_path") or "#"
            href = self._safe_url(href)
            href = "" if href == "#" else href
            name = item.get("display_name") or item.get("file_name") or "原始材料"
            file_name = item.get("file_name") or name
            mime = item.get("mime_type") or "文件"
            size = self._format_size(item.get("size_bytes"))
            if href and (item.get("is_image") or str(mime).startswith("image/")):
                thumb = f"<img src='{esc(href)}' alt='{esc(name)}'>"
            else:
                thumb = f"<div class='ql-file-icon'>{esc(Path(str(file_name)).suffix.upper() or 'FILE')}</div>"
            cards.append(
                (f"<a class='ql-material-card' href='{esc(href)}' target='_blank' rel='noopener'>" if href else "<div class='ql-material-card ql-material-unavailable'>")
                +
                f"<div class='ql-material-thumb'>{thumb}</div>"
                "<div class='ql-material-meta'>"
                f"<strong>{esc(name)}</strong>"
                f"<span>{esc(file_name)}</span>"
                f"<small>{esc(mime)} · {esc(size)}"
                + ("" if href else " · 材料链接不可用") + "</small>"
                + "</div>"
                + ("</a>" if href else "</div>")
            )
        return "".join(cards)

    def _format_size(self, size: Any) -> str:
        try:
            value = int(size)
        except (TypeError, ValueError):
            return "大小待确认"
        if value >= 1024 * 1024:
            return f"{value / (1024 * 1024):.1f} MB"
        if value >= 1024:
            return f"{value / 1024:.1f} KB"
        return f"{value} B"

    def to_markdown(self, data: dict[str, Any]) -> str:
        def text(value: Any) -> str:
            if isinstance(value, (dict, list)):
                value = json.dumps(value, ensure_ascii=False)
            value = esc(value).replace("\n", " ")
            return re.sub(r"([\\`*_{}\[\]()#+!|])", r"\\\1", value)

        if "opportunities" in data:
            lines = ["# 企灵商机列表", "", "| 商机 | 当前阶段 | 建议阶段 | 状态 | 负责人 | 下一行动 | 期限 | 阻塞 |", "|---|---|---|---|---|---|---|---|"]
            for record in self._query_records(data):
                item = self._record_data(record)
                life = self._lifecycle(item)
                action = self._next_action(life)
                values = [item["opportunity"].get("name"), self._stage_label(life.get("current_stage_id")), self._stage_label(life.get("suggested_stage_id")),
                          self._status_label(life.get("status")), life.get("owner") or item["opportunity"].get("owner"),
                          action.get("title") or action.get("action_title"), action.get("due_date"), self._blockers(item)]
                lines.append("| " + " | ".join(text(value) for value in values) + " |")
            return "\n".join(lines)
        account = data.get("account", {})
        opp = data.get("opportunity", {})
        life = self._lifecycle(data)
        lines = [f"# {text(opp.get('name', '商机详情'))}", "", f"客户：{text(account.get('company_name'))}",
                 f"当前阶段：{text(self._stage_label(life.get('current_stage_id')))}", f"建议阶段：{text(self._stage_label(life.get('suggested_stage_id')))}",
                 f"状态：{text(self._status_label(life.get('status')))}", f"版本：{text(life.get('revision'))}",
                 f"负责人：{text(life.get('owner') or opp.get('owner'))}", f"阻塞：{text(self._blockers(data) or '暂无已登记阻塞')}",
                 f"文件状态：{text(self._file_status(life))}", f"结束原因：{text(life.get('close_reason'))}" if life.get("close_reason") else "",
                 f"评分：{text(opp.get('score'))} / 100", f"风险：{text(self._risk_label(opp.get('risk_level')))}",
                 "", "## 核心需求", text(opp.get("core_need")), "", "## 行动与结果"]
        for action in life.get("actions") or data.get("next_actions", []):
            lines.append(f"- {text(action.get('title') or action.get('action_title'))}｜{text(self._status_label(action.get('status') or 'open'))}｜负责人 {text(action.get('owner'))}｜期限 {text(action.get('due_date'))}｜结果 {text(action.get('result'))}｜完成证据 {text(action.get('completion_evidence_ids') or action.get('evidence_ids') or action.get('evidence'))}")
        for key, label in [("history", "阶段历史"), ("facts", "已登记事实"), ("artifacts", "版本成果"), ("contracts", "合同与签署"), ("status_history", "状态变更")]:
            lines.extend(["", f"## {label}"])
            records = life.get(key) or []
            if isinstance(records, dict):
                records = [records]
            lines.extend(f"- {text(record)}" for record in records)
            if not records:
                lines.append("暂无记录")
        for key, label in [("contacts", "联系人"), ("decision_chain", "决策链"), ("risks", "风险清单"), ("evidence", "证据来源")]:
            lines.extend(["", f"## {label}"])
            lines.extend(f"- {text(record)}" for record in data.get(key, []))
        assessment = data.get("commercial_assessment", {}) or {}
        if assessment:
            lines.extend(["", "## 商务确认评估", f"- 赢单可能性：{text(assessment.get('win_likelihood_score'))}",
                          f"- 商机价值：{text(assessment.get('deal_attractiveness_score'))}", f"- 交付信心：{text(assessment.get('delivery_confidence_score'))}",
                          f"- 评估可信度：{text(self._confidence_label(assessment.get('confidence_level')))}"])
            lines.extend(f"- {text(record)}" for record in assessment.get("dimensions", []))
        for key, label in [("pain_points", "痛点"), ("requirements", "建设要求"), ("missing_information", "待确认信息")]:
            lines.extend(["", f"## {label}"])
            lines.extend(f"- {text(item)}" for item in opp.get(key, []))
        lines.extend(["", "## 原始材料"])
        for item in self._collect_archived_files(data):
            path = item.get("relative_path") or item.get("archived_path") or item.get("original_path")
            lines.append(f"- {text(item.get('display_name') or item.get('file_name'))}: {text(path)}")
        return "\n".join(lines)

    def _status_label(self, status: Any) -> str:
        mapping = {"confirmed": "已确认", "missing": "待补充", "open": "待处理", "active": "进行中", "unconfirmed": "待确认", "completed": "已完成", "done": "已完成", "paused": "暂停", "lost": "丢单", "cancelled": "取消", "signed": "已签单", "won": "已签单", "registered": "已登记", "needs_review": "需复核", "stale": "已过期", "invalid": "已失效", "valid": "有效", "superseded": "已被新版本替代", "stale_or_missing": "文件已变更或缺失", "verified": "已核验", "unverified": "待核验"}
        return mapping.get(str(status), esc(status))
