from __future__ import annotations
from typing import Any
from .stages.evidence_normalization import normalize
from .stages.problem_framing import frame
from .stages.decision_definition import define


def analyze(payload: dict[str, Any]) -> dict[str, Any]:
    normalized = normalize(payload)
    framed = frame(normalized)
    decision = define(normalized, framed)

    problem_definition = {
        "surface_problem": framed["surface_problem"],
        "deep_problem": framed["deep_problem"],
        "decision_problem": decision["decision_problem"],
        "business_impacts": framed["business_impacts"],
        "success_criteria": decision["success_criteria"],
        "constraints": decision["constraints"],
        "assumptions": decision["assumptions"],
        "missing_information": decision["missing_information"],
        "solution_entry_points": decision["solution_entry_points"],
    }
    case_name = payload.get("case_name", "未命名问题定义")
    structured = {
        "case_name": case_name,
        "account_id": payload.get("account_id"),
        "opportunity_id": payload.get("opportunity_id"),
        "problem_definition": problem_definition,
        "clarification_questions": decision["clarification_questions"],
        "evidence": normalized["evidence"],
        "evidence_map": decision["evidence_map"],
    }
    return {
        "human_summary": f"{problem_definition['surface_problem']['value']} 核心决策是：{problem_definition['decision_problem']['value']}",
        "structured_data": structured,
    }
