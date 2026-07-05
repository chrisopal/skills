from __future__ import annotations
import re
from typing import Any
from .utils import new_id, normalize_name

INDUSTRY_KEYWORDS = {
    "装备制造": ["装备", "设备", "非标", "产线", "机床", "制造"],
    "智能制造": ["MES", "MOM", "智能工厂", "数字化工厂", "产线"],
    "检测认证": ["实验室", "检测", "CMA", "LIMS", "报告"],
    "通信": ["运营商", "电信", "通信", "网络"],
}

SYSTEM_KEYWORDS = ["ERP", "MES", "WMS", "QMS", "EAM", "PLM", "APS", "LIMS", "SCADA", "IoT", "CRM"]
PAIN_KEYWORDS = ["效率低", "人工", "追溯", "数据", "孤岛", "质量", "交付", "成本", "协同", "不透明", "不准", "返工", "漏项"]
REGIONS = ["北京", "上海", "深圳", "广州", "苏州", "南京", "青岛", "杭州", "合肥", "武汉", "成都", "重庆", "江苏", "浙江", "山东", "安徽", "广东"]


def normalize_input(raw: dict[str, Any]) -> list[dict[str, Any]]:
    """Convert materials/plain text into evidence list.

    In production this should be replaced by a multimodal normalizer. This demo
    accepts already-parsed text materials and wraps them as Evidence objects.
    """
    if raw.get("evidence_list"):
        return raw["evidence_list"]

    evidence = []
    materials = raw.get("materials") or []
    if isinstance(materials, str):
        materials = [{"type": "text", "content": materials, "name": "plain_text"}]
    for idx, item in enumerate(materials, start=1):
        content = item.get("content") or item.get("text") or ""
        evidence.append({
            "evidence_id": item.get("evidence_id") or new_id("ev"),
            "source_type": item.get("type", "text"),
            "source_name": item.get("name") or item.get("source_name") or f"material_{idx}",
            "source_ref": item.get("source_ref"),
            "content": content,
            "extracted_fields": {},
            "confidence": float(item.get("confidence", 0.85)),
            "source_refs": item.get("source_refs", [{"location": "content", "quote": content[:120]}]),
            "requires_human_confirmation": bool(item.get("requires_human_confirmation", False)),
            "parse_warnings": item.get("parse_warnings", [])
        })
    return evidence


def _all_text(evidence_list: list[dict[str, Any]]) -> str:
    return "\n".join(ev.get("content", "") for ev in evidence_list)


def _pick_first(patterns: list[str], text: str) -> str | None:
    for pat in patterns:
        m = re.search(pat, text, flags=re.I)
        if m:
            return m.group(1).strip()
    return None


def extract_company(text: str, account_hint: str | None) -> str:
    if account_hint:
        return account_hint.strip()
    company = _pick_first([
        r"客户[:：]\s*([^，,。\n]+)",
        r"公司[:：]\s*([^，,。\n]+)",
        r"([\u4e00-\u9fa5A-Za-z0-9（）()]{2,30}(?:有限公司|股份有限公司|集团|工厂|材料厂|装备))",
    ], text)
    return company or "未知客户"


def infer_industry(text: str) -> str:
    for industry, kws in INDUSTRY_KEYWORDS.items():
        if any(kw.lower() in text.lower() for kw in kws):
            return industry
    return "待确认"


def extract_region(text: str) -> str:
    for r in REGIONS:
        if r in text:
            return r
    return "待确认"


def extract_contacts(text: str, account_id: str) -> list[dict[str, Any]]:
    contacts = []
    # Matches: 张伟 采购总监 / 张总 / 李工 / 王经理
    patterns = [
        r"([\u4e00-\u9fa5]{2,4})[，,\s]*(采购总监|信息化负责人|数字化负责人|项目经理|总经理|厂长|经理|部长|主任|工程师)",
        r"([\u4e00-\u9fa5]{1,2})(总|经理|工|主任|部长)",
    ]
    seen = set()
    for pat in patterns:
        for m in re.finditer(pat, text):
            name = m.group(1)
            title = m.group(2)
            key = name + title
            if key in seen:
                continue
            seen.add(key)
            contacts.append({
                "id": new_id("ct"),
                "account_id": account_id,
                "name": name,
                "title": title,
                "department": "待确认",
                "role_in_opportunity": infer_contact_role(title),
                "phone": None,
                "email": None,
                "attitude": "待确认",
                "source_refs": []
            })
    return contacts[:5]


def infer_contact_role(title: str) -> str:
    if "总" in title or "厂长" in title:
        return "决策人/关键影响人"
    if "采购" in title:
        return "采购影响人"
    if "信息" in title or "数字化" in title or "项目" in title:
        return "业务/IT推动人"
    if "工程" in title:
        return "技术影响人"
    return "待确认"


def extract_systems(text: str) -> list[str]:
    found = []
    for s in SYSTEM_KEYWORDS:
        if re.search(rf"\b{s}\b", text, flags=re.I) or s in text:
            found.append(s.upper() if s.lower() != "iot" else "IoT")
    return sorted(set(found))


def extract_core_need(text: str) -> str:
    candidates = [
        "质检自动化升级", "智能工厂", "数字化转型规划", "仓储管理", "供应链管理", "能源管理", "售后服务助手", "投标助手", "LIMS", "MES", "MOM", "数据中台", "AI应用"
    ]
    for c in candidates:
        if c in text:
            return c
    m = _pick_first([r"希望([^。\n]{4,50})", r"需要([^。\n]{4,50})", r"计划([^。\n]{4,50})"], text)
    return m or "客户需求待进一步澄清"


def extract_pain_points(text: str) -> list[str]:
    pains = []
    sentences = re.split(r"[。；;\n]", text)
    for s in sentences:
        if any(kw in s for kw in PAIN_KEYWORDS):
            val = s.strip()
            if val and val not in pains:
                pains.append(val[:80])
    if not pains:
        pains = ["业务痛点待进一步确认"]
    return pains[:6]


def extract_budget_signal(text: str) -> tuple[str, str | None]:
    budget_amount = None
    amount_match = re.search(r"(\d+(?:\.\d+)?\s*(?:万|万元|百万|千万|亿|元))", text)
    if amount_match and "预算" in text[max(0, amount_match.start()-20):amount_match.end()+20]:
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


def analyze(raw_input: dict[str, Any]) -> dict[str, Any]:
    evidence_list = normalize_input(raw_input)
    text = _all_text(evidence_list)
    account_id = new_id("acc")
    company_name = extract_company(text, raw_input.get("account_hint"))
    industry = infer_industry(text)
    region = extract_region(text)
    current_systems = extract_systems(text)
    core_need = extract_core_need(text)
    pain_points = extract_pain_points(text)
    budget_signal, budget_amount = extract_budget_signal(text)
    timeline = extract_timeline(text)
    contacts = extract_contacts(text, account_id)
    competitors = extract_competitors(text)
    stage, stage_reason = infer_stage(text, core_need, budget_signal)
    score, win_probability, score_level, risk_level = score_opportunity(core_need, budget_signal, budget_amount, timeline, contacts, competitors, pain_points)
    opportunity_id = new_id("opp")

    missing = []
    if budget_amount is None:
        missing.append("预算金额或预算区间未明确")
    if not contacts:
        missing.append("关键联系人和决策链未明确")
    if timeline == "时间节点未明确":
        missing.append("项目时间节点未明确")
    if core_need == "客户需求待进一步澄清":
        missing.append("核心需求和建设范围未明确")
    if not competitors:
        missing.append("竞争对手和客户已接触供应商情况未明确")

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
            "evidence_refs": [ev["evidence_id"] for ev in evidence_list[:2]]
        })
    if not contacts:
        risks.append({
            "id": new_id("risk"), "opportunity_id": opportunity_id,
            "risk_type": "decision_chain", "risk_level": "high",
            "description": "缺少关键联系人、最终决策人和影响人信息。",
            "mitigation": "补充客户组织关系和决策链，明确业务Owner、IT Owner和采购负责人。",
            "evidence_refs": []
        })

    next_actions = [
        {
            "id": new_id("act"), "opportunity_id": opportunity_id,
            "action_title": "补充需求澄清清单",
            "action_detail": "围绕建设范围、现有系统、数据来源、预算、时间节点和验收指标补充问题清单。",
            "priority": "high", "owner": raw_input.get("owner") or "销售/售前负责人",
            "deadline_suggestion": "3个工作日内", "status": "open",
            "reason": "当前商机仍存在关键缺失信息，需先澄清后再输出正式方案。"
        },
        {
            "id": new_id("act"), "opportunity_id": opportunity_id,
            "action_title": "安排技术/方案交流",
            "action_detail": "基于已识别需求准备一页式方案和问题清单，与客户进行技术交流。",
            "priority": "medium", "owner": "售前顾问",
            "deadline_suggestion": "1周内", "status": "open",
            "reason": f"当前阶段判断为{stage}，需要通过方案交流推进商机成熟。"
        }
    ]

    account = {
        "id": account_id,
        "company_name": company_name,
        "normalized_name": normalize_name(company_name),
        "industry": industry,
        "region": region,
        "company_size": "待确认",
        "business_summary": f"根据现有资料，客户属于{industry}方向，核心关注：{core_need}。",
        "current_systems": current_systems,
        "key_pain_points": pain_points,
        "source_confidence": round(sum(ev.get("confidence", 0.8) for ev in evidence_list) / max(len(evidence_list), 1), 2)
    }

    opportunity = {
        "id": opportunity_id,
        "account_id": account_id,
        "name": f"{company_name}-{core_need}",
        "stage": stage,
        "stage_status": "inferred",
        "stage_reason": stage_reason,
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
        "status": "active"
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
            "confidence": evidence_list[0].get("confidence", 0.8)
        })
        evidence_map.append({
            "id": new_id("map"),
            "opportunity_id": opportunity_id,
            "evidence_id": evidence_list[0]["evidence_id"],
            "field_name": "stage",
            "field_value": stage,
            "status": "inferred",
            "confidence": 0.76
        })

    human_summary = (
        f"商机摘要：{company_name}当前识别到核心需求为“{core_need}”，阶段判断为“{stage}”。"
        f"商机评分{score}分，风险等级{risk_level}。"
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
            "evidence": evidence_list,
            "missing_information": missing,
            "evidence_map": evidence_map
        },
        "missing_information": missing,
        "evidence_map": evidence_map
    }
