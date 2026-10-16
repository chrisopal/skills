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

from online_documents import FeishuCliClient, OnlineDocumentError, OnlineDocumentService  # noqa: E402
from writing_workspace import WritingWorkspace  # noqa: E402


class FakeClient:
    """Small in-memory Feishu-shaped client for adapter contract tests."""

    def __init__(self, xml: str, *, references: dict | None = None):
        self.xml = xml
        self.revision = 7
        self.references = references or {"img": {"r1": {"token": "resource-1"}}}
        self.fetch_calls: list[dict] = []
        self.update_calls: list[dict] = []
        self.result = "success"
        self.mutate_before_update = False

    def fetch(self, document: str, *, identity: str, revision_id: int = -1) -> dict:
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
        return {"ok": True, "data": {"result": "success", "updated_blocks_count": len(incoming)}}

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

    def test_push_is_idempotent_and_rerun_does_not_append_duplicate(self) -> None:
        self.service.bind("doxcn-demo001")
        self.service.push("SEC-1")
        second = self.service.push("SEC-1")
        self.assertEqual(second["status"], "unchanged")
        self.assertEqual(len(self.client.update_calls), 1)

    def test_push_rejects_remote_change_since_last_snapshot(self) -> None:
        self.service.bind("doxcn-demo001")
        self.client.remote_edit("第三方修改")
        with self.assertRaisesRegex(OnlineDocumentError, "远程章节已变化"):
            self.service.push("SEC-1")
        self.assertEqual(self.client.update_calls, [])

    def test_partial_success_is_failure_and_never_retried(self) -> None:
        self.service.bind("doxcn-demo001")
        self.client.result = "partial_success"
        with self.assertRaisesRegex(OnlineDocumentError, "禁止自动重试"):
            self.service.push("SEC-1")
        self.assertEqual(len(self.client.update_calls), 1)
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

    def test_pull_reuses_known_local_image_resource(self) -> None:
        self.service.bind("doxcn-demo001")
        self.client.xml = self.client.xml.replace(
            '<p block-id="old-duplicate">旧重复标题</p>',
            '<img block-id="old-duplicate" src="resource-1"/>',
        )
        with patch.object(WritingWorkspace, "_schema_errors", return_value=[]):
            self.service.pull("SEC-1")
        payload = json.loads((self.project / "artifacts/11-technical-content.json").read_text())
        chapter = next(x for x in payload["data"]["chapters"] if x["section_id"] == "SEC-1")
        self.assertIn("![图1](assets/figure.png)", chapter["body_markdown"])

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


if __name__ == "__main__":
    unittest.main()
