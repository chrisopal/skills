#!/usr/bin/env python3
"""Deterministically rotate, perspective-rectify, and crop a source image."""

from __future__ import annotations

import sys

# rectify imports a sibling analysis function; never leave bytecode inside the Skill.
sys.dont_write_bytecode = True

from _runtime import ensure_runtime

ensure_runtime(("PIL", "numpy", "cv2"))

import argparse
import json
from pathlib import Path

try:
    import cv2
    import numpy as np
except ImportError as exc:  # pragma: no cover
    raise SystemExit("Missing OpenCV/numpy. Run scripts/check_dependencies.py.") from exc

from photo_preflight import estimate_roll


AUTO_ROLL_NOOP_DEG = 0.3


def read_image(path: Path) -> np.ndarray:
    data = np.frombuffer(path.read_bytes(), dtype=np.uint8)
    image = cv2.imdecode(data, cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError(f"cannot decode image: {path}")
    return image


def write_image(path: Path, image: np.ndarray) -> None:
    suffix = path.suffix.lower() or ".png"
    extension = ".jpg" if suffix in {".jpg", ".jpeg"} else suffix
    params = [cv2.IMWRITE_JPEG_QUALITY, 95] if extension == ".jpg" else []
    ok, encoded = cv2.imencode(extension, image, params)
    if not ok:
        raise ValueError(f"cannot encode output: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(encoded.tobytes())


def rotate_bound(image: np.ndarray, angle: float) -> tuple[np.ndarray, np.ndarray]:
    height, width = image.shape[:2]
    center = (width / 2, height / 2)
    matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
    cos, sin = abs(matrix[0, 0]), abs(matrix[0, 1])
    new_width = int(round(height * sin + width * cos))
    new_height = int(round(height * cos + width * sin))
    matrix[0, 2] += new_width / 2 - center[0]
    matrix[1, 2] += new_height / 2 - center[1]
    result = cv2.warpAffine(image, matrix, (new_width, new_height), flags=cv2.INTER_CUBIC, borderValue=(0, 0, 0))
    mask = cv2.warpAffine(np.full((height, width), 255, np.uint8), matrix, (new_width, new_height), flags=cv2.INTER_NEAREST, borderValue=0)
    return result, mask


def order_quad(points: np.ndarray) -> np.ndarray:
    ordered = np.zeros((4, 2), dtype=np.float32)
    sums = points.sum(axis=1)
    diffs = np.diff(points, axis=1).reshape(-1)
    ordered[0] = points[np.argmin(sums)]
    ordered[2] = points[np.argmax(sums)]
    ordered[1] = points[np.argmin(diffs)]
    ordered[3] = points[np.argmax(diffs)]
    return ordered


def perspective(image: np.ndarray, points: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    source = order_quad(points)
    tl, tr, br, bl = source
    width = max(np.linalg.norm(br - bl), np.linalg.norm(tr - tl))
    height = max(np.linalg.norm(tr - br), np.linalg.norm(tl - bl))
    target = np.array([[0, 0], [width - 1, 0], [width - 1, height - 1], [0, height - 1]], dtype=np.float32)
    matrix = cv2.getPerspectiveTransform(source, target)
    size = (max(1, int(round(width))), max(1, int(round(height))))
    result = cv2.warpPerspective(image, matrix, size, flags=cv2.INTER_CUBIC)
    return result, np.full(result.shape[:2], 255, np.uint8)


def crop_valid(image: np.ndarray, mask: np.ndarray) -> tuple[np.ndarray, list[int]]:
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return image, [0, 0, image.shape[1], image.shape[0]]
    x, y, width, height = cv2.boundingRect(max(contours, key=cv2.contourArea))
    return image[y : y + height, x : x + width], [x, y, width, height]


def parse_quad(value: str) -> np.ndarray:
    parts = value.split(";")
    if len(parts) != 4:
        raise argparse.ArgumentTypeError("--quad requires x,y;x,y;x,y;x,y")
    try:
        return np.array([[float(number) for number in part.split(",")] for part in parts], dtype=np.float32)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("quad coordinates must be numbers") from exc


def parse_crop(value: str) -> str | list[int]:
    if value == "auto":
        return value
    try:
        values = [int(item) for item in value.split(",")]
    except ValueError as exc:
        raise argparse.ArgumentTypeError("--crop must be auto or x,y,w,h") from exc
    if len(values) != 4 or values[2] <= 0 or values[3] <= 0:
        raise argparse.ArgumentTypeError("--crop must be auto or x,y,w,h")
    return values


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--auto-roll", action="store_true")
    parser.add_argument("--rotate", type=float, help="explicit counter-clockwise-positive correction in degrees")
    parser.add_argument("--quad", type=parse_quad)
    parser.add_argument("--crop", type=parse_crop, default="auto")
    parser.add_argument("--report", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.auto_roll and args.rotate is not None:
        raise SystemExit("use either --auto-roll or --rotate")
    image = read_image(args.input)
    original_size = [image.shape[1], image.shape[0]]
    mask = np.full(image.shape[:2], 255, np.uint8)
    roll_report = None
    auto_roll_noop = False
    applied_rotation = 0.0
    if args.auto_roll:
        roll_report = estimate_roll(cv2.cvtColor(image, cv2.COLOR_BGR2GRAY))
        estimate = roll_report["angle_deg"]
        if estimate is None:
            raise SystemExit("auto roll found no reliable architectural axes; inspect and use --rotate explicitly")
        if abs(estimate) <= AUTO_ROLL_NOOP_DEG:
            auto_roll_noop = True
            applied_rotation = 0.0
        elif roll_report["confidence"] < 0.45:
            raise SystemExit(
                f"auto roll confidence {roll_report['confidence']} is ambiguous; inspect and use --rotate explicitly"
            )
        elif abs(estimate) > 3:
            raise SystemExit(
                f"auto roll estimate {estimate}° may be perspective or real geometry; inspect and use --rotate explicitly"
            )
        else:
            applied_rotation = float(estimate)
    elif args.rotate is not None:
        applied_rotation = float(args.rotate)
    if abs(applied_rotation) > 0.01:
        image, mask = rotate_bound(image, applied_rotation)
    if args.quad is not None:
        image, mask = perspective(image, args.quad)
    crop_box = [0, 0, image.shape[1], image.shape[0]]
    if args.crop == "auto":
        image, crop_box = crop_valid(image, mask)
    elif isinstance(args.crop, list):
        x, y, width, height = args.crop
        if x < 0 or y < 0 or x + width > image.shape[1] or y + height > image.shape[0]:
            raise SystemExit("explicit crop exceeds image bounds")
        image = image[y : y + height, x : x + width]
        crop_box = args.crop
    residual_roll = estimate_roll(cv2.cvtColor(image, cv2.COLOR_BGR2GRAY))
    write_image(args.output, image)
    report = {
        "input": str(args.input.resolve()),
        "output": str(args.output.resolve()),
        "original_size": original_size,
        "output_size": [image.shape[1], image.shape[0]],
        "auto_roll": roll_report,
        "auto_roll_noop": auto_roll_noop,
        "auto_roll_noop_threshold_deg": AUTO_ROLL_NOOP_DEG,
        "applied_rotation_deg": round(applied_rotation, 4),
        "residual_roll": residual_roll,
        "perspective_quad": args.quad.tolist() if args.quad is not None else None,
        "crop_box_xywh": crop_box,
    }
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "output": report["output"],
                "output_size": report["output_size"],
                "applied_rotation_deg": report["applied_rotation_deg"],
                "residual_roll_deg": residual_roll["angle_deg"],
                "residual_confidence": residual_roll["confidence"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
