#!/usr/bin/env python3
"""Deterministic, dependency-free renderer for enterprise diagram specs.

The public entry point is :func:`render_svg`.  The renderer deliberately emits
plain SVG text so callers can keep the JSON source and edit the result in any
vector editor without a browser, canvas, or external asset.
"""

from __future__ import annotations

import argparse
import heapq
import json
import math
import re
from html import escape
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
with (ROOT / "assets" / "diagram-themes.json").open(encoding="utf-8") as _theme_file:
    THEMES: dict[str, dict[str, Any]] = json.load(_theme_file)

LAYOUTS = {"layered", "flow", "pipeline", "swimlane", "network", "parallel", "sequence", "matrix"}
ROLES = {"primary", "process", "data", "success", "decision", "neutral", "warning"}
SHAPES = {"box", "diamond", "note"}
EDGE_KINDS = {"normal", "feedback", "dashed"}
ROUTES = {"auto", "left", "right"}
MAX_NODES = 64
MAX_EDGES = 120
MAX_TEXT = 4000
FONT_SIZE = 16
LINE_HEIGHT = 22
MARGIN = 48
HEADER_HEIGHT = 96
SPEC_FIELDS = {"version", "title", "subtitle", "footer", "layout", "theme", "width", "nodes", "edges", "groups"}
NODE_FIELDS = {"id", "title", "description", "row", "col", "span", "role", "shape", "badge"}
EDGE_FIELDS = {"from", "to", "label", "kind", "route"}
GROUP_FIELDS = {"id", "title", "members", "kind", "role"}


class SpecError(ValueError):
    """Raised when a diagram cannot be rendered without ambiguous geometry."""


def _finite_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _integer(value: Any, name: str, minimum: int = 0, maximum: int = 256) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise SpecError(f"{name} must be an integer")
    if value < minimum or value > maximum:
        raise SpecError(f"{name} must be between {minimum} and {maximum}")
    return value


def _text(value: Any, name: str, *, required: bool = False, maximum: int = MAX_TEXT) -> str:
    if value is None and not required:
        return ""
    if not isinstance(value, str):
        raise SpecError(f"{name} must be a string")
    if required and not value.strip():
        raise SpecError(f"{name} must not be empty")
    if len(value) > maximum:
        raise SpecError(f"{name} is too long (maximum {maximum} characters)")
    return value


def _validate(spec: dict[str, Any], selected_theme: str) -> list[dict[str, Any]]:
    if not isinstance(spec, dict):
        raise SpecError("spec must be an object")
    if spec.get("version") != "1.0":
        raise SpecError("version must be '1.0'")
    unknown = sorted(set(spec) - SPEC_FIELDS)
    if unknown:
        raise SpecError(f"unknown spec fields: {', '.join(unknown)}")
    _text(spec.get("title"), "title", required=True, maximum=200)
    _text(spec.get("subtitle", ""), "subtitle", maximum=600)
    _text(spec.get("footer", ""), "footer", maximum=600)
    layout = spec.get("layout")
    if layout not in LAYOUTS:
        raise SpecError(f"unknown layout: {layout!r}")
    if selected_theme not in THEMES:
        raise SpecError(f"unknown theme: {selected_theme!r}")
    if "width" in spec:
        if not _finite_number(spec["width"]):
            raise SpecError("width must be a finite number")
        if not 640 <= float(spec["width"]) <= 4000:
            raise SpecError("width must be between 640 and 4000")
    nodes = spec.get("nodes")
    if not isinstance(nodes, list) or not nodes:
        raise SpecError("nodes must contain at least one node")
    if len(nodes) > MAX_NODES:
        raise SpecError(f"nodes exceed maximum of {MAX_NODES}")
    seen: set[str] = set()
    normalized: list[dict[str, Any]] = []
    occupied: dict[int, list[tuple[int, int, str]]] = {}
    for index, raw in enumerate(nodes):
        if not isinstance(raw, dict):
            raise SpecError(f"nodes[{index}] must be an object")
        unknown = sorted(set(raw) - NODE_FIELDS)
        if unknown:
            raise SpecError(f"unknown nodes[{index}] fields: {', '.join(unknown)}")
        node_id = _text(raw.get("id"), f"nodes[{index}].id", required=True, maximum=80)
        if node_id in seen:
            raise SpecError(f"duplicate node id: {node_id}")
        seen.add(node_id)
        row = _integer(raw.get("row"), f"nodes[{index}].row", 0, 128)
        col = _integer(raw.get("col"), f"nodes[{index}].col", 0, 128)
        span = _integer(raw.get("span", 1), f"nodes[{index}].span", 1, 32)
        title = _text(raw.get("title"), f"nodes[{index}].title", required=True, maximum=500)
        description = _text(raw.get("description", ""), f"nodes[{index}].description", maximum=MAX_TEXT)
        role = raw.get("role", "neutral")
        shape = raw.get("shape", "box")
        badge = _text(raw.get("badge", ""), f"nodes[{index}].badge", maximum=24)
        if role not in ROLES:
            raise SpecError(f"unknown node role: {role!r}")
        if shape not in SHAPES:
            raise SpecError(f"unknown node shape: {shape!r}")
        occupied.setdefault(row, [])
        for start, end, other in occupied[row]:
            if col < end and col + span > start:
                raise SpecError(f"overlapping row/col/span nodes: {node_id} and {other}")
        occupied[row].append((col, col + span, node_id))
        normalized.append({"id": node_id, "title": title, "description": description, "row": row, "col": col, "span": span, "role": role, "shape": shape, "badge": badge})
    edges = spec.get("edges", [])
    if not isinstance(edges, list):
        raise SpecError("edges must be an array")
    if len(edges) > MAX_EDGES:
        raise SpecError(f"edges exceed maximum of {MAX_EDGES}")
    for index, raw in enumerate(edges):
        if not isinstance(raw, dict):
            raise SpecError(f"edges[{index}] must be an object")
        unknown = sorted(set(raw) - EDGE_FIELDS)
        if unknown:
            raise SpecError(f"unknown edges[{index}] fields: {', '.join(unknown)}")
        if raw.get("from") not in seen or raw.get("to") not in seen:
            raise SpecError(f"edges[{index}] references an unknown node")
        _text(raw.get("label", ""), f"edges[{index}].label", maximum=300)
        if raw.get("kind", "normal") not in EDGE_KINDS:
            raise SpecError(f"unknown edge kind: {raw.get('kind')!r}")
        if raw.get("route", "auto") not in ROUTES:
            raise SpecError(f"unknown edge route: {raw.get('route')!r}")
    groups = spec.get("groups", [])
    if not isinstance(groups, list):
        raise SpecError("groups must be an array")
    group_ids: set[str] = set()
    for index, raw in enumerate(groups):
        if not isinstance(raw, dict):
            raise SpecError(f"groups[{index}] must be an object")
        unknown = sorted(set(raw) - GROUP_FIELDS)
        if unknown:
            raise SpecError(f"unknown groups[{index}] fields: {', '.join(unknown)}")
        group_id = _text(raw.get("id"), f"groups[{index}].id", required=True, maximum=80)
        if group_id in group_ids:
            raise SpecError(f"duplicate group id: {group_id}")
        group_ids.add(group_id)
        members = raw.get("members")
        if not isinstance(members, list) or not members:
            raise SpecError(f"groups[{index}].members must be a non-empty array")
        if len(set(members)) != len(members) or any(member not in seen for member in members):
            raise SpecError(f"groups[{index}].members references an unknown or duplicate node")
        _text(raw.get("title", ""), f"groups[{index}].title", maximum=200)
        if raw.get("kind", "zone") not in {"band", "zone", "lane"}:
            raise SpecError(f"unknown group kind: {raw.get('kind')!r}")
        if raw.get("role", "neutral") not in ROLES:
            raise SpecError(f"unknown group role: {raw.get('role')!r}")
    if spec.get("layout") == "sequence" and any(node["row"] != 0 for node in normalized):
        raise SpecError("sequence nodes must all use row 0 as participant headers")
    return normalized


def _unit_width(char: str) -> float:
    if ord(char) > 255:
        return 1.0
    if char in "WwMm":
        return 0.95
    return 0.72


def _wrap(value: str, width: float, font_size: float = FONT_SIZE) -> list[str]:
    """Wrap by display width while preserving every source character."""
    if not value:
        return []
    limit = max(4.0, width / (font_size * 1.05))
    lines: list[str] = []
    for source_line in value.split("\n"):
        if not source_line:
            lines.append("")
            continue
        current: list[str] = []
        used = 0.0
        # Keep short ASCII identifiers intact when they fit.  A token which
        # is longer than the available line is still split character by
        # character, so long URLs and hashes remain renderable and lossless.
        tokens = re.findall(r"[A-Za-z0-9_-]+|[^A-Za-z0-9_-]", source_line)
        for token in tokens:
            token_width = sum(_unit_width(char) for char in token)
            if token_width <= limit and current and used + token_width > limit:
                lines.append("".join(current))
                current = []
                used = 0.0
            if token_width <= limit:
                current.append(token)
                used += token_width
                continue
            for char in token:
                amount = _unit_width(char)
                if current and used + amount > limit:
                    lines.append("".join(current))
                    current = []
                    used = 0.0
                current.append(char)
                used += amount
        lines.append("".join(current))
    return lines


def _text_lines(node: dict[str, Any], width: float) -> tuple[list[str], list[str]]:
    if node.get("shape") == "diamond":
        # A diamond's usable center is narrower than its bounding rectangle.
        # Keep text inside the widest inscribed rectangle and grow the diamond
        # vertically with the resulting line count.
        inner = max(50.0, width * 0.48)
    else:
        inner = max(50.0, width - 40)
    return _wrap(node["title"], inner), _wrap(node["description"], inner)


def _rect(node: dict[str, Any]) -> tuple[float, float, float, float]:
    return (node["x"], node["y"], node["x"] + node["width"], node["y"] + node["height"])


def _overlap_segment(a: tuple[float, float], b: tuple[float, float], rect: tuple[float, float, float, float]) -> bool:
    x0, y0, x1, y1 = rect
    if a[0] == b[0]:
        x = a[0]
        if x0 < x < x1:
            lo, hi = sorted((a[1], b[1]))
            return max(lo, y0) < min(hi, y1)
        return False
    if a[1] == b[1]:
        y = a[1]
        if y0 < y < y1:
            lo, hi = sorted((a[0], b[0]))
            return max(lo, x0) < min(hi, x1)
        return False
    return True


def _node_port(node: dict[str, Any], side: str) -> tuple[float, float]:
    x, y, w, h = node["x"], node["y"], node["width"], node["height"]
    if node.get("shape") == "diamond":
        return {"top": (x + w / 2, y), "bottom": (x + w / 2, y + h), "left": (x, y + h / 2), "right": (x + w, y + h / 2)}[side]
    return {"top": (x + w / 2, y), "bottom": (x + w / 2, y + h), "left": (x, y + h / 2), "right": (x + w, y + h / 2)}[side]


def _anchor(source: dict[str, Any], target: dict[str, Any], route: str, layout: str | None = None) -> tuple[tuple[float, float], tuple[float, float], tuple[float, float], tuple[float, float]]:
    sx, sy, sw, sh = source["x"], source["y"], source["width"], source["height"]
    tx, ty, tw, th = target["x"], target["y"], target["width"], target["height"]
    if route == "left":
        return _node_port(source, "left"), _node_port(target, "left"), (-1.0, 0.0), (-1.0, 0.0)
    if route == "right":
        return _node_port(source, "right"), _node_port(target, "right"), (1.0, 0.0), (1.0, 0.0)
    # Network and parallel diagrams encode cross-column flow explicitly.  A
    # row difference alone must not force a bottom-to-top connection: that
    # reuses the same vertical port for an incoming and outgoing edge at a
    # join/gateway and makes two arrows look like a reverse data flow.
    if layout in {"network", "parallel"} and source["col"] != target["col"]:
        if target["col"] > source["col"]:
            return _node_port(source, "right"), _node_port(target, "left"), (1.0, 0.0), (-1.0, 0.0)
        return _node_port(source, "left"), _node_port(target, "right"), (-1.0, 0.0), (1.0, 0.0)
    if target["row"] > source["row"]:
        return _node_port(source, "bottom"), _node_port(target, "top"), (0.0, 1.0), (0.0, -1.0)
    if target["row"] < source["row"]:
        return _node_port(source, "top"), _node_port(target, "bottom"), (0.0, -1.0), (0.0, 1.0)
    if target["col"] >= source["col"]:
        return _node_port(source, "right"), _node_port(target, "left"), (1.0, 0.0), (-1.0, 0.0)
    return _node_port(source, "left"), _node_port(target, "right"), (-1.0, 0.0), (1.0, 0.0)


def _self_loop(source: dict[str, Any], nodes: list[dict[str, Any]], canvas_w: float, canvas_h: float) -> tuple[list[tuple[float, float]], bool]:
    x0, y0, x1, y1 = _rect(source)
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    other_rects = []
    for node in nodes:
        if node["id"] == source["id"]:
            continue
        rx0, ry0, rx1, ry1 = _rect(node)
        other_rects.append((rx0 - 8, ry0 - 8, rx1 + 8, ry1 + 8))
    candidates = [
        [(x1, cy), (x1 + 46, cy), (x1 + 46, y0 - 30), (x1, y0 - 30), (x1, cy)],
        [(x0, cy), (x0 - 46, cy), (x0 - 46, y0 - 30), (x0, y0 - 30), (x0, cy)],
        [(cx, y0), (cx, y0 - 30), (x1 + 30, y0 - 30), (x1 + 30, y0), (cx, y0)],
        [(cx, y1), (cx, y1 + 30), (x1 + 30, y1 + 30), (x1 + 30, y1), (cx, y1)],
    ]
    for points in candidates:
        if all(0 <= x <= canvas_w and 0 <= y <= canvas_h for x, y in points) and all(not any(_overlap_segment(a, b, rect) for rect in other_rects) for a, b in zip(points, points[1:])):
            return points, True
    return candidates[0], False


def _route_orthogonal(source: dict[str, Any], target: dict[str, Any], nodes: list[dict[str, Any]], canvas_w: float, canvas_h: float, route: str, header_height: float, layout: str | None = None, extra_obstacles: list[tuple[float, float, float, float]] | None = None) -> tuple[list[tuple[float, float]], bool]:
    if source["id"] == target["id"]:
        return _self_loop(source, nodes, canvas_w, canvas_h)
    source_port, target_port, source_direction, target_direction = _anchor(source, target, route, layout)
    source_stub = (source_port[0] + source_direction[0] * 16, source_port[1] + source_direction[1] * 16)
    target_stub = (target_port[0] + target_direction[0] * 16, target_port[1] + target_direction[1] * 16)
    start, end = source_stub, target_stub
    obstacles: list[tuple[float, float, float, float]] = []
    # Route against the node rectangles themselves.  Anchors sit exactly on a
    # boundary; the path is permitted to touch a border but never enter its
    # interior, which keeps adjacent same-row nodes routable.
    for node in nodes:
        x0, y0, x1, y1 = _rect(node)
        obstacles.append((x0 - 8, y0 - 8, x1 + 8, y1 + 8))
    if extra_obstacles:
        obstacles.extend(extra_obstacles)
    xs = {round(start[0], 3), round(end[0], 3), 24.0, round(canvas_w - 24, 3)}
    ys = {round(start[1], 3), round(end[1], 3), 24.0, round(canvas_h - 24, 3)}
    for x0, y0, x1, y1 in obstacles:
        xs.update((round(x0, 3), round(x1, 3), round((x0 + x1) / 2, 3)))
        ys.update((round(y0, 3), round(y1, 3), round((y0 + y1) / 2, 3)))
    xs_sorted, ys_sorted = sorted(xs), sorted(ys)
    points = [(x, y) for x in xs_sorted for y in ys_sorted if not any(x0 < x < x1 and y0 < y < y1 for x0, y0, x1, y1 in obstacles)]
    point_set = set(points)
    if start not in point_set:
        point_set.add(start); points.append(start)
    if end not in point_set:
        point_set.add(end); points.append(end)

    def clear(a: tuple[float, float], b: tuple[float, float]) -> bool:
        if a[0] != b[0] and a[1] != b[1]:
            return False
        return not any(_overlap_segment(a, b, rect) for rect in obstacles)

    neighbors: dict[tuple[float, float], list[tuple[tuple[float, float], float]]]= {point: [] for point in points}
    by_x: dict[float, list[tuple[float, float]]] = {}
    by_y: dict[float, list[tuple[float, float]]] = {}
    for point in points:
        by_x.setdefault(point[0], []).append(point)
        by_y.setdefault(point[1], []).append(point)
    for values in (*by_x.values(), *by_y.values()):
        values.sort()
        for a, b in zip(values, values[1:]):
            if clear(a, b):
                distance = abs(a[0] - b[0]) + abs(a[1] - b[1])
                neighbors[a].append((b, distance)); neighbors[b].append((a, distance))
    queue: list[tuple[float, float, tuple[float, float], tuple[float, float] | None]] = [(0.0, 0.0, start, None)]
    best: dict[tuple[tuple[float, float], tuple[float, float] | None], float] = {(start, None): 0.0}
    parent: dict[tuple[tuple[float, float], tuple[float, float] | None], tuple[tuple[float, float], tuple[float, float] | None] | None] = {}
    finish: tuple[tuple[float, float], tuple[float, float] | None] | None = None
    while queue:
        _, turns, current, direction = heapq.heappop(queue)
        state = (current, direction)
        if current == end:
            finish = state; break
        for nxt, distance in neighbors.get(current, []):
            new_direction = (1.0, 0.0) if nxt[1] == current[1] else (0.0, 1.0)
            bend = 1.0 if direction is not None and direction != new_direction else 0.0
            new_cost = best[state] + distance + bend * 36
            next_state = (nxt, new_direction)
            if new_cost < best.get(next_state, float("inf")):
                best[next_state] = new_cost
                parent[next_state] = state
                heapq.heappush(queue, (new_cost, turns + bend, nxt, new_direction))
    if finish is None:
        # Dense feedback graphs can exhaust the compressed visibility graph.
        # Try deterministic perimeter tracks before rejecting the edge.  Each
        # candidate is checked against every node, so this fallback cannot
        # silently draw through node content.
        left, right = MARGIN - 20, canvas_w - MARGIN + 20
        top, bottom = header_height + 8, canvas_h - 24
        for track_x in ([left] if route == "left" else [right] if route == "right" else [left, right]):
            for track_y in (top, bottom):
                candidate = [start, (start[0], track_y), (track_x, track_y), (track_x, end[1]), end]
                if all(not any(_overlap_segment(a, b, rect) for rect in obstacles) for a, b in zip(candidate, candidate[1:])):
                    return candidate, True
        return [source_port, source_stub, end, target_stub, target_port], False
    path: list[tuple[float, float]] = []
    cursor: tuple[tuple[float, float], tuple[float, float] | None] | None = finish
    while cursor is not None:
        path.append(cursor[0])
        cursor = parent.get(cursor)
    path.reverse()
    simplified: list[tuple[float, float]] = []
    for point in path:
        if len(simplified) >= 2 and (simplified[-1][0] == point[0] == simplified[-2][0] or simplified[-1][1] == point[1] == simplified[-2][1]):
            simplified[-1] = point
        else:
            simplified.append(point)
    return [source_port, source_stub, *simplified, target_stub, target_port], True


def _sequence_layout(nodes: list[dict[str, Any]], edges_raw: list[dict[str, Any]], canvas_w: float, header_height: float, gap_x: float) -> tuple[list[dict[str, Any]], float, list[dict[str, Any]]]:
    count = len(nodes)
    cell_w = max(160.0, min(280.0, (canvas_w - 2 * MARGIN - gap_x * max(0, count - 1)) / max(1, count)))
    actual_w = max(canvas_w, 2 * MARGIN + count * cell_w + gap_x * max(0, count - 1))
    y = header_height + 52
    max_header = 0.0
    for index, node in enumerate(nodes):
        node["x"] = MARGIN + index * (cell_w + gap_x)
        node["y"] = y
        node["width"] = cell_w
        titles, desc = _text_lines(node, cell_w)
        node["title_lines"], node["description_lines"] = titles, desc
        node["height"] = max(66.0, 24 + len(titles) * LINE_HEIGHT + len(desc) * LINE_HEIGHT + 18)
        if node["shape"] == "diamond":
            total_lines = max(1, len(titles + desc))
            node["height"] = max(node["height"], 2 * (total_lines * LINE_HEIGHT + 18))
        max_header = max(max_header, node["height"])
    line_top = y + max_header + 44
    edge_meta: list[dict[str, Any]] = []
    label_obstacles: list[tuple[float, float, float, float]] = [_rect(node) for node in nodes]
    by_id = {node["id"]: node for node in nodes}
    lane = line_top
    label_budget = sum(max(28.0, len(_wrap(edge.get("label", ""), min(260.0, max(52.0, len(edge.get("label", "")) * 8.0 + 10.0)) - 18, 13)) * 18.0 + 10.0) + 78 for edge in edges_raw)
    for index, raw in enumerate(edges_raw):
        source, target = by_id[raw["from"]], by_id[raw["to"]]
        sx = source["x"] + source["width"] / 2
        tx = target["x"] + target["width"] / 2
        if source["id"] == target["id"]:
            right = source["x"] + source["width"] + 28
            points = [(sx, lane), (right, lane), (right, lane + 18), (sx, lane + 18)]
        else:
            # Lifelines are already drawn behind the nodes.  A message is only
            # the horizontal segment at its timestamp; avoid a long vertical
            # stroke from the participant header to the message lane.
            points = [(sx, lane), (tx, lane)]
        label_box = _label_box(points, raw.get("label", ""), actual_w, line_top + label_budget + 54, label_obstacles, header_height)
        occupied_bottom = max(point[1] for point in points)
        if label_box:
            occupied_bottom = max(occupied_bottom, label_box["y"] + label_box["height"])
        # Reserve each complete message row. A wrapped self-message label can
        # extend below the old fixed 60px timestamp interval; subsequent lines
        # and labels must not enter that row, even at a different x position.
        label_obstacles.append((8.0, line_top - 1, actual_w - 8, occupied_bottom + 2))
        edge_meta.append({"id": f"edge-{index}", "from": source["id"], "to": target["id"], "label": raw.get("label", ""), "kind": raw.get("kind", "normal"), "route": raw.get("route", "auto"), "points": points, "path": _path(points), "safe": True, "label_box": label_box})
        lane = max(lane + 60, occupied_bottom + 14)
    return nodes, actual_w, edge_meta


def _label_box(points: list[tuple[float, float]], label: str, canvas_w: float, canvas_h: float, obstacles: list[tuple[float, float, float, float]] | None = None, header_height: float = HEADER_HEIGHT, preferred_segments: list[int] | None = None) -> dict[str, Any] | None:
    if not label:
        return None
    segments = list(zip(points, points[1:]))
    # Keep ordinary short labels narrow enough to fit a grid gap.  The SVG
    # text is 13px, while this conservative estimate still leaves room for
    # Chinese glyphs and ASCII punctuation without turning ``HTTPS`` into a
    # label wider than the 56px network gap.
    width = min(260.0, max(52.0, len(label) * 8.0 + 10.0))
    lines = _wrap(label, width - 18, 13)
    height = max(28.0, len(lines) * 18.0 + 10.0)
    # Keep labels next to the segment which carries them.  A global list of
    # top-of-edge positions looks compact but makes vertical labels collide in
    # a branch/merge diagram.  Each segment gets three anchor points and the
    # candidates are placed on the side of that segment (above/below for a
    # horizontal segment, left/right for a vertical one).
    candidates: list[tuple[float, float]] = []
    useful = [pair for pair in segments if abs(pair[0][0] - pair[1][0]) + abs(pair[0][1] - pair[1][1]) >= 1.0]
    if not useful and points:
        useful = [(points[0], points[0])]
    for a, b in sorted(useful, key=lambda pair: abs(pair[0][0] - pair[1][0]) + abs(pair[0][1] - pair[1][1]), reverse=True):
        ax, ay = a
        bx, by = b
        horizontal = abs(ay - by) <= 1e-6
        for fraction in (0.25, 0.5, 0.75):
            cx = ax + (bx - ax) * fraction
            cy = ay + (by - ay) * fraction
            if horizontal:
                # Dense rows often leave no room immediately above the
                # connector.  Walk outward in one label-height steps before
                # considering the explicit header/footer fallback below.
                for offset in (7.0, height + 7.0, height * 2 + 7.0, height * 3 + 7.0, height * 4 + 7.0, height * 5 + 7.0):
                    candidates.extend(((cx - width / 2, cy - offset), (cx - width / 2, cy + offset)))
            else:
                for y_shift in (0.0, -height / 2, height / 2, -height, height, -height * 2, height * 2, -height * 3, height * 3):
                    for offset in (7.0, width + 7.0, width * 2 + 7.0):
                        candidates.extend(((cx - offset, cy - height / 2 + y_shift), (cx + offset, cy - height / 2 + y_shift)))
            # If both sides of a short segment are occupied, retain the
            # segment's horizontal ownership while using the clear header or
            # footer channel.  This is a bounded fallback, not a global
            # longest-edge placement.
            edge_x = min(max(8.0, cx - width / 2), canvas_w - width - 8)
            candidates.extend(((edge_x, header_height + 4), (edge_x, canvas_h - height - 8)))
            if obstacles:
                # Full-span nodes can consume every local side slot.  Their
                # outer boundaries are deterministic safe channels once the
                # caller has reserved canvas space for an explicit feedback
                # lane; use those boundaries before giving up.
                span_min = min(ay, by)
                span_max = max(ay, by)
                if horizontal:
                    for ox0, oy0, ox1, oy1 in obstacles:
                        if ox0 <= max(ax, bx) and ox1 >= min(ax, bx):
                            candidates.extend(((cx - width / 2, oy0 - height - 7), (cx - width / 2, oy1 + 7)))
                else:
                    for ox0, oy0, ox1, oy1 in obstacles:
                        if oy0 <= span_max and oy1 >= span_min:
                            candidates.extend(((ox0 - width - 7, cy - height / 2), (ox1 + 7, cy - height / 2)))
    if not candidates:
        candidates = [(8.0, header_height + 4)]

    # Preserve insertion order while avoiding duplicate positions from a
    # routed edge's short source/target stubs.
    candidates = list(dict.fromkeys((round(x, 3), round(y, 3)) for x, y in candidates))
    if obstacles:
        def clear(candidate: tuple[float, float]) -> bool:
            cx, cy = candidate
            box = (cx - 1, cy - 1, cx + width + 1, cy + height + 1)
            return not any(box[0] < x1 and box[2] > x0 and box[1] < y1 and box[3] > y0 for x0, y0, x1, y1 in obstacles)
        def clear_edge(candidate: tuple[float, float]) -> bool:
            cx, cy = candidate
            x0, y0, x1, y1 = cx, cy, cx + width, cy + height
            for (ax, ay), (bx, by) in segments:
                if abs(ax - bx) <= 1e-6 and x0 < ax < x1 and y0 < max(ay, by) and y1 > min(ay, by):
                    return False
                if abs(ay - by) <= 1e-6 and y0 < ay < y1 and x0 < max(ax, bx) and x1 > min(ax, bx):
                    return False
            return True
        def edge_score(candidate: tuple[float, float]) -> tuple[float, int]:
            cx, cy = candidate
            x0, y0, x1, y1 = cx, cy, cx + width, cy + height
            distances: list[tuple[int, float]] = []
            for index, ((ax, ay), (bx, by)) in enumerate(segments):
                if abs(ax - bx) <= 1e-6:
                    dx = 0.0 if x0 <= ax <= x1 else min(abs(ax - x0), abs(ax - x1))
                    dy = 0.0 if y0 <= max(ay, by) and y1 >= min(ay, by) else min(abs(y0 - max(ay, by)), abs(y1 - min(ay, by)))
                elif abs(ay - by) <= 1e-6:
                    dx = 0.0 if x0 <= max(ax, bx) and x1 >= min(ax, bx) else min(abs(x0 - max(ax, bx)), abs(x1 - min(ax, bx)))
                    dy = 0.0 if y0 <= ay <= y1 else min(abs(ay - y0), abs(ay - y1))
                else:
                    continue
                distances.append((index, math.hypot(dx, dy)))
            # Shared source/target stubs are visually ambiguous for branches
            # and merges.  The caller supplies the edge's unique segments;
            # score those first so a label (and any later leader) cannot prove
            # ownership by sitting beside a common prefix/suffix.
            preferred = [(index, distance) for index, distance in distances if preferred_segments and index in preferred_segments]
            scored = preferred or distances
            closest = min((distance for _, distance in scored), default=float("inf"))
            tied = [index for index, distance in scored if abs(distance - closest) <= 1e-6]
            if preferred_segments and preferred:
                # Outgoing branches prefer the target-side unique segment;
                # incoming merges prefer the source-side one.  The caller
                # orders the preferred list accordingly, while the final
                # index tie-break remains deterministic for ordinary edges.
                rank = {index: position for position, index in enumerate(preferred_segments)}
                return closest, min((rank.get(index, len(preferred_segments)) for index in tied), default=len(preferred_segments))
            return closest, -max(tied, default=-1)
        safe_candidates = [candidate for candidate in candidates if 8 <= candidate[0] <= canvas_w - width - 8 and header_height + 4 <= candidate[1] <= canvas_h - height - 8 and clear(candidate) and clear_edge(candidate)]
        if not safe_candidates:
            raise SpecError(f"cannot place edge label safely: {label[:40]}")
        x, y = min(enumerate(safe_candidates), key=lambda item: (*edge_score(item[1]), item[0]))[1]
    else:
        x, y = candidates[0]
        x = min(max(8.0, x), canvas_w - width - 8)
        y = min(max(header_height + 4, y), canvas_h - height - 8)
    return {"x": round(x, 2), "y": round(y, 2), "width": round(width, 2), "height": height, "lines": lines}


def _path(points: Iterable[tuple[float, float]]) -> str:
    values = list(points)
    if not values:
        return ""
    return "M " + " L ".join(f"{x:.1f} {y:.1f}" for x, y in values)


def _label_distance(points: list[tuple[float, float]], box: dict[str, Any]) -> float:
    """Return the shortest axis distance from a label rectangle to its edge."""
    x0, y0 = box["x"], box["y"]
    x1, y1 = x0 + box["width"], y0 + box["height"]
    best = float("inf")
    for (ax, ay), (bx, by) in zip(points, points[1:]):
        if abs(ax - bx) <= 1e-6:
            dx = 0.0 if x0 <= ax <= x1 else min(abs(ax - x0), abs(ax - x1))
            dy = 0.0 if y0 <= max(ay, by) and y1 >= min(ay, by) else min(abs(y0 - max(ay, by)), abs(y1 - min(ay, by)))
        elif abs(ay - by) <= 1e-6:
            dx = 0.0 if x0 <= max(ax, bx) and x1 >= min(ax, bx) else min(abs(x0 - max(ax, bx)), abs(x1 - min(ax, bx)))
            dy = 0.0 if y0 <= ay <= y1 else min(abs(ay - y0), abs(ay - y1))
        else:
            continue
        best = min(best, math.hypot(dx, dy))
    return best


def _segment_key(a: tuple[float, float], b: tuple[float, float]) -> tuple[tuple[float, float], tuple[float, float]] | None:
    """Normalize one routed segment for shared-prefix/suffix detection."""
    if a == b:
        return None
    return tuple(sorted((a, b)))


def _preferred_segments(index: int, routes: list[list[tuple[float, float]]]) -> list[int] | None:
    """Return unique route segments ordered for this edge's label.

    Branches share a source prefix and merges share a target suffix.  Labels
    should never be placed on those ambiguous pieces.  When both ends are
    shared, the middle unique segment is the only stable ownership cue.
    """
    current = routes[index]
    keys = [[_segment_key(a, b) for a, b in zip(points, points[1:])] for points in routes]
    counts: dict[tuple[tuple[float, float], tuple[float, float]], int] = {}
    for route_keys in keys:
        for key in set(key for key in route_keys if key is not None):
            counts[key] = counts.get(key, 0) + 1
    unique = [segment_index for segment_index, key in enumerate(keys[index]) if key is not None and counts.get(key, 0) == 1]
    if not unique:
        return None
    shared_start = 0
    while shared_start < len(keys[index]) and keys[index][shared_start] is not None and counts.get(keys[index][shared_start], 0) > 1:
        shared_start += 1
    shared_end = len(keys[index]) - 1
    while shared_end >= 0 and keys[index][shared_end] is not None and counts.get(keys[index][shared_end], 0) > 1:
        shared_end -= 1
    if shared_start > 0 and shared_end < len(keys[index]) - 1:
        # The edge both leaves a shared fan-out and enters a shared merge.
        # Keep the unique middle region, centered to avoid either shared end.
        middle = (min(unique) + max(unique)) / 2
        return sorted(unique, key=lambda segment_index: (abs(segment_index - middle), segment_index))
    if shared_start > 0:
        # Outgoing branch: target-side unique segments first.
        return sorted(unique, reverse=True)
    if shared_end < len(keys[index]) - 1:
        # Incoming merge: source-side unique segments first.
        return sorted(unique)
    return unique


def _leader_path(points: list[tuple[float, float]], box: dict[str, Any], obstacles: list[tuple[float, float, float, float]], preferred_segments: list[int] | None = None) -> list[tuple[float, float]] | None:
    """Find a short, arrowless Manhattan leader from an edge to a label."""
    x0, y0 = box["x"], box["y"]
    x1, y1 = x0 + box["width"], y0 + box["height"]
    if preferred_segments:
        starts = []
        for index in preferred_segments:
            if index < 0 or index >= len(points) - 1:
                continue
            a, b = points[index], points[index + 1]
            starts.extend((a, b, ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)))
    else:
        starts = list(points)
        starts.extend(((a[0] + b[0]) / 2, (a[1] + b[1]) / 2) for a, b in zip(points, points[1:]))
    ends = [(x0 + box["width"] / 2, y0), (x0 + box["width"] / 2, y1), (x0, y0 + box["height"] / 2), (x1, y0 + box["height"] / 2)]
    expanded = [(a - 2, b - 2, c + 2, d + 2) for a, b, c, d in obstacles]

    def clear_segment(a: tuple[float, float], b: tuple[float, float]) -> bool:
        if a[0] != b[0] and a[1] != b[1]:
            return False
        return not any(_overlap_segment(a, b, rect) for rect in expanded)

    def valid(path: list[tuple[float, float]]) -> bool:
        return all(clear_segment(a, b) for a, b in zip(path, path[1:]))

    # Try the direct two-bend paths first; these keep the leader visually
    # attached to a nearby segment and are sufficient for ordinary row gaps.
    ranked = sorted(((abs(s[0] - e[0]) + abs(s[1] - e[1]), s, e) for s in starts for e in ends), key=lambda item: item[0])
    for _, start, end in ranked:
        for candidate in ([start, (start[0], end[1]), end], [start, (end[0], start[1]), end]):
            if valid(candidate):
                return candidate
    # If a full-span node blocks both bends, route around its nearest outer
    # boundary.  Candidate tracks are still checked against every obstacle.
    tracks = sorted({value for rect in expanded for value in (rect[0], rect[2])})
    for _, start, end in ranked[:24]:
        for track in tracks:
            for candidate in ([start, (track, start[1]), (track, end[1]), end], [start, (start[0], track), (end[0], track), end]):
                if valid(candidate):
                    return candidate
    return None


def _svg_node(node: dict[str, Any], theme: dict[str, Any]) -> str:
    role = theme["roles"][node["role"]]
    x, y, w, h = node["x"], node["y"], node["width"], node["height"]
    stroke, fill = role["stroke"], role["fill"]
    if node["shape"] == "diamond":
        points = f"{x + w / 2:.1f},{y:.1f} {x + w:.1f},{y + h / 2:.1f} {x + w / 2:.1f},{y + h:.1f} {x:.1f},{y + h / 2:.1f}"
        shape = f'<polygon points="{points}" fill="{fill}" stroke="{stroke}" stroke-width="2"/>'
        tx, anchor = x + w / 2, "middle"
    elif node["shape"] == "note":
        fold = min(18.0, w * 0.14)
        points = f"{x:.1f},{y:.1f} {x + w - fold:.1f},{y:.1f} {x + w:.1f},{y + fold:.1f} {x + w:.1f},{y + h:.1f} {x:.1f},{y + h:.1f}"
        shape = f'<polygon points="{points}" fill="{fill}" stroke="{stroke}" stroke-width="2"/>'
        tx, anchor = x + w / 2, "middle"
    else:
        shape = f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="6" fill="{fill}" stroke="{stroke}" stroke-width="2"/>'
        tx, anchor = x + w / 2, "middle"
    lines = node["title_lines"] + node["description_lines"]
    title_count = len(node["title_lines"])
    if anchor == "middle":
        start_y = y + h / 2 - (len(lines) * LINE_HEIGHT) / 2 + FONT_SIZE
    else:
        start_y = y + 25
    text_parts = []
    for index, line in enumerate(lines):
        weight = "700" if index < title_count else "400"
        opacity = "1" if index < title_count else "0.86"
        text_parts.append(f'<tspan x="{tx:.1f}" dy="{0 if index == 0 else LINE_HEIGHT}" font-weight="{weight}" opacity="{opacity}">{escape(line)}</tspan>')
    text = f'<text x="{tx:.1f}" y="{start_y:.1f}" text-anchor="{anchor}" fill="{theme["text"]}" font-family="PingFang SC, Noto Sans CJK SC, Microsoft YaHei, Hiragino Sans GB, STSong, Arial, Helvetica, sans-serif" font-size="{FONT_SIZE}px">{"".join(text_parts)}</text>'
    badge = ""
    if node.get("badge"):
        bx, by = x + 16, y + 14
        badge = f'<circle cx="{bx:.1f}" cy="{by:.1f}" r="11" fill="{stroke}"/><text x="{bx:.1f}" y="{by + 5:.1f}" text-anchor="middle" fill="#FFFFFF" font-family="PingFang SC, Noto Sans CJK SC, Microsoft YaHei, Hiragino Sans GB, STSong, Arial, Helvetica, sans-serif" font-size="12px" font-weight="700">{escape(node["badge"])}</text>'
    return f'<g data-node-id="{escape(node["id"], quote=True)}">{shape}{badge}{text}</g>'


def _header_metrics(spec: dict[str, Any], width: float) -> tuple[float, list[str], list[str]]:
    title_lines = _wrap(spec["title"], max(80.0, width - 2 * MARGIN), 24)
    subtitle_lines = _wrap(spec.get("subtitle", ""), max(80.0, width - 2 * MARGIN), 16) if spec.get("subtitle") else []
    return max(96.0, 22 + len(title_lines) * 28 + len(subtitle_lines) * 20 + 22), title_lines, subtitle_lines


def _footer_lines(spec: dict[str, Any], width: float) -> list[str]:
    return _wrap(spec.get("footer", ""), max(80.0, width - 2 * MARGIN), 13) if spec.get("footer") else []


def _render_svg(result: dict[str, Any], spec: dict[str, Any], theme: dict[str, Any], header_height: float) -> str:
    width, height = result["width"], result["height"]
    _, title_lines, subtitle_lines = _header_metrics(spec, width)
    title_center = width / 2
    title_tspans = "".join(f'<tspan x="{title_center:.1f}" dy="{0 if index == 0 else 28}">{escape(line)}</tspan>' for index, line in enumerate(title_lines))
    title_y = 34
    subtitle_y = title_y + len(title_lines) * 28 + 2
    subtitle_tspans = "".join(f'<tspan x="{title_center:.1f}" dy="{0 if index == 0 else 20}">{escape(line)}</tspan>' for index, line in enumerate(subtitle_lines))
    feedback_marker_color = theme["text"] if result["theme"] == "monochrome" else "#C0392B"
    font_family = "PingFang SC, Noto Sans CJK SC, Microsoft YaHei, Hiragino Sans GB, STSong, Arial, Helvetica, sans-serif"
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width:.0f}" height="{height:.0f}" viewBox="0 0 {width:.0f} {height:.0f}" role="img" aria-labelledby="diagram-title">', "<defs>", f'<marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill="{theme["text"]}"/></marker>', f'<marker id="arrow-red" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill="{feedback_marker_color}"/></marker>', "</defs>", f'<rect width="100%" height="100%" fill="{theme["canvas"]}"/>', f'<rect x="0" y="0" width="{width:.0f}" height="{header_height:.0f}" fill="{theme["header"]}"/>', f'<text id="diagram-title" x="{title_center:.1f}" y="{title_y}" text-anchor="middle" fill="{theme["header_text"]}" font-family="{font_family}" font-size="24px" font-weight="700">{title_tspans}</text>']
    if subtitle_lines:
        parts.append(f'<text x="{title_center:.1f}" y="{subtitle_y}" text-anchor="middle" fill="{theme["header_text"]}" opacity="0.82" font-family="{font_family}" font-size="16px">{subtitle_tspans}</text>')
    for group in result["groups"]:
        role = theme["roles"][group["role"]]
        dash = "6 5" if group["kind"] in {"zone", "lane"} else "10 6"
        title_lines = group.get("title_lines", [group["title"]])
        tspans = "".join(f'<tspan x="{group["x"] + 14:.1f}" dy="{0 if index == 0 else 18}">{escape(line)}</tspan>' for index, line in enumerate(title_lines))
        parts.append(f'<g data-group-id="{escape(group["id"], quote=True)}"><rect x="{group["x"]:.1f}" y="{group["y"]:.1f}" width="{group["width"]:.1f}" height="{group["height"]:.1f}" rx="10" fill="{role["fill"]}" fill-opacity="0.28" stroke="{theme["group"]}" stroke-width="1.5" stroke-dasharray="{dash}"/><text x="{group["x"] + 14:.1f}" y="{group["y"] + 22:.1f}" fill="{role["stroke"]}" font-family="{font_family}" font-size="14px" font-weight="700">{tspans}</text></g>')
    for edge in result["edges"]:
        feedback_color = theme["text"] if result["theme"] == "monochrome" else "#C0392B"
        color = feedback_color if edge["kind"] == "feedback" else theme["text"]
        dash = ' stroke-dasharray="8 6"' if edge["kind"] in {"feedback", "dashed"} else ""
        marker = "arrow-red" if edge["kind"] == "feedback" and result["theme"] != "monochrome" else "arrow"
        if edge.get("leader_points"):
            parts.append(f'<path d="{_path(edge["leader_points"])}" fill="none" stroke="{theme["grid"]}" stroke-width="1.2" data-edge-label-leader="{edge["id"]}"/>')
        parts.append(f'<path d="{_path(edge["points"])}" fill="none" stroke="{color}" stroke-width="2"{dash} marker-end="url(#{marker})" data-edge-id="{edge["id"]}"/>')
        if edge.get("label_box"):
            box = edge["label_box"]
            label_lines = box.get("lines", [edge["label"]])
            tspans = "".join(f'<tspan x="{box["x"] + box["width"] / 2:.1f}" dy="{0 if index == 0 else 18}">{escape(line)}</tspan>' for index, line in enumerate(label_lines))
            parts.append(f'<rect x="{box["x"]:.1f}" y="{box["y"]:.1f}" width="{box["width"]:.1f}" height="{box["height"]:.1f}" rx="4" fill="{theme["canvas"]}" stroke="{theme["grid"]}"/><text x="{box["x"] + box["width"] / 2:.1f}" y="{box["y"] + 18:.1f}" text-anchor="middle" fill="{theme["text"]}" font-family="{font_family}" font-size="13px">{tspans}</text>')
    if spec.get("layout") == "sequence":
        for node in result["nodes"]:
            x = node["x"] + node["width"] / 2
            parts.append(f'<path d="M {x:.1f} {node["y"] + node["height"]:.1f} L {x:.1f} {height - 28:.1f}" stroke="{theme["grid"]}" stroke-width="1.5" stroke-dasharray="5 5"/>')
    parts.extend(_svg_node(node, theme) for node in result["nodes"])
    footer_lines = _footer_lines(spec, width)
    if footer_lines:
        footer_tspans = "".join(f'<tspan x="{MARGIN}" dy="{0 if index == 0 else 18}">{escape(line)}</tspan>' for index, line in enumerate(footer_lines))
        parts.append(f'<text x="{MARGIN}" y="{height - 15 - (len(footer_lines) - 1) * 18:.1f}" fill="{theme["muted"]}" font-family="{font_family}" font-size="13px">{footer_tspans}</text>')
    parts.append("</svg>")
    return "".join(parts)


def _prepare_groups(raw_groups: list[dict[str, Any]], nodes: list[dict[str, Any]], layout: str | None = None) -> list[dict[str, Any]]:
    by_id = {node["id"]: node for node in nodes}
    groups: list[dict[str, Any]] = []
    lane_bounds: tuple[float, float] | None = None
    if layout == "swimlane" and any(raw.get("kind", "zone") == "lane" for raw in raw_groups):
        all_top = min(node["y"] for node in nodes)
        all_bottom = max(node["y"] + node["height"] for node in nodes)
        lane_title_lines = []
        for raw in raw_groups:
            if raw.get("kind", "zone") == "lane" and raw.get("title"):
                members = [by_id[member] for member in raw["members"]]
                x0 = min(node["x"] for node in members) - 22
                x1 = max(node["x"] + node["width"] for node in members) + 22
                lane_title_lines.append(len(_wrap(raw["title"], max(50.0, x1 - x0 - 28), 14)))
        max_title_lines = max(lane_title_lines, default=1)
        lane_bounds = (all_top - (34 + max(0, max_title_lines - 1) * 18), all_bottom + 22)
    for raw in raw_groups:
        members = [by_id[member] for member in raw["members"]]
        x0 = min(node["x"] for node in members) - 22
        x1 = max(node["x"] + node["width"] for node in members) + 22
        y1 = max(node["y"] + node["height"] for node in members) + 22
        title = raw.get("title", "")
        title_lines = _wrap(title, max(50.0, x1 - x0 - 28), 14) if title else []
        if lane_bounds is not None and raw.get("kind", "zone") == "lane":
            y0, y1 = lane_bounds
        else:
            y0 = min(node["y"] for node in members) - (34 + max(0, len(title_lines) - 1) * 18)
        groups.append({"id": raw["id"], "title": title, "title_lines": title_lines, "kind": raw.get("kind", "zone"), "role": raw.get("role", "neutral"), "members": list(raw["members"]), "x": x0, "y": y0, "width": x1 - x0, "height": y1 - y0})
    return groups


def render_svg(spec: dict, theme: str | None = None) -> dict:
    """Render a validated diagram and return SVG plus geometry QA metadata."""
    if not isinstance(spec, dict):
        raise SpecError("spec must be an object")
    chosen = theme if theme is not None else spec.get("theme", "reference")
    nodes = _validate(spec, chosen)
    width = float(spec.get("width", 900))
    edges_raw = spec.get("edges", [])
    layout = spec["layout"]
    has_groups = bool(spec.get("groups"))
    gap_x = 56.0 if has_groups else 36.0
    gap_y = 76.0 if has_groups else 40.0
    if layout in {"network", "parallel"}:
        # Reserve enough horizontal channel for ordinary edge labels in
        # column-oriented diagrams.  Longer labels are capped here and use
        # the existing safe side-channel/leader fallback instead of making a
        # sparse network arbitrarily wide.
        label_width = max((min(120.0, max(52.0, len(edge.get("label", "")) * 8.0 + 10.0)) for edge in spec.get("edges", []) if edge.get("label")), default=0.0)
        gap_x = max(gap_x, label_width + 6.0)
    header_height, _, _ = _header_metrics(spec, width)
    footer_height = 20 + max(0, len(_footer_lines(spec, width)) - 1) * 18
    groups: list[dict[str, Any]] = []
    if layout == "sequence":
        nodes, width, edge_meta = _sequence_layout(nodes, edges_raw, width, header_height, gap_x)
        message_bottom = max((max(max(point[1] for point in edge["points"]), edge["label_box"]["y"] + edge["label_box"]["height"] if edge["label_box"] else 0) for edge in edge_meta), default=max(node["y"] + node["height"] for node in nodes))
        height = message_bottom + 70 + footer_height
        groups = _prepare_groups(spec.get("groups", []), nodes, layout)
    else:
        cols = max(node["col"] + node["span"] for node in nodes)
        rows = max(node["row"] for node in nodes) + 1
        cell_w = max(150.0, (width - 2 * MARGIN - gap_x * max(0, cols - 1)) / max(1, cols))
        width = max(width, 2 * MARGIN + cols * cell_w + gap_x * max(0, cols - 1))
        for node in nodes:
            node["x"] = MARGIN + node["col"] * (cell_w + gap_x)
            node["width"] = node["span"] * cell_w + max(0, node["span"] - 1) * gap_x
            node["title_lines"], node["description_lines"] = _text_lines(node, node["width"])
            node["height"] = max(66.0, 24 + len(node["title_lines"]) * LINE_HEIGHT + len(node["description_lines"]) * LINE_HEIGHT + 18)
            if node["shape"] == "diamond":
                total_lines = max(1, len(node["title_lines"] + node["description_lines"]))
                # Keep the complete wrapped text stack inside a conservative
                # central rectangle; the diamond's sloping edges narrow at
                # both ends, so rectangle-height sizing is insufficient.
                node["height"] = max(node["height"], 2 * (total_lines * LINE_HEIGHT + 18))
        row_heights: dict[int, float] = {}
        for node in nodes:
            row_heights[node["row"]] = max(row_heights.get(node["row"], 0), node["height"])
        row_y: dict[int, float] = {}
        cursor = header_height + 52
        for row in range(rows):
            row_y[row] = cursor
            cursor += row_heights.get(row, 66.0) + gap_y
        for node in nodes:
            node["y"] = row_y[node["row"]]
        height = cursor + footer_height
        groups = _prepare_groups(spec.get("groups", []), nodes, layout)
        # Explicit right-side feedback tracks need room for their label boxes.
        # Keep the grid width (and therefore node geometry) stable, then
        # extend only the SVG canvas so a long feedback label can sit outside
        # the rightmost node instead of being rejected or overlapping it.
        canvas_width = width
        rightmost = max((node["x"] + node["width"] for node in nodes), default=width - MARGIN)
        for raw in edges_raw:
            if raw.get("route", "auto") == "right" and raw.get("label"):
                estimated_label_width = min(260.0, max(52.0, len(raw["label"]) * 8.0 + 10.0))
                # Ordinary short labels fit beside the existing perimeter
                # track.  Reserve a side lane only when the label itself is
                # wide enough that local slots cannot be safe.
                if estimated_label_width > 70.0:
                    canvas_width = max(canvas_width, rightmost + estimated_label_width + MARGIN + 16)
        width = canvas_width
        by_id = {node["id"]: node for node in nodes}
        edge_meta = []
        label_obstacles = [_rect(node) for node in nodes]
        group_title_obstacles: list[tuple[float, float, float, float]] = []
        for group in groups:
            # Only swimlane lane headers reserve routing space.  Bands and
            # zones in other layouts deliberately keep their historical
            # routing behavior; their title is outside the process channel.
            if layout != "swimlane" or group.get("kind") != "lane":
                continue
            title_height = max(18, len(group.get("title_lines", [])) * 18 + 8)
            title_obstacle = (group["x"] + 8, group["y"] + 8, group["x"] + group["width"] - 8, group["y"] + title_height)
            group_title_obstacles.append(title_obstacle)
            label_obstacles.append(title_obstacle)
        routed_edges: list[tuple[dict[str, Any], list[tuple[float, float]]]] = []
        for index, raw in enumerate(edges_raw):
            source, target = by_id[raw["from"]], by_id[raw["to"]]
            points, safe = _route_orthogonal(source, target, nodes, width, height, raw.get("route", "auto"), header_height, layout, group_title_obstacles)
            if not safe:
                raise SpecError(f"unsafe routing for edge {index} ({source['id']} -> {target['id']})")
            routed_edges.append((raw, points))
        all_routes = [points for _, points in routed_edges]
        for index, (raw, points) in enumerate(routed_edges):
            preferred_segments = _preferred_segments(index, all_routes)
            label_box = _label_box(points, raw.get("label", ""), width, height, label_obstacles, header_height, preferred_segments)
            if label_box:
                label_obstacles.append((label_box["x"], label_box["y"], label_box["x"] + label_box["width"], label_box["y"] + label_box["height"]))
            edge_meta.append({"id": f"edge-{index}", "from": raw["from"], "to": raw["to"], "label": raw.get("label", ""), "kind": raw.get("kind", "normal"), "route": raw.get("route", "auto"), "points": points, "path": _path(points), "safe": True, "label_box": label_box, "preferred_segments": preferred_segments})
    # Labels that must live in a side channel remain explicitly connected to
    # their own polyline.  Leaders are computed after all label boxes exist so
    # they also avoid labels belonging to neighboring edges.
    node_obstacles = [_rect(node) for node in nodes]
    for group in groups:
        if layout != "swimlane" or group.get("kind") != "lane":
            continue
        title_height = max(18, len(group.get("title_lines", [])) * 18 + 8)
        node_obstacles.append((group["x"] + 8, group["y"] + 8, group["x"] + group["width"] - 8, group["y"] + title_height))
    all_boxes = [edge["label_box"] for edge in edge_meta if edge.get("label_box")]
    for edge in edge_meta:
        box = edge.get("label_box")
        if not box or _label_distance(edge["points"], box) <= 24.0:
            continue
        other_boxes = [(item["x"], item["y"], item["x"] + item["width"], item["y"] + item["height"]) for item in all_boxes if item is not box]
        leader = _leader_path(edge["points"], box, node_obstacles + other_boxes, edge.get("preferred_segments"))
        if leader is None:
            raise SpecError(f"cannot connect edge label safely: {edge['label'][:40]}")
        edge["leader_points"] = leader
    fit_scale = min(453.5 / width, 652.0 / height)
    min_font_pt = 16.0 * fit_scale
    warnings: list[str] = []
    if min_font_pt < 8.0:
        warnings.append(f"A4 版心缩放后最小正文约 {min_font_pt:.1f}pt，小于 8pt；请拆分总览与局部图")
    scaled_height = height * (453.5 / width)
    if scaled_height > 652.0:
        scaled_height_cm = scaled_height * 2.54 / 72.0
        warnings.append(f"A4 缩放后图高约 {scaled_height:.0f}pt（{scaled_height_cm:.1f}cm），超过 23cm 版心；建议拆分总览与局部图")
    result: dict[str, Any] = {"svg": "", "width": round(width, 2), "height": round(height, 2), "theme": chosen, "layout": layout, "nodes": nodes, "edges": edge_meta, "groups": groups, "warnings": warnings}
    result["svg"] = _render_svg(result, spec, THEMES[chosen], header_height)
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Render an enterprise diagram JSON spec to standalone SVG")
    parser.add_argument("--source", required=True, help="JSON diagram spec")
    parser.add_argument("--out", required=True, help="SVG output path")
    parser.add_argument("--theme", choices=sorted(THEMES), help="theme override")
    args = parser.parse_args(argv)
    source_path = Path(args.source)
    output_path = Path(args.out)
    if output_path.suffix.lower() != ".svg":
        parser.error("--out must be an .svg path")
    try:
        spec = json.loads(source_path.read_text(encoding="utf-8"))
        result = render_svg(spec, args.theme)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("x", encoding="utf-8") as output_file:
            output_file.write(result["svg"])
    except FileExistsError:
        parser.error(f"refusing to overwrite existing output: {output_path}")
    except (OSError, json.JSONDecodeError, SpecError) as exc:
        parser.error(str(exc))
    metadata = {key: value for key, value in result.items() if key != "svg"}
    print(json.dumps(metadata, ensure_ascii=False, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
