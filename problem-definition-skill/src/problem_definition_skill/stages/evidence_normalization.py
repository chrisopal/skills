from __future__ import annotations
from typing import Any


def normalize(payload: dict[str, Any]) -> dict[str, Any]:
    evidence: list[dict[str, Any]] = []

    for index, item in enumerate(payload.get("evidence_list", []), start=1):
        evidence.append({
            "evidence_id": item.get("evidence_id") or item.get("source_id") or f"ev_{index:03d}",
            "source_type": item.get("source_type", "evidence"),
            "source_name": item.get("source_name", f"Evidence {index}"),
            "content": str(item.get("content", "")),
            "confidence": float(item.get("confidence", 0.8)),
            "source_refs": item.get("source_refs", []),
        })

    offset = len(evidence)
    for index, item in enumerate(payload.get("materials", []), start=1):
        evidence.append({
            "evidence_id": item.get("evidence_id") or item.get("source_id") or f"ev_{offset + index:03d}",
            "source_type": item.get("type") or item.get("source_type") or "material",
            "source_name": item.get("source_name") or item.get("name") or f"Material {index}",
            "content": str(item.get("content", "")),
            "confidence": float(item.get("confidence", 0.75)),
            "source_refs": item.get("source_refs", []),
        })

    direct_texts = []
    for key in ("text", "meeting_notes", "customer_requirements"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            direct_texts.append((key, value))
    for value in payload.get("customer_statements", []) if isinstance(payload.get("customer_statements"), list) else []:
        if isinstance(value, str) and value.strip():
            direct_texts.append(("customer_statement", value))

    for key, value in direct_texts:
        evidence.append({
            "evidence_id": f"ev_{len(evidence)+1:03d}",
            "source_type": key,
            "source_name": key,
            "content": value,
            "confidence": 0.8,
            "source_refs": [],
        })

    opportunity = payload.get("structured_data") or payload.get("opportunity_analysis") or {}
    if isinstance(opportunity, dict) and opportunity:
        compact_parts = []
        opp = opportunity.get("opportunity", opportunity.get("structured_data", {}).get("opportunity", {}))
        for field in ("name", "core_need", "stage", "budget_signal", "expected_timeline"):
            if isinstance(opp, dict) and opp.get(field):
                compact_parts.append(f"{field}: {opp[field]}")
        for field in ("pain_points", "requirements", "missing_information"):
            if isinstance(opp, dict) and opp.get(field):
                compact_parts.append(f"{field}: {opp[field]}")
        if compact_parts:
            evidence.append({
                "evidence_id": f"ev_{len(evidence)+1:03d}",
                "source_type": "opportunity_analysis_output",
                "source_name": "Opportunity analysis output",
                "content": "\n".join(compact_parts),
                "confidence": 0.85,
                "source_refs": [],
            })

    all_text = "\n".join(item["content"] for item in evidence if item["content"])
    return {
        "evidence": evidence,
        "all_text": all_text,
        "source_ids": [item["evidence_id"] for item in evidence],
    }
