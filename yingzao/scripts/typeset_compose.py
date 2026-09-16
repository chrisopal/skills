#!/usr/bin/env python3
"""Render and gate a real-font typeset guide or layered final text."""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from pathlib import Path
from typing import Any

sys.dont_write_bytecode = True

from _runtime import ensure_runtime

ensure_runtime(("PIL", "fontTools"))

try:
    from PIL import Image, ImageColor, ImageDraw, ImageFont, ImageOps
    from fontTools.ttLib import TTFont
except ImportError as exc:  # pragma: no cover
    raise SystemExit("Missing Pillow or fontTools. Run scripts/check_dependencies.py.") from exc


ANCHORS = {
    "lt": (0.0, 0.0), "mt": (0.5, 0.0), "rt": (1.0, 0.0),
    "lm": (0.0, 0.5), "mm": (0.5, 0.5), "rm": (1.0, 0.5),
    "lb": (0.0, 1.0), "mb": (0.5, 1.0), "rb": (1.0, 1.0),
}
MARKER_RE = re.compile(r"^[A-Z][A-Z0-9_-]{0,11}$")


def semantic_marker(item: dict[str, Any], element_id: str, errors: list[str]) -> tuple[str | None, str | None]:
    """Read a compact ASCII guide marker that can be referenced verbatim in the model prompt."""
    marker = str(item.get("guide_marker", "")).strip()
    label = str(item.get("guide_label", "")).strip()
    if not marker:
        if label:
            errors.append(f"{element_id}: guide_label requires guide_marker")
        return None, None
    if not MARKER_RE.fullmatch(marker):
        errors.append(f"{element_id}: invalid guide_marker {marker!r}")
    if not label:
        errors.append(f"{element_id}: guide_marker requires guide_label")
    elif not label.isascii() or not label.isprintable():
        errors.append(f"{element_id}: guide_label must be printable ASCII for reliable guide rendering")
    return marker, label or None


def guide_marker_summary(
    primitive_reports: list[dict[str, Any]], layer_reports: list[dict[str, Any]]
) -> tuple[list[dict[str, Any]], list[str]]:
    markers: dict[str, dict[str, Any]] = {}
    errors: list[str] = []
    for kind, reports in (("primitive", primitive_reports), ("text", layer_reports)):
        for item in reports:
            marker = item.get("guide_marker")
            if not marker:
                continue
            label = item.get("guide_label")
            current = markers.setdefault(marker, {"id": marker, "label": label, "elements": []})
            if current["label"] != label:
                errors.append(
                    f"guide marker {marker!r} has conflicting labels {current['label']!r} and {label!r}"
                )
            current["elements"].append({"kind": kind, "id": item["id"]})
    return [markers[key] for key in sorted(markers)], errors


def render_guide_marker_badges(
    canvas: tuple[int, int], primitive_reports: list[dict[str, Any]], layer_reports: list[dict[str, Any]]
) -> Image.Image:
    """Render small spatial IDs last so their correspondence survives the guide image."""
    overlay = Image.new("RGBA", canvas, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    font_size = max(13, min(28, round(canvas[0] * 0.016)))
    try:
        font = ImageFont.load_default(size=font_size)
    except TypeError:  # Pillow < 10.1
        font = ImageFont.load_default()
    items: list[tuple[dict[str, Any], list[int]]] = []
    for report in primitive_reports:
        if not report.get("guide_marker"):
            continue
        if report.get("bbox"):
            bbox = list(report["bbox"])
        else:
            xs = [point[0] for point in report.get("points", [])]
            ys = [point[1] for point in report.get("points", [])]
            if not xs or not ys:
                continue
            bbox = [min(xs), min(ys), max(xs), max(ys)]
        items.append((report, bbox))
    for report in layer_reports:
        if report.get("guide_marker"):
            items.append((report, list(report["layout_bbox"])))
    for report, bbox in items:
        text = f"[{report['guide_marker']}] {report['guide_label']}"
        text_bbox = draw.textbbox((0, 0), text, font=font)
        width = text_bbox[2] - text_bbox[0] + 12
        height = text_bbox[3] - text_bbox[1] + 8
        left, top, right, bottom = map(int, bbox)
        if top - height - 4 >= 0:
            x, y = left, top - height - 4
        elif right + width + 4 <= canvas[0]:
            x, y = right + 4, top
        elif bottom + height + 4 <= canvas[1]:
            x, y = left, bottom + 4
        else:
            x, y = left + 4, top + 4
        x = max(0, min(canvas[0] - width, x))
        y = max(0, min(canvas[1] - height, y))
        draw.rectangle([x, y, x + width, y + height], fill=(24, 24, 24, 224))
        draw.text((x + 6 - text_bbox[0], y + 4 - text_bbox[1]), text, font=font, fill=(255, 255, 255, 255))
    return overlay


def position(value: float | int, extent: int) -> float:
    number = float(value)
    return number * extent if 0 <= number <= 1 else number


def color_with_opacity(value: str, opacity: int) -> tuple[int, int, int, int]:
    rgb = ImageColor.getrgb(value)
    return rgb + (max(0, min(255, opacity)),)


def text_dimensions(text: str, font: ImageFont.FreeTypeFont, tracking: float, line_height: float, orientation: str) -> tuple[int, int, list[tuple[str, float, float]]]:
    probe = Image.new("L", (4, 4))
    draw = ImageDraw.Draw(probe)
    glyphs: list[tuple[str, float, float]] = []
    if orientation == "vertical":
        y = 0.0
        max_width = 0.0
        for char in text.replace("\n", ""):
            box = draw.textbbox((0, 0), char, font=font)
            width, height = box[2] - box[0], box[3] - box[1]
            glyphs.append((char, 0.0, y))
            max_width = max(max_width, width)
            y += line_height if line_height > 0 else height + tracking
        return max(1, round(max_width)), max(1, round(y - (line_height if glyphs else 0) + font.size)), glyphs

    lines = text.splitlines() or [""]
    y = 0.0
    max_width = 0.0
    for line in lines:
        x = 0.0
        for char in line:
            box = draw.textbbox((0, 0), char, font=font)
            width = box[2] - box[0]
            glyphs.append((char, x, y))
            x += width + tracking
        if line:
            x -= tracking
        max_width = max(max_width, x)
        y += line_height
    return max(1, round(max_width)), max(1, round(y)), glyphs


def boxes_intersect(left: list[int], right: list[int]) -> bool:
    return not (left[2] <= right[0] or right[2] <= left[0] or left[3] <= right[1] or right[3] <= left[1])


def expand_bbox(bbox: list[int], padding: int) -> list[int]:
    return [bbox[0] - padding, bbox[1] - padding, bbox[2] + padding, bbox[3] + padding]


def point_in_rect(point: tuple[float, float], rect: list[int]) -> bool:
    return rect[0] <= point[0] <= rect[2] and rect[1] <= point[1] <= rect[3]


def orientation(a: tuple[float, float], b: tuple[float, float], c: tuple[float, float]) -> float:
    return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])


def point_on_segment(point: tuple[float, float], start: tuple[float, float], end: tuple[float, float]) -> bool:
    if abs(orientation(start, end, point)) > 1e-7:
        return False
    return (
        min(start[0], end[0]) - 1e-7 <= point[0] <= max(start[0], end[0]) + 1e-7
        and min(start[1], end[1]) - 1e-7 <= point[1] <= max(start[1], end[1]) + 1e-7
    )


def segments_intersect(
    a: tuple[float, float], b: tuple[float, float], c: tuple[float, float], d: tuple[float, float]
) -> bool:
    ab_c = orientation(a, b, c)
    ab_d = orientation(a, b, d)
    cd_a = orientation(c, d, a)
    cd_b = orientation(c, d, b)
    if ((ab_c > 0 and ab_d < 0) or (ab_c < 0 and ab_d > 0)) and (
        (cd_a > 0 and cd_b < 0) or (cd_a < 0 and cd_b > 0)
    ):
        return True
    return any(
        (
            abs(value) <= 1e-7 and point_on_segment(point, start, end)
            for value, point, start, end in (
                (ab_c, c, a, b),
                (ab_d, d, a, b),
                (cd_a, a, c, d),
                (cd_b, b, c, d),
            )
        )
    )


def segment_intersects_rect(start: tuple[float, float], end: tuple[float, float], rect: list[int]) -> bool:
    if point_in_rect(start, rect) or point_in_rect(end, rect):
        return True
    left, top, right, bottom = rect
    edges = [
        ((left, top), (right, top)),
        ((right, top), (right, bottom)),
        ((right, bottom), (left, bottom)),
        ((left, bottom), (left, top)),
    ]
    return any(segments_intersect(start, end, edge_start, edge_end) for edge_start, edge_end in edges)


def point_in_polygon(point: tuple[float, float], points: list[tuple[float, float]]) -> bool:
    inside = False
    previous = points[-1]
    for current in points:
        if point_on_segment(point, previous, current):
            return True
        if (current[1] > point[1]) != (previous[1] > point[1]):
            crossing_x = (previous[0] - current[0]) * (point[1] - current[1]) / (previous[1] - current[1]) + current[0]
            if point[0] < crossing_x:
                inside = not inside
        previous = current
    return inside


def primitive_intersects_rect(primitive: dict[str, Any], rect: list[int]) -> bool:
    kind = primitive["type"]
    half_width = max(0, int(primitive.get("width_px", 1)) // 2)
    padded = expand_bbox(rect, half_width)
    if kind == "rect":
        bbox = primitive["bbox"]
        return not (bbox[2] < padded[0] or padded[2] < bbox[0] or bbox[3] < padded[1] or padded[3] < bbox[1])
    if kind == "ellipse":
        left, top, right, bottom = primitive["bbox"]
        center_x, center_y = (left + right) / 2, (top + bottom) / 2
        radius_x, radius_y = max(0.5, (right - left) / 2), max(0.5, (bottom - top) / 2)
        closest_x = max(padded[0], min(center_x, padded[2]))
        closest_y = max(padded[1], min(center_y, padded[3]))
        return ((closest_x - center_x) / radius_x) ** 2 + ((closest_y - center_y) / radius_y) ** 2 <= 1
    points = [(float(point[0]), float(point[1])) for point in primitive["points"]]
    if kind == "line":
        return any(segment_intersects_rect(points[index - 1], points[index], padded) for index in range(1, len(points)))
    if kind == "polygon":
        edges_hit = any(
            segment_intersects_rect(points[index - 1], points[index], padded) for index in range(len(points))
        )
        if edges_hit:
            return True
        corners = [
            (padded[0], padded[1]),
            (padded[2], padded[1]),
            (padded[2], padded[3]),
            (padded[0], padded[3]),
        ]
        return point_in_polygon(((padded[0] + padded[2]) / 2, (padded[1] + padded[3]) / 2), points) or any(
            point_in_polygon(corner, points) for corner in corners
        )
    raise ValueError(f"unsupported primitive type {kind!r}")


def is_display_layer(layer: dict[str, Any]) -> bool:
    role = str(layer.get("role", "")).strip().lower().replace("_", "-")
    return role in {"display", "display-title", "title", "structural-title"}


def required_codepoints(text: str) -> list[int]:
    """Return unique printable codepoints that the selected font must cover."""
    seen: set[int] = set()
    codepoints: list[int] = []
    for char in text:
        if char.isspace() or unicodedata.category(char) in {"Cc", "Cf"}:
            continue
        codepoint = ord(char)
        if codepoint not in seen:
            seen.add(codepoint)
            codepoints.append(codepoint)
    return codepoints


def validate_font_coverage(font_path: Path, font_index: int, text: str) -> dict[str, Any]:
    """Verify cmap coverage instead of mistaking .notdef boxes for valid ink."""
    font = TTFont(str(font_path), fontNumber=font_index, lazy=True)
    try:
        cmap = font.getBestCmap() or {}
        required = required_codepoints(text)
        missing = [codepoint for codepoint in required if codepoint not in cmap]
    finally:
        font.close()
    return {
        "checked_codepoints": [f"U+{codepoint:04X}" for codepoint in required],
        "missing_codepoints": [f"U+{codepoint:04X}" for codepoint in missing],
        "missing_characters": [chr(codepoint) for codepoint in missing],
        "passed": not missing,
    }


def canvas_size(spec: dict[str, Any]) -> tuple[int, int]:
    value = spec.get("canvas")
    if not isinstance(value, list) or len(value) != 2:
        raise ValueError("blank art requires spec.canvas [width, height]")
    width, height = int(value[0]), int(value[1])
    if width <= 0 or height <= 0:
        raise ValueError("spec.canvas dimensions must be positive")
    return width, height


def draw_reinterpret_scaffold(
    canvas: tuple[int, int],
    glyphs: list[tuple[str, float, float]],
    *,
    x: float,
    y: float,
    width: int,
    line_height: float,
    orientation: str,
    font_path: Path,
    font_index: int,
    font_size: int,
) -> Image.Image:
    """Draw spatial character slots without anchoring the model to a stock display face."""
    overlay = Image.new("RGBA", canvas, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    label_size = max(16, round(font_size * 0.22))
    label_font = ImageFont.truetype(str(font_path), size=label_size, index=font_index)
    for index, (char, offset_x, offset_y) in enumerate(glyphs):
        if orientation == "vertical":
            slot_left = x
            slot_top = y + offset_y
            slot_right = x + width
            slot_bottom = slot_top + line_height
        else:
            slot_left = x + offset_x
            slot_top = y + offset_y
            next_offset = glyphs[index + 1][1] if index + 1 < len(glyphs) and glyphs[index + 1][2] == offset_y else None
            slot_right = x + (next_offset if next_offset is not None else width)
            slot_bottom = slot_top + line_height
        box = [round(slot_left), round(slot_top), round(slot_right), round(slot_bottom)]
        draw.rectangle(box, fill=(128, 128, 128, 14), outline=(128, 128, 128, 92), width=2)
        label_bbox = draw.textbbox((0, 0), char, font=label_font)
        label_width = label_bbox[2] - label_bbox[0]
        label_height = label_bbox[3] - label_bbox[1]
        label_x = slot_left + (slot_right - slot_left - label_width) / 2 - label_bbox[0]
        label_y = slot_top + (slot_bottom - slot_top - label_height) / 2 - label_bbox[1]
        draw.text((label_x, label_y), char, font=label_font, fill=(96, 96, 96, 118))
    return overlay


def draw_primitives(
    base: Image.Image, spec: dict[str, Any]
) -> tuple[list[dict[str, Any]], list[str], Image.Image]:
    background_overlay = Image.new("RGBA", base.size, (0, 0, 0, 0))
    subject_overlay = Image.new("RGBA", base.size, (0, 0, 0, 0))
    reports: list[dict[str, Any]] = []
    errors: list[str] = []
    for index, item in enumerate(spec.get("primitives", [])):
        primitive_id = str(item.get("id", f"primitive-{index + 1}"))
        guide_marker, guide_label = semantic_marker(item, primitive_id, errors)
        kind = item.get("type")
        primitive_layer = str(item.get("layer", "background"))
        role = str(item.get("role", "")).strip().lower().replace("_", "-")
        if primitive_layer not in {"background", "subject_front"}:
            errors.append(f"{primitive_id}: layer must be background or subject_front")
            continue
        if primitive_layer == "subject_front" and role != "subject-footprint":
            errors.append(f"{primitive_id}: subject_front primitives require role=subject-footprint")
            continue
        overlay = subject_overlay if primitive_layer == "subject_front" else background_overlay
        draw = ImageDraw.Draw(overlay)
        fill = color_with_opacity(item.get("fill", "#000000"), int(item.get("opacity", 255)))
        stroke = color_with_opacity(item.get("stroke", item.get("fill", "#000000")), int(item.get("opacity", 255)))
        width = max(1, int(item.get("width_px", 1)))
        try:
            if kind in {"rect", "ellipse"}:
                bbox = item.get("bbox")
                if not isinstance(bbox, list) or len(bbox) != 4:
                    raise ValueError("bbox must be [left, top, right, bottom]")
                resolved = [
                    position(bbox[0], base.width),
                    position(bbox[1], base.height),
                    position(bbox[2], base.width),
                    position(bbox[3], base.height),
                ]
                if kind == "rect":
                    draw.rectangle(resolved, fill=fill, outline=stroke if item.get("stroke") else None, width=width)
                else:
                    draw.ellipse(resolved, fill=fill, outline=stroke if item.get("stroke") else None, width=width)
                reports.append(
                    {
                        "id": primitive_id,
                        "type": kind,
                        "bbox": [round(value) for value in resolved],
                        "width_px": width,
                        "layer": primitive_layer,
                        "role": role or None,
                        "guide_marker": guide_marker,
                        "guide_label": guide_label,
                    }
                )
            elif kind in {"polygon", "line"}:
                points = item.get("points")
                if not isinstance(points, list) or len(points) < (3 if kind == "polygon" else 2):
                    raise ValueError(f"{kind} requires enough [x, y] points")
                resolved_points = [
                    (position(point[0], base.width), position(point[1], base.height)) for point in points
                ]
                if any(not isinstance(point, list) or len(point) != 2 for point in points):
                    raise ValueError("points must contain [x, y] pairs")
                if kind == "polygon":
                    draw.polygon(resolved_points, fill=fill, outline=stroke if item.get("stroke") else None)
                else:
                    draw.line(resolved_points, fill=stroke, width=width, joint="curve")
                reports.append(
                    {
                        "id": primitive_id,
                        "type": kind,
                        "points": [[round(x), round(y)] for x, y in resolved_points],
                        "width_px": width,
                        "layer": primitive_layer,
                        "role": role or None,
                        "guide_marker": guide_marker,
                        "guide_label": guide_label,
                    }
                )
            else:
                raise ValueError(f"unsupported primitive type {kind!r}")
        except (IndexError, TypeError, ValueError) as exc:
            errors.append(f"{primitive_id}: {exc}")
    base.alpha_composite(background_overlay)
    return reports, errors, subject_overlay


def alignment_value(layer: dict[str, Any], axis: str, basis: str) -> float:
    if axis == "baseline":
        if layer["orientation"] != "horizontal":
            raise ValueError("baseline alignment only supports horizontal text")
        return float(layer["baseline_y_first"])
    bbox_key = "ink_bbox" if basis == "ink" else "layout_bbox"
    bbox = layer[bbox_key]
    if axis == "left":
        return float(bbox[0])
    if axis == "right":
        return float(bbox[2])
    if axis == "top":
        return float(bbox[1])
    if axis == "bottom":
        return float(bbox[3])
    if axis == "center_x":
        return (float(bbox[0]) + float(bbox[2])) / 2
    if axis == "center_y":
        return (float(bbox[1]) + float(bbox[3])) / 2
    raise ValueError(f"unsupported alignment axis {axis!r}")


def validate_alignment_groups(
    spec: dict[str, Any], layer_reports: list[dict[str, Any]], canvas_width: int
) -> tuple[list[dict[str, Any]], list[str]]:
    by_id = {item["id"]: item for item in layer_reports}
    reports: list[dict[str, Any]] = []
    errors: list[str] = []
    default_tolerance = max(1.0, canvas_width * 0.0025)
    for index, group in enumerate(spec.get("alignment_groups", [])):
        group_id = str(group.get("id", f"alignment-{index + 1}"))
        members = list(group.get("members", []))
        axis = str(group.get("axis", "left"))
        basis = str(group.get("basis", "ink"))
        tolerance = float(group.get("tolerance_px", default_tolerance))
        display_group = str(group.get("role", "")).strip().lower() in {"display", "display-title"} or any(
            is_display_layer(by_id[member]) for member in members if member in by_id
        )
        layout_reason = str(group.get("layout_reason", "")).strip()
        if basis not in {"ink", "layout"}:
            errors.append(f"{group_id}: basis must be ink or layout")
            continue
        if display_group and basis == "layout" and not layout_reason:
            errors.append(
                f"{group_id}: display-title alignment must use basis=ink; basis=layout requires layout_reason"
            )
            continue
        if len(members) < 2:
            errors.append(f"{group_id}: requires at least two members")
            continue
        missing = [member for member in members if member not in by_id]
        if missing:
            errors.append(f"{group_id}: unknown members {', '.join(missing)}")
            continue
        try:
            values = {member: alignment_value(by_id[member], axis, basis) for member in members}
        except ValueError as exc:
            errors.append(f"{group_id}: {exc}")
            continue
        spread = max(values.values()) - min(values.values())
        passed = spread <= tolerance
        reports.append(
            {
                "id": group_id,
                "members": members,
                "axis": axis,
                "basis": basis,
                "display_group": display_group,
                "layout_reason": layout_reason or None,
                "values_px": {key: round(value, 3) for key, value in values.items()},
                "spread_px": round(spread, 3),
                "tolerance_px": round(tolerance, 3),
                "passed": passed,
            }
        )
        if not passed:
            errors.append(
                f"{group_id}: {basis} {axis} spread {spread:.3f}px exceeds tolerance {tolerance:.3f}px"
            )
    return reports, errors


def validate_primitive_text_exclusions(
    spec: dict[str, Any], primitive_reports: list[dict[str, Any]], layer_reports: list[dict[str, Any]]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[str]]:
    primitive_by_id = {item["id"]: item for item in primitive_reports}
    layer_by_id = {item["id"]: item for item in layer_reports}
    primitive_ids = set(primitive_by_id)
    layer_ids = set(layer_by_id)
    contracts: list[dict[str, Any]] = []
    contract_by_pair: dict[tuple[str, str], dict[str, Any]] = {}
    errors: list[str] = []
    for index, item in enumerate(spec.get("overlap_contracts", [])):
        contract_id = str(item.get("id", f"overlap-{index + 1}"))
        primitive_id = str(item.get("primitive", ""))
        text_id = str(item.get("text", ""))
        reason = str(item.get("reason", "")).strip()
        z_order = str(item.get("z_order", "")).strip()
        pair = (primitive_id, text_id)
        contract = {
            "id": contract_id,
            "primitive": primitive_id,
            "text": text_id,
            "reason": reason,
            "z_order": z_order or None,
            "used": False,
        }
        contracts.append(contract)
        if not primitive_id or primitive_id not in primitive_ids:
            errors.append(f"{contract_id}: unknown primitive {primitive_id!r}")
            continue
        if not text_id or text_id not in layer_ids:
            errors.append(f"{contract_id}: unknown text layer {text_id!r}")
            continue
        if not reason:
            errors.append(f"{contract_id}: overlap contract requires a non-empty reason")
            continue
        if z_order == "text-behind-subject":
            primitive = primitive_by_id[primitive_id]
            text_layer = layer_by_id[text_id]
            if primitive.get("layer") != "subject_front" or primitive.get("role") != "subject-footprint":
                errors.append(
                    f"{contract_id}: text-behind-subject requires a subject_front primitive "
                    "with role=subject-footprint"
                )
                continue
            if text_layer.get("layer") != "behind_subject":
                errors.append(f"{contract_id}: text-behind-subject requires the text layer to use layer=behind_subject")
                continue
        if pair in contract_by_pair:
            errors.append(f"{contract_id}: duplicate overlap contract for {primitive_id} + {text_id}")
            continue
        contract_by_pair[pair] = contract

    intersections: list[dict[str, Any]] = []
    for primitive in primitive_reports:
        for layer in layer_reports:
            exclusion_bbox = layer["primitive_exclusion_bbox"]
            if not primitive_intersects_rect(primitive, exclusion_bbox):
                continue
            pair = (primitive["id"], layer["id"])
            contract = contract_by_pair.get(pair)
            allowed = contract is not None
            if contract is not None:
                contract["used"] = True
            intersections.append(
                {
                    "primitive": primitive["id"],
                    "text": layer["id"],
                    "text_exclusion_bbox": exclusion_bbox,
                    "allowed": allowed,
                    "contract_id": contract["id"] if contract else None,
                }
            )
            if not allowed:
                errors.append(
                    f"{primitive['id']}: intersects text exclusion zone {layer['id']}; "
                    "reroute the primitive or register an overlap_contract"
                )
    return intersections, contracts, errors


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("art", help="base image path, or literal 'blank' for an opaque spec-defined canvas")
    parser.add_argument("spec", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--subject-mask", type=Path)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--validate-only", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    spec = json.loads(args.spec.read_text(encoding="utf-8"))
    guide_mode = args.art == "blank" or spec.get("mode") == "typeset-guide"
    if args.art == "blank":
        try:
            width, height = canvas_size(spec)
        except ValueError as exc:
            raise SystemExit(str(exc)) from exc
        background = color_with_opacity(spec.get("background", "#FFFFFF"), 255)
        base = Image.new("RGBA", (width, height), background)
        art_label = "blank"
    else:
        art_path = Path(args.art)
        base = ImageOps.exif_transpose(Image.open(art_path)).convert("RGBA")
        art_label = str(art_path.resolve())
    if spec.get("canvas") and list(base.size) != list(spec["canvas"]):
        raise SystemExit(f"spec canvas {spec['canvas']} does not match art {list(base.size)}")

    primitive_reports, primitive_errors, subject_overlay = draw_primitives(base, spec)

    behind = Image.new("RGBA", base.size, (0, 0, 0, 0))
    front = Image.new("RGBA", base.size, (0, 0, 0, 0))
    layer_reports: list[dict[str, Any]] = []
    errors: list[str] = list(primitive_errors)
    occupied: list[dict[str, Any]] = []
    needs_mask = False

    for index, item in enumerate(spec.get("layers", [])):
        layer_id = str(item.get("id", f"layer-{index + 1}"))
        guide_marker, guide_label = semantic_marker(item, layer_id, errors)
        text = str(item.get("text", ""))
        font_path = Path(str(item.get("font", ""))).expanduser()
        if not text:
            errors.append(f"{layer_id}: empty text")
            continue
        if not font_path.is_file():
            errors.append(f"{layer_id}: font not found: {font_path}")
            continue
        try:
            font_index = int(item.get("font_index", 0))
            font = ImageFont.truetype(str(font_path), size=int(item["size_px"]), index=font_index)
        except (OSError, KeyError, ValueError) as exc:
            errors.append(f"{layer_id}: cannot load font: {exc}")
            continue
        try:
            coverage = validate_font_coverage(font_path, font_index, text)
        except Exception as exc:  # fontTools exposes format-specific exceptions
            errors.append(f"{layer_id}: cannot inspect font cmap: {exc}")
            continue
        if not coverage["passed"]:
            missing = " ".join(
                f"{char}({codepoint})"
                for char, codepoint in zip(
                    coverage["missing_characters"], coverage["missing_codepoints"]
                )
            )
            errors.append(f"{layer_id}: font does not cover required characters: {missing}")
        tracking = float(item.get("tracking_px", 0))
        line_height = float(item.get("line_height_px", round(font.size * 1.2)))
        orientation = item.get("orientation", "horizontal")
        if orientation not in {"horizontal", "vertical"}:
            errors.append(f"{layer_id}: invalid orientation {orientation}")
            continue
        vertical_order = item.get("vertical_order")
        if orientation == "vertical" and vertical_order != "top-to-bottom":
            errors.append(
                f"{layer_id}: vertical text requires vertical_order=top-to-bottom"
            )
        if orientation == "horizontal" and vertical_order is not None:
            errors.append(f"{layer_id}: vertical_order is only valid for vertical text")
        width, height, glyphs = text_dimensions(text, font, tracking, line_height, orientation)
        anchor = item.get("anchor", "lt")
        if anchor not in ANCHORS:
            errors.append(f"{layer_id}: invalid anchor {anchor}")
            continue
        anchor_x, anchor_y = ANCHORS[anchor]
        x = position(item.get("x", 0), base.width) - width * anchor_x
        y = position(item.get("y", 0), base.height) - height * anchor_y
        layout_bbox = [round(x), round(y), round(x + width), round(y + height)]

        z_layer = item.get("layer", "front")
        if z_layer not in {"front", "behind_subject"}:
            errors.append(f"{layer_id}: invalid layer {z_layer}")
            continue
        if z_layer == "behind_subject":
            needs_mask = True
        target = behind if z_layer == "behind_subject" else front
        measurement_overlay = Image.new("RGBA", base.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(measurement_overlay)
        fill = color_with_opacity(item.get("fill", "#111111"), int(item.get("opacity", 255)))
        stroke_width = int(item.get("stroke_width", 0))
        stroke_fill = color_with_opacity(item.get("stroke_fill", item.get("fill", "#111111")), int(item.get("opacity", 255)))
        glyph_ink_boxes: list[tuple[int, int, int, int]] = []
        for char, offset_x, offset_y in glyphs:
            point = (x + offset_x, y + offset_y)
            glyph_ink_boxes.append(draw.textbbox(point, char, font=font, stroke_width=stroke_width))
            draw.text(point, char, font=font, fill=fill, stroke_width=stroke_width, stroke_fill=stroke_fill)
        if not glyph_ink_boxes:
            errors.append(f"{layer_id}: font produced no visible ink")
            continue
        unclipped_ink_bbox = [
            min(box[0] for box in glyph_ink_boxes),
            min(box[1] for box in glyph_ink_boxes),
            max(box[2] for box in glyph_ink_boxes),
            max(box[3] for box in glyph_ink_boxes),
        ]
        rendered_bbox = measurement_overlay.getchannel("A").getbbox()
        if rendered_bbox is None:
            errors.append(f"{layer_id}: rendered alpha is empty")
            continue
        ink_bbox = list(rendered_bbox)
        safe_padding = max(0, int(item.get("collision_padding_px", 0)))
        collision_bbox = expand_bbox(ink_bbox, safe_padding)
        role = str(item.get("role", "")).strip()
        display_layer = is_display_layer({"id": layer_id, "role": role})
        glyph_design_mode = str(item.get("glyph_design_mode", "")).strip().lower()
        guide_render = str(item.get("guide_render", "text")).strip().lower()
        if guide_mode and display_layer:
            if glyph_design_mode not in {"literal", "reinterpret"}:
                errors.append(f"{layer_id}: display layers require glyph_design_mode=literal or reinterpret")
            if glyph_design_mode == "reinterpret" and guide_render != "scaffold":
                errors.append(
                    f"{layer_id}: reinterpret display layers require guide_render=scaffold "
                    "so a stock font silhouette cannot become the strongest visual anchor"
                )
            if glyph_design_mode == "literal" and guide_render != "text":
                errors.append(f"{layer_id}: literal display layers require guide_render=text")
        minimum_exclusion_padding = round(font.size * (0.25 if display_layer else 0.5))
        primitive_exclusion_padding = max(
            safe_padding,
            int(item.get("primitive_exclusion_padding_px", minimum_exclusion_padding)),
            minimum_exclusion_padding,
        )
        primitive_exclusion_bbox = expand_bbox(ink_bbox, primitive_exclusion_padding)
        if unclipped_ink_bbox[0] < 0 or unclipped_ink_bbox[1] < 0 or unclipped_ink_bbox[2] > base.width or unclipped_ink_bbox[3] > base.height:
            errors.append(f"{layer_id}: visible ink overflow {unclipped_ink_bbox} outside {list(base.size)}")
        allow_overlap = bool(item.get("allow_overlap", False))
        for previous in occupied:
            if boxes_intersect(collision_bbox, previous["collision_bbox"]) and not (allow_overlap or previous["allow_overlap"]):
                errors.append(f"{layer_id}: visible-ink collision with {previous['id']}")
        occupied.append(
            {
                "id": layer_id,
                "collision_bbox": collision_bbox,
                "allow_overlap": allow_overlap,
            }
        )
        if guide_mode and display_layer and glyph_design_mode == "reinterpret" and guide_render == "scaffold":
            guide_overlay = draw_reinterpret_scaffold(
                base.size,
                glyphs,
                x=x,
                y=y,
                width=width,
                line_height=line_height,
                orientation=orientation,
                font_path=font_path,
                font_index=font_index,
                font_size=font.size,
            )
            target.alpha_composite(guide_overlay)
        else:
            target.alpha_composite(measurement_overlay)
        if orientation == "horizontal":
            line_count = len(text.splitlines() or [""])
            baseline_ys = [round(y + font.getmetrics()[0] + line_index * line_height, 3) for line_index in range(line_count)]
        else:
            line_count = 1
            baseline_ys = []
        layer_reports.append(
            {
                "id": layer_id,
                "text": text,
                "role": role or None,
                "display_layer": display_layer,
                "glyph_design_mode": glyph_design_mode or None,
                "guide_render": guide_render,
                "font": str(font_path.resolve()),
                "font_index": font_index,
                "font_loaded": True,
                "font_coverage": coverage,
                "fallback": not coverage["passed"],
                "layout_bbox": layout_bbox,
                "ink_bbox": ink_bbox,
                "unclipped_ink_bbox_estimate": unclipped_ink_bbox,
                "collision_bbox": collision_bbox,
                "collision_padding_px": safe_padding,
                "primitive_exclusion_bbox": primitive_exclusion_bbox,
                "primitive_exclusion_padding_px": primitive_exclusion_padding,
                "layer": z_layer,
                "orientation": orientation,
                "vertical_order": vertical_order if orientation == "vertical" else None,
                "line_count": line_count,
                "allow_overlap": allow_overlap,
                "baseline_y": baseline_ys[0] if baseline_ys else None,
                "baseline_y_first": baseline_ys[0] if baseline_ys else None,
                "baseline_ys": baseline_ys,
                "guide_marker": guide_marker,
                "guide_label": guide_label,
            }
        )

    has_subject_footprint = any(
        item.get("layer") == "subject_front" and item.get("role") == "subject-footprint"
        for item in primitive_reports
    )
    if needs_mask and args.subject_mask is None and not has_subject_footprint:
        errors.append("behind_subject layers require --subject-mask or a subject_front subject-footprint primitive")

    if guide_mode and len(layer_reports) >= 2 and not spec.get("alignment_groups"):
        errors.append("typeset-guide with two or more text layers requires alignment_groups")

    alignment_reports, alignment_errors = validate_alignment_groups(spec, layer_reports, base.width)
    errors.extend(alignment_errors)
    primitive_text_intersections, overlap_contracts, primitive_text_errors = validate_primitive_text_exclusions(
        spec, primitive_reports, layer_reports
    )
    errors.extend(primitive_text_errors)
    guide_markers, marker_errors = guide_marker_summary(primitive_reports, layer_reports)
    errors.extend(marker_errors)

    report = {
        "art": art_label,
        "spec": str(args.spec.resolve()),
        "canvas": list(base.size),
        "mode": "typeset-guide" if guide_mode else spec.get("mode", "layered-final-type"),
        "primitives": primitive_reports,
        "layers": layer_reports,
        "alignment_groups": alignment_reports,
        "primitive_text_intersections": primitive_text_intersections,
        "overlap_contracts": overlap_contracts,
        "guide_markers": guide_markers,
        "errors": errors,
        "passed": not errors,
    }
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    if args.validate_only:
        print(f"valid: {len(layer_reports)} measured text layers")
        return 0

    result = Image.alpha_composite(base, behind)
    if needs_mask:
        if args.subject_mask is not None:
            mask = ImageOps.exif_transpose(Image.open(args.subject_mask)).convert("L")
            if mask.size != base.size:
                raise SystemExit(f"subject mask {list(mask.size)} does not match art {list(base.size)}")
            result = Image.composite(base, result, mask)
        result = Image.alpha_composite(result, subject_overlay)
    result = Image.alpha_composite(result, front)
    if guide_mode and guide_markers:
        result = Image.alpha_composite(
            result, render_guide_marker_badges(base.size, primitive_reports, layer_reports)
        )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    if args.output.suffix.lower() in {".jpg", ".jpeg"}:
        result.convert("RGB").save(args.output, quality=95, subsampling=0)
    else:
        result.save(args.output)
    print(f"saved {len(layer_reports)} measured text layers to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
