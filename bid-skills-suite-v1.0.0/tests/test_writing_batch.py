from __future__ import annotations

import hashlib
import json
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

SUITE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SUITE_ROOT / "scripts"))

from writing_batch import WritingBatch  # noqa: E402
from writing_workspace import WorkspaceError  # noqa: E402


class WritingBatchTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = TemporaryDirectory()
        self.project = Path(self.temp.name)
        for name in ("work", "artifacts", "inputs"):
            (self.project / name).mkdir()
        self._write("work/project.json", {"project_id": "P-001", "project_name": "批量测试"})
        self._write("work/writing-settings.json", {"tone": "plain_chinese", "target_words": None,
                                                    "execution_mode": "parallel", "max_parallel": 2, "revision": 1})
        self._write("inputs/source-registry.json", {"project_id": "P-001", "sources": []})
        self._write("artifacts/03-requirements.json", {"project_id": "P-001", "artifact_id": "A03", "revision": 1,
                                                         "data": {"requirements": [{"id": "R-1", "text": "可追溯"}, {"id": "R-2", "text": "可实施"}]}})
        self._write("artifacts/04-scoring.json", {"project_id": "P-001", "artifact_id": "A04", "revision": 1,
                                                   "data": {"items": [{"id": "S-1", "title": "方案", "max_score": 20}]}})
        self._write("artifacts/09-evidence-selection.json", {"project_id": "P-001", "artifact_id": "A09", "revision": 1,
                                                              "data": {"materials": [{"id": "M-1", "title": "证据"}], "selections": []}})
        self._write("artifacts/08-outline.json", {"schema_version": "1.0", "skill_id": "bid-outline-planning",
                                                   "created_at": "2026-10-07T00:00:00Z", "project_id": "P-001",
                                                   "artifact_id": "A08", "revision": 1, "data": {"sections": [
                                                       {"id": "SEC-1", "number": "1", "title": "方案", "parent_id": None,
                                                        "requirement_ids": ["R-1"], "scoring_ids": ["S-1"], "evidence_needed": ["M-1"],
                                                        "visuals_needed": [], "task": "回答方案", "locked": True},
                                                       {"id": "SEC-2", "number": "2", "title": "实施", "parent_id": None,
                                                        "requirement_ids": ["R-2"], "scoring_ids": [], "evidence_needed": [],
                                                        "visuals_needed": [], "task": "回答实施", "locked": False},
                                                   ], "unmapped_ids": []}})
        refs = []
        for artifact_id, relative in (("A03", "artifacts/03-requirements.json"), ("A04", "artifacts/04-scoring.json"),
                                      ("A08", "artifacts/08-outline.json"), ("A09", "artifacts/09-evidence-selection.json")):
            refs.append({"artifact_id": artifact_id, "revision": 1, "relative_path": relative, "sha256": self._digest(relative)})
        self._write("artifacts/11-technical-content.json", {"schema_version": "1.0", "skill_id": "bid-technical-writing",
                                                              "created_at": "2026-10-07T00:00:00Z", "project_id": "P-001",
                                                              "artifact_id": "A11", "revision": 1, "status": "needs_review", "inputs": refs,
                                                              "summary": "草稿", "data": {"chapters": [
                                                                  {"id": "CH-1", "section_id": "SEC-1", "title": "方案", "body_markdown": "旧方案",
                                                                   "base_revision": 0, "requirement_ids": ["R-1"], "design_ids": [], "evidence_ids": ["M-1"],
                                                                   "state": "proposed", "confirmation_ref": None},
                                                                  {"id": "CH-2", "section_id": "SEC-2", "title": "实施", "body_markdown": "旧实施",
                                                                   "base_revision": 0, "requirement_ids": ["R-2"], "design_ids": [], "evidence_ids": [],
                                                                   "state": "proposed", "confirmation_ref": None},
                                                              ], "responses": [], "unresolved_claims": []}, "warnings": [], "blockers": []})

    def tearDown(self) -> None:
        self.temp.cleanup()

    def _write(self, relative: str, value: dict) -> None:
        path = self.project / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def _digest(self, relative: str) -> str:
        return hashlib.sha256((self.project / relative).read_bytes()).hexdigest()

    def _batch(self, batch_id: str = "batch-1") -> WritingBatch:
        return WritingBatch(self.project, batch_id)

    def _proposal(self, batch: WritingBatch, section_id: str, body: str, **overrides: object) -> Path:
        task = batch._state()["tasks"][section_id]
        attempt = task["attempts"][-1]
        payload = {"batch_id": batch.batch_id, "section_id": section_id, "chapter_id": task["chapter_id"],
                   "attempt": attempt["attempt"], "base_revision": batch._state()["snapshot"]["writing"]["revision"],
                   "base_sha256": batch._state()["snapshot"]["writing"]["sha256"], "body_markdown": body,
                   "requirement_ids": task["requirement_ids"]}
        payload.update(overrides)
        path = self.project / attempt["proposal_relative_path"]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False) + "\n", encoding="utf-8")
        return path

    def _ready(self, batch: WritingBatch, section_id: str, agent_id: str, body: str) -> None:
        batch.claim(section_id)
        batch.bind(section_id, agent_id)
        path = self._proposal(batch, section_id, body)
        batch.collect(section_id, path.relative_to(self.project).as_posix())

    def _external_edit(self) -> None:
        path = self.project / "artifacts/11-technical-content.json"
        value = json.loads(path.read_text(encoding="utf-8"))
        value["summary"] = "外部写入"
        path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def test_prepare_context_and_slots_honor_parallel_limit(self) -> None:
        batch = self._batch()
        result = batch.prepare(["SEC-1", "SEC-2"], effective_mode="parallel")
        self.assertEqual(result["effective_limit"], 2)
        first = batch.claim("SEC-1")
        batch.bind("SEC-1", "/root/qcs_write_93")
        second = batch.claim("SEC-2")
        self.assertEqual(second["attempt"], 1)
        context = json.loads((self.project / first["context_path"]).read_text())
        self.assertEqual(context["task"]["requirement_ids"], ["R-1"])
        self.assertNotIn("旧实施", json.dumps(context, ensure_ascii=False))
        self.assertEqual(batch.status()["tasks"][0]["agent_id"], "/root/qcs_write_93")
        with self.assertRaises(WorkspaceError) as caught:
            batch.claim("SEC-1")
        self.assertEqual(caught.exception.code, "batch_slots_full")

    def test_two_real_proposals_collect_and_merge_with_readback(self) -> None:
        batch = self._batch()
        batch.prepare(["SEC-1", "SEC-2"], effective_mode="parallel")
        for section_id, agent_id, body in (("SEC-1", "a-1", "新方案"), ("SEC-2", "a-2", "新实施")):
            batch.claim(section_id)
            batch.bind(section_id, agent_id)
            self._proposal(batch, section_id, body)
            batch.collect(section_id, self._proposal(batch, section_id, body).relative_to(self.project).as_posix())
        result = batch.merge()
        self.assertEqual(result["counts"]["merged"], 2)
        writing = json.loads((self.project / "artifacts/11-technical-content.json").read_text())
        self.assertEqual({row["body_markdown"] for row in writing["data"]["chapters"]}, {"新方案", "新实施"})
        self.assertTrue(result["merge"]["downstream_refresh_required"])

    def test_invalid_inputs_and_effective_mode_are_rejected(self) -> None:
        batch = self._batch()
        with self.assertRaises(WorkspaceError):
            batch.prepare(["SEC-1", "SEC-1"])
        with self.assertRaises(WorkspaceError):
            batch.prepare([])
        with self.assertRaises(WorkspaceError):
            batch.prepare(["SEC-1"], max_attempts=0)
        with self.assertRaises(WorkspaceError):
            batch.prepare(["SEC-1"], effective_mode="unsupported")
        with self.assertRaises(WorkspaceError):
            batch.prepare(["SEC-1"], effective_mode="sequential")
        self.assertEqual(batch.prepare(["SEC-1"], effective_mode="sequential",
                                       effective_mode_reason="native parallel capability unavailable")["effective_mode"], "sequential")
        with self.assertRaises(WorkspaceError):
            WritingBatch(self.project, "bad/id")
        with self.assertRaises(WorkspaceError):
            batch.claim("../SEC-1")

    def test_collect_rejects_empty_foreign_base_and_requirement_mismatch(self) -> None:
        batch = self._batch()
        batch.prepare(["SEC-1"])
        batch.claim("SEC-1")
        batch.bind("SEC-1", "agent-1")
        path = self._proposal(batch, "SEC-1", "")
        with self.assertRaises(WorkspaceError):
            batch.collect("SEC-1", path.relative_to(self.project).as_posix())
        self._proposal(batch, "SEC-1", "ok", requirement_ids=["R-2"])
        with self.assertRaises(WorkspaceError):
            batch.collect("SEC-1", path.relative_to(self.project).as_posix())
        self._proposal(batch, "SEC-1", "ok", requirement_ids=["R-1"], base_revision=999)
        with self.assertRaises(WorkspaceError):
            batch.collect("SEC-1", path.relative_to(self.project).as_posix())
        self._proposal(batch, "SEC-1", "ok", requirement_ids=["R-1"], attempt=True)
        with self.assertRaises(WorkspaceError):
            batch.collect("SEC-1", path.relative_to(self.project).as_posix())
        self._proposal(batch, "SEC-1", "ok", requirement_ids=["R-1"], base_revision=True)
        with self.assertRaises(WorkspaceError):
            batch.collect("SEC-1", path.relative_to(self.project).as_posix())
        self._proposal(batch, "SEC-1", "ok", requirement_ids=["R-1"])
        foreign = self.project / "work/foreign.json"
        foreign.write_text(path.read_text(), encoding="utf-8")
        with self.assertRaises(WorkspaceError):
            batch.collect("SEC-1", "work/foreign.json")

    def test_failure_retries_only_failed_task_and_caps_attempts(self) -> None:
        batch = self._batch()
        batch.prepare(["SEC-1", "SEC-2"], effective_mode="parallel", max_attempts=2)
        batch.claim("SEC-1"); batch.bind("SEC-1", "a1"); batch.fail("SEC-1", "host error")
        retry = batch.claim("SEC-1")
        self.assertEqual(retry["attempt"], 2)
        batch.fail("SEC-1", "second host error")
        with self.assertRaises(WorkspaceError) as caught:
            batch.claim("SEC-1")
        self.assertEqual(caught.exception.code, "attempts_exhausted")
        self.assertEqual(batch.status()["tasks"][1]["status"], "pending")

    def test_drift_and_post_collect_mutation_are_blocked(self) -> None:
        batch = self._batch()
        batch.prepare(["SEC-1"])
        batch.claim("SEC-1"); batch.bind("SEC-1", "a1")
        path = self._proposal(batch, "SEC-1", "ready")
        batch.collect("SEC-1", path.relative_to(self.project).as_posix())
        path.write_text(path.read_text().replace("ready", "tampered"), encoding="utf-8")
        with self.assertRaises(WorkspaceError) as caught:
            batch.merge()
        self.assertEqual(caught.exception.code, "batch_drift")

    def test_ready_proposal_revision_requires_explicit_recollection(self) -> None:
        batch = self._batch()
        batch.prepare(["SEC-1"])
        self._ready(batch, "SEC-1", "agent-1", "初稿")
        old_sha = batch._state()["tasks"]["SEC-1"]["attempts"][-1]["candidate_sha256"]
        path = self._proposal(batch, "SEC-1", "宿主核对后的修改稿")
        with self.assertRaises(WorkspaceError) as caught:
            batch.merge()
        self.assertEqual(caught.exception.code, "batch_drift")
        batch.collect("SEC-1", path.relative_to(self.project).as_posix())
        attempt = batch._state()["tasks"]["SEC-1"]["attempts"][-1]
        self.assertEqual(attempt["agent_id"], "agent-1")
        self.assertEqual(attempt["attempt"], 1)
        self.assertEqual([row["sha256"] for row in attempt["collections"]], [old_sha, self._digest(path.relative_to(self.project).as_posix())])
        self.assertEqual(batch.merge()["counts"]["merged"], 1)
        writing = json.loads((self.project / "artifacts/11-technical-content.json").read_text())
        self.assertEqual(writing["data"]["chapters"][0]["body_markdown"], "宿主核对后的修改稿")
        with self.assertRaises(WorkspaceError):
            batch.collect("SEC-1", path.relative_to(self.project).as_posix())

        batch2 = self._batch("batch-2")
        batch2.prepare(["SEC-1"])
        (self.project / "inputs/source-registry.json").write_text('{"project_id":"P-001","sources":[]}\n', encoding="utf-8")
        with self.assertRaises(WorkspaceError) as caught:
            batch2.claim("SEC-1")
        self.assertEqual(caught.exception.code, "batch_drift")

    def test_partial_merge_resumes_and_path_escape_is_rejected(self) -> None:
        batch = self._batch()
        batch.prepare(["SEC-1", "SEC-2"], effective_mode="parallel")
        for section_id, agent_id, body in (("SEC-1", "a1", "one"), ("SEC-2", "a2", "two")):
            batch.claim(section_id); batch.bind(section_id, agent_id); path = self._proposal(batch, section_id, body)
            batch.collect(section_id, path.relative_to(self.project).as_posix())
        state = batch._state()
        first_head = batch.workspace.save({"expected_revision": 1,
                                            "expected_sha256": state["snapshot"]["writing"]["sha256"],
                                            "chapter_id": "CH-1", "body_markdown": "one"})["writing"]
        state["tasks"]["SEC-1"]["status"] = "merged"
        state["tasks"]["SEC-1"]["attempts"][-1].update({"status": "merged", "merged_revision": first_head["revision"],
                                                           "merged_head_sha256": first_head["sha256"]})
        state["merge"].update({"status": "partial", "head_revision": first_head["revision"],
                                "head_sha256": first_head["sha256"]})
        batch._write_state(state)
        self.assertEqual(batch.merge()["counts"]["merged"], 2)
        with self.assertRaises(WorkspaceError):
            batch.collect("SEC-2", "../outside.json")

    def test_external_edit_between_preflight_and_first_save_is_conflict(self) -> None:
        batch = self._batch()
        batch.prepare(["SEC-1"])
        self._ready(batch, "SEC-1", "agent-1", "one")
        original_save = batch.workspace.save

        def edit_then_save(request: dict) -> dict:
            self._external_edit()
            return original_save(request)

        with patch.object(batch.workspace, "save", side_effect=edit_then_save):
            with self.assertRaises(WorkspaceError) as caught:
                batch.merge()
        self.assertEqual(caught.exception.code, "stale_write")
        self.assertEqual(batch._state()["merge"]["status"], "partial")
        self.assertIsNotNone(batch.status()["drift"])

    def test_external_edit_between_two_saves_keeps_first_checkpoint(self) -> None:
        batch = self._batch()
        batch.prepare(["SEC-1", "SEC-2"], effective_mode="parallel")
        self._ready(batch, "SEC-1", "agent-1", "one")
        self._ready(batch, "SEC-2", "agent-2", "two")
        original_save = batch.workspace.save
        calls = 0

        def save_with_second_call_edit(request: dict) -> dict:
            nonlocal calls
            calls += 1
            if calls == 2:
                self._external_edit()
            return original_save(request)

        with patch.object(batch.workspace, "save", side_effect=save_with_second_call_edit):
            with self.assertRaises(WorkspaceError) as caught:
                batch.merge()
        self.assertEqual(caught.exception.code, "stale_write")
        state = batch._state()
        self.assertEqual(state["tasks"]["SEC-1"]["status"], "merged")
        self.assertEqual(state["tasks"]["SEC-2"]["status"], "ready")
        self.assertEqual(state["merge"]["status"], "partial")
        self.assertIsNotNone(batch.status()["drift"])


if __name__ == "__main__":
    unittest.main()
