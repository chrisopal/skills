#!/usr/bin/env python3
"""Create a reviewable subject mask from a polygon or GrabCut rectangle."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True

from _runtime import ensure_runtime

ensure_runtime(("numpy", "cv2"))

try:
    import cv2
    import numpy as np
except ImportError as exc:  # pragma: no cover
    raise SystemExit("Missing OpenCV/numpy. Run scripts/check_dependencies.py.") from exc


def read_image(path: Path) -> np.ndarray:
    data = np.frombuffer(path.read_bytes(), dtype=np.uint8)
    image = cv2.imdecode(data, cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError(f"cannot decode image: {path}")
    return image


def write_image(path: Path, image: np.ndarray) -> None:
    suffix = path.suffix.lower() or ".png"
    if suffix not in {".png", ".jpg", ".jpeg"}:
        raise ValueError("output must be PNG or JPEG")
    extension = ".jpg" if suffix in {".jpg", ".jpeg"} else ".png"
    params = [cv2.IMWRITE_JPEG_QUALITY, 94] if extension == ".jpg" else []
    ok, encoded = cv2.imencode(extension, image, params)
    if not ok:
        raise ValueError(f"cannot encode output: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(encoded.tobytes())


def parse_polygon(value: str) -> np.ndarray:
    try:
        points = np.array(
            [[int(number) for number in pair.split(",")] for pair in value.split(";")],
            dtype=np.int32,
        )
    except ValueError as exc:
        raise argparse.ArgumentTypeError("polygon must be x,y;x,y;...") from exc
    if len(points) < 3 or points.shape[1:] != (2,):
        raise argparse.ArgumentTypeError("polygon requires at least three x,y points")
    return points


def parse_rect(value: str) -> tuple[int, int, int, int]:
    try:
        values = tuple(int(item) for item in value.split(","))
    except ValueError as exc:
        raise argparse.ArgumentTypeError("rect must be x,y,w,h") from exc
    if len(values) != 4 or values[2] <= 0 or values[3] <= 0:
        raise argparse.ArgumentTypeError("rect must be x,y,w,h with positive size")
    return values


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path, help="grayscale PNG mask; white means subject")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--polygon", type=parse_polygon, help="x,y;x,y;... in source pixels")
    group.add_argument("--rect", type=parse_rect, help="GrabCut seed rectangle x,y,w,h")
    parser.add_argument("--iterations", type=int, default=5, help="GrabCut iterations for --rect")
    parser.add_argument("--expand", type=int, default=0, help="positive dilates, negative erodes, in pixels")
    parser.add_argument("--feather", type=int, default=0, help="Gaussian feather radius in pixels")
    parser.add_argument(
        "--preview",
        "--proof",
        dest="preview",
        type=Path,
        help="save a pre-generation red overlay; --proof is a deprecated alias",
    )
    parser.add_argument("--report", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.output.suffix.lower() != ".png":
        raise SystemExit("subject mask output must use a .png extension")
    image = read_image(args.input)
    height, width = image.shape[:2]
    if args.polygon is not None:
        points = args.polygon
        if np.any(points[:, 0] < 0) or np.any(points[:, 1] < 0) or np.any(points[:, 0] >= width) or np.any(points[:, 1] >= height):
            raise SystemExit("polygon contains points outside the image")
        mask = np.zeros((height, width), np.uint8)
        cv2.fillPoly(mask, [points], 255)
        method = "polygon"
        seed = points.tolist()
    else:
        x, y, rect_width, rect_height = args.rect
        if x < 0 or y < 0 or x + rect_width > width or y + rect_height > height:
            raise SystemExit("GrabCut rectangle exceeds image bounds")
        labels = np.zeros((height, width), np.uint8)
        background = np.zeros((1, 65), np.float64)
        foreground = np.zeros((1, 65), np.float64)
        cv2.grabCut(
            image,
            labels,
            (x, y, rect_width, rect_height),
            background,
            foreground,
            max(1, args.iterations),
            cv2.GC_INIT_WITH_RECT,
        )
        mask = np.where((labels == cv2.GC_FGD) | (labels == cv2.GC_PR_FGD), 255, 0).astype(np.uint8)
        method = "grabcut-rect"
        seed = list(args.rect)

    if args.expand:
        radius = abs(args.expand)
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (radius * 2 + 1, radius * 2 + 1))
        operation = cv2.dilate if args.expand > 0 else cv2.erode
        mask = operation(mask, kernel)
    if args.feather:
        kernel_size = args.feather * 2 + 1
        mask = cv2.GaussianBlur(mask, (kernel_size, kernel_size), 0)

    coverage = float(np.mean(mask > 127))
    if coverage < 0.01 or coverage > 0.95:
        raise SystemExit(f"mask coverage {coverage:.3f} is implausible; adjust the seed")
    write_image(args.output, mask)

    if args.preview:
        overlay = image.copy()
        red = np.zeros_like(image)
        red[:, :, 2] = 255
        alpha = (mask.astype(np.float32) / 255 * 0.42)[:, :, None]
        overlay = np.uint8(np.clip(overlay * (1 - alpha) + red * alpha, 0, 255))
        contours, _ = cv2.findContours(np.uint8(mask >= 128) * 255, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cv2.drawContours(overlay, contours, -1, (255, 255, 255), 2)
        write_image(args.preview, overlay)

    report = {
        "input": str(args.input.resolve()),
        "mask": str(args.output.resolve()),
        "canvas": [width, height],
        "method": method,
        "seed": seed,
        "expand_px": args.expand,
        "feather_px": args.feather,
        "subject_coverage": round(coverage, 5),
        "manual_inspection_required": True,
    }
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
