"""Evidence and boundary tests for the host-model tender router."""

from __future__ import annotations

import copy
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import bidkit
import tender_router


class TenderRouterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.project = self.root / "project"
        bidkit.init_project(self.project, "ROUTE-TEST")
        self.source = self.project / "inputs/tender.md"
        self.source.write_text(
            "项目分为两个标包，面向智能工厂。\n"
            "本标包采购设备并配套软件平台、接口集成和持续运维服务。\n"
            "设备型号和数量按清单交付，软件与集成范围以接口测试记录验收。\n"
            "另一个标包只采购软件平台和接口集成。\n",
            encoding="utf-8",
        )
        self.intake_path = self.project / "artifacts/01-source-intake.json"
        self.write_intake()

    def write_intake(self, *, project_id: str = "ROUTE-TEST", coverage: str = "complete", role: str = "main") -> dict:
        source_hash = tender_router.sha256(self.source)
        registry = {
            "sources": [
                {
                    "source_id": "SRC-001",
                    "revision": 1,
                    "relative_path": "inputs/tender.md",
                    "sha256": source_hash,
                    "bytes": self.source.stat().st_size,
                    "role": role,
                }
            ]
        }
        (self.project / "inputs/source-registry.json").write_text(
            json.dumps(registry, ensure_ascii=False), encoding="utf-8"
        )
        intake = {
            "schema_version": "1.0",
            "skill_id": "bid-source-intake",
            "project_id": project_id,
            "artifact_id": "ART-01",
            "revision": 1,
            "status": "needs_review" if coverage != "complete" else "ready",
            "inputs": [
                {
                    "artifact_id": "SRC-001",
                    "revision": 1,
                    "relative_path": "inputs/tender.md",
                    "sha256": source_hash,
                }
            ],
            "summary": "synthetic",
            "data": {
                "documents": [
                    {
                        "source_id": "SRC-001",
                        "filename": "tender.md",
                        "relative_path": "inputs/tender.md",
                        "sha256": source_hash,
                        "bytes": self.source.stat().st_size,
                        "role": role,
                        "revision": 1,
                        "duplicate_group": None,
                        "status": "parsed",
                    }
                ],
                "blocks": [
                    {"block_id": "SRC-001-B001", "source_id": "SRC-001", "location": "L1", "page": None, "text": "项目分为两个标包，面向智能工厂。", "method": "native"},
                    {"block_id": "SRC-001-B002", "source_id": "SRC-001", "location": "L2", "page": None, "text": "本标包采购设备并配套软件平台、接口集成和持续运维服务。", "method": "native"},
                    {"block_id": "SRC-001-B003", "source_id": "SRC-001", "location": "L3", "page": None, "text": "设备型号和数量按清单交付，软件与集成范围以接口测试记录验收。", "method": "native"},
                    {"block_id": "SRC-001-B004", "source_id": "SRC-001", "location": "L4", "page": None, "text": "另一个标包只采购软件平台和接口集成。", "method": "native"},
                ],
                "page_audit": [],
                "coverage": coverage,
            },
            "warnings": ["synthetic source"],
            "blockers": [],
        }
        self.intake_path.write_text(json.dumps(intake, ensure_ascii=False), encoding="utf-8")
        return intake

    def evidence(self, location: str, quote: str) -> dict:
        return {"source_id": "SRC-001", "location": location, "quote": quote}

    def decision(self, *, structure: str = "single", lots: list[dict] | None = None) -> dict:
        if lots is None:
            lots = [
                {
                    "lot_id": "LOT-1",
                    "lot_name": "综合标包",
                    "mode": "mixed",
                    "components": [
                        {
                            "category": "hardware_supply",
                            "rationale": "设备型号和数量属于独立供货范围。",
                            "evidence": [self.evidence("L3", "设备型号和数量按清单交付")],
                        },
                        {
                            "category": "software_integration",
                            "rationale": "平台、接口集成和测试是独立软件交付范围。",
                            "evidence": [self.evidence("L2", "软件平台、接口集成")],
                        },
                        {
                            "category": "service_outsourcing",
                            "rationale": "持续运维服务是单独描述的持续服务范围。",
                            "evidence": [self.evidence("L2", "持续运维服务")],
                        },
                    ],
                    "scenario_tags": ["smart_factory"],
                    "scenario_evidence": [
                        {
                            "tag": "smart_factory",
                            "rationale": "原文明确说明智能工厂场景。",
                            "evidence": [self.evidence("L1", "智能工厂")],
                        }
                    ],
                    "unknowns": [],
                }
            ]
        for lot in lots:
            lot.setdefault("scenario_evidence", [])
        intake_hash = tender_router.sha256(self.intake_path)
        return {
            "schema_version": "1.0",
            "project_id": "ROUTE-TEST",
            "intake_sha256": intake_hash,
            "catalog_sha256": tender_router.sha256(tender_router.CATALOG_PATH),
            "lot_structure": structure,
            "lot_structure_evidence": [self.evidence("L1", "项目分为两个标包")],
            "lots": lots,
        }

    def write_decision(self, decision: dict, name: str = "work/classification.json") -> Path:
        path = self.project / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(decision, ensure_ascii=False), encoding="utf-8")
        return path

    def route(self, decision: dict | None = None, out: str = "artifacts/02-tender-routing.json") -> dict:
        decision_path = self.write_decision(decision or self.decision())
        return tender_router.compose_route(self.project, self.intake_path, decision_path, self.project / out)

    def test_brief_preserves_full_blocks_catalog_contract_and_partial_warning(self) -> None:
        self.write_intake(coverage="partial")
        output = tender_router.build_brief(self.project, self.intake_path, self.project / "work/routing-brief.json")
        self.assertEqual(output["project_id"], "ROUTE-TEST")
        self.assertEqual(output["skill_id"], "bid-project-profile")
        self.assertEqual(output["intake_sha256"], tender_router.sha256(self.intake_path))
        self.assertEqual(len(output["source_blocks"]), 4)
        self.assertEqual(len(output["catalog"]["templates"]), 4)
        self.assertIn("decision_contract", output)
        self.assertTrue(any("partial" in warning for warning in output["warnings"]))
        self.assertEqual(output["inputs"][0]["artifact_id"], "ART-01")
        self.assertEqual(output["inputs"][0]["relative_path"], "artifacts/01-source-intake.json")
        self.assertEqual(output["source_inventory"][0]["role"], "main")
        self.assertEqual(len(output["classification_blocks"]), 4)

    def test_route_binds_intake_and_decision_file_hashes(self) -> None:
        result = self.route(self.decision())
        self.assertEqual(result["skill_id"], "bid-project-profile")
        self.assertEqual(result["inputs"][0]["artifact_id"], "ART-01")
        self.assertEqual(result["inputs"][1]["artifact_id"], "HOST-CLASSIFICATION")
        self.assertEqual(result["inputs"][1]["sha256"], tender_router.sha256(self.project / "work/classification.json"))
        self.assertEqual(result["decision_sha256"], result["inputs"][1]["sha256"])

    def test_pure_software_stays_single_despite_hardware_mention(self) -> None:
        lot = self.decision()["lots"][0]
        lot["components"] = [
            {
                "category": "software_integration",
                "rationale": "软件平台和接口集成是采购范围。",
                "evidence": [self.evidence("L4", "只采购软件平台和接口集成")],
            }
        ]
        lot["mode"] = "single"
        lot["scenario_tags"] = []
        lot["scenario_evidence"] = []
        decision = self.decision(structure="single", lots=[lot])
        decision["lot_structure_evidence"] = [self.evidence("L4", "只采购软件平台和接口集成")]
        result = self.route(decision)
        self.assertEqual(result["lots"][0]["mode"], "single")
        self.assertEqual(result["selected_template_categories"], ["software_integration"])

    def test_mixed_categories_compose_three_domain_templates(self) -> None:
        result = self.route(self.decision())
        self.assertEqual(result["status"], "needs_review")
        self.assertEqual({item["category"] for item in result["lots"][0]["selected_templates"]}, {"hardware_supply", "software_integration", "service_outsourcing"})
        self.assertEqual(result["extraction_plan"]["source_kind"], "instruction")

    def test_separate_lots_are_not_misreported_as_mixed(self) -> None:
        first = copy.deepcopy(self.decision()["lots"][0])
        first.update(
            lot_id="LOT-1",
            lot_name="设备标包",
            mode="single",
            components=[first["components"][0]],
            scenario_tags=[],
            scenario_evidence=[],
            unknowns=[],
        )
        second = {
            "lot_id": "LOT-2",
            "lot_name": "软件标包",
            "mode": "single",
            "components": [{"category": "software_integration", "rationale": "独立软件标包。", "evidence": [self.evidence("L4", "只采购软件平台和接口集成")]}],
            "scenario_tags": [],
            "unknowns": [],
        }
        decision = self.decision(structure="multiple", lots=[first, second])
        result = self.route(decision)
        self.assertEqual(result["classification"]["lot_structure"], "multiple")
        self.assertEqual([lot["mode"] for lot in result["lots"]], ["single", "single"])

    def test_invalid_category_mode_and_duplicate_are_rejected(self) -> None:
        invalid_category = self.decision()
        invalid_category["lots"][0]["components"][0]["category"] = "smart_factory"
        with self.assertRaises(ValueError):
            self.route(invalid_category)
        invalid_mode = self.decision()
        invalid_mode["lots"][0]["mode"] = "single"
        with self.assertRaises(ValueError):
            self.route(invalid_mode)
        duplicate = self.decision()
        duplicate["lots"][0]["components"].append(copy.deepcopy(duplicate["lots"][0]["components"][0]))
        with self.assertRaises(ValueError):
            self.route(duplicate)

    def test_catalog_hash_is_required_and_must_match_current_catalog(self) -> None:
        missing = self.decision()
        del missing["catalog_sha256"]
        with self.assertRaises(ValueError):
            self.route(missing, out="artifacts/missing-catalog-hash.json")
        stale = self.decision()
        stale["catalog_sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "catalog"):
            self.route(stale, out="artifacts/stale-catalog-hash.json")

    def test_scenario_tags_require_exact_evidence_tag_set(self) -> None:
        missing = self.decision()
        missing["lots"][0]["scenario_evidence"] = []
        with self.assertRaisesRegex(ValueError, "scenario_evidence与scenario_tags"):
            self.route(missing, out="artifacts/missing-scenario-evidence.json")
        forged = self.decision()
        forged["lots"][0]["scenario_evidence"][0]["evidence"][0]["quote"] = "伪造场景"
        with self.assertRaises(ValueError):
            self.route(forged, out="artifacts/forged-scenario-evidence.json")

    def test_source_documents_inputs_and_blocks_must_be_bound(self) -> None:
        intake = json.loads(self.intake_path.read_text(encoding="utf-8"))
        intake["inputs"][0]["artifact_id"] = "SRC-OTHER"
        self.intake_path.write_text(json.dumps(intake, ensure_ascii=False), encoding="utf-8")
        with self.assertRaises(ValueError):
            tender_router.build_brief(self.project, self.intake_path, self.project / "work/mismatch.json")

        self.write_intake()
        intake = json.loads(self.intake_path.read_text(encoding="utf-8"))
        intake["data"]["blocks"].append(
            {"block_id": "B-UNKNOWN", "source_id": "SRC-404", "location": "L1", "page": None, "text": "未登记", "method": "native"}
        )
        self.intake_path.write_text(json.dumps(intake, ensure_ascii=False), encoding="utf-8")
        with self.assertRaises(ValueError):
            tender_router.build_brief(self.project, self.intake_path, self.project / "work/block-mismatch.json")

        for field, value in (("relative_path", "inputs/other.md"), ("sha256", "f" * 64), ("revision", 2)):
            with self.subTest(field=field):
                self.write_intake()
                intake = json.loads(self.intake_path.read_text(encoding="utf-8"))
                intake["data"]["documents"][0][field] = value
                self.intake_path.write_text(json.dumps(intake, ensure_ascii=False), encoding="utf-8")
                with self.assertRaises(ValueError):
                    tender_router.build_brief(self.project, self.intake_path, self.project / f"work/{field}-mismatch.json")

        self.write_intake(role="supplier")
        intake = json.loads(self.intake_path.read_text(encoding="utf-8"))
        intake["data"]["documents"][0]["role"] = "main"
        self.intake_path.write_text(json.dumps(intake, ensure_ascii=False), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "source-registry"):
            tender_router.build_brief(self.project, self.intake_path, self.project / "work/forged-role.json")

    def test_supplier_blocks_cannot_support_classification_and_gap_is_reported(self) -> None:
        self.write_intake(role="supplier")
        brief = tender_router.build_brief(self.project, self.intake_path, self.project / "work/supplier-brief.json")
        self.assertEqual(brief["source_readiness"]["tender_block_count"], 0)
        self.assertEqual(brief["classification_blocks"], [])
        self.assertTrue(any("tender原文块" in item for item in brief["blockers"]))
        with self.assertRaisesRegex(ValueError, "supplier/unknown"):
            self.route(self.decision(), out="artifacts/supplier-route.json")

    def test_single_requires_scope_evidence_and_unknown_requires_reason(self) -> None:
        no_scope = self.decision(structure="single")
        no_scope["lot_structure_evidence"] = []
        with self.assertRaisesRegex(ValueError, "范围依据"):
            self.route(no_scope, out="artifacts/no-scope.json")
        unknown = self.decision(structure="unknown", lots=[
            {
                "lot_id": "LOT-U",
                "lot_name": "待核实标包",
                "mode": "unknown",
                "components": [],
                "scenario_tags": [],
                "unknowns": [],
            }
        ])
        with self.assertRaisesRegex(ValueError, "unknowns原因"):
            self.route(unknown, out="artifacts/unknown-no-reason.json")

    def test_duplicate_catalog_category_is_rejected_explicitly(self) -> None:
        catalog = json.loads(tender_router.CATALOG_PATH.read_text(encoding="utf-8"))
        catalog["templates"].append(copy.deepcopy(catalog["templates"][0]))
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "catalog.json"
            path.write_text(json.dumps(catalog, ensure_ascii=False), encoding="utf-8")
            with patch.object(tender_router, "CATALOG_PATH", path), self.assertRaisesRegex(ValueError, "重复category"):
                tender_router._load_catalog()

    def test_missing_quote_and_wrong_location_are_rejected(self) -> None:
        missing = self.decision()
        missing["lots"][0]["components"][0]["evidence"][0]["quote"] = "不存在的原文"
        with self.assertRaises(ValueError):
            self.route(missing)
        wrong_location = self.decision()
        wrong_location["lots"][0]["components"][0]["evidence"][0]["location"] = "P99"
        with self.assertRaises(ValueError):
            self.route(wrong_location)

    def test_quote_matching_ignores_whitespace_only(self) -> None:
        decision = self.decision()
        decision["lots"][0]["components"][0]["evidence"][0]["quote"] = "设备 型号 和 数量\n按清单交付"
        result = self.route(decision)
        self.assertEqual(result["status"], "needs_review")

    def test_cross_project_and_stale_hashes_are_rejected(self) -> None:
        cross = self.decision()
        cross["project_id"] = "OTHER"
        with self.assertRaises(ValueError):
            self.route(cross)
        self.source.write_text(self.source.read_text(encoding="utf-8") + "changed\n", encoding="utf-8")
        with self.assertRaises(ValueError):
            tender_router.build_brief(self.project, self.intake_path, self.project / "work/brief-stale.json")
        self.write_intake()
        decision = self.decision()
        self.intake_path.write_text(self.intake_path.read_text(encoding="utf-8") + "\n", encoding="utf-8")
        with self.assertRaises(ValueError):
            self.route(decision)

    def test_path_escape_symlink_and_overwrite_are_rejected(self) -> None:
        with self.assertRaises(ValueError):
            tender_router.build_brief(self.project, "../outside.json", self.project / "work/brief.json")
        outside = self.root / "outside.json"
        outside.write_text("KEEP", encoding="utf-8")
        (self.project / "work/link.json").symlink_to(outside)
        with self.assertRaises(ValueError):
            tender_router.build_brief(self.project, self.intake_path, self.project / "work/link.json")
        output = self.project / "work/brief.json"
        tender_router.build_brief(self.project, self.intake_path, output)
        with self.assertRaises(ValueError):
            tender_router.build_brief(self.project, self.intake_path, output)
        self.assertEqual(outside.read_text(encoding="utf-8"), "KEEP")

    def test_unknown_fallback_keeps_unknowns_and_blockers(self) -> None:
        lot = {
            "lot_id": "LOT-U",
            "lot_name": "待核实标包",
            "mode": "unknown",
            "components": [],
            "scenario_tags": [],
            "unknowns": ["原文未明确采购边界"],
        }
        result = self.route(self.decision(structure="unknown", lots=[lot]))
        self.assertEqual(result["status"], "needs_review")
        self.assertTrue(result["blockers"])
        self.assertEqual(result["lots"][0]["selected_templates"], [])


if __name__ == "__main__":
    unittest.main()
