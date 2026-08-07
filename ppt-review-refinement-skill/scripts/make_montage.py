#!/usr/bin/env python3
"""Create a labeled contact sheet from rendered slide PNGs."""

from __future__ import annotations

import argparse
import math
import re
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from common import ensure_dir


def numeric_key(path: Path) -> int:
    match = re.search(r"(\d+)(?=\.png$)", path.name)
    return int(match.group(1)) if match else 10**9


def create_montage(
    image_dir: str | Path,
    output_path: str | Path,
    *,
    columns: int = 4,
    thumb_width: int = 400,
    label_height: int = 34,
    gap: int = 16,
) -> Path:
    image_dir = Path(image_dir)
    output_path = Path(output_path)
    ensure_dir(output_path.parent)
    paths = sorted(image_dir.glob("slide-*.png"), key=numeric_key)
    if not paths:
        raise FileNotFoundError(f"No slide-*.png files found in {image_dir}")

    with Image.open(paths[0]) as first:
        ratio = first.height / first.width
    thumb_height = max(1, round(thumb_width * ratio))
    rows = math.ceil(len(paths) / columns)
    canvas_w = gap + columns * (thumb_width + gap)
    canvas_h = gap + rows * (thumb_height + label_height + gap)
    canvas = Image.new("RGB", (canvas_w, canvas_h), "white")
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.load_default()

    for idx, path in enumerate(paths):
        row, col = divmod(idx, columns)
        x = gap + col * (thumb_width + gap)
        y = gap + row * (thumb_height + label_height + gap)
        with Image.open(path) as image:
            thumb = image.convert("RGB")
            thumb.thumbnail((thumb_width, thumb_height), Image.Resampling.LANCZOS)
            px = x + (thumb_width - thumb.width) // 2
            py = y + (thumb_height - thumb.height) // 2
            canvas.paste(thumb, (px, py))
        draw.rectangle((x, y, x + thumb_width, y + thumb_height), outline="gray", width=1)
        label = f"Slide {numeric_key(path)}"
        draw.text((x + 6, y + thumb_height + 8), label, fill="black", font=font)

    canvas.save(output_path, quality=92)
    return output_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a slide montage/contact sheet.")
    parser.add_argument("image_dir")
    parser.add_argument("--out", required=True)
    parser.add_argument("--columns", type=int, default=4)
    parser.add_argument("--thumb-width", type=int, default=400)
    args = parser.parse_args()
    try:
        path = create_montage(
            args.image_dir,
            args.out,
            columns=args.columns,
            thumb_width=args.thumb_width,
        )
        print(f"Wrote {path}")
        return 0
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
