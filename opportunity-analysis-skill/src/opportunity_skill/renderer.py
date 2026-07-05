from __future__ import annotations
import html
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
        return "<li>暂无</li>"
    return "".join(f"<li>{esc(x)}</li>" for x in items)


def table_rows(rows: list[dict[str, Any]], fields: list[str]) -> str:
    if not rows:
        return f"<tr><td colspan='{len(fields)}'>暂无</td></tr>"
    out = []
    for row in rows:
        out.append("<tr>" + "".join(f"<td>{esc(row.get(f))}</td>" for f in fields) + "</tr>")
    return "".join(out)


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
        full_html = f"<style>{self.css}</style>\n{html_body}"
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
            "opportunity.risk_level": esc(opp.get("risk_level")),
            "opportunity.win_probability_percent": esc(opp.get("win_probability_percent")),
            "opportunity.core_need": esc(opp.get("core_need")),
            "opportunity.budget_signal": esc(opp.get("budget_signal")),
            "opportunity.expected_timeline": esc(opp.get("expected_timeline")),
            "pain_points_list": li(opp.get("pain_points", [])),
            "next_actions_list": self._action_items(data.get("next_actions", [])),
            "missing_information_list": li(opp.get("missing_information", []) or data.get("missing_information", [])),
        }
        return replace_tokens(tpl, mapping)

    def _render_opportunity_detail(self, data: dict[str, Any]) -> str:
        card = self._render_opportunity_card(data)
        tpl = (self.template_dir / "opportunity_detail.html").read_text(encoding="utf-8")
        mapping = {
            "opportunity_card": card,
            "contacts_rows": table_rows(data.get("contacts", []), ["name", "title", "department", "role_in_opportunity", "attitude"]),
            "risks_rows": table_rows(data.get("risks", []), ["risk_level", "risk_type", "description", "mitigation"]),
            "evidence_list": li([f"{ev.get('source_name')}: {ev.get('content')}" for ev in data.get("evidence", [])]),
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
        return replace_tokens(tpl, {"risks_rows": table_rows(data.get("risks", []), ["risk_level", "risk_type", "description", "mitigation"])})

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
            out.append(f"<li><strong>{esc(a.get('action_title'))}</strong>｜{esc(a.get('priority'))}<br/><span>{esc(a.get('reason'))}</span></li>")
        return "".join(out)

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
        lines.append("\n## 待确认信息")
        for item in opp.get("missing_information", []):
            lines.append(f"- {item}")
        return "\n".join(lines)
