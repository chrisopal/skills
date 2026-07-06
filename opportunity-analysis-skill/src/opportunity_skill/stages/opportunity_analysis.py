from __future__ import annotations

import re
from typing import Any

from ..assessment import build_commercial_assessment
from ..stage_management import infer_opportunity_stage
from ..utils import new_id
from .account_profile_extraction import pick_first


def extract_core_need(text: str) -> str:
    candidates = [
        "质检自动化升级", "智能工厂", "数字化转型规划", "仓储管理", "供应链管理", "能源管理", "售后服务助手", "投标助手", "LIMS", "MES", "MOM", "数据中台", "AI应用"
    ]
    for c in candidates:
        if c in text:
            return c
    m = pick_first([r"希望([^。\n]{4,50})", r"需要([^。\n]{4,50})", r"计划([^。\n]{4,50})"], text)
    return m or "客户需求待进一步澄清"


def extract_budget_signal(text: str) -> tuple[str, str | None]:
    budget_amount = None
    amount_match = re.search(r"(\d+(?:\.\d+)?\s*(?:万|万元|百万|千万|亿|元))", text)
    if amount_match and "预算" in text[max(0, amount_match.start() - 20):amount_match.end() + 20]:
        budget_amount = amount_match.group(1)
    if "预算" in text or "技改" in text or "立项" in text:
        return "存在预算/立项信号", budget_amount
    return "预算信息未明确", None


def extract_timeline(text: str) -> str:
    patterns = [r"(Q[1-4])", r"(\d{1,2}月(?:底|前|份)?)", r"(上半年|下半年|年底|年内|春节前|国庆前)", r"(\d{4}年\d{1,2}月)"]
    for p in patterns:
        m = re.search(p, text, flags=re.I)
        if m:
            return m.group(1)
    return "时间节点未明确"


def infer_stage(text: str, core_need: str, budget_signal: str) -> tuple[str, str]:
    if any(k in text for k in ["中标", "已签", "合同已签", "赢单"]):
        return "赢单", "原文出现中标/签约信号"
    if any(k in text for k in ["投标", "招标", "报价", "比选"]):
        return "投标/报价", "原文出现投标/报价/比选信号"
    if any(k in text for k in ["方案", "技术交流", "汇报", "演示"]):
        return "方案交流", "原文出现方案交流/技术交流信号"
    if core_need != "客户需求待进一步澄清":
        return "需求确认", "已识别明确需求方向，但采购和决策链仍需确认"
    if budget_signal != "预算信息未明确":
        return "初步沟通", "有预算信号但需求不完整"
    return "线索", "信息较少，仅可作为线索"


def extract_competitors(text: str) -> list[str]:
    comps = []
    for pat in [r"竞争对手[:：]\s*([^。\n]+)", r"对比([^。\n]{2,30})", r"还有([^。\n]{2,30})参与"]:
        m = re.search(pat, text)
        if m:
            comps.extend(re.split(r"[,，、/ ]+", m.group(1)))
    return [c for c in comps if c][:5]


def score_opportunity(core_need: str, budget_signal: str, budget_amount: str | None, timeline: str, contacts: list, competitors: list, pains: list) -> tuple[int, float, str, str]:
    score = 0
    score += 18 if core_need != "客户需求待进一步澄清" else 6
    score += 15 if budget_amount else (9 if budget_signal != "预算信息未明确" else 3)
    score += 12 if contacts else 4
    score += 8 if timeline != "时间节点未明确" else 3
    score += 6 if competitors else 8
    score += 13 if core_need != "客户需求待进一步澄清" else 5
    score += 8
    score += 4 if len(pains) <= 3 else 2
    score = max(0, min(100, score))
    prob = round(score / 100 * 0.85, 2)
    level = "A" if score >= 80 else "B" if score >= 65 else "C" if score >= 45 else "D"
    risk = "high" if score < 50 else "medium" if score < 75 else "low"
    return score, prob, level, risk


def classify_score(score: int) -> tuple[str, str]:
    level = "A" if score >= 80 else "B" if score >= 65 else "C" if score >= 45 else "D"
    risk = "high" if score < 50 else "medium" if score < 75 else "low"
    return level, risk


def label_confidence(level: Any) -> str:
    mapping = {"high": "高", "medium": "中", "low": "低"}
    return mapping.get(str(level), "待确认")


def analyze_opportunity(
    raw_input: dict[str, Any],
    evidence_list: list[dict[str, Any]],
    text: str,
    account_profile: dict[str, Any],
) -> dict[str, Any]:
    account_id = account_profile["account_id"]
    company_name = account_profile["company_name"]
    current_systems = account_profile["current_systems"]
    pain_points = account_profile["pain_points"]
    contacts = account_profile["contacts"]
    decision_chain = account_profile["decision_chain"]

    core_need = extract_core_need(text)
    budget_signal, budget_amount = extract_budget_signal(text)
    timeline = extract_timeline(text)
    competitors = extract_competitors(text)
    stage_result = infer_opportunity_stage({
        "text": text,
        "core_need": core_need,
        "budget_signal": budget_signal,
        "budget_amount": budget_amount,
        "timeline": timeline,
        "contacts": contacts,
        "decision_chain": decision_chain,
    })
    stage = stage_result["stage"]
    stage_reason = stage_result["stage_reason"]
    baseline_score, baseline_win_probability, _baseline_score_level, _baseline_risk_level = score_opportunity(
        core_need, budget_signal, budget_amount, timeline, contacts, competitors, pain_points
    )
    commercial_assessment = build_commercial_assessment({
        "text": text,
        "stage": stage,
        "core_need": core_need,
        "budget_signal": budget_signal,
        "budget_amount": budget_amount,
        "timeline": timeline,
        "contacts": contacts,
        "decision_chain": decision_chain,
        "competitors": competitors,
        "current_systems": current_systems,
        "pain_points": pain_points,
        "evidence_list": evidence_list,
        "baseline_score": baseline_score,
        "baseline_win_probability": baseline_win_probability,
        "sales_confirmation_answers": raw_input.get("sales_confirmation_answers", []),
    })
    score = commercial_assessment["overall_opportunity_score"]
    win_probability = commercial_assessment["win_probability"]
    confidence_label = label_confidence(commercial_assessment.get("confidence_level"))
    score_level, risk_level = classify_score(score)
    opportunity_id = new_id("opp")

    has_requirement_owner = any(c.get("is_requirement_owner") for c in contacts)
    has_confirmed_decision_maker = any(n.get("decision_role") == "最终决策人/关键拍板人" and n.get("status") == "confirmed" for n in decision_chain)
    missing = []
    if budget_amount is None:
        missing.append("预算金额或预算区间未明确")
    if not has_requirement_owner:
        missing.append("客户需求负责人未明确")
    if not has_confirmed_decision_maker:
        missing.append("最终决策人或关键拍板人未明确")
    if timeline == "时间节点未明确":
        missing.append("项目时间节点未明确")
    if core_need == "客户需求待进一步澄清":
        missing.append("核心需求和建设范围未明确")
    if not competitors:
        missing.append("竞争对手和客户已接触供应商情况未明确")
    if commercial_assessment["unanswered_critical_count"]:
        missing.append(f"商务确认评估仍有{commercial_assessment['unanswered_critical_count']}个关键问题待回答")

    requirements = []
    if core_need != "客户需求待进一步澄清":
        requirements.append(core_need)
    for sys in current_systems:
        requirements.append(f"需考虑与现有{sys}系统集成")

    risks = []
    if budget_amount is None:
        risks.append({
            "id": new_id("risk"), "opportunity_id": opportunity_id,
            "risk_type": "budget", "risk_level": "medium",
            "description": "当前仅识别到预算信号，缺少明确预算金额或区间。",
            "mitigation": "下一次沟通需向采购/项目负责人确认预算范围和审批路径。",
            "evidence_refs": [ev["evidence_id"] for ev in evidence_list[:2]],
        })
    if not has_requirement_owner or not has_confirmed_decision_maker:
        risks.append({
            "id": new_id("risk"), "opportunity_id": opportunity_id,
            "risk_type": "decision_chain", "risk_level": "high",
            "description": "客户需求负责人或最终拍板人尚未完全确认，可能影响方案评审和采购推进。",
            "mitigation": "补充客户组织关系和决策链，明确业务Owner、项目Owner、最终决策人、IT/技术和采购负责人。",
            "evidence_refs": [ev["evidence_id"] for ev in evidence_list[:2]],
        })

    next_actions = [
        {
            "id": new_id("act"), "opportunity_id": opportunity_id,
            "action_title": "完成商务确认评估",
            "action_detail": "请商务负责人围绕客户购买意向、客户关系、竞对定位、预算匹配、交易吸引力和交付风险回答关键确认问题。",
            "priority": "high", "owner": raw_input.get("owner") or "商务负责人",
            "deadline_suggestion": "2个工作日内", "status": "open",
            "reason": f"当前评估可信度为{confidence_label}，仍有{commercial_assessment['unanswered_critical_count']}个关键问题待确认。",
        },
        {
            "id": new_id("act"), "opportunity_id": opportunity_id,
            "action_title": "补充需求澄清清单",
            "action_detail": "围绕建设范围、现有系统、数据来源、预算、时间节点和验收指标补充问题清单。",
            "priority": "high", "owner": raw_input.get("owner") or "销售/售前负责人",
            "deadline_suggestion": "3个工作日内", "status": "open",
            "reason": "当前商机仍存在关键缺失信息，需先澄清后再输出正式方案。",
        },
        {
            "id": new_id("act"), "opportunity_id": opportunity_id,
            "action_title": "安排技术/方案交流",
            "action_detail": "基于已识别需求准备一页式方案和问题清单，与客户进行技术交流。",
            "priority": "medium", "owner": "售前顾问",
            "deadline_suggestion": "1周内", "status": "open",
            "reason": f"当前阶段判断为{stage}，需要通过方案交流推进商机成熟。",
        },
    ]

    account = {
        "id": account_id,
        "company_name": company_name,
        "normalized_name": account_profile["normalized_name"],
        "industry": account_profile["industry"],
        "region": account_profile["region"],
        "company_size": "待确认",
        "business_summary": f"根据现有资料，客户属于{account_profile['industry']}方向，核心关注：{core_need}。",
        "current_systems": current_systems,
        "key_pain_points": pain_points,
        "source_confidence": account_profile["source_confidence"],
    }

    opportunity = {
        "id": opportunity_id,
        "account_id": account_id,
        "name": f"{company_name}-{core_need}",
        "stage": stage,
        "stage_status": "inferred",
        "stage_id": stage_result["stage_id"],
        "stage_reason": stage_reason,
        "stage_confidence": stage_result["stage_confidence"],
        "stage_signal_hits": stage_result["stage_signal_hits"],
        "opportunity_confirmed": stage_result["opportunity_confirmed"],
        "core_need": core_need,
        "budget_signal": budget_signal,
        "budget_amount": budget_amount,
        "expected_timeline": timeline,
        "win_probability": win_probability,
        "score": score,
        "score_level": score_level,
        "risk_level": risk_level,
        "competitors": competitors,
        "pain_points": pain_points,
        "requirements": requirements,
        "missing_information": missing,
        "status": "active",
    }

    evidence_map = []
    if evidence_list:
        evidence_map.append({
            "id": new_id("map"),
            "opportunity_id": opportunity_id,
            "evidence_id": evidence_list[0]["evidence_id"],
            "field_name": "core_need",
            "field_value": core_need,
            "status": "inferred" if core_need == "客户需求待进一步澄清" else "confirmed",
            "confidence": evidence_list[0].get("confidence", 0.8),
        })
        evidence_map.append({
            "id": new_id("map"),
            "opportunity_id": opportunity_id,
            "evidence_id": evidence_list[0]["evidence_id"],
            "field_name": "stage",
            "field_value": stage,
            "status": "inferred",
            "confidence": 0.76,
        })

    human_summary = (
        f"商机摘要：{company_name}当前识别到核心需求为“{core_need}”，阶段判断为“{stage}”。"
        f"商机评分{score}分，赢单概率约{int(round(win_probability * 100))}%，评估可信度{confidence_label}。"
        f"主要待确认信息包括：{'；'.join(missing) if missing else '暂无关键缺失信息'}。"
    )

    return {
        "human_summary": human_summary,
        "structured_data": {
            "account": account,
            "contacts": contacts,
            "opportunity": opportunity,
            "risks": risks,
            "next_actions": next_actions,
            "decision_chain": decision_chain,
            "commercial_assessment": commercial_assessment,
            "sales_confirmation_questions": commercial_assessment.get("questions", []),
            "sales_confirmation_answers": commercial_assessment.get("answers", []),
            "evidence": evidence_list,
            "missing_information": missing,
            "evidence_map": evidence_map,
        },
        "missing_information": missing,
        "evidence_map": evidence_map,
    }
