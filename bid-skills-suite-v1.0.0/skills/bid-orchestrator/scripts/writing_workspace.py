#!/usr/bin/env python3
"""Bounded local Markdown writing workspace for the portable bid skills suite."""
from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import mimetypes
import os
import re
import tempfile
from contextlib import contextmanager
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from outline_view import ordered_sections
from writing_policy import POLICY_DEFAULTS, VISUAL_POLICY_DEFAULTS, normalize_settings, resolve_policy


SUITE_ROOT = Path(__file__).resolve().parents[1]
UI_ROOT = SUITE_ROOT / "assets" / "ui"
DEFAULT_SETTINGS = {
    **POLICY_DEFAULTS,
    "tone": "plain_chinese",
    "target_words": None,
    "execution_mode": "sequential",
    "max_parallel": 1,
    "guidance": "由宿主总控读取后按章节启动子Agent并汇总；保存设置本身不启动任务。",
    "visuals": {
        **VISUAL_POLICY_DEFAULTS,
        "enabled": True,
        "diagram_engine": "auto",
        "diagram_theme": "reference",
        "diagram_format": "svg",
        "layout_template": "auto",
        "architecture_layers": None,
        "image_mode": "host",
        "tool": "auto",
        "model": "",
        "style": "企业概念示意",
        "aspect_ratio": "16:9",
        "max_images": 2,
    },
}


class WorkspaceError(ValueError):
    """Expected client or project data error with a stable response code."""

    def __init__(self, message: str, code: str = "invalid_input", status: int = 400):
        super().__init__(message)
        self.code = code
        self.status = status


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def _read_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise WorkspaceError(f"缺少文件：{path.name}", "missing_file", 404) from exc
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise WorkspaceError(f"无法读取 JSON：{path.name}", "invalid_project", 422) from exc
    if not isinstance(value, dict):
        raise WorkspaceError(f"JSON 顶层必须是对象：{path.name}", "invalid_project", 422)
    return value


def _write_atomic(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp_name, path)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)


def _write_text_atomic(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(value)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp_name, path)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)


def _write_bytes_atomic(path: Path, value: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(value)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp_name, path)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)


def _safe_path(root: Path, value: str, label: str, must_exist: bool = False) -> Path:
    if not isinstance(value, str) or not value.strip():
        raise WorkspaceError(f"{label}不能为空", "invalid_input")
    candidate = Path(value)
    if candidate.is_absolute() or ".." in candidate.parts:
        raise WorkspaceError(f"{label}必须位于项目内", "path_traversal")
    result = (root / candidate).resolve()
    if not result.is_relative_to(root):
        raise WorkspaceError(f"{label}越过项目目录", "path_traversal")
    if must_exist and not result.is_file():
        raise WorkspaceError(f"缺少{label}：{value}", "missing_file", 404)
    return result


def _json_digest(path: Path) -> str:
    return _digest(path)


def _json_input(path: Path, project_id: str) -> dict:
    payload = _read_json(path)
    if payload.get("project_id") not in (None, project_id):
        raise WorkspaceError(f"项目 ID 不一致：{path.name}", "project_mismatch", 422)
    return payload


def _relative(project: Path, path: Path) -> str:
    return path.relative_to(project).as_posix()


@contextmanager
def _file_lock(project: Path):
    """Serialize writes across processes with an explicit advisory lock."""
    lock_path = _safe_path(project, "work/.writing-workspace.lock", "写作锁")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    stream = None
    fallback = False
    try:
        try:
            import fcntl
        except ImportError:  # pragma: no cover - O_EXCL fallback rejects concurrent owners.
            fcntl = None
        if fcntl:
            stream = lock_path.open("a+", encoding="utf-8")
            fcntl.flock(stream.fileno(), fcntl.LOCK_EX)
            yield
        else:
            try:
                fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            except FileExistsError as exc:
                raise WorkspaceError("已有写作进程占用锁；确认进程已退出后清理锁文件。", "lock_busy", 409) from exc
            stream = os.fdopen(fd, "w", encoding="utf-8")
            fallback = True
            stream.write(json.dumps({"pid": os.getpid(), "at": _now()}))
            stream.flush()
            yield
    finally:
        if fcntl and stream is not None:
            fcntl.flock(stream.fileno(), fcntl.LOCK_UN)
        if stream is not None:
            stream.close()
        if fallback:
            lock_path.unlink(missing_ok=True)


def _copy_json(value: object) -> object:
    return json.loads(json.dumps(value, ensure_ascii=False))


class WritingWorkspace:
    """Read and propose edits to one technical writing artifact."""

    def __init__(self, project: str | Path, outline_path: str, writing_path: str):
        self.project = Path(project).resolve()
        if not self.project.is_dir():
            raise WorkspaceError("项目目录不存在", "invalid_project", 404)
        self.outline_path = _safe_path(self.project, outline_path, "目录路径", True)
        self.writing_path = _safe_path(self.project, writing_path, "写作产物路径", True)
        self.project_meta_path = _safe_path(self.project, "work/project.json", "项目元数据", True)
        self.project_id = self._load_project_id()
        self._validate_artifact_identity(self.outline_path)
        self._validate_artifact_identity(self.writing_path)

    def _load_project_id(self) -> str:
        value = _read_json(self.project_meta_path).get("project_id")
        if not isinstance(value, str) or not value.strip():
            raise WorkspaceError("项目元数据缺少 project_id", "project_mismatch", 422)
        return value.strip()

    def _validate_artifact_identity(self, path: Path) -> dict:
        payload = _json_input(path, self.project_id)
        expected_skill = "bid-technical-writing" if path == self.writing_path else "bid-outline-planning"
        if payload.get("skill_id") != expected_skill:
            raise WorkspaceError(f"{path.name} skill_id 不匹配", "project_mismatch", 422)
        if payload.get("project_id") != self.project_id:
            raise WorkspaceError(f"{path.name} project_id 不匹配", "project_mismatch", 422)
        return payload

    def _load_artifact(self, path: Path) -> dict:
        payload = _json_input(path, self.project_id)
        if path.is_relative_to(self.project / "artifacts") and payload.get("project_id") != self.project_id:
            raise WorkspaceError(f"{path.name} project_id 不匹配", "project_mismatch", 422)
        return payload

    def _settings_path(self) -> Path:
        return _safe_path(self.project, "work/writing-settings.json", "写作设置")

    @staticmethod
    def _migrate_legacy_settings(value: dict) -> tuple[dict, bool]:
        """Translate the retired diagram_renderer field once for persisted settings."""
        candidate = _copy_json(value)
        visuals = candidate.get("visuals")
        if not isinstance(visuals, dict) or "diagram_renderer" not in visuals:
            return candidate, False
        old_value = visuals.pop("diagram_renderer")
        legacy_engine = {"svg": "auto", "mermaid": "mermaid", "auto": "auto"}.get(old_value)
        if legacy_engine is None:
            raise WorkspaceError("visuals.diagram_renderer 无效", "invalid_input")
        if "diagram_engine" in visuals or "diagram_format" in visuals:
            raise WorkspaceError("旧 diagram_renderer 不能与新图表设置同时存在", "invalid_input")
        visuals["diagram_engine"] = legacy_engine
        visuals["diagram_format"] = "svg"
        return candidate, True

    def _settings_snapshot(self, *, migrate: bool, locked: bool = False) -> dict:
        path = self._settings_path()
        value = _read_json(path)
        candidate, migrated = self._migrate_legacy_settings(value)
        result = self._validate_settings(candidate)
        try:
            normalize_settings(result, {s['id'] for s in self._load_artifact(self.outline_path)['data']['sections']})
        except ValueError as exc:
            raise WorkspaceError(str(exc), "invalid_input") from exc
        result["revision"] = value.get("revision", 0)
        if migrated and migrate:
            if locked:
                _write_atomic(path, result)
            else:
                with _file_lock(self.project):
                    current = _read_json(path)
                    current_candidate, current_migrated = self._migrate_legacy_settings(current)
                    if current_migrated:
                        current_result = self._validate_settings(current_candidate)
                        current_result["revision"] = current.get("revision", 0)
                        _write_atomic(path, current_result)
                        result = current_result
                    else:
                        result = self._validate_settings(current)
                        result["revision"] = current.get("revision", 0)
            result["sha256"] = _digest(path)
        else:
            result["sha256"] = _digest(path)
        return result

    def settings(self) -> dict:
        path = self._settings_path()
        if not path.is_file():
            result = _copy_json(DEFAULT_SETTINGS)
            result.update({"revision": 0, "sha256": ""})
            return result
        return self._settings_snapshot(migrate=True)

    @staticmethod
    def _validate_settings(value: dict) -> dict:
        if not isinstance(value, dict):
            raise WorkspaceError("设置必须是对象", "invalid_input")
        WritingWorkspace._reject_secret_fields(value)
        if set(value) - (set(DEFAULT_SETTINGS) | {"revision"}):
            raise WorkspaceError("设置包含不支持的字段", "invalid_input")
        result = _copy_json(DEFAULT_SETTINGS)
        incoming = dict(value)
        incoming_visuals = incoming.pop("visuals", None)
        result.update(incoming)
        if incoming_visuals is not None:
            if not isinstance(incoming_visuals, dict):
                raise WorkspaceError("visuals 必须是对象", "invalid_input")
            if set(incoming_visuals) - set(DEFAULT_SETTINGS["visuals"]):
                raise WorkspaceError("配图设置包含不支持的字段", "invalid_input")
            result["visuals"].update(incoming_visuals)
        if result["tone"] not in {"plain_chinese", "formal_chinese"}:
            raise WorkspaceError("tone 必须是 plain_chinese 或 formal_chinese", "invalid_input")
        target = result.get("target_words")
        if target is not None and (isinstance(target, bool) or not isinstance(target, int) or target <= 0):
            raise WorkspaceError("target_words 必须是正整数", "invalid_input")
        if result["execution_mode"] not in {"sequential", "parallel"}:
            raise WorkspaceError("execution_mode 无效", "invalid_input")
        if isinstance(result["max_parallel"], bool) or result["max_parallel"] not in {1, 2}:
            raise WorkspaceError("max_parallel 只能是 1 或 2", "invalid_input")
        visuals = result["visuals"]
        if not isinstance(visuals.get("enabled"), bool):
            raise WorkspaceError("visuals.enabled 必须是布尔值", "invalid_input")
        if visuals.get("diagram_engine") not in {"auto", "drawio", "plantuml", "mermaid", "blueprint"}:
            raise WorkspaceError("visuals.diagram_engine 无效", "invalid_input")
        if visuals.get("diagram_theme") not in {"reference", "blue", "teal", "green", "slate", "monochrome"}:
            raise WorkspaceError("visuals.diagram_theme 无效", "invalid_input")
        if visuals.get("diagram_format") not in {"svg", "png"}:
            raise WorkspaceError("visuals.diagram_format 无效", "invalid_input")
        if visuals.get("layout_template") not in {"auto", "layered", "swimlane", "sequence", "flow", "pipeline", "network", "parallel", "matrix"}:
            raise WorkspaceError("visuals.layout_template 无效", "invalid_input")
        layers = visuals.get("architecture_layers")
        if (layers is not None and (isinstance(layers, bool) or not isinstance(layers, int)
                                    or not 1 <= layers <= 12)):
            raise WorkspaceError("visuals.architecture_layers 必须为空或 1 到 12 的整数", "invalid_input")
        if visuals.get("image_mode") not in {"host", "disabled"}:
            raise WorkspaceError("visuals.image_mode 无效", "invalid_input")
        for field in ("tool", "model", "style"):
            if not isinstance(visuals.get(field), str) or len(visuals[field]) > 200:
                raise WorkspaceError(
                    f"visuals.{field} 必须是 200 字符以内的文本", "invalid_input")
        if visuals.get("aspect_ratio") not in {"16:9", "4:3", "1:1"}:
            raise WorkspaceError("visuals.aspect_ratio 无效", "invalid_input")
        max_images = visuals.get("max_images")
        if (isinstance(max_images, bool) or not isinstance(max_images, int)
                or not 1 <= max_images <= 8):
            raise WorkspaceError("visuals.max_images 必须是 1 到 8 的整数", "invalid_input")
        result["guidance"] = DEFAULT_SETTINGS["guidance"]
        try:
            return normalize_settings(result)
        except ValueError as exc:
            raise WorkspaceError(str(exc), "invalid_input") from exc

    @staticmethod
    def _reject_secret_fields(value: object) -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                normalized = str(key).lower().replace("-", "_")
                secret_name = (
                    r"(?:secret|token|password|api[_-]?key|"
                    r"access[_-]?(?:key|token)|authorization|credential)"
                )
                if normalized in {"key", "auth"} or re.search(secret_name, normalized):
                    raise WorkspaceError("设置不能包含密钥或凭据字段", "invalid_input")
                WritingWorkspace._reject_secret_fields(child)
        elif isinstance(value, list):
            for child in value:
                WritingWorkspace._reject_secret_fields(child)

    def save_settings(self, value: dict) -> dict:
        if not isinstance(value, dict):
            raise WorkspaceError("设置必须是对象", "invalid_input")
        value = dict(value)
        if "expected_revision" not in value or "expected_sha256" not in value:
            raise WorkspaceError("保存设置必须提供 expected_revision 和 expected_sha256", "invalid_input")
        expected_revision = value.pop("expected_revision", None)
        expected_sha = value.pop("expected_sha256", None)
        with _file_lock(self.project):
            current = (self._settings_snapshot(migrate=True, locked=True)
                       if self._settings_path().is_file() else self.settings())
            if (isinstance(expected_revision, bool) or not isinstance(expected_revision, int)
                    or expected_revision < 0):
                raise WorkspaceError("expected_revision 必须是非负整数", "invalid_input")
            if not isinstance(expected_sha, str) or not re.fullmatch(r"(?:[0-9a-f]{64})?", expected_sha):
                raise WorkspaceError("expected_sha256 无效", "invalid_input")
            if expected_revision != current["revision"]:
                raise WorkspaceError("写作设置已被其他标签页修改，请重载后重试。", "stale_settings", 409)
            if expected_sha != current["sha256"]:
                raise WorkspaceError("写作设置哈希已变化，请重载后重试。", "stale_settings", 409)
            result = self._validate_settings(value)
            try:
                normalize_settings(result, {s['id'] for s in self._load_artifact(self.outline_path)['data']['sections']})
            except ValueError as exc:
                raise WorkspaceError(str(exc), "invalid_input") from exc
            result["revision"] = current["revision"] + 1
            _write_atomic(self._settings_path(), result)
        return self.settings()

    def _artifact_refs(self, payload: dict, stack: set[str] | None = None) -> list[dict]:
        refs = payload.get("inputs", [])
        if not isinstance(refs, list):
            raise WorkspaceError("上游 inputs 必须是数组", "invalid_project", 422)
        stack = set() if stack is None else set(stack)
        result = []
        for ref in refs:
            if not isinstance(ref, dict) or not isinstance(ref.get("relative_path"), str):
                raise WorkspaceError("上游引用缺少 relative_path", "invalid_project", 422)
            if not isinstance(ref.get("sha256"), str) or not re.fullmatch(r"[0-9a-f]{64}", ref["sha256"]):
                raise WorkspaceError("上游引用缺少有效 sha256", "invalid_project", 422)
            if "revision" in ref and (isinstance(ref["revision"], bool) or
                                       not isinstance(ref["revision"], int) or ref["revision"] < 1):
                raise WorkspaceError("上游引用 revision 无效", "invalid_project", 422)
            path = _safe_path(self.project, ref["relative_path"], "上游引用")
            row = dict(ref)
            row["relative_path"] = _relative(self.project, path)
            row["expected_sha256"] = ref.get("sha256")
            row["exists"] = path.is_file()
            row["actual_sha256"] = _digest(path) if path.is_file() else None
            row["changed"] = bool(path.is_file() and ref.get("sha256") != row["actual_sha256"])
            result.append(row)
            key = row["relative_path"]
            if key in stack:
                row["cycle"] = True
                continue
            if path.is_file() and path.suffix.lower() == ".json":
                upstream = _read_json(path)
                if upstream.get("project_id") not in (None, self.project_id):
                    row["project_mismatch"] = True
                if ref.get("artifact_id") and upstream.get("artifact_id") not in (None, ref.get("artifact_id")):
                    row["artifact_mismatch"] = True
                if "revision" in ref and "revision" in upstream and ref["revision"] != upstream["revision"]:
                    row["revision_mismatch"] = True
                result.extend(self._artifact_refs(upstream, stack | {key}))
        unique = {}
        for row in result:
            unique[(row.get("relative_path"), row.get("expected_sha256"))] = row
        return list(unique.values())

    def _source_checks(self) -> list[dict]:
        registry = self.project / "inputs/source-registry.json"
        if not registry.is_file():
            return []
        payload = _read_json(registry)
        if payload.get("project_id") not in (None, self.project_id):
            raise WorkspaceError("原件登记表项目与工作目录不一致", "project_mismatch", 422)
        rows = []
        for source in payload.get("sources", []):
            if not isinstance(source, dict) or not source.get("relative_path"):
                continue
            path = _safe_path(self.project, source["relative_path"], "已登记原件")
            actual = _digest(path) if path.is_file() else None
            rows.append({"source_id": source.get("source_id"), "relative_path": _relative(self.project, path),
                         "exists": path.is_file(), "changed": actual != source.get("sha256"),
                         "expected_sha256": source.get("sha256"), "actual_sha256": actual})
        return rows

    def _coverage(self, outline_path: Path | None = None) -> dict:
        checker = None
        try:
            checker = importlib.import_module("writing_checks")
        except ImportError:
            pass
        if checker and hasattr(checker, "check_project"):
            try:
                return checker.check_project(self.project, self.outline_path,
                                             self.writing_path, None)
            except Exception as exc:  # checker is advisory; editor remains usable.
                return {"status": "ERROR", "error": str(exc), "semantic_acceptance": "NOT_TESTED"}
        return {"status": "NOT_RUN", "semantic_acceptance": "NOT_TESTED",
                "note": "writing_checks.check_project 未提供；仅展示结构引用。"}

    def _upstream(self, writing: dict) -> dict:
        rows = self._artifact_refs(writing)
        errors = []
        for row in rows:
            if not row["exists"]:
                errors.append(f"缺少上游：{row['relative_path']}")
            elif row["changed"]:
                errors.append(f"上游已变化：{row['relative_path']}")
            if row.get("project_mismatch"):
                errors.append(f"上游项目不一致：{row['relative_path']}")
            if row.get("artifact_mismatch"):
                errors.append(f"上游产物标识不一致：{row['relative_path']}")
            if row.get("revision_mismatch"):
                errors.append(f"上游版本不一致：{row['relative_path']}")
            if row.get("cycle"):
                errors.append(f"上游引用存在循环：{row['relative_path']}")
        sources = self._source_checks()
        errors.extend(f"登记原件已变化：{x['relative_path']}" for x in sources if x["changed"])
        return {"refs": rows, "sources": sources, "errors": sorted(set(errors)),
                "current": not errors}

    def _chapter_rows(self, outline: dict, writing: dict) -> list[dict]:
        current = {x.get("id"): x for x in writing.get("data", {}).get("chapters", [])
                   if isinstance(x, dict) and x.get("id")}
        rows = []
        try:
            sections = ordered_sections(outline.get("data", {}).get("sections", []))
        except ValueError as exc:
            raise WorkspaceError(str(exc), "invalid_project", 422) from exc
        for section in sections:
            chapter = current.get(section.get("id")) or current.get(f"CH-{section.get('id')}")
            # A chapter normally uses its own ID; section ID is retained for unwritten nav items.
            if chapter is None:
                chapter = next((x for x in current.values() if x.get("section_id") == section.get("id")), None)
            rows.append({"id": chapter.get("id") if chapter else section.get("id"),
                         "section_id": section.get("id"), "number": section.get("number", ""),
                         "parent_id": section.get("parent_id"), "depth": section["depth"],
                         "display_number": section["display_number"],
                         "children_count": section["children_count"],
                         "title": section.get("title", "未命名章节"), "written": bool(chapter),
                         "state": (chapter or {}).get("state", "unwritten"),
                         "requirement_ids": section.get("requirement_ids", []),
                         "scoring_ids": section.get("scoring_ids", []),
                         "evidence_ids": (chapter or {}).get("evidence_ids", []),
                         "visuals_needed": section.get("visuals_needed", [])})
        return rows

    def _references(self, chapter: dict | None, requirements: dict, scoring: dict, evidence: dict) -> dict:
        chapter = chapter or {}
        requirement_ids = set(chapter.get("requirement_ids", []))
        scoring_ids = set(chapter.get("scoring_ids", []))
        evidence_ids = set(chapter.get("evidence_ids", []))
        req_rows = requirements.get("data", {}).get("requirements", [])
        score_rows = scoring.get("data", {}).get("items", [])
        evidence_rows = evidence.get("data", {}).get("materials", [])
        return {"requirements": [x for x in req_rows if x.get("id") in requirement_ids],
                "scoring": [x for x in score_rows if x.get("id") in scoring_ids],
                "evidence": [x for x in evidence_rows if x.get("id") in evidence_ids],
                "missing_evidence": sorted(evidence_ids - {x.get("id") for x in evidence_rows})}

    @staticmethod
    def _section_scoring(outline: dict, section_id: str | None) -> list[str]:
        sections = {x.get("id"): x for x in outline.get("data", {}).get("sections", [])}
        result = []
        current = sections.get(section_id)
        seen = set()
        while current and current.get("id") not in seen:
            seen.add(current.get("id"))
            result.extend(current.get("scoring_ids", []))
            current = sections.get(current.get("parent_id"))
        return list(dict.fromkeys(result))

    def state(self, chapter_id: str | None = None) -> dict:
        project_meta = _read_json(self.project_meta_path)
        outline = self._load_artifact(self.outline_path)
        writing = self._load_artifact(self.writing_path)
        requirements_path = _safe_path(self.project, "artifacts/03-requirements.json", "需求产物")
        scoring_path = _safe_path(self.project, "artifacts/04-scoring.json", "评分产物")
        evidence_path = _safe_path(self.project, "artifacts/09-evidence-selection.json", "证据产物")
        visuals_path = _safe_path(self.project, "artifacts/13-visuals.json", "图表产物")
        requirements = self._load_artifact(requirements_path) if requirements_path.is_file() else {
            "data": {"requirements": []}, "missing": True}
        scoring = self._load_artifact(scoring_path) if scoring_path.is_file() else {
            "data": {"items": []}, "missing": True}
        evidence = self._load_artifact(evidence_path) if evidence_path.is_file() else {
            "data": {"materials": []}, "missing": True}
        visuals = self._load_artifact(visuals_path) if visuals_path.is_file() else {
            "data": {"figures": []}, "missing": True}
        chapters = writing.get("data", {}).get("chapters", [])
        upstream = self._upstream(writing)
        rows = self._chapter_rows(outline, writing)
        if chapter_id:
            selected_row = next((x for x in rows if x.get("id") == chapter_id), None)
            if selected_row is None:
                raise WorkspaceError("chapter_id 不在当前目录中", "not_found", 404)
            chapter = next((x for x in chapters if x.get("id") == selected_row["id"]), None)
            if chapter is None:
                chapter = next((x for x in chapters if x.get("section_id") == selected_row["section_id"]), None)
        else:
            chapter = chapters[0] if chapters else None
            selected_row = next((x for x in rows if x.get("id") == (chapter or {}).get("id")), None)
            if selected_row is None and rows:
                selected_row = rows[0]
        if chapter is None and selected_row:
            chapter = {"id": selected_row["id"], "section_id": selected_row["section_id"],
                       "title": selected_row["title"], "body_markdown": "", "state": "unwritten",
                       "requirement_ids": selected_row["requirement_ids"],
                       "evidence_ids": selected_row["evidence_ids"],
                       "scoring_ids": self._section_scoring(outline, selected_row["section_id"]),
                       "visuals_needed": selected_row["visuals_needed"]}
        elif chapter is not None and selected_row:
            chapter = _copy_json(chapter)
            chapter["scoring_ids"] = chapter.get("scoring_ids") or self._section_scoring(
                outline, selected_row["section_id"])
            chapter.setdefault("visuals_needed", selected_row["visuals_needed"])
        project_view = dict(project_meta)
        profile_path = _safe_path(self.project, "artifacts/02-project-profile.json", "项目画像")
        if profile_path.is_file():
            profile = self._load_artifact(profile_path)
            project_view["project_name"] = profile.get("data", {}).get("project_name") or self.project_id
        else:
            project_view["project_name"] = project_meta.get("project_name") or self.project_id
        project_view.update({"project_id": self.project_id, "root": str(self.project)})
        outline_view = dict(outline)
        outline_view["sha256"] = _digest(self.outline_path)
        writing_view = dict(writing)
        writing_view["sha256"] = _digest(self.writing_path)
        settings = self.settings()
        selected_section = next((s for s in outline['data']['sections']
                                 if s['id'] == (selected_row or {}).get('section_id')), None)
        chapter_policy = (resolve_policy(selected_section, outline['data']['sections'],
                                         scoring['data']['items'], requirements['data']['requirements'], settings)
                          if selected_section else None)
        return {"project": project_view, "outline": outline_view, "writing": writing_view,
                "chapters": rows, "chapter": chapter, "requirements": requirements,
                "score": scoring, "scoring": scoring, "evidence": evidence,
                "visuals": visuals,
                "references": self._references(chapter, requirements, scoring, evidence),
                "upstream": upstream, "coverage": self._coverage(), "settings": settings,
                "chapter_policy": chapter_policy,
                "ui": {"semantic_acceptance": "NOT_TESTED", "writable_state": "proposed/draft only"}}

    def _validate_save_request(self, request: dict) -> tuple[int, str, str, str]:
        if not isinstance(request, dict):
            raise WorkspaceError("请求必须是 JSON 对象")
        expected_revision = request.get("expected_revision")
        expected_sha = request.get("expected_sha256")
        chapter_id = request.get("chapter_id")
        body = request.get("body_markdown")
        if isinstance(expected_revision, bool) or not isinstance(expected_revision, int) or expected_revision < 0:
            raise WorkspaceError("expected_revision 必须是非负整数")
        if not isinstance(expected_sha, str) or not re.fullmatch(r"[0-9a-f]{64}", expected_sha):
            raise WorkspaceError("expected_sha256 无效")
        if not isinstance(chapter_id, str) or not chapter_id.strip():
            raise WorkspaceError("chapter_id 不能为空")
        if not isinstance(body, str) or not body.strip():
            raise WorkspaceError("body_markdown 不能为空")
        return expected_revision, expected_sha, chapter_id.strip(), body

    def _schema_errors(self, payload: dict) -> list[str]:
        try:
            from jsonschema import Draft202012Validator, FormatChecker
        except ImportError:
            return ["缺少已声明依赖 jsonschema，无法验证写作产物 Schema"]
        schema_candidates = (
            SUITE_ROOT / "skills/bid-technical-writing/assets/output.schema.json",
            SUITE_ROOT / "skills/bid-technical-writing/assets/writing-output.schema.json",
            SUITE_ROOT / "assets/writing-output.schema.json",
            Path(__file__).resolve().parent / "../skills/bid-technical-writing/assets/output.schema.json",
            Path(__file__).resolve().parent / "../skills/bid-technical-writing/assets/writing-output.schema.json",
        )
        schema_path = next((path for path in schema_candidates if path.is_file()), None)
        if schema_path is None:
            return ["找不到 bid-technical-writing output.schema.json，拒绝写入"]
        schema = _read_json(schema_path)
        validator = Draft202012Validator(schema, format_checker=FormatChecker())
        return [".".join(map(str, error.absolute_path)) + ": " + error.message
                for error in validator.iter_errors(payload)]

    def _markdown_report(self, payload: dict) -> str:
        lines = [f"# 技术标正文草稿（{payload.get('project_id', self.project_id)}）", "",
                 "> 状态：草稿（proposed/draft），语义验收：NOT_TESTED", ""]
        for chapter in payload.get("data", {}).get("chapters", []):
            lines.extend([f"## {chapter.get('title', chapter.get('id', '未命名章节'))}", "",
                          chapter.get("body_markdown", "").rstrip(), ""])
        return "\n".join(lines).rstrip() + "\n"

    def save(self, request: dict) -> dict:
        expected_revision, expected_sha, chapter_id, body = self._validate_save_request(request)
        with _file_lock(self.project):
            current = self._load_artifact(self.writing_path)
            revision = current.get("revision", 0)
            actual_sha = _digest(self.writing_path)
            if expected_revision != revision or expected_sha != actual_sha:
                raise WorkspaceError("写作产物已被其他标签页或进程修改，请重载后合并。", "stale_write", 409)
            upstream = self._upstream(current)
            if upstream["errors"]:
                raise WorkspaceError("上游输入缺失或已变化：" + "；".join(upstream["errors"]),
                                     "upstream_changed", 409)
            outline = self._load_artifact(self.outline_path)
            sections = {x.get("id"): x for x in outline.get("data", {}).get("sections", [])}
            existing = current.setdefault("data", {}).setdefault("chapters", [])
            if not isinstance(existing, list):
                raise WorkspaceError("写作产物 chapters 结构无效", "invalid_project", 422)
            selected = next((x for x in existing if x.get("id") == chapter_id), None)
            if selected is None:
                selected = next((x for x in existing if x.get("section_id") == chapter_id), None)
            section = sections.get(selected.get("section_id") if selected else chapter_id)
            if section is None:
                raise WorkspaceError("chapter_id 不在当前目录中", "invalid_input")
            if selected is None:
                selected = {"id": chapter_id, "section_id": section["id"], "title": section.get("title", ""),
                            "base_revision": revision, "requirement_ids": list(section.get("requirement_ids", [])),
                            "design_ids": [], "evidence_ids": [], "state": "proposed", "confirmation_ref": None}
                existing.append(selected)
            selected["body_markdown"] = body
            selected["state"] = "proposed"
            selected["base_revision"] = revision
            for chapter in existing:
                if chapter.get("state") == "accepted":
                    chapter["state"] = "proposed"
            current["revision"] = revision + 1
            current["status"] = "draft"
            current["project_id"] = self.project_id
            current.setdefault("data", {}).setdefault("responses", [])
            current.setdefault("data", {}).setdefault("unresolved_claims", [])
            errors = self._schema_errors(current)
            if errors:
                raise WorkspaceError("写作产物结构不符合契约：" + "；".join(errors[:5]), "invalid_project", 422)
            history = _safe_path(self.project, "work/writing-history", "写作历史目录")
            markdown_path = _safe_path(self.project, _relative(self.project, self.writing_path.with_suffix(".md")),
                                       "写作 Markdown")
            audit = _safe_path(self.project, "work/writing-audit.jsonl", "写作审计日志")
            history.mkdir(parents=True, exist_ok=True)
            stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
            snapshot = history / f"r{revision:06d}-{stamp}-{actual_sha[:12]}.json"
            suffix = 1
            while snapshot.exists():
                snapshot = history / f"r{revision:06d}-{stamp}-{actual_sha[:12]}-{suffix}.json"
                suffix += 1
            old_json = self.writing_path.read_bytes()
            old_markdown = markdown_path.read_bytes() if markdown_path.exists() else None
            old_audit = audit.read_bytes() if audit.exists() else None
            json_written = markdown_written = audit_written = False
            try:
                _write_atomic(snapshot, _read_json(self.writing_path))
                _write_atomic(self.writing_path, current)
                json_written = True
                _write_text_atomic(markdown_path, self._markdown_report(current))
                markdown_written = True
                with audit.open("a", encoding="utf-8") as stream:
                    stream.write(json.dumps({"at": _now(), "action": "save", "chapter_id": chapter_id,
                                             "from_revision": revision, "to_revision": revision + 1,
                                             "snapshot": _relative(self.project, snapshot),
                                             "status": "draft"}, ensure_ascii=False) + "\n")
                    stream.flush()
                    os.fsync(stream.fileno())
                audit_written = True
            except Exception as exc:
                rollback_errors = []
                try:
                    if json_written:
                        _write_bytes_atomic(self.writing_path, old_json)
                    if markdown_written:
                        if old_markdown is None:
                            markdown_path.unlink(missing_ok=True)
                        else:
                            _write_bytes_atomic(markdown_path, old_markdown)
                    if audit_written or audit.exists():
                        if old_audit is None:
                            audit.unlink(missing_ok=True)
                        else:
                            _write_bytes_atomic(audit, old_audit)
                    snapshot.unlink(missing_ok=True)
                except Exception as rollback_exc:  # pragma: no cover - filesystem failure path.
                    rollback_errors.append(str(rollback_exc))
                if rollback_errors:
                    raise WorkspaceError(
                        "保存发生部分写入，正文落盘状态需人工检查；派生文件恢复失败。",
                        "partial_save", 500) from exc
                raise WorkspaceError("保存失败，已回滚正文和派生文件，请重试。", "save_rolled_back", 500) from exc
            return self.state(chapter_id)


class _RequestHandler(BaseHTTPRequestHandler):
    server_version = "BidWritingWorkspace/1.0"

    @property
    def workspace(self) -> WritingWorkspace:
        return self.server.workspace  # type: ignore[attr-defined]

    def _origin_allowed(self) -> bool:
        origin = self.headers.get("Origin")
        if not origin:
            return True
        parsed = urlparse(origin)
        host = parsed.hostname
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        return host in {"127.0.0.1", "localhost"} and port == self.server.server_port

    def _host_allowed(self) -> bool:
        host_header = self.headers.get("Host")
        if not host_header:
            return True
        parsed = urlparse("http://" + host_header)
        host = parsed.hostname
        port = parsed.port or 80
        return host in {"127.0.0.1", "localhost"} and port == self.server.server_port

    def _request_allowed(self) -> bool:
        return self._origin_allowed() and self._host_allowed()

    def _send_json(self, status: int, value: object) -> None:
        body = json.dumps(value, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        origin = self.headers.get("Origin")
        if origin and self._origin_allowed():
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Vary", "Origin")
        self.end_headers()
        self.wfile.write(body)

    def _error(self, exc: Exception) -> None:
        if isinstance(exc, WorkspaceError):
            self._send_json(exc.status, {"error": {"code": exc.code, "message": str(exc)}})
        else:
            self._send_json(500, {"error": {"code": "internal_error", "message": "服务内部错误"}})

    def _json_body(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0 or length > 2 * 1024 * 1024:
            raise WorkspaceError("请求体为空或超过 2MB", "invalid_input")
        try:
            value = json.loads(self.rfile.read(length).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise WorkspaceError("请求体不是有效 JSON", "invalid_input") from exc
        if not isinstance(value, dict):
            raise WorkspaceError("请求体必须是对象", "invalid_input")
        return value

    def do_OPTIONS(self) -> None:  # noqa: N802
        if not self._request_allowed():
            self._send_json(403, {"error": {"code": "origin_forbidden", "message": "请求来源不允许"}})
            return
        self.send_response(204)
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self) -> None:  # noqa: N802
        if not self._request_allowed():
            self._send_json(403, {"error": {"code": "origin_forbidden", "message": "请求来源不允许"}})
            return
        parsed = urlparse(self.path)
        try:
            if parsed.path == "/api/state":
                query = parse_qs(parsed.query)
                chapter_id = query.get("chapter_id", [None])[0]
                self._send_json(200, self.workspace.state(chapter_id))
                return
            if parsed.path == "/api/settings":
                self._send_json(200, self.workspace.settings())
                return
            if parsed.path == "/api/file":
                path = _safe_path(self.workspace.project, parse_qs(parsed.query).get("path", [""])[0], "文件路径", True)
                if path.suffix.lower() not in {".json", ".md", ".pdf", ".txt", ".png", ".jpg", ".jpeg", ".svg"}:
                    raise WorkspaceError("文件类型不允许在线查看", "invalid_input")
                body = path.read_bytes()
                self.send_response(200)
                content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
                if path.suffix.lower() == ".svg":
                    content_type = "text/plain; charset=utf-8"
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(len(body)))
                self.send_header("X-Content-Type-Options", "nosniff")
                self.end_headers()
                self.wfile.write(body)
                return
            if parsed.path == "/" or parsed.path == "/index.html":
                self._send_asset("writing-editor.html", "text/html; charset=utf-8")
                return
            if parsed.path.startswith("/assets/ui/"):
                name = parsed.path.rsplit("/", 1)[-1]
                if name not in {"writing-editor.css", "writing-editor.js"}:
                    raise WorkspaceError("静态资源不存在", "missing_file", 404)
                content_type = "text/css; charset=utf-8" if name.endswith(".css") else "text/javascript; charset=utf-8"
                self._send_asset(name, content_type)
                return
            self._send_json(404, {"error": {"code": "not_found", "message": "路径不存在"}})
        except Exception as exc:
            self._error(exc)

    def _send_asset(self, name: str, content_type: str) -> None:
        path = UI_ROOT / name
        if not path.is_file():
            raise WorkspaceError("静态资源不存在", "missing_file", 404)
        body = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self) -> None:  # noqa: N802
        if not self._request_allowed():
            self._send_json(403, {"error": {"code": "origin_forbidden", "message": "请求来源不允许"}})
            return
        try:
            if self.path == "/api/save":
                self._send_json(200, self.workspace.save(self._json_body()))
                return
            if self.path == "/api/settings":
                self._send_json(200, self.workspace.save_settings(self._json_body()))
                return
            self._send_json(404, {"error": {"code": "not_found", "message": "路径不存在"}})
        except Exception as exc:
            self._error(exc)

    def log_message(self, format: str, *args: object) -> None:
        return


class WritingHTTPServer(ThreadingHTTPServer):
    allow_reuse_address = True

    def __init__(self, address: tuple[str, int], workspace: WritingWorkspace):
        super().__init__(address, _RequestHandler)
        self.workspace = workspace


def create_server(workspace: WritingWorkspace, port: int = 0) -> WritingHTTPServer:
    return WritingHTTPServer(("127.0.0.1", port), workspace)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", required=True, type=Path)
    parser.add_argument("--port", required=True, type=int)
    parser.add_argument("--outline", default="artifacts/08-outline.json")
    parser.add_argument("--writing", default="artifacts/11-technical-content.json")
    args = parser.parse_args()
    if not 0 < args.port < 65536:
        parser.error("--port 必须在 1-65535 之间")
    workspace = WritingWorkspace(args.project, args.outline, args.writing)
    server = create_server(workspace, args.port)
    print(f"writing-editor listening on http://127.0.0.1:{server.server_port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        return 0
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
