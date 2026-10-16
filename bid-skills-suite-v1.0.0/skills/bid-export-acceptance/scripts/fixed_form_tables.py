"""Validation and serialization helpers for fixed-form tables.

The document-spec table shape remains intentionally small: headers and rows
provide the source grid, while merges and missing_cells describe the parts of
the fixed form that need structural treatment in Word.
"""

from __future__ import annotations

import html
import math
from typing import Any


_TABLE_FIELDS = {
    "headers",
    "rows",
    "header_rows",
    "widths_cm",
    "merges",
    "missing_cells",
    "page_break_before",
    "paragraphs_before",
    "paragraphs_after",
}


def _text(value: Any) -> str:
    return str(value)


def _integer(value: Any, label: str, *, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ValueError(f"{label}必须是大于等于{minimum}的整数")
    return value


def _matrix(value: Any, label: str, *, allow_empty: bool = True) -> list[list[str]]:
    if not isinstance(value, list):
        raise ValueError(f"{label}必须是数组")
    result = []
    for index, row in enumerate(value):
        if not isinstance(row, list):
            raise ValueError(f"{label}[{index}]必须是数组")
        if not row and not allow_empty:
            raise ValueError(f"{label}[{index}]不能为空")
        result.append([_text(cell) for cell in row])
    return result


def normalize_table_spec(table: dict[str, Any], *, label: str = "table") -> dict[str, Any]:
    """Validate and normalize a document-spec table into a rectangular grid."""
    if not isinstance(table, dict):
        raise ValueError(f"{label}必须是对象")
    unknown = set(table) - _TABLE_FIELDS
    if unknown:
        raise ValueError(f"{label}存在不支持的字段：{sorted(unknown)}")

    raw_headers = table.get("headers", [])
    if not isinstance(raw_headers, list):
        raise ValueError(f"{label}.headers必须是数组")
    header_rows = table.get("header_rows", 1)
    header_rows = _integer(header_rows, f"{label}.header_rows")

    # A one-dimensional headers array is the legacy one-row form.  A nested
    # array is required for two or more explicit header rows.
    if raw_headers and all(not isinstance(value, list) for value in raw_headers):
        headers = [[_text(value) for value in raw_headers]]
    else:
        headers = _matrix(raw_headers, f"{label}.headers")
    if header_rows == 0 and headers:
        raise ValueError(f"{label}.header_rows为0时headers必须为空数组")
    if header_rows and len(headers) != header_rows:
        raise ValueError(f"{label}.headers行数必须等于header_rows")

    rows = _matrix(table.get("rows", []), f"{label}.rows")
    grid = headers + rows
    if not grid:
        raise ValueError(f"{label}至少需要一行")
    columns = len(grid[0])
    if columns == 0:
        raise ValueError(f"{label}至少需要一列")
    if any(len(row) != columns for row in grid):
        raise ValueError(f"{label}表格列数不一致")

    widths = table.get("widths_cm")
    if widths is not None:
        if (not isinstance(widths, list) or len(widths) != columns
                or any(isinstance(value, bool) or not isinstance(value, (int, float))
                       or not math.isfinite(value) or value <= 0 for value in widths)):
            raise ValueError(f"{label}.widths_cm必须是与列数一致的正数数组")
        widths = list(widths)
    page_break_before = table.get("page_break_before", False)
    if not isinstance(page_break_before, bool):
        raise ValueError(f"{label}.page_break_before必须是布尔值")
    extra_paragraphs = {}
    for field in ("paragraphs_before", "paragraphs_after"):
        values = table.get(field, [])
        if not isinstance(values, list) or any(not isinstance(value, str) for value in values):
            raise ValueError(f"{label}.{field}必须是文本数组")
        extra_paragraphs[field] = list(values)

    occupied: dict[tuple[int, int], tuple[int, int]] = {}
    merges = []
    for index, merge in enumerate(table.get("merges", [])):
        merge_label = f"{label}.merges[{index}]"
        if not isinstance(merge, dict) or set(merge) != {"row", "column", "row_span", "col_span"}:
            raise ValueError(f"{merge_label}必须包含row、column、row_span、col_span")
        row = _integer(merge["row"], f"{merge_label}.row")
        column = _integer(merge["column"], f"{merge_label}.column")
        row_span = _integer(merge["row_span"], f"{merge_label}.row_span", minimum=1)
        col_span = _integer(merge["col_span"], f"{merge_label}.col_span", minimum=1)
        if row_span == 1 and col_span == 1:
            raise ValueError(f"{merge_label}至少需要跨越两个单元格")
        if row + row_span > len(grid) or column + col_span > columns:
            raise ValueError(f"{merge_label}超出表格范围")
        anchor = (row, column)
        for covered_row in range(row, row + row_span):
            for covered_column in range(column, column + col_span):
                position = (covered_row, covered_column)
                if position in occupied:
                    raise ValueError(f"{merge_label}与已有合并区域重叠")
                if position != anchor and grid[covered_row][covered_column].strip():
                    raise ValueError(f"{merge_label}覆盖了非空单元格，无法安全合并")
                occupied[position] = anchor
        merges.append({"row": row, "column": column, "row_span": row_span, "col_span": col_span})

    missing_cells = []
    seen_missing = set()
    for index, missing in enumerate(table.get("missing_cells", [])):
        missing_label = f"{label}.missing_cells[{index}]"
        if not isinstance(missing, dict) or set(missing) != {"row", "column", "label"}:
            raise ValueError(f"{missing_label}必须包含row、column、label")
        row = _integer(missing["row"], f"{missing_label}.row")
        column = _integer(missing["column"], f"{missing_label}.column")
        if row >= len(grid) or column >= columns:
            raise ValueError(f"{missing_label}超出表格范围")
        if not isinstance(missing["label"], str) or not missing["label"].strip():
            raise ValueError(f"{missing_label}.label必须是非空文本")
        position = (row, column)
        if position in seen_missing:
            raise ValueError(f"{missing_label}重复声明单元格")
        anchor = occupied.get(position, position)
        if anchor != position:
            raise ValueError(f"{missing_label}位于合并区域覆盖单元格，必须标注合并锚点")
        if grid[row][column].strip():
            raise ValueError(f"{missing_label}对应单元格已有内容")
        seen_missing.add(position)
        placeholder = f"【待补充：{missing['label']}】"
        grid[row][column] = placeholder
        missing_cells.append({"row": row, "column": column, "label": missing["label"],
                              "placeholder": placeholder})

    return {
        "headers": headers,
        "rows": rows,
        "grid": grid,
        "header_rows": header_rows,
        "widths_cm": widths,
        "merges": merges,
        "missing_cells": missing_cells,
        "page_break_before": page_break_before,
        **extra_paragraphs,
    }


def expanded_grid(table: dict[str, Any]) -> list[list[str]]:
    """Return the logical grid as Word exposes merged anchor text per cell."""
    normalized = normalize_table_spec(table) if "grid" not in table else table
    grid = [list(row) for row in normalized["grid"]]
    for merge in normalized["merges"]:
        value = grid[merge["row"]][merge["column"]]
        for row in range(merge["row"], merge["row"] + merge["row_span"]):
            for column in range(merge["column"], merge["column"] + merge["col_span"]):
                grid[row][column] = value
    return grid


def effective_grid(table: dict[str, Any]) -> list[list[str]]:
    """Public name for the logical grid used by DOCX/PDF acceptance checks."""
    return expanded_grid(table)


def table_to_markdown(table: dict[str, Any]) -> str:
    """Serialize a fixed table with safe pipe Markdown or merge-aware HTML."""
    normalized = normalize_table_spec(table)
    missing = {(item["row"], item["column"]): item for item in normalized["missing_cells"]}

    def escaped(value: str) -> str:
        return html.escape(value, quote=False).replace("\n", "<br>")

    def content(row: int, column: int) -> str:
        value = escaped(normalized["grid"][row][column])
        item = missing.get((row, column))
        return f"<mark>{escaped(item['placeholder'])}</mark>" if item else value

    def surrounded(body: str) -> str:
        before = "\n".join(escaped(value) for value in normalized["paragraphs_before"])
        after = "\n".join(escaped(value) for value in normalized["paragraphs_after"])
        return "\n".join(value for value in (before, body, after) if value)

    # Keep the common one-header, unmerged case as a readable pipe table.
    if normalized["header_rows"] == 1 and not normalized["merges"]:
        lines = [
            "| " + " | ".join(content(0, column).replace("|", "&#124;")
                                for column in range(len(normalized["grid"][0]))) + " |",
            "| " + " | ".join("---" for _ in normalized["grid"][0]) + " |",
        ]
        lines.extend(
            "| " + " | ".join(content(row, column).replace("|", "&#124;")
                                for column in range(len(normalized["grid"][row]))) + " |"
            for row in range(1, len(normalized["grid"]))
        )
        return surrounded("\n".join(lines))

    lines = []
    grid = normalized["grid"]
    lines.append("<table>")
    anchors = {(merge["row"], merge["column"]): merge for merge in normalized["merges"]}
    covered = {(row, column) for merge in normalized["merges"]
               for row in range(merge["row"], merge["row"] + merge["row_span"])
               for column in range(merge["column"], merge["column"] + merge["col_span"])
               if (row, column) != (merge["row"], merge["column"])}
    missing = {(item["row"], item["column"]): item for item in normalized["missing_cells"]}
    for row_index, row in enumerate(grid):
        tag = "th" if row_index < normalized["header_rows"] else "td"
        cells = []
        for column, value in enumerate(row):
            if (row_index, column) in covered:
                continue
            merge = anchors.get((row_index, column), {})
            attrs = []
            if merge.get("row_span", 1) > 1:
                attrs.append(f'rowspan="{merge["row_span"]}"')
            if merge.get("col_span", 1) > 1:
                attrs.append(f'colspan="{merge["col_span"]}"')
            cells.append(f"<{tag}{(' ' + ' '.join(attrs)) if attrs else ''}>{content(row_index, column)}</{tag}>")
        lines.append("<tr>" + "".join(cells) + "</tr>")
    lines.append("</table>")
    return surrounded("\n".join(lines))
