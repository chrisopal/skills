"""Focused closure and warranty semantics before runtime integration."""

from __future__ import annotations

import copy
import importlib.util
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
CLOSURE = ROOT / "skills/delivery-orchestrator/scripts/closure.py"


def load_closure():
    spec = importlib.util.spec_from_file_location("delivery_closure", CLOSURE)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


closure = load_closure()


def rows(data, key, required=()):
    value = data.get(key)
    if not isinstance(value, list):
        raise ValueError(f"{key} must be a list")
    seen = set()
    for item in value:
        if not isinstance(item, dict) or any(field not in item for field in ("id", *required)):
            raise ValueError(f"{key} item requires id and {required}")
        if item["id"] in seen:
            raise ValueError(f"Duplicate/invalid item ID in {key}")
        seen.add(item["id"])
    return value


def ref(aid, revision=1, fill="a"):
    return {"artifact_id": aid, "revision": revision, "sha256": fill * 64}


class ClosureTests(unittest.TestCase):
    def setUp(self):
        self.refs = {
            "evidence": ref("EVID", fill="a"),
            "decision": ref("DEC", fill="b"),
            "terms": ref("TERMS", fill="c"),
            "transfer": ref("TRANSFER", fill="d"),
            "product": ref("PRODUCT", fill="e"),
        }
        self.upstream = [
            {"artifact_id": "EVID", "revision": 1, "sha256": "a" * 64, "kind": "evidence"},
            {"artifact_id": "DEC", "revision": 1, "sha256": "b" * 64, "kind": "minutes"},
            {"artifact_id": "TERMS", "revision": 1, "sha256": "c" * 64, "kind": "contract"},
            {"artifact_id": "TRANSFER", "revision": 1, "sha256": "d" * 64, "kind": "handover",
             "data": {"operations": {"state": "accepted"}, "open_items": []}},
            {"artifact_id": "PRODUCT", "revision": 1, "sha256": "e" * 64, "kind": "handover"},
        ]

    def artifact(self, data=None, *, status="ready", artifact_id="CLOSE"):
        data = copy.deepcopy(data or self.data())
        return {
            "artifact_id": artifact_id,
            "kind": "closure",
            "status": status,
            "data": data,
        }

    def data(self):
        return {
            "origin": "actual",
            "as_of": "2026-10-11",
            "obligations": [{
                "id": "O1", "title": "Return access card", "category": "handover",
                "owner": "delivery-owner", "state": "closed", "due_date": "2026-10-01",
                "evidence_refs": [self.refs["evidence"]], "recipient": None, "receipt_refs": [],
            }],
            "warranty": {
                "applicable": False, "reason": "Excluded by contract", "owner": None,
                "start_date": None, "end_date": None, "terms_refs": [self.refs["terms"]], "transfer_refs": [], "items": [],
            },
            "administration": {"state": "closed", "decision_refs": [self.refs["decision"]]},
            "settlement": {"state": "reconciled", "evidence_refs": [self.refs["evidence"]]},
            "resources": [{"id": "R1", "owner": "delivery-owner", "state": "released",
                           "reason": "", "evidence_refs": [self.refs["evidence"]]}],
            "archive": [{"id": "A1", "artifact_ref": self.refs["product"], "owner": "records-owner",
                         "classification": "project-record", "retention_until": "2031-10-11"}],
            "lessons": [{"id": "L1", "observation": "Handover was clear", "action": "Reuse checklist",
                         "owner": "delivery-owner"}],
        }

    def validate(self, data=None, *, purpose="internal", upstream=None):
        closure.validate(self.artifact(data), upstream if upstream is not None else self.upstream,
                         rows, lambda value, label, unknown=False: value, purpose)

    def test_complete_actual_closure_has_four_independent_positive_statuses(self):
        self.validate()
        result = closure.gate(self.artifact(), self.upstream, "current", "2026-10-11")
        self.assertTrue(all(result[key] for key in (
            "administrative_closed", "warranty_transferred", "warranty_ended", "fully_discharged", "ready")))

    def test_simulation_origin_is_rejected_for_real_project(self):
        data = self.data()
        data["origin"] = "simulation"
        with self.assertRaisesRegex(ValueError, "real project"):
            self.validate(data)

    def test_as_of_and_warranty_dates_are_strict_and_ordered(self):
        data = self.data()
        data["as_of"] = "2026-02-30"
        with self.assertRaisesRegex(ValueError, "calendar date"):
            self.validate(data)
        data = self.data()
        data["warranty"] = {
            "applicable": True, "reason": "Contract warranty", "owner": "support-owner",
            "start_date": "2026-10-11", "end_date": "2026-10-01", "terms_refs": [self.refs["terms"]],
            "transfer_refs": [], "items": [],
        }
        with self.assertRaisesRegex(ValueError, "on or before"):
            self.validate(data)

    def test_transferred_and_closed_obligations_require_their_evidence(self):
        data = self.data()
        data["obligations"][0]["state"] = "transferred"
        data["obligations"][0]["recipient"] = "customer-owner"
        with self.assertRaisesRegex(ValueError, "receipt evidence"):
            self.validate(data)
        data = self.data()
        data["obligations"][0]["state"] = "closed"
        data["obligations"][0]["evidence_refs"] = []
        with self.assertRaisesRegex(ValueError, "evidence_refs"):
            self.validate(data)

    def test_archive_must_bind_a_real_upstream_product_and_not_self(self):
        data = self.data()
        data["archive"][0]["artifact_ref"] = self.refs["evidence"]
        with self.assertRaisesRegex(ValueError, "actual product"):
            self.validate(data)
        data = self.data()
        data["archive"][0]["artifact_ref"] = ref("CLOSE", fill="f")
        with self.assertRaisesRegex(ValueError, "itself"):
            self.validate(data, upstream=self.upstream + [{"artifact_id": "CLOSE", "revision": 1, "sha256": "f" * 64, "kind": "closure"}])

    def test_transferred_open_obligation_can_allow_administrative_close(self):
        data = self.data()
        data["obligations"][0].update(state="transferred", recipient="customer-owner", receipt_refs=[self.refs["transfer"]])
        result = closure.gate(self.artifact(data), self.upstream, "current", "2026-10-11")
        self.assertTrue(result["administrative_closed"])
        self.assertFalse(result["fully_discharged"])

    def test_open_obligation_blocks_administrative_close(self):
        data = self.data()
        data["obligations"][0]["state"] = "open"
        result = closure.gate(self.artifact(data), self.upstream, "current", "2026-10-11")
        self.assertFalse(result["administrative_closed"])
        self.assertTrue(any("Open obligation" in reason for reason in result["reasons"]))

    def test_warranty_before_end_blocks_full_discharge_even_when_items_closed(self):
        data = self.data()
        data["warranty"] = {
            "applicable": True, "reason": "Contract warranty", "owner": "support-owner",
            "start_date": "2026-10-01", "end_date": "2027-10-01", "terms_refs": [self.refs["terms"]],
            "transfer_refs": [self.refs["transfer"]], "items": [],
        }
        result = closure.gate(self.artifact(data), self.upstream, "current", "2026-10-11")
        self.assertTrue(result["administrative_closed"])
        self.assertTrue(result["warranty_transferred"])
        self.assertFalse(result["warranty_ended"])
        self.assertFalse(result["fully_discharged"])
        self.assertTrue(any("has not passed" in reason for reason in result["reasons"]))

    def test_open_warranty_item_blocks_after_warranty_end(self):
        data = self.data()
        data["warranty"] = {
            "applicable": True, "reason": "Contract warranty", "owner": "support-owner",
            "start_date": "2026-01-01", "end_date": "2026-10-01", "terms_refs": [self.refs["terms"]],
            "transfer_refs": [self.refs["transfer"]], "items": [{
                "id": "W1", "title": "Follow-up defect", "owner": "support-owner", "state": "open", "evidence_refs": [],
            }],
        }
        result = closure.gate(self.artifact(data), self.upstream, "current", "2026-10-11")
        self.assertFalse(result["warranty_ended"])
        self.assertFalse(result["fully_discharged"])
        self.assertTrue(any("Open warranty item" in reason for reason in result["reasons"]))

    def test_unknown_dates_remain_gate_gaps(self):
        data = self.data()
        data["obligations"][0]["due_date"] = None
        data["archive"][0]["retention_until"] = None
        result = closure.gate(self.artifact(data), self.upstream, "current", "2026-10-11")
        self.assertFalse(result["fully_discharged"])
        self.assertTrue(any("due date is unknown" in reason for reason in result["reasons"]))
        self.assertTrue(any("retention date is unknown" in reason for reason in result["reasons"]))

    def test_stale_or_draft_artifact_cannot_be_ready(self):
        result = closure.gate(self.artifact(status="draft"), self.upstream, "stale", "2026-10-11")
        self.assertFalse(result["ready"])
        self.assertFalse(result["fully_discharged"])
        self.assertTrue(any("stale" in reason for reason in result["reasons"]))

    def test_revision_cannot_delete_prior_closed_records(self):
        previous = self.data()
        current = copy.deepcopy(previous)
        current["obligations"] = []
        with self.assertRaisesRegex(ValueError, "cannot be deleted"):
            closure.check_revision(previous, current)

    def test_revision_reopen_requires_correction_and_evidence(self):
        previous = self.data()
        current = copy.deepcopy(previous)
        current["obligations"][0]["state"] = "open"
        with self.assertRaisesRegex(ValueError, "correction_reason"):
            closure.check_revision(previous, current)
        current["obligations"][0].update(correction_reason="Verified defect remains", evidence_refs=[self.refs["evidence"]])
        self.assertTrue(closure.check_revision(previous, current))

    def test_reference_categories_are_checked(self):
        data = self.data()
        data["administration"]["decision_refs"] = [self.refs["terms"]]
        with self.assertRaisesRegex(ValueError, "incompatible artifact kind"):
            self.validate(data)

    def test_reference_semantics_accept_runtime_payload_without_duplicate_hash(self):
        upstream = copy.deepcopy(self.upstream)
        for item in upstream:
            item.pop("sha256")
        self.validate(upstream=upstream)
        data = self.data()
        data["warranty"] = {
            "applicable": True, "reason": "Contract warranty", "owner": "support-owner",
            "start_date": "2026-10-01", "end_date": "2027-10-01", "terms_refs": [self.refs["evidence"]],
            "transfer_refs": [], "items": [],
        }
        with self.assertRaisesRegex(ValueError, "incompatible artifact kind"):
            self.validate(data)


if __name__ == "__main__":
    unittest.main()
