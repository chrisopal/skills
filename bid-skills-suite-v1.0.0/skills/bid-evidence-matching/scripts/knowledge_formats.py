"""Small, dependency-free helpers for structured enterprise document extraction.

The public extraction contract intentionally remains a text block with a stable
location.  These helpers add table and embedded-image metadata without making
the source parser depend on a presentation library.
"""
from __future__ import annotations

import hashlib
import posixpath
import re
import zipfile
from pathlib import Path
from typing import Any
from xml.etree import ElementTree


W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
A = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PR_REL_TYPE = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/image"
SLIDE_REL_TYPE = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide"
NOTES_REL_TYPE = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/notesSlide"
NS = {
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
}


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _int_attr(element: ElementTree.Element, name: str, default: int = 1) -> int:
    value = element.attrib.get(name)
    try:
        result = int(value) if value is not None else default
    except (TypeError, ValueError):
        return default
    return result if result > 0 else default


def _sha_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _table_spec(rows: list[list[str]], merges: list[dict[str, int]] | None = None,
                *, header_rows: int = 1) -> dict[str, Any]:
    """Return the raw shape accepted by fixed_form_tables.normalize_table_spec."""
    if not rows or not rows[0] or any(len(row) != len(rows[0]) for row in rows):
        raise ValueError("表格行列不规则，无法安全保留结构")
    header_rows = max(0, min(header_rows, len(rows)))
    candidate = {
        "headers": rows[:header_rows],
        "rows": rows[header_rows:],
        "header_rows": header_rows,
        "merges": merges or [],
    }
    # Import lazily so this helper can still be copied with the extractor.
    from fixed_form_tables import normalize_table_spec

    normalized = normalize_table_spec(candidate, label="extracted_table")
    return {
        "headers": normalized["headers"],
        "rows": normalized["rows"],
        "header_rows": normalized["header_rows"],
        "merges": normalized["merges"],
    }


def table_text(table: dict[str, Any]) -> str:
    rows = table.get("headers", []) + table.get("rows", [])
    return "\n".join("\t".join(str(cell) for cell in row) for row in rows)


def docx_table_spec(table: Any) -> tuple[dict[str, Any], str]:
    """Build a merge-aware table spec from a python-docx Table.

    python-docx exposes merged cells as repeated references.  Using those
    references lets us retain both horizontal and vertical merges while the
    existing cell blocks remain available to old source-text consumers.
    """
    # Retain the cell wrappers while taking IDs.  python-docx may create a new
    # proxy for each property access; taking IDs from temporary proxies can
    # otherwise make the interpreter reuse an ID for two distinct cells.
    cell_rows = [list(row.cells) for row in table.rows]
    rows = [[cell.text.strip() for cell in cells] for cells in cell_rows]
    references = [[id(cell._tc) for cell in cells] for cells in cell_rows]
    if not rows or not rows[0]:
        raise ValueError("DOCX表格为空")
    width = len(rows[0])
    if any(len(row) != width for row in rows):
        raise ValueError("DOCX表格行列不规则")

    merges: list[dict[str, int]] = []
    seen: set[int] = set()
    for row_index, refs in enumerate(references):
        for column_index, ref in enumerate(refs):
            if ref in seen:
                continue
            positions = [
                (r, c)
                for r, ref_row in enumerate(references)
                for c, candidate in enumerate(ref_row)
                if candidate == ref
            ]
            seen.add(ref)
            min_row = min(r for r, _ in positions)
            max_row = max(r for r, _ in positions)
            min_col = min(c for _, c in positions)
            max_col = max(c for _, c in positions)
            expected = {
                (r, c)
                for r in range(min_row, max_row + 1)
                for c in range(min_col, max_col + 1)
            }
            if len(positions) > 1 and set(positions) == expected:
                merges.append({
                    "row": min_row,
                    "column": min_col,
                    "row_span": max_row - min_row + 1,
                    "col_span": max_col - min_col + 1,
                })
                for r, c in positions:
                    if (r, c) != (min_row, min_col):
                        rows[r][c] = ""

    header_rows = 0
    for row in table.rows:
        tr_pr = row._tr.find(f"{W}trPr")
        if tr_pr is None or tr_pr.find(f"{W}tblHeader") is None:
            break
        header_rows += 1
    # Tables without explicit Word header metadata still have a useful first
    # row for Wiki rendering and for the fixed-form table contract.
    if header_rows == 0:
        header_rows = 1
    spec = _table_spec(rows, merges, header_rows=header_rows)
    return spec, table_text(spec)


def _write_asset(assets_dir: Path, source_id: str, location: str, name: str,
                 data: bytes, content_type: str | None = None) -> dict[str, Any]:
    project_dir = assets_dir.parent.parent
    assets_root = project_dir / "assets"
    knowledge_root = assets_root / "knowledge"
    if assets_root.is_symlink() or knowledge_root.is_symlink():
        raise ValueError("知识资源目录或其父目录不能是符号链接")
    expected_root = project_dir.resolve() / "assets" / "knowledge"
    if assets_dir.resolve(strict=False) != expected_root:
        raise ValueError("知识资源目录必须位于项目assets/knowledge内")
    digest = _sha_bytes(data)
    suffix = Path(name).suffix.lower() or ".bin"
    safe_name = re.sub(r"[^A-Za-z0-9_.-]+", "_", Path(name).stem)[:60] or "image"
    output = assets_dir / f"{source_id}-{safe_name}-{digest[:16]}{suffix}"
    assets_dir.mkdir(parents=True, exist_ok=True)
    if output.is_symlink():
        raise ValueError("知识资源目标不能是符号链接")
    if output.exists() and output.read_bytes() != data:
        raise OSError("知识资源哈希冲突：" + output.name)
    if not output.exists():
        output.write_bytes(data)
    bitmap = suffix in {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tif", ".tiff", ".webp"}
    inferred_type = {
        ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
        ".gif": "image/gif", ".bmp": "image/bmp", ".tif": "image/tiff",
        ".tiff": "image/tiff", ".webp": "image/webp", ".svg": "image/svg+xml",
    }.get(suffix, "application/octet-stream")
    return {
        "relative_path": output.relative_to(assets_dir.parent.parent).as_posix(),
        "sha256": digest,
        "bytes": len(data),
        "content_type": content_type or inferred_type,
        "source_location": location,
        "safe_bitmap_preview": bitmap,
        "delivery": "inline_preview" if bitmap else "file_link",
    }


def extract_docx_assets(path: Path, assets_dir: Path, source_id: str) -> list[dict[str, Any]]:
    """Extract only embedded image parts; never unpack macros or OLE objects."""
    result = []
    with zipfile.ZipFile(path) as package:
        for name in sorted(package.namelist()):
            if not name.startswith("word/media/") or name.endswith("/"):
                continue
            suffix = Path(name).suffix.lower()
            if suffix not in {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tif", ".tiff", ".webp", ".emf", ".wmf", ".svg"}:
                continue
            data = package.read(name)
            result.append({
                "location": "docx/" + name,
                "asset": _write_asset(assets_dir, source_id, "docx/" + name, Path(name).name, data),
                "text": f"[嵌入图片：{Path(name).name}]",
            })
    return result


def _rels_path(slide_name: str) -> str:
    parent = str(Path(slide_name).parent)
    return f"{parent}/_rels/{Path(slide_name).name}.rels"


def _target(base: str, target: str) -> str:
    return posixpath.normpath(posixpath.join(posixpath.dirname(base), target))


def _relationship_targets(package: zipfile.ZipFile, rels_name: str) -> dict[str, tuple[str, str]]:
    if rels_name not in package.namelist():
        return {}
    root = ElementTree.fromstring(package.read(rels_name))
    source_name = rels_name.replace("/_rels/", "/").removesuffix(".rels")
    return {
        relationship.attrib.get("Id", ""): (
            relationship.attrib.get("Type", ""),
            _target(source_name, relationship.attrib.get("Target", "")),
        )
        for relationship in root
        if relationship.attrib.get("Id")
    }


def _presentation_slides(package: zipfile.ZipFile, names: set[str]) -> tuple[list[str], list[str]]:
    """Return slide targets in sldIdLst order and explicit metadata warnings."""
    warnings: list[str] = []
    def fallback() -> list[str]:
        return sorted(
            (name for name in names if re.fullmatch(r"ppt/slides/slide\d+\.xml", name)),
            key=lambda name: int(re.search(r"(\d+)", Path(name).stem).group(1)),
        )

    presentation = "ppt/presentation.xml"
    rels = "ppt/_rels/presentation.xml.rels"
    if presentation not in names or rels not in names:
        warnings.append("PPTX缺少presentation.xml或其关系文件；按文件名回退，slide顺序需复核。")
        return fallback(), warnings
    root = ElementTree.fromstring(package.read(presentation))
    rel_targets = _relationship_targets(package, rels)
    slide_ids = root.find(".//p:sldIdLst", NS)
    if slide_ids is None:
        warnings.append("PPTX缺少sldIdLst；按文件名回退，slide顺序需复核。")
        return fallback(), warnings
    slides: list[str] = []
    for slide_id in list(slide_ids):
        relationship_id = slide_id.attrib.get(f"{{{REL_NS}}}id")
        relation = rel_targets.get(relationship_id or "")
        if relation is None or relation[0] != SLIDE_REL_TYPE:
            warnings.append(f"PPTX sldId {slide_id.attrib.get('id', '')} 缺少有效 slide 关系。")
            continue
        target = relation[1]
        if target not in names:
            warnings.append(f"PPTX slide 关系目标缺失：{target}")
            continue
        slides.append(target)
    if not slides:
        warnings.append("PPTX没有可由sldIdLst读取的slide；按文件名回退，内容需复核。")
        return fallback(), warnings
    return slides, warnings


def _pptx_table(element: ElementTree.Element) -> tuple[dict[str, Any], str]:
    rows: list[list[str]] = []
    tbl = element.find(".//a:tbl", NS)
    if tbl is None:
        raise ValueError("PPTX图形中没有表格")
    trs = [x for x in list(tbl) if _local(x.tag) == "tr"]
    grid = tbl.find("a:tblGrid", NS)
    width = len([x for x in list(grid) if _local(x.tag) == "gridCol"]) if grid is not None else 0
    width = max(width, max((sum(_int_attr(cell, "gridSpan", 1) for cell in list(tr)
                            if _local(cell.tag) == "tc") for tr in trs), default=0))
    # The DrawingML table format may express a merge using gridSpan/rowSpan,
    # hMerge/vMerge continuation cells, or both.  Keep an anchor map so a
    # continuation consumes its physical cell instead of being skipped by a
    # generic "next empty column" loop.
    anchor_at: dict[tuple[int, int], tuple[int, int]] = {}
    merge_by_anchor: dict[tuple[int, int], dict[str, int]] = {}
    explicit_grid_span: set[tuple[int, int]] = set()
    warnings = False
    for row_index, tr in enumerate(trs):
        cells = [x for x in list(tr) if _local(x.tag) == "tc"]
        row = [""] * width
        column = 0
        for cell in cells:
            text = "".join(node.text or "" for node in cell.iter(f"{A}t"))
            h_merge = cell.attrib.get("hMerge") in {"1", "true"}
            v_merge = cell.attrib.get("vMerge") in {"1", "true"}
            if h_merge or v_merge:
                target = anchor_at.get((row_index, column))
                if target is None and v_merge and row_index:
                    target = anchor_at.get((row_index - 1, column))
                if target is None and h_merge:
                    # Some producers emit hMerge continuations after a
                    # gridSpan anchor, so the current column is already past
                    # the occupied range.  The last anchor is the only safe
                    # association in that case.
                    candidates = [anchor for position, anchor in anchor_at.items()
                                  if position[0] == row_index and position[1] < column]
                    target = candidates[-1] if candidates else None
                if target is None:
                    warnings = True
                else:
                    merge = merge_by_anchor.setdefault(
                        target,
                        {"row": target[0], "column": target[1], "row_span": 1, "col_span": 1},
                    )
                    redundant_grid_span = (
                        h_merge and target in explicit_grid_span
                        and column >= target[1] + merge["col_span"]
                    )
                    if h_merge and not redundant_grid_span:
                        end = column - target[1] + 1
                        if end > merge["col_span"]:
                            merge["col_span"] = end
                            anchor_at[(row_index, column)] = target
                    if v_merge:
                        end = row_index - target[0] + 1
                        if end > merge["row_span"]:
                            merge["row_span"] = end
                            anchor_at[(row_index, column)] = target
                    # A continuation after an explicit gridSpan is redundant;
                    # otherwise it occupies one physical column.
                    if not redundant_grid_span:
                        column += 1
                    continue

            while column < width and (row_index, column) in anchor_at:
                column += 1
            if column >= width:
                raise ValueError("PPTX表格存在无法定位的合并单元格")
            col_span = _int_attr(cell, "gridSpan", 1)
            row_span = _int_attr(cell, "rowSpan", 1)
            if column + col_span > width or row_index + row_span > len(trs):
                raise ValueError("PPTX表格合并范围超出表格")
            anchor = (row_index, column)
            row[column] = text
            anchor_at[anchor] = anchor
            for covered_row in range(row_index, row_index + row_span):
                for covered_column in range(column, column + col_span):
                    anchor_at.setdefault((covered_row, covered_column), anchor)
            if col_span > 1 or row_span > 1:
                merge_by_anchor[anchor] = {"row": row_index, "column": column,
                                           "row_span": row_span, "col_span": col_span}
                if col_span > 1:
                    explicit_grid_span.add(anchor)
            column += col_span
        rows.append(row)
    if not width or any(len(row) != width for row in rows):
        raise ValueError("PPTX表格行列不规则，无法安全保留结构")
    if warnings:
        raise ValueError("PPTX表格合并续单元格缺少可定位的锚点")
    merges = [merge for merge in merge_by_anchor.values()
              if merge["row_span"] > 1 or merge["col_span"] > 1]
    spec = _table_spec(rows, merges)
    return spec, table_text(spec)


def _slide_shapes(tree):
    for shape in tree:
        if _local(shape.tag) == 'grpSp':
            yield from _slide_shapes(shape)
        else:
            yield shape


def extract_pptx(path: Path, assets_dir: Path, source_id: str) -> dict[str, Any]:
    """Extract slide text, tables, notes, and image assets from OOXML only."""
    blocks: list[dict[str, Any]] = []
    warnings: list[str] = []
    review = False
    with zipfile.ZipFile(path) as package:
        names = set(package.namelist())
        slide_names, metadata_warnings = _presentation_slides(package, names)
        warnings.extend(f"{source_id}: {warning}" for warning in metadata_warnings)
        review = bool(metadata_warnings)
        for slide_no, slide_name in enumerate(slide_names, 1):
            root = ElementTree.fromstring(package.read(slide_name))
            sp_tree = root.find(".//p:spTree", NS)
            if sp_tree is not None:
                shape_no = 0
                for shape in _slide_shapes(sp_tree):
                    kind = _local(shape.tag)
                    if kind == "sp":
                        text = "".join(node.text or "" for node in shape.iter(f"{A}t"))
                        if text.strip():
                            shape_no += 1
                            blocks.append({"location": f"slide[{slide_no}]/shape[{shape_no}]",
                                           "page": slide_no, "text": text, "content_kind": "text"})
                    elif kind == "graphicFrame" and shape.find(".//a:tbl", NS) is not None:
                        try:
                            table, text = _pptx_table(shape)
                        except ValueError as exc:
                            warnings.append(f"{source_id}: slide[{slide_no}]表格结构待复核（{exc}）")
                            review = True
                            continue
                        blocks.append({"location": f"slide[{slide_no}]/table[{len([b for b in blocks if b.get('page') == slide_no and b.get('content_kind') == 'table']) + 1}]",
                                       "page": slide_no, "text": text, "content_kind": "table",
                                       "table": table})
                    elif kind == "graphicFrame":
                        warnings.append(f"{source_id}: slide[{slide_no}]含图表或其他图形对象，需视觉复核")
                        review = True
                        text = "".join(node.text or "" for node in shape.iter(f"{A}t"))
                        if text.strip():
                            shape_no += 1
                            blocks.append({"location": f"slide[{slide_no}]/shape[{shape_no}]",
                                           "page": slide_no, "text": text, "content_kind": "text"})

            rels_name = _rels_path(slide_name)
            if rels_name in names:
                relationships = _relationship_targets(package, rels_name)
                image_no = 0
                for relation_type, target in relationships.values():
                    if relation_type != PR_REL_TYPE:
                        continue
                    if target not in names:
                        warnings.append(f"{source_id}: slide[{slide_no}]图片资源缺失，需复核")
                        review = True
                        continue
                    image_no += 1
                    data = package.read(target)
                    asset = _write_asset(assets_dir, source_id, f"slide[{slide_no}]/image[{image_no}]", Path(target).name, data)
                    blocks.append({"location": f"slide[{slide_no}]/image[{image_no}]",
                                   "page": slide_no, "text": f"[嵌入图片：{Path(target).name}]",
                                   "content_kind": "asset", "asset": asset})
                    review = True
                for relation_type, target in relationships.values():
                    if relation_type != NOTES_REL_TYPE:
                        continue
                    if target not in names:
                        warnings.append(f"{source_id}: slide[{slide_no}]备注关系目标缺失，需复核")
                        review = True
                        continue
                    root = ElementTree.fromstring(package.read(target))
                    text = "".join(node.text or "" for node in root.iter(f"{A}t"))
                    if text.strip():
                        blocks.append({"location": f"slide[{slide_no}]/notes",
                                       "page": slide_no, "text": text,
                                       "content_kind": "notes", "is_note": True})
    if not slide_names:
        raise ValueError("PPTX没有可读取的幻灯片XML")
    return {"blocks": blocks, "warnings": warnings, "review": review}
