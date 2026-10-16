#!/usr/bin/env python3
"""Portable online-document synchronisation for the bid skills suite.

The module deliberately keeps the provider boundary small.  Feishu is implemented
through the installed ``lark-cli`` executable; the client can be replaced in tests
or by a future provider without changing the project/synchronisation rules.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence
from urllib.parse import urlparse, urlunparse
from xml.etree import ElementTree

from writing_workspace import WritingWorkspace, WorkspaceError


SCHEMA_VERSION = "1.0"
DEFAULT_TIMEOUT = 30
SUPPORTED_PROVIDERS = {"feishu", "tencent", "office"}
# A deliberately explicit registry: ``None`` means the provider is recognised
# for future extension but is not silently treated as connected today.
PROVIDER_REGISTRY: dict[str, Any] = {"feishu": None, "tencent": None, "office": None}
PROVIDER_DOMAINS = {
    "feishu.cn": "feishu",
    "larksuite.com": "feishu",
    "open.feishu.cn": "feishu",
    "docs.qq.com": "tencent",
    "office.com": "office",
    "sharepoint.com": "office",
}
RASTER_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp"}
_TOKEN_RE = re.compile(r"^[A-Za-z0-9_-]{6,256}$")
_ID_ATTRS = ("block-id", "block_id", "id")
_HEADING_RE = re.compile(r"^h([1-6])$")


class OnlineDocumentError(ValueError):
    """Expected adapter failure with a stable code for the CLI and callers."""

    def __init__(self, message: str, code: str = "online_document_error", status: int = 400):
        super().__init__(message)
        self.code = code
        self.status = status


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _copy(value: Any) -> Any:
    return json.loads(json.dumps(value, ensure_ascii=False))


def _digest_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _digest_text(value: str) -> str:
    return _digest_bytes(value.encode("utf-8"))


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise OnlineDocumentError(f"缺少项目文件：{path.name}", "missing_project_file", 404) from exc
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise OnlineDocumentError(f"项目文件不可读：{path.name}", "invalid_project", 422) from exc
    if not isinstance(value, dict):
        raise OnlineDocumentError(f"项目文件必须是 JSON 对象：{path.name}", "invalid_project", 422)
    return value


def _safe_path(project: Path, relative: str, label: str, *, must_exist: bool = False) -> Path:
    if not isinstance(relative, str) or not relative.strip():
        raise OnlineDocumentError(f"{label}不能为空", "invalid_input")
    candidate = Path(relative)
    if candidate.is_absolute() or ".." in candidate.parts:
        raise OnlineDocumentError(f"{label}必须位于项目内", "path_traversal", 422)
    resolved = (project / candidate).resolve()
    if not resolved.is_relative_to(project):
        raise OnlineDocumentError(f"{label}越过项目目录", "path_traversal", 422)
    if must_exist and not resolved.is_file():
        raise OnlineDocumentError(f"缺少{label}：{relative}", "missing_project_file", 404)
    return resolved


def _atomic_write(path: Path, data: str | bytes, *, binary: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        mode = "wb" if binary else "w"
        kwargs = {} if binary else {"encoding": "utf-8"}
        with os.fdopen(fd, mode, **kwargs) as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def _append_audit(path: Path, event: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(dict(event), ensure_ascii=False) + "\n")
        stream.flush()
        os.fsync(stream.fileno())


def _relative(project: Path, path: Path) -> str:
    return path.relative_to(project).as_posix()


def _xml_local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1].lower()


def _text(node: ElementTree.Element) -> str:
    return " ".join("".join(node.itertext()).split())


def _element_id(node: ElementTree.Element) -> str | None:
    for key in _ID_ATTRS:
        value = node.attrib.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _serialize(node: ElementTree.Element) -> str:
    return ElementTree.tostring(node, encoding="unicode", short_empty_elements=True)


def _canonical_url(value: str) -> tuple[str, str, str]:
    """Return canonical URL, provider hint, and document token.

    Feishu accepts both ``/docx/<token>`` and ``/wiki/<token>`` URLs.  A raw
    token is accepted for callers that already resolved a URL.  Fragments are
    intentionally discarded because block anchors are not document identity.
    """
    if not isinstance(value, str) or not value.strip():
        raise OnlineDocumentError("在线文档 URL/token 不能为空", "invalid_url")
    raw = value.strip()
    parsed = urlparse(raw)
    if not parsed.scheme and not parsed.netloc:
        if not _TOKEN_RE.fullmatch(raw):
            raise OnlineDocumentError("在线文档 token 格式无效", "invalid_url")
        return raw, "feishu", raw
    if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password:
        raise OnlineDocumentError("在线文档 URL 必须是安全的 HTTP(S) 地址", "invalid_url")
    host = parsed.hostname.lower()
    provider = PROVIDER_DOMAINS.get(host)
    if provider is None:
        provider = next((kind for domain, kind in PROVIDER_DOMAINS.items() if host.endswith("." + domain)), None)
    if provider is None:
        raise OnlineDocumentError("未识别在线文档提供方", "unsupported_provider")
    parts = [part for part in parsed.path.split("/") if part]
    token = ""
    if provider == "feishu":
        try:
            index = next(i for i, part in enumerate(parts) if part in {"docx", "wiki"})
            token = parts[index + 1]
        except (StopIteration, IndexError) as exc:
            raise OnlineDocumentError("飞书 URL 缺少 docx/wiki token", "invalid_url") from exc
    elif parts:
        token = parts[-1]
    if not _TOKEN_RE.fullmatch(token):
        raise OnlineDocumentError("在线文档 URL token 格式无效", "invalid_url")
    canonical = urlunparse((parsed.scheme.lower(), parsed.netloc.lower(), parsed.path.rstrip("/"), "", parsed.query, ""))
    return canonical, provider, token


def _provider_for(value: str, explicit: str) -> str:
    if explicit not in {"auto", *SUPPORTED_PROVIDERS}:
        raise OnlineDocumentError("provider 必须是 auto、feishu、tencent 或 office", "invalid_input")
    _, inferred, _ = _canonical_url(value)
    provider = inferred if explicit == "auto" else explicit
    if provider != inferred and inferred != "feishu":
        raise OnlineDocumentError("provider 与在线文档 URL 不匹配", "provider_mismatch")
    if PROVIDER_REGISTRY.get(provider) is None:
        raise OnlineDocumentError(
            f"当前提供方 {provider} 已登记但尚未实现；仅支持 Feishu，保留后续扩展边界",
            "unsupported_provider", 501,
        )
    return provider


def _parse_xml(xml: str) -> ElementTree.Element:
    if not isinstance(xml, str) or not xml.strip():
        raise OnlineDocumentError("在线文档 XML 为空", "malformed_xml", 422)
    try:
        root = ElementTree.fromstring(xml)
    except ElementTree.ParseError as exc:
        raise OnlineDocumentError("在线文档 XML 无法解析", "malformed_xml", 422) from exc
    if _xml_local_name(root.tag) == "fragment":
        return root
    return root


def _top_blocks(root: ElementTree.Element) -> list[ElementTree.Element]:
    return list(root)


def _heading_info(root: ElementTree.Element) -> list[dict[str, Any]]:
    blocks = _top_blocks(root)
    headings: list[dict[str, Any]] = []
    for index, block in enumerate(blocks):
        match = _HEADING_RE.fullmatch(_xml_local_name(block.tag))
        if not match:
            continue
        block_id = _element_id(block)
        headings.append({
            "index": index,
            "level": int(match.group(1)),
            "title": _text(block),
            "block_id": block_id,
        })
    return headings


def _chapter_slice(root: ElementTree.Element, heading: Mapping[str, Any]) -> tuple[list[ElementTree.Element], int]:
    blocks = _top_blocks(root)
    start = int(heading["index"])
    level = int(heading["level"])
    end = len(blocks)
    for candidate in _heading_info(root):
        if candidate["index"] <= start:
            continue
        if candidate["level"] <= level:
            end = int(candidate["index"])
            break
    return blocks[start:end], end


def _markdown_to_xml(markdown: str, project: Path) -> list[ElementTree.Element]:
    if not isinstance(markdown, str) or not markdown.strip():
        raise OnlineDocumentError("章节正文不能为空", "empty_chapter")
    blocks: list[ElementTree.Element] = []
    paragraph: list[str] = []

    def flush() -> None:
        if paragraph:
            node = ElementTree.Element("p")
            node.text = " ".join(part.strip() for part in paragraph if part.strip())
            blocks.append(node)
            paragraph.clear()

    for line in markdown.splitlines():
        stripped = line.strip()
        if not stripped:
            flush()
            continue
        heading = re.match(r"^(#{1,6})\s+(.+?)\s*$", stripped)
        if heading:
            flush()
            node = ElementTree.Element(f"h{len(heading.group(1))}")
            node.text = heading.group(2)
            blocks.append(node)
            continue
        image = re.match(r"^!\[([^]]*)\]\(([^)]+)\)\s*$", stripped)
        if image:
            flush()
            blocks.append(_local_image(project, image.group(2), image.group(1)))
            continue
        if stripped.startswith("<") and stripped.endswith(">"):
            # Local drafts may already contain a documented image tag.  Parse and
            # validate it so source files remain editable, but reject other raw XML.
            try:
                node = ElementTree.fromstring(stripped)
            except ElementTree.ParseError as exc:
                raise OnlineDocumentError("章节包含无效 XML", "unsupported_rich_content", 422) from exc
            if _xml_local_name(node.tag) != "img" or "path" not in node.attrib:
                raise OnlineDocumentError("章节包含不支持的富文本", "unsupported_rich_content", 422)
            flush()
            blocks.append(_local_image(project, node.attrib["path"], node.attrib.get("caption", "")))
            continue
        list_item = re.match(r"^(?:[-*]|\d+[.)])\s+(.+)$", stripped)
        if list_item:
            flush()
            node = ElementTree.Element("p")
            node.text = ("• " if not stripped[0].isdigit() else "") + list_item.group(1)
            blocks.append(node)
            continue
        paragraph.append(stripped)
    flush()
    return blocks


def _local_image(project: Path, value: str, caption: str = "") -> ElementTree.Element:
    raw = value.strip()
    if raw.startswith("@./"):
        raw = raw[3:]
    path = _safe_path(project, raw, "图片路径", must_exist=True)
    if path.suffix.lower() not in RASTER_EXTENSIONS:
        raise OnlineDocumentError("在线文档仅支持本地栅格图片", "unsupported_resource", 422)
    node = ElementTree.Element("img", {"path": "@./" + _relative(project, path)})
    if caption:
        node.set("caption", caption.strip())
    return node


def _local_section_xml(project: Path, section: Mapping[str, Any], chapter: Mapping[str, Any], figures: Sequence[Mapping[str, Any]]) -> str:
    level = min(max(int(section.get("depth", 0)) + 1, 1), 6)
    root = ElementTree.Element("section")
    heading = ElementTree.SubElement(root, f"h{level}")
    heading.text = str(section.get("title") or chapter.get("title") or "未命名章节")
    body_nodes = _markdown_to_xml(str(chapter.get("body_markdown") or ""), project)
    seen_images: set[str] = set()
    for node in body_nodes:
        if _xml_local_name(node.tag) == "img":
            seen_images.add(node.attrib.get("path", ""))
        root.append(node)
    for figure in figures:
        rendered = figure.get("rendered_path")
        if not rendered or figure.get("state") not in {"rendered", "reviewed"}:
            continue
        node = _local_image(project, str(rendered), str(figure.get("caption") or figure.get("title") or ""))
        if node.attrib.get("path") not in seen_images:
            root.append(node)
            seen_images.add(node.attrib.get("path", ""))
    # Feishu update accepts a sequence of documented top-level blocks.  Keep the
    # synthetic container out of the payload so it never reaches the provider.
    return "".join(_serialize(node) for node in root)


def _remote_mapping(root: ElementTree.Element, sections: Sequence[Mapping[str, Any]]) -> dict[str, dict[str, Any]]:
    headings = _heading_info(root)
    latest: dict[str, dict[str, Any]] = {}
    for heading in headings:
        title = str(heading.get("title") or "").strip()
        if title:
            latest[title] = dict(heading)
    mapping: dict[str, dict[str, Any]] = {}
    used_titles: set[str] = set()
    for section in sections:
        title = str(section.get("title") or "").strip()
        if not title or title in used_titles or title not in latest:
            continue
        used_titles.add(title)
        heading = latest[title]
        nodes, end = _chapter_slice(root, heading)
        ids = [_element_id(node) for node in nodes]
        if any(node_id is None for node_id in ids):
            first_id = last_id = None
        else:
            first_id, last_id = ids[0], ids[-1]
        section_xml = "<section>" + "".join(_serialize(node) for node in nodes) + "</section>"
        mapping[str(section["id"])] = {
            "section_id": str(section["id"]),
            "title": title,
            "heading_level": int(heading["level"]),
            "heading_block_id": heading.get("block_id"),
            "first_block_id": first_id,
            "last_block_id": last_id,
            "block_count": len(nodes),
            "remote_hash": _digest_text(section_xml),
            "remote_xml": section_xml,
            "mapped_at": _now(),
        }
    return mapping


def _response_document(response: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(response, Mapping):
        raise OnlineDocumentError("在线文档响应不是 JSON 对象", "remote_invalid_response", 502)
    if response.get("ok") is False:
        raise OnlineDocumentError("在线文档读取失败", "remote_read_failed", 502)
    data = response.get("data") if isinstance(response.get("data"), Mapping) else response
    document = data.get("document") if isinstance(data, Mapping) else None
    if not isinstance(document, Mapping):
        raise OnlineDocumentError("在线文档响应缺少 document", "remote_invalid_response", 502)
    result = dict(document)
    content = result.get("content")
    if not isinstance(content, str):
        raise OnlineDocumentError("在线文档响应缺少 XML content", "remote_invalid_response", 502)
    result["content"] = content
    result["reference_map"] = result.get("reference_map") if isinstance(result.get("reference_map"), Mapping) else {}
    return result


class FeishuCliClient:
    """Default client using lark-cli with explicit identity and bounded calls."""

    def __init__(self, timeout: int = DEFAULT_TIMEOUT, cwd: str | Path | None = None):
        self.timeout = timeout
        self.cwd = str(Path(cwd).resolve()) if cwd is not None else os.getcwd()

    @staticmethod
    def _redact(message: str, document: str) -> str:
        text = str(message or "")
        parsed = urlparse(document)
        token = document if not parsed.scheme else next((part for part in parsed.path.split("/") if len(part) >= 6), "")
        if document:
            text = text.replace(document, "<document>")
        if token:
            text = text.replace(token, "<document-token>")
        return re.sub(r"(token|access[_-]?token|authorization|secret)[=:][^\s,;]+", r"\1=<redacted>", text, flags=re.I)[:1000]

    def _run(self, argv: list[str], *, document: str, identity: str, stdin: str | None = None, write: bool = False) -> dict[str, Any]:
        try:
            completed = subprocess.run(
                argv,
                cwd=self.cwd,
                input=stdin,
                text=True,
                capture_output=True,
                timeout=self.timeout,
                check=False,
                shell=False,
            )
        except subprocess.TimeoutExpired as exc:
            code = "remote_write_unknown" if write else "remote_timeout"
            raise OnlineDocumentError("在线文档操作超时" if not write else "在线文档写入结果未知，禁止自动重试", code, 504) from exc
        except OSError as exc:
            raise OnlineDocumentError("无法启动 lark-cli", "cli_unavailable", 503) from exc
        if completed.returncode != 0:
            detail = self._redact(completed.stderr, document)
            raise OnlineDocumentError("在线文档命令失败" + (f"：{detail}" if detail else ""), "remote_command_failed", 502)
        try:
            result = json.loads(completed.stdout)
        except json.JSONDecodeError as exc:
            raise OnlineDocumentError("在线文档命令返回无效 JSON", "remote_invalid_response", 502) from exc
        if not isinstance(result, dict):
            raise OnlineDocumentError("在线文档命令返回格式无效", "remote_invalid_response", 502)
        return result

    def fetch(self, document: str, *, identity: str, revision_id: int = -1) -> dict[str, Any]:
        return self._run([
            "lark-cli", "docs", "+fetch", "--doc", document, "--doc-format", "xml",
            "--detail", "full", "--scope", "full", "--revision-id", str(revision_id), "--as", identity,
        ], document=document, identity=identity)

    def update(self, document: str, *, identity: str, revision_id: int, command: str,
               content: str, block_id: str | None = None, start_block_id: str | None = None,
               end_block_id: str | None = None) -> dict[str, Any]:
        argv = ["lark-cli", "docs", "+update", "--doc", document, "--doc-format", "xml",
                "--command", command, "--revision-id", str(revision_id), "--as", identity, "--content", "-"]
        if block_id is not None:
            argv += ["--block-id", block_id]
        if start_block_id is not None:
            argv += ["--start-block-id", start_block_id]
        if end_block_id is not None:
            argv += ["--end-block-id", end_block_id]
        return self._run(argv, document=document, identity=identity, stdin=content, write=True)


PROVIDER_REGISTRY["feishu"] = FeishuCliClient


class OnlineDocumentService:
    """Bind one bid project to one online document and synchronize by chapter."""

    def __init__(self, project: str | Path, client: Any | None = None):
        self.project = Path(project).resolve()
        if not self.project.is_dir():
            raise OnlineDocumentError("项目目录不存在", "invalid_project", 404)
        self.project_meta_path = _safe_path(self.project, "work/project.json", "项目元数据", must_exist=True)
        self.project_id = _read_json(self.project_meta_path).get("project_id")
        if not isinstance(self.project_id, str) or not self.project_id.strip():
            raise OnlineDocumentError("项目元数据缺少 project_id", "project_mismatch", 422)
        self.client = client or FeishuCliClient(cwd=self.project)

    @property
    def binding_path(self) -> Path:
        return _safe_path(self.project, "work/online-document.json", "在线文档绑定文件")

    @property
    def audit_path(self) -> Path:
        return _safe_path(self.project, "work/online-document-audit.jsonl", "在线文档审计文件")

    def _load_binding(self, *, required: bool = True) -> dict[str, Any] | None:
        if not self.binding_path.is_file():
            if required:
                raise OnlineDocumentError("尚未绑定在线文档", "not_bound", 409)
            return None
        value = _read_json(self.binding_path)
        if value.get("project_id") != self.project_id:
            raise OnlineDocumentError("在线文档绑定项目 ID 不一致", "project_mismatch", 422)
        if value.get("provider") not in SUPPORTED_PROVIDERS:
            raise OnlineDocumentError("在线文档绑定 provider 无效", "invalid_project", 422)
        return value

    def _sections(self) -> list[dict[str, Any]]:
        path = _safe_path(self.project, "artifacts/08-outline.json", "目录产物", must_exist=True)
        payload = _read_json(path)
        if payload.get("project_id") != self.project_id or payload.get("skill_id") != "bid-outline-planning":
            raise OnlineDocumentError("目录产物项目或 skill_id 不一致", "project_mismatch", 422)
        sections = payload.get("data", {}).get("sections")
        if not isinstance(sections, list):
            raise OnlineDocumentError("目录产物缺少 sections", "invalid_project", 422)
        return [item for item in sections if isinstance(item, dict) and isinstance(item.get("id"), str)]

    def _chapter(self, section_id: str) -> tuple[dict[str, Any], dict[str, Any]]:
        sections = {item["id"]: item for item in self._sections()}
        section = sections.get(section_id)
        if section is None:
            raise OnlineDocumentError("section_id 不在当前目录中", "not_found", 404)
        writing = _read_json(_safe_path(self.project, "artifacts/11-technical-content.json", "写作产物", must_exist=True))
        if writing.get("project_id") != self.project_id or writing.get("skill_id") != "bid-technical-writing":
            raise OnlineDocumentError("写作产物项目或 skill_id 不一致", "project_mismatch", 422)
        chapters = writing.get("data", {}).get("chapters", [])
        if not isinstance(chapters, list):
            raise OnlineDocumentError("写作产物 chapters 结构无效", "invalid_project", 422)
        chapter = next((x for x in chapters if isinstance(x, dict) and x.get("section_id") == section_id), None)
        if chapter is None:
            chapter = next((x for x in chapters if isinstance(x, dict) and x.get("id") == section_id), None)
        if not isinstance(chapter, dict):
            raise OnlineDocumentError("章节尚未建立本地写作记录", "local_chapter_missing", 409)
        return section, chapter

    def _figures(self, section_id: str) -> list[dict[str, Any]]:
        path = _safe_path(self.project, "artifacts/13-visuals.json", "配图产物")
        if not path.is_file():
            return []
        payload = _read_json(path)
        if payload.get("project_id") != self.project_id or payload.get("skill_id") != "bid-visuals":
            raise OnlineDocumentError("配图产物项目或 skill_id 不一致", "project_mismatch", 422)
        figures = payload.get("data", {}).get("figures", [])
        if not isinstance(figures, list):
            raise OnlineDocumentError("配图产物 figures 结构无效", "invalid_project", 422)
        return [x for x in figures if isinstance(x, dict) and x.get("section_id") == section_id]

    def _fetch_document(self, binding: Mapping[str, Any]) -> dict[str, Any]:
        response = self.client.fetch(binding["url"], identity=binding["identity"], revision_id=-1)
        document = _response_document(response)
        remote_id = document.get("document_id")
        if remote_id and binding.get("provider") == "feishu" and binding.get("url_kind") in {"docx", "token"} and remote_id != binding.get("canonical_id"):
            raise OnlineDocumentError("远程文档 ID 与绑定 token 不一致", "remote_document_mismatch", 422)
        root = _parse_xml(document["content"])
        project_attr = root.attrib.get("project-id") or root.attrib.get("project_id")
        if project_attr and project_attr != self.project_id:
            raise OnlineDocumentError("远程文档项目 ID 不一致", "project_mismatch", 422)
        document["_root"] = root
        document["_remote_id"] = remote_id or binding.get("canonical_id")
        return document

    def _snapshot(self, document: Mapping[str, Any], revision: Any) -> tuple[str, dict[str, Any]]:
        xml = str(document["content"])
        digest = _digest_text(xml)
        safe_revision = re.sub(r"[^A-Za-z0-9_.-]", "_", str(revision if revision is not None else "unknown"))
        base = f"r{safe_revision}-{digest[:12]}"
        directory = _safe_path(self.project, "work/online-document-snapshots", "在线文档快照目录")
        raw_path = directory / f"{base}.xml"
        refs_path = directory / f"{base}.references.json"
        if not raw_path.exists():
            _atomic_write(raw_path, xml)
        refs = document.get("reference_map") if isinstance(document.get("reference_map"), Mapping) else {}
        if not refs_path.exists():
            _atomic_write(refs_path, json.dumps(refs, ensure_ascii=False, indent=2) + "\n")
        return _relative(self.project, raw_path), {
            "raw_path": _relative(self.project, raw_path),
            "reference_map_path": _relative(self.project, refs_path),
            "revision_id": revision,
            "sha256": digest,
            "remote_document_id": document.get("_remote_id"),
            "saved_at": _now(),
        }

    def _refresh(self, binding: dict[str, Any], *, audit_action: str) -> dict[str, Any]:
        document = self._fetch_document(binding)
        revision = document.get("revision_id", -1)
        _, snapshot = self._snapshot(document, revision)
        mapping = _remote_mapping(document["_root"], self._sections())
        previous = binding.get("current_mapping") if isinstance(binding.get("current_mapping"), dict) else {}
        for section_id, item in mapping.items():
            old = previous.get(section_id) if isinstance(previous.get(section_id), dict) else {}
            if isinstance(old.get("last_synced"), dict):
                item["last_synced"] = _copy(old["last_synced"])
            item["remote_hash_at_fetch"] = item["remote_hash"]
        pending = self._pending(mapping)
        binding["current_mapping"] = mapping
        binding["last_fetch"] = snapshot
        binding["pending_differences"] = pending
        binding["last_remote_revision"] = revision
        binding["updated_at"] = _now()
        _atomic_write(self.binding_path, json.dumps(binding, ensure_ascii=False, indent=2) + "\n")
        _append_audit(self.audit_path, {"at": _now(), "action": audit_action, "status": "success",
                                        "revision_id": revision, "snapshot": snapshot["raw_path"],
                                        "pending_count": len(pending)})
        return {"document": document, "binding": binding}

    def _local_hash(self, section_id: str) -> tuple[str, str]:
        section, chapter = self._chapter(section_id)
        xml = _local_section_xml(self.project, section, chapter, self._figures(section_id))
        return _digest_text(xml), xml

    def _pending(self, mapping: Mapping[str, Mapping[str, Any]]) -> list[dict[str, Any]]:
        pending: list[dict[str, Any]] = []
        for section_id, item in mapping.items():
            try:
                local_hash, _ = self._local_hash(section_id)
            except OnlineDocumentError as exc:
                pending.append({"section_id": section_id, "kind": "local_unavailable", "message": str(exc)})
                continue
            receipt = item.get("last_synced") if isinstance(item.get("last_synced"), Mapping) else None
            if receipt:
                if local_hash != receipt.get("local_hash"):
                    pending.append({"section_id": section_id, "kind": "local_unpublished"})
                if item.get("remote_hash") != receipt.get("remote_hash"):
                    pending.append({"section_id": section_id, "kind": "remote_changed"})
            else:
                pending.append({"section_id": section_id, "kind": "local_unpublished"})
        mapped = set(mapping)
        for section in self._sections():
            section_id = str(section["id"])
            if section_id in mapped:
                continue
            try:
                self._local_hash(section_id)
            except OnlineDocumentError:
                continue
            # A local chapter with no remote title has never been published and
            # must keep review/check blocked until push establishes a receipt.
            pending.append({"section_id": section_id, "kind": "local_unpublished"})
        return pending

    def bind(self, url: str, identity: str = "user", provider: str = "auto") -> dict[str, Any]:
        if identity not in {"user", "bot"}:
            raise OnlineDocumentError("identity 必须是 user 或 bot", "invalid_input")
        canonical, inferred, token = _canonical_url(url)
        selected = _provider_for(url, provider)
        parsed = urlparse(canonical)
        url_kind = "docx" if "/docx/" in parsed.path else "wiki" if "/wiki/" in parsed.path else "token"
        provisional = {
            "schema_version": SCHEMA_VERSION, "project_id": self.project_id, "provider": selected,
            "url": canonical, "canonical_id": token, "url_kind": url_kind, "identity": identity,
            "bound_at": _now(), "current_mapping": {}, "pending_differences": [],
        }
        document = self._fetch_document(provisional)
        revision = document.get("revision_id", -1)
        _, snapshot = self._snapshot(document, revision)
        provisional["last_fetch"] = snapshot
        provisional["last_remote_revision"] = revision
        provisional["remote_document_id"] = document.get("_remote_id")
        provisional["current_mapping"] = _remote_mapping(document["_root"], self._sections())
        for item in provisional["current_mapping"].values():
            item["remote_hash_at_fetch"] = item["remote_hash"]
        provisional["pending_differences"] = self._pending(provisional["current_mapping"])
        _atomic_write(self.binding_path, json.dumps(provisional, ensure_ascii=False, indent=2) + "\n")
        _append_audit(self.audit_path, {"at": _now(), "action": "bind", "status": "success",
                                        "provider": selected, "revision_id": revision,
                                        "snapshot": snapshot["raw_path"]})
        return self.status()

    def status(self) -> dict[str, Any]:
        binding = self._load_binding(required=False)
        if binding is None:
            return {"bound": False, "provider": None, "url": None, "identity": None,
                    "current_mapping": {}, "pending_differences": [], "project_id": self.project_id}
        mapping = _copy(binding.get("current_mapping") if isinstance(binding.get("current_mapping"), dict) else {})
        pending = self._pending(mapping)
        return {"bound": True, "project_id": self.project_id, "provider": binding.get("provider"),
                "url": binding.get("url"), "identity": binding.get("identity"),
                "canonical_id": binding.get("canonical_id"), "last_fetch": binding.get("last_fetch"),
                "last_remote_revision": binding.get("last_remote_revision"),
                "current_mapping": mapping, "pending_differences": pending,
                "persisted_pending_differences": binding.get("pending_differences", [])}

    def fetch(self) -> dict[str, Any]:
        binding = self._load_binding()
        return self._refresh(binding, audit_action="fetch")["binding"] | {"status": self.status()}

    def _mapping_for_push(self, before: Mapping[str, Any], current: Mapping[str, Any], section_id: str) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
        old_map = before.get("current_mapping") if isinstance(before.get("current_mapping"), Mapping) else {}
        current_map = current.get("current_mapping") if isinstance(current.get("current_mapping"), Mapping) else {}
        return (old_map.get(section_id) if isinstance(old_map.get(section_id), dict) else None,
                current_map.get(section_id) if isinstance(current_map.get(section_id), dict) else None)

    def push(self, section_id: str) -> dict[str, Any]:
        before = self._load_binding()
        refreshed = self._refresh(_copy(before), audit_action="fetch_before_push")["binding"]
        old_item, item = self._mapping_for_push(before, refreshed, section_id)
        local_hash, content = self._local_hash(section_id)
        if item is None:
            # An absent title can be inserted, but an existing fetched baseline is
            # still required so a stale user cannot append into an unknown document.
            old_revision = before.get("last_remote_revision")
            if old_revision is None:
                raise OnlineDocumentError("缺少远程文档基线，请先 fetch", "missing_remote_baseline", 409)
            command = "block_insert_after"
            anchor = "-1"
            sections = self._sections()
            index = next((i for i, value in enumerate(sections) if value.get("id") == section_id), 0)
            current_map = refreshed.get("current_mapping", {})
            for previous in reversed(sections[:index]):
                candidate = current_map.get(previous.get("id")) if isinstance(current_map, dict) else None
                if isinstance(candidate, dict) and candidate.get("last_block_id"):
                    anchor = candidate["last_block_id"]
                    break
            target = {"command": command, "block_id": anchor}
        else:
            baseline = (old_item or {}).get("last_synced", {}).get("remote_hash") if isinstance((old_item or {}).get("last_synced"), Mapping) else (old_item or {}).get("remote_hash")
            if baseline and item.get("remote_hash") != baseline:
                raise OnlineDocumentError("远程章节已变化，请先 fetch/pull 后再 push", "remote_changed", 409)
            if isinstance(item.get("last_synced"), Mapping) and local_hash == item["last_synced"].get("local_hash"):
                return {"status": "unchanged", "section_id": section_id, "binding": self.status()}
            if not item.get("first_block_id") or not item.get("last_block_id"):
                raise OnlineDocumentError("远程章节缺少可编辑 block ID", "missing_block_id", 422)
            target = {"command": "block_replace", "start_block_id": item["first_block_id"], "end_block_id": item["last_block_id"]}
        revision = refreshed.get("last_remote_revision", -1)
        try:
            response = self.client.update(refreshed["url"], identity=refreshed["identity"], revision_id=revision,
                                          content=content, **target)
        except Exception:
            _append_audit(self.audit_path, {"at": _now(), "action": "push", "status": "unknown",
                                            "section_id": section_id, "revision_id": revision})
            raise
        data = response.get("data") if isinstance(response, Mapping) and isinstance(response.get("data"), Mapping) else response
        result = data.get("result") if isinstance(data, Mapping) else None
        if result != "success":
            # Never retry: a write response that is partial or unknown needs human
            # inspection before another mutation is attempted.
            _append_audit(self.audit_path, {"at": _now(), "action": "push", "status": "partial_success" if result == "partial_success" else "failed",
                                            "section_id": section_id, "revision_id": revision, "result": result})
            raise OnlineDocumentError("在线文档写入未确认成功，禁止自动重试", "partial_success" if result == "partial_success" else "remote_write_failed", 502)
        after = self._refresh(refreshed, audit_action="fetch_after_push")["binding"]
        current = after.get("current_mapping", {}).get(section_id, {})
        current["last_synced"] = {"local_hash": local_hash, "remote_hash": current.get("remote_hash"),
                                   "revision_id": after.get("last_remote_revision"), "synced_at": _now()}
        after.setdefault("current_mapping", {})[section_id] = current
        after["pending_differences"] = self._pending(after["current_mapping"])
        _atomic_write(self.binding_path, json.dumps(after, ensure_ascii=False, indent=2) + "\n")
        _append_audit(self.audit_path, {"at": _now(), "action": "push", "status": "success",
                                        "section_id": section_id, "revision_id": after.get("last_remote_revision")})
        return {"status": "pushed", "section_id": section_id, "binding": self.status()}

    def _remote_to_markdown(self, nodes: Sequence[ElementTree.Element], known_figures: Sequence[Mapping[str, Any]] = ()) -> str:
        lines: list[str] = []
        supported = {"p", "h1", "h2", "h3", "h4", "h5", "h6", "br", "b", "em", "u", "del", "img"}

        def validate(node: ElementTree.Element, *, top_level: bool = False) -> None:
            tag = _xml_local_name(node.tag)
            if tag not in supported:
                raise OnlineDocumentError("远程章节包含当前适配器不支持的富文本或资源", "unsupported_rich_content", 422)
            if tag == "img" and not top_level:
                # Image blocks are handled at the top level and reused from the
                # local rendered figure ledger; embedded unknown resources are
                # deliberately not flattened into text.
                raise OnlineDocumentError("远程章节包含嵌入式图片资源，无法安全拉回", "unsupported_rich_content", 422)
            if tag == "img":
                return
            for child in node:
                validate(child, top_level=False)

        def inline(node: ElementTree.Element) -> str:
            tag = _xml_local_name(node.tag)
            value = node.text or ""
            value += "".join(inline(child) + (child.tail or "") for child in node)
            if tag == "b":
                return f"**{value}**"
            if tag == "em":
                return f"*{value}*"
            if tag == "u":
                return f"__{value}__"
            if tag == "del":
                return f"~~{value}~~"
            if tag == "br":
                return "\n"
            return value

        image_index = 0
        for index, node in enumerate(nodes):
            tag = _xml_local_name(node.tag)
            validate(node, top_level=True)
            if tag == "img":
                if image_index >= len(known_figures):
                    raise OnlineDocumentError("远程章节包含未登记图片资源，无法安全拉回", "unsupported_rich_content", 422)
                figure = known_figures[image_index]
                rendered = figure.get("rendered_path")
                if not rendered:
                    raise OnlineDocumentError("远程图片缺少本地可复用素材", "unsupported_resource", 422)
                _safe_path(self.project, str(rendered), "图片路径", must_exist=True)
                caption = str(figure.get("caption") or figure.get("title") or "").strip()
                lines.append(f"![{caption}]({rendered})")
                image_index += 1
                if index < len(nodes) - 1:
                    lines.append("")
                continue
            if tag == "br":
                lines.append("")
                continue
            if tag.startswith("h"):
                lines.append("#" * int(tag[1:]) + " " + inline(node))
            else:
                lines.append(inline(node))
            if index < len(nodes) - 1:
                lines.append("")
        return "\n".join(lines).strip() or "远程章节为空"

    def pull(self, section_id: str) -> dict[str, Any]:
        binding = self._load_binding()
        refreshed = self._refresh(_copy(binding), audit_action="fetch_before_pull")["binding"]
        item = refreshed.get("current_mapping", {}).get(section_id)
        if not isinstance(item, dict):
            raise OnlineDocumentError("远程文档找不到对应章节标题", "remote_section_missing", 404)
        snapshot = refreshed.get("last_fetch", {})
        raw_path = _safe_path(self.project, snapshot.get("raw_path", ""), "在线文档快照", must_exist=True)
        root = _parse_xml(raw_path.read_text(encoding="utf-8"))
        heading = next((x for x in _heading_info(root) if x.get("block_id") == item.get("heading_block_id")), None)
        if heading is None:
            raise OnlineDocumentError("远程章节 block 已失效，请重新 fetch", "stale_mapping", 409)
        nodes, _ = _chapter_slice(root, heading)
        body = self._remote_to_markdown(nodes[1:], self._figures(section_id))
        workspace = WritingWorkspace(self.project, "artifacts/08-outline.json", "artifacts/11-technical-content.json")
        _, local_chapter = self._chapter(section_id)
        state = workspace.state(str(local_chapter.get("id") or section_id))
        saved = workspace.save({"expected_revision": state["writing"]["revision"],
                                "expected_sha256": state["writing"]["sha256"],
                                "chapter_id": state["chapter"]["id"], "body_markdown": body})
        local_hash, _ = self._local_hash(section_id)
        item["last_synced"] = {"local_hash": local_hash, "remote_hash": item.get("remote_hash"),
                                "revision_id": refreshed.get("last_remote_revision"), "synced_at": _now()}
        refreshed["current_mapping"][section_id] = item
        refreshed["pending_differences"] = self._pending(refreshed["current_mapping"])
        _atomic_write(self.binding_path, json.dumps(refreshed, ensure_ascii=False, indent=2) + "\n")
        _append_audit(self.audit_path, {"at": _now(), "action": "pull", "status": "success", "section_id": section_id,
                                        "revision_id": refreshed.get("last_remote_revision")})
        return {"status": "pulled", "section_id": section_id, "writing": saved, "binding": self.status()}

    def assert_current(self, section_ids: Sequence[str] | None = None) -> dict[str, Any]:
        binding = self._load_binding()
        refreshed = self._refresh(_copy(binding), audit_action="check")["binding"]
        pending = refreshed.get("pending_differences", [])
        if section_ids is not None:
            requested = {str(value) for value in section_ids}
            valid = {str(item["id"]) for item in self._sections()}
            if not requested or not requested.issubset(valid):
                raise OnlineDocumentError("section_ids 必须是当前目录中的非空章节集合", "invalid_input")
            pending = [item for item in pending if str(item.get("section_id")) in requested]
        if pending:
            kinds = ", ".join(sorted({str(item.get("kind")) for item in pending}))
            raise OnlineDocumentError(f"在线文档与本地同步收据不一致：{kinds}", "not_current", 409)
        _append_audit(self.audit_path, {"at": _now(), "action": "check", "status": "success"})
        return {"status": "current", "binding": self.status()}

    def check_current(self, section_ids: Sequence[str] | None = None) -> dict[str, Any]:
        """Alias used by API callers; reads remote state before returning."""
        return self.assert_current(section_ids)


def _cli_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Bid suite online document adapter")
    parser.add_argument("action", choices=("bind", "status", "fetch", "push", "pull", "check"))
    parser.add_argument("--project", required=True)
    parser.add_argument("--url")
    parser.add_argument("--identity", default="user", choices=("user", "bot"))
    parser.add_argument("--provider", default="auto", choices=("auto", "feishu", "tencent", "office"))
    parser.add_argument("--section-id")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = _cli_parser()
    args = parser.parse_args(argv)
    try:
        service = OnlineDocumentService(args.project)
        if args.action == "bind":
            if not args.url:
                raise OnlineDocumentError("bind 必须提供 --url", "invalid_input")
            result = service.bind(args.url, identity=args.identity, provider=args.provider)
        elif args.action == "status":
            result = service.status()
        elif args.action == "fetch":
            result = service.fetch()
        elif args.action == "push":
            if not args.section_id:
                raise OnlineDocumentError("push 必须提供 --section-id", "invalid_input")
            result = service.push(args.section_id)
        elif args.action == "pull":
            if not args.section_id:
                raise OnlineDocumentError("pull 必须提供 --section-id", "invalid_input")
            result = service.pull(args.section_id)
        else:
            result = service.assert_current([args.section_id] if args.section_id else None)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (OnlineDocumentError, WorkspaceError) as exc:
        print(json.dumps({"ok": False, "error": {"code": getattr(exc, "code", "error"), "message": str(exc)}}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
