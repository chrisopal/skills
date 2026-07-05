from __future__ import annotations
import html
from urllib.parse import quote
from pathlib import Path
from typing import Any

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
    result = template
    for key, value in mapping.items():
        result = result.replace("{{" + key + "}}", str(value))
    return result


class SkillDisplayRenderer:
    def __init__(self, template_dir: str | Path | None = None):
        self.template_dir = Path(template_dir) if template_dir else TEMPLATE_DIR
        self.css = CSS_PATH.read_text(encoding="utf-8") if CSS_PATH.exists() else ""

    def render(self, template_id: str, data: dict[str, Any], output_format: str = "html") -> dict[str, str]:
        if template_id == "opportunity_detail":
            html_body = self._render_opportunity_detail(data)
        elif template_id == "customer_profile":
            html_body = self._render_customer_profile(data)
        elif template_id == "opportunity_kanban":
            html_body = self._render_kanban(data)
        elif template_id == "risk_table":
            html_body = self._render_risk_table(data)
        elif template_id == "next_action_list":
            html_body = self._render_next_actions(data)
        else:
            html_body = self._render_opportunity_card(data)
        full_html = (
            "<!doctype html>\n"
            "<html lang='zh-CN'>\n"
            "<head>\n"
            "<meta charset='utf-8'>\n"
            "<meta name='viewport' content='width=device-width, initial-scale=1'>\n"
            f"<style>{self.css}</style>\n"
            "</head>\n"
            f"<body>{html_body}</body>\n"
            "</html>"
        )
        markdown = self.to_markdown(data)
        return {"html": full_html, "markdown": markdown, "template_id": template_id}

    def _render_opportunity_card(self, data: dict[str, Any]) -> str:
        tpl = (self.template_dir / "opportunity_card.html").read_text(encoding="utf-8")
        account = data.get("account", {})
        opp = dict(data.get("opportunity", {}))
        opp["win_probability_percent"] = int(round((opp.get("win_probability") or 0) * 100))
        mapping = {
            "opportunity.name": esc(opp.get("name")),
            "account.company_name": esc(account.get("company_name")),
            "account.industry": esc(account.get("industry")),
            "account.region": esc(account.get("region")),
            "opportunity.score_level": esc(opp.get("score_level")),
            "opportunity.score": esc(opp.get("score")),
            "opportunity.stage": esc(opp.get("stage")),
            "opportunity.stage_reason": esc(opp.get("stage_reason")),
            "opportunity.risk_level": esc(opp.get("risk_level")),
            "opportunity.win_probability_percent": esc(opp.get("win_probability_percent")),
            "opportunity.core_need": esc(opp.get("core_need")),
            "opportunity.budget_signal": esc(opp.get("budget_signal")),
            "opportunity.budget_amount": esc(opp.get("budget_amount")),
            "opportunity.expected_timeline": esc(opp.get("expected_timeline")),
            "evidence.count": esc(len(data.get("evidence", []))),
            "pain_points_list": li(opp.get("pain_points", [])),
            "requirements_list": li(opp.get("requirements", [])),
            "next_actions_list": self._action_items(data.get("next_actions", [])),
            "missing_information_list": li(opp.get("missing_information", []) or data.get("missing_information", [])),
        }
        return replace_tokens(tpl, mapping)

    def _render_opportunity_detail(self, data: dict[str, Any]) -> str:
        card = self._render_opportunity_card(data)
        tpl = (self.template_dir / "opportunity_detail.html").read_text(encoding="utf-8")
        mapping = {
            "opportunity_card": card,
            "account.company_name": esc(data.get("account", {}).get("company_name")),
            "account.business_summary": esc(data.get("account", {}).get("business_summary")),
            "contacts.count": esc(len(data.get("contacts", []))),
            "decision_chain.summary": esc(self._decision_chain_summary(data.get("decision_chain", []))),
            "missing.count": esc(len(data.get("opportunity", {}).get("missing_information", []))),
            "evidence.count": esc(len(data.get("evidence", []))),
            "materials.count": esc(len(self._collect_archived_files(data))),
            "pain_points_list": li(data.get("opportunity", {}).get("pain_points", [])),
            "next_actions_list": self._action_items(data.get("next_actions", [])),
            "missing_information_list": li(data.get("opportunity", {}).get("missing_information", [])),
            "contacts_rows": self._contacts_rows(data.get("contacts", [])),
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
        return replace_tokens(tpl, {"next_actions_list": self._action_items(data.get("next_actions", []))})

    def _render_kanban(self, data: dict[str, Any]) -> str:
        tpl = (self.template_dir / "opportunity_kanban.html").read_text(encoding="utf-8")
        opportunities = data.get("opportunities", []) if isinstance(data.get("opportunities"), list) else []
        stages = ["线索", "初步沟通", "需求确认", "方案交流", "投标/报价", "商务谈判", "赢单", "丢单"]
        columns = []
        for stage in stages:
            cards = []
            for opp in opportunities:
                if opp.get("stage") == stage:
                    cards.append(f"<div class='kanban-card'><strong>{esc(opp.get('name'))}</strong><br/>评分：{esc(opp.get('score'))}｜风险：{esc(opp.get('risk_level'))}</div>")
            columns.append(f"<div class='kanban-col'><h3>{esc(stage)}</h3>{''.join(cards) or '<p>暂无</p>'}</div>")
        return replace_tokens(tpl, {"kanban_columns": "".join(columns)})

    def _action_items(self, actions: list[dict[str, Any]]) -> str:
        if not actions:
            return "<li>暂无</li>"
        out = []
        for a in actions:
            out.append(
                "<li>"
                f"<strong>{esc(a.get('action_title'))}</strong>"
                f"<span class='ql-tag orange'>{esc(a.get('priority'))}</span><br/>"
                f"<span>{esc(a.get('reason'))}</span>"
                "</li>"
            )
        return "".join(out)

    def _contacts_rows(self, contacts: list[dict[str, Any]]) -> str:
        if not contacts:
            return "<tr><td colspan='8'>暂无</td></tr>"
        rows = []
        for c in contacts:
            status = "需求负责人" if c.get("is_requirement_owner") else esc(c.get("confirmation_status"))
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
                f"<td><span class='ql-tag {self._influence_class(node.get('influence_level'))}'>{esc(node.get('influence_level'))}</span></td>"
                f"<td>{esc(node.get('responsibility_scope'))}</td>"
                f"<td><strong>{status}</strong><br/><span class='ql-muted-text'>{esc(node.get('next_step'))}</span></td>"
                "</tr>"
            )
        return "".join(rows)

    def _influence_class(self, influence: Any) -> str:
        if influence == "high":
            return "orange"
        if influence == "medium":
            return "green"
        return ""

    def _risk_rows(self, risks: list[dict[str, Any]]) -> str:
        if not risks:
            return "<tr><td colspan='4'>暂无</td></tr>"
        rows = []
        for r in risks:
            level = esc(r.get("risk_level"))
            rows.append(
                "<tr>"
                f"<td><span class='ql-tag risk-{level}'>{level}</span></td>"
                f"<td>{esc(r.get('risk_type'))}</td>"
                f"<td>{esc(r.get('description'))}</td>"
                f"<td>{esc(r.get('mitigation'))}</td>"
                "</tr>"
            )
        return "".join(rows)

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
                f"{esc(compact(ev.get('content'), 220))}"
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
            href = quote(str(href), safe="/:._-%#?=&")
            name = item.get("display_name") or item.get("file_name") or "原始材料"
            file_name = item.get("file_name") or name
            mime = item.get("mime_type") or "文件"
            size = self._format_size(item.get("size_bytes"))
            if item.get("is_image") or str(mime).startswith("image/"):
                thumb = f"<img src='{esc(href)}' alt='{esc(name)}'>"
            else:
                thumb = f"<div class='ql-file-icon'>{esc(Path(str(file_name)).suffix.upper() or 'FILE')}</div>"
            cards.append(
                f"<a class='ql-material-card' href='{esc(href)}' target='_blank' rel='noopener'>"
                f"<div class='ql-material-thumb'>{thumb}</div>"
                "<div class='ql-material-meta'>"
                f"<strong>{esc(name)}</strong>"
                f"<span>{esc(file_name)}</span>"
                f"<small>{esc(mime)} · {esc(size)}</small>"
                "</div>"
                "</a>"
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
        account = data.get("account", {})
        opp = data.get("opportunity", {})
        lines = [
            f"# {opp.get('name', '商机详情')}",
            "",
            f"**客户：** {account.get('company_name', '待确认')}",
            f"**行业/地区：** {account.get('industry', '待确认')} / {account.get('region', '待确认')}",
            f"**阶段：** {opp.get('stage', '待确认')}",
            f"**评分：** {opp.get('score', '待确认')} / 100",
            f"**风险等级：** {opp.get('risk_level', '待确认')}",
            "",
            "## 核心需求",
            str(opp.get("core_need", "待确认")),
            "",
            "## 下一步行动",
        ]
        for a in data.get("next_actions", []):
            lines.append(f"- {a.get('action_title')}｜{a.get('priority')}｜{a.get('reason')}")
        lines.append("\n## 决策链")
        for node in data.get("decision_chain", []):
            name = node.get("person_name") or "待确认"
            lines.append(f"- {node.get('decision_role')}: {name}｜{node.get('status')}｜{node.get('next_step')}")
        lines.append("\n## 待确认信息")
        for item in opp.get("missing_information", []):
            lines.append(f"- {item}")
        files = self._collect_archived_files(data)
        if files:
            lines.append("\n## 原始材料")
            for item in files:
                link = item.get("relative_path") or item.get("archived_path") or item.get("original_path") or ""
                lines.append(f"- {item.get('display_name') or item.get('file_name') or '原始材料'}: {link}")
        return "\n".join(lines)
