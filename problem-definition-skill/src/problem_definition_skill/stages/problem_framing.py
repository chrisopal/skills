from __future__ import annotations
from typing import Any


def frame(normalized: dict[str, Any]) -> dict[str, Any]:
    text = normalized["all_text"]
    refs = normalized["source_ids"]

    surface = "客户希望推进相关业务或数字化建设，但具体范围、指标和实施边界仍需进一步澄清。"
    if "质检" in text or "质量" in text:
        surface = "客户希望推进质量检测自动化升级，并提升检测效率、数据准确性与追溯能力。"
    elif "仓储" in text or "库存" in text:
        surface = "客户希望改善仓储与库存管理，并提升作业效率、库存准确性和过程可追溯性。"
    elif "供应链" in text:
        surface = "客户希望提升供应链计划、协同与履约能力。"

    deep = "当前问题并非单一系统缺失，而是业务流程、数据标准、系统协同和组织责任尚未形成完整闭环。"
    reason = "从客户表达中的流程、数据、系统和管理诉求综合判断。"

    impacts: list[str] = []
    for keyword, impact in [
        ("漏检", "质量风险和客户投诉风险"),
        ("效率", "作业效率与交付周期"),
        ("追溯", "问题追溯与责任定位"),
        ("数据", "经营分析与持续改进能力"),
        ("MES", "跨系统协同与数据一致性"),
        ("库存", "库存准确性与资金占用"),
        ("交付", "客户履约与交付稳定性"),
    ]:
        if keyword in text and impact not in impacts:
            impacts.append(impact)
    if not impacts:
        impacts = ["项目范围失控", "方案与真实业务脱节", "投资价值难以衡量"]

    status = "confirmed" if refs else "inferred"
    return {
        "surface_problem": {"value": surface, "status": status, "reason": "基于客户材料还原和归纳。", "evidence_refs": refs},
        "deep_problem": {"value": deep, "status": "inferred", "reason": reason, "evidence_refs": refs},
        "business_impacts": impacts,
    }
