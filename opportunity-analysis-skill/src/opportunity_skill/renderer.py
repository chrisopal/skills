from __future__ import annotations
import html
import math
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
        assessment = data.get("commercial_assessment", {}) or {}
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
            "assessment.summary": esc(self._assessment_summary(data.get("commercial_assessment", {}))),
            "assessment.win_likelihood_score": esc(data.get("commercial_assessment", {}).get("win_likelihood_score")),
            "assessment.deal_attractiveness_score": esc(data.get("commercial_assessment", {}).get("deal_attractiveness_score")),
            "assessment.delivery_confidence_score": esc(data.get("commercial_assessment", {}).get("delivery_confidence_score")),
            "assessment.unanswered_critical_count": esc(data.get("commercial_assessment", {}).get("unanswered_critical_count")),
            "assessment_radar_chart": self._assessment_radar_chart(data.get("commercial_assessment", {})),
            "assessment_dimension_bars": self._assessment_dimension_bars(data.get("commercial_assessment", {}).get("dimensions", [])),
            "assessment_dimension_rows": self._assessment_dimension_rows(data.get("commercial_assessment", {}).get("dimensions", [])),
            "sales_questions.count": esc(len(data.get("sales_confirmation_questions", []) or data.get("commercial_assessment", {}).get("questions", []))),
            "sales_question_items": self._sales_question_items(data.get("sales_confirmation_questions", []) or data.get("commercial_assessment", {}).get("questions", [])),
            "sales_confirmation_cards": self._sales_confirmation_cards(data.get("commercial_assessment", {}).get("dimensions", [])),
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
        total_score = 0
        scored_count = 0
        high_risk_count = 0
        missing_total = 0
        for opp in opportunities:
            if opp.get("score") is not None:
                total_score += int(opp.get("score") or 0)
                scored_count += 1
            if opp.get("risk_level") == "high":
                high_risk_count += 1
            missing_total += len(opp.get("missing_information") or [])
        for stage in stages:
            cards = []
            stage_items = [opp for opp in opportunities if opp.get("stage") == stage]
            stage_items = sorted(stage_items, key=lambda x: (x.get("score") or 0, x.get("updated_at") or ""), reverse=True)
            stage_score = round(sum((opp.get("score") or 0) for opp in stage_items) / max(len(stage_items), 1)) if stage_items else "暂无"
            for opp in stage_items:
                score = int(opp.get("score") or 0)
                win_percent = int(round((opp.get("win_probability") or 0) * 100))
                risk = self._risk_class(opp.get("risk_level"))
                missing = opp.get("missing_information") or []
                requirements = opp.get("requirements") or []
                focus = missing[0] if missing else (requirements[0] if requirements else "下一步待根据客户反馈确认")
                budget = opp.get("budget_amount") or opp.get("budget_signal") or "预算待确认"
                cards.append(
                    "<article class='kanban-card'>"
                    "<div class='kanban-card-topline'>"
                    f"<span class='ql-tag green'>{esc(opp.get('score_level'))}级</span>"
                    f"<span class='ql-tag risk-{risk}'>风险 {esc(self._risk_label(opp.get('risk_level')))}</span>"
                    "</div>"
                    f"<h3>{esc(opp.get('name'))}</h3>"
                    f"<p class='kanban-account'>{esc(opp.get('company_name'))} · {esc(opp.get('industry'))} · {esc(opp.get('region'))}</p>"
                    "<div class='kanban-score-row'>"
                    "<div>"
                    "<span>评分</span>"
                    f"<strong>{esc(score)}</strong>"
                    "</div>"
                    "<div>"
                    "<span>赢单</span>"
                    f"<strong>{esc(win_percent)}%</strong>"
                    "</div>"
                    "</div>"
                    "<div class='kanban-score-track' aria-hidden='true'>"
                    f"<span style='width:{max(0, min(100, score))}%'></span>"
                    "</div>"
                    "<dl class='kanban-meta'>"
                    f"<div><dt>需求</dt><dd>{esc(compact(opp.get('core_need'), 34))}</dd></div>"
                    f"<div><dt>时间</dt><dd>{esc(opp.get('expected_timeline'))}</dd></div>"
                    f"<div><dt>预算</dt><dd>{esc(compact(budget, 34))}</dd></div>"
                    "</dl>"
                    "<div class='kanban-focus'>"
                    "<span>优先动作</span>"
                    f"<strong>{esc(compact(focus, 58))}</strong>"
                    "</div>"
                    "</article>"
                )
            empty = "<div class='kanban-empty'>暂无商机</div>"
            columns.append(
                "<section class='kanban-col'>"
                "<div class='kanban-col-head'>"
                f"<div><h2>{esc(stage)}</h2><span>{esc(len(stage_items))} 个商机</span></div>"
                f"<strong>{esc(stage_score)}</strong>"
                "</div>"
                f"<div class='kanban-card-list'>{''.join(cards) or empty}</div>"
                "</section>"
            )
        avg_score = round(total_score / scored_count) if scored_count else "暂无"
        query_summary = self._query_summary(data.get("query", {}))
        return replace_tokens(tpl, {
            "kanban_columns": "".join(columns),
            "query.summary": esc(query_summary),
            "summary.count": esc(len(opportunities)),
            "summary.avg_score": esc(avg_score),
            "summary.high_risk": esc(high_risk_count),
            "summary.missing": esc(missing_total),
        })

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

    def _action_items(self, actions: list[dict[str, Any]]) -> str:
        if not actions:
            return "<li>暂无</li>"
        out = []
        for a in actions:
            out.append(
                "<li>"
                f"<strong>{esc(a.get('action_title'))}</strong>"
                f"<span class='ql-tag orange'>{esc(self._priority_label(a.get('priority')))}</span><br/>"
                f"<span>{esc(self._localized_level_text(a.get('reason')))}</span>"
                "</li>"
            )
        return "".join(out)

    def _priority_label(self, priority: Any) -> str:
        mapping = {"high": "高", "medium": "中", "low": "低"}
        return mapping.get(str(priority), esc(priority))

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
                f"<td><span class='ql-tag {self._influence_class(node.get('influence_level'))}'>{esc(self._influence_label(node.get('influence_level')))}</span></td>"
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
            "deal_attractiveness": "成交意向",
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
        center = (180.0, 180.0)
        radius = 105.0
        label_radius = 150.0
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
        labels = []
        for i, item in enumerate(items):
            x, y = point(i, label_radius)
            anchor = "middle"
            if x < center[0] - 18:
                anchor = "end"
            elif x > center[0] + 18:
                anchor = "start"
            score = int(item.get("score") or 0)
            label = compact(item.get("label"), 9)
            labels.append(f"<text x='{x:.1f}' y='{y:.1f}' text-anchor='{anchor}'>{esc(label)} {esc(score)}</text>")
        return (
            "<section class='ql-radar-panel'>"
            "<div class='ql-radar-panel-head'>"
            f"<strong>{esc(self._category_label(category))}</strong>"
            f"<span>概况 {esc(category_score)}分</span>"
            "</div>"
            f"<svg class='ql-radar-chart' viewBox='0 0 360 360' role='img' aria-label='{esc(self._category_label(category))}维度评分雷达图'>"
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

    def _sales_confirmation_cards(self, dimensions: list[dict[str, Any]]) -> str:
        needs = [
            d for d in dimensions
            if d.get("evidence_status") == "needs_sales_confirmation"
        ]
        if not needs:
            return "<div class='ql-confirmation-empty'>暂无未确认维度</div>"
        priority = {"P0": 0, "P1": 1, "P2": 2}
        cards = []
        for item in sorted(needs, key=lambda x: (priority.get(x.get("priority"), 9), 0 if x.get("critical") else 1, x.get("category") or "", x.get("dimension_id") or "")):
            rating = item.get("rating") or "unknown"
            critical = "关键" if item.get("critical") else "补充"
            cards.append(
                "<article class='ql-confirmation-card'>"
                "<div class='ql-confirmation-card-head'>"
                f"<strong>{esc(item.get('label'))}</strong>"
                f"<span class='ql-tag rating-{esc(rating)}'>{esc(self._rating_label(rating))}</span>"
                "</div>"
                "<div class='ql-confirmation-meta'>"
                f"<span>{esc(item.get('priority'))} · {esc(critical)} · {esc(self._category_label(item.get('category')))}</span>"
                f"<span>{esc(item.get('score'))}分</span>"
                "</div>"
                f"<p>{esc(item.get('question'))}</p>"
                "<div class='ql-confirmation-answer'>回答格式：<code>dimension_id</code> "
                f"<code>{esc(item.get('dimension_id'))}</code> + <code>rating</code> 强/中/弱/未知 + <code>answer_text</code></div>"
                "</article>"
            )
        return "".join(cards)

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
                f"<td>{esc(compact(item.get('rationale'), 120))}</td>"
                f"<td>{esc(item.get('question'))}</td>"
                "</tr>"
            )
        return "".join(rows)

    def _sales_question_items(self, questions: list[dict[str, Any]]) -> str:
        if not questions:
            return "<li class='ql-empty'>暂无关键问题</li>"
        out = []
        for q in questions:
            out.append(
                "<li>"
                f"<div><strong>{esc(q.get('question'))}</strong></div>"
                f"<span class='ql-tag orange'>{esc(q.get('priority'))}</span>"
                f"<span class='ql-muted-text'>{esc(q.get('label'))}｜{esc(q.get('impact'))}</span>"
                "</li>"
            )
        return "".join(out)

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
            f"**风险等级：** {self._risk_label(opp.get('risk_level'))}",
            "",
            "## 核心需求",
            str(opp.get("core_need", "待确认")),
            "",
            "## 下一步行动",
        ]
        for a in data.get("next_actions", []):
            lines.append(f"- {a.get('action_title')}｜{self._priority_label(a.get('priority'))}｜{self._localized_level_text(a.get('reason'))}")
        lines.append("\n## 决策链")
        for node in data.get("decision_chain", []):
            name = node.get("person_name") or "待确认"
            lines.append(f"- {node.get('decision_role')}: {name}｜{self._status_label(node.get('status'))}｜{self._localized_level_text(node.get('next_step'))}")
        assessment = data.get("commercial_assessment", {}) or {}
        if assessment:
            lines.append("\n## 商务确认评估")
            lines.append(f"- 赢单可能性：{assessment.get('win_likelihood_score')}")
            lines.append(f"- 成交意向：{assessment.get('deal_attractiveness_score')}")
            lines.append(f"- 交付信心：{assessment.get('delivery_confidence_score')}")
            lines.append(f"- 评估可信度：{self._confidence_label(assessment.get('confidence_level'))}")
            lines.append("\n## 待商务确认问题")
            for q in assessment.get("questions", []):
                lines.append(f"- [{q.get('priority')}] {q.get('question')}")
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

    def _status_label(self, status: Any) -> str:
        mapping = {"confirmed": "已确认", "missing": "待补充", "open": "待处理", "active": "进行中"}
        return mapping.get(str(status), esc(status))
