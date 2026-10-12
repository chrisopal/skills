#!/usr/bin/env python3
"""Local daily delivery operations built on the immutable delivery runtime.

This module deliberately keeps the four operational ledgers small and explicit:
progress is a weekly-compatible operational evidence ledger, hours are actual
timesheets, risks are the runtime risk ledger, and changes are runtime change
proposals.  It never activates a candidate or fabricates an approver.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import date, datetime, timedelta, timezone
import argparse
from contextlib import contextmanager
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import threading
import uuid

try:
    import fcntl
except ImportError:  # pragma: no cover - Windows fallback remains process-serialized
    fcntl = None


_RUNTIME_PATH = Path(__file__).with_name("runtime.py")
_SPEC = importlib.util.spec_from_file_location("delivery_daily_runtime", _RUNTIME_PATH)
if _SPEC is None or _SPEC.loader is None:  # pragma: no cover - import machinery failure
    raise ImportError("Unable to load delivery runtime")
runtime = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(runtime)


MAX_TEXT = 5000
PROGRESS_ID = "DAILY-PROGRESS"
DEFAULT_HOURS_ID = "HOURS"
DEFAULT_RISKS_ID = "RISKS"

_LOCKS: dict[str, threading.RLock] = {}
_LOCKS_GUARD = threading.Lock()


class ConflictError(ValueError):
    """Raised when a writer used an older ledger revision."""

    status_code = 409

    def __init__(self, message: str, current_revision: int = 0, current: dict | None = None,
                 current_fingerprint: str | None = None):
        super().__init__(message)
        self.current_revision = current_revision
        self.current = current
        self.current_fingerprint = current_fingerprint


def _project_key(project: str | Path) -> str:
    return str(runtime.root_path(project))


def project_lock(project: str | Path) -> threading.RLock:
    key = _project_key(project)
    with _LOCKS_GUARD:
        return _LOCKS.setdefault(key, threading.RLock())


@contextmanager
def project_write_lock(project: str | Path):
    """Serialize this process and other local processes sharing a project."""
    lock = project_lock(project)
    with lock:
        lock_path = runtime.confined(project, "00-control/daily-workbench.lock")
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        with lock_path.open("a+") as handle:
            if fcntl is not None:
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                if fcntl is not None:
                    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def registry_fingerprint(project: str | Path) -> str:
    path = runtime.confined(project, "00-control/registry.json")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _text(value, label: str, *, required: bool = True, limit: int = MAX_TEXT) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{label} must be text")
    value = value.strip()
    if required and not value:
        raise ValueError(f"{label} is required")
    if len(value) > limit:
        raise ValueError(f"{label} is too long")
    if any(ord(char) < 32 and char not in "\t\n\r" for char in value):
        raise ValueError(f"{label} contains an invalid control character")
    return value


def _identifier(value, label: str) -> str:
    value = _text(value, label, limit=80)
    runtime.identifier(value)
    return value


def _date(value, label: str = "date") -> str:
    if value is None:
        return datetime.now(timezone.utc).date().isoformat()
    value = _text(value, label, limit=10)
    try:
        return date.fromisoformat(value).isoformat()
    except ValueError:
        raise ValueError(f"{label} must be YYYY-MM-DD") from None


def _week_period(day: str) -> str:
    current = date.fromisoformat(day)
    monday = current - timedelta(days=current.weekday())
    return f"{monday.isoformat()}/{(monday + timedelta(days=6)).isoformat()}"


def _list(value, label: str, *, max_items: int = 200) -> list:
    if value is None:
        return []
    if not isinstance(value, list) or len(value) > max_items:
        raise ValueError(f"{label} must be a list with at most {max_items} items")
    return value


def _number(value, label: str, *, allow_none: bool = False) -> float | None:
    if value is None and allow_none:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float, str)):
        raise ValueError(f"{label} must be numeric")
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"{label} must be numeric") from None
    if number != number or number in (float("inf"), float("-inf")) or number < 0:
        raise ValueError(f"{label} must be finite and nonnegative")
    return number


def _ref_key(ref: dict) -> tuple[str, int, str]:
    return (ref["artifact_id"], ref["revision"], ref["sha256"])


def _latest(project: str | Path, artifact_id: str, kind: str | None = None) -> tuple[dict | None, dict | None]:
    try:
        ref = runtime.latest_ref(project, artifact_id)
    except ValueError:
        return None, None
    value = runtime.load_artifact(project, ref)
    if kind is not None and value["kind"] != kind:
        raise ValueError(f"{artifact_id} is not a {kind} ledger")
    return ref, value


def _ledger(project: str | Path, kind: str, create_id: str | None = None) -> tuple[str, dict | None, dict | None]:
    """Resolve the existing singleton ID for a kind before considering a new ID."""
    registry = runtime.read_registry(project)
    if create_id and create_id in registry["artifacts"]:
        entry = registry["artifacts"][create_id]
        if entry.get("kind") != kind:
            raise ValueError(f"{create_id} already belongs to {entry.get('kind')}, not {kind}")
        ref = runtime.canonical_ref(dict(entry, artifact_id=create_id))
        return create_id, ref, runtime.load_artifact(project, ref)
    if kind == "weekly" and create_id:
        # WEEKLY may already be a semantic reporting artifact. Daily evidence
        # has its own stable ID and must never reuse that master ledger.
        return create_id, None, None
    matches = [(aid, entry) for aid, entry in registry["artifacts"].items() if entry.get("kind") == kind]
    if len(matches) > 1:
        raise ValueError(f"Project has multiple {kind} master ledgers: {[aid for aid, _ in matches]}")
    if matches:
        aid, entry = matches[0]
        ref = runtime.canonical_ref(dict(entry, artifact_id=aid))
        return aid, ref, runtime.load_artifact(project, ref)
    if create_id is None:
        return "", None, None
    existing = registry["artifacts"].get(create_id)
    if existing and existing.get("kind") != kind:
        raise ValueError(f"{create_id} already belongs to {existing.get('kind')}, not {kind}")
    return create_id, None, None


def _plan_context(project: str | Path) -> tuple[dict | None, set[str]]:
    registry = runtime.read_registry(project)
    candidates = [(aid, entry) for aid, entry in registry["artifacts"].items() if entry.get("kind") == "plan"]
    if not candidates:
        return None, set()
    aid, entry = candidates[0]
    effective = registry.get("effective", {}).get(aid)
    ref = runtime.canonical_ref(dict(effective or entry, artifact_id=aid))
    value = runtime.load_artifact(project, ref)
    ids = {item.get("id") for item in value["data"].get("work_packages", []) if isinstance(item, dict)}
    return ref, {item for item in ids if isinstance(item, str)}


def _validate_work_package(project: str | Path, work_package_id: str) -> dict | None:
    plan_ref, work_package_ids = _plan_context(project)
    if plan_ref is not None and work_package_id not in work_package_ids:
        raise ValueError(f"work_package_id is not present in the registered plan: {work_package_id}")
    return plan_ref


def _resolve_evidence(project: str | Path, payload: dict) -> list[dict]:
    raw = payload.get("evidence_refs", [])
    ids = payload.get("evidence_ids", [])
    if not isinstance(raw, list) or not isinstance(ids, list):
        raise ValueError("evidence_refs and evidence_ids must be lists")
    values = list(raw) + list(ids)
    resolved: list[dict] = []
    seen: set[tuple[str, int, str]] = set()
    for item in values:
        if isinstance(item, str):
            aid = _identifier(item, "evidence_id")
            ref = runtime.latest_ref(project, aid)
        elif isinstance(item, dict):
            ref = runtime.canonical_ref(item)
            runtime.load_artifact(project, ref)
        else:
            raise ValueError("Evidence must be an artifact ID or exact artifact reference")
        if _ref_key(ref) not in seen:
            resolved.append(ref)
            seen.add(_ref_key(ref))
    return resolved


def _registration_inputs(project: str | Path, prior: dict | None, data: dict,
                         extra: list[dict] | None = None) -> list[dict]:
    refs: list[dict] = []
    for ref in (prior or {}).get("inputs", []):
        refs.append(runtime.canonical_ref(ref))
    for ref in runtime.walk_refs(data):
        refs.append(runtime.canonical_ref(ref))
    for ref in extra or []:
        refs.append(runtime.canonical_ref(ref))
    result: list[dict] = []
    seen: set[tuple[str, int, str]] = set()
    for ref in refs:
        if _ref_key(ref) not in seen:
            result.append(ref)
            seen.add(_ref_key(ref))
    return result


def _check_registry_precondition(project: str | Path, expected_fingerprint: str | None):
    current = registry_fingerprint(project)
    if expected_fingerprint is None:
        raise ValueError("expected_registry_fingerprint is required")
    if expected_fingerprint != current:
        raise ConflictError("Project registry changed; reload before saving", current_fingerprint=current)


def _expected_revision(project: str | Path, artifact_id: str, expected_revision) -> tuple[dict | None, dict | None]:
    ref, value = _latest(project, artifact_id)
    current_revision = ref["revision"] if ref else 0
    if expected_revision is not None:
        if isinstance(expected_revision, bool) or not isinstance(expected_revision, int) or expected_revision < 0:
            raise ValueError("expected_revision must be a nonnegative integer")
        if expected_revision != current_revision:
            raise ConflictError(
                f"{artifact_id} changed from revision {expected_revision} to {current_revision}; reload before saving",
                current_revision,
            )
    return ref, value


def _new_revision(prior_ref: dict | None) -> int:
    return prior_ref["revision"] + 1 if prior_ref else 1


def _register(project: str | Path, artifact_id: str, kind: str, data: dict, prior_ref: dict | None,
              *, status: str = "ready", visibility: str = "internal", inputs: list[dict] | None = None) -> dict:
    info = runtime.read_project(project)
    # The runtime intentionally rejects an artifact depending on another
    # revision of its own ID. Immutable revision files already preserve the
    # ledger history, so appends preserve upstream inputs but never self-reference.
    inputs = list(inputs) if inputs is not None else []
    payload = {
        "project_id": info["project_id"],
        "artifact_id": artifact_id,
        "revision": _new_revision(prior_ref),
        "kind": kind,
        "visibility": visibility,
        "status": status,
        "inputs": inputs,
        "data": data,
    }
    return runtime.register(project, payload)


def _copy_data(value: dict | None, defaults: dict) -> dict:
    result = deepcopy(value["data"] if value else defaults)
    if not isinstance(result, dict):
        raise ValueError("Ledger data must be an object")
    return result


def state(project: str | Path) -> dict:
    """Return the runtime snapshot plus small revision metadata for the UI."""
    with project_write_lock(project):
        return _state_unlocked(project)


def _state_unlocked(project: str | Path) -> dict:
    root = runtime.root_path(project)
    snapshot = runtime.snapshot(root)
    registry = runtime.read_registry(root)
    latest = {
        aid: {"revision": entry["revision"], "kind": entry["kind"]}
        for aid, entry in registry["artifacts"].items()
    }
    resolved = {}
    for kind, create_id in (("weekly", PROGRESS_ID), ("timesheets", DEFAULT_HOURS_ID), ("risks", DEFAULT_RISKS_ID)):
        aid, ref, value = _ledger(root, kind, create_id)
        if kind == "weekly" and aid == "":
            aid = PROGRESS_ID
        resolved[kind] = {"artifact_id": aid, "revision": ref["revision"] if ref else 0}
    plan_ref, work_package_ids = _plan_context(root)
    evidence_options = []
    for item in snapshot.get("artifacts", []):
        if item.get("kind") in {"source", "evidence", "review", "requirements", "minutes"}:
            evidence_options.append({"artifact_id": item["artifact_id"], "revision": item["revision"], "kind": item["kind"]})
    return {
        "project": runtime.read_project(root),
        "snapshot": snapshot,
        "latest": latest,
        "effective": registry["effective"],
        "registry_fingerprint": registry_fingerprint(root),
        "ledger_ids": resolved,
        "plan_work_packages": sorted(work_package_ids),
        "evidence_options": evidence_options,
        "active_ledgers": {
            PROGRESS_ID: resolved["weekly"]["revision"],
            resolved["timesheets"]["artifact_id"]: resolved["timesheets"]["revision"],
            resolved["risks"]["artifact_id"]: resolved["risks"]["revision"],
        },
    }


def record_progress(project: str | Path, payload: dict, expected_revision=None, expected_registry_fingerprint=None) -> dict:
    if not isinstance(payload, dict):
        raise ValueError("Progress payload must be an object")
    day = _date(payload.get("date"))
    work_package_id = _identifier(payload.get("work_package_id"), "work_package_id")
    status = _text(payload.get("status", "in_progress"), "status", limit=20)
    if status not in {"completed", "in_progress", "blocked", "planned"}:
        raise ValueError("status must be completed, in_progress, blocked, or planned")
    summary = _text(payload.get("summary") or payload.get("actual_output"), "summary")
    next_step = _text(payload.get("next_step", ""), "next_step", required=False)
    entry_id = payload.get("entry_id", payload.get("id")) or f"OP-{day.replace('-', '')}-{uuid.uuid4().hex[:10]}"
    entry_id = _identifier(entry_id, "entry_id")
    customer_visible = payload.get("customer_visible") is True
    with project_write_lock(project):
        _check_registry_precondition(project, expected_registry_fingerprint)
        plan_ref = _validate_work_package(project, work_package_id)
        evidence_refs = _resolve_evidence(project, payload)
        if status == "completed" and not evidence_refs:
            raise ValueError("Completed progress requires exact registered evidence references")
        prior_ref, prior = _expected_revision(project, PROGRESS_ID, expected_revision)
        data = _copy_data(prior, {
            "period": _week_period(day), "as_of": day, "completed": [], "next": [],
            "milestones": [], "risks": [], "decisions_required": [], "coverage_gaps": [], "operations": [],
        })
        operations = data.setdefault("operations", [])
        if any(item.get("id") == entry_id for item in operations):
            raise ValueError(f"Duplicate progress entry ID: {entry_id}")
        entry = {
            "id": entry_id, "date": day, "work_package_id": work_package_id,
            "status": status, "summary": summary, "next_step": next_step,
            "evidence_refs": evidence_refs, "customer_visible": customer_visible,
        }
        operations.append(entry)
        data["period"] = _week_period(day)
        data["as_of"] = max(str(data.get("as_of", day)), day)
        data["completed"] = [item for item in operations if item.get("status") == "completed"]
        data["next"] = list(dict.fromkeys(item["next_step"] for item in operations if item.get("next_step")))
        inputs = _registration_inputs(project, prior, data, [plan_ref] if plan_ref else [])
        ref = _register(project, PROGRESS_ID, "weekly", data, prior_ref, inputs=inputs)
        return {"ref": ref, "entry": entry, "revision": ref["revision"], "state": _state_unlocked(project)}


def record_hours(project: str | Path, payload: dict, expected_revision=None, expected_registry_fingerprint=None) -> dict:
    if not isinstance(payload, dict):
        raise ValueError("Hours payload must be an object")
    day = _date(payload.get("date"))
    person = _text(payload.get("person"), "person", limit=200)
    work_package_id = _identifier(payload.get("work_package_id"), "work_package_id")
    hours = _number(payload.get("hours"), "hours")
    rate = _number(payload.get("rate"), "rate", allow_none=True)
    resource_type = _text(payload.get("resource_type", "internal"), "resource_type", limit=20)
    status = _text(payload.get("status", "submitted"), "status", limit=20)
    if resource_type not in {"internal", "outsourced"}:
        raise ValueError("resource_type must be internal or outsourced")
    if status != "submitted":
        raise ValueError("Daily hours endpoint accepts submitted timesheets only")
    entry_id = payload.get("entry_id", payload.get("id")) or f"H-{day.replace('-', '')}-{uuid.uuid4().hex[:10]}"
    entry_id = _identifier(entry_id, "entry_id")
    with project_write_lock(project):
        _check_registry_precondition(project, expected_registry_fingerprint)
        hours_id, prior_ref, prior = _ledger(project, "timesheets", DEFAULT_HOURS_ID)
        plan_ref = _validate_work_package(project, work_package_id)
        data = _copy_data(prior, {"items": [], "remaining_labor": None})
        items = data.setdefault("items", [])
        if any(item.get("id") == entry_id for item in items):
            raise ValueError(f"Duplicate timesheet entry ID: {entry_id}")
        entry = {
            "id": entry_id, "person": person, "date": day, "work_package_id": work_package_id,
            "hours": hours, "rate": rate, "resource_type": resource_type, "status": "submitted",
        }
        items.append(entry)
        inputs = _registration_inputs(project, prior, data, [plan_ref] if plan_ref else [])
        ref = _register(project, hours_id, "timesheets", data, prior_ref, inputs=inputs)
        return {
            "ref": ref, "entry": entry, "revision": ref["revision"],
            "ledger_id": hours_id, "cost_summary": runtime.cost_summary(project), "state": _state_unlocked(project),
        }


def record_risk(project: str | Path, payload: dict, expected_revision=None, expected_registry_fingerprint=None) -> dict:
    if not isinstance(payload, dict):
        raise ValueError("Risk payload must be an object")
    item_id = _identifier(payload.get("entry_id", payload.get("id")), "entry_id")
    risk_type = _text(payload.get("type", "risk"), "type", limit=20)
    if risk_type not in {"risk", "issue", "quality"}:
        raise ValueError("type must be risk, issue, or quality")
    title = _text(payload.get("title"), "title", limit=300)
    owner = _text(payload.get("owner"), "owner", limit=200)
    status = _text(payload.get("status", "open"), "status", limit=20)
    if status not in {"open", "closed"}:
        raise ValueError("status must be open or closed")
    action = _text(payload.get("action", ""), "action", required=False, limit=1000)
    due = _date(payload["due"], "due") if payload.get("due") else ""
    if status == "closed" and not (payload.get("evidence_refs") or payload.get("evidence_ids")):
        raise ValueError("Closing a risk requires exact registered evidence references")
    item = {
        "id": item_id, "type": risk_type, "title": title, "owner": owner,
        "status": status, "action": action, "due": due,
    }
    with project_write_lock(project):
        _check_registry_precondition(project, expected_registry_fingerprint)
        risk_id, prior_ref, prior = _ledger(project, "risks", DEFAULT_RISKS_ID)
        evidence_refs = _resolve_evidence(project, payload)
        if status == "closed" and not evidence_refs:
            raise ValueError("Closing a risk requires exact registered evidence references")
        item["evidence_refs"] = evidence_refs
        data = _copy_data(prior, {"items": []})
        items = data.setdefault("items", [])
        existing_index = next((index for index, existing in enumerate(items) if existing.get("id") == item_id), None)
        if existing_index is None:
            items.append(item)
        else:
            # Risk state changes are revisions of the same stable ledger row;
            # the previous aggregate remains recoverable as an older artifact.
            item = {**items[existing_index], **item}
            items[existing_index] = item
        inputs = _registration_inputs(project, prior, data)
        ref = _register(project, risk_id, "risks", data, prior_ref, inputs=inputs)
        return {"ref": ref, "entry": item, "revision": ref["revision"], "ledger_id": risk_id, "state": _state_unlocked(project)}


def record_change(project: str | Path, payload: dict, expected_revision=None, expected_registry_fingerprint=None) -> dict:
    if not isinstance(payload, dict):
        raise ValueError("Change payload must be an object")
    change_id = _identifier(payload.get("change_id", payload.get("id")), "change_id")
    reason = _text(payload.get("reason"), "reason", limit=2000)
    change_state = _text(payload.get("state", "proposed"), "state", limit=20)
    if change_state != "proposed":
        raise ValueError("This endpoint only creates or revises proposed changes")
    affected_ids = [_identifier(item, "affected_id") for item in _list(payload.get("affected_ids"), "affected_ids")]
    if not affected_ids:
        raise ValueError("affected_ids is required")
    impact = payload.get("impact")
    if not isinstance(impact, dict):
        raise ValueError("impact must be an object")
    replacements = _list(payload.get("replacements"), "replacements")
    baseline_refs = _list(payload.get("baseline_refs"), "baseline_refs")
    decision_refs = _list(payload.get("decision_refs"), "decision_refs")
    for label, refs in (("baseline_refs", baseline_refs), ("replacements", replacements), ("decision_refs", decision_refs)):
        if not all(isinstance(ref, dict) for ref in refs):
            raise ValueError(f"{label} must contain artifact references")
    with project_write_lock(project):
        _check_registry_precondition(project, expected_registry_fingerprint)
        registry = runtime.read_registry(project)
        existing_entry = registry["artifacts"].get(change_id)
        if existing_entry and existing_entry.get("kind") != "change":
            raise ValueError(f"{change_id} already belongs to {existing_entry.get('kind')}")
        prior_ref, prior = _latest(project, change_id, "change")
        if prior is not None and prior["data"]["state"] != "proposed":
            raise ValueError("Decided changes are immutable through the proposal endpoint; create a new proposal")
        if prior_ref is not None and expected_revision is None:
            raise ValueError("expected_revision is required when revising a change proposal")
        if prior_ref is not None and expected_revision != prior_ref["revision"]:
            raise ConflictError("Change proposal revision is stale", prior_ref["revision"], current_fingerprint=registry_fingerprint(project))
        # Baselines are only taken from the current effective refs when explicitly requested.
        if payload.get("use_effective_baseline"):
            baseline_refs = [registry["effective"][aid] for aid in affected_ids if aid in registry["effective"]]
        inputs: list[dict] = []
        for ref in baseline_refs + replacements + decision_refs:
            canonical = runtime.canonical_ref(ref)
            runtime.load_artifact(project, canonical)
            if _ref_key(canonical) not in {_ref_key(item) for item in inputs}:
                inputs.append(canonical)
        data = {
            "state": change_state, "reason": reason, "affected_ids": affected_ids,
            "baseline_refs": baseline_refs, "replacements": replacements,
            "decision_refs": decision_refs, "impact": deepcopy(impact),
        }
        ref = _register(project, change_id, "change", data, prior_ref, status="ready", visibility="internal", inputs=inputs)
        return {"ref": ref, "change": data, "revision": ref["revision"], "state": _state_unlocked(project)}


def _period_dates(period: str | None) -> tuple[str, str]:
    if not period:
        today = datetime.now(timezone.utc).date()
        start = today - timedelta(days=today.weekday())
        return start.isoformat(), (start + timedelta(days=6)).isoformat()
    match = re.fullmatch(r"(\d{4}-\d{2}-\d{2})/(\d{4}-\d{2}-\d{2})", period)
    if not match:
        raise ValueError("period must be YYYY-MM-DD/YYYY-MM-DD")
    start, end = match.groups()
    _date(start, "period start")
    _date(end, "period end")
    if start > end:
        raise ValueError("period start must be before period end")
    return start, end


def weekly_report(project: str | Path, period: str | None = None, audience: str = "internal") -> str:
    with project_write_lock(project):
        return _weekly_report_unlocked(project, period, audience)


def _weekly_report_unlocked(project: str | Path, period: str | None = None, audience: str = "internal") -> str:
    if audience not in {"internal", "customer"}:
        raise ValueError("audience must be internal or customer")
    start, end = _period_dates(period)
    snapshot = runtime.snapshot(project)
    records = {item["artifact_id"]: item for item in snapshot["artifacts"]}
    progress_id, _, _ = _ledger(project, "weekly", PROGRESS_ID)
    hours_id, _, _ = _ledger(project, "timesheets", DEFAULT_HOURS_ID)
    risks_id, _, _ = _ledger(project, "risks", DEFAULT_RISKS_ID)
    operations = (records.get(progress_id, {}).get("data", {}).get("operations", []))
    operations = [item for item in operations if start <= str(item.get("date", "")) <= end]
    if audience == "customer":
        operations = [item for item in operations if item.get("customer_visible") is True]
    completed = [item for item in operations if item.get("status") == "completed"]
    pending = [item for item in operations if item.get("status") != "completed" or item.get("next_step")]
    lines = [
        f"# 项目周报（{start} 至 {end}）" + (" 客户讨论稿 待审核" if audience=="customer" else " 内部"),
        "",
        f"项目：{snapshot['project_id']}（{snapshot['purpose']}）",
        f"事实截止：{datetime.now(timezone.utc).date().isoformat()}",
        "",
        "## 已完成",
    ]
    lines.extend(f"- {item['date']} · {item['work_package_id']}：{item['summary']}" for item in completed)
    if not completed:
        lines.append("- 本周期暂无已登记的完成事实。")
    lines += ["", "## 待推进"]
    lines.extend(f"- {item['date']} · {item['work_package_id']}：{item.get('next_step') or item['summary']}" for item in pending)
    if not pending:
        lines.append("- 本周期暂无待推进事项。")
    if audience == "internal":
        risks = records.get(risks_id, {}).get("data", {}).get("items", [])
        lines += ["", "## 风险与问题"]
        lines.extend(f"- {item['id']} · {item['status']} · {item['title']}（责任人：{item['owner']}）" for item in risks)
        if not risks:
            lines.append("- 当前风险台账为空。")
        hours = records.get(hours_id, {}).get("data", {}).get("items", [])
        lines += ["", "## 内部工时与成本（内部）", "", f"- 周期工时记录数：{sum(start <= str(item.get('date', '')) <= end for item in hours)}"]
        summary = snapshot.get("cost_summary", {})
        lines.append(f"- 当前内部人工：{summary.get('internal_labor') or '未知'} {summary.get('currency', '')}".rstrip())
        lines.append(f"- 当前预测：{summary.get('forecast') or '未知'} {summary.get('currency', '')}".rstrip())
        if summary.get("gaps"):
            lines.append(f"- 成本证据缺口：{'；'.join(summary['gaps'])}")
        changes = [item for item in records.values() if item.get("kind") == "change"]
        lines += ["", "## 变更提案"]
        lines.extend(f"- {item['artifact_id']}：{item['data'].get('state')} · {item['data'].get('reason')}" for item in changes)
        if not changes:
            lines.append("- 当前没有变更提案。")
    source_records = [item for item in records.values() if item.get('kind') in {'plan','timesheets','risks','change'} or item.get('artifact_id')==PROGRESS_ID]
    if audience=='internal':
        lines += ['', '## 来源版本']
        lines.extend(f"- {item['artifact_id']} r{item['revision']} SHA256 {item['sha256']}；引用状态 {item['health']}" for item in source_records)
        if snapshot.get('alerts'):
            lines += ['', '## 需复核的引用', *['- '+alert for alert in snapshot['alerts']]]
    else:
        lines += ["", "## 对客边界", "", "本报告仅包含已登记的进度事实与待推进事项；内部工时、费率、成本和变更提案不属于对客内容。"]
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project", type=Path)
    parser.add_argument("command", choices=["state", "report"])
    parser.add_argument("--audience", choices=["internal", "customer"], default="internal")
    parser.add_argument("--period")
    args = parser.parse_args()
    result = state(args.project) if args.command == "state" else weekly_report(args.project, args.period, args.audience)
    if isinstance(result, str):
        print(result, end="")
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
