"""Pure resource and cost calculations for the delivery runtime.

The runtime owns project/artifact loading and stable ledger identity.  This
module only validates the optional phase-two ledger sections and calculates
views from an already loaded data dictionary.  ``number`` and ``rows`` are
passed in by the caller so the module shares the runtime's numeric and row
validation rules without importing the runtime.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Callable


__all__ = [
    "validate",
    "remaining_labor",
    "resource_summary",
    "cost_parts",
    "payment_summary",
]


Number = Callable[..., Decimal | None]
Rows = Callable[..., list[dict[str, Any]]]


def _number(number: Number, value: Any, label: str, *, unknown: bool = True) -> Decimal | None:
    """Call the runtime numeric callback while allowing explicitly unknown values."""
    if value is None and unknown:
        return None
    return number(value, label, unknown)


def _money(value: Decimal | None) -> str | None:
    return None if value is None else str(value.quantize(Decimal("0.01")))


def _rows(data: dict[str, Any], key: str, required: tuple[str, ...]) -> list[dict[str, Any]]:
    value = data.get(key)
    if not isinstance(value, list):
        raise ValueError(f"{key} must be a list")
    seen: set[str] = set()
    result: list[dict[str, Any]] = []
    for item in value:
        if not isinstance(item, dict) or any(name not in item for name in ("id", *required)):
            raise ValueError(f"{key} item requires id and {required}")
        item_id = item["id"]
        if not isinstance(item_id, str) or not item_id or item_id in seen:
            raise ValueError(f"Duplicate/invalid item ID in {key}")
        seen.add(item_id)
        result.append(item)
    return result


def _optional_rows(data: dict[str, Any], key: str, required: tuple[str, ...]) -> list[dict[str, Any]]:
    if key not in data:
        return []
    return _rows(data, key, required)


def _cost_ref(item: dict[str, Any]) -> str:
    refs = {
        str(item[key]).strip()
        for key in ("external_ref", "travel_or_expense_ref", "procurement_ref")
        if item.get(key)
    }
    if len(refs) > 1:
        raise ValueError("Conflicting logical cost references; use one aggregate stable item")
    return next(iter(refs), str(item.get("id", "")))


def _validate_resource_sections(data: dict[str, Any], number: Number, rows: Rows) -> None:
    capacities = rows(data, "capacities", ("person", "period", "available_hours")) if "capacities" in data else []
    allocations = rows(data, "allocations", ("person", "period", "work_package_id", "planned_hours")) if "allocations" in data else []
    remaining = rows(data, "remaining_work", ("person", "work_package_id", "remaining_hours", "rate", "resource_type", "basis")) if "remaining_work" in data else []
    capacity_keys: set[tuple[str, str]] = set()
    allocation_keys: set[tuple[str, str, str]] = set()
    remaining_keys: set[tuple[str, str]] = set()
    for item in capacities:
        if not item.get("person") or not item.get("period"):
            raise ValueError("Capacity requires nonempty person and period")
        key = (str(item["person"]), str(item["period"]))
        if key in capacity_keys:
            raise ValueError("Duplicate capacity for person/period")
        capacity_keys.add(key)
        _number(number, item.get("available_hours"), f"capacity {item['id']}.available_hours")
    for item in allocations:
        if not item.get("person") or not item.get("period") or not item.get("work_package_id"):
            raise ValueError("Allocation requires nonempty person, period and work_package_id")
        key = (str(item["person"]), str(item["period"]), str(item["work_package_id"]))
        if key in allocation_keys:
            raise ValueError("Duplicate allocation for person/period/work_package_id")
        allocation_keys.add(key)
        _number(number, item.get("planned_hours"), f"allocation {item['id']}.planned_hours")
    for item in remaining:
        if not item.get("person") or not item.get("work_package_id") or not item.get("basis"):
            raise ValueError("Remaining work requires nonempty person, work_package_id and basis")
        key = (str(item["person"]), str(item["work_package_id"]))
        if key in remaining_keys:
            raise ValueError("Duplicate remaining work for person/work_package_id")
        remaining_keys.add(key)
        _number(number, item.get("remaining_hours"), f"remaining_work {item['id']}.remaining_hours")
        _number(number, item.get("rate"), f"remaining_work {item['id']}.rate")
        if item.get("resource_type") not in {"internal", "outsourced"}:
            raise ValueError("Unknown remaining_work resource_type")
    if "remaining_labor" in data:
        _number(number, data.get("remaining_labor"), "remaining_labor")
    if "remaining_work" in data and ("remaining_labor" not in data or data.get("remaining_labor") is not None):
        raise ValueError("remaining_labor must be null when remaining_work is supplied")


def _validate_payment_conditions(data: dict[str, Any], number: Number, rows: Rows) -> None:
    if "payment_conditions" not in data:
        return
    items = rows(data, "items", ())
    item_ids = {item["id"] for item in items}
    conditions = rows(data, "payment_conditions", ("cost_item_id", "amount", "due_date", "condition", "state", "evidence_refs"))
    totals: dict[str, Decimal] = {}
    costs: dict[str, Decimal | None] = {}
    for item in items:
        costs[item["id"]] = _number(number, item.get("amount"), f"cost {item['id']}.amount")
    for item in conditions:
        cost_id = item["cost_item_id"]
        if cost_id not in item_ids:
            raise ValueError(f"Payment condition maps to unknown cost item: {cost_id}")
        amount = _number(number, item.get("amount"), f"payment condition {item['id']}.amount")
        state = item.get("state")
        if state not in {"pending", "due", "paid"}:
            raise ValueError("Unknown payment condition state")
        if state in {"due", "paid"}:
            if not item.get("condition") or not item.get("due_date") or not item.get("evidence_refs"):
                raise ValueError("Due/paid payment condition needs condition, due_date and evidence_refs")
        if amount is not None:
            totals[cost_id] = totals.get(cost_id, Decimal(0)) + amount
    for cost_id, total in totals.items():
        cost_total = costs[cost_id]
        if cost_total is not None and total > cost_total:
            raise ValueError(f"Payment conditions exceed cost item total: {cost_id}")


def _validate_cost_items(data: dict[str, Any], number: Number, rows: Rows) -> None:
    items = rows(data, "items", ("category", "work_package_id", "state", "amount", "basis", "payment_status"))
    refs: set[str] = set()
    aggregate_ids: set[str] = set()
    detail_parent_ids: set[str] = set()
    for item in items:
        if item.get("category") not in {"travel", "purchase", "outsourcing", "other"}:
            raise ValueError("Costs use non-labor categories")
        state = item.get("state")
        if state not in {"estimate", "committed", "incurred", "partial"}:
            raise ValueError("Unknown cost state")
        ref = _cost_ref(item)
        if ref in refs:
            raise ValueError("Duplicate logical cost reference; revise one stable cost item")
        refs.add(ref)
        if not item.get("basis"):
            raise ValueError("Cost requires nonempty basis")
        if state == "partial":
            if "incurred_amount" not in item or "remaining_amount" not in item:
                raise ValueError("Partial cost requires incurred_amount and remaining_amount")
            incurred = _number(number, item.get("incurred_amount"), f"cost {item['id']}.incurred_amount", unknown=False)
            remaining = _number(number, item.get("remaining_amount"), f"cost {item['id']}.remaining_amount", unknown=False)
            amount = _number(number, item.get("amount"), f"cost {item['id']}.amount", unknown=False)
            if incurred is None or remaining is None or amount is None:
                raise ValueError("Partial cost amounts must be known")
            if amount != incurred + remaining:
                raise ValueError("Partial cost amount must equal incurred_amount + remaining_amount")
        else:
            _number(number, item.get("amount"), f"cost {item['id']}.amount")
        marker = item.get("line_type") or item.get("entry_type") or item.get("aggregation") or item.get("record_type")
        if item.get("is_aggregate") is True or item.get("aggregate") is True:
            marker = "aggregate"
        elif item.get("is_detail") is True or item.get("detail") is True:
            marker = "detail"
        if marker == "aggregate":
            aggregate_ids.add(item["id"])
        elif marker == "detail":
            detail_parent_ids.add(str(item.get("aggregate_of") or item.get("aggregate_id") or item.get("detail_of") or item.get("parent_cost_id") or item.get("parent_id") or ""))
        parent = item.get("aggregate_of") or item.get("aggregate_id") or item.get("detail_of") or item.get("parent_cost_id") or item.get("parent_id")
        if parent:
            detail_parent_ids.add(str(parent))
    if aggregate_ids & detail_parent_ids:
        raise ValueError("Aggregate and detail cost rows cannot be combined")
    _validate_payment_conditions(data, number, rows)


def validate(kind: str, data: dict[str, Any], number: Number, rows: Rows) -> None:
    """Validate phase-two economics fields, raising ``ValueError`` on unsafe data."""
    if not isinstance(data, dict):
        raise ValueError("Economic data must be an object")
    if kind == "timesheets":
        _validate_resource_sections(data, number, rows)
    elif kind == "costs":
        _validate_cost_items(data, number, rows)
    else:
        return


def remaining_labor(data: dict[str, Any], number: Number) -> tuple[Decimal, list[str]] | None:
    """Return internal remaining labor cost and gaps, or ``None`` for legacy data."""
    if "remaining_work" not in data:
        return None
    records = _rows(data, "remaining_work", ("person", "work_package_id", "remaining_hours", "rate", "resource_type", "basis"))
    total = Decimal(0)
    gaps: list[str] = []
    for item in records:
        hours = _number(number, item.get("remaining_hours"), f"remaining_work {item['id']}.remaining_hours")
        rate = _number(number, item.get("rate"), f"remaining_work {item['id']}.rate")
        if item.get("resource_type") not in {"internal", "outsourced"}:
            gaps.append(f"{item['id']}: unknown resource_type")
            continue
        if item["resource_type"] == "outsourced":
            continue
        if hours is None:
            gaps.append(f"{item['id']}: remaining hours unknown")
        if rate is None:
            gaps.append(f"{item['id']}: rate unknown")
        if hours is not None and rate is not None:
            total += hours * rate
    return total, gaps


def resource_summary(data: dict[str, Any], number: Number) -> dict[str, Any]:
    """Summarize capacity and planned allocation by person and period."""
    capacities = _optional_rows(data, "capacities", ("person", "period", "available_hours"))
    allocations = _optional_rows(data, "allocations", ("person", "period", "work_package_id", "planned_hours"))
    grouped: dict[tuple[str, str], dict[str, Any]] = {}
    gaps: list[str] = []
    for item in capacities:
        key = (str(item["person"]), str(item["period"]))
        entry = grouped.setdefault(key, {"available_hours": Decimal(0), "planned_hours": Decimal(0), "capacity_known": True, "planned_known": True, "allocation_count": 0})
        value = _number(number, item.get("available_hours"), f"capacity {item['id']}.available_hours")
        if value is None:
            entry["capacity_known"] = False
            gaps.append(f"{item['id']}: available capacity unknown")
        elif entry["capacity_known"]:
            entry["available_hours"] += value
    for item in allocations:
        key = (str(item["person"]), str(item["period"]))
        entry = grouped.setdefault(key, {"available_hours": Decimal(0), "planned_hours": Decimal(0), "capacity_known": False, "planned_known": True, "allocation_count": 0})
        entry["allocation_count"] += 1
        value = _number(number, item.get("planned_hours"), f"allocation {item['id']}.planned_hours")
        if value is None:
            entry["planned_known"] = False
            gaps.append(f"{item['id']}: planned hours unknown")
        elif entry["planned_known"]:
            entry["planned_hours"] += value
        if key not in {(str(x["person"]), str(x["period"])) for x in capacities}:
            gaps.append(f"{item['id']}: capacity missing for {key[0]}/{key[1]}")
    by_person_period: dict[str, dict[str, Any]] = {}
    total_capacity = Decimal(0)
    total_planned = Decimal(0)
    overloaded = False
    for key, entry in sorted(grouped.items()):
        available = entry["available_hours"] if entry["capacity_known"] else None
        planned = entry["planned_hours"] if entry["planned_known"] else None
        over = bool(available is not None and planned is not None and planned > available)
        overloaded = overloaded or over
        if available is not None:
            total_capacity += available
        if planned is not None:
            total_planned += planned
        by_person_period[f"{key[0]}|{key[1]}"] = {
            "person": key[0], "period": key[1], "available_hours": _money(available),
            "load_hours": _money(planned), "planned_hours": _money(planned), "overloaded": over,
            "allocation_count": entry["allocation_count"],
        }
    return {
        "capacity_hours": _money(total_capacity),
        "load_hours": _money(total_planned),
        "planned_hours": _money(total_planned),
        "by_person_period": by_person_period,
        "overloaded": overloaded,
        "complete": not gaps,
        "gaps": gaps,
    }


def cost_parts(item: dict[str, Any], number: Number) -> tuple[Decimal, Decimal, Decimal, list[str]]:
    """Split a cost row into incurred, committed, estimate and gaps."""
    incurred = committed = estimate = Decimal(0)
    gaps: list[str] = []
    state = item.get("state")
    if state == "partial":
        first = _number(number, item.get("incurred_amount"), f"cost {item.get('id', '?')}.incurred_amount")
        second = _number(number, item.get("remaining_amount"), f"cost {item.get('id', '?')}.remaining_amount")
        amount = _number(number, item.get("amount"), f"cost {item.get('id', '?')}.amount")
        if first is None or second is None or amount is None:
            gaps.append(f"{item.get('id', '?')}: partial cost amount unknown")
        elif amount != first + second:
            gaps.append(f"{item.get('id', '?')}: partial cost total mismatch")
        else:
            incurred, committed = first, second
        return incurred, committed, estimate, gaps
    amount = _number(number, item.get("amount"), f"cost {item.get('id', '?')}.amount")
    if amount is None:
        gaps.append(f"{item.get('id', '?')}: expense amount unknown")
    elif state == "incurred":
        incurred = amount
    elif state == "committed":
        committed = amount
    elif state == "estimate":
        estimate = amount
    else:
        gaps.append(f"{item.get('id', '?')}: unknown cost state")
    return incurred, committed, estimate, gaps


def payment_summary(data: dict[str, Any], number: Number) -> dict[str, Any]:
    """Summarize payment conditions independently from cost totals."""
    conditions = _optional_rows(data, "payment_conditions", ("cost_item_id", "amount", "due_date", "condition", "state", "evidence_refs"))
    items = _optional_rows(data, "items", ())
    costs = {item["id"]: item for item in items}
    gaps: list[str] = []
    by_cost: dict[str, dict[str, Any]] = {}
    totals = {"pending": Decimal(0), "due": Decimal(0), "paid": Decimal(0)}
    for item in conditions:
        cost_id = item["cost_item_id"]
        if cost_id not in costs:
            gaps.append(f"{item['id']}: unknown cost item {cost_id}")
            continue
        amount = _number(number, item.get("amount"), f"payment condition {item['id']}.amount")
        state = item.get("state")
        if state not in totals:
            gaps.append(f"{item['id']}: unknown payment condition state")
            continue
        if state in {"due", "paid"} and (not item.get("condition") or not item.get("due_date") or not item.get("evidence_refs")):
            gaps.append(f"{item['id']}: due/paid condition evidence incomplete")
        row = by_cost.setdefault(cost_id, {"amount": Decimal(0), "known": True, "conditions": []})
        row["conditions"].append(item["id"])
        if amount is None:
            row["known"] = False
            gaps.append(f"{item['id']}: payment amount unknown")
            continue
        row["amount"] += amount
        totals[state] += amount
    for cost_id, row in by_cost.items():
        total = _number(number, costs[cost_id].get("amount"), f"cost {cost_id}.amount")
        if row["known"] and total is not None and row["amount"] > total:
            gaps.append(f"{cost_id}: payment conditions exceed cost total")
        row["amount"] = _money(row["amount"])
        del row["known"]
    return {
        "by_cost_item": by_cost,
        "pending": _money(totals["pending"]),
        "due": _money(totals["due"]),
        "paid": _money(totals["paid"]),
        "total": _money(sum(totals.values(), Decimal(0))),
        "complete": not gaps,
        "gaps": gaps,
    }
