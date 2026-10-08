from __future__ import annotations

import hashlib
import json
import threading
import urllib.error
import urllib.request
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch


SUITE_ROOT = Path(__file__).resolve().parents[1]
import sys

sys.path.insert(0, str(SUITE_ROOT / "scripts"))

from writing_workspace import WorkspaceError, create_server  # noqa: E402
from writing_workspace import WritingWorkspace  # noqa: E402


class WritingWorkspaceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = TemporaryDirectory()
        self.project = Path(self.temp.name)
        for name in ("work", "artifacts", "inputs", "assets", "profiles"):
            (self.project / name).mkdir()
        (self.project / "work/project.json").write_text(
            json.dumps({"project_id": "P-001", "mode": "full"}), encoding="utf-8"
        )
        (self.project / "inputs/source-registry.json").write_text(
            json.dumps({"sources": []}), encoding="utf-8"
        )
        self._write("artifacts/03-requirements.json", {
            "project_id": "P-001",
            "artifact_id": "ART-03",
            "revision": 1,
            "data": {"requirements": [{"id": "R-1", "text": "系统应可追溯", "mandatory": "yes"}]},
        })
        self._write("artifacts/04-scoring.json", {
            "project_id": "P-001",
            "artifact_id": "ART-04",
            "revision": 1,
            "data": {"items": [{"id": "S-1", "title": "技术方案", "max_score": 20}]},
        })
        self._write("artifacts/09-evidence-selection.json", {
            "project_id": "P-001",
            "artifact_id": "ART-09",
            "revision": 1,
            "data": {"materials": [{"id": "M-1", "title": "项目证明"}], "selections": []},
        })
        self._write("artifacts/08-outline.json", {
            "schema_version": "1.0", "skill_id": "bid-outline-planning", "created_at": "2026-10-07T00:00:00Z",
            "project_id": "P-001",
            "artifact_id": "ART-08",
            "revision": 1,
            "data": {"sections": [
                {"id": "SEC-1", "number": "1", "title": "技术方案", "parent_id": None,
                 "requirement_ids": ["R-1"], "scoring_ids": ["S-1"], "evidence_needed": ["M-1"],
                 "visuals_needed": [], "task": "说明方案", "locked": True},
                {"id": "SEC-2", "number": "2", "title": "实施安排", "parent_id": None,
                 "requirement_ids": [], "scoring_ids": [], "evidence_needed": [],
                 "visuals_needed": ["实施流程图"], "task": "说明安排", "locked": False},
            ], "unmapped_ids": []},
        })
        refs = []
        for artifact_id, relative in (("ART-03", "artifacts/03-requirements.json"),
                                      ("ART-04", "artifacts/04-scoring.json"),
                                      ("ART-08", "artifacts/08-outline.json"),
                                      ("ART-09", "artifacts/09-evidence-selection.json")):
            refs.append({"artifact_id": artifact_id, "revision": 1, "relative_path": relative,
                         "sha256": self._digest(relative)})
        self._write("artifacts/11-technical-content.json", {
            "schema_version": "1.0", "skill_id": "bid-technical-writing", "created_at": "2026-10-07T00:00:00Z", "project_id": "P-001",
            "artifact_id": "ART-11", "revision": 1, "status": "needs_review", "inputs": refs,
            "summary": "草稿", "data": {"chapters": [{
                "id": "CH-1", "section_id": "SEC-1", "title": "技术方案", "body_markdown": "旧稿",
                "base_revision": 0, "requirement_ids": ["R-1"], "design_ids": [], "evidence_ids": ["M-1"],
                "state": "proposed", "confirmation_ref": None,
            }], "responses": [], "unresolved_claims": []}, "warnings": [], "blockers": [],
        })

    def tearDown(self) -> None:
        self.temp.cleanup()

    def _write(self, relative: str, value: dict) -> None:
        path = self.project / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def _digest(self, relative: str) -> str:
        return hashlib.sha256((self.project / relative).read_bytes()).hexdigest()

    def _workspace(self) -> WritingWorkspace:
        return WritingWorkspace(self.project, "artifacts/08-outline.json", "artifacts/11-technical-content.json")

    def test_save_reopen_snapshots_and_writes_markdown_audit(self) -> None:
        workspace = self._workspace()
        state = workspace.state("CH-1")
        result = workspace.save({
            "expected_revision": state["writing"]["revision"],
            "expected_sha256": state["writing"]["sha256"],
            "chapter_id": "CH-1",
            "body_markdown": "# 新稿\n\n内容。",
        })
        self.assertEqual(result["writing"]["revision"], 2)
        self.assertEqual(self._workspace().state("CH-1")["chapter"]["body_markdown"], "# 新稿\n\n内容。")
        self.assertTrue(list((self.project / "work/writing-history").glob("*.json")))
        self.assertIn("# 技术方案", (self.project / "artifacts/11-technical-content.md").read_text())
        self.assertTrue((self.project / "work/writing-audit.jsonl").is_file())

    def test_derived_markdown_failure_rolls_back_authoritative_json(self) -> None:
        workspace = self._workspace()
        state = workspace.state("CH-1")
        before = (self.project / "artifacts/11-technical-content.json").read_bytes()
        request = {"expected_revision": state["writing"]["revision"],
                   "expected_sha256": state["writing"]["sha256"],
                   "chapter_id": "CH-1", "body_markdown": "新草稿"}
        with patch("writing_workspace._write_text_atomic", side_effect=OSError("disk failure")):
            with self.assertRaises(WorkspaceError) as raised:
                workspace.save(request)
        self.assertEqual(raised.exception.code, "save_rolled_back")
        self.assertEqual((self.project / "artifacts/11-technical-content.json").read_bytes(), before)
        self.assertFalse(list((self.project / "work/writing-history").glob("*.json")))
        self.assertFalse((self.project / "work/writing-audit.jsonl").exists())

    def test_stale_concurrent_save_is_rejected_without_overwrite(self) -> None:
        first, second = self._workspace(), self._workspace()
        original = first.state("CH-1")["writing"]
        first.save({"expected_revision": original["revision"], "expected_sha256": original["sha256"],
                    "chapter_id": "CH-1", "body_markdown": "首个保存"})
        with self.assertRaises(WorkspaceError) as caught:
            second.save({"expected_revision": original["revision"], "expected_sha256": original["sha256"],
                         "chapter_id": "CH-1", "body_markdown": "过期保存"})
        self.assertEqual(caught.exception.code, "stale_write")
        self.assertEqual(self._workspace().state("CH-1")["chapter"]["body_markdown"], "首个保存")

    def test_missing_or_changed_upstream_blocks_save(self) -> None:
        workspace = self._workspace()
        (self.project / "artifacts/03-requirements.json").unlink()
        state = workspace.state("CH-1")
        self.assertTrue(state["upstream"]["errors"])
        with self.assertRaises(WorkspaceError) as caught:
            workspace.save({"expected_revision": 1, "expected_sha256": state["writing"]["sha256"],
                            "chapter_id": "CH-1", "body_markdown": "不应写入"})
        self.assertEqual(caught.exception.code, "upstream_changed")

    def test_unwritten_section_is_selectable_and_unknown_section_is_404(self) -> None:
        workspace = self._workspace()
        unwritten = workspace.state("SEC-2")
        self.assertEqual(unwritten["chapter"]["id"], "SEC-2")
        self.assertEqual(unwritten["chapter"]["state"], "unwritten")
        with self.assertRaises(WorkspaceError) as caught:
            workspace.state("does-not-exist")
        self.assertEqual(caught.exception.code, "not_found")
        self.assertEqual(caught.exception.status, 404)

    def test_scoring_refs_are_derived_from_outline_when_chapter_omits_them(self) -> None:
        writing = json.loads((self.project / "artifacts/11-technical-content.json").read_text())
        self._write("artifacts/11-technical-content.json", writing)
        refs = self._workspace().state("CH-1")["references"]["scoring"]
        self.assertEqual([row["id"] for row in refs], ["S-1"])

    def test_settings_are_validated_and_persisted(self) -> None:
        workspace = self._workspace()
        settings_path = self.project / "work/writing-settings.json"
        settings_path.write_text(json.dumps({"tone": "plain_chinese", "target_words": None,
                                             "execution_mode": "sequential", "max_parallel": 1,
                                             "revision": 3}), encoding="utf-8")
        initial = workspace.settings()
        self.assertTrue(initial["visuals"]["enabled"])
        self.assertEqual(initial["visuals"]["diagram_engine"], "auto")
        self.assertEqual(initial["visuals"]["diagram_format"], "svg")
        self.assertEqual(initial["visuals"]["layout_template"], "auto")
        self.assertIsNone(initial["visuals"]["architecture_layers"])
        self.assertEqual(initial["visuals"]["image_mode"], "host")
        self.assertEqual(initial["visuals"]["max_images"], 2)
        with self.assertRaises(WorkspaceError) as missing_guard:
            workspace.save_settings({"tone": "formal_chinese"})
        self.assertEqual(missing_guard.exception.code, "invalid_input")
        settings = workspace.save_settings({"tone": "formal_chinese", "target_words": 1200,
                                             "execution_mode": "parallel", "max_parallel": 2,
                                             "visuals": {"enabled": False, "diagram_engine": "plantuml",
                                                         "diagram_format": "png", "layout_template": "sequence",
                                                         "architecture_layers": 4,
                                                         "image_mode": "disabled", "tool": "local",
                                                         "model": "preferred-model", "style": "clean",
                                                         "aspect_ratio": "4:3", "max_images": 4},
                                             "expected_revision": initial["revision"],
                                             "expected_sha256": initial["sha256"]})
        self.assertEqual(self._workspace().settings(), settings)
        self.assertTrue((self.project / "work/writing-settings.json").exists())
        self.assertEqual(settings["visuals"]["model"], "preferred-model")
        self.assertEqual(settings["visuals"]["diagram_engine"], "plantuml")
        self.assertEqual(settings["visuals"]["diagram_format"], "png")
        self.assertEqual(settings["visuals"]["layout_template"], "sequence")
        self.assertEqual(settings["visuals"]["architecture_layers"], 4)
        self.assertFalse(settings["visuals"]["enabled"])
        for invalid in (
            {"visuals": {"max_images": True}},
            {"visuals": {"diagram_engine": "raster"}},
            {"visuals": {"diagram_format": "jpeg"}},
            {"visuals": {"layout_template": "grid"}},
            {"visuals": {"architecture_layers": 2}},
            {"visuals": {"style": "x" * 201}},
            {"visuals": {"api_key": "should-never-be-stored"}},
        ):
            current = workspace.settings()
            invalid.update({"expected_revision": current["revision"],
                            "expected_sha256": current["sha256"]})
            with self.assertRaises(WorkspaceError):
                workspace.save_settings(invalid)
        with self.assertRaises(WorkspaceError) as caught:
            workspace.save_settings({"tone": "plain_chinese", "expected_revision": 0,
                                     "expected_sha256": ""})
        self.assertEqual(caught.exception.code, "stale_settings")

    def test_legacy_diagram_renderer_is_migrated_once_on_read(self) -> None:
        workspace = self._workspace()
        settings_path = self.project / "work/writing-settings.json"
        for old_value, expected_engine in (("svg", "auto"), ("mermaid", "mermaid"), ("auto", "auto")):
            settings_path.write_text(json.dumps({
                "tone": "plain_chinese", "revision": 7,
                "visuals": {"enabled": True, "diagram_renderer": old_value},
            }), encoding="utf-8")
            migrated = workspace.settings()
            self.assertEqual(migrated["visuals"]["diagram_engine"], expected_engine)
            self.assertEqual(migrated["visuals"]["diagram_format"], "svg")
            persisted = json.loads(settings_path.read_text(encoding="utf-8"))
            self.assertNotIn("diagram_renderer", persisted["visuals"])
            self.assertEqual(persisted["visuals"]["diagram_engine"], expected_engine)
            self.assertEqual(persisted["revision"], 7)
            stable_hash = migrated["sha256"]
            self.assertEqual(workspace.settings()["sha256"], stable_hash)

    def test_new_saves_reject_retired_diagram_renderer_field(self) -> None:
        workspace = self._workspace()
        current = workspace.settings()
        with self.assertRaises(WorkspaceError):
            workspace.save_settings({
                "visuals": {"diagram_renderer": "mermaid"},
                "expected_revision": current["revision"],
                "expected_sha256": current["sha256"],
            })

    def test_save_settings_creates_missing_settings_file(self) -> None:
        workspace = self._workspace()
        current = workspace.settings()
        self.assertFalse((self.project / "work/writing-settings.json").exists())
        saved = workspace.save_settings({
            "visuals": {"diagram_engine": "drawio"},
            "expected_revision": current["revision"],
            "expected_sha256": current["sha256"],
        })
        self.assertEqual(saved["revision"], 1)
        self.assertEqual(saved["visuals"]["diagram_engine"], "drawio")
        self.assertTrue((self.project / "work/writing-settings.json").is_file())

    def test_stale_hash_from_before_legacy_migration_is_rejected(self) -> None:
        workspace = self._workspace()
        settings_path = self.project / "work/writing-settings.json"
        settings_path.write_text(json.dumps({
            "tone": "plain_chinese", "revision": 4,
            "visuals": {"enabled": True, "diagram_renderer": "svg"},
        }), encoding="utf-8")
        stale_hash = self._digest("work/writing-settings.json")
        current = workspace.settings()
        with self.assertRaises(WorkspaceError) as caught:
            workspace.save_settings({
                "visuals": {"diagram_engine": "drawio"},
                "expected_revision": current["revision"],
                "expected_sha256": stale_hash,
            })
        self.assertEqual(caught.exception.code, "stale_settings")
        self.assertEqual(workspace.settings()["visuals"]["diagram_engine"], "auto")

    def test_settings_reject_unknown_fields_without_persisting_credentials(self) -> None:
        workspace = self._workspace()
        before = workspace.settings()
        for field in ("private_key", "bearer", "cookie", "unknown_preference", "diagram_renderer"):
            for payload in ({field: "do-not-store"}, {"visuals": {field: "do-not-store"}}):
                payload.update({"expected_revision": before["revision"],
                                "expected_sha256": before["sha256"]})
                with self.subTest(payload=payload), self.assertRaises(WorkspaceError):
                    workspace.save_settings(payload)
                self.assertEqual(workspace.settings(), before)
        self.assertFalse((self.project / "work/writing-settings.json").exists())

    def test_save_preflights_history_and_audit_paths_before_writing(self) -> None:
        outside = Path(self.temp.name).parent / (Path(self.temp.name).name + "-outside")
        outside.mkdir()
        history = self.project / "work/writing-history"
        history.symlink_to(outside, target_is_directory=True)
        workspace = self._workspace()
        before = (self.project / "artifacts/11-technical-content.json").read_bytes()
        state = workspace.state("CH-1")
        with self.assertRaises(WorkspaceError) as caught:
            workspace.save({"expected_revision": state["writing"]["revision"],
                            "expected_sha256": state["writing"]["sha256"], "chapter_id": "CH-1",
                            "body_markdown": "不会写入"})
        self.assertEqual(caught.exception.code, "path_traversal")
        self.assertEqual((self.project / "artifacts/11-technical-content.json").read_bytes(), before)
        outside.rmdir()

    def test_invalid_input_and_path_traversal_are_rejected(self) -> None:
        with self.assertRaises(WorkspaceError):
            WritingWorkspace(self.project, "../outside.json", "artifacts/11-technical-content.json")
        workspace = self._workspace()
        with self.assertRaises(WorkspaceError) as caught:
            workspace.save({"expected_revision": 1, "expected_sha256": "bad", "chapter_id": "CH-1",
                            "body_markdown": "   "})
        self.assertEqual(caught.exception.code, "invalid_input")

    def test_script_text_is_kept_as_markdown_and_ui_does_not_inject_html(self) -> None:
        workspace = self._workspace()
        state = workspace.state("CH-1")
        workspace.save({"expected_revision": 1, "expected_sha256": state["writing"]["sha256"],
                        "chapter_id": "CH-1", "body_markdown": "<script>alert(1)</script>"})
        self.assertIn("<script>alert(1)</script>", (self.project / "artifacts/11-technical-content.md").read_text())
        script = (SUITE_ROOT / "assets/ui/writing-editor.js").read_text(encoding="utf-8")
        self.assertNotIn("innerHTML", script)
        self.assertIn("unsavedBuffers", script)
        self.assertIn("放弃当前编辑", script)
        page = (SUITE_ROOT / "assets/ui/writing-editor.html").read_text(encoding="utf-8")
        self.assertIn("settings-form", page)
        for field in ("visuals-enabled-setting", "diagram-engine-setting", "diagram-format-setting",
                      "layout-template-setting", "architecture-layers-setting", "image-mode-setting",
                      "visual-tool-setting", "visual-model-setting", "visual-style-setting",
                      "visual-aspect-ratio-setting", "visual-max-images-setting"):
            self.assertIn(field, page)
        self.assertNotIn("diagram-renderer-setting", page)
        self.assertIn("图表引擎", page)
        self.assertIn("输出格式", page)
        self.assertIn("布局模板", page)
        self.assertIn("架构层数", page)

    def test_outline_state_has_parent_order_and_display_number(self) -> None:
        path = self.project / 'artifacts/08-outline.json'
        outline = json.loads(path.read_text())
        outline['data']['sections'][0]['number'] = '一'
        outline['data']['sections'][1]['number'] = '二'
        child = dict(outline['data']['sections'][1], id='SEC-3', parent_id='SEC-1',
                     number='一.1', title='子章节')
        outline['data']['sections'].append(child)
        path.write_text(json.dumps(outline), encoding='utf-8')
        rows = self._workspace().state()['chapters']
        self.assertEqual([r['section_id'] for r in rows], ['SEC-1', 'SEC-3', 'SEC-2'])
        self.assertEqual(rows[1]['parent_id'], 'SEC-1')
        self.assertEqual(rows[1]['display_number'], '1.1')
        self.assertEqual(rows[1]['depth'], 1)
        child['parent_id'] = 'missing'
        outline['data']['sections'][-1] = child
        path.write_text(json.dumps(outline), encoding='utf-8')
        with self.assertRaises(WorkspaceError) as caught:
            self._workspace().state()
        self.assertEqual(caught.exception.code, 'invalid_project')

    def test_external_request_origin_is_rejected(self) -> None:
        server = create_server(self._workspace(), 0)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            url = f"http://127.0.0.1:{server.server_port}/api/state"
            request = urllib.request.Request(url, headers={"Origin": "https://evil.example"})
            with self.assertRaises(urllib.error.HTTPError) as caught:
                urllib.request.urlopen(request, timeout=2)
            self.assertEqual(caught.exception.code, 403)
            request = urllib.request.Request(url, headers={"Origin": f"http://127.0.0.1:{server.server_port}"})
            with urllib.request.urlopen(request, timeout=2) as response:
                self.assertEqual(response.status, 200)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)


if __name__ == "__main__":
    unittest.main()
