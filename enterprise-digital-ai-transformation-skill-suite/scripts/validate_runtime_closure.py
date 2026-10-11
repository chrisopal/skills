"""Validate the declarative runtime-closure contract without executing or approving work."""

from __future__ import annotations

import hashlib
import json
import re
import posixpath
import sys
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any


MODES = {"manual-simulation", "host-execution"}
DECISIONS = {"pending", "approved", "rejected", "conditional-pass"}
OUTPUT_STATUSES = {"candidate", "validated", "approved", "stale"}
DELIVERY_STATUSES = {"candidate", "formal"}
DELIVERY_KINDS = {"report", "contentpack", "html", "ppt"}
RESULT_STATUSES = {"pass", "fail", "pending", "not-reviewed", "approved", "rejected"}
FINDING_STATUSES = {"open", "closed"}
EXECUTION_STATES = {"in-progress", "ready", "delivered"}
GATE_TYPES = {"phase", "customer"}
SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")
SEMVER_RE = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+$")
PRESENTATION_NS = "http://schemas.openxmlformats.org/presentationml/2006/main"
RELATIONSHIPS_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PACKAGE_RELATIONSHIPS_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
SLIDE_RELATIONSHIP_TYPES = {
    f"{RELATIONSHIPS_NS}/slide",
    "http://purl.oclc.org/ooxml/officeDocument/relationships/slide",
}


def _missing(value: Any) -> bool:
    return value is None or value == "" or value == [] or value == {}


def _same_ref(left: Any, right: Any) -> bool:
    if not isinstance(left, dict) or not isinstance(right, dict):
        return False
    return all(left.get(field) == right.get(field) for field in ("id", "version", "sha256", "path"))


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _artifact_ref(ref: Any, label: str, root: Path, errors: list[str]) -> bool:
    if not isinstance(ref, dict):
        errors.append(f"{label}: artifact reference must be an object")
        return False
    valid = True
    for field in ("id", "version", "sha256", "path"):
        if _missing(ref.get(field)) or not isinstance(ref.get(field), str):
            errors.append(f"{label}: missing explicit {field}")
            valid = False
    sha = ref.get("sha256")
    if not isinstance(sha, str) or not SHA256_RE.fullmatch(sha):
        errors.append(f"{label}: sha256 must be 64 hexadecimal characters")
        valid = False
    path_value = ref.get("path")
    if not isinstance(path_value, str):
        return False
    relative_path = Path(path_value)
    if relative_path.is_absolute() or ".." in relative_path.parts:
        errors.append(f"{label}: path must stay below root")
        return False
    try:
        resolved = (root / relative_path).resolve()
        resolved.relative_to(root.resolve())
    except (OSError, ValueError, TypeError):
        errors.append(f"{label}: path escapes root")
        return False
    try:
        exists = resolved.is_file()
    except OSError:
        exists = False
    if not exists:
        errors.append(f"{label}: referenced file does not exist: {path_value}")
        return False
    if valid:
        try:
            actual = _hash_file(resolved)
        except OSError as exc:
            errors.append(f"{label}: cannot read referenced file: {exc}")
            return False
        if actual.lower() != sha.lower():
            errors.append(f"{label}: sha256 does not match file")
            valid = False
    return valid


def _require_string(value: Any, label: str, errors: list[str]) -> None:
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{label}: required non-empty string")


def _validate_page_map(item: dict[str, Any], label: str, errors: list[str]) -> None:
    page_count = item.get("page_count")
    if not isinstance(page_count, int) or isinstance(page_count, bool) or page_count < 1:
        errors.append(f"{label}: page_count must be a positive integer")
        return
    page_map = item.get("page_map")
    if not isinstance(page_map, list) or len(page_map) != page_count:
        errors.append(f"{label}: page_map must contain one entry for every page")
        return
    pages: list[int] = []
    for index, entry in enumerate(page_map):
        entry_label = f"{label}.page_map[{index}]"
        if not isinstance(entry, dict):
            errors.append(f"{entry_label}: entry must be an object")
            continue
        page = entry.get("page")
        if not isinstance(page, int) or isinstance(page, bool) or page < 1:
            errors.append(f"{entry_label}: page must be a positive integer")
        else:
            pages.append(page)
        _require_string(entry.get("source_id"), f"{entry_label}.source_id", errors)
    if sorted(pages) != list(range(1, page_count + 1)):
        errors.append(f"{label}: page_map pages must cover 1..page_count exactly")


def _read_contentpack(path: Path, label: str, errors: list[str]) -> tuple[int, set[str]]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        errors.append(f"{label}: contentpack must be readable JSON: {exc}")
        return 0, set()
    if not isinstance(payload, dict):
        errors.append(f"{label}: contentpack JSON must be an object")
        return 0, set()
    pages = payload.get("slides", payload.get("pages"))
    if not isinstance(pages, list) or not pages:
        errors.append(f"{label}: contentpack JSON must contain non-empty slides/pages")
        return 0, set()
    source_ids: set[str] = set()
    for index, page in enumerate(pages):
        if not isinstance(page, dict):
            errors.append(f"{label}: slides/pages[{index}] requires a source id")
            continue
        page_id = page.get("id")
        slide_id = page.get("slide_id")
        if page_id is not None and slide_id is not None and page_id != slide_id:
            errors.append(f"{label}: conflicting source id and slide_id at slides/pages[{index}]")
        source_id = page_id if page_id is not None else slide_id
        if not isinstance(source_id, str) or not source_id.strip():
            errors.append(f"{label}: slides/pages[{index}] requires a source id")
            continue
        if source_id in source_ids:
            errors.append(f"{label}: duplicate source id {source_id}")
        source_ids.add(source_id)
    return len(pages), source_ids


def _read_ppt_slide_count(path: Path, label: str, errors: list[str]) -> int:
    try:
        with zipfile.ZipFile(path) as archive:
            names = set(archive.namelist())
            if "ppt/presentation.xml" not in names or "ppt/_rels/presentation.xml.rels" not in names:
                errors.append(f"{label}: ppt ZIP requires presentation.xml and presentation relationships")
                return 0
            try:
                presentation = ET.fromstring(archive.read("ppt/presentation.xml"))
                relationships = ET.fromstring(archive.read("ppt/_rels/presentation.xml.rels"))
            except (KeyError, ET.ParseError, UnicodeDecodeError) as exc:
                errors.append(f"{label}: ppt presentation XML is malformed: {exc}")
                return 0

            slide_list = presentation.find(f"{{{PRESENTATION_NS}}}sldIdLst")
            if slide_list is None:
                errors.append(f"{label}: ppt presentation must contain p:sldIdLst")
                return 0
            referenced_rel_ids: list[str] = []
            for slide_id in list(slide_list):
                rel_id = slide_id.attrib.get(f"{{{RELATIONSHIPS_NS}}}id")
                if not isinstance(rel_id, str) or not rel_id:
                    errors.append(f"{label}: every p:sldId must reference a relationship")
                    continue
                if rel_id in referenced_rel_ids:
                    errors.append(f"{label}: duplicate slide relationship id {rel_id}")
                referenced_rel_ids.append(rel_id)
            if not referenced_rel_ids:
                errors.append(f"{label}: ppt presentation must reference at least one slide")
                return 0

            slide_relationships: dict[str, str] = {}
            external_slide_relationships: set[str] = set()
            for relationship in list(relationships):
                if relationship.tag.rsplit("}", 1)[-1] != "Relationship":
                    continue
                if relationship.attrib.get("Type") in SLIDE_RELATIONSHIP_TYPES:
                    rel_id = relationship.attrib.get("Id")
                    target = relationship.attrib.get("Target")
                    if isinstance(rel_id, str) and isinstance(target, str):
                        if rel_id in slide_relationships:
                            errors.append(f"{label}: duplicate slide relationship id {rel_id}")
                        slide_relationships[rel_id] = target
                        if relationship.attrib.get("TargetMode", "").lower() == "external":
                            external_slide_relationships.add(rel_id)

            referenced_targets: set[str] = set()
            for rel_id in referenced_rel_ids:
                target = slide_relationships.get(rel_id)
                if target is None:
                    errors.append(f"{label}: missing slide relationship target for {rel_id}")
                    continue
                if rel_id in external_slide_relationships:
                    errors.append(f"{label}: slide relationship target must be internal: {target}")
                    continue
                if target.startswith("/") or target.startswith("\\") or ".." in target.replace("\\", "/").split("/"):
                    errors.append(f"{label}: slide relationship target escapes ppt root: {target}")
                    continue
                target_path = posixpath.normpath(posixpath.join("ppt", target.replace("\\", "/")))
                if not target_path.startswith("ppt/slides/") or not target_path.endswith(".xml"):
                    errors.append(f"{label}: slide relationship target must be an internal ppt/slides XML: {target}")
                    continue
                if target_path in referenced_targets:
                    errors.append(f"{label}: duplicate referenced slide target {target_path}")
                    continue
                referenced_targets.add(target_path)
                if target_path not in names:
                    errors.append(f"{label}: referenced slide target does not exist: {target_path}")
                    continue
                try:
                    slide_root = ET.fromstring(archive.read(target_path))
                except (KeyError, ET.ParseError, UnicodeDecodeError) as exc:
                    errors.append(f"{label}: referenced slide XML is malformed: {target_path}: {exc}")
                    continue
                if slide_root.tag != f"{{{PRESENTATION_NS}}}sld":
                    errors.append(f"{label}: referenced slide is not a valid p:sld: {target_path}")

            actual_slide_files = {
                name
                for name in names
                if name.startswith("ppt/slides/")
                and name.endswith(".xml")
                and "/" not in name[len("ppt/slides/"):]
            }
            orphan_files = actual_slide_files - referenced_targets
            if orphan_files:
                errors.append(f"{label}: orphan slide files are not referenced by presentation: {sorted(orphan_files)}")
            if actual_slide_files != referenced_targets:
                errors.append(f"{label}: slide files must equal presentation-referenced slides")
            return len(referenced_targets) if referenced_targets else 0
    except (OSError, zipfile.BadZipFile) as exc:
        errors.append(f"{label}: ppt artifact must be a readable ZIP: {exc}")
        return 0


def validate(snapshot: dict[str, Any], root: str | Path) -> list[str]:
    """Return declarative runtime-closure errors; an empty list means valid."""

    errors: list[str] = []
    try:
        root_path = Path(root).resolve()
    except (TypeError, ValueError, OSError) as exc:
        return [f"root: invalid path: {exc}"]
    if not isinstance(snapshot, dict):
        return ["snapshot: top-level value must be an object"]

    for field in ("snapshot_id", "project_id"):
        _require_string(snapshot.get(field), f"snapshot.{field}", errors)
    mode = snapshot.get("mode")
    if mode not in MODES:
        errors.append("snapshot.mode: must be manual-simulation or host-execution")
    execution_state = snapshot.get("execution_state", "ready")
    if execution_state not in EXECUTION_STATES:
        errors.append("snapshot.execution_state: invalid enum")

    tasks = snapshot.get("tasks")
    if not isinstance(tasks, list) or not tasks:
        errors.append("tasks: must be a non-empty list")
        tasks = []
    task_ids: set[str] = set()
    task_records: dict[str, dict[str, Any]] = {}
    output_refs: dict[str, dict[str, Any]] = {}
    output_task: dict[str, str] = {}
    output_stale: set[str] = set()
    task_actors: dict[str, str] = {}

    for index, task in enumerate(tasks):
        label = f"tasks[{index}]"
        if not isinstance(task, dict):
            errors.append(f"{label}: must be an object")
            continue
        task_id = task.get("id")
        _require_string(task_id, f"{label}.id", errors)
        task_key = task_id if isinstance(task_id, str) else label
        if isinstance(task_id, str):
            if task_id in task_ids:
                errors.append(f"{label}: duplicate task id {task_id}")
            task_ids.add(task_id)

        required_ids = task.get("required_input_ids")
        if not isinstance(required_ids, list) or not required_ids or any(not isinstance(item, str) or not item for item in required_ids):
            errors.append(f"{label}.required_input_ids: must explicitly list required artifacts")
            required_ids = []
        elif len(set(required_ids)) != len(required_ids):
            errors.append(f"{label}.required_input_ids: duplicate artifact id")

        inputs = task.get("inputs")
        input_ids: list[str] = []
        input_refs: list[dict[str, Any]] = []
        if not isinstance(inputs, list) or not inputs:
            errors.append(f"{label}.inputs: must be a non-empty list")
            inputs = []
        for input_index, ref in enumerate(inputs):
            ref_label = f"{label}.inputs[{input_index}]"
            _artifact_ref(ref, ref_label, root_path, errors)
            if isinstance(ref, dict) and isinstance(ref.get("id"), str):
                input_ids.append(ref["id"])
                input_refs.append(ref)
        if len(set(input_ids)) != len(input_ids):
            errors.append(f"{label}.inputs: duplicate artifact id")
        if set(input_ids) != set(required_ids) or len(input_ids) != len(required_ids):
            errors.append(f"{label}: inputs must contain every required_input_ids artifact exactly once")

        run = task.get("run")
        actor = None
        if not isinstance(run, dict):
            errors.append(f"{label}.run: explicit run object is required")
        else:
            run_mode = run.get("mode")
            if run_mode not in MODES:
                errors.append(f"{label}.run.mode: must be manual-simulation or host-execution")
            elif run_mode != mode:
                errors.append(f"{label}.run.mode: must match snapshot.mode")
            _require_string(run.get("actor"), f"{label}.run.actor", errors)
            actor = run.get("actor") if isinstance(run.get("actor"), str) else None
            if mode == "host-execution":
                _require_string(task.get("skill_name"), f"{label}.skill_name", errors)
                skill_version = task.get("skill_version")
                if not isinstance(skill_version, str) or not SEMVER_RE.fullmatch(skill_version):
                    errors.append(f"{label}.skill_version: explicit semver required")
                _artifact_ref(run.get("evidence_ref"), f"{label}.run.evidence_ref", root_path, errors)
            elif task.get("skill_version") is not None and (
                not isinstance(task.get("skill_version"), str) or not SEMVER_RE.fullmatch(task.get("skill_version"))
            ):
                errors.append(f"{label}.skill_version: invalid semver")
        if isinstance(task_id, str) and actor:
            task_actors[task_id] = actor

        outputs = task.get("outputs")
        if not isinstance(outputs, list) or not outputs:
            errors.append(f"{label}.outputs: must be a non-empty list")
            outputs = []
        output_ids: set[str] = set()
        for output_index, ref in enumerate(outputs):
            ref_label = f"{label}.outputs[{output_index}]"
            _artifact_ref(ref, ref_label, root_path, errors)
            if not isinstance(ref, dict):
                continue
            output_id = ref.get("id")
            if isinstance(output_id, str):
                if output_id in output_ids or output_id in output_refs:
                    errors.append(f"{ref_label}: duplicate output artifact id {output_id}")
                output_ids.add(output_id)
                output_refs[output_id] = ref
                output_task[output_id] = task_key
            status = ref.get("status")
            if status not in OUTPUT_STATUSES:
                errors.append(f"{ref_label}.status: must be candidate, validated, approved, or stale")
            elif mode == "manual-simulation" and status in {"validated", "approved"}:
                errors.append(f"{ref_label}: manual-simulation cannot mark output {status}")
            depends_on = ref.get("depends_on", [])
            if not isinstance(depends_on, list) or any(not isinstance(item, str) or not item for item in depends_on):
                errors.append(f"{ref_label}.depends_on: must be a list of artifact ids")
        task_records[task_key] = {
            "input_ids": input_ids,
            "input_refs": input_refs,
            "output_ids": list(output_ids),
            "task": task,
        }

    for task_key, record in task_records.items():
        for input_ref in record["input_refs"]:
            input_id = input_ref["id"]
            registered_output = output_refs.get(input_id)
            if registered_output is not None and not _same_ref(registered_output, input_ref):
                errors.append(
                    f"task {task_key}: input {input_id} must match the exact output lineage version/hash/path"
                )

    changed_ids: set[str] = set()
    changes = snapshot.get("upstream_changes", [])
    if not isinstance(changes, list):
        errors.append("upstream_changes: must be a list")
        changes = []
    for index, change in enumerate(changes):
        label = f"upstream_changes[{index}]"
        if not isinstance(change, dict):
            errors.append(f"{label}: must be an object")
            continue
        _require_string(change.get("artifact_id"), f"{label}.artifact_id", errors)
        _require_string(change.get("from_version"), f"{label}.from_version", errors)
        _require_string(change.get("to_version"), f"{label}.to_version", errors)
        if isinstance(change.get("artifact_id"), str):
            changed_ids.add(change["artifact_id"])

    for output_id, ref in output_refs.items():
        if ref.get("status") == "stale":
            output_stale.add(output_id)
    stale_tasks: set[str] = set()
    progress = True
    while progress:
        progress = False
        for task_key, record in task_records.items():
            input_ids = record["input_ids"]
            if task_key not in stale_tasks and (changed_ids.intersection(input_ids) or output_stale.intersection(input_ids)):
                stale_tasks.add(task_key)
                progress = True
            if task_key in stale_tasks:
                for output_id in record["output_ids"]:
                    if output_id not in output_stale:
                        output_stale.add(output_id)
                        progress = True
    for output_id, ref in output_refs.items():
        depends_on = ref.get("depends_on", [])
        if isinstance(depends_on, list) and (changed_ids.intersection(depends_on) or output_stale.intersection(depends_on)):
            output_stale.add(output_id)
        if output_id in output_stale and ref.get("status") != "stale":
            errors.append(f"output {output_id}: upstream change requires status stale")

    reviews = snapshot.get("reviews")
    if not isinstance(reviews, list) or not reviews:
        errors.append("reviews: must be a non-empty list")
        reviews = []
    review_candidates: list[dict[str, Any]] = []
    reviews_by_candidate: dict[str, list[dict[str, Any]]] = {}
    for index, review in enumerate(reviews):
        label = f"reviews[{index}]"
        if not isinstance(review, dict):
            errors.append(f"{label}: must be an object")
            continue
        _require_string(review.get("id"), f"{label}.id", errors)
        candidate = review.get("candidate")
        candidate_valid = _artifact_ref(candidate, f"{label}.candidate", root_path, errors)
        candidate_id = candidate.get("id") if isinstance(candidate, dict) else None
        if candidate_valid and isinstance(candidate, dict):
            review_candidates.append(candidate)
            output = output_refs.get(candidate_id)
            if output is None or not _same_ref(output, candidate):
                errors.append(f"{label}.candidate: must bind an exact task output version/hash/path")
            else:
                reviews_by_candidate.setdefault(candidate_id, []).append(review)
                expected_actor = task_actors.get(output_task.get(candidate_id, ""))
                if expected_actor and review.get("generated_by") != expected_actor:
                    errors.append(f"{label}.generated_by: must match task run.actor")
        _require_string(review.get("generated_by"), f"{label}.generated_by", errors)
        _require_string(review.get("reviewed_by"), f"{label}.reviewed_by", errors)
        if review.get("generated_by") == review.get("reviewed_by"):
            errors.append(f"{label}: reviewer must differ from generator")
        if review.get("reviewer_independent") is not True:
            errors.append(f"{label}: reviewer_independent must be true")

        results = review.get("results")
        if not isinstance(results, dict):
            errors.append(f"{label}.results: technical/professional/customer results must be separate")
        else:
            for result_name in ("technical", "professional", "customer"):
                result = results.get(result_name)
                if not isinstance(result, dict) or result.get("status") not in RESULT_STATUSES:
                    errors.append(f"{label}.results.{result_name}: invalid or missing result status")
                elif mode == "manual-simulation" and result_name == "customer" and result.get("status") == "approved":
                    errors.append(f"{label}.results.customer: manual-simulation cannot approve customer result")

        findings = review.get("findings")
        if not isinstance(findings, list):
            errors.append(f"{label}.findings: must be a list")
            findings = []
        for finding_index, finding in enumerate(findings):
            finding_label = f"{label}.findings[{finding_index}]"
            if not isinstance(finding, dict):
                errors.append(f"{finding_label}: must be an object")
                continue
            _require_string(finding.get("id"), f"{finding_label}.id", errors)
            _require_string(finding.get("owner"), f"{finding_label}.owner", errors)
            _require_string(finding.get("due"), f"{finding_label}.due", errors)
            status = finding.get("status")
            if status not in FINDING_STATUSES:
                errors.append(f"{finding_label}.status: must be open or closed")
            if "blocking" in finding and not isinstance(finding.get("blocking"), bool):
                errors.append(f"{finding_label}.blocking: must be boolean")
            retest = finding.get("retest_evidence")
            if status == "closed":
                if not _artifact_ref(retest, f"{finding_label}.retest_evidence", root_path, errors):
                    errors.append(f"{finding_label}: closed remediation requires retest evidence")
            elif retest is not None:
                _artifact_ref(retest, f"{finding_label}.retest_evidence", root_path, errors)
            if status == "open" and finding.get("blocking", True) and isinstance(results, dict):
                professional = results.get("professional", {})
                if isinstance(professional, dict) and professional.get("status") == "pass":
                    errors.append(f"{finding_label}: open blocking finding cannot coexist with professional pass")

    gate_decisions = snapshot.get("gate_decisions")
    if not isinstance(gate_decisions, list) or not gate_decisions:
        errors.append("gate_decisions: must be a non-empty list")
        gate_decisions = []
    customer_approvals: dict[str, list[dict[str, Any]]] = {}
    for index, gate in enumerate(gate_decisions):
        label = f"gate_decisions[{index}]"
        if not isinstance(gate, dict):
            errors.append(f"{label}: must be an object")
            continue
        _require_string(gate.get("id"), f"{label}.id", errors)
        _require_string(gate.get("gate"), f"{label}.gate", errors)
        gate_mode = gate.get("mode")
        if gate_mode not in MODES:
            errors.append(f"{label}.mode: must be explicit")
        elif gate_mode != mode:
            errors.append(f"{label}.mode: must match snapshot.mode")
        gate_type = gate.get("gate_type", "phase")
        if gate_type not in GATE_TYPES:
            errors.append(f"{label}.gate_type: invalid enum")
        decision = gate.get("decision")
        if decision not in DECISIONS:
            errors.append(f"{label}.decision: invalid enum")
        if mode == "manual-simulation" and decision in {"approved", "conditional-pass"}:
            errors.append(f"{label}: manual-simulation cannot approve")
        if decision in {"approved", "conditional-pass"}:
            candidate = gate.get("candidate")
            candidate_ok = _artifact_ref(candidate, f"{label}.candidate", root_path, errors)
            candidate_id = candidate.get("id") if isinstance(candidate, dict) else None
            if not candidate_ok or not any(_same_ref(candidate, reviewed) for reviewed in review_candidates):
                errors.append(f"{label}.candidate: approval must name an exactly reviewed candidate")
            record_ok = _artifact_ref(gate.get("decision_record_ref"), f"{label}.decision_record_ref", root_path, errors)
            if not record_ok:
                errors.append(f"{label}: approval requires a real decision record reference")
            _require_string(gate.get("decided_by"), f"{label}.decided_by", errors)
            _require_string(gate.get("decided_at"), f"{label}.decided_at", errors)
            if gate_mode != "host-execution":
                errors.append(f"{label}: approval requires host-execution")
            if decision == "approved" and gate_type == "customer" and gate_mode == "host-execution" and candidate_ok and record_ok and isinstance(candidate_id, str):
                customer_approvals.setdefault(candidate_id, []).append(gate)

    for output_id, output in output_refs.items():
        if output.get("status") != "approved":
            continue
        qualifying_review = None
        for review in reviews_by_candidate.get(output_id, []):
            results = review.get("results", {})
            professional = results.get("professional", {}) if isinstance(results, dict) else {}
            findings = review.get("findings", [])
            technical = results.get("technical", {}) if isinstance(results, dict) else {}
            if not isinstance(technical, dict):
                technical = {}
            if not isinstance(professional, dict):
                professional = {}
            if review.get("reviewer_independent") is True and technical.get("status") == "pass" and professional.get("status") == "pass" and all(
                isinstance(finding, dict) and finding.get("status") == "closed" and finding.get("retest_evidence")
                for finding in findings
            ):
                qualifying_review = review
                break
        if qualifying_review is None:
            errors.append(f"output {output_id}: approved output requires independent technical/professional pass and closed findings")
        if output_id not in customer_approvals:
            errors.append(f"output {output_id}: approved output requires customer approved Gate")

    deliveries = snapshot.get("deliveries")
    if not isinstance(deliveries, list):
        errors.append("deliveries: must be a list")
        deliveries = []
    if not deliveries and execution_state != "in-progress":
        errors.append("deliveries: empty deliveries require execution_state=in-progress")

    for index, delivery in enumerate(deliveries):
        label = f"deliveries[{index}]"
        if not isinstance(delivery, dict):
            errors.append(f"{label}: must be an object")
            continue
        _require_string(delivery.get("id"), f"{label}.id", errors)
        status = delivery.get("status")
        if status not in DELIVERY_STATUSES:
            errors.append(f"{label}.status: must be candidate or formal")
        if mode == "manual-simulation" and status == "formal":
            errors.append(f"{label}: manual-simulation cannot produce formal delivery")
        package_page_count = delivery.get("package_page_count")
        if not isinstance(package_page_count, int) or isinstance(package_page_count, bool) or package_page_count < 1:
            errors.append(f"{label}.package_page_count: must be a positive integer")
            package_page_count = None
        items = delivery.get("items")
        if not isinstance(items, list):
            errors.append(f"{label}.items: must be a list")
            items = []
        kinds: set[str] = set()
        contentpack_ids: set[str] = set()
        formal_items: list[tuple[dict[str, Any], dict[str, Any]]] = []
        for item_index, item in enumerate(items):
            item_label = f"{label}.items[{item_index}]"
            if not isinstance(item, dict):
                errors.append(f"{item_label}: must be an object")
                continue
            kind = item.get("kind")
            if kind not in DELIVERY_KINDS:
                errors.append(f"{item_label}.kind: must be report, contentpack, html, or ppt")
            elif kind in kinds:
                errors.append(f"{label}: duplicate delivery kind {kind}")
            else:
                kinds.add(kind)
            artifact = item.get("artifact")
            artifact_ok = _artifact_ref(artifact, f"{item_label}.artifact", root_path, errors)
            _validate_page_map(item, item_label, errors)
            if artifact_ok and isinstance(artifact, dict) and kind == "contentpack":
                count, ids = _read_contentpack(root_path / artifact["path"], item_label, errors)
                contentpack_ids.update(ids)
                if item.get("page_count") != count:
                    errors.append(f"{item_label}: declared page_count must equal actual contentpack JSON count")
            elif artifact_ok and isinstance(artifact, dict) and kind == "ppt":
                actual_count = _read_ppt_slide_count(root_path / artifact["path"], item_label, errors)
                if item.get("page_count") != actual_count:
                    errors.append(f"{item_label}: declared page_count must equal actual PPT ZIP slide count")
            if isinstance(artifact, dict) and status == "formal":
                registered_output = output_refs.get(artifact.get("id"))
                if registered_output is None or not _same_ref(registered_output, artifact):
                    errors.append(f"{item_label}: formal delivery must bind an exact task output")
                elif registered_output.get("status") != "approved":
                    errors.append(f"{item_label}: formal delivery must bind an approved task output")
                formal_items.append((item, artifact))
            if package_page_count is not None and item.get("page_count") != package_page_count:
                _require_string(item.get("page_count_explanation"), f"{item_label}.page_count_explanation", errors)
        if kinds != DELIVERY_KINDS:
            errors.append(f"{label}.items: must map report/contentpack/html/ppt exactly once")
        if contentpack_ids:
            for item_index, item in enumerate(items):
                if not isinstance(item, dict) or not isinstance(item.get("page_map"), list):
                    continue
                for page_index, entry in enumerate(item["page_map"]):
                    if isinstance(entry, dict) and isinstance(entry.get("source_id"), str) and entry["source_id"] not in contentpack_ids:
                        errors.append(f"{label}.items[{item_index}].page_map[{page_index}].source_id: unknown contentpack source id")
            ppt_item = next((item for item in items if isinstance(item, dict) and item.get("kind") == "ppt"), None)
            if isinstance(ppt_item, dict) and isinstance(ppt_item.get("page_map"), list):
                ppt_source_ids = {
                    entry.get("source_id")
                    for entry in ppt_item["page_map"]
                    if isinstance(entry, dict) and isinstance(entry.get("source_id"), str)
                }
                missing_source_ids = contentpack_ids - ppt_source_ids
                if missing_source_ids:
                    errors.append(
                        f"{label}.ppt.page_map: missing contentpack source ids {sorted(missing_source_ids)}"
                    )
        if status == "formal":
            for item, artifact in formal_items:
                candidate_id = artifact.get("id")
                candidate_reviews = reviews_by_candidate.get(candidate_id, [])
                qualifying_review = None
                for review in candidate_reviews:
                    results = review.get("results", {})
                    professional = results.get("professional", {}) if isinstance(results, dict) else {}
                    findings = review.get("findings", [])
                    technical = results.get("technical", {}) if isinstance(results, dict) else {}
                    if not isinstance(technical, dict):
                        technical = {}
                    if not isinstance(professional, dict):
                        professional = {}
                    if review.get("reviewer_independent") is True and technical.get("status") == "pass" and professional.get("status") == "pass" and all(
                        isinstance(finding, dict) and finding.get("status") == "closed" and finding.get("retest_evidence")
                        for finding in findings
                    ):
                        qualifying_review = review
                        break
                if qualifying_review is None:
                    errors.append(f"{label}: formal delivery requires independent technical/professional pass and closed findings for {candidate_id}")
                if candidate_id not in customer_approvals:
                    errors.append(f"{label}: formal delivery requires actual approved customer gate for {candidate_id}")
                if candidate_id in output_stale:
                    errors.append(f"{label}: formal delivery cannot contain stale output {candidate_id}")

    return errors


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args or len(args) > 2:
        print("usage: validate_runtime_closure.py SNAPSHOT.json [ROOT]", file=sys.stderr)
        return 1
    snapshot_path = Path(args[0])
    root = Path(args[1]) if len(args) == 2 else snapshot_path.parent
    try:
        snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
        errors = validate(snapshot, root)
    except (OSError, UnicodeError, json.JSONDecodeError, TypeError, ValueError) as exc:
        errors = [f"unable to read snapshot: {exc}"]
    print(json.dumps({
        "passed": not errors,
        "errors": errors,
        "scope": "runtime closure structure, references, hashes, format counts, review/gate evidence, staleness, and delivery mapping; not execution, document authenticity, or approval",
    }, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
