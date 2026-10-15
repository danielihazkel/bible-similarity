"""The base map under the places (DESIGN.md §16.57): Natural Earth's land, lakes and rivers
(public domain, 1:10m), clipped to the region and simplified, small enough to send once.

Plain geometry, no GIS library: a polygon ring is clipped to the box by Sutherland–Hodgman (the
box is convex), a line is cut where it leaves the box, and both are thinned by Douglas–Peucker
at `tolerance` degrees, then rounded to `digits` decimals. Rings smaller than `min_area` square
degrees are dropped. Coordinates stay longitude / latitude; the viewer projects them.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import numpy as np

Box = tuple[float, float, float, float]  # lon_min, lat_min, lon_max, lat_max
Path_ = list[tuple[float, float]]


def clip_ring(ring: Path_, box: Box) -> Path_:
    """A polygon ring clipped to the box (Sutherland–Hodgman); empty when it lies outside."""
    x0, y0, x1, y1 = box
    edges = [
        (lambda p: p[0] >= x0, lambda a, b: _at_x(a, b, x0)),
        (lambda p: p[0] <= x1, lambda a, b: _at_x(a, b, x1)),
        (lambda p: p[1] >= y0, lambda a, b: _at_y(a, b, y0)),
        (lambda p: p[1] <= y1, lambda a, b: _at_y(a, b, y1)),
    ]
    out = list(ring)
    for inside, cross in edges:
        if not out:
            break
        src, out = out, []
        prev = src[-1]
        for p in src:
            if inside(p):
                if not inside(prev):
                    out.append(cross(prev, p))
                out.append(p)
            elif inside(prev):
                out.append(cross(prev, p))
            prev = p
    return out


def _at_x(a: tuple[float, float], b: tuple[float, float], x: float) -> tuple[float, float]:
    t = (x - a[0]) / (b[0] - a[0])
    return x, a[1] + t * (b[1] - a[1])


def _at_y(a: tuple[float, float], b: tuple[float, float], y: float) -> tuple[float, float]:
    t = (y - a[1]) / (b[1] - a[1])
    return a[0] + t * (b[0] - a[0]), y


def clip_line(line: Path_, box: Box) -> list[Path_]:
    """The pieces of a line inside the box (each cut where it leaves, closed where it enters)."""
    x0, y0, x1, y1 = box

    def inside(p: tuple[float, float]) -> bool:
        return x0 <= p[0] <= x1 and y0 <= p[1] <= y1

    pieces: list[Path_] = []
    cur: Path_ = []
    for a, b in zip(line, line[1:], strict=False):
        seg = _clip_segment(a, b, box)
        if seg is None:
            if cur:
                pieces.append(cur)
                cur = []
            continue
        p, q = seg
        if not cur:
            cur = [p]
        cur.append(q)
        if not inside(b):
            pieces.append(cur)
            cur = []
    if cur:
        pieces.append(cur)
    return [p for p in pieces if len(p) > 1]


def _clip_segment(
    a: tuple[float, float], b: tuple[float, float], box: Box
) -> tuple[tuple[float, float], tuple[float, float]] | None:
    """Liang–Barsky: the part of segment a-b inside the box, or None."""
    x0, y0, x1, y1 = box
    dx, dy = b[0] - a[0], b[1] - a[1]
    t0, t1 = 0.0, 1.0
    for p, q in ((-dx, a[0] - x0), (dx, x1 - a[0]), (-dy, a[1] - y0), (dy, y1 - a[1])):
        if p == 0:
            if q < 0:
                return None
            continue
        t = q / p
        if p < 0:
            t0 = max(t0, t)
        else:
            t1 = min(t1, t)
        if t0 > t1:
            return None
    return (a[0] + t0 * dx, a[1] + t0 * dy), (a[0] + t1 * dx, a[1] + t1 * dy)


def simplify(points: Path_, tolerance: float) -> Path_:
    """Douglas–Peucker: the points a polyline keeps when none dropped is further than `tolerance`
    from the line kept."""
    if len(points) < 3 or tolerance <= 0:
        return list(points)
    pts = np.asarray(points, dtype=float)
    keep = np.zeros(len(pts), dtype=bool)
    keep[0] = keep[-1] = True
    stack = [(0, len(pts) - 1)]
    while stack:
        i, j = stack.pop()
        if j <= i + 1:
            continue
        a, b = pts[i], pts[j]
        seg = pts[i + 1 : j]
        d = b - a
        norm = float(np.hypot(*d))
        if norm == 0:
            dist = np.hypot(*(seg - a).T)
        else:
            dist = np.abs(d[0] * (seg[:, 1] - a[1]) - d[1] * (seg[:, 0] - a[0])) / norm
        k = int(np.argmax(dist))
        if dist[k] > tolerance:
            keep[i + 1 + k] = True
            stack += [(i, i + 1 + k), (i + 1 + k, j)]
    return [tuple(p) for p in pts[keep]]  # type: ignore[misc]


def ring_area(ring: Path_) -> float:
    """Unsigned area (square degrees) by the shoelace formula."""
    if len(ring) < 3:
        return 0.0
    x, y = np.asarray(ring, dtype=float).T
    return float(abs(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1))) / 2)


def _features(path: Path) -> Iterator[dict[str, Any]]:
    yield from json.loads(path.read_text(encoding="utf-8"))["features"]


def _parts(geom: dict[str, Any]) -> Iterator[list[Path_]]:
    """A geometry's polygons (lists of rings) or lines (one path each, as a one-ring list)."""
    kind, coords = geom["type"], geom["coordinates"]
    if kind == "Polygon":
        yield coords
    elif kind == "MultiPolygon":
        yield from coords
    elif kind == "LineString":
        yield [coords]
    elif kind == "MultiLineString":
        for line in coords:
            yield [line]


def shapes(
    path: Path,
    layer: str,
    box: Box,
    tolerance: float,
    digits: int,
    min_area: float,
    max_rank: int | None = None,
) -> list[dict[str, Any]]:
    """One layer's shapes inside the box: `layer, name, rank, rings` (each ring a list of
    [lon, lat]; for lines, each ring is a piece of the line). Features ranked above `max_rank`
    (Natural Earth's `scalerank`: higher is less important) are left out."""
    out = []
    lines = layer == "rivers"
    for f in _features(path):
        props = f.get("properties") or {}
        rank = props.get("scalerank")
        if max_rank is not None and rank is not None and rank > max_rank:
            continue
        rings: list[Path_] = []
        for part in _parts(f["geometry"] or {"type": "None", "coordinates": []}):
            for ring in part:
                pts = [(float(p[0]), float(p[1])) for p in ring]
                if lines:
                    pieces = clip_line(pts, box)
                else:
                    clipped = clip_ring(pts, box)
                    pieces = [clipped] if ring_area(clipped) >= min_area else []
                for piece in pieces:
                    s = simplify(piece, tolerance)
                    s = [(round(x, digits), round(y, digits)) for x, y in s]
                    s = [p for i, p in enumerate(s) if i == 0 or p != s[i - 1]]
                    if len(s) >= (2 if lines else 4):
                        rings.append(s)
        if rings:
            name = props.get("name") or props.get("name_en") or ""
            out.append({"layer": layer, "name": str(name), "rank": rank, "rings": rings})
    return out
