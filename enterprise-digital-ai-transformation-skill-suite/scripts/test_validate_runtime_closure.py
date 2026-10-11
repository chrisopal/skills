import copy
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

from validate_runtime_closure import validate


class RuntimeClosureTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.snapshot = self._fixture()

    def tearDown(self):
        self.tempdir.cleanup()

    def _write(self, name, content):
        path = self.root / name
        path.write_text(content, encoding="utf-8")
        return path

    def _write_json(self, name, value):
        return self._write(name, json.dumps(value))

    def _write_pptx(self, name, slide_count=2):
        path = self.root / name
        with zipfile.ZipFile(path, "w") as archive:
            slide_ids = []
            relationships = []
            for index in range(slide_count):
                number = 7 + index * 2
                rel_id = f"rId{index + 1}"
                slide_ids.append(f'<p:sldId id="{256 + index}" r:id="{rel_id}"/>')
                relationships.append(
                    f'<Relationship Id="{rel_id}" '
                    'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide" '
                    f'Target="slides/slide{number}.xml"/>'
                )
                archive.writestr(
                    f"ppt/slides/slide{number}.xml",
                    '<p:sld xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"/>',
                )
            archive.writestr(
                "ppt/presentation.xml",
                '<p:presentation xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" '
                'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
                f'<p:sldIdLst>{"".join(slide_ids)}</p:sldIdLst></p:presentation>',
            )
            archive.writestr(
                "ppt/_rels/presentation.xml.rels",
                '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                f'{"".join(relationships)}</Relationships>',
            )
        return path

    def _write_fake_pptx(self, name):
        path = self.root / name
        with zipfile.ZipFile(path, "w") as archive:
            archive.writestr("ppt/slides/slide1.xml", "<p:sld/>")
            archive.writestr("ppt/slides/slide2.xml", "<p:sld/>")
        return path

    def _ref(self, artifact_id, filename, version="1.0.0"):
        path = self._write(filename, f"{artifact_id}:{version}\n")
        return {
            "id": artifact_id,
            "version": version,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "path": filename,
        }

    def _fixture(self):
        context = self._ref("context", "context.json")
        register = self._ref("register", "register.yaml")
        workflow = self._ref("workflow", "workflow.yaml")
        candidate = self._ref("candidate", "candidate.json", "2.1.0")
        candidate["status"] = "candidate"
        retest = self._ref("retest", "retest.json")
        run_evidence = self._ref("run-evidence", "run-evidence.json")
        report = self._ref("report", "report.pdf")
        contentpack_path = self._write_json("contentpack.json", {"slides": [{"id": "slide-1"}, {"id": "slide-2"}]})
        contentpack = {
            "id": "contentpack",
            "version": "1.0.0",
            "sha256": hashlib.sha256(contentpack_path.read_bytes()).hexdigest(),
            "path": "contentpack.json",
        }
        html = self._ref("html", "review.html")
        ppt_path = self._write_pptx("deck.pptx")
        ppt = {
            "id": "ppt",
            "version": "1.0.0",
            "sha256": hashlib.sha256(ppt_path.read_bytes()).hexdigest(),
            "path": "deck.pptx",
        }

        def delivery_item(kind, artifact, page_count=2):
            return {
                "kind": kind,
                "artifact": artifact,
                "page_count": page_count,
                "page_map": [
                    {"page": 1, "source_id": "slide-1"},
                    {"page": 2, "source_id": "slide-2"},
                ],
            }

        return {
            "snapshot_id": "runtime-closure-fixture-001",
            "project_id": "sample-manufacturing-dtx",
            "mode": "host-execution",
            "tasks": [
                {
                    "id": "task-s1",
                    "stage": "S1",
                    "required_input_ids": ["context", "register", "workflow"],
                    "inputs": [context, register, workflow],
                    "outputs": [candidate],
                    "skill_name": "evidence-factbase",
                    "skill_version": "1.1.0",
                    "run": {"mode": "host-execution", "actor": "operator", "evidence_ref": run_evidence},
                }
            ],
            "reviews": [
                {
                    "id": "review-s1",
                    "candidate": candidate,
                    "generated_by": "operator",
                    "reviewed_by": "independent-reviewer",
                    "reviewer_independent": True,
                    "results": {
                        "technical": {"status": "pass"},
                        "professional": {"status": "pass"},
                        "customer": {"status": "pending"},
                    },
                    "findings": [
                        {
                            "id": "finding-1",
                            "owner": "author",
                            "due": "2026-10-12",
                            "status": "closed",
                            "retest_evidence": retest,
                        }
                    ],
                }
            ],
            "gate_decisions": [
                {
                    "id": "gate-s1",
                    "gate": "G1",
                    "mode": "host-execution",
                    "decision": "pending",
                    "candidate": candidate,
                }
            ],
            "upstream_changes": [],
            "deliveries": [
                {
                    "id": "delivery-s1",
                    "status": "candidate",
                    "package_page_count": 2,
                    "items": [
                        delivery_item("report", report),
                        delivery_item("contentpack", contentpack),
                        delivery_item("html", html),
                        delivery_item("ppt", ppt),
                    ],
                }
            ],
        }

    def test_valid_host_execution_snapshot_passes(self):
        self.assertEqual(validate(self.snapshot, self.root), [])

    def _formal_snapshot(self):
        snapshot = copy.deepcopy(self.snapshot)
        task = snapshot["tasks"][0]
        output_refs = [dict(item["artifact"]) for item in snapshot["deliveries"][0]["items"]]
        for ref in output_refs:
            ref["status"] = "approved"
        task["outputs"].extend(output_refs)
        reviews = snapshot["reviews"]
        for index, ref in enumerate(output_refs):
            reviews.append({
                "id": f"review-delivery-{index}",
                "candidate": ref,
                "generated_by": "operator",
                "reviewed_by": "independent-reviewer",
                "reviewer_independent": True,
                "results": {
                    "technical": {"status": "pass"},
                    "professional": {"status": "pass"},
                    "customer": {"status": "pending"},
                },
                "findings": [{
                    "id": f"closed-{index}",
                    "owner": "author",
                    "due": "2026-10-12",
                    "status": "closed",
                    "retest_evidence": snapshot["reviews"][0]["findings"][0]["retest_evidence"],
                }],
            })
            snapshot["gate_decisions"].append({
                "id": f"customer-gate-{index}",
                "gate": "G1",
                "gate_type": "customer",
                "mode": "host-execution",
                "decision": "approved",
                "candidate": ref,
                "decision_record_ref": task["run"]["evidence_ref"],
                "decided_by": "customer-sponsor",
                "decided_at": "2026-10-11T12:00:00Z",
            })
        snapshot["deliveries"][0]["status"] = "formal"
        return snapshot

    def test_formal_delivery_requires_output_reviews_and_customer_gate(self):
        self.assertEqual(validate(self._formal_snapshot(), self.root), [])

    def test_contentpack_accepts_slide_id_and_rejects_conflicting_id(self):
        snapshot = copy.deepcopy(self.snapshot)
        contentpack_path = self.root / "contentpack.json"
        contentpack_path.write_text(json.dumps({"slides": [{"slide_id": "slide-1"}, {"slide_id": "slide-2"}]}), encoding="utf-8")
        contentpack = snapshot["deliveries"][0]["items"][1]["artifact"]
        contentpack["sha256"] = hashlib.sha256(contentpack_path.read_bytes()).hexdigest()
        self.assertEqual(validate(snapshot, self.root), [])
        contentpack_path.write_text(json.dumps({"slides": [{"id": "slide-a", "slide_id": "slide-b"}, {"id": "slide-2"}]}), encoding="utf-8")
        contentpack["sha256"] = hashlib.sha256(contentpack_path.read_bytes()).hexdigest()
        errors = validate(snapshot, self.root)
        self.assertTrue(any("conflict" in error or "source id" in error for error in errors))

    def test_formal_delivery_must_bind_actual_task_outputs(self):
        snapshot = self._formal_snapshot()
        snapshot["deliveries"][0]["items"][0]["artifact"]["id"] = "not-an-output"
        errors = validate(snapshot, self.root)
        self.assertTrue(any("task output" in error or "output" in error for error in errors))

    def test_formal_delivery_must_bind_approved_task_outputs(self):
        snapshot = self._formal_snapshot()
        report_output = next(output for output in snapshot["tasks"][0]["outputs"] if output["id"] == "report")
        report_output["status"] = "candidate"
        errors = validate(snapshot, self.root)
        self.assertTrue(any("approved" in error and "formal" in error for error in errors))

    def test_formal_delivery_requires_independent_professional_pass(self):
        snapshot = self._formal_snapshot()
        snapshot["reviews"][1]["results"]["professional"]["status"] = "pending"
        errors = validate(snapshot, self.root)
        self.assertTrue(any("professional" in error for error in errors))

    def test_formal_delivery_requires_customer_approval_gate(self):
        snapshot = self._formal_snapshot()
        snapshot["gate_decisions"] = [gate for gate in snapshot["gate_decisions"] if gate["decision"] == "pending"]
        errors = validate(snapshot, self.root)
        self.assertTrue(any("customer" in error for error in errors))

    def test_conditional_pass_does_not_qualify_as_customer_approval(self):
        snapshot = self._formal_snapshot()
        for gate in snapshot["gate_decisions"]:
            if gate["decision"] == "approved":
                gate["decision"] = "conditional-pass"
        errors = validate(snapshot, self.root)
        self.assertTrue(any("approved customer" in error or "customer approval" in error for error in errors))

    def test_phase_approved_gate_is_allowed_but_not_customer_approval(self):
        snapshot = copy.deepcopy(self.snapshot)
        gate = snapshot["gate_decisions"][0]
        gate.update({
            "decision": "approved",
            "gate_type": "phase",
            "decision_record_ref": snapshot["tasks"][0]["run"]["evidence_ref"],
            "decided_by": "phase-owner",
            "decided_at": "2026-10-11T12:00:00Z",
        })
        self.assertEqual(validate(snapshot, self.root), [])

    def test_formal_delivery_requires_technical_pass_too(self):
        snapshot = self._formal_snapshot()
        snapshot["reviews"][1]["results"]["technical"]["status"] = "fail"
        errors = validate(snapshot, self.root)
        self.assertTrue(any("technical" in error for error in errors))

    def test_malformed_nested_result_returns_structured_error_without_crashing(self):
        snapshot = self._formal_snapshot()
        snapshot["reviews"][1]["results"]["technical"] = "not-an-object"
        errors = validate(snapshot, self.root)
        self.assertTrue(any("technical" in error for error in errors))

    def test_formal_delivery_requires_closed_findings(self):
        snapshot = self._formal_snapshot()
        snapshot["reviews"][1]["findings"][0]["status"] = "open"
        snapshot["reviews"][1]["findings"][0].pop("retest_evidence")
        errors = validate(snapshot, self.root)
        self.assertTrue(any("closed" in error or "formal" in error for error in errors))

    def test_approved_output_requires_review_and_customer_gate_even_without_delivery(self):
        snapshot = copy.deepcopy(self.snapshot)
        snapshot["tasks"][0]["outputs"][0]["status"] = "approved"
        snapshot["deliveries"] = []
        snapshot["execution_state"] = "in-progress"
        errors = validate(snapshot, self.root)
        self.assertTrue(any("approved output" in error for error in errors))

    def test_open_blocking_finding_cannot_report_professional_pass(self):
        snapshot = copy.deepcopy(self.snapshot)
        finding = snapshot["reviews"][0]["findings"][0]
        finding["status"] = "open"
        finding.pop("retest_evidence")
        errors = validate(snapshot, self.root)
        self.assertTrue(any("blocking" in error for error in errors))

    def test_open_finding_may_wait_for_retest_but_closed_finding_cannot(self):
        snapshot = copy.deepcopy(self.snapshot)
        finding = snapshot["reviews"][0]["findings"][0]
        finding["status"] = "open"
        finding["blocking"] = False
        finding.pop("retest_evidence")
        self.assertEqual(validate(snapshot, self.root), [])
        finding["status"] = "closed"
        errors = validate(snapshot, self.root)
        self.assertTrue(any("retest" in error for error in errors))

    def test_review_generator_must_match_task_run_actor(self):
        snapshot = copy.deepcopy(self.snapshot)
        snapshot["reviews"][0]["generated_by"] = "other-actor"
        errors = validate(snapshot, self.root)
        self.assertTrue(any("run.actor" in error or "generated_by" in error for error in errors))

    def test_host_execution_requires_skill_version_and_run_evidence(self):
        snapshot = copy.deepcopy(self.snapshot)
        snapshot["tasks"][0].pop("skill_version")
        snapshot["tasks"][0]["run"].pop("evidence_ref")
        errors = validate(snapshot, self.root)
        self.assertTrue(any("skill_version" in error for error in errors))
        self.assertTrue(any("evidence_ref" in error for error in errors))

    def test_status_and_result_enums_are_closed(self):
        snapshot = copy.deepcopy(self.snapshot)
        snapshot["tasks"][0]["outputs"][0]["status"] = "made-up"
        snapshot["reviews"][0]["results"]["technical"]["status"] = "made-up"
        snapshot["reviews"][0]["findings"][0]["status"] = "made-up"
        errors = validate(snapshot, self.root)
        self.assertGreaterEqual(len(errors), 3)

    def test_staleness_propagates_from_task_inputs_transitively(self):
        snapshot = copy.deepcopy(self.snapshot)
        next_output_path = self._write("next-output.json", "next output\n")
        next_output = {
            "id": "next-output",
            "version": "1.0.0",
            "sha256": hashlib.sha256(next_output_path.read_bytes()).hexdigest(),
            "path": "next-output.json",
            "status": "validated",
        }
        snapshot["tasks"].append({
            "id": "task-s2",
            "stage": "S2",
            "required_input_ids": ["candidate"],
            "inputs": [dict(snapshot["tasks"][0]["outputs"][0])],
            "outputs": [next_output],
            "skill_name": "as-is-operating-model",
            "skill_version": "1.0.0",
            "run": {"mode": "host-execution", "actor": "operator", "evidence_ref": snapshot["tasks"][0]["run"]["evidence_ref"]},
        })
        snapshot["upstream_changes"] = [{"artifact_id": "context", "from_version": "1.0.0", "to_version": "2.0.0"}]
        errors = validate(snapshot, self.root)
        self.assertTrue(any("stale" in error for error in errors))

    def test_downstream_input_must_match_registered_output_ref_exactly(self):
        snapshot = copy.deepcopy(self.snapshot)
        next_output_path = self._write("next-output.json", "next output\n")
        next_output = {
            "id": "next-output",
            "version": "1.0.0",
            "sha256": hashlib.sha256(next_output_path.read_bytes()).hexdigest(),
            "path": "next-output.json",
            "status": "validated",
        }
        downstream_input = dict(snapshot["tasks"][0]["outputs"][0], version="9.9.9")
        snapshot["tasks"].append({
            "id": "task-s2",
            "stage": "S2",
            "required_input_ids": ["candidate"],
            "inputs": [downstream_input],
            "outputs": [next_output],
            "skill_name": "as-is-operating-model",
            "skill_version": "1.0.0",
            "run": {"mode": "host-execution", "actor": "operator", "evidence_ref": snapshot["tasks"][0]["run"]["evidence_ref"]},
        })
        errors = validate(snapshot, self.root)
        self.assertTrue(any("lineage" in error or "exact output" in error for error in errors))

    def test_malformed_hash_type_returns_errors_without_crashing(self):
        snapshot = copy.deepcopy(self.snapshot)
        snapshot["tasks"][0]["inputs"][0]["sha256"] = {"unexpected": "object"}
        errors = validate(snapshot, self.root)
        self.assertTrue(errors)

    def test_ppt_and_contentpack_counts_are_read_from_actual_files_and_source_ids_resolve(self):
        snapshot = copy.deepcopy(self.snapshot)
        snapshot["deliveries"][0]["items"][1]["page_count"] = 1
        snapshot["deliveries"][0]["items"][0]["page_map"][0]["source_id"] = "missing-slide"
        errors = validate(snapshot, self.root)
        self.assertTrue(any("contentpack" in error or "count" in error for error in errors))
        self.assertTrue(any("source_id" in error or "source" in error for error in errors))

    def test_contentpack_page_map_must_cover_every_source_id(self):
        snapshot = copy.deepcopy(self.snapshot)
        ppt_item = next(item for item in snapshot["deliveries"][0]["items"] if item["kind"] == "ppt")
        ppt_item["page_map"] = [
            {"page": 1, "source_id": "slide-1"},
            {"page": 2, "source_id": "slide-1"},
        ]
        errors = validate(snapshot, self.root)
        self.assertTrue(any("source" in error and "page_map" in error for error in errors))

    def test_fake_ppt_zip_with_slide_files_but_no_presentation_is_rejected(self):
        snapshot = copy.deepcopy(self.snapshot)
        fake_path = self._write_fake_pptx("fake-deck.pptx")
        ppt_item = next(item for item in snapshot["deliveries"][0]["items"] if item["kind"] == "ppt")
        ppt_item["artifact"]["path"] = fake_path.name
        ppt_item["artifact"]["sha256"] = hashlib.sha256(fake_path.read_bytes()).hexdigest()
        errors = validate(snapshot, self.root)
        self.assertTrue(any("presentation" in error or "referenced" in error for error in errors))

    def test_manual_simulation_cannot_validate_or_formally_deliver(self):
        snapshot = copy.deepcopy(self.snapshot)
        snapshot["mode"] = "manual-simulation"
        snapshot["tasks"][0]["run"]["mode"] = "manual-simulation"
        snapshot["tasks"][0]["outputs"][0]["status"] = "validated"
        snapshot["deliveries"][0]["status"] = "formal"
        errors = validate(snapshot, self.root)
        self.assertTrue(any("simulation" in error for error in errors))

    def test_required_input_set_cannot_be_replaced_by_one_previous_stage_input(self):
        snapshot = copy.deepcopy(self.snapshot)
        snapshot["tasks"][0]["inputs"] = snapshot["tasks"][0]["inputs"][:1]
        errors = validate(snapshot, self.root)
        self.assertTrue(any("required_input_ids" in error for error in errors))

    def test_duplicate_required_input_ids_and_duplicate_input_artifacts_are_rejected(self):
        snapshot = copy.deepcopy(self.snapshot)
        snapshot["tasks"][0]["required_input_ids"].append("context")
        snapshot["tasks"][0]["inputs"].append(snapshot["tasks"][0]["inputs"][0])
        errors = validate(snapshot, self.root)
        self.assertTrue(any("duplicate" in error for error in errors))

    def test_input_requires_explicit_version_sha_and_existing_matching_file(self):
        snapshot = copy.deepcopy(self.snapshot)
        snapshot["tasks"][0]["inputs"][0]["sha256"] = "0" * 64
        snapshot["tasks"][0]["inputs"][1].pop("version")
        snapshot["tasks"][0]["inputs"][2]["path"] = "missing.yaml"
        errors = validate(snapshot, self.root)
        self.assertTrue(any("sha256" in error or "version" in error or "file" in error for error in errors))

    def test_task_run_mode_must_be_explicit_and_match_snapshot(self):
        snapshot = copy.deepcopy(self.snapshot)
        snapshot["tasks"][0]["run"]["mode"] = "magic"
        errors = validate(snapshot, self.root)
        self.assertTrue(any("mode" in error for error in errors))

    def test_review_must_bind_exact_candidate_and_independent_reviewer(self):
        snapshot = copy.deepcopy(self.snapshot)
        snapshot["reviews"][0]["candidate"] = dict(snapshot["reviews"][0]["candidate"], version="1.0.0")
        snapshot["reviews"][0]["reviewed_by"] = "author"
        snapshot["reviews"][0]["reviewer_independent"] = False
        errors = validate(snapshot, self.root)
        self.assertTrue(any("candidate" in error for error in errors))
        self.assertTrue(any("independent" in error or "reviewer" in error for error in errors))

    def test_findings_require_owner_due_and_retest_evidence(self):
        snapshot = copy.deepcopy(self.snapshot)
        snapshot["reviews"][0]["findings"][0].pop("owner")
        snapshot["reviews"][0]["findings"][0].pop("retest_evidence")
        errors = validate(snapshot, self.root)
        self.assertTrue(any("owner" in error for error in errors))
        self.assertTrue(any("retest" in error for error in errors))

    def test_technical_professional_customer_results_must_be_separate(self):
        snapshot = copy.deepcopy(self.snapshot)
        snapshot["reviews"][0]["results"] = {"result": {"status": "pass"}}
        errors = validate(snapshot, self.root)
        self.assertTrue(any("technical" in error for error in errors))
        self.assertTrue(any("professional" in error for error in errors))
        self.assertTrue(any("customer" in error for error in errors))

    def test_simulation_can_never_approve(self):
        snapshot = copy.deepcopy(self.snapshot)
        snapshot["mode"] = "manual-simulation"
        snapshot["tasks"][0]["run"]["mode"] = "manual-simulation"
        snapshot["gate_decisions"][0]["decision"] = "approved"
        errors = validate(snapshot, self.root)
        self.assertTrue(any("simulation" in error for error in errors))

    def test_simulation_cannot_mark_an_output_approved(self):
        snapshot = copy.deepcopy(self.snapshot)
        snapshot["mode"] = "manual-simulation"
        snapshot["tasks"][0]["run"]["mode"] = "manual-simulation"
        snapshot["tasks"][0]["outputs"][0]["status"] = "approved"
        errors = validate(snapshot, self.root)
        self.assertTrue(any("simulation" in error for error in errors))

    def test_host_approval_requires_real_decision_record_person_time_and_exact_candidate(self):
        snapshot = copy.deepcopy(self.snapshot)
        snapshot["gate_decisions"][0].update(
            {"decision": "approved", "decided_by": "sponsor", "candidate": {"id": "candidate", "version": "1.0.0"}}
        )
        errors = validate(snapshot, self.root)
        self.assertTrue(any("decision record" in error for error in errors))
        self.assertTrue(any("candidate" in error for error in errors))

    def test_changed_upstream_marks_dependent_output_stale_and_blocks_formal_delivery(self):
        snapshot = copy.deepcopy(self.snapshot)
        snapshot["tasks"][0]["outputs"][0]["depends_on"] = ["context"]
        snapshot["upstream_changes"] = [{"artifact_id": "context", "from_version": "1.0.0", "to_version": "1.1.0"}]
        snapshot["tasks"][0]["outputs"][0]["status"] = "validated"
        snapshot["deliveries"][0]["status"] = "formal"
        errors = validate(snapshot, self.root)
        self.assertTrue(any("stale" in error for error in errors))

    def test_stale_output_cannot_be_formal_delivery(self):
        snapshot = copy.deepcopy(self.snapshot)
        snapshot["tasks"][0]["outputs"][0]["status"] = "stale"
        snapshot["deliveries"][0]["status"] = "formal"
        snapshot["deliveries"][0]["items"][0]["artifact"] = dict(snapshot["tasks"][0]["outputs"][0])
        errors = validate(snapshot, self.root)
        self.assertTrue(any("formal" in error and "stale" in error for error in errors))

    def test_delivery_requires_four_kinds_page_maps_and_sha256(self):
        snapshot = copy.deepcopy(self.snapshot)
        snapshot["deliveries"][0]["items"].pop()
        snapshot["deliveries"][0]["items"][0]["page_map"] = []
        snapshot["deliveries"][0]["items"][1]["artifact"].pop("sha256")
        errors = validate(snapshot, self.root)
        self.assertTrue(any("ppt" in error or "kind" in error for error in errors))
        self.assertTrue(any("page_map" in error for error in errors))
        self.assertTrue(any("sha256" in error for error in errors))

    def test_delivery_page_count_mismatch_requires_explanation(self):
        snapshot = copy.deepcopy(self.snapshot)
        ppt_item = next(item for item in snapshot["deliveries"][0]["items"] if item["kind"] == "ppt")
        ppt_item["page_count"] = 24
        ppt_item["page_map"] = [{"page": n, "source_id": "candidate"} for n in range(1, 25)]
        errors = validate(snapshot, self.root)
        self.assertTrue(any("page count" in error or "explanation" in error for error in errors))

    def test_cli_returns_zero_for_valid_snapshot_and_one_for_invalid_snapshot(self):
        snapshot_path = self.root / "snapshot.json"
        snapshot_path.write_text(json.dumps(self.snapshot), encoding="utf-8")
        script = Path(__file__).with_name("validate_runtime_closure.py")
        completed = subprocess.run([sys.executable, str(script), str(snapshot_path), str(self.root)], capture_output=True, text=True)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        invalid = copy.deepcopy(self.snapshot)
        invalid["mode"] = "bad"
        snapshot_path.write_text(json.dumps(invalid), encoding="utf-8")
        completed = subprocess.run([sys.executable, str(script), str(snapshot_path), str(self.root)], capture_output=True, text=True)
        self.assertEqual(completed.returncode, 1, completed.stdout)


if __name__ == "__main__":
    unittest.main()
