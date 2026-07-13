from __future__ import annotations
import re
from typing import Any


def define(normalized: dict[str, Any], framed: dict[str, Any]) -> dict[str, Any]:
    text = normalized["all_text"]
    refs = normalized["source_ids"]
    decision = "管理层需要决定优先建设范围、试点对象、投入边界及分阶段实施路径。"

    missing: list[str] = []
    checks = [
        ("预算", "预算金额或预算区间"),
        ("决策", "最终决策人及决策流程"),
        ("节拍", "目标节拍及现状基线"),
        ("点位", "业务/检测点位和范围清单"),
        ("验收", "验收指标和验收责任人"),
    ]
    for keyword, label in checks:
        if keyword not in text:
            missing.append(label)
    if "预算" in text and not re.search(r"\d+(?:\.\d+)?\s*(?:万|万元|元)", text):
        missing.append("明确预算金额或预算区间")

    criteria = [
        {"dimension": "业务", "criterion": "明确优先解决的业务问题及试点范围", "metric": "范围确认率", "target_value": "待确认", "status": "inferred"},
        {"dimension": "流程", "criterion": "形成从问题识别到异常闭环的目标流程", "metric": "关键流程覆盖率", "target_value": "待确认", "status": "inferred"},
        {"dimension": "数据", "criterion": "关键数据可采集、可追溯、可用于分析", "metric": "数据完整率/准确率", "target_value": "待确认", "status": "inferred"},
        {"dimension": "系统", "criterion": "与现有系统集成边界和接口责任明确", "metric": "接口联调通过率", "target_value": "待确认", "status": "inferred"},
    ]

    questions = [
        {"question": "本次项目优先解决的三个业务问题分别是什么？", "purpose": "确认问题优先级", "target_role": "项目负责人/业务负责人", "priority": "P0", "related_issue": "范围"},
        {"question": "当前关键指标的基线值和目标值分别是多少？", "purpose": "定义成功标准", "target_role": "业务负责人", "priority": "P0", "related_issue": "价值"},
        {"question": "项目预算区间、资金来源及审批状态是什么？", "purpose": "判断实施边界", "target_role": "采购/财务/项目负责人", "priority": "P0", "related_issue": "预算"},
        {"question": "最终决策人、影响人和使用部门分别是谁？", "purpose": "明确决策链", "target_role": "客户项目负责人", "priority": "P0", "related_issue": "决策"},
        {"question": "现有系统、设备和数据接口有哪些，责任边界如何划分？", "purpose": "确认集成范围", "target_role": "IT/设备/业务部门", "priority": "P1", "related_issue": "集成"},
    ]

    evidence_map = [
        {"field_name": field, "source_ids": refs, "confidence": 0.72 if refs else 0.5}
        for field in ("surface_problem", "deep_problem", "decision_problem")
    ]

    return {
        "decision_problem": {"value": decision, "status": "inferred", "reason": "将建设诉求转化为管理决策问题。", "evidence_refs": refs},
        "success_criteria": criteria,
        "constraints": [
            {"type": "time", "value": "实施窗口需确认", "status": "missing"},
            {"type": "budget", "value": "预算边界需确认", "status": "missing"},
        ],
        "assumptions": [
            {"hypothesis": "客户愿意采用分阶段试点方式推进", "status": "inferred", "validation_method": "与项目负责人确认"}
        ],
        "missing_information": list(dict.fromkeys(missing)),
        "solution_entry_points": [
            "先进行问题与范围澄清工作坊",
            "选择一个高价值、低依赖场景作为试点",
            "建立业务指标、流程、数据和系统的追踪矩阵",
        ],
        "clarification_questions": questions,
        "evidence_map": evidence_map,
    }
