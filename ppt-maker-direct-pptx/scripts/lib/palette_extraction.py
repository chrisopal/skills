"""Deterministic palette extraction from a reference image.

Used by `scripts/style_from_reference.py` to seed `color_strategy` before the
vision model fills in the rest of the master_style. The algorithm is
intentionally simple and deterministic so tests can rely on snapshot output:

1. Load the image via Pillow.
2. Resize down to at most 200x200 to keep work bounded.
3. Quantize to `n_colors` (default 6) using Pillow's median-cut.
4. Sort the palette by descending pixel count.
5. Return tuples of (hex, fraction, rgb).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PIL import Image

DEFAULT_N_COLORS = 6
MAX_DIMENSION = 200


@dataclass(frozen=True)
class PaletteColor:
    hex: str
    fraction: float
    rgb: tuple[int, int, int]


def _rgb_to_hex(rgb: tuple[int, int, int]) -> str:
    return "#{:02X}{:02X}{:02X}".format(*rgb)


def extract_palette(
    image_path: Path,
    *,
    n_colors: int = DEFAULT_N_COLORS,
    max_dimension: int = MAX_DIMENSION,
) -> list[PaletteColor]:
    if n_colors < 1:
        raise ValueError("n_colors must be >= 1")
    if not image_path.exists():
        raise FileNotFoundError(image_path)

    with Image.open(image_path) as raw:
        img = raw.convert("RGB")
        img.thumbnail((max_dimension, max_dimension))
        quantized = img.quantize(colors=n_colors, method=Image.Quantize.MEDIANCUT)
        palette_bytes = quantized.getpalette() or []
        available = len(palette_bytes) // 3
        limit = min(n_colors, available)
        palette_rgb = [
            (palette_bytes[i * 3], palette_bytes[i * 3 + 1], palette_bytes[i * 3 + 2])
            for i in range(limit)
        ]
        histogram = quantized.histogram()  # length 256 for P-mode

    total = sum(histogram[:limit]) or 1
    colors: list[PaletteColor] = []
    for idx, rgb in enumerate(palette_rgb):
        count = histogram[idx] if idx < len(histogram) else 0
        colors.append(
            PaletteColor(
                hex=_rgb_to_hex(rgb),
                fraction=count / total,
                rgb=rgb,
            )
        )
    colors.sort(key=lambda c: c.fraction, reverse=True)
    return colors


def palette_to_color_strategy(palette: list[PaletteColor]) -> dict[str, str]:
    """Map the top palette entries onto the conventional master_style color slots.

    Goal: provide reasonable defaults so the vision model can override individual
    fields without re-extracting colors.

    Mapping order (descending pixel share):
      1. background
      2. primary
      3. secondary
      4. neutral
      5. text_primary (fallback to '#1E1E1E' if palette runs out)
      6. text_secondary (fallback to '#6B7280')
    """

    slots = ["background", "primary", "secondary", "neutral", "text_primary", "text_secondary"]
    fallbacks = {
        "background": "#FFFFFF",
        "primary": "#A8D86B",
        "secondary": "#0F95B6",
        "neutral": "#D9D9D9",
        "text_primary": "#1E1E1E",
        "text_secondary": "#6B7280",
    }
    out: dict[str, str] = {}
    for idx, slot in enumerate(slots):
        if idx < len(palette):
            out[slot] = palette[idx].hex
        else:
            out[slot] = fallbacks[slot]
    return out
