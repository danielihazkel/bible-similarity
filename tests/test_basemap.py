"""The base map's geometry (`data/basemap.py`, DESIGN.md §16.57)."""

import pytest

from bsim.data.basemap import clip_line, clip_ring, ring_area, simplify

BOX = (0.0, 0.0, 10.0, 10.0)


def test_clip_ring():
    inside = [(1, 1), (2, 1), (2, 2), (1, 1)]
    assert clip_ring(inside, BOX) == inside
    assert clip_ring([(20, 20), (30, 20), (30, 30)], BOX) == []
    # a square half outside: cut along the box edge
    half = clip_ring([(5, 2), (15, 2), (15, 4), (5, 4)], BOX)
    assert sorted(set(half)) == [(5, 2), (5, 4), (10.0, 2.0), (10.0, 4.0)]
    assert ring_area(half) == pytest.approx(10.0)


def test_clip_line():
    # in, out and back in: two pieces, each cut at the edge
    pieces = clip_line([(5, 5), (15, 5), (15, 8), (5, 8)], BOX)
    assert pieces == [[(5, 5), (10.0, 5.0)], [(10.0, 8.0), (5, 8)]]
    assert clip_line([(20, 20), (30, 30)], BOX) == []
    # crossing the box without a point inside
    assert clip_line([(-5, 5), (15, 5)], BOX) == [[(0.0, 5.0), (10.0, 5.0)]]


def test_simplify():
    line = [(0, 0), (1, 0.01), (2, -0.01), (3, 0), (4, 2), (5, 0)]
    assert simplify(line, 0.1) == [(0, 0), (3, 0), (4, 2), (5, 0)]
    assert simplify(line, 0) == line
    assert simplify([(0, 0), (1, 1)], 1.0) == [(0, 0), (1, 1)]
