"""Project closure and warranty gates.

This module validates a declarative closure ledger.  It does not perform a
payment, revoke access, certify evidence, or assert that a referenced person
or document is authentic.  The runtime owns exact artifact reference and
input-closure checks; this module adds the business meaning of each reference
field and the distinction between administrative closure and full discharge.
"""

from __future__ import annotations

from datetime import date
import re
from typing import Any, Iterable


KINDS = {"closure"}
REQUIRED = {
    "closure": (
        "origin",
        "as_of",
        "obligations",
        "warranty",
        "administration",
        "settlement",
        "resources",
        "archive",
        "lessons",
    )
}

# These names are consumed by runtime.walk_refs.  Keep this list local and
# additive: runtime combines it with the references owned by other modules.
REFERENCE_KEYS = {
    "evidence_refs",
    "decision_refs",
    "receipt_refs",
    "terms_refs",
    "transfer_refs",
    "artifact_ref",
}

_DATE_RE = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$")
_OBLIGATION_STATES = {"open", "transferred", "closed"}
_EVIDENCE_KINDS = {
    "source",
    "evidence",
    "minutes",
    "milestone",
    "confirmation",
    "review",
    "testing",
    "release",
    "handover",
    "contract",
    "change",
}
_DECISION_KINDS = {"minutes", "change", "review", "confirmation", "kickoff", "weekly"}
_RECEIPT_KINDS = {"evidence", "confirmation", "milestone", "handover", "minutes"}
_TERMS_KINDS = {"contract", "change", "milestone"}
_TRANSFER_KINDS = {"evidence", "confirmation", "milestone", "handover", "minutes"}
_PRODUCT_KINDS = {
    "contract",
    "kickoff",
    "discovery",
    "minutes",
    "requirements",
    "blueprint",
    "plan",
    "timesheets",
    "costs",
    "risks",
    "change",
    "weekly",
    "milestone",
    "solution",
    "ui_design",
    "integration",
    "work_package",
    "testing",
    "release",
    "handover",
}


def _text(value: Any, label: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a nonempty string")


def _date(value: Any, label: str, *, unknown: bool = True) -> date | None:
    """Parse a date without assigning a value to an unknown date."""
    if value is None or value == "":
        if unknown:
            return None
        raise ValueError(f"{label} is required")
    if not isinstance(value, str) or not _DATE_RE.fullmatch(value):
        raise ValueError(f"{label} must use YYYY-MM-DD")
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise ValueError(f"{label} is not a valid calendar date") from None


def _ref_identity(ref: Any) -> tuple[Any, ...]:
    if not isinstance(ref, dict) or not isinstance(ref.get("artifact_id"), str) or not ref["artifact_id"].strip():
        raise ValueError("Artifact references must contain artifact_id")
    identity = [ref["artifact_id"]]
    if any(key in ref for key in ("revision", "sha256")):
        if not isinstance(ref.get("revision"), int) or isinstance(ref.get("revision"), bool) or ref["revision"] < 1:
            raise ValueError("Artifact references require a positive revision")
        checksum = ref.get("sha256")
        if not isinstance(checksum, str) or not re.fullmatch(r"[0-9a-f]{64}", checksum):
            raise ValueError("Artifact references require a complete SHA-256")
        identity.extend((ref["revision"], checksum))
    return tuple(identity)


def _upstream_index(upstream: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    result = []
    for obj in upstream or ():
        if not isinstance(obj, dict) or not isinstance(obj.get("artifact_id"), str):
            continue
        result.append(obj)
    return result


def _resolve(ref: Any, upstream: list[dict[str, Any]], current_id: str | None = None) -> dict[str, Any]:
    identity = _ref_identity(ref)
    if current_id and identity[0] == current_id:
        raise ValueError("Closure references cannot point to itself")
    matches = []
    for obj in upstream:
        if obj["artifact_id"] != identity[0]:
            continue
        if len(identity) == 1:
            matches.append(obj)
        elif obj.get("revision") == identity[1] and (
            obj.get("sha256") is None or obj.get("sha256") == identity[2]
        ):
            # Runtime load_artifact returns the payload, whose checksum is
            # held by the exact input ref rather than duplicated on payload.
            matches.append(obj)
    if len(matches) != 1:
        raise ValueError(f"Reference {identity[0]} is not an exact upstream input")
    return matches[0]


def _refs(
    refs: Any,
    label: str,
    upstream: list[dict[str, Any]],
    allowed_kinds: set[str],
    current_id: str | None,
    *,
    required: bool = False,
    positive: bool = False,
) -> list[Any]:
    if not isinstance(refs, list):
        raise ValueError(f"{label} must be a list of artifact references")
    if required and not refs:
        raise ValueError(f"{label} requires at least one reference")
    for ref in refs:
        obj = _resolve(ref, upstream, current_id)
        if obj.get("kind") not in allowed_kinds:
            raise ValueError(f"{label} references incompatible artifact kind: {obj.get('kind')}")
        if positive:
            data = obj.get("data", {})
            if obj.get("status", "ready") != "ready":
                raise ValueError(f"{label} needs ready evidence")
            if (obj["kind"] == "confirmation" and (data.get("state") != "accepted" or data.get("open_items"))
                    or obj["kind"] == "review" and data.get("verdict") != "pass"
                    or obj["kind"] == "change" and data.get("state") != "approved"
                    or obj["kind"] == "handover" and (data.get("operations", {}).get("state") != "accepted" or data.get("open_items"))):
                raise ValueError(f"{label} cannot use rejected, conditional or unresolved evidence")
    return refs


def _rows(data: dict[str, Any], key: str, required: tuple[str, ...], rows) -> list[dict[str, Any]]:
    items = rows(data, key, required)
    for item in items:
        if not isinstance(item, dict):
            raise ValueError(f"{key} items must be objects")
    return items


def _data(value: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(value, dict) or not isinstance(value.get("data"), dict):
        raise ValueError("Closure artifact must contain an object data field")
    return value["data"]


def validate(value, upstream, rows, number, purpose):
    """Validate closure semantics after runtime reference closure checks."""
    if not isinstance(value, dict) or value.get("kind") not in KINDS:
        return
    data = _data(value)
    current_id = value.get("artifact_id")
    origin = data.get("origin")
    if origin not in {"actual", "simulation"}:
        raise ValueError("Closure origin must be actual or simulation")
    if origin == "simulation" and purpose != "simulation":
        raise ValueError("Simulated closure is invalid in a real project")
    _date(data.get("as_of"), "closure.as_of", unknown=False)
    upstream_index = _upstream_index(upstream)

    obligations = _rows(
        data,
        "obligations",
        ("title", "category", "owner", "state", "due_date", "evidence_refs", "recipient", "receipt_refs"),
        rows,
    )
    for item in obligations:
        _text(item["title"], f"obligation {item['id']}.title")
        _text(item["category"], f"obligation {item['id']}.category")
        _text(item["owner"], f"obligation {item['id']}.owner")
        if item["state"] not in _OBLIGATION_STATES:
            raise ValueError(f"Unknown obligation state: {item['state']}")
        _date(item.get("due_date"), f"obligation {item['id']}.due_date")
        _refs(item["evidence_refs"], f"obligation {item['id']}.evidence_refs", upstream_index, _EVIDENCE_KINDS, current_id,
              positive=item["state"] == "closed")
        _refs(item["receipt_refs"], f"obligation {item['id']}.receipt_refs", upstream_index, _RECEIPT_KINDS, current_id, positive=True)
        recipient = item.get("recipient")
        if recipient not in (None, ""):
            _text(recipient, f"obligation {item['id']}.recipient")
        if item["state"] == "transferred" and (recipient in (None, "") or not item["receipt_refs"]):
            raise ValueError(f"Transferred obligation {item['id']} needs recipient and receipt evidence")
        if item["state"] == "closed" and not item["evidence_refs"]:
            raise ValueError(f"Closed obligation {item['id']} needs evidence_refs")
        if "correction_reason" in item and item["correction_reason"] is not None:
            _text(item["correction_reason"], f"obligation {item['id']}.correction_reason")
        if "history" in item and not isinstance(item["history"], list):
            raise ValueError(f"obligation {item['id']}.history must be a list")

    warranty = data["warranty"]
    if not isinstance(warranty, dict):
        raise ValueError("warranty must be an object")
    if not isinstance(warranty.get("applicable"), bool):
        raise ValueError("warranty.applicable must be boolean")
    if "reason" not in warranty or warranty["reason"] is None:
        raise ValueError("warranty.reason is required")
    if warranty["reason"] != "":
        _text(warranty["reason"], "warranty.reason")
    if not warranty["applicable"]:
        _text(warranty["reason"], "warranty.reason")
    _date(warranty.get("start_date"), "warranty.start_date")
    _date(warranty.get("end_date"), "warranty.end_date")
    if warranty.get("start_date") and warranty.get("end_date"):
        if _date(warranty["start_date"], "warranty.start_date") > _date(warranty["end_date"], "warranty.end_date"):
            raise ValueError("warranty.start_date must be on or before end_date")
    _refs(warranty.get("terms_refs", []), "warranty.terms_refs", upstream_index, _TERMS_KINDS, current_id,
          required=True, positive=True)
    _refs(warranty.get("transfer_refs", []), "warranty.transfer_refs", upstream_index, _TRANSFER_KINDS, current_id, positive=True)
    warranty_items = _rows(warranty, "items", ("title", "owner", "state", "evidence_refs"), rows)
    for item in warranty_items:
        _text(item["title"], f"warranty item {item['id']}.title")
        _text(item["owner"], f"warranty item {item['id']}.owner")
        if item["state"] not in {"open", "closed"}:
            raise ValueError(f"Unknown warranty item state: {item['state']}")
        _refs(item["evidence_refs"], f"warranty item {item['id']}.evidence_refs", upstream_index, _EVIDENCE_KINDS, current_id,
              positive=item["state"] == "closed")
        if item["state"] == "closed" and not item["evidence_refs"]:
            raise ValueError(f"Closed warranty item {item['id']} needs evidence_refs")
        if "correction_reason" in item and item["correction_reason"] is not None:
            _text(item["correction_reason"], f"warranty item {item['id']}.correction_reason")
        if "history" in item and not isinstance(item["history"], list):
            raise ValueError(f"warranty item {item['id']}.history must be a list")
    if warranty["applicable"]:
        _text(warranty.get("owner"), "warranty.owner")
    elif warranty.get("owner") not in (None, ""):
        _text(warranty["owner"], "warranty.owner")

    administration = data["administration"]
    if not isinstance(administration, dict) or administration.get("state") not in {"open", "closed"}:
        raise ValueError("administration.state must be open or closed")
    _refs(administration.get("decision_refs", []), "administration.decision_refs", upstream_index, _DECISION_KINDS, current_id,
          required=administration["state"] == "closed", positive=administration["state"] == "closed")

    settlement = data["settlement"]
    if not isinstance(settlement, dict) or settlement.get("state") not in {"open", "reconciled"}:
        raise ValueError("settlement.state must be open or reconciled")
    _refs(settlement.get("evidence_refs", []), "settlement.evidence_refs", upstream_index, _EVIDENCE_KINDS, current_id,
          required=settlement["state"] == "reconciled", positive=settlement["state"] == "reconciled")

    resources = _rows(data, "resources", ("owner", "state", "reason", "evidence_refs"), rows)
    for item in resources:
        _text(item["owner"], f"resource {item['id']}.owner")
        if item["state"] not in {"retained", "released"}:
            raise ValueError(f"Unknown resource state: {item['state']}")
        _refs(item["evidence_refs"], f"resource {item['id']}.evidence_refs", upstream_index, _EVIDENCE_KINDS, current_id,
              positive=item["state"] == "released")
        if item["state"] == "retained":
            _text(item["reason"], f"resource {item['id']}.reason")
        elif not item["evidence_refs"]:
            raise ValueError(f"Released resource {item['id']} needs evidence_refs")

    archives = _rows(data, "archive", ("artifact_ref", "owner", "classification", "retention_until"), rows)
    for item in archives:
        _text(item["owner"], f"archive {item['id']}.owner")
        _text(item["classification"], f"archive {item['id']}.classification")
        _date(item.get("retention_until"), f"archive {item['id']}.retention_until")
        obj = _resolve(item["artifact_ref"], upstream_index, current_id)
        if obj.get("kind") not in _PRODUCT_KINDS:
            raise ValueError(f"archive {item['id']} must bind an actual product artifact")

    lessons = _rows(data, "lessons", ("observation", "action", "owner"), rows)
    for item in lessons:
        for field in ("observation", "action", "owner"):
            _text(item[field], f"lesson {item['id']}.{field}")


def _section(value: dict[str, Any]) -> dict[str, Any]:
    return value.get("data", value) if isinstance(value, dict) else {}


def _stable_rows(data: dict[str, Any], key: str) -> dict[str, dict[str, Any]]:
    items = data.get(key, [])
    if not isinstance(items, list):
        raise ValueError(f"{key} must be a list")
    result: dict[str, dict[str, Any]] = {}
    for item in items:
        if not isinstance(item, dict) or not isinstance(item.get("id"), str) or not item["id"]:
            raise ValueError(f"{key} rows need stable IDs")
        if item["id"] in result:
            raise ValueError(f"Duplicate stable ID in {key}: {item['id']}")
        result[item["id"]] = item
    return result


def _check_reopen(previous: dict[str, Any], current: dict[str, Any], key: str, label: str) -> None:
    old_rows = _stable_rows(previous, key)
    new_rows = _stable_rows(current, key)
    missing = set(old_rows) - set(new_rows)
    if missing:
        raise ValueError(f"Closed {label} records cannot be deleted: {', '.join(sorted(missing))}")
    for item_id, old in old_rows.items():
        if old.get("state") == "closed" and new_rows[item_id].get("state") != "closed":
            item = new_rows[item_id]
            if not item.get("correction_reason") or not item.get("evidence_refs"):
                raise ValueError(f"Reopening {label} {item_id} needs correction_reason and evidence_refs")


def check_revision(previous, current):
    """Keep closure obligations and warranty items stable across revisions."""
    old = _section(previous)
    new = _section(current)
    _check_reopen(old, new, "obligations", "obligation")
    _check_reopen(old, new, "resources", "resource")
    _check_reopen(old, new, "archive", "archive")
    old_warranty = old.get("warranty", {})
    new_warranty = new.get("warranty", {})
    if not isinstance(old_warranty, dict) or not isinstance(new_warranty, dict):
        raise ValueError("warranty must be an object")
    _check_reopen(old_warranty, new_warranty, "items", "warranty item")
    if old_warranty.get("applicable") and not new_warranty.get("applicable"):
        if (not new_warranty.get("correction_reason")
                or new_warranty.get("terms_refs") == old_warranty.get("terms_refs")):
            raise ValueError("Changing warranty applicability needs correction_reason and new terms evidence")
    return True


def _health_current(health: Any) -> bool:
    return health == "current" or health is True


def gate(value, upstream=None, health="current", as_of=None):
    """Return independent closure statuses and a conservative readiness gate."""
    data = _data(value)
    reasons: list[str] = []
    healthy = _health_current(health)
    status_ready = value.get("status") == "ready"
    if not status_ready:
        reasons.append("Artifact is not ready")
    if not healthy:
        reasons.append("Artifact dependencies are stale or unreadable")

    as_of_value = as_of if as_of is not None else data.get("as_of")
    as_of_date = _date(as_of_value, "gate.as_of")
    if as_of_date is None:
        reasons.append("Gate as_of date is unknown")

    obligations = data.get("obligations", [])
    administration = data.get("administration", {})
    settlement = data.get("settlement", {})
    admin_reasons: list[str] = []
    if administration.get("state") != "closed":
        admin_reasons.append("Administration is not closed")
    if not administration.get("decision_refs"):
        admin_reasons.append("Administration decision evidence is missing")
    if settlement.get("state") != "reconciled":
        admin_reasons.append("Settlement is not reconciled")
    for item in obligations:
        if item.get("state") == "open":
            admin_reasons.append(f"Open obligation remains: {item.get('id', '<unknown>')}")
    reasons.extend(admin_reasons)
    administrative_closed = not admin_reasons

    warranty = data.get("warranty", {})
    applicable = warranty.get("applicable") is True
    warranty_transfer_reasons: list[str] = []
    if applicable and not warranty.get("transfer_refs"):
        warranty_transfer_reasons.append("Warranty transfer evidence is missing")
    warranty_transferred = not warranty_transfer_reasons

    warranty_end_reasons: list[str] = []
    warranty_items = warranty.get("items", [])
    if applicable:
        start_date = _date(warranty.get("start_date"), "warranty.start_date")
        end_date = _date(warranty.get("end_date"), "warranty.end_date")
        if start_date is None:
            warranty_end_reasons.append("Warranty start date is unknown")
        if end_date is None:
            warranty_end_reasons.append("Warranty end date is unknown")
        if as_of_date is None or end_date is None:
            pass
        elif as_of_date < end_date:
            warranty_end_reasons.append("Warranty end date has not passed")
    for item in warranty_items:
        if item.get("state") == "open":
            warranty_end_reasons.append(f"Open warranty item remains: {item.get('id', '<unknown>')}")
    warranty_ended = not warranty_end_reasons

    full_reasons = list(admin_reasons) + list(warranty_end_reasons) + list(warranty_transfer_reasons)
    if as_of_date is None:
        full_reasons.append("Gate as_of date is unknown")
    if not data.get("archive"):
        full_reasons.append("Archive index is empty")
    for item in obligations:
        if item.get("state") == "transferred":
            full_reasons.append(f"Transferred obligation is not fully discharged: {item.get('id', '<unknown>')}")
        if item.get("due_date") in (None, ""):
            full_reasons.append(f"Obligation due date is unknown: {item.get('id', '<unknown>')}")
        elif as_of_date is not None and item.get("state") == "open" and _date(item["due_date"], "obligation.due_date") < as_of_date:
            full_reasons.append(f"Overdue obligation remains open: {item.get('id', '<unknown>')}")
    for item in data.get("resources", []):
        if item.get("state") == "retained":
            full_reasons.append(f"Resource remains retained: {item.get('id', '<unknown>')}")
        elif item.get("state") == "released" and not item.get("evidence_refs"):
            full_reasons.append(f"Resource release evidence is missing: {item.get('id', '<unknown>')}")
    for item in data.get("archive", []):
        if item.get("retention_until") in (None, ""):
            full_reasons.append(f"Archive retention date is unknown: {item.get('id', '<unknown>')}")
    if not applicable and not warranty.get("reason"):
        full_reasons.append("Warranty applicability reason is missing")
    if not healthy:
        full_reasons.append("Closure inputs are not current")
    if not status_ready:
        full_reasons.append("Closure artifact is not ready")
    fully_discharged = not full_reasons

    eligible = status_ready and healthy
    return {
        "administrative_closed": bool(eligible and administrative_closed),
        "warranty_transferred": bool(eligible and warranty_transferred),
        "warranty_ended": bool(eligible and warranty_ended),
        "fully_discharged": bool(eligible and fully_discharged),
        "ready": bool(eligible and fully_discharged),
        "reasons": list(dict.fromkeys(reasons + full_reasons + warranty_transfer_reasons)),
    }
