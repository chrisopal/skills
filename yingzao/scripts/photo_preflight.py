#!/usr/bin/env python3
"""Quantitative preflight for Yingzao source photographs."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any

sys.dont_write_bytecode = True

from _runtime import ensure_runtime

ensure_runtime(("PIL", "numpy", "cv2"))

try:
    import cv2
    import numpy as np
    from PIL import ExifTags, Image, ImageDraw, ImageOps
except ImportError as exc:  # pragma: no cover - exercised by dependency checker
    raise SystemExit(
        "Missing image dependencies. Run scripts/check_dependencies.py and install requirements.txt."
    ) from exc


def weighted_median(values: list[tuple[float, float]]) -> float | None:
    if not values:
        return None
    ordered = sorted(values, key=lambda item: item[0])
    halfway = sum(weight for _, weight in ordered) / 2
    cumulative = 0.0
    for value, weight in ordered:
        cumulative += weight
        if cumulative >= halfway:
            return value
    return ordered[-1][0]


def estimate_roll(gray: np.ndarray) -> dict[str, Any]:
    height, width = gray.shape
    scale = min(1.0, 1400 / max(width, height))
    work = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
    edges = cv2.Canny(work, 60, 180)
    min_length = max(40, int(min(work.shape) * 0.12))
    lines = cv2.HoughLinesP(
        edges,
        1,
        np.pi / 180,
        threshold=max(45, min_length // 2),
        minLineLength=min_length,
        maxLineGap=max(10, min_length // 5),
    )
    candidates: list[tuple[float, float]] = []
    visible_lines: list[dict[str, float]] = []
    if lines is not None:
        for item in lines[:, 0, :]:
            x1, y1, x2, y2 = map(float, item)
            dx, dy = x2 - x1, y2 - y1
            length = math.hypot(dx, dy)
            angle = math.degrees(math.atan2(dy, dx))
            while angle <= -90:
                angle += 180
            while angle > 90:
                angle -= 180
            correction_axis: float | None = None
            if abs(angle) <= 18:
                correction_axis = angle
            elif abs(abs(angle) - 90) <= 18:
                correction_axis = angle - 90 if angle > 0 else angle + 90
            if correction_axis is not None:
                candidates.append((correction_axis, length))
                if len(visible_lines) < 40:
                    visible_lines.append(
                        {
                            "x1": x1 / work.shape[1],
                            "y1": y1 / work.shape[0],
                            "x2": x2 / work.shape[1],
                            "y2": y2 / work.shape[0],
                            "axis_deviation_deg": correction_axis,
                        }
                    )
    angle = weighted_median(candidates)
    total_weight = sum(weight for _, weight in candidates)
    agreement_weight = (
        sum(weight for value, weight in candidates if angle is not None and abs(value - angle) <= 1.5)
        if total_weight
        else 0.0
    )
    confidence = agreement_weight / total_weight if total_weight else 0.0
    return {
        "angle_deg": round(angle, 3) if angle is not None else None,
        "confidence": round(confidence, 3),
        "candidate_count": len(candidates),
        "lines": visible_lines,
    }


def dominant_palette(rgb: np.ndarray, count: int = 5) -> list[dict[str, Any]]:
    sample = cv2.resize(rgb, (160, 160), interpolation=cv2.INTER_AREA).reshape(-1, 3)
    sample = np.float32(sample)
    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.4)
    _, labels, centers = cv2.kmeans(sample, count, None, criteria, 5, cv2.KMEANS_PP_CENTERS)
    counts = np.bincount(labels.flatten(), minlength=count)
    order = np.argsort(counts)[::-1]
    result = []
    for index in order:
        color = tuple(int(round(value)) for value in centers[index])
        result.append(
            {
                "hex": "#%02X%02X%02X" % color,
                "share": round(float(counts[index] / counts.sum()), 4),
            }
        )
    return result


def grid_negative_space(gray: np.ndarray, edges: np.ndarray) -> list[dict[str, Any]]:
    height, width = gray.shape
    regions: list[dict[str, Any]] = []
    for row in range(3):
        for col in range(3):
            x0, x1 = round(col * width / 3), round((col + 1) * width / 3)
            y0, y1 = round(row * height / 3), round((row + 1) * height / 3)
            crop_gray = gray[y0:y1, x0:x1]
            crop_edge = edges[y0:y1, x0:x1]
            edge_density = float(np.mean(crop_edge > 0))
            variance = min(1.0, float(np.std(crop_gray)) / 80)
            score = (1 - edge_density) * 0.7 + (1 - variance) * 0.3
            regions.append(
                {
                    "cell": f"r{row + 1}c{col + 1}",
                    "bbox_norm": [col / 3, row / 3, (col + 1) / 3, (row + 1) / 3],
                    "edge_density": round(edge_density, 4),
                    "luminance_std_norm": round(variance, 4),
                    "score": round(score, 4),
                }
            )
    return sorted(regions, key=lambda item: item["score"], reverse=True)


def attention_bbox(rgb: np.ndarray) -> list[float] | None:
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    grad_x = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
    grad_y = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
    magnitude = cv2.magnitude(grad_x, grad_y)
    hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)
    saliency = magnitude + hsv[:, :, 1].astype(np.float32) * 0.35
    threshold = np.percentile(saliency, 82)
    mask = np.uint8(saliency >= threshold) * 255
    kernel = np.ones((7, 7), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=2)
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None
    height, width = gray.shape
    contour = max(contours, key=cv2.contourArea)
    x, y, w, h = cv2.boundingRect(contour)
    if w * h < width * height * 0.01:
        return None
    return [round(x / width, 4), round(y / height, 4), round((x + w) / width, 4), round((y + h) / height, 4)]


def exif_payload(image: Image.Image) -> dict[str, Any]:
    raw = image.getexif()
    if not raw:
        return {"datetime": None, "gps": None}
    named = {ExifTags.TAGS.get(key, str(key)): value for key, value in raw.items()}
    exif_ifd: dict[int, Any] = {}
    gps_info: dict[int, Any] | Any = None
    try:
        exif_ifd = raw.get_ifd(34665)  # Exif IFD
    except (AttributeError, KeyError, TypeError):
        exif_ifd = {}
    try:
        gps_info = raw.get_ifd(34853)  # GPSInfo IFD
    except (AttributeError, KeyError, TypeError):
        gps_info = named.get("GPSInfo")
    datetime = (
        exif_ifd.get(36867)
        or exif_ifd.get(36868)
        or named.get("DateTimeOriginal")
        or named.get("DateTime")
    )
    gps = None
    if isinstance(gps_info, dict):
        gps_named = {ExifTags.GPSTAGS.get(key, str(key)): value for key, value in gps_info.items()}

        def dms(value: Any) -> float:
            return float(value[0]) + float(value[1]) / 60 + float(value[2]) / 3600

        try:
            latitude = dms(gps_named["GPSLatitude"])
            longitude = dms(gps_named["GPSLongitude"])
            latitude_ref = gps_named.get("GPSLatitudeRef")
            longitude_ref = gps_named.get("GPSLongitudeRef")
            if isinstance(latitude_ref, bytes):
                latitude_ref = latitude_ref.decode(errors="ignore")
            if isinstance(longitude_ref, bytes):
                longitude_ref = longitude_ref.decode(errors="ignore")
            if latitude_ref == "S":
                latitude *= -1
            if longitude_ref == "W":
                longitude *= -1
            gps = {"latitude": round(latitude, 6), "longitude": round(longitude, 6)}
        except (KeyError, TypeError, ValueError, ZeroDivisionError):
            gps = None
    return {"datetime": str(datetime) if datetime else None, "gps": gps}


def classify(report: dict[str, Any]) -> tuple[str, int, list[str]]:
    score = 0
    flags: list[str] = []
    min_edge = min(report["image"]["width"], report["image"]["height"])
    if min_edge >= 1200:
        score += 2
    elif min_edge >= 800:
        score += 1
    else:
        score -= 2
        flags.append("low_resolution")
    blur = report["quality"]["laplacian_variance"]
    if blur >= 120:
        score += 2
    elif blur < 45:
        score -= 2
        flags.append("possible_blur")
    if report["exposure"]["shadow_clip_share"] > 0.22:
        score -= 1
        flags.append("heavy_shadow_clipping")
    if report["exposure"]["highlight_clip_share"] > 0.16:
        score -= 1
        flags.append("heavy_highlight_clipping")
    if report["attention_bbox_norm"]:
        x0, y0, x1, y1 = report["attention_bbox_norm"]
        if (x1 - x0) * (y1 - y0) >= 0.05:
            score += 1
    roll = report["geometry"]["roll"]
    if roll["angle_deg"] is not None and abs(roll["angle_deg"]) > 1:
        if roll["confidence"] >= 0.45 and abs(roll["angle_deg"]) <= 3:
            flags.append("rectification_recommended")
        else:
            flags.append("geometry_inspection_required")
    role = "hero" if score >= 3 else ("support" if score >= 0 else "reject")
    return role, score, flags


def controlled_tags(report: dict[str, Any]) -> list[str]:
    tags = ["横向" if report["image"]["width"] > report["image"]["height"] else "竖向"]
    edge = report["quality"]["edge_density"]
    if edge > 0.16:
        tags.append("高密度")
    elif edge < 0.07:
        tags.append("低密度")
    if report["exposure"]["mean_luminance"] < 70:
        tags.append("夜景")
    if report["negative_space"][0]["score"] > 0.8:
        tags.append("留白")
    if report["exif"]["datetime"] and any(hour in report["exif"]["datetime"] for hour in (" 18:", " 19:", " 20:", " 21:")):
        tags.append("暖光")
    return list(dict.fromkeys(tags))


def build_report(path: Path) -> tuple[dict[str, Any], Image.Image]:
    source = Image.open(path)
    exif = exif_payload(source)
    image = ImageOps.exif_transpose(source).convert("RGB")
    rgb = np.array(image)
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    edges = cv2.Canny(gray, 70, 180)
    height, width = gray.shape
    report: dict[str, Any] = {
        "source": str(path.resolve()),
        "image": {
            "width": width,
            "height": height,
            "megapixels": round(width * height / 1_000_000, 3),
            "aspect_ratio": round(width / height, 5),
            "orientation": "landscape" if width > height else ("portrait" if height > width else "square"),
        },
        "exif": exif,
        "quality": {
            "laplacian_variance": round(float(cv2.Laplacian(gray, cv2.CV_64F).var()), 3),
            "edge_density": round(float(np.mean(edges > 0)), 4),
        },
        "exposure": {
            "mean_luminance": round(float(np.mean(gray)), 3),
            "shadow_clip_share": round(float(np.mean(gray <= 8)), 4),
            "highlight_clip_share": round(float(np.mean(gray >= 247)), 4),
        },
        "geometry": {"roll": estimate_roll(gray)},
        "palette": dominant_palette(rgb),
        "negative_space": grid_negative_space(gray, edges),
        "attention_bbox_norm": attention_bbox(rgb),
    }
    role, score, flags = classify(report)
    report["triage"] = {"role": role, "score": score, "flags": flags, "manual_override_allowed": True}
    report["controlled_tag_suggestions"] = controlled_tags(report)
    return report, image


def save_preflight_visuals(image: Image.Image, report: dict[str, Any], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    preview = image.copy()
    preview.thumbnail((1400, 1400), Image.Resampling.LANCZOS)
    draw = ImageDraw.Draw(preview)
    width, height = preview.size
    bbox = report.get("attention_bbox_norm")
    if bbox:
        draw.rectangle((bbox[0] * width, bbox[1] * height, bbox[2] * width, bbox[3] * height), outline="#FF4B33", width=max(2, width // 500))
    for region in report["negative_space"][:3]:
        x0, y0, x1, y1 = region["bbox_norm"]
        draw.rectangle((x0 * width, y0 * height, x1 * width, y1 * height), outline="#38D6A5", width=max(2, width // 700))
    for line in report["geometry"]["roll"]["lines"][:12]:
        draw.line((line["x1"] * width, line["y1"] * height, line["x2"] * width, line["y2"] * height), fill="#53A7FF", width=max(1, width // 900))
    preview.save(output_dir / "preflight-overlay.jpg", quality=92, subsampling=0)
    thumb = image.copy()
    thumb.thumbnail((150, 150), Image.Resampling.LANCZOS)
    thumb.save(output_dir / "thumbnail-150.png")
    ImageOps.grayscale(thumb).save(output_dir / "thumbnail-150-grayscale.png")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--json", dest="json_path", type=Path)
    parser.add_argument(
        "--visual-dir",
        "--proof-dir",
        dest="visual_dir",
        type=Path,
        help="save pre-generation overlays and thumbnails; --proof-dir is a deprecated alias",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report, image = build_report(args.input)
    payload = json.dumps(report, ensure_ascii=False, indent=2)
    if args.json_path:
        args.json_path.parent.mkdir(parents=True, exist_ok=True)
        args.json_path.write_text(payload + "\n", encoding="utf-8")
    else:
        print(payload)
    if args.visual_dir:
        save_preflight_visuals(image, report, args.visual_dir)
    role = report["triage"]["role"]
    flags = ",".join(report["triage"]["flags"]) or "none"
    print(f"preflight role={role} score={report['triage']['score']} flags={flags}")
    return 0 if role != "reject" else 2


if __name__ == "__main__":
    raise SystemExit(main())
