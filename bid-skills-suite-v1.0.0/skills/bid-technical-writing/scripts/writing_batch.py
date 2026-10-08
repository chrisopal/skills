#!/usr/bin/env python3
"""Persistent, host-coordinated batch chapter drafting.

This module deliberately does not start agents or call a model.  A host uses
``claim`` to obtain an immutable task context and proposal path, dispatches its
native agent, then calls ``bind``, ``collect``, ``fail`` and ``merge`` with the
actual result.  The JSON state under ``work/writing-batches`` is the durable
coordination record; canonical writing content is changed only by merge.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from writing_workspace import (  # type: ignore
    WorkspaceError,
    WritingWorkspace,
    _copy_json,
    _digest,
    _file_lock,
    _read_json,
    _safe_path,
    _write_atomic,
)


SCHEMA_VERSION = "1.0"
_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_id(value: object, label: str) -> str:
    if not isinstance(value, str) or not _ID_RE.fullmatch(value.strip()):
        raise WorkspaceError(f"{label}无效", "invalid_input")
    return value.strip()


def _agent_id(value: object) -> str:
    """Native task handles may contain slashes; they are metadata only."""
    if not isinstance(value, str) or not value.strip() or len(value.strip()) > 512:
        raise WorkspaceError("agent_id不能为空且不能超过512字符", "invalid_input")
    return value.strip()


def _list_ids(value: object, label: str) -> list[str]:
    if (not isinstance(value, (list, tuple)) or not value
            or any(not isinstance(item, str) or not item.strip() for item in value)):
        raise WorkspaceError(f"{label}必须是非空文本列表", "invalid_input")
    result = [item.strip() for item in value]
    if len(set(result)) != len(result):
        raise WorkspaceError(f"{label}不能重复", "invalid_input")
    return result


def _path_is_safe(project: Path, path: Path) -> None:
    """Reject symlinked project files and directories, including parents."""
    relative = path.relative_to(project)
    current = project
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            raise WorkspaceError("批量上下文路径不能经过符号链接", "path_traversal")


def _read_json_bytes(path: Path) -> dict:
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise WorkspaceError(f"无法读取批量文件：{path.name}", "invalid_project", 422) from exc
    return _parse_json_bytes(path, raw)


def _parse_json_bytes(path: Path, raw: bytes) -> dict:
    try:
        value = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise WorkspaceError(f"无法读取批量文件：{path.name}", "invalid_project", 422) from exc
    if not isinstance(value, dict):
        raise WorkspaceError(f"批量文件顶层必须是对象：{path.name}", "invalid_project", 422)
    return value


def _pick_rows(value: object, ids: set[str], section_ids: set[str]) -> list[dict]:
    """Select only relevant design/material rows without copying an artifact."""
    if not isinstance(value, list):
        return []
    result = []
    for row in value:
        if not isinstance(row, dict):
            continue
        row_id = row.get("id")
        row_sections = row.get("section_ids", row.get("sections", []))
        if isinstance(row_sections, str):
            row_sections = [row_sections]
        if (isinstance(row_id, str) and row_id in ids) or (
            isinstance(row_sections, list) and section_ids.intersection(row_sections)
        ):
            result.append(_copy_json(row))
    return result


class WritingBatch:
    """Coordinate independent chapter proposals for one ``WritingWorkspace``."""

    def __init__(self, project: str | Path, batch_id: str, *, outline_path: str = "artifacts/08-outline.json",
                 writing_path: str = "artifacts/11-technical-content.json"):
        raw_project = Path(project)
        if raw_project.is_symlink():
            raise WorkspaceError("项目路径不能是符号链接", "path_traversal")
        self.workspace = WritingWorkspace(raw_project, outline_path, writing_path)
        self.project = self.workspace.project
        self.batch_id = _safe_id(batch_id, "batch_id")
        self.outline_path = outline_path
        self.writing_path = writing_path
        self.batch_dir = _safe_path(self.project, f"work/writing-batches/{self.batch_id}", "批量目录")
        self.state_path = self.batch_dir / "state.json"
        self.snapshot_path = self.batch_dir / "snapshot.json"
        _path_is_safe(self.project, self.batch_dir)
        _path_is_safe(self.project, self.workspace.outline_path)
        _path_is_safe(self.project, self.workspace.writing_path)

    @classmethod
    def open(cls, project: str | Path, batch_id: str, **kwargs: Any) -> "WritingBatch":
        batch = cls(project, batch_id, **kwargs)
        if not batch.state_path.is_file():
            raise WorkspaceError("批量不存在", "not_found", 404)
        return batch

    @contextmanager
    def _batch_lock(self):
        lock = _safe_path(self.project, "work/.writing-batch.lock", "批量锁")
        lock.parent.mkdir(parents=True, exist_ok=True)
        stream = lock.open("a+", encoding="utf-8")
        try:
            import fcntl
            fcntl.flock(stream.fileno(), fcntl.LOCK_EX)
            yield
        finally:
            try:
                import fcntl
                fcntl.flock(stream.fileno(), fcntl.LOCK_UN)
            finally:
                stream.close()

    def _state(self) -> dict:
        _path_is_safe(self.project, self.state_path)
        if not self.state_path.is_file():
            raise WorkspaceError("批量不存在", "not_found", 404)
        state = _read_json_bytes(self.state_path)
        if state.get("schema_version") != SCHEMA_VERSION or state.get("batch_id") != self.batch_id:
            raise WorkspaceError("批量状态版本或标识无效", "invalid_project", 422)
        return state

    def _write_state(self, state: dict) -> None:
        _path_is_safe(self.project, self.state_path)
        _write_atomic(self.state_path, state)

    def _rel(self, path: Path) -> str:
        return path.relative_to(self.project).as_posix()

    def _assert_snapshot_current(self, state: dict, *, canonical: bool = True) -> dict:
        """Re-read all frozen inputs and reject drift before coordination work."""
        snapshot = state["snapshot"]
        project_meta = self.project / "work/project.json"
        if _digest(project_meta) != snapshot["project_meta"]["sha256"]:
            raise WorkspaceError("项目元数据已变化，请重新准备批量", "batch_drift", 409)
        settings = self.workspace.settings()
        frozen_settings = snapshot["settings"]
        if settings.get("revision") != frozen_settings.get("revision") or settings.get("sha256") != frozen_settings.get("sha256"):
            raise WorkspaceError("写作设置已变化，请重新准备批量", "batch_drift", 409)
        registry = self.project / "inputs/source-registry.json"
        _path_is_safe(self.project, registry)
        actual_registry = _digest(registry) if registry.is_file() else None
        if actual_registry != snapshot["source_registry"].get("sha256"):
            raise WorkspaceError("原件登记表已变化，请重新准备批量", "batch_drift", 409)
        current = _read_json(self.workspace.writing_path)
        upstream = self.workspace._upstream(current)
        if upstream["errors"]:
            raise WorkspaceError("上游输入缺失或已变化：" + "；".join(upstream["errors"]), "upstream_changed", 409)
        for row in (*upstream["refs"], *upstream["sources"]):
            relative = row.get("relative_path")
            if isinstance(relative, str):
                _path_is_safe(self.project, _safe_path(self.project, relative, "上游路径"))
        if _digest(self.workspace.outline_path) != snapshot["outline"]["sha256"]:
            raise WorkspaceError("目录已变化，请重新准备批量", "batch_drift", 409)
        expected_refs = {(row["relative_path"], row.get("expected_sha256")) for row in snapshot["upstream"]["refs"]}
        current_refs = {(row["relative_path"], row.get("expected_sha256")) for row in upstream["refs"]}
        if expected_refs != current_refs or snapshot["upstream"]["sources"] != upstream["sources"]:
            raise WorkspaceError("上游依赖已变化，请重新准备批量", "batch_drift", 409)
        if canonical:
            expected_revision = state["merge"].get("head_revision", snapshot["writing"]["revision"])
            expected_sha = state["merge"].get("head_sha256", snapshot["writing"]["sha256"])
            if current.get("revision") != expected_revision or _digest(self.workspace.writing_path) != expected_sha:
                raise WorkspaceError("正文产物已变化，请核对批量合并检查点", "batch_drift", 409)
        return {"writing": current, "writing_sha256": _digest(self.workspace.writing_path), "upstream": upstream}

    def _solution_context(self, section: dict, chapter: dict) -> dict:
        path = self.project / "artifacts/10-solution-design.json"
        if not path.is_file():
            return {"available": False, "relative_path": "artifacts/10-solution-design.json"}
        artifact = self.workspace._load_artifact(path)
        ids = set(chapter.get("design_ids", []))
        section_ids = {section["id"]}
        decisions = _pick_rows(artifact.get("data", {}).get("decisions", []), ids, section_ids)
        return {"available": True, "relative_path": self._rel(path), "artifact_id": artifact.get("artifact_id"),
                "revision": artifact.get("revision"), "sha256": _digest(path), "decisions": decisions,
                "scope_in": _copy_json(artifact.get("data", {}).get("scope_in", [])),
                "scope_out": _copy_json(artifact.get("data", {}).get("scope_out", []))}

    def _task_context(self, state: dict, task: dict, attempt: int, *, proposal_path: str, context_path: str) -> dict:
        outline = self.workspace._load_artifact(self.workspace.outline_path)
        section = next(item for item in outline.get("data", {}).get("sections", []) if item.get("id") == task["section_id"])
        writing = _read_json(self.workspace.writing_path)
        chapter = next((item for item in writing.get("data", {}).get("chapters", []) if item.get("id") == task["chapter_id"]), None)
        if chapter is None:
            chapter = {"id": task["chapter_id"], "section_id": task["section_id"], "title": section.get("title", ""),
                       "body_markdown": "", "requirement_ids": task["requirement_ids"], "evidence_ids": [], "design_ids": []}
        current_state = self.workspace.state(task["chapter_id"])
        references = current_state["references"]
        return {"schema_version": SCHEMA_VERSION, "batch_id": self.batch_id, "project_id": state["project_id"],
                "section_id": task["section_id"], "chapter_id": task["chapter_id"], "attempt": attempt,
                "base_revision": state["snapshot"]["writing"]["revision"], "base_sha256": state["snapshot"]["writing"]["sha256"],
                "task": {"number": section.get("number", ""), "title": section.get("title", ""),
                         "task_card": section.get("task", section.get("description", "")),
                         "requirement_ids": task["requirement_ids"], "scoring_ids": task["scoring_ids"],
                         "evidence_ids": task["evidence_ids"], "visuals_needed": _copy_json(section.get("visuals_needed", []))},
                "project": _copy_json(state["snapshot"]["project_meta"]),
                "references": {"requirements": references.get("requirements", []), "scoring": references.get("scoring", []),
                               "evidence": references.get("evidence", []), "missing_evidence": references.get("missing_evidence", [])},
                "solution": self._solution_context(section, chapter),
                "existing_chapter": {"title": chapter.get("title", section.get("title", "")),
                                     "body_markdown": chapter.get("body_markdown", "")},
                "settings": _copy_json(state["snapshot"]["settings"]),
                "resolved_policy": _copy_json(current_state.get("chapter_policy")),
                "proposal_relative_path": proposal_path, "context_relative_path": context_path,
                "instructions": "仅写入 proposal_relative_path；不得修改项目正文或其它文件。"}

    def prepare(self, section_ids: list[str], *, max_attempts: int = 2, effective_mode: str | None = None,
                effective_mode_reason: str | None = None) -> dict:
        section_ids = _list_ids(section_ids, "section_id")
        if isinstance(max_attempts, bool) or not isinstance(max_attempts, int) or not 1 <= max_attempts <= 10:
            raise WorkspaceError("max_attempts 必须是 1 到 10 的整数", "invalid_input")
        with self._batch_lock():
            if self.batch_dir.exists():
                raise WorkspaceError("batch_id 已存在，不能覆盖批量状态", "batch_exists", 409)
            if self.project / "work/project.json" == self.batch_dir:
                raise WorkspaceError("批量目录无效", "path_traversal")
            current = _read_json(self.workspace.writing_path)
            upstream = self.workspace._upstream(current)
            if upstream["errors"]:
                raise WorkspaceError("上游输入缺失或已变化：" + "；".join(upstream["errors"]), "upstream_changed", 409)
            settings = self.workspace.settings()
            if effective_mode is None:
                effective_mode = settings["execution_mode"]
            if effective_mode not in {"parallel", "sequential"}:
                raise WorkspaceError("effective_mode 必须是 parallel 或 sequential", "invalid_input")
            reason = (effective_mode_reason or "").strip()
            if effective_mode != settings["execution_mode"] and not reason:
                raise WorkspaceError("effective_mode与写作设置不一致时必须记录原因", "invalid_input")
            if settings["execution_mode"] == "sequential" and effective_mode == "parallel":
                raise WorkspaceError("当前写作设置只允许串行执行", "invalid_input")
            effective_limit = 1 if effective_mode == "sequential" else settings["max_parallel"]
            outline = self.workspace._load_artifact(self.workspace.outline_path)
            sections = outline.get("data", {}).get("sections", [])
            by_id = {row.get("id"): row for row in sections if isinstance(row, dict)}
            missing = [item for item in section_ids if item not in by_id]
            if missing:
                raise WorkspaceError("section_id 不在当前目录中：" + ",".join(missing), "not_found", 404)
            tasks = {}
            writing_chapters = current.get("data", {}).get("chapters", [])
            for section_id in section_ids:
                section = by_id[section_id]
                chapter = next((item for item in writing_chapters if isinstance(item, dict) and
                                (item.get("section_id") == section_id or item.get("id") == section_id)), None)
                chapter_id = (chapter or {}).get("id", section_id)
                view = self.workspace.state(chapter_id)
                chapter = view["chapter"]
                requirement_ids = _list_ids(section.get("requirement_ids", []), f"{section_id}.requirement_ids") if section.get("requirement_ids", []) else []
                scoring_ids = _list_ids(chapter.get("scoring_ids", section.get("scoring_ids", [])), f"{section_id}.scoring_ids") if (chapter.get("scoring_ids", section.get("scoring_ids", []))) else []
                evidence_ids = _list_ids(chapter.get("evidence_ids", section.get("evidence_needed", [])), f"{section_id}.evidence_ids") if (chapter.get("evidence_ids", section.get("evidence_needed", []))) else []
                tasks[section_id] = {"section_id": section_id, "chapter_id": chapter["id"], "title": section.get("title", ""),
                                     "requirement_ids": requirement_ids, "scoring_ids": scoring_ids, "evidence_ids": evidence_ids,
                                     "status": "pending", "attempts": []}
            project_meta_path = self.project / "work/project.json"
            registry_path = self.project / "inputs/source-registry.json"
            _path_is_safe(self.project, project_meta_path)
            _path_is_safe(self.project, registry_path)
            registry_value = _copy_json(_read_json(registry_path)) if registry_path.is_file() else None
            snapshot = {"project_meta": {"relative_path": "work/project.json", "value": _copy_json(_read_json(project_meta_path)), "sha256": _digest(project_meta_path)},
                        "settings": _copy_json(settings),
                        "outline": {"relative_path": self._rel(self.workspace.outline_path), "artifact_id": outline.get("artifact_id"), "revision": outline.get("revision"), "sha256": _digest(self.workspace.outline_path)},
                        "writing": {"relative_path": self._rel(self.workspace.writing_path), "artifact_id": current.get("artifact_id"), "revision": current.get("revision"), "sha256": _digest(self.workspace.writing_path)},
                        "upstream": {"refs": _copy_json(upstream["refs"]), "sources": _copy_json(upstream["sources"]), "errors": []},
                        "source_registry": {"relative_path": "inputs/source-registry.json", "value": registry_value,
                                            "sha256": _digest(registry_path) if registry_path.is_file() else None}}
            self.batch_dir.mkdir(parents=True, exist_ok=False)
            _path_is_safe(self.project, self.batch_dir)
            state = {"schema_version": SCHEMA_VERSION, "batch_id": self.batch_id, "project_id": self.workspace.project_id,
                     "created_at": _now(), "effective_mode": effective_mode, "effective_mode_reason": reason,
                     "configured_execution_mode": settings["execution_mode"], "max_parallel": settings["max_parallel"],
                     "effective_limit": effective_limit, "max_attempts": max_attempts, "snapshot": snapshot, "tasks": tasks,
                     "merge": {"status": "pending", "head_revision": current.get("revision"), "head_sha256": _digest(self.workspace.writing_path),
                               "downstream_refresh_required": False, "downstream_refresh_scope": []}}
            _write_atomic(self.snapshot_path, {"schema_version": SCHEMA_VERSION, "batch_id": self.batch_id, "snapshot": snapshot, "tasks": tasks})
            _write_atomic(self.state_path, state)
        return self.status()

    def claim(self, section_id: str) -> dict:
        section_id = _safe_id(section_id, "section_id")
        with self._batch_lock():
            state = self._state()
            self._assert_snapshot_current(state)
            task = state["tasks"].get(section_id)
            if task is None:
                raise WorkspaceError("section_id 不在批量中", "not_found", 404)
            active = sum(1 for item in state["tasks"].values() if item["status"] in {"dispatching", "running"})
            if active >= state["effective_limit"]:
                raise WorkspaceError("已达到批量并行槽位上限", "batch_slots_full", 409)
            if task["status"] not in {"pending", "failed"}:
                raise WorkspaceError("章节当前不可领取：" + task["status"], "invalid_state", 409)
            if len(task["attempts"]) >= state["max_attempts"]:
                raise WorkspaceError("章节已达到最大尝试次数", "attempts_exhausted", 409)
            attempt = len(task["attempts"]) + 1
            attempt_dir = self.batch_dir / "tasks" / section_id / f"attempt-{attempt:03d}"
            proposal = attempt_dir / "proposal.json"
            context = attempt_dir / "task.json"
            _path_is_safe(self.project, attempt_dir)
            proposal_rel, context_rel = self._rel(proposal), self._rel(context)
            task_context = self._task_context(state, task, attempt, proposal_path=proposal_rel, context_path=context_rel)
            _write_atomic(context, task_context)
            task["attempts"].append({"attempt": attempt, "status": "dispatching", "agent_id": None,
                                      "context_relative_path": context_rel, "context_sha256": _digest(context),
                                      "proposal_relative_path": proposal_rel, "proposal_sha256": None,
                                      "failure_reason": None, "candidate_sha256": None, "merged_revision": None,
                                      "merged_head_sha256": None})
            task["status"] = "dispatching"
            self._write_state(state)
            return {"batch_id": self.batch_id, "section_id": section_id, "chapter_id": task["chapter_id"],
                    "attempt": attempt, "status": "dispatching", "context_path": context_rel,
                    "proposal_path": proposal_rel, "dispatch_required": True}

    def bind(self, section_id: str, agent_id: str) -> dict:
        section_id, agent_id = _safe_id(section_id, "section_id"), _agent_id(agent_id)
        with self._batch_lock():
            state = self._state(); self._assert_snapshot_current(state)
            task = state["tasks"].get(section_id)
            if task is None:
                raise WorkspaceError("section_id 不在批量中", "not_found", 404)
            if task["status"] != "dispatching":
                raise WorkspaceError("章节不在等待绑定状态", "invalid_state", 409)
            attempt = task["attempts"][-1]
            attempt["agent_id"] = agent_id
            attempt["status"] = "running"
            task["status"] = "running"
            self._write_state(state)
            return {"batch_id": self.batch_id, "section_id": section_id, "attempt": attempt["attempt"],
                    "status": "running", "agent_id": agent_id, "proposal_path": attempt["proposal_relative_path"]}

    def fail(self, section_id: str, reason: str) -> dict:
        section_id = _safe_id(section_id, "section_id")
        if not isinstance(reason, str) or not reason.strip():
            raise WorkspaceError("失败原因不能为空", "invalid_input")
        with self._batch_lock():
            state = self._state(); task = state["tasks"].get(section_id)
            if task is None:
                raise WorkspaceError("section_id 不在批量中", "not_found", 404)
            if task["status"] not in {"dispatching", "running"}:
                raise WorkspaceError("章节当前不可标记失败", "invalid_state", 409)
            attempt = task["attempts"][-1]
            attempt.update({"status": "failed", "failure_reason": reason.strip()})
            task["status"] = "failed"
            self._write_state(state)
            return {"batch_id": self.batch_id, "section_id": section_id, "attempt": attempt["attempt"], "status": "failed"}

    def collect(self, section_id: str, proposal: str) -> dict:
        section_id = _safe_id(section_id, "section_id")
        with self._batch_lock():
            state = self._state(); self._assert_snapshot_current(state)
            task = state["tasks"].get(section_id)
            if task is None:
                raise WorkspaceError("section_id 不在批量中", "not_found", 404)
            if task["status"] not in {"running", "ready"}:
                raise WorkspaceError("只能收集已绑定或待合并任务的提案", "invalid_state", 409)
            attempt = task["attempts"][-1]
            path = _safe_path(self.project, proposal, "proposal路径", True)
            _path_is_safe(self.project, path)
            if self._rel(path) != attempt["proposal_relative_path"]:
                raise WorkspaceError("proposal路径不是当前尝试的专用输出路径", "invalid_input")
            context_path = _safe_path(self.project, attempt["context_relative_path"], "任务上下文", True)
            if _digest(context_path) != attempt["context_sha256"]:
                raise WorkspaceError("任务上下文已被修改", "batch_drift", 409)
            try:
                proposal_bytes = path.read_bytes()
            except OSError as exc:
                raise WorkspaceError("无法读取proposal", "invalid_project", 422) from exc
            candidate = _parse_json_bytes(path, proposal_bytes)
            allowed = {"batch_id", "section_id", "chapter_id", "attempt", "base_revision", "base_sha256", "body_markdown", "requirement_ids", "trace_links", "evidence_references"}
            if set(candidate) - allowed:
                raise WorkspaceError("proposal包含不支持的字段", "invalid_input")
            if candidate.get("batch_id") != self.batch_id or candidate.get("section_id") != section_id or candidate.get("chapter_id") != task["chapter_id"]:
                raise WorkspaceError("proposal身份与批量任务不一致", "project_mismatch", 422)
            proposal_attempt = candidate.get("attempt")
            proposal_base_revision = candidate.get("base_revision")
            if (isinstance(proposal_attempt, bool) or not isinstance(proposal_attempt, int) or proposal_attempt <= 0
                    or isinstance(proposal_base_revision, bool) or not isinstance(proposal_base_revision, int)
                    or proposal_base_revision <= 0):
                raise WorkspaceError("proposal的attempt和base_revision必须是正整数", "invalid_input")
            if proposal_attempt != attempt["attempt"] or proposal_base_revision != state["snapshot"]["writing"]["revision"] or candidate.get("base_sha256") != state["snapshot"]["writing"]["sha256"]:
                raise WorkspaceError("proposal的attempt或正文基线不一致", "stale_write", 409)
            body = candidate.get("body_markdown")
            if not isinstance(body, str) or not body.strip():
                raise WorkspaceError("proposal正文不能为空", "invalid_input")
            if candidate.get("requirement_ids") != task["requirement_ids"]:
                raise WorkspaceError("proposal requirement_ids必须等于任务分配列表", "invalid_input")
            for optional in ("trace_links", "evidence_references"):
                if optional in candidate and not isinstance(candidate[optional], list):
                    raise WorkspaceError(f"proposal的{optional}必须是列表", "invalid_input")
            candidate_sha = hashlib.sha256(proposal_bytes).hexdigest()
            collections = attempt.setdefault("collections", [])
            # Preserve the previous receipt when reopening a batch written
            # before collection history was introduced.
            if not collections and attempt.get("candidate_sha256"):
                collections.append({"sha256": attempt["candidate_sha256"], "collected_at": None})
            if not collections or collections[-1]["sha256"] != candidate_sha:
                collections.append({"sha256": candidate_sha, "collected_at": _now()})
            attempt.update({"status": "ready", "proposal_sha256": candidate_sha, "candidate_sha256": candidate_sha,
                            "trace_links_present": isinstance(candidate.get("trace_links"), list),
                            "evidence_references_present": isinstance(candidate.get("evidence_references"), list)})
            task["status"] = "ready"
            self._write_state(state)
            return {"batch_id": self.batch_id, "section_id": section_id, "attempt": attempt["attempt"],
                    "status": "ready", "proposal_path": attempt["proposal_relative_path"], "proposal_sha256": candidate_sha}

    def merge(self) -> dict:
        with self._batch_lock():
            state = self._state()
            current_info = self._assert_snapshot_current(state, canonical=False)
            expected_head_revision = state["merge"].get("head_revision", state["snapshot"]["writing"]["revision"])
            expected_head_sha = state["merge"].get("head_sha256", state["snapshot"]["writing"]["sha256"])
            if (current_info["writing"].get("revision") != expected_head_revision
                    or current_info["writing_sha256"] != expected_head_sha):
                raise WorkspaceError("正文产物在批量合并外发生变化", "stale_write", 409)
            pending = [task for task in state["tasks"].values() if task["status"] not in {"merged"}]
            if any(task["status"] != "ready" for task in pending):
                raise WorkspaceError("只有全部选中章节ready后才能合并", "batch_not_ready", 409)
            # Preflight every candidate before the first canonical save.  A bad
            # proposal therefore cannot leave a partial merge or mutate state.
            for task in pending:
                attempt = task["attempts"][-1]
                path = _safe_path(self.project, attempt["proposal_relative_path"], "proposal路径", True)
                _path_is_safe(self.project, path)
                proposal_bytes = path.read_bytes()
                if hashlib.sha256(proposal_bytes).hexdigest() != attempt["candidate_sha256"]:
                    raise WorkspaceError("proposal在收集后已被修改", "batch_drift", 409)
                candidate = _parse_json_bytes(path, proposal_bytes)
                if (candidate.get("batch_id") != self.batch_id or candidate.get("section_id") != task["section_id"]
                        or candidate.get("chapter_id") != task["chapter_id"]):
                    raise WorkspaceError("proposal身份已变化", "project_mismatch", 422)
                proposal_attempt = candidate.get("attempt")
                proposal_base_revision = candidate.get("base_revision")
                if (isinstance(proposal_attempt, bool) or not isinstance(proposal_attempt, int) or proposal_attempt <= 0
                        or isinstance(proposal_base_revision, bool) or not isinstance(proposal_base_revision, int)
                        or proposal_base_revision <= 0):
                    raise WorkspaceError("proposal的attempt和base_revision必须是正整数", "invalid_input")
                if (proposal_attempt != attempt["attempt"]
                        or proposal_base_revision != state["snapshot"]["writing"]["revision"]
                        or candidate.get("base_sha256") != state["snapshot"]["writing"]["sha256"]
                        or candidate.get("requirement_ids") != task["requirement_ids"]):
                    raise WorkspaceError("proposal的基线、尝试或需求列表已变化", "stale_write", 409)
                if not isinstance(candidate.get("body_markdown"), str) or not candidate["body_markdown"].strip():
                    raise WorkspaceError("proposal正文不能为空", "invalid_input")
            for task in state["tasks"].values():
                if task["status"] == "merged":
                    continue
                attempt = task["attempts"][-1]
                path = _safe_path(self.project, attempt["proposal_relative_path"], "proposal路径", True)
                _path_is_safe(self.project, path)
                try:
                    proposal_bytes = path.read_bytes()
                    if hashlib.sha256(proposal_bytes).hexdigest() != attempt["candidate_sha256"]:
                        raise WorkspaceError("proposal在收集后已被修改", "batch_drift", 409)
                    candidate = _parse_json_bytes(path, proposal_bytes)
                    if (candidate.get("batch_id") != self.batch_id or candidate.get("section_id") != task["section_id"]
                            or candidate.get("chapter_id") != task["chapter_id"]):
                        raise WorkspaceError("proposal身份已变化", "project_mismatch", 422)
                    current = _read_json(self.workspace.writing_path)
                    current_sha = _digest(self.workspace.writing_path)
                    if (current.get("revision") != expected_head_revision or current_sha != expected_head_sha):
                        raise WorkspaceError("正文产物在保存前已被其他进程修改", "stale_write", 409)
                    result = self.workspace.save({"expected_revision": expected_head_revision,
                                                 "expected_sha256": expected_head_sha, "chapter_id": task["chapter_id"],
                                                 "body_markdown": candidate["body_markdown"]})
                    new_writing = result["writing"]
                    new_chapter = result.get("chapter") or {}
                    new_sha = new_writing["sha256"]
                    if (new_writing.get("revision") != expected_head_revision + 1
                            or new_chapter.get("body_markdown") != candidate["body_markdown"]):
                        raise WorkspaceError("保存返回的正文版本或章节正文不明确", "stale_write", 409)
                    # WritingWorkspace.save releases its lock before returning;
                    # hold the same canonical lock while reading back and
                    # checkpointing so an intervening writer cannot be adopted.
                    with _file_lock(self.project):
                        reread = _read_json(self.workspace.writing_path)
                        reread_sha = _digest(self.workspace.writing_path)
                        if (reread.get("revision") != expected_head_revision + 1 or reread_sha != new_sha):
                            raise WorkspaceError("保存后正文被其他进程修改，无法确认合并头", "stale_write", 409)
                        attempt.update({"status": "merged", "merged_revision": new_writing["revision"],
                                        "merged_head_sha256": new_sha})
                        task["status"] = "merged"
                        state["merge"].update({"status": "partial", "head_revision": new_writing["revision"],
                                                "head_sha256": new_sha})
                        self._write_state(state)
                except Exception as exc:
                    state["merge"]["status"] = "partial"
                    state["merge"]["conflict_reason"] = str(exc)
                    self._write_state(state)
                    raise
                expected_head_revision, expected_head_sha = new_writing["revision"], new_sha
            state["merge"].update({"status": "merged", "downstream_refresh_required": True,
                                    "downstream_refresh_scope": ["writing_trace", "visuals", "layout", "review", "export"]})
            self._write_state(state)
            return self.status()

    def status(self) -> dict:
        state = self._state()
        try:
            drift = self._assert_snapshot_current(state, canonical=True)
            drift_error = None
        except WorkspaceError as exc:
            drift, drift_error = None, {"code": exc.code, "message": str(exc)}
        rows = []
        for task in state["tasks"].values():
            current = task["attempts"][-1] if task["attempts"] else None
            rows.append({"section_id": task["section_id"], "chapter_id": task["chapter_id"], "title": task["title"],
                         "status": task["status"], "attempt": current.get("attempt") if current else 0,
                         "agent_id": current.get("agent_id") if current else None,
                         "proposal_path": current.get("proposal_relative_path") if current else None})
        return {"batch_id": self.batch_id, "project_id": state["project_id"], "effective_mode": state["effective_mode"],
                "effective_limit": state["effective_limit"], "max_attempts": state["max_attempts"], "tasks": rows,
                "counts": {status: sum(1 for task in rows if task["status"] == status) for status in ("pending", "failed", "dispatching", "running", "ready", "merged")},
                "merge": _copy_json(state["merge"]), "drift": drift_error, "state_path": self._rel(self.state_path)}


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Coordinate host-native batch chapter drafting")
    parser.add_argument("command", choices=("prepare", "claim", "bind", "collect", "fail", "merge", "status"))
    parser.add_argument("--project", required=True)
    parser.add_argument("--batch-id", required=True)
    parser.add_argument("--section-id", action="append", default=[])
    parser.add_argument("--max-attempts", type=int, default=2)
    parser.add_argument("--effective-mode", choices=("parallel", "sequential"), default=None)
    parser.add_argument("--effective-mode-reason", default="")
    parser.add_argument("--agent-id")
    parser.add_argument("--proposal")
    parser.add_argument("--reason")
    parser.add_argument("--outline-path", default="artifacts/08-outline.json")
    parser.add_argument("--writing-path", default="artifacts/11-technical-content.json")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        kwargs = {"outline_path": args.outline_path, "writing_path": args.writing_path}
        batch = WritingBatch(args.project, args.batch_id, **kwargs)
        if args.command == "prepare":
            result = batch.prepare(args.section_id, max_attempts=args.max_attempts, effective_mode=args.effective_mode,
                                   effective_mode_reason=args.effective_mode_reason)
        elif args.command == "claim":
            result = batch.claim(args.section_id[0])
        elif args.command == "bind":
            result = batch.bind(args.section_id[0], args.agent_id or "")
        elif args.command == "collect":
            result = batch.collect(args.section_id[0], args.proposal or "")
        elif args.command == "fail":
            result = batch.fail(args.section_id[0], args.reason or "")
        elif args.command == "merge":
            result = batch.merge()
        else:
            result = batch.status()
    except (WorkspaceError, IndexError) as exc:
        print(json.dumps({"error": {"code": getattr(exc, "code", "invalid_input"), "message": str(exc)}}, ensure_ascii=False), file=sys.stderr)
        return getattr(exc, "status", 2) if isinstance(exc, WorkspaceError) else 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
