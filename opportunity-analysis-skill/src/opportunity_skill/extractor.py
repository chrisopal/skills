from __future__ import annotations

from typing import Any

from .stages.account_profile_extraction import (
    INDUSTRY_KEYWORDS,
    PAIN_KEYWORDS,
    REGIONS,
    SYSTEM_KEYWORDS,
    contact_priority,
    extract_account_profile,
    extract_company,
    extract_contacts,
    extract_pain_points,
    extract_region,
    extract_systems,
    identify_decision_chain,
    infer_contact_role,
    infer_decision_role,
    infer_department,
    infer_industry,
    infer_responsibility_scope,
    is_requirement_owner,
    normalize_contact_name,
    pick_first,
)
from .stages.evidence_normalization import all_text, normalize_input
from .stages.opportunity_analysis import (
    analyze_opportunity,
    classify_score,
    extract_budget_signal,
    extract_competitors,
    extract_core_need,
    extract_timeline,
    infer_stage,
    score_opportunity,
)


def _all_text(evidence_list: list[dict[str, Any]]) -> str:
    """Backward-compatible alias for older imports and tests."""
    return all_text(evidence_list)


def _pick_first(patterns: list[str], text: str) -> str | None:
    """Backward-compatible alias for older imports and tests."""
    return pick_first(patterns, text)


def analyze(raw_input: dict[str, Any]) -> dict[str, Any]:
    """Run the closed-loop opportunity analysis pipeline.

    The skill remains one portable capability, while the internal stages are
    now independently reusable by host agents or future adapters:
    evidence_normalization -> account_profile_extraction -> opportunity_analysis.
    """
    evidence_list = normalize_input(raw_input)
    text = all_text(evidence_list)
    account_profile = extract_account_profile(text, raw_input, evidence_list)
    return analyze_opportunity(raw_input, evidence_list, text, account_profile)


__all__ = [
    "INDUSTRY_KEYWORDS",
    "PAIN_KEYWORDS",
    "REGIONS",
    "SYSTEM_KEYWORDS",
    "_all_text",
    "_pick_first",
    "all_text",
    "analyze",
    "analyze_opportunity",
    "classify_score",
    "contact_priority",
    "extract_account_profile",
    "extract_budget_signal",
    "extract_company",
    "extract_competitors",
    "extract_contacts",
    "extract_core_need",
    "extract_pain_points",
    "extract_region",
    "extract_systems",
    "extract_timeline",
    "identify_decision_chain",
    "infer_contact_role",
    "infer_decision_role",
    "infer_department",
    "infer_industry",
    "infer_responsibility_scope",
    "infer_stage",
    "is_requirement_owner",
    "normalize_contact_name",
    "normalize_input",
    "pick_first",
    "score_opportunity",
]
