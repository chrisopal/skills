"""Job-level regressions: resume, immutable payload and no duplicate submit."""

import json
from unittest.mock import Mock, patch

import pytest

from scripts import profiles
from scripts.__main__ import main
from scripts.video_manifest import load_video_job, run_video_manifest


@pytest.fixture(autouse=True)
def isolated_ledger(tmp_path, monkeypatch):
    monkeypatch.setattr(profiles, "DEFAULT_ROOT", tmp_path / "runtime")


@pytest.fixture
def manifest(tmp_path):
    (tmp_path / "片子.mp4").write_bytes(b"video version one")
    (tmp_path / "封面.png").write_bytes(b"cover version one")
    path = tmp_path / "job.json"
    path.write_text(json.dumps({
        "title": "路上怎样改变了一个人？", "content": "第一段。\n\n第二段。",
        "video": "片子.mp4", "cover": "封面.png", "account": "读书账号",
        "tags": ["历史人物", "#读书分享", "历史人物"],
    }, ensure_ascii=False), encoding="utf-8")
    return path


def test_preflight_resolves_relative_files_and_never_opens_browser(manifest):
    publisher = Mock()
    result = run_video_manifest(str(manifest), publisher=publisher, preflight=True)
    assert result["status"] == "preflight_ready"
    assert result["published"] is False
    assert result["video_path"] == str(manifest.parent / "片子.mp4")
    publisher.assert_not_called()
    assert not manifest.with_name("job.json.state.json").exists()
    job, _, _ = load_video_job(manifest)
    assert job["tags"] == ["历史人物", "读书分享"]


def test_missing_cover_fails_before_browser(manifest):
    (manifest.parent / "封面.png").unlink()
    publisher = Mock()
    with pytest.raises(ValueError, match="媒体文件"):
        run_video_manifest(str(manifest), publisher=publisher)
    publisher.assert_not_called()


def test_saved_job_resumes_without_new_upload(manifest):
    publisher = Mock(return_value={"status": "draft_saved", "published": False})
    run_video_manifest(str(manifest), publisher=publisher)
    assert publisher.call_args.kwargs["resume_draft"] is False
    run_video_manifest(str(manifest), publisher=publisher)
    assert publisher.call_args.kwargs["resume_draft"] is True
    assert publisher.call_args.kwargs["save_draft"] is True


@pytest.mark.parametrize("change", ["content", "video", "cover", "account", "profile"])
def test_resume_requires_same_content_media_and_account(manifest, change):
    publisher = Mock(return_value={"status": "draft_saved"})
    run_video_manifest(str(manifest), publisher=publisher)
    raw = json.loads(manifest.read_text())
    if change in {"video", "cover"}:
        (manifest.parent / raw[change]).write_bytes(b"changed bytes")
    elif change in {"content", "account"}:
        raw[change] += " changed"
        manifest.write_text(json.dumps(raw), encoding="utf-8")
    with pytest.raises(ValueError, match="已变化"):
        run_video_manifest(str(manifest), publisher=publisher,
                           profile="different" if change == "profile" else None)
    assert publisher.call_count == 1


@pytest.mark.parametrize("status", ["confirmed", "submitted_unconfirmed", "failed"])
def test_no_repeat_after_any_submission_attempt(manifest, status):
    publisher = Mock(return_value={"status": status, "published": status == "confirmed"})
    run_video_manifest(str(manifest), publisher=publisher, auto_publish=True)
    with pytest.raises(ValueError, match="禁止"):
        run_video_manifest(str(manifest), publisher=publisher, auto_publish=True)
    assert publisher.call_count == 1


def test_crash_after_start_is_not_retried(manifest):
    publisher = Mock(side_effect=RuntimeError("connection lost"))
    with pytest.raises(RuntimeError):
        run_video_manifest(str(manifest), publisher=publisher, auto_publish=True)
    with pytest.raises(ValueError, match="禁止"):
        run_video_manifest(str(manifest), publisher=publisher)
    assert publisher.call_count == 1


def test_preparation_crash_resumes_instead_of_uploading_again(manifest):
    publisher = Mock(side_effect=RuntimeError("browser closed"))
    with pytest.raises(RuntimeError):
        run_video_manifest(str(manifest), publisher=publisher)
    publisher.side_effect = None
    publisher.return_value = {"status": "draft_saved"}
    run_video_manifest(str(manifest), publisher=publisher)
    assert publisher.call_args.kwargs["resume_draft"] is True


def test_manual_publication_blocks_future_browser_work(manifest):
    publisher = Mock()
    result = run_video_manifest(str(manifest), publisher=publisher, record_published=True)
    assert result["published"] is True
    assert result["success"] is False  # user report is not independent verification
    with pytest.raises(ValueError, match="禁止"):
        run_video_manifest(str(manifest), publisher=publisher)
    publisher.assert_not_called()


def test_existing_production_manifest_published_flag_blocks_upload(manifest):
    raw = json.loads(manifest.read_text())
    raw["published"] = True
    manifest.write_text(json.dumps(raw), encoding="utf-8")
    publisher = Mock()
    with pytest.raises(ValueError, match="禁止"):
        run_video_manifest(str(manifest), publisher=publisher)
    publisher.assert_not_called()


def test_job_lock_prevents_concurrent_duplicate(manifest):
    manifest.with_name("job.json.lock").write_text("", encoding="utf-8")
    publisher = Mock()
    with pytest.raises(ValueError, match="已有进程"):
        run_video_manifest(str(manifest), publisher=publisher)
    publisher.assert_not_called()


@pytest.mark.parametrize("field,value", [
    ("account", None), ("tags", "a,b"), ("tags", ["two words"]),
    ("content", ""), ("visibility", "unknown"), ("is_original", "false"),
])
def test_invalid_manifest_rejected(manifest, field, value):
    raw = json.loads(manifest.read_text())
    raw[field] = value
    manifest.write_text(json.dumps(raw), encoding="utf-8")
    with pytest.raises(ValueError):
        load_video_job(manifest)


def test_cli_preflight_and_manual_record_do_not_start_browser(manifest, capsys):
    with patch("scripts.__main__.publish.publish_video") as publisher:
        with patch("sys.argv", ["scripts", "publish-video", "--manifest", str(manifest), "--preflight"]):
            assert main() == 0
        assert json.loads(capsys.readouterr().out)["status"] == "preflight_ready"
        with patch("sys.argv", ["scripts", "publish-video", "--manifest", str(manifest), "--record-published"]):
            assert main() == 0
        assert json.loads(capsys.readouterr().out)["status"] == "recorded_published"
        publisher.assert_not_called()


def test_cli_conflicting_arguments_fail_before_browser(manifest, capsys):
    with patch("scripts.__main__.publish.publish_video") as publisher:
        with patch("sys.argv", ["scripts", "publish-video", "--manifest", str(manifest), "--title", "different"]):
            assert main() == 1
        assert "不能" in json.loads(capsys.readouterr().out)["message"]
        publisher.assert_not_called()


@pytest.mark.parametrize("mode", ["manual", "submission"])
@pytest.mark.parametrize("operation", ["copy", "rename"])
def test_duplicate_protection_survives_manifest_move(manifest, mode, operation):
    publisher = Mock(return_value={"status": "submitted_unconfirmed"})
    run_video_manifest(str(manifest), publisher=publisher,
                       record_published=mode == "manual", auto_publish=mode == "submission")
    publisher.reset_mock()
    moved = manifest.with_name("renamed.json")
    moved.write_bytes(manifest.read_bytes())
    if operation == "rename":
        manifest.unlink()
    with pytest.raises(ValueError, match="禁止"):
        run_video_manifest(str(moved), publisher=publisher)
    publisher.assert_not_called()


@pytest.mark.parametrize("change", ["content", "account", "video"])
def test_manual_record_rejects_changed_saved_payload(manifest, change):
    publisher = Mock(return_value={"status": "draft_saved"})
    run_video_manifest(str(manifest), publisher=publisher)
    raw = json.loads(manifest.read_text())
    if change == "video":
        (manifest.parent / raw[change]).write_bytes(b"different video")
    else:
        raw[change] += " changed"
        manifest.write_text(json.dumps(raw), encoding="utf-8")
    with pytest.raises(ValueError, match="已变化"):
        run_video_manifest(str(manifest), publisher=publisher, record_published=True)
    assert publisher.call_count == 1


def test_manual_record_has_current_fingerprint(manifest):
    _, fingerprint, _ = load_video_job(manifest)
    run_video_manifest(str(manifest), publisher=Mock(), record_published=True)
    state = json.loads(manifest.with_name("job.json.state.json").read_text())
    assert state["fingerprint"] == fingerprint
    ledger = profiles.profile_paths().session_path.parent / "publish-jobs" / f"{fingerprint}.json"
    assert json.loads(ledger.read_text())["fingerprint"] == fingerprint
