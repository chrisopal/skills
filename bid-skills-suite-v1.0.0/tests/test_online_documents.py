from __future__ import annotations

import copy
import hashlib
import json
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from xml.etree import ElementTree

SUITE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SUITE_ROOT / "scripts"))

from online_documents import FeishuCliClient, OnlineDocumentError, OnlineDocumentService, _remote_mapping  # noqa: E402
from writing_workspace import WritingWorkspace  # noqa: E402


class FakeClient:
    """Small in-memory Feishu-shaped client for adapter contract tests."""

    atomic_replace = True
    strict_unique_titles = False

    def __init__(self, xml: str, *, references: dict | None = None):
        self.xml = xml
        self.revision = 7
        self.references = references or {"img": {"r1": {"token": "resource-1"}}}
        self.fetch_calls: list[dict] = []
        self.update_calls: list[dict] = []
        self.result = "success"
        self.mutate_before_update = False
        self.mutate_on_success = True
        self.update_ok = True
        self.local_resource_failures: list[dict] = []
        self.fail_fetch_after: int | None = None

    def fetch(self, document: str, *, identity: str, revision_id: int = -1) -> dict:
        if self.fail_fetch_after is not None and len(self.fetch_calls) >= self.fail_fetch_after:
            raise RuntimeError("post-write fetch unavailable")
        self.fetch_calls.append({"document": document, "identity": identity, "revision_id": revision_id})
        return {"ok": True, "identity": identity, "data": {"document": {
            "document_id": "doxcn-demo001", "revision_id": self.revision,
            "content": self.xml, "reference_map": copy.deepcopy(self.references),
        }}}

    def update(self, document: str, *, identity: str, revision_id: int, command: str,
               content: str, block_id: str | None = None, start_block_id: str | None = None,
               end_block_id: str | None = None) -> dict:
        self.update_calls.append({"document": document, "identity": identity, "revision_id": revision_id,
                                  "command": command, "content": content, "block_id": block_id,
                                  "start_block_id": start_block_id, "end_block_id": end_block_id})
        if self.result != "success":
            return {"ok": True, "data": {"result": self.result, "updated_blocks_count": 1}}
        if not self.mutate_on_success:
            return {"ok": True, "data": {"result": "success", "updated_blocks_count": 1}}
        if revision_id != self.revision:
            return {"ok": True, "data": {"result": "failed", "warnings": ["revision conflict"]}}
        root = ElementTree.fromstring(self.xml)
        incoming = ElementTree.fromstring(f"<fragment>{content}</fragment>")
        blocks = list(root)
        if command == "block_replace":
            ids = [node.attrib.get("block-id") or node.attrib.get("id") for node in blocks]
            start = ids.index(start_block_id)
            end = ids.index(end_block_id)
            root[:] = blocks[:start] + list(incoming) + blocks[end + 1:]
        elif command == "block_insert_after":
            if block_id in {"-1", None}:
                root.extend(list(incoming))
            elif block_id == "0":
                root[:] = list(incoming) + blocks
            else:
                ids = [node.attrib.get("block-id") or node.attrib.get("id") for node in blocks]
                anchor = ids.index(block_id)
                root[:] = blocks[:anchor + 1] + list(incoming) + blocks[anchor + 1:]
        else:
            raise AssertionError(f"unexpected update command {command}")
        self.xml = ElementTree.tostring(root, encoding="unicode")
        self.revision += 1
        return {"ok": self.update_ok, "data": {"result": "success", "updated_blocks_count": len(incoming),
                "local_resource_failures": copy.deepcopy(self.local_resource_failures)}}

    def remote_edit(self, text: str) -> None:
        root = ElementTree.fromstring(self.xml)
        for node in root:
            if ((node.attrib.get("block-id") or node.attrib.get("id")) == "old-duplicate"
                    or (node.tag == "p" and node.text == "本地旧稿")):
                node.text = text
                break
        self.xml = ElementTree.tostring(root, encoding="unicode")
        self.revision += 1


class OnlineDocumentsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = TemporaryDirectory()
        self.project = Path(self.temp.name)
        for directory in ("work", "artifacts", "assets"):
            (self.project / directory).mkdir()
        (self.project / "work/project.json").write_text(json.dumps({"project_id": "P-001"}), encoding="utf-8")
        self._write("artifacts/08-outline.json", {
            "schema_version": "1.0", "skill_id": "bid-outline-planning", "project_id": "P-001",
            "revision": 1, "data": {"sections": [
                {"id": "SEC-1", "number": "1", "title": "技术方案", "parent_id": None, "depth": 0},
                {"id": "SEC-2", "number": "2", "title": "实施安排", "parent_id": None, "depth": 0},
                {"id": "SEC-3", "number": "3", "title": "本地新增", "parent_id": None, "depth": 0},
            ]},
        })
        self._write("artifacts/11-technical-content.json", {
            "schema_version": "1.0", "skill_id": "bid-technical-writing", "project_id": "P-001",
            "artifact_id": "ART-11", "revision": 1, "status": "draft", "inputs": [],
            "data": {"chapters": [
                {"id": "CH-1", "section_id": "SEC-1", "title": "技术方案", "body_markdown": "本地旧稿",
                 "base_revision": 0, "requirement_ids": [], "design_ids": [], "evidence_ids": [],
                 "state": "proposed", "confirmation_ref": None},
                {"id": "CH-3", "section_id": "SEC-3", "title": "本地新增", "body_markdown": "新增内容",
                 "base_revision": 0, "requirement_ids": [], "design_ids": [], "evidence_ids": [],
                 "state": "proposed", "confirmation_ref": None},
            ], "responses": [], "unresolved_claims": []},
            "warnings": [], "blockers": [],
        })
        (self.project / "assets/figure.png").write_bytes(b"fake-png")
        self._write("artifacts/13-visuals.json", {
            "schema_version": "1.0", "skill_id": "bid-visuals", "project_id": "P-001",
            "revision": 1, "data": {"figures": [{"id": "FIG-1", "section_id": "SEC-1",
            "title": "架构图", "rendered_path": "assets/figure.png", "state": "rendered",
            "caption": "图1", "kind": "architecture"}]},
        })
        self.client = FakeClient(self.remote_xml)
        self.service = OnlineDocumentService(self.project, self.client)

    @property
    def remote_xml(self) -> str:
        return (
            '<document project-id="P-001"><title block-id="title">远程标书</title>'
            '<p block-id="before">保留的前置内容</p>'
            '<h2 block-id="chapter-1">技术方案</h2>'
            '<p block-id="remote-body">远程旧稿</p>'
            '<img block-id="remote-image" src="resource-1"/>'
            '<h2 block-id="chapter-2">实施安排</h2>'
            '<p block-id="other-body">其他章节不应被改写</p>'
            '<h2 block-id="chapter-1-old">技术方案</h2>'
            '<p block-id="old-duplicate">旧重复标题</p></document>'
        )

    def tearDown(self) -> None:
        self.temp.cleanup()

    def _write(self, relative: str, value: dict) -> None:
        path = self.project / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def test_status_is_local_only_and_bind_records_full_snapshot_without_sync_receipts(self) -> None:
        self.assertFalse(self.service.status()["bound"])
        self.service.bind("https://feishu.cn/docx/doxcn-demo001?x=1", identity="user")
        self.assertEqual(len(self.client.fetch_calls), 1)
        status = self.service.status()
        self.assertEqual(len(self.client.fetch_calls), 1)
        self.assertEqual(status["current_mapping"]["SEC-1"]["title"], "技术方案")
        self.assertNotIn("last_synced", status["current_mapping"]["SEC-1"])
        self.assertTrue(any(item["kind"] == "local_unpublished" for item in status["pending_differences"]))
        self.assertTrue(list((self.project / "work/online-document-snapshots").glob("*.xml")))
        self.assertTrue(list((self.project / "work/online-document-snapshots").glob("*.references.json")))

    def test_bind_rejects_project_url_identity_and_provider_errors(self) -> None:
        with self.assertRaisesRegex(OnlineDocumentError, "token"):
            self.service.bind("https://feishu.cn/docx/short")
        with self.assertRaisesRegex(OnlineDocumentError, "安全"):
            self.service.bind("https://user:password@feishu.cn/docx/doxcn-demo001")
        with self.assertRaisesRegex(OnlineDocumentError, "尚未实现"):
            self.service.bind("https://docs.qq.com/doc/abcdefghi")
        with self.assertRaisesRegex(OnlineDocumentError, "identity"):
            self.service.bind("doxcn-demo001", identity="admin")

    def test_fetch_uses_latest_unique_duplicate_title_and_refreshes_mapping(self) -> None:
        self.service.bind("doxcn-demo001")
        mapping = self.service.fetch()["current_mapping"]
        self.assertEqual(mapping["SEC-1"]["heading_block_id"], "chapter-1-old")
        self.assertEqual(mapping["SEC-1"]["last_block_id"], "old-duplicate")
        self.assertEqual(mapping["SEC-2"]["heading_block_id"], "chapter-2")

    def test_bind_accepts_rootless_feishu_block_sequence(self) -> None:
        self.client.xml = (
            '<title id="doc-title">远程标书</title>'
            '<p id="before">保留内容</p>'
            '<h1 id="chapter-1">技术方案</h1>'
            '<p id="body-1">远程正文</p>'
        )
        self.service.bind("doxcn-demo001")
        mapping = self.service.status()["current_mapping"]
        self.assertEqual(mapping["SEC-1"]["heading_block_id"], "chapter-1")
        self.assertEqual(mapping["SEC-1"]["last_block_id"], "body-1")

    def test_push_replaces_only_target_and_embeds_local_raster(self) -> None:
        self.service.bind("doxcn-demo001")
        result = self.service.push("SEC-1")
        self.assertEqual(result["status"], "pushed")
        self.assertEqual(len(self.client.update_calls), 1)
        call = self.client.update_calls[0]
        self.assertEqual(call["command"], "block_replace")
        self.assertIn('<img path="@./assets/figure.png"', call["content"])
        self.assertIn("其他章节不应被改写", self.client.xml)
        self.assertIn("远程旧稿", self.client.xml)
        self.assertNotIn("旧重复标题", self.client.xml)
        self.assertIn("last_synced", self.service.status()["current_mapping"]["SEC-1"])

    def test_heading_containing_body_deduplicates_and_roundtrips_nested_child(self) -> None:
        payload = json.loads((self.project / "artifacts/11-technical-content.json").read_text())
        payload["data"]["chapters"][0]["body_markdown"] = "## 1. 技术方案\n### 子章节\n子章节正文"
        self._write("artifacts/11-technical-content.json", payload)
        self.service.bind("doxcn-demo001")
        self.service.push("SEC-1")
        content = self.client.update_calls[0]["content"]
        self.assertEqual(content.count("技术方案"), 1)
        self.assertIn("<h3>子章节</h3>", content)
        with patch.object(WritingWorkspace, "_schema_errors", return_value=[]):
            self.service.pull("SEC-1")
        written = json.loads((self.project / "artifacts/11-technical-content.json").read_text())
        body = next(x for x in written["data"]["chapters"] if x["section_id"] == "SEC-1")["body_markdown"]
        self.assertNotIn("技术方案", body)
        self.assertIn("## 子章节", body)

    def test_push_is_idempotent_and_rerun_does_not_append_duplicate(self) -> None:
        self.service.bind("doxcn-demo001")
        self.service.push("SEC-1")
        second = self.service.push("SEC-1")
        self.assertEqual(second["status"], "unchanged")
        self.assertEqual(len(self.client.update_calls), 1)

    def test_new_chapter_insert_uses_adjacent_remote_heading_level(self) -> None:
        self.service.bind("doxcn-demo001")
        result = self.service.push("SEC-3")
        self.assertEqual(result["status"], "pushed")
        self.assertTrue(self.client.update_calls[0]["content"].startswith("<h2>"))

    def test_post_write_refresh_failure_persists_reconciliation_guard(self) -> None:
        self.service.bind("doxcn-demo001")
        self.client.fail_fetch_after = 2
        with self.assertRaisesRegex(RuntimeError, "post-write"):
            self.service.push("SEC-1")
        self.assertIn("SEC-1", self.service.status()["pending_write_unknown"])
        with self.assertRaisesRegex(OnlineDocumentError, "结果未知"):
            self.service.push("SEC-1")

    def test_image_bytes_are_part_of_local_sync_hash(self) -> None:
        self.service.bind("doxcn-demo001")
        self.service.push("SEC-1")
        first_hash = self.service.status()["current_mapping"]["SEC-1"]["last_synced"]["local_hash"]
        (self.project / "assets/figure.png").write_bytes(b"changed-png")
        status = self.service.status()
        second_hash, _ = self.service._local_hash("SEC-1")
        self.assertNotEqual(first_hash, second_hash)
        self.assertTrue(any(item["kind"] == "local_unpublished" for item in status["pending_differences"]))

    def test_push_rejects_remote_change_since_last_snapshot(self) -> None:
        self.service.bind("doxcn-demo001")
        self.client.remote_edit("第三方修改")
        with self.assertRaisesRegex(OnlineDocumentError, "远程章节已变化"):
            self.service.push("SEC-1")
        self.assertEqual(self.client.update_calls, [])

    def test_rebind_same_target_preserves_first_baseline_and_blocks_human_remote_edit(self) -> None:
        self.service.bind("doxcn-demo001")
        payload = json.loads((self.project / "artifacts/11-technical-content.json").read_text())
        payload["data"]["chapters"][0]["body_markdown"] = "人类本地修改"
        self._write("artifacts/11-technical-content.json", payload)
        self.client.remote_edit("人类远程修改")
        self.service.fetch()
        self.service.bind("https://feishu.cn/docx/doxcn-demo001?view=1")
        with self.assertRaisesRegex(OnlineDocumentError, "远程章节已变化"):
            self.service.push("SEC-1")
        self.assertEqual(self.client.update_calls, [])

    def test_binding_switch_is_rejected_before_network_fetch(self) -> None:
        self.service.bind("doxcn-demo001")
        calls = len(self.client.fetch_calls)
        with self.assertRaisesRegex(OnlineDocumentError, "其他在线文档"):
            self.service.bind("doxcn-other002")
        self.assertEqual(len(self.client.fetch_calls), calls)

    def test_success_without_remote_mutation_is_rejected_without_receipt(self) -> None:
        self.service.bind("doxcn-demo001")
        self.client.mutate_on_success = False
        with self.assertRaisesRegex(OnlineDocumentError, "回读正文不一致"):
            self.service.push("SEC-1")
        self.assertNotIn("last_synced", self.service.status()["current_mapping"]["SEC-1"])

    def test_existing_replace_requires_provider_atomic_capability(self) -> None:
        self.service.bind("doxcn-demo001")
        self.client.atomic_replace = False
        with self.assertRaisesRegex(OnlineDocumentError, "原子版本校验"):
            self.service.push("SEC-1")
        self.assertEqual(self.client.update_calls, [])

    def test_strict_duplicate_title_receipt_is_pending_and_not_current(self) -> None:
        self.service.bind("doxcn-demo001")
        self.service.push("SEC-1")
        self.client.strict_unique_titles = True
        status = self.service.status()
        self.assertTrue(any(item["kind"] == "duplicate_title_unsafe" for item in status["pending_differences"]))
        with self.assertRaisesRegex(OnlineDocumentError, "duplicate_title_unsafe"):
            self.service.check_current(["SEC-1"])

    def test_strict_duplicate_title_is_rejected_on_pull(self) -> None:
        self.client.strict_unique_titles = True
        self.service.bind("doxcn-demo001")
        with self.assertRaisesRegex(OnlineDocumentError, "重复章节标题"):
            self.service.pull("SEC-1")

    def test_nested_subchapter_is_fail_closed(self) -> None:
        self.client.xml = self.client.xml.replace(
            '<p block-id="old-duplicate">旧重复标题</p>',
            '<h3 block-id="nested">实施安排</h3><p block-id="nested-body">子章节正文</p>',
        )
        self.service.bind("doxcn-demo001")
        with self.assertRaisesRegex(OnlineDocumentError, "嵌套子章节"):
            self.service.push("SEC-1")
        self.assertEqual(self.client.update_calls, [])

    def test_internal_remote_headings_can_pull_without_outline_child_mapping(self) -> None:
        self.client.xml = (
            '<document project-id="P-001"><title block-id="title">远程标书</title>'
            '<h2 block-id="chapter-1">技术方案</h2>'
            '<h3 block-id="internal">内部段落</h3><p block-id="internal-body">正文</p>'
            '<h2 block-id="chapter-2">实施安排</h2><p block-id="other-body">其他</p></document>'
        )
        self.service.bind("doxcn-demo001")
        with patch.object(WritingWorkspace, "_schema_errors", return_value=[]):
            self.service.pull("SEC-1")
        payload = json.loads((self.project / "artifacts/11-technical-content.json").read_text())
        body = next(x for x in payload["data"]["chapters"] if x["section_id"] == "SEC-1")["body_markdown"]
        self.assertIn("## 内部段落", body)

    def test_mapped_nested_child_remains_unsafe_after_prior_pull_receipt(self) -> None:
        self.client.xml = (
            '<document project-id="P-001"><title block-id="title">远程标书</title>'
            '<h2 block-id="chapter-1">技术方案</h2>'
            '<h3 block-id="internal">内部段落</h3><p block-id="internal-body">正文</p>'
            '<h2 block-id="chapter-2">实施安排</h2><p block-id="other-body">其他</p></document>'
        )
        self.service.bind("doxcn-demo001")
        with patch.object(WritingWorkspace, "_schema_errors", return_value=[]):
            self.service.pull("SEC-1")
        self.client.xml = self.client.xml.replace(
            '<h3 block-id="internal">内部段落</h3>',
            '<h3 block-id="internal">实施安排</h3>',
        )
        with self.assertRaisesRegex(OnlineDocumentError, "嵌套子章节"):
            self.service.pull("SEC-1")

    def test_mapped_child_heading_is_rejected_on_pull(self) -> None:
        self.client.xml = self.client.xml.replace(
            '<p block-id="old-duplicate">旧重复标题</p>',
            '<h3 block-id="nested">实施安排</h3><p block-id="nested-body">子章节正文</p>',
        )
        self.service.bind("doxcn-demo001")
        with self.assertRaisesRegex(OnlineDocumentError, "嵌套子章节"):
            self.service.pull("SEC-1")

    def test_strict_provider_rejects_duplicate_chapter_titles(self) -> None:
        self.client.strict_unique_titles = True
        # The fixture has two matching titles; the provider must not select the
        # last one and silently replace an ambiguous range.
        self.client.xml = self.remote_xml.replace(
            '</document>', '<h2 block-id="chapter-1-old">技术方案</h2><p block-id="old-duplicate">重复</p></document>')
        self.service.bind("doxcn-demo001")
        with self.assertRaisesRegex(OnlineDocumentError, "重复章节标题"):
            self.service.push("SEC-1")
        self.assertEqual(self.client.update_calls, [])

    def test_target_comments_are_fail_closed(self) -> None:
        self.client.references = {"comments": {"c1": {"block-id": "old-duplicate"}}}
        self.service.bind("doxcn-demo001")
        with self.assertRaisesRegex(OnlineDocumentError, "评论引用"):
            self.service.push("SEC-1")
        self.assertEqual(self.client.update_calls, [])

    def test_partial_success_is_failure_and_never_retried(self) -> None:
        self.service.bind("doxcn-demo001")
        self.client.result = "partial_success"
        with self.assertRaisesRegex(OnlineDocumentError, "禁止自动重试"):
            self.service.push("SEC-1")
        self.assertEqual(len(self.client.update_calls), 1)
        self.assertNotIn("last_synced", self.service.status()["current_mapping"]["SEC-1"])
        with self.assertRaisesRegex(OnlineDocumentError, "结果未知"):
            self.service.push("SEC-1")

    def test_ok_false_resource_failure_is_not_treated_as_success(self) -> None:
        self.service.bind("doxcn-demo001")
        self.client.update_ok = False
        self.client.local_resource_failures = [{"kind": "image", "status": "upload_failed"}]
        with self.assertRaisesRegex(OnlineDocumentError, "禁止自动重试"):
            self.service.push("SEC-1")
        self.assertNotIn("last_synced", self.service.status()["current_mapping"]["SEC-1"])

    def test_check_current_blocks_local_and_remote_differences_but_can_scope(self) -> None:
        self.service.bind("doxcn-demo001")
        with self.assertRaisesRegex(OnlineDocumentError, "非空"):
            self.service.check_current([])
        with self.assertRaisesRegex(OnlineDocumentError, "local_unpublished"):
            self.service.check_current(["SEC-1"])
        self.service.push("SEC-1")
        self.client.remote_edit("第三方修改")
        with self.assertRaisesRegex(OnlineDocumentError, "remote_changed"):
            self.service.check_current(["SEC-1"])

    def test_reference_map_change_with_same_xml_is_remote_difference(self) -> None:
        self.service.bind("doxcn-demo001")
        self.service.push("SEC-1")
        self.client.references = {"comments": {"c1": {"block-id": "before"}}}
        with self.assertRaisesRegex(OnlineDocumentError, "remote_changed"):
            self.service.check_current(["SEC-1"])

    def test_pull_uses_writing_workspace_cas_and_does_not_issue_update(self) -> None:
        self.service.bind("doxcn-demo001")
        self.client.xml = self.client.xml.replace('<img block-id="remote-image" src="resource-1"/>', "")
        with patch.object(WritingWorkspace, "_schema_errors", return_value=[]):
            result = self.service.pull("SEC-1")
        self.assertEqual(result["status"], "pulled")
        payload = json.loads((self.project / "artifacts/11-technical-content.json").read_text())
        chapter = next(x for x in payload["data"]["chapters"] if x["section_id"] == "SEC-1")
        self.assertIn("旧重复标题", chapter["body_markdown"])
        self.assertEqual(self.client.update_calls, [])

    def test_pull_disables_advisories_while_online_lock_is_held(self) -> None:
        self.service.bind("doxcn-demo001")
        self.client.xml = self.client.xml.replace('<img block-id="remote-image" src="resource-1"/>', "")
        state_calls: list[dict] = []
        save_calls: list[dict] = []
        original_state = WritingWorkspace.state
        original_save = WritingWorkspace.save

        def state_probe(workspace, *args, **kwargs):
            state_calls.append(kwargs)
            return original_state(workspace, *args, **kwargs)

        def save_probe(workspace, request, *args, **kwargs):
            save_calls.append(kwargs)
            return original_save(workspace, request, *args, **kwargs)

        with patch.object(WritingWorkspace, "state", new=state_probe), \
                patch.object(WritingWorkspace, "save", new=save_probe), \
                patch.object(WritingWorkspace, "_schema_errors", return_value=[]):
            self.service.pull("SEC-1")
        self.assertGreaterEqual(len(state_calls), 1)
        self.assertTrue(all(call == {"include_advisories": False} for call in state_calls))
        self.assertEqual(save_calls, [{"include_advisories": False}])

    def test_pull_reuses_known_local_image_resource(self) -> None:
        self.service.bind("doxcn-demo001")
        self.service.push("SEC-1")
        with patch.object(WritingWorkspace, "_schema_errors", return_value=[]):
            self.service.pull("SEC-1")
        payload = json.loads((self.project / "artifacts/11-technical-content.json").read_text())
        chapter = next(x for x in payload["data"]["chapters"] if x["section_id"] == "SEC-1")
        self.assertIn("![图1](assets/figure.png)", chapter["body_markdown"])

    def test_markdown_table_pushes_native_xml_and_roundtrips(self) -> None:
        payload = json.loads((self.project / "artifacts/11-technical-content.json").read_text())
        payload["data"]["chapters"][0]["body_markdown"] = (
            "| **指标** | 方法 |\n| --- | --- |\n| 目标 | 分层 |\n| 结果 | 可追溯 |"
        )
        self._write("artifacts/11-technical-content.json", payload)
        self.service.bind("doxcn-demo001")
        result = self.service.push("SEC-1")
        self.assertEqual(result["status"], "pushed")
        content = self.client.update_calls[0]["content"]
        self.assertIn("<table>", content)
        self.assertIn("<thead><tr><th><p><b>指标</b></p></th><th><p>方法</p></th></tr></thead>", content)
        self.assertIn("<tbody><tr><td><p>目标</p></td><td><p>分层</p></td></tr>", content)
        with patch.object(WritingWorkspace, "_schema_errors", return_value=[]):
            self.service.pull("SEC-1")
        written = json.loads((self.project / "artifacts/11-technical-content.json").read_text())
        body = next(x for x in written["data"]["chapters"] if x["section_id"] == "SEC-1")["body_markdown"]
        self.assertIn("| **指标** | 方法 |", body)
        self.assertIn("| 目标 | 分层 |", body)
        self.assertIn("| 结果 | 可追溯 |", body)

    def test_markdown_table_must_be_rectangular(self) -> None:
        payload = json.loads((self.project / "artifacts/11-technical-content.json").read_text())
        payload["data"]["chapters"][0]["body_markdown"] = "| A | B |\n| --- | --- |\n| only |"
        self._write("artifacts/11-technical-content.json", payload)
        self.service.bind("doxcn-demo001")
        with self.assertRaisesRegex(OnlineDocumentError, "矩形"):
            self.service.push("SEC-1")
        self.assertEqual(self.client.update_calls, [])

    def test_pull_roundtrips_native_simple_table_and_rejects_merged_table(self) -> None:
        self.client.xml = (
            '<document project-id="P-001"><title block-id="title">远程标书</title>'
            '<h2 block-id="chapter-1">技术方案</h2>'
            '<table id="table-1"><colgroup><col width="160"/><col width="244"/></colgroup>'
            '<thead><tr><th vertical-align="top"><p id="head-1">指标</p></th>'
            '<th vertical-align="top"><p id="head-2">方法</p></th></tr></thead>'
            '<tbody><tr><td vertical-align="top"><p id="body-1">目标</p></td>'
            '<td vertical-align="top"><p id="body-2">分层</p></td></tr></tbody></table>'
            '<h2 block-id="chapter-2">实施安排</h2><p block-id="other-body">其他</p></document>'
        )
        self.service.bind("doxcn-demo001")
        with patch.object(WritingWorkspace, "_schema_errors", return_value=[]):
            self.service.pull("SEC-1")
        payload = json.loads((self.project / "artifacts/11-technical-content.json").read_text())
        body = next(x for x in payload["data"]["chapters"] if x["section_id"] == "SEC-1")["body_markdown"]
        self.assertIn("| 指标 | 方法 |", body)
        self.assertIn("| --- | --- |", body)
        self.assertIn("| 目标 | 分层 |", body)

        self.client.xml = self.client.xml.replace(
            '<th vertical-align="top"><p id="head-1">指标</p></th>',
            '<th colspan="2"><p id="head-1">指标</p></th>'
        )
        before = (self.project / "artifacts/11-technical-content.json").read_bytes()
        with self.assertRaisesRegex(OnlineDocumentError, "合并单元格"):
            self.service.pull("SEC-1")
        self.assertEqual((self.project / "artifacts/11-technical-content.json").read_bytes(), before)

    def test_pull_rejects_unsupported_remote_resource_without_local_write(self) -> None:
        self.service.bind("doxcn-demo001")
        self._write("artifacts/13-visuals.json", {
            "schema_version": "1.0", "skill_id": "bid-visuals", "project_id": "P-001", "revision": 1,
            "data": {"figures": []},
        })
        self.client.xml = self.client.xml.replace(
            '<p block-id="old-duplicate">旧重复标题</p>',
            '<img block-id="old-duplicate" src="resource-1"/>',
        )
        before = (self.project / "artifacts/11-technical-content.json").read_bytes()
        with self.assertRaisesRegex(OnlineDocumentError, "未登记"):
            self.service.pull("SEC-1")
        self.assertEqual((self.project / "artifacts/11-technical-content.json").read_bytes(), before)

    def test_table_inline_format_loss_fails_readback_verification(self) -> None:
        payload = json.loads((self.project / "artifacts/11-technical-content.json").read_text())
        payload["data"]["chapters"][0]["body_markdown"] = (
            "| **指标** | 方法 |\n| --- | --- |\n| 目标 | 分层 |"
        )
        self._write("artifacts/11-technical-content.json", payload)
        self.service.bind("doxcn-demo001")
        original_update = self.client.update

        def strip_inline(*args, **kwargs):
            result = original_update(*args, **kwargs)
            self.client.xml = self.client.xml.replace("<b>指标</b>", "指标")
            return result

        self.client.update = strip_inline
        with self.assertRaisesRegex(OnlineDocumentError, "回读正文不一致"):
            self.service.push("SEC-1")
        self.assertNotIn("last_synced", self.service.status()["current_mapping"]["SEC-1"])

    def test_path_safe_local_image_and_malformed_remote_xml(self) -> None:
        self.service.bind("doxcn-demo001")
        self.client.xml = "<document><h2 block-id=\"chapter-1\">技术方案"
        with self.assertRaisesRegex(OnlineDocumentError, "XML"):
            self.service.fetch()
        self._write("artifacts/13-visuals.json", {
            "schema_version": "1.0", "skill_id": "bid-visuals", "project_id": "P-001", "revision": 1,
            "data": {"figures": [{"section_id": "SEC-1", "rendered_path": "../escape.png", "state": "rendered"}]},
        })
        self.client.xml = self.remote_xml
        with self.assertRaisesRegex(OnlineDocumentError, "项目内"):
            self.service.push("SEC-1")

    def test_cli_client_uses_project_cwd_explicit_identity_and_stdin(self) -> None:
        client = FeishuCliClient(cwd=self.project)
        completed = type("Completed", (), {"returncode": 0, "stdout": '{"ok":true}', "stderr": ""})()
        with patch("online_documents.subprocess.run", return_value=completed) as run:
            client._run(["lark-cli", "docs", "+update"], document="doxcn-demo001",
                        identity="user", stdin="<p>内容</p>", write=True)
        kwargs = run.call_args.kwargs
        self.assertEqual(kwargs["cwd"], str(self.project.resolve()))
        self.assertFalse(kwargs["shell"])
        self.assertEqual(kwargs["input"], "<p>内容</p>")

    def test_cli_error_redacts_document_token(self) -> None:
        client = FeishuCliClient(cwd=self.project)
        completed = type("Completed", (), {"returncode": 1, "stdout": "", "stderr": "failed docx/doxcn-demo001"})()
        with patch("online_documents.subprocess.run", return_value=completed):
            with self.assertRaises(OnlineDocumentError) as caught:
                client._run(["lark-cli"], document="https://feishu.cn/docx/doxcn-demo001",
                            identity="user", write=True)
        self.assertNotIn("doxcn-demo001", str(caught.exception))

    def test_cli_json_error_extracts_safe_code_and_message(self) -> None:
        client = FeishuCliClient(cwd=self.project)
        completed = type("Completed", (), {
            "returncode": 1, "stdout": json.dumps({"error": {
                "code": "app_scope_not_applied", "message": "token=doxcn-demo001 denied",
            }}), "stderr": "",
        })()
        with patch("online_documents.subprocess.run", return_value=completed):
            with self.assertRaises(OnlineDocumentError) as caught:
                client._run(["lark-cli"], document="https://feishu.cn/docx/doxcn-demo001",
                            identity="user", write=True)
        self.assertIn("app_scope_not_applied", str(caught.exception))
        self.assertNotIn("doxcn-demo001", str(caught.exception))

    def test_cli_partial_json_response_is_returned_for_reconciliation(self) -> None:
        client = FeishuCliClient(cwd=self.project)
        completed = type("Completed", (), {
            "returncode": 1, "stdout": json.dumps({"ok": False, "data": {
                "result": "success", "local_resource_failures": [{"kind": "image"}],
            }}), "stderr": "",
        })()
        with patch("online_documents.subprocess.run", return_value=completed):
            result = client._run(["lark-cli"], document="doxcn-demo001", identity="user", write=True)
        self.assertFalse(result["ok"])
        self.assertTrue(result["data"]["local_resource_failures"])


class NumberedChapterMappingTests(unittest.TestCase):
    def test_internal_numbered_homonym_is_not_an_outline_chapter(self):
        sections = [
            {"id": "MAIN", "number": "9", "title": "服务方案"},
            {"id": "EMERGENCY", "number": "9.13", "title": "应急响应措施"},
        ]
        root = ElementTree.fromstring(
            '<document><h1 id="main">服务方案</h1><p id="intro">总述</p>'
            '<h2 id="internal">4. 应急响应措施</h2><p id="summary">摘要</p></document>'
        )
        mapping = _remote_mapping(root, sections)
        self.assertNotIn("EMERGENCY", mapping)
        self.assertIsNone(mapping["MAIN"]["unsafe_reason"])
        self.assertEqual(mapping["MAIN"]["last_block_id"], "summary")

    def test_matching_numbered_child_still_protects_parent(self):
        sections = [
            {"id": "MAIN", "number": "9", "title": "服务方案"},
            {"id": "EMERGENCY", "number": "9.13", "title": "应急响应措施"},
        ]
        root = ElementTree.fromstring(
            '<document><h1 id="main">服务方案</h1><p id="intro">总述</p>'
            '<h2 id="child">9.13 应急响应措施</h2><p id="body">完整正文</p></document>'
        )
        mapping = _remote_mapping(root, sections)
        self.assertEqual(mapping["EMERGENCY"]["heading_block_id"], "child")
        self.assertEqual(mapping["MAIN"]["unsafe_reason"], "nested_outline_section")


if __name__ == "__main__":
    unittest.main()
