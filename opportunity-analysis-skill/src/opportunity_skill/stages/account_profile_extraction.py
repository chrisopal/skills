from __future__ import annotations

import re
from typing import Any

from ..utils import new_id, normalize_name

INDUSTRY_KEYWORDS = {
    "装备制造": ["装备", "设备", "非标", "产线", "机床", "制造"],
    "智能制造": ["MES", "MOM", "智能工厂", "数字化工厂", "产线"],
    "检测认证": ["实验室", "检测", "CMA", "LIMS", "报告"],
    "通信": ["运营商", "电信", "通信", "网络"],
}

SYSTEM_KEYWORDS = ["ERP", "MES", "WMS", "QMS", "EAM", "PLM", "APS", "LIMS", "SCADA", "IoT", "CRM"]
PAIN_KEYWORDS = ["效率低", "人工", "追溯", "数据", "孤岛", "质量", "交付", "成本", "协同", "不透明", "不准", "返工", "漏项"]
REGIONS = ["北京", "上海", "深圳", "广州", "苏州", "南京", "青岛", "杭州", "合肥", "武汉", "成都", "重庆", "江苏", "浙江", "山东", "安徽", "广东"]


def pick_first(patterns: list[str], text: str) -> str | None:
    for pat in patterns:
        m = re.search(pat, text, flags=re.I)
        if m:
            return m.group(1).strip()
    return None


def extract_company(text: str, account_hint: str | None) -> str:
    if account_hint:
        return account_hint.strip()
    company = pick_first([
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


def extract_systems(text: str) -> list[str]:
    found = []
    for s in SYSTEM_KEYWORDS:
        if re.search(rf"\b{s}\b", text, flags=re.I) or s in text:
            found.append(s.upper() if s.lower() != "iot" else "IoT")
    return sorted(set(found))


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


def extract_contacts(text: str, account_id: str) -> list[dict[str, Any]]:
    contacts_by_key: dict[str, dict[str, Any]] = {}
    phone = pick_first([r"(1[3-9]\d[-\s]?\d{4}[-\s]?\d{4})"], text)
    email = pick_first([r"([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})"], text)

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

    for m in re.finditer(r"([\u4e00-\u9fa5]{1,4}(?:总|经理|工|主任|部长)?)（客户[-－—]([^）]{2,20})）", text):
        add_contact(m.group(1), m.group(2), "speaker_label")

    for m in re.finditer(r"([\u4e00-\u9fa5]{2,4})[｜|，,\s]*(采购总监|生产负责人|项目负责人|需求负责人|业务负责人|信息化负责人|数字化负责人|技术负责人|项目经理|总经理|厂长|经理|部长|主任|工程师)", text):
        add_contact(m.group(1), m.group(2), "contact_text")

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


def extract_account_profile(text: str, raw_input: dict[str, Any], evidence_list: list[dict[str, Any]]) -> dict[str, Any]:
    account_id = new_id("acc")
    company_name = extract_company(text, raw_input.get("account_hint"))
    industry = infer_industry(text)
    current_systems = extract_systems(text)
    pain_points = extract_pain_points(text)
    contacts = extract_contacts(text, account_id)
    decision_chain = identify_decision_chain(contacts, evidence_list)

    return {
        "account_id": account_id,
        "company_name": company_name,
        "normalized_name": normalize_name(company_name),
        "industry": industry,
        "region": extract_region(text),
        "current_systems": current_systems,
        "pain_points": pain_points,
        "contacts": contacts,
        "decision_chain": decision_chain,
        "source_confidence": round(sum(ev.get("confidence", 0.8) for ev in evidence_list) / max(len(evidence_list), 1), 2),
    }
