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
from contextlib import contextmanager
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
_TITLE_PREFIX_RE = re.compile(
    r"^\s*(?:(?:第\s*[0-9一二三四五六七八九十百千万]+\s*[章节篇])|"
    r"(?:[0-9]+(?:\.[0-9]+)*\s*[、.)：:]?)|"
    r"(?:[一二三四五六七八九十百千万]+\s*[、.)：:]))\s*"
)


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


@contextmanager
def _online_lock(project: Path):
    """Serialize one project's bind/fetch/update/receipt operation.

    This lock is intentionally separate from WritingWorkspace's lock: push and
    pull must hold it while doing network I/O, then acquire the workspace lock
    only inside ``WritingWorkspace.save`` without a lock cycle.
    """
    path = _safe_path(project, "work/.online-document.lock", "在线文档锁")
    path.parent.mkdir(parents=True, exist_ok=True)
    stream = None
    fallback = False
    try:
        try:
            import fcntl
        except ImportError:  # pragma: no cover - Windows fallback.
            fcntl = None
        if fcntl is not None:
            stream = path.open("a+", encoding="utf-8")
            fcntl.flock(stream.fileno(), fcntl.LOCK_EX)
            yield
        else:
            try:
                fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            except FileExistsError as exc:
                raise OnlineDocumentError("已有在线文档操作正在执行", "lock_busy", 409) from exc
            stream = os.fdopen(fd, "w", encoding="utf-8")
            fallback = True
            yield
    finally:
        if fcntl is not None and stream is not None:
            fcntl.flock(stream.fileno(), fcntl.LOCK_UN)
        if stream is not None:
            stream.close()
        if fallback:
            path.unlink(missing_ok=True)


def _relative(project: Path, path: Path) -> str:
    return path.relative_to(project).as_posix()


def _xml_local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1].lower()


def _text(node: ElementTree.Element) -> str:
    return " ".join("".join(node.itertext()).split())


def _title_key(value: Any) -> str:
    text = " ".join(str(value or "").split())
    return _TITLE_PREFIX_RE.sub("", text).strip()


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
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise OnlineDocumentError("在线文档 URL 必须是安全的 HTTPS 地址", "invalid_url")
    if parsed.query and re.search(r"(?:^|&)(?:access[_-]?token|token|authorization|secret|password)=", parsed.query, re.I):
        raise OnlineDocumentError("在线文档 URL 不得包含敏感查询参数", "invalid_url")
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
    canonical = urlunparse(("https", parsed.netloc.lower(), parsed.path.rstrip("/"), "", "", ""))
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
    raw = xml.strip()
    try:
        root = ElementTree.fromstring(raw)
    except ElementTree.ParseError as exc:
        # lark-cli's full XML format is a top-level block sequence in some
        # responses (for example ``<title/> <p/> <h1/>``), rather than one
        # document element.  Normalize that sequence to an internal fragment
        # without changing the block XML sent back to the provider.
        without_declaration = re.sub(r"^\s*<\?xml[^>]*\?>", "", raw, count=1).strip()
        try:
            root = ElementTree.fromstring(f"<fragment>{without_declaration}</fragment>")
        except ElementTree.ParseError:
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


def _split_markdown_table_row(line: str) -> list[str] | None:
    """Split one pipe-table row while honoring escaped pipes in cell text."""
    raw = line.strip()
    if "|" not in raw or raw.startswith("!"):
        return None
    if raw.startswith("|"):
        raw = raw[1:]
    if raw.endswith("|") and not raw.endswith("\\|"):
        raw = raw[:-1]
    cells: list[str] = []
    value: list[str] = []
    escaped = False
    for char in raw:
        if char == "|" and not escaped:
            cells.append("".join(value).strip().replace("\\|", "|"))
            value.clear()
            escaped = False
            continue
        value.append(char)
        escaped = char == "\\" and not escaped
        if char != "\\":
            escaped = False
    cells.append("".join(value).strip().replace("\\|", "|"))
    return cells if cells else None


def _is_markdown_table_separator(cells: Sequence[str]) -> bool:
    return bool(cells) and all(
        bool(re.fullmatch(r":?-{3,}:?", cell.replace(" ", ""))) for cell in cells
    )


_MARKDOWN_INLINE_RE = re.compile(r"(\*\*.+?\*\*|~~.+?~~|__.+?__|\*.+?\*)")


def _append_markdown_inline(parent: ElementTree.Element, value: str) -> None:
    """Write the small inline Markdown subset supported by remote pull."""
    cursor = 0
    for match in _MARKDOWN_INLINE_RE.finditer(value):
        if match.start() > cursor:
            text = value[cursor:match.start()]
            if parent.text is None and not list(parent):
                parent.text = text
            else:
                previous = list(parent)[-1]
                previous.tail = (previous.tail or "") + text
        token = match.group(1)
        if token.startswith("**"):
            tag, inner = "b", token[2:-2]
        elif token.startswith("~~"):
            tag, inner = "del", token[2:-2]
        elif token.startswith("__"):
            tag, inner = "u", token[2:-2]
        else:
            tag, inner = "em", token[1:-1]
        child = ElementTree.SubElement(parent, tag)
        child.text = inner
        cursor = match.end()
    if cursor < len(value):
        text = value[cursor:]
        if parent.text is None and not list(parent):
            parent.text = text
        elif list(parent):
            previous = list(parent)[-1]
            previous.tail = (previous.tail or "") + text


def _markdown_table_xml(
    header: Sequence[str], rows: Sequence[Sequence[str]]
) -> ElementTree.Element:
    table = ElementTree.Element("table")
    thead = ElementTree.SubElement(table, "thead")
    header_row = ElementTree.SubElement(thead, "tr")
    for value in header:
        cell = ElementTree.SubElement(header_row, "th")
        paragraph = ElementTree.SubElement(cell, "p")
        _append_markdown_inline(paragraph, value)
    tbody = ElementTree.SubElement(table, "tbody")
    for row in rows:
        table_row = ElementTree.SubElement(tbody, "tr")
        for value in row:
            cell = ElementTree.SubElement(table_row, "td")
            paragraph = ElementTree.SubElement(cell, "p")
            _append_markdown_inline(paragraph, value)
    return table


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

    lines = markdown.splitlines()
    index = 0
    while index < len(lines):
        line = lines[index]
        stripped = line.strip()
        if not stripped:
            flush()
            index += 1
            continue
        table_header = _split_markdown_table_row(stripped)
        if table_header is not None and index + 1 < len(lines):
            separator = _split_markdown_table_row(lines[index + 1])
            if separator is not None and _is_markdown_table_separator(separator):
                if len(table_header) != len(separator) or not table_header:
                    raise OnlineDocumentError("Markdown 表格必须是矩形", "unsupported_rich_content", 422)
                rows: list[list[str]] = []
                next_index = index + 2
                while next_index < len(lines):
                    row = _split_markdown_table_row(lines[next_index])
                    if row is None:
                        break
                    if len(row) != len(table_header):
                        raise OnlineDocumentError("Markdown 表格必须是矩形", "unsupported_rich_content", 422)
                    rows.append(row)
                    next_index += 1
                if not rows:
                    raise OnlineDocumentError("Markdown 表格至少需要一行数据", "unsupported_rich_content", 422)
                flush()
                blocks.append(_markdown_table_xml(table_header, rows))
                index = next_index
                continue
        heading = re.match(r"^(#{1,6})\s+(.+?)\s*$", stripped)
        if heading:
            flush()
            node = ElementTree.Element(f"h{len(heading.group(1))}")
            node.text = heading.group(2)
            blocks.append(node)
            index += 1
            continue
        image = re.match(r"^!\[([^]]*)\]\(([^)]+)\)\s*$", stripped)
        if image:
            flush()
            blocks.append(_local_image(project, image.group(2), image.group(1)))
            index += 1
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
            index += 1
            continue
        list_item = re.match(r"^(?:[-*]|\d+[.)])\s+(.+)$", stripped)
        if list_item:
            flush()
            node = ElementTree.Element("p")
            node.text = ("• " if not stripped[0].isdigit() else "") + list_item.group(1)
            blocks.append(node)
            index += 1
            continue
        paragraph.append(stripped)
        index += 1
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


def _rebase_heading_levels(xml: str, old_root_level: int, new_root_level: int) -> str:
    try:
        root = ElementTree.fromstring(f"<fragment>{xml}</fragment>")
    except ElementTree.ParseError as exc:
        raise OnlineDocumentError("本地章节 XML 无法解析", "invalid_project", 422) from exc
    delta = int(new_root_level) - int(old_root_level)
    for node in root:
        match = _HEADING_RE.fullmatch(_xml_local_name(node.tag))
        if not match:
            continue
        node.tag = f"h{min(max(int(match.group(1)) + delta, 1), 6)}"
    return "".join(_serialize(node) for node in root)


def _local_section_xml(project: Path, section: Mapping[str, Any], chapter: Mapping[str, Any],
                       figures: Sequence[Mapping[str, Any]], heading_level: int | None = None) -> str:
    local_level = min(max(int(section.get("depth", 0)) + 1, 1), 6)
    level = min(max(int(heading_level or local_level), 1), 6)
    root = ElementTree.Element("section")
    heading = ElementTree.SubElement(root, f"h{level}")
    heading.text = str(section.get("title") or chapter.get("title") or "未命名章节")
    body_nodes = _markdown_to_xml(str(chapter.get("body_markdown") or ""), project)
    duplicate_heading_level: int | None = None
    if body_nodes and _HEADING_RE.fullmatch(_xml_local_name(body_nodes[0].tag)):
        if _title_key(_text(body_nodes[0])) == _title_key(section.get("title") or chapter.get("title")):
            duplicate_heading_level = int(_xml_local_name(body_nodes[0].tag)[1:])
            body_nodes = body_nodes[1:]
            for node in body_nodes:
                match = _HEADING_RE.fullmatch(_xml_local_name(node.tag))
                if match and int(match.group(1)) > duplicate_heading_level:
                    node.tag = f"h{max(int(match.group(1)) - 1, 1)}"
    body_xml = "".join(_serialize(node) for node in body_nodes)
    body_xml = _rebase_heading_levels(body_xml, local_level, level)
    body_root = ElementTree.fromstring(f"<fragment>{body_xml}</fragment>") if body_xml else ElementTree.Element("fragment")
    seen_images: set[str] = set()
    for node in body_root:
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


def _local_image_descriptors(project: Path, xml: str) -> list[dict[str, str]]:
    """Return ordered local image paths and byte hashes for a candidate XML."""
    try:
        root = ElementTree.fromstring(f"<fragment>{xml}</fragment>")
    except ElementTree.ParseError as exc:  # pragma: no cover - generated XML is validated above.
        raise OnlineDocumentError("本地章节 XML 无法解析", "invalid_project", 422) from exc
    result: list[dict[str, str]] = []
    for node in root.iter():
        if _xml_local_name(node.tag) != "img":
            continue
        value = node.attrib.get("path")
        if not value:
            raise OnlineDocumentError("本地图片缺少 path", "unsupported_resource", 422)
        raw = value[3:] if value.startswith("@./") else value
        path = _safe_path(project, raw, "图片路径", must_exist=True)
        result.append({"relative_path": _relative(project, path), "sha256": _digest_bytes(path.read_bytes()),
                       "caption": node.attrib.get("caption", "")})
    return result


def _local_snapshot(project: Path, section: Mapping[str, Any], chapter: Mapping[str, Any],
                    figures: Sequence[Mapping[str, Any]]) -> tuple[str, str, list[dict[str, str]]]:
    xml = _local_section_xml(project, section, chapter, figures)
    images = _local_image_descriptors(project, xml)
    hash_input = xml + "\n" + json.dumps(images, ensure_ascii=False, sort_keys=True)
    return _digest_text(hash_input), xml, images


_TABLE_INLINE_TAGS = {"b", "em", "u", "del", "br"}


def _simple_table_rows(
    table: ElementTree.Element,
) -> tuple[list[ElementTree.Element], list[list[ElementTree.Element]]]:
    """Validate and return the header/data cell nodes for a simple table.

    The adapter deliberately accepts the documented table shape only.  A table
    with merged cells, styling attributes, nested blocks, or uneven rows is
    rejected so pull never silently changes the meaning of a rich document.
    """
    if _xml_local_name(table.tag) != "table":
        raise OnlineDocumentError("远程章节表格结构无效", "unsupported_rich_content", 422)
    if any(key not in _ID_ATTRS for key in table.attrib):
        raise OnlineDocumentError("远程章节表格包含复杂属性", "unsupported_rich_content", 422)
    parts = list(table)
    if parts and _xml_local_name(parts[0].tag) == "colgroup":
        colgroup = parts.pop(0)
        if any(key not in _ID_ATTRS for key in colgroup.attrib):
            raise OnlineDocumentError("远程章节表格列定义属性不支持", "unsupported_rich_content", 422)
        cols = list(colgroup)
        if not cols or any(_xml_local_name(col.tag) != "col" for col in cols):
            raise OnlineDocumentError("远程章节表格列定义结构无效", "unsupported_rich_content", 422)
        for col in cols:
            if any(key not in {"width", "span", *_ID_ATTRS} for key in col.attrib):
                raise OnlineDocumentError("远程章节表格列定义属性不支持", "unsupported_rich_content", 422)
    if len(parts) != 2 or [_xml_local_name(part.tag) for part in parts] != ["thead", "tbody"]:
        raise OnlineDocumentError("远程章节包含复杂表格，当前适配器拒绝拉回", "unsupported_rich_content", 422)
    thead, tbody = parts
    if any(any(key not in _ID_ATTRS for key in part.attrib) for part in parts):
        raise OnlineDocumentError("远程章节表格包含复杂属性", "unsupported_rich_content", 422)
    header_rows = list(thead)
    body_rows = list(tbody)
    if (len(header_rows) != 1 or not body_rows or
            any(_xml_local_name(row.tag) != "tr" for row in header_rows + body_rows)):
        raise OnlineDocumentError("远程章节表格缺少简单行结构", "unsupported_rich_content", 422)

    def cells(row: ElementTree.Element, expected: str) -> list[ElementTree.Element]:
        result = list(row)
        if not result or any(_xml_local_name(cell.tag) != expected for cell in result):
            raise OnlineDocumentError("远程章节表格单元格结构不支持", "unsupported_rich_content", 422)
        if any(key not in _ID_ATTRS for key in row.attrib):
            raise OnlineDocumentError("远程章节表格行属性不支持", "unsupported_rich_content", 422)
        for cell in result:
            # Any colspan/rowspan, including an explicit value of 1, can hide
            # an omitted cell in the source XML.  Keep this boundary strict.
            if any(key in cell.attrib for key in ("colspan", "rowspan")):
                raise OnlineDocumentError("远程章节表格包含合并单元格", "unsupported_rich_content", 422)
            if any(key not in {"vertical-align", *_ID_ATTRS} for key in cell.attrib):
                raise OnlineDocumentError("远程章节表格包含复杂单元格属性", "unsupported_rich_content", 422)
            if ("vertical-align" in cell.attrib and
                    cell.attrib["vertical-align"] not in {"top", "middle", "bottom"}):
                raise OnlineDocumentError("远程章节表格单元格对齐属性无效", "unsupported_rich_content", 422)
            paragraphs = list(cell)
            if len(paragraphs) != 1 or _xml_local_name(paragraphs[0].tag) != "p":
                raise OnlineDocumentError("远程章节表格单元格必须只包含一个段落", "unsupported_rich_content", 422)
            paragraph = paragraphs[0]
            if any(key not in _ID_ATTRS for key in paragraph.attrib):
                raise OnlineDocumentError("远程章节表格段落属性不支持", "unsupported_rich_content", 422)

            def validate_inline(node: ElementTree.Element) -> None:
                if _xml_local_name(node.tag) not in _TABLE_INLINE_TAGS:
                    raise OnlineDocumentError("远程章节表格包含嵌套块内容", "unsupported_rich_content", 422)
                if any(key not in _ID_ATTRS for key in node.attrib):
                    raise OnlineDocumentError("远程章节表格行内属性不支持", "unsupported_rich_content", 422)
                for child in node:
                    validate_inline(child)

            for child in paragraph:
                validate_inline(child)
        return result

    header = cells(header_rows[0], "th")
    data = [cells(row, "td") for row in body_rows]
    width = len(header)
    if any(len(row) != width for row in data):
        raise OnlineDocumentError("远程章节表格行列数不一致", "unsupported_rich_content", 422)
    return header, data


def _inline_semantics(node: ElementTree.Element) -> list[Any]:
    """Capture inline structure while ignoring provider-generated IDs."""
    result: list[Any] = [_xml_local_name(node.tag), node.text or ""]
    for child in node:
        result.append(_inline_semantics(child))
        result.append(child.tail or "")
    return result


def _simple_table_semantics(table: ElementTree.Element) -> list[list[Any]]:
    header, data = _simple_table_rows(table)
    return [[_inline_semantics(cell[0]) for cell in header]] + [
        [_inline_semantics(cell[0]) for cell in row] for row in data
    ]


def _remote_mapping(root: ElementTree.Element, sections: Sequence[Mapping[str, Any]]) -> dict[str, dict[str, Any]]:
    headings = _heading_info(root)
    outline_titles = {_title_key(section.get("title")): str(section.get("id")) for section in sections}
    title_counts: dict[str, int] = {}
    for heading in headings:
        title = _title_key(heading.get("title"))
        if title:
            title_counts[title] = title_counts.get(title, 0) + 1
    latest: dict[str, dict[str, Any]] = {}
    for heading in headings:
        title = _title_key(heading.get("title"))
        if title:
            latest[title] = dict(heading)
    mapping: dict[str, dict[str, Any]] = {}
    used_titles: set[str] = set()
    for section in sections:
        title = _title_key(section.get("title"))
        if not title or title in used_titles or title not in latest:
            continue
        used_titles.add(title)
        heading = latest[title]
        nodes, end = _chapter_slice(root, heading)
        ids = [_element_id(node) for node in nodes]
        nested = [
            {"title": candidate["title"], "level": candidate["level"], "block_id": candidate.get("block_id")}
            for candidate in _heading_info(root)
            if heading["index"] < candidate["index"] < end and candidate["level"] > heading["level"]
        ]
        nested_outline_section_ids = [
            outline_titles[_title_key(candidate["title"])]
            for candidate in _heading_info(root)
            if heading["index"] < candidate["index"] < end
            and candidate["level"] > heading["level"]
            and _title_key(candidate["title"]) in outline_titles
            and outline_titles[_title_key(candidate["title"])] != str(section["id"])
        ]
        if any(node_id is None for node_id in ids):
            first_id = last_id = None
        else:
            first_id, last_id = ids[0], ids[-1]
        section_xml = "<section>" + "".join(_serialize(node) for node in nodes) + "</section>"
        mapping[str(section["id"])] = {
            "section_id": str(section["id"]),
            "title": str(heading.get("title") or title).strip(),
            "heading_level": int(heading["level"]),
            "heading_block_id": heading.get("block_id"),
            "first_block_id": first_id,
            "last_block_id": last_id,
            "block_count": len(nodes),
            "nested_headings": nested,
            "nested_outline_section_ids": nested_outline_section_ids,
            "unsafe_reason": "nested_outline_section" if nested_outline_section_ids else None,
            "duplicate_title": title_counts.get(title, 0) > 1,
            "remote_hash": _digest_text(section_xml),
            "remote_xml": section_xml,
            "mapped_at": _now(),
        }
    return mapping


def _remote_image_ref(node: ElementTree.Element) -> str | None:
    for key in ("token", "src", "data-ref", "ref", "href", "path"):
        value = node.attrib.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _reference_contains(value: Any, needle: str) -> bool:
    if isinstance(value, str):
        return value == needle
    if isinstance(value, Mapping):
        return any(_reference_contains(key, needle) or _reference_contains(child, needle)
                   for key, child in value.items())
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return any(_reference_contains(child, needle) for child in value)
    return False


def _has_target_comments(reference_map: Mapping[str, Any], block_ids: set[str]) -> bool:
    comments = reference_map.get("comments") if isinstance(reference_map, Mapping) else None
    if comments is None:
        return False
    values = comments.values() if isinstance(comments, Mapping) else comments if isinstance(comments, Sequence) else (comments,)
    for value in values:
        candidates: list[str] = []
        def collect(candidate: Any) -> None:
            if isinstance(candidate, Mapping):
                for key, child in candidate.items():
                    normalized = str(key).lower().replace("_", "-")
                    if "block" in normalized and isinstance(child, (str, int)):
                        candidates.append(str(child))
                    collect(child)
            elif isinstance(candidate, Sequence) and not isinstance(candidate, (str, bytes, bytearray)):
                for child in candidate:
                    collect(child)
            elif isinstance(candidate, str):
                candidates.extend(re.findall(r"(?:block-id|block_id|blockId)=[\"']([^\"']+)[\"']", candidate))
        collect(value)
        if set(candidates) & block_ids:
            return True
    return False


def _remote_semantics(xml: str) -> tuple[str, list[dict[str, str | None]]]:
    try:
        root = ElementTree.fromstring(xml)
    except ElementTree.ParseError as exc:
        raise OnlineDocumentError("远程章节 XML 无法解析", "remote_invalid_response", 502) from exc
    text_parts: list[str] = []
    images: list[dict[str, str | None]] = []
    for node in root:
        if _xml_local_name(node.tag) == "img":
            images.append({"ref": _remote_image_ref(node), "path": node.attrib.get("path")})
            continue
        if _xml_local_name(node.tag) == "table":
            text_parts.append("TABLE:" + json.dumps(_simple_table_semantics(node), ensure_ascii=False,
                                                       separators=(",", ":")))
            continue
        text_parts.append(" ".join("".join(node.itertext()).split()))
    return "\n".join(text_parts), images


def _block_ids_from_xml(xml: str) -> set[str]:
    try:
        root = ElementTree.fromstring(xml)
    except ElementTree.ParseError:
        return set()
    return {block_id for node in root.iter() if (block_id := _element_id(node))}


def _heading_signature(xml: str) -> list[list[Any]]:
    try:
        root = ElementTree.fromstring(f"<fragment>{xml}</fragment>")
    except ElementTree.ParseError:
        return []
    headings = []
    first = True
    for node in root:
        match = _HEADING_RE.fullmatch(_xml_local_name(node.tag))
        if not match:
            continue
        if first:
            first = False
            continue
        headings.append([_title_key(_text(node)), int(match.group(1))])
    return headings


def _mapping_heading_signature(item: Mapping[str, Any]) -> list[list[Any]]:
    nested = item.get("nested_headings") if isinstance(item.get("nested_headings"), Sequence) else []
    return [[_title_key(value.get("title")), int(value.get("level", 0))]
            for value in nested if isinstance(value, Mapping)]


def _response_document(response: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(response, Mapping):
        raise OnlineDocumentError("在线文档响应不是 JSON 对象", "remote_invalid_response", 502)
    if response.get("ok") is False:
        data = response.get("data") if isinstance(response.get("data"), Mapping) else {}
        if data.get("local_resource_failures"):
            raise OnlineDocumentError("在线文档资源处理未完成", "remote_partial_success", 502)
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

    # lark-cli's revision argument is not a documented atomic compare-and-swap
    # for block_replace.  Existing chapter replacement therefore requires a
    # provider client that explicitly guarantees conditional replacement.
    atomic_replace = False
    strict_unique_titles = True

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
            detail_source = completed.stderr
            try:
                payload = json.loads(completed.stdout or "")
            except json.JSONDecodeError:
                payload = None
            if isinstance(payload, Mapping):
                data = payload.get("data") if isinstance(payload.get("data"), Mapping) else payload
                if payload.get("ok") is False or (isinstance(data, Mapping) and data.get("local_resource_failures")):
                    # Preserve the structured failure for the service.  It will
                    # reject the mutation and persist reconciliation state; do
                    # not turn a provider partial response into a blind retry.
                    return dict(payload)
                error = payload.get("error") if isinstance(payload.get("error"), Mapping) else (
                    data.get("error") if isinstance(data, Mapping) and isinstance(data.get("error"), Mapping) else None
                )
                if isinstance(error, Mapping):
                    detail_source = ": ".join(str(error[key]) for key in ("code", "message") if error.get(key))
            detail = self._redact(detail_source, document)
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
        refs = document.get("reference_map") if isinstance(document.get("reference_map"), Mapping) else {}
        refs_json = json.dumps(refs, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        digest = _digest_text(xml)
        snapshot_key = _digest_text(xml + "\n" + refs_json)
        safe_revision = re.sub(r"[^A-Za-z0-9_.-]", "_", str(revision if revision is not None else "unknown"))
        base = f"r{safe_revision}-{snapshot_key[:12]}"
        directory = _safe_path(self.project, "work/online-document-snapshots", "在线文档快照目录")
        raw_path = directory / f"{base}.xml"
        refs_path = directory / f"{base}.references.json"
        if not raw_path.exists():
            _atomic_write(raw_path, xml)
        if not refs_path.exists():
            _atomic_write(refs_path, json.dumps(refs, ensure_ascii=False, indent=2) + "\n")
        return _relative(self.project, raw_path), {
            "raw_path": _relative(self.project, raw_path),
            "reference_map_path": _relative(self.project, refs_path),
            "revision_id": revision,
            "sha256": digest,
            "reference_map_sha256": _digest_text(refs_json),
            "snapshot_key_sha256": snapshot_key,
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
            item["reference_map_sha256"] = snapshot.get("reference_map_sha256")
        if not isinstance(binding.get("baseline_mapping"), dict):
            # Migrate bindings written by the first adapter revision.  The first
            # observed remote state is the immutable conflict baseline; it is
            # advanced only after a verified push or pull receipt.
            binding["baseline_mapping"] = _copy(previous or mapping)
        pending = self._pending(mapping)
        for section_id in (binding.get("pending_write_unknown", {}) or {}):
            pending.append({"section_id": str(section_id), "kind": "write_unknown"})
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
        digest, xml, _ = _local_snapshot(self.project, section, chapter, self._figures(section_id))
        return digest, xml

    def _local_candidate(self, section_id: str) -> tuple[str, str, list[dict[str, str]]]:
        section, chapter = self._chapter(section_id)
        return _local_snapshot(self.project, section, chapter, self._figures(section_id))

    def _local_candidate_for_body(self, section_id: str, body: str) -> tuple[str, str, list[dict[str, str]]]:
        section, chapter = self._chapter(section_id)
        candidate = _copy(chapter)
        candidate["body_markdown"] = body
        return _local_snapshot(self.project, section, candidate, self._figures(section_id))

    def _pending(self, mapping: Mapping[str, Mapping[str, Any]]) -> list[dict[str, Any]]:
        pending: list[dict[str, Any]] = []
        for section_id, item in mapping.items():
            try:
                local_hash, _ = self._local_hash(section_id)
            except OnlineDocumentError as exc:
                pending.append({"section_id": section_id, "kind": "local_unavailable", "message": str(exc)})
                continue
            receipt = item.get("last_synced") if isinstance(item.get("last_synced"), Mapping) else None
            if item.get("duplicate_title") and bool(getattr(self.client, "strict_unique_titles", False)):
                pending.append({"section_id": section_id, "kind": "duplicate_title_unsafe"})
            if receipt:
                if local_hash != receipt.get("local_hash"):
                    pending.append({"section_id": section_id, "kind": "local_unpublished"})
                if (item.get("remote_hash") != receipt.get("remote_hash") or
                        (receipt.get("reference_map_sha256") and
                         item.get("reference_map_sha256") != receipt.get("reference_map_sha256"))):
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

    def _bind_locked(self, url: str, identity: str = "user", provider: str = "auto") -> dict[str, Any]:
        if identity not in {"user", "bot"}:
            raise OnlineDocumentError("identity 必须是 user 或 bot", "invalid_input")
        canonical, inferred, token = _canonical_url(url)
        selected = _provider_for(url, provider)
        parsed = urlparse(canonical)
        url_kind = "docx" if "/docx/" in parsed.path else "wiki" if "/wiki/" in parsed.path else "token"
        existing = self._load_binding(required=False)
        if existing is not None and (existing.get("provider"), existing.get("canonical_id")) != (selected, token):
            raise OnlineDocumentError("项目已绑定其他在线文档；当前接口没有 reset，请先保留原绑定", "binding_conflict", 409)
        provisional = {
            "schema_version": SCHEMA_VERSION, "project_id": self.project_id, "provider": selected,
            "url": canonical, "canonical_id": token, "url_kind": url_kind, "identity": identity,
            "bound_at": existing.get("bound_at", _now()) if existing else _now(),
            "current_mapping": {}, "pending_differences": [],
        }
        if existing:
            for key in ("baseline_mapping", "current_mapping", "last_fetch", "last_remote_revision",
                        "remote_document_id", "pending_differences", "pending_write_unknown"):
                if key in existing:
                    provisional[key] = _copy(existing[key])
        document = self._fetch_document(provisional)
        revision = document.get("revision_id", -1)
        _, snapshot = self._snapshot(document, revision)
        provisional["last_fetch"] = snapshot
        provisional["last_remote_revision"] = revision
        provisional["remote_document_id"] = document.get("_remote_id")
        mapping = _remote_mapping(document["_root"], self._sections())
        old_mapping = existing.get("current_mapping", {}) if existing else {}
        for section_id, item in mapping.items():
            old = old_mapping.get(section_id) if isinstance(old_mapping, Mapping) else None
            if isinstance(old, Mapping) and isinstance(old.get("last_synced"), Mapping):
                item["last_synced"] = _copy(old["last_synced"])
            item["remote_hash_at_fetch"] = item["remote_hash"]
            item["reference_map_sha256"] = snapshot.get("reference_map_sha256")
        provisional["current_mapping"] = mapping
        if not isinstance(provisional.get("baseline_mapping"), dict):
            provisional["baseline_mapping"] = _copy(existing.get("current_mapping", mapping) if existing else mapping)
        provisional["pending_differences"] = self._pending(provisional["current_mapping"])
        _atomic_write(self.binding_path, json.dumps(provisional, ensure_ascii=False, indent=2) + "\n")
        _append_audit(self.audit_path, {"at": _now(), "action": "bind", "status": "success",
                                        "provider": selected, "revision_id": revision,
                                        "snapshot": snapshot["raw_path"]})
        return self.status()

    def bind(self, url: str, identity: str = "user", provider: str = "auto") -> dict[str, Any]:
        with _online_lock(self.project):
            return self._bind_locked(url, identity=identity, provider=provider)

    def status(self) -> dict[str, Any]:
        binding = self._load_binding(required=False)
        if binding is None:
            return {"bound": False, "provider": None, "url": None, "identity": None,
                    "current_mapping": {}, "pending_differences": [], "project_id": self.project_id}
        mapping = _copy(binding.get("current_mapping") if isinstance(binding.get("current_mapping"), dict) else {})
        pending = self._pending(mapping)
        for section_id in (binding.get("pending_write_unknown", {}) or {}):
            pending.append({"section_id": str(section_id), "kind": "write_unknown"})
        return {"bound": True, "project_id": self.project_id, "provider": binding.get("provider"),
                "url": binding.get("url"), "identity": binding.get("identity"),
                "canonical_id": binding.get("canonical_id"), "last_fetch": binding.get("last_fetch"),
                "last_remote_revision": binding.get("last_remote_revision"),
                "current_mapping": mapping, "pending_differences": pending,
                "persisted_pending_differences": binding.get("pending_differences", []),
                "pending_write_unknown": binding.get("pending_write_unknown", {})}

    def _fetch_locked(self) -> dict[str, Any]:
        binding = self._load_binding()
        return self._refresh(binding, audit_action="fetch")["binding"] | {"status": self.status()}

    def fetch(self) -> dict[str, Any]:
        with _online_lock(self.project):
            return self._fetch_locked()

    def _mapping_for_push(self, before: Mapping[str, Any], current: Mapping[str, Any], section_id: str) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
        old_map = before.get("current_mapping") if isinstance(before.get("current_mapping"), Mapping) else {}
        current_map = current.get("current_mapping") if isinstance(current.get("current_mapping"), Mapping) else {}
        return (old_map.get(section_id) if isinstance(old_map.get(section_id), dict) else None,
                current_map.get(section_id) if isinstance(current_map.get(section_id), dict) else None)

    def _persist_pending_write(self, binding: Mapping[str, Any], section_id: str, candidate_hash: str,
                               revision: Any, reason: str) -> None:
        updated = _copy(binding)
        pending = updated.setdefault("pending_write_unknown", {})
        pending[str(section_id)] = {"candidate_hash": candidate_hash, "revision_id": revision,
                                    "reason": reason, "at": _now()}
        _atomic_write(self.binding_path, json.dumps(updated, ensure_ascii=False, indent=2) + "\n")

    def _verify_readback(self, expected_xml: str, item: Mapping[str, Any], reference_map: Mapping[str, Any],
                         prior_receipt: Mapping[str, Any] | None) -> list[dict[str, str]]:
        expected_text, expected_images = _remote_semantics("<section>" + expected_xml + "</section>")
        actual_text, actual_images = _remote_semantics(str(item.get("remote_xml") or "<section/>"))
        if expected_text != actual_text:
            raise OnlineDocumentError("在线文档写入回读正文不一致", "remote_readback_mismatch", 502)
        if len(expected_images) != len(actual_images):
            raise OnlineDocumentError("在线文档写入回读图片数量不一致", "remote_resource_mismatch", 502)
        prior_resources = prior_receipt.get("resource_map", []) if isinstance(prior_receipt, Mapping) else []
        if prior_resources and len(prior_resources) != len(actual_images):
            raise OnlineDocumentError("在线文档资源映射数量变化，拒绝确认收据", "remote_resource_mismatch", 502)
        resources: list[dict[str, str]] = []
        for index, (expected, actual) in enumerate(zip(expected_images, actual_images)):
            ref = actual.get("ref")
            if not ref:
                raise OnlineDocumentError("在线文档回读图片缺少资源 token", "remote_resource_mismatch", 502)
            expected_path = expected.get("path")
            actual_path = actual.get("path")
            if expected_path and actual_path and expected_path != actual_path:
                raise OnlineDocumentError("在线文档回读图片路径不一致", "remote_resource_mismatch", 502)
            # A local @./ path is the portable fake/provider representation.  A
            # provider token must also appear in the full reference map so a
            # success response cannot silently drop the actual resource.
            if not str(ref).startswith("@./") and reference_map and not _reference_contains(reference_map, str(ref)):
                raise OnlineDocumentError("在线文档回读图片未出现在资源引用表", "remote_resource_mismatch", 502)
            if prior_resources and str(prior_resources[index].get("remote_ref")) != str(ref):
                raise OnlineDocumentError("在线文档图片资源 token 顺序变化", "remote_resource_mismatch", 502)
            expected_descriptor = _local_image_descriptors(self.project, expected_xml)[index]
            resources.append({"remote_ref": str(ref), "relative_path": expected_descriptor["relative_path"],
                              "local_sha256": expected_descriptor["sha256"],
                              "caption": expected_descriptor.get("caption", "")})
        return resources

    def _push_locked(self, section_id: str) -> dict[str, Any]:
        before = self._load_binding()
        pending_unknown = before.get("pending_write_unknown") if isinstance(before.get("pending_write_unknown"), Mapping) else {}
        if section_id in pending_unknown:
            raise OnlineDocumentError("上次在线文档写入结果未知，请先 pull 或人工核对后再 push",
                                      "write_reconciliation_required", 409)
        candidate_hash, content, _ = self._local_candidate(section_id)
        local_section, _ = self._chapter(section_id)
        local_level = min(max(int(local_section.get("depth", 0)) + 1, 1), 6)
        refreshed_result = self._refresh(_copy(before), audit_action="fetch_before_push")
        refreshed = refreshed_result["binding"]
        document = refreshed_result["document"]
        old_item, item = self._mapping_for_push(before, refreshed, section_id)
        current_candidate_hash, _, _ = self._local_candidate(section_id)
        if current_candidate_hash != candidate_hash:
            raise OnlineDocumentError("本地章节在远程写入前发生变化，请重新 push", "local_changed", 409)
        if item is None:
            # An absent title can be inserted, but an existing fetched baseline is
            # still required so a stale user cannot append into an unknown document.
            old_revision = before.get("last_remote_revision")
            if old_revision is None:
                raise OnlineDocumentError("缺少远程文档基线，请先 fetch", "missing_remote_baseline", 409)
            command = "block_insert_after"
            anchor = "-1"
            insert_level = local_level
            sections = self._sections()
            index = next((i for i, value in enumerate(sections) if value.get("id") == section_id), 0)
            current_map = refreshed.get("current_mapping", {})
            for previous in reversed(sections[:index]):
                candidate = current_map.get(previous.get("id")) if isinstance(current_map, dict) else None
                if isinstance(candidate, dict) and candidate.get("last_block_id"):
                    anchor = candidate["last_block_id"]
                    insert_level = int(candidate.get("heading_level") or insert_level)
                    break
            if anchor == "-1":
                for following in sections[index + 1:]:
                    candidate = current_map.get(following.get("id")) if isinstance(current_map, dict) else None
                    if isinstance(candidate, dict) and candidate.get("first_block_id"):
                        insert_level = int(candidate.get("heading_level") or insert_level)
                        break
            target = {"command": command, "block_id": anchor}
            content = _rebase_heading_levels(content, local_level, insert_level)
        else:
            baseline_map = before.get("baseline_mapping") if isinstance(before.get("baseline_mapping"), Mapping) else {}
            baseline_item = baseline_map.get(section_id) if isinstance(baseline_map, Mapping) else None
            if not isinstance(baseline_item, Mapping):
                raise OnlineDocumentError("远程章节缺少不可变同步基线，请先 pull 或重新建立绑定", "remote_changed", 409)
            baseline = baseline_item.get("remote_hash") if isinstance(baseline_item, Mapping) else (old_item or {}).get("remote_hash")
            baseline_ref = baseline_item.get("reference_map_sha256") if isinstance(baseline_item, Mapping) else None
            if baseline and (item.get("remote_hash") != baseline or
                             (baseline_ref and item.get("reference_map_sha256") != baseline_ref)):
                raise OnlineDocumentError("远程章节已变化，请先 fetch/pull 后再 push", "remote_changed", 409)
            content = _rebase_heading_levels(content, local_level, int(item.get("heading_level") or 1))
            if item.get("unsafe_reason") or item.get("nested_headings"):
                receipt = item.get("last_synced") if isinstance(item.get("last_synced"), Mapping) else {}
                if item.get("unsafe_reason") == "nested_outline_section" or (
                        not receipt and _heading_signature(content) != _mapping_heading_signature(item)) or (
                        receipt and _heading_signature(content) != _mapping_heading_signature(item)):
                    raise OnlineDocumentError("目标章节包含未确认的嵌套子章节，当前安全更新拒绝覆盖", "nested_section_unsafe", 409)
            if item.get("duplicate_title") and bool(getattr(self.client, "strict_unique_titles", False)):
                raise OnlineDocumentError("远程文档存在重复章节标题，无法安全确定替换范围", "duplicate_title_unsafe", 409)
            if isinstance(item.get("last_synced"), Mapping) and candidate_hash == item["last_synced"].get("local_hash"):
                return {"status": "unchanged", "section_id": section_id, "binding": self.status()}
            if not bool(getattr(self.client, "atomic_replace", False)):
                raise OnlineDocumentError("当前提供方未保证章节替换的原子版本校验，请先 pull 或使用原生合并端点",
                                          "requires_native_merge", 501)
            reference_map = document.get("reference_map", {})
            block_ids = _block_ids_from_xml(str(item.get("remote_xml") or ""))
            if _has_target_comments(reference_map, block_ids):
                raise OnlineDocumentError("目标章节包含评论引用，当前安全更新拒绝覆盖", "comments_unsupported", 409)
            if not item.get("first_block_id") or not item.get("last_block_id"):
                raise OnlineDocumentError("远程章节缺少可编辑 block ID", "missing_block_id", 422)
            target = {"command": "block_replace", "start_block_id": item["first_block_id"], "end_block_id": item["last_block_id"]}
        revision = refreshed.get("last_remote_revision", -1)
        try:
            response = self.client.update(refreshed["url"], identity=refreshed["identity"], revision_id=revision,
                                          content=content, **target)
        except Exception:
            self._persist_pending_write(refreshed, section_id, candidate_hash, revision, "exception")
            _append_audit(self.audit_path, {"at": _now(), "action": "push", "status": "unknown",
                                            "section_id": section_id, "revision_id": revision})
            raise
        data = response.get("data") if isinstance(response, Mapping) and isinstance(response.get("data"), Mapping) else response
        result = data.get("result") if isinstance(data, Mapping) else None
        resource_failures = data.get("local_resource_failures") if isinstance(data, Mapping) else None
        if (isinstance(response, Mapping) and response.get("ok") is False) or resource_failures or result != "success":
            # Never retry: a write response that is partial or unknown needs human
            # inspection before another mutation is attempted.
            _append_audit(self.audit_path, {"at": _now(), "action": "push", "status": "partial_success" if result == "partial_success" else "failed",
                                            "section_id": section_id, "revision_id": revision, "result": result})
            self._persist_pending_write(refreshed, section_id, candidate_hash, revision, str(result or "failed"))
            code = "remote_partial_success" if resource_failures or result == "partial_success" or (isinstance(response, Mapping) and response.get("ok") is False) else "remote_write_failed"
            raise OnlineDocumentError("在线文档写入未确认成功，禁止自动重试", code, 502)
        try:
            after_result = self._refresh(refreshed, audit_action="fetch_after_push")
        except Exception:
            self._persist_pending_write(refreshed, section_id, candidate_hash, revision, "postwrite_refresh_failed")
            _append_audit(self.audit_path, {"at": _now(), "action": "push", "status": "unknown",
                                            "section_id": section_id, "revision_id": revision,
                                            "reason": "postwrite_refresh_failed"})
            raise
        after = after_result["binding"]
        current = after.get("current_mapping", {}).get(section_id, {})
        current_candidate_hash, _, _ = self._local_candidate(section_id)
        if current_candidate_hash != candidate_hash:
            self._persist_pending_write(after, section_id, candidate_hash, revision, "local_changed_after_write")
            raise OnlineDocumentError("远程写入后本地章节发生变化，未生成同步收据", "local_changed_after_write", 409)
        try:
            resources = self._verify_readback(content, current, after_result["document"].get("reference_map", {}),
                                              (old_item or {}).get("last_synced") if isinstance(old_item, Mapping) else None)
        except OnlineDocumentError:
            self._persist_pending_write(after, section_id, candidate_hash, revision, "readback_mismatch")
            raise
        current["last_synced"] = {"local_hash": candidate_hash, "remote_hash": current.get("remote_hash"),
                                   "revision_id": after.get("last_remote_revision"), "synced_at": _now(),
                                   "reference_map_sha256": current.get("reference_map_sha256"),
                                   "resource_map": resources,
                                   "nested_signature": _mapping_heading_signature(current)}
        after.setdefault("current_mapping", {})[section_id] = current
        after.setdefault("baseline_mapping", {})[section_id] = _copy(current)
        after["pending_differences"] = self._pending(after["current_mapping"])
        after.setdefault("pending_write_unknown", {}).pop(section_id, None)
        _atomic_write(self.binding_path, json.dumps(after, ensure_ascii=False, indent=2) + "\n")
        _append_audit(self.audit_path, {"at": _now(), "action": "push", "status": "success",
                                        "section_id": section_id, "revision_id": after.get("last_remote_revision")})
        return {"status": "pushed", "section_id": section_id, "binding": self.status()}

    def push(self, section_id: str) -> dict[str, Any]:
        with _online_lock(self.project):
            return self._push_locked(section_id)

    def _remote_to_markdown(self, nodes: Sequence[ElementTree.Element], resource_map: Sequence[Mapping[str, Any]] = (),
                            reference_map: Mapping[str, Any] | None = None, chapter_level: int = 1,
                            local_root_level: int = 1) -> str:
        lines: list[str] = []
        supported = {"p", "h1", "h2", "h3", "h4", "h5", "h6", "br", "b", "em", "u", "del", "img", "table"}

        def validate(node: ElementTree.Element, *, top_level: bool = False) -> None:
            tag = _xml_local_name(node.tag)
            if tag not in supported:
                raise OnlineDocumentError("远程章节包含当前适配器不支持的富文本或资源", "unsupported_rich_content", 422)
            if tag == "table":
                _simple_table_rows(node)
                return
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

        def table_markdown(node: ElementTree.Element) -> list[str]:
            header, data = _simple_table_rows(node)
            rows = [[inline(cell[0]) for cell in header]]
            rows.extend([[inline(cell[0]) for cell in row] for row in data])

            def format_row(row: Sequence[str]) -> str:
                # A literal pipe would make the resulting Markdown ambiguous;
                # escape it rather than changing the number of cells.
                if any("\n" in value for value in row):
                    raise OnlineDocumentError(
                        "远程章节表格包含不支持的换行富文本", "unsupported_rich_content", 422
                    )
                values = [value.replace("|", r"\|") for value in row]
                return "| " + " | ".join(values) + " |"

            result = [
                format_row(rows[0]),
                "| " + " | ".join("---" for _ in rows[0]) + " |",
            ]
            result.extend(format_row(row) for row in rows[1:])
            return result

        image_index = 0
        for index, node in enumerate(nodes):
            tag = _xml_local_name(node.tag)
            validate(node, top_level=True)
            if tag == "img":
                if image_index >= len(resource_map):
                    raise OnlineDocumentError("远程章节包含未登记图片资源，无法安全拉回", "unsupported_rich_content", 422)
                resource = resource_map[image_index]
                ref = _remote_image_ref(node)
                if not ref or ref != resource.get("remote_ref"):
                    raise OnlineDocumentError("远程图片资源 token 顺序或映射不一致", "remote_resource_mismatch", 409)
                if reference_map and not str(ref).startswith("@./") and not _reference_contains(reference_map, str(ref)):
                    raise OnlineDocumentError("远程图片资源未出现在引用表", "remote_resource_mismatch", 409)
                rendered = resource.get("relative_path")
                if not rendered:
                    raise OnlineDocumentError("远程图片缺少本地可复用素材", "unsupported_resource", 422)
                path = _safe_path(self.project, str(rendered), "图片路径", must_exist=True)
                if _digest_bytes(path.read_bytes()) != resource.get("local_sha256"):
                    raise OnlineDocumentError("本地图片资源已变化，无法安全拉回", "remote_resource_mismatch", 409)
                caption = str(resource.get("caption") or "").strip()
                lines.append(f"![{caption}]({rendered})")
                image_index += 1
                if index < len(nodes) - 1:
                    lines.append("")
                continue
            if tag == "br":
                lines.append("")
                continue
            if tag == "table":
                lines.extend(table_markdown(node))
                if index < len(nodes) - 1:
                    lines.append("")
                continue
            if tag.startswith("h"):
                local_level = min(max(local_root_level + int(tag[1:]) - int(chapter_level), 1), 6)
                lines.append("#" * local_level + " " + inline(node))
            else:
                lines.append(inline(node))
            if index < len(nodes) - 1:
                lines.append("")
        return "\n".join(lines).strip() or "远程章节为空"

    def _pull_locked(self, section_id: str) -> dict[str, Any]:
        binding = self._load_binding()
        refreshed_result = self._refresh(_copy(binding), audit_action="fetch_before_pull")
        refreshed = refreshed_result["binding"]
        item = refreshed.get("current_mapping", {}).get(section_id)
        if not isinstance(item, dict):
            raise OnlineDocumentError("远程文档找不到对应章节标题", "remote_section_missing", 404)
        if item.get("duplicate_title") and bool(getattr(self.client, "strict_unique_titles", False)):
            raise OnlineDocumentError("远程文档存在重复章节标题，无法安全拉回", "duplicate_title_unsafe", 409)
        if item.get("unsafe_reason"):
            if item.get("unsafe_reason") == "nested_outline_section":
                raise OnlineDocumentError("目标章节包含未确认的嵌套子章节，当前安全拉回拒绝覆盖", "nested_section_unsafe", 409)
            receipt = item.get("last_synced") if isinstance(item.get("last_synced"), Mapping) else {}
            if not receipt or receipt.get("nested_signature") != _mapping_heading_signature(item):
                raise OnlineDocumentError("目标章节包含未确认的嵌套子章节，当前安全拉回拒绝覆盖", "nested_section_unsafe", 409)
        root = refreshed_result["document"]["_root"]
        heading = next((x for x in _heading_info(root) if x.get("block_id") == item.get("heading_block_id")), None)
        if heading is None:
            raise OnlineDocumentError("远程章节 block 已失效，请重新 fetch", "stale_mapping", 409)
        nodes, _ = _chapter_slice(root, heading)
        section, local_chapter = self._chapter(section_id)
        local_root_level = min(max(int(section.get("depth", 0)) + 1, 1), 6)
        receipt = item.get("last_synced") if isinstance(item.get("last_synced"), Mapping) else {}
        resource_map = receipt.get("resource_map", []) if isinstance(receipt, Mapping) else []
        body = self._remote_to_markdown(nodes[1:], resource_map, refreshed_result["document"].get("reference_map", {}),
                                        chapter_level=int(item.get("heading_level") or 1),
                                        local_root_level=local_root_level)
        workspace = WritingWorkspace(self.project, "artifacts/08-outline.json", "artifacts/11-technical-content.json")
        figures = self._figures(section_id)
        state = workspace.state(str(local_chapter.get("id") or section_id), include_advisories=False)
        saved = workspace.save({"expected_revision": state["writing"]["revision"],
                                "expected_sha256": state["writing"]["sha256"],
                                "chapter_id": state["chapter"]["id"], "body_markdown": body},
                                include_advisories=False)
        written_chapter = _copy(local_chapter)
        written_chapter["body_markdown"] = body
        written_hash, _, _ = _local_snapshot(self.project, section, written_chapter, figures)
        item["last_synced"] = {"local_hash": written_hash, "remote_hash": item.get("remote_hash"),
                                "revision_id": refreshed.get("last_remote_revision"), "synced_at": _now(),
                                "reference_map_sha256": item.get("reference_map_sha256"),
                                "resource_map": list(resource_map),
                                "nested_signature": _mapping_heading_signature(item)}
        refreshed["current_mapping"][section_id] = item
        refreshed.setdefault("baseline_mapping", {})[section_id] = _copy(item)
        refreshed.setdefault("pending_write_unknown", {}).pop(section_id, None)
        refreshed["pending_differences"] = self._pending(refreshed["current_mapping"])
        _atomic_write(self.binding_path, json.dumps(refreshed, ensure_ascii=False, indent=2) + "\n")
        _append_audit(self.audit_path, {"at": _now(), "action": "pull", "status": "success", "section_id": section_id,
                                        "revision_id": refreshed.get("last_remote_revision")})
        return {"status": "pulled", "section_id": section_id, "writing": saved, "binding": self.status()}

    def pull(self, section_id: str) -> dict[str, Any]:
        with _online_lock(self.project):
            return self._pull_locked(section_id)

    def _assert_current_locked(self, section_ids: Sequence[str] | None = None) -> dict[str, Any]:
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

    def assert_current(self, section_ids: Sequence[str] | None = None) -> dict[str, Any]:
        with _online_lock(self.project):
            return self._assert_current_locked(section_ids)

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
