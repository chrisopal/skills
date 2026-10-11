"""Focused tests for phase-two resource, cost, and payment calculations."""

from decimal import Decimal
import importlib.util
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / "skills/delivery-orchestrator/scripts/runtime.py"
ECONOMICS = ROOT / "skills/delivery-orchestrator/scripts/economics.py"


def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


runtime = load(RUNTIME, "delivery_runtime_for_economics")
economics = load(ECONOMICS, "delivery_economics")


class EconomicsTests(unittest.TestCase):
    def test_legacy_remaining_labor_is_untouched(self):
        self.assertIsNone(economics.remaining_labor({"remaining_labor": "20"}, runtime.number))

    def test_remaining_work_counts_internal_only_and_keeps_unknown_rate_gap(self):
        data = {
            "remaining_labor": None,
            "remaining_work": [
                {"id": "RW1", "person": "A", "work_package_id": "WP1", "remaining_hours": "2", "rate": "100", "resource_type": "internal", "basis": "plan"},
                {"id": "RW2", "person": "Vendor", "work_package_id": "WP1", "remaining_hours": "10", "rate": "200", "resource_type": "outsourced", "basis": "settlement"},
                {"id": "RW3", "person": "B", "work_package_id": "WP2", "remaining_hours": "1", "rate": None, "resource_type": "internal", "basis": "rate pending"},
            ],
        }
        economics.validate("timesheets", data, runtime.number, runtime.rows)
        total, gaps = economics.remaining_labor(data, runtime.number)
        self.assertEqual(total, Decimal("200"))
        self.assertTrue(any("RW3" in gap for gap in gaps))

    def test_remaining_labor_cannot_be_double_counted(self):
        data = {
            "remaining_labor": "100",
            "remaining_work": [],
        }
        with self.assertRaisesRegex(ValueError, "remaining_labor"):
            economics.validate("timesheets", data, runtime.number, runtime.rows)

    def test_resource_summary_reports_overload_and_missing_capacity(self):
        result = economics.resource_summary({
            "capacities": [{"id": "C1", "person": "A", "period": "2026-10", "available_hours": "8"}],
            "allocations": [
                {"id": "A1", "person": "A", "period": "2026-10", "work_package_id": "WP1", "planned_hours": "10"},
                {"id": "A2", "person": "B", "period": "2026-10", "work_package_id": "WP2", "planned_hours": "3"},
            ],
        }, runtime.number)
        self.assertTrue(result["overloaded"])
        self.assertEqual(result["by_person_period"]["A|2026-10"]["planned_hours"], "10.00")
        self.assertTrue(any("capacity missing" in gap for gap in result["gaps"]))

    def test_partial_procurement_splits_without_double_counting(self):
        item = {
            "id": "PO1", "category": "purchase", "work_package_id": "WP1", "state": "partial",
            "amount": "150", "incurred_amount": "50", "remaining_amount": "100",
            "basis": "one purchase", "payment_status": "due", "procurement_ref": "PO-1",
        }
        economics.validate("costs", {"items": [item]}, runtime.number, runtime.rows)
        incurred, committed, estimate, gaps = economics.cost_parts(item, runtime.number)
        self.assertEqual((incurred, committed, estimate, gaps), (Decimal("50"), Decimal("100"), Decimal(0), []))

    def test_outsourcing_settlement_is_a_cost_item_only(self):
        item = {
            "id": "OUT1", "category": "outsourcing", "work_package_id": "WP1", "state": "incurred",
            "amount": "1600", "basis": "settlement", "payment_status": "paid",
        }
        self.assertEqual(economics.cost_parts(item, runtime.number)[:3], (Decimal("1600"), Decimal(0), Decimal(0)))
        self.assertEqual(economics.remaining_labor({"remaining_work": [{
            "id": "RW1", "person": "Vendor", "work_package_id": "WP1", "remaining_hours": "8", "rate": "200", "resource_type": "outsourced", "basis": "settlement",
        }]}, runtime.number)[0], Decimal(0))

    def test_missing_optional_input_is_valid_and_missing_cost_amount_is_gap(self):
        self.assertEqual(economics.resource_summary({}, runtime.number)["gaps"], [])
        parts = economics.cost_parts({"id": "C1", "state": "incurred", "amount": None}, runtime.number)
        self.assertTrue(parts[3])

    def test_duplicate_rows_are_rejected(self):
        data = {"capacities": [
            {"id": "C1", "person": "A", "period": "P", "available_hours": "1"},
            {"id": "C1", "person": "A", "period": "P", "available_hours": "1"},
        ]}
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            economics.validate("timesheets", data, runtime.number, runtime.rows)

    def test_duplicate_logical_resource_rows_are_rejected_even_with_new_ids(self):
        cases = [
            ({"capacities": [
                {"id": "C1", "person": "A", "period": "P", "available_hours": "1"},
                {"id": "C2", "person": "A", "period": "P", "available_hours": "2"},
            ]}, "capacity"),
            ({"allocations": [
                {"id": "A1", "person": "A", "period": "P", "work_package_id": "WP", "planned_hours": "1"},
                {"id": "A2", "person": "A", "period": "P", "work_package_id": "WP", "planned_hours": "2"},
            ]}, "allocation"),
            ({"remaining_labor": None, "remaining_work": [
                {"id": "R1", "person": "A", "work_package_id": "WP", "remaining_hours": "1", "rate": "10", "resource_type": "internal", "basis": "plan"},
                {"id": "R2", "person": "A", "work_package_id": "WP", "remaining_hours": "2", "rate": "10", "resource_type": "internal", "basis": "plan"},
            ]}, "remaining"),
        ]
        for data, label in cases:
            with self.subTest(label=label), self.assertRaisesRegex(ValueError, "Duplicate"):
                economics.validate("timesheets", data, runtime.number, runtime.rows)

    def test_unknown_internal_rate_is_not_zero(self):
        result = economics.remaining_labor({"remaining_work": [{
            "id": "RW1", "person": "A", "work_package_id": "WP1", "remaining_hours": "2", "rate": None, "resource_type": "internal", "basis": "pending",
        }]}, runtime.number)
        self.assertEqual(result[0], Decimal(0))
        self.assertTrue(result[1])

    def test_aggregate_and_detail_rows_are_rejected(self):
        items = [
            {"id": "PO1", "line_type": "aggregate", "category": "purchase", "work_package_id": "WP1", "state": "estimate", "amount": "100", "basis": "aggregate", "payment_status": "pending", "procurement_ref": "PO-1"},
            {"id": "PO1-D1", "line_type": "detail", "aggregate_of": "PO1", "category": "purchase", "work_package_id": "WP1", "state": "estimate", "amount": "100", "basis": "detail", "payment_status": "pending", "procurement_ref": "PO-1-D1"},
        ]
        with self.assertRaisesRegex(ValueError, "Aggregate and detail"):
            economics.validate("costs", {"items": items}, runtime.number, runtime.rows)

    def test_bad_partial_total_is_rejected(self):
        item = {"id": "PO1", "category": "purchase", "work_package_id": "WP1", "state": "partial", "amount": "99", "incurred_amount": "50", "remaining_amount": "100", "basis": "bad", "payment_status": "pending"}
        with self.assertRaisesRegex(ValueError, "must equal"):
            economics.validate("costs", {"items": [item]}, runtime.number, runtime.rows)

    def test_unknown_partial_amount_is_rejected(self):
        item = {"id": "PO1", "category": "purchase", "work_package_id": "WP1", "state": "partial", "amount": "100", "incurred_amount": None, "remaining_amount": "100", "basis": "pending", "payment_status": "pending"}
        with self.assertRaisesRegex(ValueError, "must be numeric"):
            economics.validate("costs", {"items": [item]}, runtime.number, runtime.rows)

    def test_payment_conditions_do_not_increase_cost(self):
        data = {
            "items": [{"id": "PO1", "category": "purchase", "work_package_id": "WP1", "state": "partial", "amount": "150", "incurred_amount": "50", "remaining_amount": "100", "basis": "purchase", "payment_status": "due"}],
            "payment_conditions": [
                {"id": "PAY1", "cost_item_id": "PO1", "amount": "50", "due_date": "2026-10-12", "condition": "delivery", "state": "paid", "evidence_refs": ["receipt-1"]},
                {"id": "PAY2", "cost_item_id": "PO1", "amount": "100", "due_date": "2026-11-01", "condition": "acceptance", "state": "pending", "evidence_refs": []},
            ],
        }
        economics.validate("costs", data, runtime.number, runtime.rows)
        summary = economics.payment_summary(data, runtime.number)
        self.assertEqual(summary["total"], "150.00")
        self.assertEqual(economics.cost_parts(data["items"][0], runtime.number)[0], Decimal("50"))

    def test_payment_condition_mapping_and_overpayment_are_rejected(self):
        data = {"items": [{"id": "PO1", "category": "purchase", "work_package_id": "WP1", "state": "incurred", "amount": "100", "basis": "purchase", "payment_status": "due"}], "payment_conditions": [{"id": "PAY1", "cost_item_id": "PO1", "amount": "101", "due_date": "2026-10-12", "condition": "delivery", "state": "due", "evidence_refs": ["e1"]}]}
        with self.assertRaisesRegex(ValueError, "exceed"):
            economics.validate("costs", data, runtime.number, runtime.rows)

    def test_known_payment_subtotal_rejected_even_with_unknown_condition(self):
        data = {"items": [{"id": "PO1", "category": "purchase", "work_package_id": "WP1", "state": "incurred", "amount": "100", "basis": "purchase", "payment_status": "due"}], "payment_conditions": [
            {"id": "PAY1", "cost_item_id": "PO1", "amount": "101", "due_date": "2026-10-12", "condition": "delivery", "state": "due", "evidence_refs": ["e1"]},
            {"id": "PAY2", "cost_item_id": "PO1", "amount": None, "due_date": "", "condition": "", "state": "pending", "evidence_refs": []},
        ]}
        with self.assertRaisesRegex(ValueError, "exceed"):
            economics.validate("costs", data, runtime.number, runtime.rows)


if __name__ == "__main__":
    unittest.main()
