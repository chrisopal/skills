"""Tiny axis-aligned rectangle helpers used by the geometry lint pass.

Coordinates are in PowerPoint inches (16:9 canvas = 13.333 × 7.5).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

CANVAS_WIDTH = 13.333
CANVAS_HEIGHT = 7.5
EPSILON = 1e-6


@dataclass(frozen=True)
class Rect:
    x: float
    y: float
    w: float
    h: float

    @property
    def right(self) -> float:
        return self.x + self.w

    @property
    def bottom(self) -> float:
        return self.y + self.h

    def is_in_canvas(self, *, w: float = CANVAS_WIDTH, h: float = CANVAS_HEIGHT) -> bool:
        return (
            self.x >= -EPSILON
            and self.y >= -EPSILON
            and self.right <= w + EPSILON
            and self.bottom <= h + EPSILON
        )

    def overlaps(self, other: "Rect") -> bool:
        if self.right <= other.x + EPSILON or other.right <= self.x + EPSILON:
            return False
        if self.bottom <= other.y + EPSILON or other.bottom <= self.y + EPSILON:
            return False
        return True

    def overlap_area(self, other: "Rect") -> float:
        if not self.overlaps(other):
            return 0.0
        ox = max(0.0, min(self.right, other.right) - max(self.x, other.x))
        oy = max(0.0, min(self.bottom, other.bottom) - max(self.y, other.y))
        return ox * oy


def rect_from(value: dict | None) -> Rect | None:
    if not isinstance(value, dict):
        return None
    try:
        return Rect(
            x=float(value["x"]),
            y=float(value["y"]),
            w=float(value["w"]),
            h=float(value["h"]),
        )
    except (KeyError, ValueError, TypeError):
        return None


def collect_overlap_pairs(rects: Iterable[tuple[str, Rect]]) -> list[tuple[str, str, float]]:
    """Return all (label_a, label_b, overlap_area) pairs that intersect."""

    items = list(rects)
    out = []
    for i in range(len(items)):
        for j in range(i + 1, len(items)):
            label_a, rect_a = items[i]
            label_b, rect_b = items[j]
            area = rect_a.overlap_area(rect_b)
            if area > EPSILON:
                out.append((label_a, label_b, area))
    return out
