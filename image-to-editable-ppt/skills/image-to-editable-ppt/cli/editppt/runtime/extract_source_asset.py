#!/usr/bin/env python3
"""Deterministically separate a foreground asset from a uniform source region."""

import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image


def parse_box(value):
    parts = [int(item.strip()) for item in str(value).split(",")]
    if len(parts) != 4 or parts[2] <= 0 or parts[3] <= 0:
        raise argparse.ArgumentTypeError("box must be X,Y,W,H with positive width and height")
    return parts


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


def relative_or_absolute(page_dir, path):
    try:
        return path.relative_to(page_dir).as_posix()
    except ValueError:
        return str(path)


def border_pixels(array):
    if array.shape[0] < 2 or array.shape[1] < 2:
        return array.reshape(-1, 3)
    return np.concatenate(
        [
            array[0, :, :],
            array[-1, :, :],
            array[1:-1, 0, :],
            array[1:-1, -1, :],
        ],
        axis=0,
    )


def extract_asset(source_image, box, max_background_variation, low_threshold, feather, padding):
    source_width, source_height = source_image.size
    x, y, width, height = box
    if x < 0 or y < 0 or x + width > source_width or y + height > source_height:
        raise ValueError(f"box {box} falls outside source size {source_image.size}")

    region = source_image.crop((x, y, x + width, y + height)).convert("RGB")
    rgb = np.asarray(region, dtype=np.float64)
    border = border_pixels(rgb)
    background = np.median(border, axis=0)
    border_distances = np.linalg.norm(border - background, axis=1)
    background_variation = float(np.percentile(border_distances, 90))
    if background_variation > max_background_variation:
        raise ValueError(
            "source region border is not uniform enough for deterministic extraction "
            f"(p90 distance {background_variation:.2f} > {max_background_variation:.2f}); "
            "use source-faithful image-edit asset separation instead"
        )

    effective_low = max(float(low_threshold), background_variation + 2.0)
    effective_high = effective_low + max(1.0, float(feather))
    distances = np.linalg.norm(rgb - background, axis=2)
    alpha = ((distances - effective_low) / (effective_high - effective_low) * 255.0).clip(0, 255).astype(np.uint8)
    alpha_border = border_pixels(np.repeat(alpha[:, :, None], 3, axis=2))[:, 0]
    foreground_border_ratio = float((alpha_border >= 8).mean())
    if foreground_border_ratio > 0.02:
        raise ValueError(
            "foreground reaches the extraction boundary "
            f"({foreground_border_ratio:.1%} of border pixels); enlarge the box or use image-edit separation"
        )
    alpha_box = Image.fromarray(alpha).point(lambda value: 255 if value >= 8 else 0).getbbox()
    if not alpha_box:
        raise ValueError("deterministic extraction found no foreground pixels")

    left = max(0, alpha_box[0] - padding)
    top = max(0, alpha_box[1] - padding)
    right = min(width, alpha_box[2] + padding)
    bottom = min(height, alpha_box[3] + padding)
    rgba = np.dstack([rgb.astype(np.uint8), alpha])
    output = Image.fromarray(rgba).crop((left, top, right, bottom))
    output_box = [x + left, y + top, right - left, bottom - top]
    metadata = {
        "background_rgb": [int(round(value)) for value in background],
        "background_variation_p90": round(background_variation, 3),
        "foreground_border_ratio": round(foreground_border_ratio, 5),
        "alpha_low_threshold": round(effective_low, 3),
        "alpha_high_threshold": round(effective_high, 3),
        "source_box_px": box,
        "output_box_px": output_box,
    }
    return output, output_box, metadata


def main():
    parser = argparse.ArgumentParser(
        description="Separate an unoccluded foreground object from a uniform source background without generative redrawing."
    )
    parser.add_argument("page_dir")
    parser.add_argument("--source", default="source.png")
    parser.add_argument("--box", required=True, type=parse_box, metavar="X,Y,W,H")
    parser.add_argument("--out", required=True)
    parser.add_argument("--id", default="source_asset")
    parser.add_argument("--alt")
    parser.add_argument("--z-index", type=int, default=220)
    parser.add_argument("--fragment")
    parser.add_argument("--max-background-variation", type=float, default=28.0)
    parser.add_argument("--low-threshold", type=float, default=16.0)
    parser.add_argument("--feather", type=float, default=28.0)
    parser.add_argument("--padding", type=int, default=2)
    args = parser.parse_args()

    if not 0 <= args.max_background_variation <= 48:
        parser.error("--max-background-variation must be between 0 and 48")
    if args.low_threshold < 1:
        parser.error("--low-threshold must be at least 1")
    if args.feather < 1:
        parser.error("--feather must be at least 1")

    page_dir = Path(args.page_dir).expanduser().resolve()
    source_path = resolve_under(page_dir, args.source, "source.png")
    output_path = resolve_under(page_dir, args.out, "")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    source_image = Image.open(source_path)
    output, output_box, metadata = extract_asset(
        source_image,
        args.box,
        args.max_background_variation,
        args.low_threshold,
        args.feather,
        max(0, args.padding),
    )
    output.save(output_path)

    output_ref = relative_or_absolute(page_dir, output_path)
    source_ref = relative_or_absolute(page_dir, source_path)
    payload = {
        "schema_version": 1,
        "id": args.id,
        "source": source_ref,
        "output": output_ref,
        **metadata,
    }
    if args.fragment:
        fragment_path = resolve_under(page_dir, args.fragment, "")
        fragment = {
            "images": [
                {
                    "id": args.id,
                    "path": output_ref,
                    "box_px": output_box,
                    "alt": args.alt or f"Source-faithfully extracted asset {args.id}",
                    "z_index": args.z_index,
                }
            ],
            "asset_provenance": [
                {
                    "path": output_ref,
                    "source": source_ref,
                    "source_type": "source-faithful-extraction",
                    "provenance_note": (
                        "Deterministically separated exact source pixels from a verified uniform background "
                        "with editppt image extract-source."
                    ),
                    "source_box_px": args.box,
                    "output_box_px": output_box,
                }
            ],
        }
        fragment_path.parent.mkdir(parents=True, exist_ok=True)
        fragment_path.write_text(json.dumps(fragment, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        payload["fragment"] = relative_or_absolute(page_dir, fragment_path)
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
