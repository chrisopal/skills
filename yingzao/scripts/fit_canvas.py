#!/usr/bin/env python3
"""Fit a Yingzao image to an exact poster canvas without stretching."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.dont_write_bytecode = True

from _runtime import ensure_runtime

ensure_runtime(("PIL",))

try:
    from PIL import Image, ImageColor, ImageOps
except ImportError as exc:  # pragma: no cover
    raise SystemExit("Missing Pillow. Run scripts/check_dependencies.py.") from exc


def parse_size(value: str) -> tuple[int, int]:
    try:
        width, height = (int(item) for item in value.lower().split("x", 1))
    except (ValueError, TypeError) as exc:
        raise argparse.ArgumentTypeError("size must be WIDTHxHEIGHT") from exc
    if width <= 0 or height <= 0:
        raise argparse.ArgumentTypeError("size values must be positive")
    return width, height


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--size", required=True, type=parse_size)
    parser.add_argument("--mode", choices=("crop", "pad"), default="crop")
    parser.add_argument("--anchor", choices=("center", "top", "bottom", "left", "right"), default="center")
    parser.add_argument("--background", default="#EDE4D2")
    return parser.parse_args()


def centering(anchor: str) -> tuple[float, float]:
    return {
        "center": (0.5, 0.5),
        "top": (0.5, 0.0),
        "bottom": (0.5, 1.0),
        "left": (0.0, 0.5),
        "right": (1.0, 0.5),
    }[anchor]


def main() -> int:
    args = parse_args()
    image = ImageOps.exif_transpose(Image.open(args.input)).convert("RGBA")
    width, height = args.size
    if args.mode == "crop":
        result = ImageOps.fit(image, (width, height), method=Image.Resampling.LANCZOS, centering=centering(args.anchor))
    else:
        scale = min(width / image.width, height / image.height)
        resized = image.resize((max(1, round(image.width * scale)), max(1, round(image.height * scale))), Image.Resampling.LANCZOS)
        background = ImageColor.getrgb(args.background)
        result = Image.new("RGBA", (width, height), background + (255,))
        cx, cy = centering(args.anchor)
        x = round((width - resized.width) * cx)
        y = round((height - resized.height) * cy)
        result.alpha_composite(resized, (x, y))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    if args.output.suffix.lower() in {".jpg", ".jpeg"}:
        result.convert("RGB").save(args.output, quality=95, subsampling=0)
    else:
        result.save(args.output)
    print(f"saved {width}x{height} mode={args.mode} anchor={args.anchor} to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
