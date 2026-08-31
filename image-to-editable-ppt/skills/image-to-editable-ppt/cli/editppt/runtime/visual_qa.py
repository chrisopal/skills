#!/usr/bin/env python3
"""Deterministic source-versus-preview visual QA for editable PPT pages."""

import argparse
import json
import re
from pathlib import Path

import numpy as np
from PIL import Image


HEX_COLOR = re.compile(r"^#?([0-9a-fA-F]{6})$")


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path, payload):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def resolve_under(page_dir, value, default):
    page_dir = Path(page_dir).resolve()
    path = Path(value or default).expanduser()
    if not path.is_absolute():
        path = page_dir / path
    path = path.resolve()
    try:
        path.relative_to(page_dir)
    except ValueError as exc:
        raise ValueError(f"path must stay inside page directory: {path}") from exc
    return path


def parse_color(value):
    match = HEX_COLOR.match(str(value or "").strip())
    if not match:
        return None
    raw = match.group(1)
    return np.array([int(raw[index : index + 2], 16) for index in (0, 2, 4)], dtype=np.float64)


def object_id(item, prefix, index):
    return str(item.get("id") or f"{prefix}_{index}")


def box_intersection(a, b):
    ax, ay, aw, ah = (float(value) for value in a)
    bx, by, bw, bh = (float(value) for value in b)
    left = max(ax, bx)
    top = max(ay, by)
    right = min(ax + aw, bx + bw)
    bottom = min(ay + ah, by + bh)
    if right <= left or bottom <= top:
        return None
    return [left, top, right - left, bottom - top]


def box_area(box):
    return max(0.0, float(box[2])) * max(0.0, float(box[3]))


def alpha_ink_box(page_dir, item):
    box = item.get("box_px")
    if not box or len(box) != 4:
        return None
    path = resolve_under(page_dir, item.get("path"), "")
    if not path.exists():
        return list(box)
    with Image.open(path) as image:
        rgba = image.convert("RGBA")
        alpha_box = rgba.getchannel("A").point(lambda value: 255 if value >= 16 else 0).getbbox()
        source_width, source_height = rgba.size
    if not alpha_box or not source_width or not source_height:
        return None
    x, y, width, height = (float(value) for value in box)
    left = x + alpha_box[0] * width / source_width
    top = y + alpha_box[1] * height / source_height
    ink_width = (alpha_box[2] - alpha_box[0]) * width / source_width
    ink_height = (alpha_box[3] - alpha_box[1]) * height / source_height
    return [left, top, ink_width, ink_height]


def allowed_overlap_keys(config):
    allowed = set()
    violations = []
    for index, entry in enumerate(config.get("allowed_overlaps", [])):
        if not isinstance(entry, dict):
            violations.append(
                {
                    "field": f"visual_qa.allowed_overlaps[{index}]",
                    "reason": "allowed overlap entries must be objects with an exact pair and a reason",
                }
            )
            continue
        kind = str(entry.get("kind") or "image-text")
        reason = str(entry.get("reason") or "").strip()
        if kind == "image-text":
            first = entry.get("image_id")
            second = entry.get("text_id")
        elif kind == "text-text":
            pair = sorted([str(entry.get("text_id_a") or ""), str(entry.get("text_id_b") or "")])
            first, second = pair
        else:
            first = second = None
        if not first or not second or not reason:
            violations.append(
                {
                    "field": f"visual_qa.allowed_overlaps[{index}]",
                    "reason": "allowed overlap entries require exact object ids and a non-empty reason",
                }
            )
            continue
        allowed.add((kind, str(first), str(second)))
    return allowed, violations


def overlap_checks(page_dir, manifest, config):
    allowed, contract_violations = allowed_overlap_keys(config)
    violations = []
    image_threshold = float(config.get("image_text_overlap_ratio", 0.08))
    text_threshold = float(config.get("text_text_overlap_ratio", 0.15))
    texts = manifest.get("text_boxes", [])

    for image_index, image in enumerate(manifest.get("images", [])):
        ink_box = alpha_ink_box(page_dir, image)
        if not ink_box:
            continue
        image_id = object_id(image, "image", image_index)
        for text_index, text in enumerate(texts):
            text_box = text.get("box_px")
            if not text_box:
                continue
            text_id = object_id(text, "text", text_index)
            if ("image-text", image_id, text_id) in allowed:
                continue
            intersection = box_intersection(ink_box, text_box)
            if not intersection:
                continue
            ratio = box_area(intersection) / max(1.0, min(box_area(ink_box), box_area(text_box)))
            if ratio >= image_threshold:
                violations.append(
                    {
                        "kind": "image-text",
                        "image_id": image_id,
                        "text_id": text_id,
                        "image_ink_box_px": [round(value, 2) for value in ink_box],
                        "text_box_px": text_box,
                        "intersection_px": [round(value, 2) for value in intersection],
                        "overlap_ratio": round(ratio, 4),
                        "reason": "foreground image ink overlaps editable text beyond the allowed ratio",
                    }
                )

    for first_index, first in enumerate(texts):
        first_box = first.get("box_px")
        if not first_box:
            continue
        first_id = object_id(first, "text", first_index)
        for second_index in range(first_index + 1, len(texts)):
            second = texts[second_index]
            second_box = second.get("box_px")
            if not second_box:
                continue
            second_id = object_id(second, "text", second_index)
            pair = sorted([first_id, second_id])
            if ("text-text", pair[0], pair[1]) in allowed:
                continue
            intersection = box_intersection(first_box, second_box)
            if not intersection:
                continue
            ratio = box_area(intersection) / max(1.0, min(box_area(first_box), box_area(second_box)))
            if ratio >= text_threshold:
                violations.append(
                    {
                        "kind": "text-text",
                        "text_id_a": first_id,
                        "text_id_b": second_id,
                        "intersection_px": [round(value, 2) for value in intersection],
                        "overlap_ratio": round(ratio, 4),
                        "reason": "editable text boxes overlap beyond the allowed ratio",
                    }
                )

    return violations, contract_violations


def exemption_ids(config, key):
    ids = set()
    violations = []
    for index, entry in enumerate(config.get(key, [])):
        if not isinstance(entry, dict) or not entry.get("shape_id") or not str(entry.get("reason") or "").strip():
            violations.append(
                {
                    "field": f"visual_qa.{key}[{index}]",
                    "reason": "visual QA exemptions require shape_id and a non-empty reason",
                }
            )
            continue
        ids.add(str(entry["shape_id"]))
    return ids, violations


def color_checks(source_array, manifest, config):
    source_height, source_width = source_array.shape[:2]
    slide_area = max(1, source_width * source_height)
    threshold = float(config.get("shape_color_distance", 65.0))
    max_area_ratio = float(config.get("max_color_check_area_ratio", 0.30))
    exempt, contract_violations = exemption_ids(config, "color_exemptions")
    mismatches = []

    for index, shape in enumerate(manifest.get("shapes", [])):
        shape_id = object_id(shape, "shape", index)
        if shape_id in exempt:
            continue
        box = shape.get("box_px")
        fill = parse_color(shape.get("fill"))
        if not box or fill is None or len(box) != 4:
            continue
        x, y, width, height = (int(round(float(value))) for value in box)
        if width <= 2 or height <= 2 or width * height / slide_area > max_area_ratio:
            continue
        padding = max(1, min(6, int(min(width, height) * 0.12)))
        x0 = max(0, x + padding)
        y0 = max(0, y + padding)
        x1 = min(source_width, x + width - padding)
        y1 = min(source_height, y + height - padding)
        if x1 <= x0 or y1 <= y0:
            continue
        pixels = source_array[y0:y1, x0:x1].reshape(-1, 3).astype(np.float64)
        source_median = np.median(pixels, axis=0)
        distance = float(np.linalg.norm(source_median - fill))
        if distance >= threshold:
            mismatches.append(
                {
                    "shape_id": shape_id,
                    "shape_index": index,
                    "box_px": box,
                    "manifest_fill": "#" + "".join(f"{int(value):02X}" for value in fill),
                    "source_median_rgb": [int(round(value)) for value in source_median],
                    "color_distance": round(distance, 2),
                    "threshold": threshold,
                    "reason": "solid shape fill differs materially from the source region median",
                }
            )

    return mismatches, contract_violations


def longest_run(indices):
    if not len(indices):
        return None
    best = current_start = previous = int(indices[0])
    best_start = best_end = best
    for raw in indices[1:]:
        value = int(raw)
        if value != previous + 1:
            if previous - current_start > best_end - best_start:
                best_start, best_end = current_start, previous
            current_start = value
        previous = value
    if previous - current_start > best_end - best_start:
        best_start, best_end = current_start, previous
    return best_start, best_end + 1


def infer_fill_span(source_array, shape, check):
    box = shape.get("box_px")
    fill = parse_color(shape.get("fill"))
    if not box or fill is None:
        return None
    source_height, source_width = source_array.shape[:2]
    x, y, width, height = (int(round(float(value))) for value in box)
    margin = check.get("search_margin_px", 24)
    if isinstance(margin, (list, tuple)) and len(margin) == 2:
        margin_x, margin_y = (int(value) for value in margin)
    else:
        margin_x = margin_y = int(margin)
    tolerance = float(check.get("color_distance", 80.0))

    row_y0 = max(0, y - margin_y)
    row_y1 = min(source_height, y + height + margin_y)
    row_x0 = max(0, x)
    row_x1 = min(source_width, x + width)
    if row_y1 <= row_y0 or row_x1 <= row_x0:
        return None
    row_medians = np.median(source_array[row_y0:row_y1, row_x0:row_x1].astype(np.float64), axis=1)
    row_distances = np.linalg.norm(row_medians - fill, axis=1)
    row_run = longest_run(np.where(row_distances <= tolerance)[0])
    if not row_run:
        return None
    inferred_y0 = row_y0 + row_run[0]
    inferred_y1 = row_y0 + row_run[1]

    col_x0 = max(0, x - margin_x)
    col_x1 = min(source_width, x + width + margin_x)
    col_medians = np.median(
        source_array[inferred_y0:inferred_y1, col_x0:col_x1].astype(np.float64), axis=0
    )
    col_distances = np.linalg.norm(col_medians - fill, axis=1)
    col_run = longest_run(np.where(col_distances <= tolerance)[0])
    if not col_run:
        return None
    inferred_x0 = col_x0 + col_run[0]
    inferred_x1 = col_x0 + col_run[1]
    return [inferred_x0, inferred_y0, inferred_x1 - inferred_x0, inferred_y1 - inferred_y0]


def geometry_checks(source_array, manifest, config):
    shapes = manifest.get("shapes", [])
    checks = list(config.get("geometry_checks", []))
    auto_vertical = bool(config.get("auto_check_tall_structures", True))
    source_height, source_width = source_array.shape[:2]
    slide_area = max(1, source_width * source_height)
    explicitly_checked = set()
    contract_violations = []

    for index, check in enumerate(checks):
        if not isinstance(check, dict):
            contract_violations.append(
                {
                    "field": f"visual_qa.geometry_checks[{index}]",
                    "reason": "geometry checks must be objects",
                }
            )
            continue
        shape_id = check.get("shape_id")
        shape_index = check.get("shape_index")
        if shape_id is not None:
            matches = [i for i, shape in enumerate(shapes) if str(shape.get("id") or "") == str(shape_id)]
            if not matches:
                contract_violations.append(
                    {
                        "field": f"visual_qa.geometry_checks[{index}].shape_id",
                        "reason": f"geometry check references unknown shape id {shape_id}",
                    }
                )
                continue
            shape_index = matches[0]
        if shape_index is None or int(shape_index) < 0 or int(shape_index) >= len(shapes):
            contract_violations.append(
                {
                    "field": f"visual_qa.geometry_checks[{index}]",
                    "reason": "geometry check requires a valid shape_id or shape_index",
                }
            )
            continue
        shape_index = int(shape_index)
        explicitly_checked.add(shape_index)
        check["_shape_index"] = shape_index

    if auto_vertical:
        for index, shape in enumerate(shapes):
            if index in explicitly_checked:
                continue
            box = shape.get("box_px")
            if not box or parse_color(shape.get("fill")) is None:
                continue
            _, _, width, height = (float(value) for value in box)
            area_ratio = width * height / slide_area
            if width > 0 and height / width >= 4.0 and 0.01 <= area_ratio <= 0.10:
                checks.append(
                    {
                        "_shape_index": index,
                        "mode": "source-fill-span",
                        "search_margin_px": [max(8, int(width * 0.15)), max(24, int(height * 0.18))],
                        "box_tolerance_px": max(6, int(width * 0.08)),
                        "auto": True,
                    }
                )

    mismatches = []
    for check in checks:
        if "_shape_index" not in check:
            continue
        shape_index = int(check["_shape_index"])
        shape = shapes[shape_index]
        if str(check.get("mode") or "source-fill-span") != "source-fill-span":
            contract_violations.append(
                {
                    "field": f"visual_qa.geometry_checks[{shape_index}].mode",
                    "reason": "supported geometry mode is source-fill-span",
                }
            )
            continue
        inferred = infer_fill_span(source_array, shape, check)
        shape_id = object_id(shape, "shape", shape_index)
        if not inferred:
            mismatches.append(
                {
                    "shape_id": shape_id,
                    "shape_index": shape_index,
                    "box_px": shape.get("box_px"),
                    "reason": "could not find a contiguous source fill span for the structural shape",
                }
            )
            continue
        expected = [float(value) for value in shape.get("box_px")]
        tolerance = float(check.get("box_tolerance_px", 8.0))
        edge_deltas = [
            abs(expected[0] - inferred[0]),
            abs(expected[1] - inferred[1]),
            abs(expected[0] + expected[2] - inferred[0] - inferred[2]),
            abs(expected[1] + expected[3] - inferred[1] - inferred[3]),
        ]
        if max(edge_deltas) > tolerance:
            mismatches.append(
                {
                    "shape_id": shape_id,
                    "shape_index": shape_index,
                    "box_px": shape.get("box_px"),
                    "inferred_source_box_px": inferred,
                    "edge_deltas_px": [round(value, 2) for value in edge_deltas],
                    "tolerance_px": tolerance,
                    "auto": bool(check.get("auto")),
                    "reason": "structural shape bounds differ from the contiguous source fill span",
                }
            )

    return mismatches, contract_violations


def diff_metrics(source_image, preview_image, config):
    if preview_image.size != source_image.size:
        preview_image = preview_image.resize(source_image.size, Image.Resampling.LANCZOS)
    source = np.asarray(source_image.convert("RGB"), dtype=np.int16)
    preview = np.asarray(preview_image.convert("RGB"), dtype=np.int16)
    difference = np.abs(source - preview)
    max_channel = difference.max(axis=2)
    metrics = {
        "mean_absolute_error": round(float(difference.mean()), 4),
        "p95_absolute_error": round(float(np.percentile(difference, 95)), 4),
        "changed_pixel_ratio_20": round(float((max_channel > 20).mean()), 6),
        "changed_pixel_ratio_40": round(float((max_channel > 40).mean()), 6),
    }
    violations = []
    if config.get("max_mean_absolute_error") is not None:
        threshold = float(config["max_mean_absolute_error"])
        if metrics["mean_absolute_error"] > threshold:
            violations.append(
                {
                    "metric": "mean_absolute_error",
                    "value": metrics["mean_absolute_error"],
                    "threshold": threshold,
                    "reason": "source-versus-preview mean difference exceeds the configured limit",
                }
            )
    if config.get("max_changed_pixel_ratio_40") is not None:
        threshold = float(config["max_changed_pixel_ratio_40"])
        if metrics["changed_pixel_ratio_40"] > threshold:
            violations.append(
                {
                    "metric": "changed_pixel_ratio_40",
                    "value": metrics["changed_pixel_ratio_40"],
                    "threshold": threshold,
                    "reason": "source-versus-preview changed-pixel ratio exceeds the configured limit",
                }
            )
    return metrics, violations, difference.astype(np.uint8)


def write_diff_image(source_image, difference, output_path):
    intensity = difference.max(axis=2)
    heat = np.zeros((*intensity.shape, 3), dtype=np.uint8)
    heat[..., 0] = intensity
    heat[..., 1] = intensity // 5
    heat[..., 2] = intensity // 8
    source = np.asarray(source_image.convert("RGB"), dtype=np.uint8)
    overlay = (source.astype(np.float32) * 0.45 + heat.astype(np.float32) * 0.85).clip(0, 255).astype(np.uint8)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(overlay).save(output_path)


def run_visual_qa(page_dir, manifest_path, source_path, preview_path, report_path, diff_path):
    manifest = read_json(manifest_path)
    config = manifest.get("visual_qa") if isinstance(manifest.get("visual_qa"), dict) else {}
    source_image = Image.open(source_path).convert("RGB")
    preview_image = Image.open(preview_path).convert("RGB")
    source_array = np.asarray(source_image)

    overlap_violations, overlap_contract = overlap_checks(page_dir, manifest, config)
    color_mismatches, color_contract = color_checks(source_array, manifest, config)
    geometry_mismatches, geometry_contract = geometry_checks(source_array, manifest, config)
    metrics, diff_violations, difference = diff_metrics(source_image, preview_image, config)
    write_diff_image(source_image, difference, diff_path)

    contract_violations = overlap_contract + color_contract + geometry_contract
    report = {
        "schema_version": 1,
        "source": str(source_path),
        "preview": str(preview_path),
        "diff": str(diff_path),
        "diff_metrics": metrics,
        "overlap_violations": overlap_violations,
        "shape_color_mismatches": color_mismatches,
        "geometry_mismatches": geometry_mismatches,
        "diff_threshold_violations": diff_violations,
        "contract_violations": contract_violations,
        "passed": not any(
            (
                overlap_violations,
                color_mismatches,
                geometry_mismatches,
                diff_violations,
                contract_violations,
            )
        ),
    }
    write_json(report_path, report)
    return report


def main():
    parser = argparse.ArgumentParser(description="Run deterministic source-versus-preview visual QA for one page.")
    parser.add_argument("page_dir")
    parser.add_argument("--manifest", default="manifest.json")
    parser.add_argument("--source", default="source.png")
    parser.add_argument("--preview", default="preview.png")
    parser.add_argument("--report", default="visual-qa.json")
    parser.add_argument("--diff", default="visual-diff.png")
    args = parser.parse_args()

    page_dir = Path(args.page_dir).expanduser().resolve()
    manifest_path = resolve_under(page_dir, args.manifest, "manifest.json")
    source_path = resolve_under(page_dir, args.source, "source.png")
    preview_path = resolve_under(page_dir, args.preview, "preview.png")
    report_path = resolve_under(page_dir, args.report, "visual-qa.json")
    diff_path = resolve_under(page_dir, args.diff, "visual-diff.png")
    try:
        report = run_visual_qa(page_dir, manifest_path, source_path, preview_path, report_path, diff_path)
    except Exception as exc:
        report = {
            "schema_version": 1,
            "source": str(source_path),
            "preview": str(preview_path),
            "diff": str(diff_path),
            "contract_violations": [{"field": "visual_qa", "reason": str(exc)}],
            "passed": False,
        }
        write_json(report_path, report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    raise SystemExit(0 if report.get("passed") is True else 1)


if __name__ == "__main__":
    main()
