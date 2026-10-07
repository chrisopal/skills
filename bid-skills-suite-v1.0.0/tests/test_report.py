"""Security and source-binding tests for the offline tender report renderer."""

from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import render_report


class ReportRendererTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.project = Path(self.temp.name) / "project"
        (self.project / "inputs").mkdir(parents=True)
        (self.project / "artifacts").mkdir()
        (self.project / "work").mkdir()
        (self.project / "inputs/tender.txt").write_text("原文 <script>alert(1)</script>\n", encoding="utf-8")
        self._write_fixture()

    def _write_fixture(self) -> None:
        source = self.project / "inputs/tender.txt"
        source_hash = hashlib.sha256(source.read_bytes()).hexdigest()

        def artifact(artifact_id: str, skill_id: str, data: dict, inputs: list[dict] | None = None) -> dict:
            return {
                "schema_version": "1.0",
                "skill_id": skill_id,
                "project_id": "TEST-REPORT",
                "artifact_id": artifact_id,
                "revision": 1,
                "status": "needs_review",
                "inputs": inputs or [],
                "summary": "synthetic",
                "data": data,
                "warnings": [],
                "blockers": [],
            }

        intake = artifact(
            "ART-01-NATIVE",
            "bid-source-intake",
            {"documents": [{"source_id": "SRC-001", "filename": "tender.txt", "relative_path": "inputs/tender.txt", "sha256": source_hash, "bytes": source.stat().st_size, "revision": 1, "role": "main", "status": "parsed"}], "blocks": [], "page_audit": [], "coverage": "complete"},
            [{"artifact_id": "SRC-001", "revision": 1, "relative_path": "inputs/tender.txt", "sha256": source_hash}],
        )
        route = artifact("ART-02-TENDER-ROUTING", "bid-project-profile", {"classification": {"project_id": "TEST-REPORT", "lot_structure": "single"}, "source_inventory": [{"source_id": "SRC-001", "relative_path": "inputs/tender.txt", "sha256": source_hash, "revision": 1}], "intake_sha256": "", "selected_template_categories": ["software_integration"], "scope": {"boundary": "待业务复核"}}, [{"artifact_id": "ART-01-NATIVE", "revision": 1, "relative_path": "artifacts/01-source-intake-r2.json", "sha256": ""}])
        profile = artifact("ART-02-PROFILE", "bid-project-profile", {"project_name": "测试项目", "buyer": "测试采购人", "bidder": None, "lot_scope": ["LOT-1"], "deadlines": [], "key_facts": [{"key": "最高限价", "value": "待补"}], "unknowns": ["缺企业资料"]})
        requirement = {"id": "R-001", "category": "functional", "text": "安全输入 </script><img src=x onerror=alert(1)>", "mandatory": "yes", "basis_type": "explicit", "conditions": ["条件"], "acceptance": "验收", "sources": [{"source_id": "SRC-001", "location": "P1", "quote": "原文"}], "related_ids": []}
        requirements = artifact("ART-03-REQUIREMENTS", "bid-requirements", {"requirements": [requirement, {**requirement, "id": "R-002", "category": "integration", "basis_type": "derived"}, {**requirement, "id": "R-003", "category": "quality", "basis_type": "proposal"}], "conflicts": [], "unread_scopes": []})
        scoring = artifact("ART-04-SCORING", "bid-scoring", {"declared_total": 100, "items": [{"id": "S-00", "parent_id": None, "title": "价格", "max_score": 40, "node_type": "leaf", "aggregation": "sum", "rule_text": "按原文", "sources": [{"source_id": "SRC-001", "location": "P1", "quote": "评分"}]}], "unknowns": []})
        compliance = artifact("ART-05-COMPLIANCE", "bid-compliance", {"rules": [{"id": "C-001", "kind": "qualification", "condition": "资格条件", "fatal": None, "required_action": "补资料", "sources": [{"source_id": "SRC-001", "location": "P1", "quote": "资格"}]}], "unknowns": []})
        formats = artifact("ART-06-FORMAT-RULES", "bid-format-extraction", {"formats": [{"id": "F-001", "kind": "form", "strength": "mandatory", "title": "投标函", "original_text": "按格式", "sources": [{"source_id": "SRC-001", "location": "P1", "quote": "格式"}]}], "unknowns": []})
        intake_path = self.project / "artifacts/01-source-intake-r2.json"
        intake_path.write_text(json.dumps(intake, ensure_ascii=False), encoding="utf-8")
        intake_hash = hashlib.sha256(intake_path.read_bytes()).hexdigest()
        route["intake_sha256"] = intake_hash
        route["inputs"][0]["sha256"] = intake_hash
        route["classification"] = route["data"].pop("classification")
        route["source_inventory"] = route["data"].pop("source_inventory")
        route["selected_template_categories"] = route["data"].pop("selected_template_categories")
        route["scope"] = route["data"].pop("scope")
        route_path = self.project / "artifacts/02-tender-routing-r2.json"
        route_path.write_text(json.dumps(route, ensure_ascii=False), encoding="utf-8")
        route_hash = hashlib.sha256(route_path.read_bytes()).hexdigest()
        profile["inputs"] = [{"artifact_id": "ART-01-NATIVE", "revision": 1, "relative_path": "artifacts/01-source-intake-r2.json", "sha256": intake_hash}, {"artifact_id": "ART-02-TENDER-ROUTING", "revision": 1, "relative_path": "artifacts/02-tender-routing-r2.json", "sha256": route_hash}]
        artifacts = [profile, requirements, scoring, compliance, formats]
        for data, filename in zip(artifacts, ("02-project-profile-r2.json", "03-requirements-r2.json", "04-scoring-r2.json", "05-compliance-r2.json", "06-format-rules-r2.json")):
            (self.project / "artifacts" / filename).write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        paths = ["artifacts/01-source-intake-r2.json", "artifacts/02-project-profile-r2.json", "artifacts/03-requirements-r2.json", "artifacts/04-scoring-r2.json", "artifacts/05-compliance-r2.json", "artifacts/06-format-rules-r2.json", "artifacts/02-tender-routing-r2.json"]
        ids = ["ART-01-NATIVE", "ART-02-PROFILE", "ART-03-REQUIREMENTS", "ART-04-SCORING", "ART-05-COMPLIANCE", "ART-06-FORMAT-RULES", "ART-02-TENDER-ROUTING"]
        inputs = [{"artifact_id": aid, "revision": 1, "relative_path": rel, "sha256": hashlib.sha256((self.project / rel).read_bytes()).hexdigest()} for aid, rel in zip(ids, paths)]
        workflow = {"schema_version": "1.0", "skill_id": "bid-orchestrator", "project_id": "TEST-REPORT", "artifact_id": "ART-17-WORKFLOW", "revision": 1, "status": "needs_review", "inputs": inputs, "summary": "待复核", "data": {"stages": [{"skill_id": skill, "artifact_path": path, "state": "needs_review"} for skill, path in zip(render_report.REQUIRED_STAGES, paths[:6])]}, "warnings": [], "blockers": []}
        (self.project / "work/17-workflow-state.json").write_text(json.dumps(workflow, ensure_ascii=False), encoding="utf-8")

    def test_counts_escape_all_requirements_and_writes_manifest(self) -> None:
        manifest = render_report.generate(self.project)
        output = self.project / "reports/tender-report.html"
        text = output.read_text(encoding="utf-8")
        self.assertEqual(manifest["counts"]["requirements"]["total"], 3)
        self.assertEqual(manifest["counts"]["scores"]["nodes"], 1)
        self.assertNotIn("</script><img", text.lower())
        self.assertNotIn("<img src=x", text)
        self.assertIn("原文明示", text)
        self.assertIn("推导", text)
        self.assertIn("建议", text)
        self.assertIn("单一标包", text)
        self.assertIn("软件开发与系统集成", text)
        self.assertNotIn('class="metric">software_integration', text)
        self.assertTrue((self.project / "reports/tender-report.manifest.json").is_file())

    def test_input_hash_change_is_rejected(self) -> None:
        path = self.project / "artifacts/03-requirements-r2.json"
        path.write_text(path.read_text(encoding="utf-8") + "\n", encoding="utf-8")
        with self.assertRaisesRegex(render_report.ReportInputError, "输入哈希不匹配"):
            render_report.generate(self.project)

    def test_qualification_requirement_group_and_filter_use_chinese_label(self) -> None:
        artifact_path = self.project / "artifacts/03-requirements-r2.json"
        artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
        artifact["data"]["requirements"][0]["category"] = "qualification"
        artifact_path.write_text(json.dumps(artifact, ensure_ascii=False), encoding="utf-8")
        workflow_path = self.project / "work/17-workflow-state.json"
        workflow = json.loads(workflow_path.read_text(encoding="utf-8"))
        entry = next(item for item in workflow["inputs"] if item["relative_path"] == "artifacts/03-requirements-r2.json")
        entry["sha256"] = hashlib.sha256(artifact_path.read_bytes()).hexdigest()
        workflow_path.write_text(json.dumps(workflow), encoding="utf-8")
        render_report.generate(self.project)
        document = (self.project / "reports/tender-report.html").read_text(encoding="utf-8")
        self.assertTrue('<option value="qualification">资格条件</option>' in document, "资格需求筛选项应显示中文标签")
        self.assertNotIn('<h3>qualification', document)

    def test_path_escape_is_rejected_before_reading(self) -> None:
        workflow_path = self.project / "work/17-workflow-state.json"
        workflow = json.loads(workflow_path.read_text(encoding="utf-8"))
        workflow["inputs"][0]["relative_path"] = "../outside.json"
        workflow_path.write_text(json.dumps(workflow), encoding="utf-8")
        with self.assertRaisesRegex(render_report.ReportInputError, "路径越界"):
            render_report.generate(self.project)

    def test_artifact_revision_mismatch_is_rejected(self) -> None:
        artifact_path = self.project / "artifacts/03-requirements-r2.json"
        artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
        artifact["revision"] = 2
        artifact_path.write_text(json.dumps(artifact, ensure_ascii=False), encoding="utf-8")
        workflow_path = self.project / "work/17-workflow-state.json"
        workflow = json.loads(workflow_path.read_text(encoding="utf-8"))
        entry = next(item for item in workflow["inputs"] if item["relative_path"] == "artifacts/03-requirements-r2.json")
        entry["sha256"] = hashlib.sha256(artifact_path.read_bytes()).hexdigest()
        workflow_path.write_text(json.dumps(workflow, ensure_ascii=False), encoding="utf-8")
        with self.assertRaisesRegex(render_report.ReportInputError, "revision不一致"):
            render_report.generate(self.project)

    def test_stale_stage_is_rejected(self) -> None:
        workflow_path = self.project / "work/17-workflow-state.json"
        workflow = json.loads(workflow_path.read_text(encoding="utf-8"))
        workflow["data"]["stages"][0]["state"] = "stale"
        workflow_path.write_text(json.dumps(workflow, ensure_ascii=False), encoding="utf-8")
        with self.assertRaisesRegex(render_report.ReportInputError, "未完成或已失效"):
            render_report.generate(self.project)

    def test_unstarted_writing_does_not_block_understanding_report(self) -> None:
        workflow_path = self.project / "work/17-workflow-state.json"
        workflow = json.loads(workflow_path.read_text(encoding="utf-8"))
        workflow["data"]["stages"].append({"skill_id": "bid-technical-writing", "state": "not_started", "artifact_path": None})
        workflow_path.write_text(json.dumps(workflow, ensure_ascii=False), encoding="utf-8")
        self.assertEqual(render_report.generate(self.project)["counts"]["requirements"]["total"], 3)

    def test_route_identity_is_checked(self) -> None:
        route_path = self.project / "artifacts/02-tender-routing-r2.json"
        route = json.loads(route_path.read_text(encoding="utf-8"))
        route["artifact_id"] = "ART-02-TENDER-ROUTING-STALE"
        route_path.write_text(json.dumps(route, ensure_ascii=False), encoding="utf-8")
        new_hash = hashlib.sha256(route_path.read_bytes()).hexdigest()
        workflow_path = self.project / "work/17-workflow-state.json"
        workflow = json.loads(workflow_path.read_text(encoding="utf-8"))
        entry = next(item for item in workflow["inputs"] if "tender-routing" in item["relative_path"])
        entry["sha256"] = new_hash
        profile_path = self.project / "artifacts/02-project-profile-r2.json"
        profile = json.loads(profile_path.read_text(encoding="utf-8"))
        profile["inputs"][1]["sha256"] = new_hash
        profile_path.write_text(json.dumps(profile, ensure_ascii=False), encoding="utf-8")
        profile_entry = next(item for item in workflow["inputs"] if "project-profile" in item["relative_path"])
        profile_entry["sha256"] = hashlib.sha256(profile_path.read_bytes()).hexdigest()
        workflow_path.write_text(json.dumps(workflow, ensure_ascii=False), encoding="utf-8")
        with self.assertRaisesRegex(render_report.ReportInputError, "身份不一致|产物ID不一致"):
            render_report.generate(self.project)

    def test_existing_output_is_not_silently_overwritten(self) -> None:
        render_report.generate(self.project)
        with self.assertRaises(FileExistsError):
            render_report.generate(self.project)

    def test_analysis_copy_does_not_change_literal_source_quotes(self) -> None:
        artifact_path = self.project / "artifacts/03-requirements-r2.json"
        artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
        artifact["data"]["requirements"][0]["sources"][0]["quote"] = "needs_review：原文技术术语template_path"
        artifact["data"]["unknowns"] = ["未重建模板，template_path留空，降为reference。"]
        artifact_path.write_text(json.dumps(artifact, ensure_ascii=False), encoding="utf-8")
        workflow_path = self.project / "work/17-workflow-state.json"
        workflow = json.loads(workflow_path.read_text(encoding="utf-8"))
        entry = next(item for item in workflow["inputs"] if item["relative_path"] == "artifacts/03-requirements-r2.json")
        entry["sha256"] = hashlib.sha256(artifact_path.read_bytes()).hexdigest()
        workflow_path.write_text(json.dumps(workflow, ensure_ascii=False), encoding="utf-8")
        render_report.generate(self.project)
        document = (self.project / "reports/tender-report.html").read_text(encoding="utf-8")
        self.assertIn("needs_review：原文技术术语template_path", document)
        self.assertIn("未重建模板，模板文件路径留空，降为参考格式。", document)

    def test_overwrite_preserves_previous_report_and_manifest(self) -> None:
        render_report.generate(self.project)
        manifest = render_report.generate(self.project, overwrite=True)
        self.assertEqual(len(manifest["previous_output_backups"]), 2)
        for rel in manifest["previous_output_backups"]:
            self.assertTrue((self.project / rel).is_file())


if __name__ == "__main__":
    unittest.main()
