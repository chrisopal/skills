from __future__ import annotations

from typing import Any

from ..utils import new_id


def normalize_input(raw: dict[str, Any]) -> list[dict[str, Any]]:
    """Convert normalized evidence or text materials into Evidence records.

    Host agents should parse/OCR/transcribe raw media first. The reference
    runtime keeps this stage deterministic and dependency-free by wrapping
    already-extracted text plus source-file metadata.
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
            "parse_warnings": item.get("parse_warnings", []),
        })
    return evidence


def all_text(evidence_list: list[dict[str, Any]]) -> str:
    return "\n".join(ev.get("content", "") for ev in evidence_list)
