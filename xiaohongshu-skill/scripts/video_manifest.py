"""Local video publishing jobs. No account credentials are stored here."""

from __future__ import annotations

import hashlib
import json
import os
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from .profiles import profile_paths
from .publish import validate_media_paths, validate_publish_request
from .session_store import atomic_write_json

TERMINAL_STATES = {
    "confirmed", "submitted_unconfirmed", "submission_started",
    "published_manually_user_reported", "recorded_published",
}


def _read_object(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("发布清单和状态文件必须是 JSON 对象")
    return value


def _digest(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _state_path(manifest: Path) -> Path:
    return manifest.with_name(manifest.name + ".state.json")


@contextmanager
def _job_lock(path: Path):
    lock = path.with_name(path.name + ".lock")
    try:
        fd = os.open(lock, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError as exc:
        raise ValueError("该清单已有进程运行；核实原进程和发布结果后再处理锁文件") from exc
    try:
        os.close(fd)
        yield
    finally:
        lock.unlink(missing_ok=True)


def _already_submitted(data: dict) -> bool:
    return data.get("published") is True or data.get("status") in TERMINAL_STATES


def load_video_job(path: Path, *, profile: str | None = None, allow_published: bool = False) -> tuple[dict, str, dict]:
    """Validate a manifest and bind resume to content, media bytes and account."""
    raw = _read_object(path)
    if _already_submitted(raw) and not allow_published:
        raise ValueError("该清单已发布或提交结果待核对；禁止重复提交")
    title, content = raw.get("title"), raw.get("content")
    if not isinstance(content, str) or not content.strip():
        raise ValueError("清单 content 必须是非空正文")
    account = raw.get("account")
    if not isinstance(account, str) or not account.strip():
        raise ValueError("清单 account 必须填写发布账号显示名称")
    tags = raw.get("tags", [])
    if not isinstance(tags, list) or len(tags) > 10 or any(
        not isinstance(tag, str) or not tag.lstrip("#").strip()
        or any(char.isspace() for char in tag.strip()) for tag in tags
    ):
        raise ValueError("tags 必须为最多10个非空、无空格的话题名称")
    tags = list(dict.fromkeys(tag.lstrip("#").strip() for tag in tags))
    if len(content) + sum(len(tag) + 2 for tag in tags) > 1000:
        raise ValueError("正文和话题合计超过1000字，请先缩短并在平台复核")
    visibility = raw.get("visibility", "公开可见")
    if visibility not in {"公开可见", "仅自己可见", "仅互关好友可见"}:
        raise ValueError("visibility 不是支持的可见范围")
    if not isinstance(raw.get("is_original", False), bool):
        raise ValueError("is_original 必须是布尔值")

    def media(key: str, alias: str) -> str | None:
        value = raw.get(key, raw.get(alias))
        if value is None and key == "cover":
            return None
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"清单缺少有效的 {key} 文件路径")
        target = Path(value).expanduser()
        if not target.is_absolute():
            target = path.parent / target
        return validate_media_paths([str(target)])[0]

    video = media("video", "video_path")
    cover = media("cover", "cover_path")
    validation = validate_publish_request(
        title=title, media_paths=[video], schedule_time=raw.get("schedule_time"),
    )
    job = {
        "title": title, "content": content, "video_path": video,
        "cover_path": cover, "tags": tags, "expected_account": account.strip(),
        "visibility": visibility, "is_original": raw.get("is_original", False),
        "schedule_time": raw.get("schedule_time"),
    }
    hashes = {"video": _digest(video)}
    if cover:
        hashes["cover"] = _digest(cover)
    identity = {**job, "profile": profile or "default", "media_sha256": hashes}
    # A moved file with the same bytes is the same job.
    identity.pop("video_path")
    identity.pop("cover_path")
    fingerprint = hashlib.sha256(json.dumps(
        identity, ensure_ascii=False, sort_keys=True,
    ).encode("utf-8")).hexdigest()
    summary = {
        "status": "preflight_ready", "action": "publish_video",
        "title": title, "account": account.strip(), "video_path": video,
        "cover_path": cover, "schedule_time": job["schedule_time"],
        "visibility": visibility, "success": False, "published": False,
        "warnings": list(validation.warnings), "fingerprint": fingerprint,
        "message": "本地预检通过；尚未连接账号或上传媒体",
    }
    return job, fingerprint, summary


def run_video_manifest(
    manifest_path: str,
    *,
    publisher: Callable,
    preflight: bool = False,
    record_published: bool = False,
    auto_publish: bool = False,
    resume_draft: bool = False,
    profile: str | None = None,
    **browser_options,
) -> dict:
    """Run once, resume saved drafts, and stop after uncertain submission."""
    path = Path(manifest_path).expanduser().resolve()
    if sum((preflight, record_published, auto_publish)) > 1:
        raise ValueError("预检、记录手动发布和自动提交只能选择一种")
    with _job_lock(path):
        state_path = _state_path(path)
        state = _read_object(state_path) if state_path.exists() else {}
        job, fingerprint, result = load_video_job(
            path, profile=profile, allow_published=record_published,
        )
        if state.get("fingerprint") and state["fingerprint"] != fingerprint:
            raise ValueError("清单、媒体或账号已变化；请使用新清单并重新确认内容")
        ledger_path = profile_paths(profile).session_path.parent / "publish-jobs" / f"{fingerprint}.json"
        ledger = _read_object(ledger_path) if ledger_path.exists() else {}
        if not record_published and any(_already_submitted(item) for item in (state, ledger)):
            raise ValueError("该任务已发布或提交结果待核对；禁止重新上传或自动重试")
        if preflight:
            return result
        ledger_path.parent.mkdir(parents=True, exist_ok=True)
        # The content lock survives manifest renames and serializes copied jobs.
        with _job_lock(ledger_path):
            ledger = _read_object(ledger_path) if ledger_path.exists() else {}
            if not record_published and _already_submitted(ledger):
                raise ValueError("该任务已发布或提交结果待核对；禁止重新上传或自动重试")

            def persist(value: dict) -> None:
                record = {
                    **value, "fingerprint": fingerprint, "title": job["title"],
                    "account": job["expected_account"], "updated_at": _now(),
                }
                # Authoritative ledger first: a sidecar write failure stays safe.
                atomic_write_json(ledger_path, record)
                atomic_write_json(state_path, record)

            if record_published:
                result = {
                    **result, "status": "recorded_published", "published": True,
                    "success": False,
                    "message": "已记录用户手动发布；未独立核验线上结果，不再自动提交",
                }
                persist(result)
                return result
            resume = resume_draft or any(
                item.get("status") in {"draft_saved", "preparing"}
                for item in (state, ledger)
            )
            # Persist before browser work. A crash must not invite resubmission.
            persist({"status": "submission_started" if auto_publish else "preparing"})
            response = publisher(
                **job, **browser_options, auto_publish=auto_publish,
                resume_draft=resume, save_draft=not auto_publish,
            )
            status = response.get("status", "failed")
            recorded_status = status
            if auto_publish and status not in {"confirmed", "submitted_unconfirmed"}:
                recorded_status = "submission_started"
            elif not auto_publish and status != "draft_saved":
                recorded_status = "preparing"
            persist({
                "status": recorded_status, "result_status": status,
                "published": response.get("published", False),
            })
            return {**response, "fingerprint": fingerprint, "state_file": str(state_path)}
