from __future__ import annotations
import re
from typing import Any
from .assessment import build_commercial_assessment
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
            "file_path": item.get("file_path") or item.get("path") or item.get("source_path"),
            "attachments": item.get("attachments", []),
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
    contacts_by_key: dict[str, dict[str, Any]] = {}
    phone = _pick_first([r"(1[3-9]\d[-\s]?\d{4}[-\s]?\d{4})"], text)
    email = _pick_first([r"([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})"], text)

    def add_contact(name: str, title: str, source_hint: str, phone_hint: str | None = None, email_hint: str | None = None) -> None:
        name = normalize_contact_name(name)
        title = title.strip()
        if not name or not title:
            return
        key = f"{name}|{title}"
        role = infer_contact_role(title)
        decision_role = infer_decision_role(title, name)
        is_owner = is_requirement_owner(title, decision_role)
        existing = contacts_by_key.get(key)
        contact = existing or {
            "id": new_id("ct"),
            "account_id": account_id,
            "name": name,
            "title": title,
            "department": infer_department(title),
            "role_in_opportunity": role,
            "responsibility_scope": infer_responsibility_scope(title, decision_role),
            "decision_role": decision_role,
            "is_requirement_owner": is_owner,
            "confirmation_status": "confirmed",
            "phone": None,
            "email": None,
            "attitude": "待确认",
            "source_refs": [],
        }
        if phone_hint or ("采购" in title and phone):
            contact["phone"] = phone_hint or phone
        if email_hint or ("采购" in title and email):
            contact["email"] = email_hint or email
        refs = contact.setdefault("source_refs", [])
        if source_hint not in refs:
            refs.append(source_hint)
        contacts_by_key[key] = contact

    # Speaker labels such as 王总（客户-生产负责人） or 李经理（客户-项目负责人）
    for m in re.finditer(r"([\u4e00-\u9fa5]{1,4}(?:总|经理|工|主任|部长)?)（客户[-－—]([^）]{2,20})）", text):
        add_contact(m.group(1), m.group(2), "speaker_label")

    # Business card / notes: 张伟 采购总监, 张伟｜采购总监
    for m in re.finditer(r"([\u4e00-\u9fa5]{2,4})[｜|，,\s]*(采购总监|生产负责人|项目负责人|需求负责人|业务负责人|信息化负责人|数字化负责人|技术负责人|项目经理|总经理|厂长|经理|部长|主任|工程师)", text):
        add_contact(m.group(1), m.group(2), "contact_text")

    # Short references such as 王总 / 李工 are useful only when no richer title was found.
    if not contacts_by_key:
        for m in re.finditer(r"(?<![\u4e00-\u9fa5])([\u4e00-\u9fa5]{1,2})(总|经理|工|主任|部长)(?![\u4e00-\u9fa5])", text):
            add_contact(m.group(1) + m.group(2), m.group(2), "short_reference")

    contacts = sorted(contacts_by_key.values(), key=contact_priority)
    return contacts[:8]


def normalize_contact_name(name: str) -> str:
    clean = name.strip()
    clean = re.sub(r"^(?:联系人|系人|客户|姓名|负责人)[:：]?", "", clean)
    return clean


def infer_contact_role(title: str) -> str:
    if any(k in title for k in ["需求", "生产", "业务"]):
        return "客户需求负责人"
    if "项目" in title:
        return "客户项目负责人"
    if "采购" in title:
        return "采购/商务影响人"
    if any(k in title for k in ["信息", "数字化", "IT"]):
        return "IT/集成影响人"
    if any(k in title for k in ["技术", "工程"]):
        return "技术影响人"
    if "总" in title or "厂长" in title:
        return "决策人/关键影响人"
    return "待确认"


def infer_decision_role(title: str, name: str = "") -> str:
    if any(k in title for k in ["需求", "生产", "业务"]):
        return "业务需求负责人"
    if "项目" in title:
        return "项目推进负责人"
    if "采购" in title:
        return "采购/商务负责人"
    if any(k in title for k in ["信息", "数字化", "IT"]):
        return "IT/系统集成负责人"
    if any(k in title for k in ["技术", "工程"]):
        return "技术评估负责人"
    if "总经理" in title or "厂长" in title or name.endswith("总"):
        return "最终决策人/关键拍板人"
    return "其他影响人"


def infer_department(title: str) -> str:
    if any(k in title for k in ["生产", "业务", "需求"]):
        return "业务/生产"
    if "项目" in title:
        return "项目组"
    if "采购" in title:
        return "采购"
    if any(k in title for k in ["信息", "数字化", "IT"]):
        return "IT/信息化"
    if any(k in title for k in ["技术", "工程"]):
        return "技术/工程"
    return "待确认"


def infer_responsibility_scope(title: str, decision_role: str) -> str:
    if decision_role == "业务需求负责人":
        return "定义业务痛点、检测场景、验收指标和现场使用要求"
    if decision_role == "项目推进负责人":
        return "组织方案评审、实施路径确认、跨部门协同和资料清单"
    if decision_role == "采购/商务负责人":
        return "预算区间、供应商比选、商务流程和合同推进"
    if decision_role == "IT/系统集成负责人":
        return "MES/数据接口、系统集成、安全和上线配合"
    if decision_role == "技术评估负责人":
        return "检测点位、节拍、设备选型和技术可行性"
    if decision_role == "最终决策人/关键拍板人":
        return "项目优先级、预算审批和最终决策"
    return f"{title}相关影响因素待确认"


def is_requirement_owner(title: str, decision_role: str) -> bool:
    return decision_role in {"业务需求负责人", "项目推进负责人"} or any(k in title for k in ["需求负责人", "生产负责人", "业务负责人", "项目负责人"])


def contact_priority(contact: dict[str, Any]) -> tuple[int, str]:
    role = contact.get("decision_role") or ""
    order = {
        "业务需求负责人": 0,
        "项目推进负责人": 1,
        "最终决策人/关键拍板人": 2,
        "技术评估负责人": 3,
        "IT/系统集成负责人": 4,
        "采购/商务负责人": 5,
    }
    return (order.get(role, 9), contact.get("name") or "")


def identify_decision_chain(contacts: list[dict[str, Any]], evidence_list: list[dict[str, Any]]) -> list[dict[str, Any]]:
    evidence_refs = [ev.get("evidence_id") for ev in evidence_list[:2] if ev.get("evidence_id")]
    role_specs = [
        ("业务需求负责人", "1", "high", "确认真实业务痛点、检测范围、验收口径"),
        ("项目推进负责人", "2", "high", "确认评审节奏、实施路径、资料清单和跨部门协调"),
        ("最终决策人/关键拍板人", "3", "high", "确认预算审批、立项优先级和最终决策人"),
        ("技术评估负责人", "4", "medium", "确认检测点位、节拍、设备/视觉方案可行性"),
        ("IT/系统集成负责人", "5", "medium", "确认MES接口、数据采集、系统集成和上线边界"),
        ("采购/商务负责人", "6", "medium", "确认预算区间、比选规则、合同与付款流程"),
    ]
    chain = []
    for role, level, influence, next_step in role_specs:
        matched = next((c for c in contacts if c.get("decision_role") == role), None)
        chain.append({
            "id": new_id("dc"),
            "contact_id": matched.get("id") if matched else None,
            "person_name": matched.get("name") if matched else None,
            "title": matched.get("title") if matched else None,
            "decision_role": role,
            "chain_level": level,
            "responsibility_scope": matched.get("responsibility_scope") if matched else infer_responsibility_scope("", role),
            "influence_level": influence,
            "status": "confirmed" if matched else "missing",
            "evidence_refs": evidence_refs if matched else [],
            "next_step": "保持对齐并纳入后续技术/方案交流" if matched else next_step,
        })
    return chain


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


def classify_score(score: int) -> tuple[str, str]:
    level = "A" if score >= 80 else "B" if score >= 65 else "C" if score >= 45 else "D"
    risk = "high" if score < 50 else "medium" if score < 75 else "low"
    return level, risk


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
    decision_chain = identify_decision_chain(contacts, evidence_list)
    competitors = extract_competitors(text)
    stage, stage_reason = infer_stage(text, core_need, budget_signal)
    baseline_score, baseline_win_probability, baseline_score_level, baseline_risk_level = score_opportunity(core_need, budget_signal, budget_amount, timeline, contacts, competitors, pain_points)
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
            "evidence_refs": [ev["evidence_id"] for ev in evidence_list[:2]]
        })
    if not has_requirement_owner or not has_confirmed_decision_maker:
        risks.append({
            "id": new_id("risk"), "opportunity_id": opportunity_id,
            "risk_type": "decision_chain", "risk_level": "high",
            "description": "客户需求负责人或最终拍板人尚未完全确认，可能影响方案评审和采购推进。",
            "mitigation": "补充客户组织关系和决策链，明确业务Owner、项目Owner、最终决策人、IT/技术和采购负责人。",
            "evidence_refs": [ev["evidence_id"] for ev in evidence_list[:2]]
        })

    next_actions = [
        {
            "id": new_id("act"), "opportunity_id": opportunity_id,
            "action_title": "完成商务确认评估",
            "action_detail": "请商务负责人围绕客户购买意向、客户关系、竞对定位、预算匹配、交易吸引力和交付风险回答关键确认问题。",
            "priority": "high", "owner": raw_input.get("owner") or "商务负责人",
            "deadline_suggestion": "2个工作日内", "status": "open",
            "reason": f"当前评估可信度为{commercial_assessment['confidence_level']}，仍有{commercial_assessment['unanswered_critical_count']}个关键问题待确认。"
        },
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
        f"商机评分{score}分，赢单概率约{int(round(win_probability * 100))}%，评估可信度{commercial_assessment['confidence_level']}。"
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
            "evidence_map": evidence_map
        },
        "missing_information": missing,
        "evidence_map": evidence_map
    }
