"""The served DB's key lookups search an index, never scan a big table (§10, M106).

The fixture DB has a handful of rows, so its `sqlite_stat1` would let the planner scan; with the
statistics removed the planner assumes large tables, as the real DB's are.
"""

import sqlite3

import pytest

from bsim.api.queries import core
from bsim.api.queries.common import _span_book


@pytest.fixture
def conn(built):
    _, db = built
    c = sqlite3.connect(db)
    c.execute("DELETE FROM sqlite_stat1")
    c.commit()
    c.close()
    c = sqlite3.connect(db)
    yield c
    c.close()


def plan(conn: sqlite3.Connection, sql: str, args) -> list[str]:
    return [r[3] for r in conn.execute(f"EXPLAIN QUERY PLAN {sql}", list(args))]


def scans(conn, sql, args) -> list[str]:
    big = ("verses", "discoveries", "words", "matches")
    return [p for p in plan(conn, sql, args) if p.startswith("SCAN ") and p.split()[1] in big]


def traced(conn, fn, *args) -> list[tuple[str, list]]:
    """The SQL statements `fn` runs, with their arguments, for EXPLAIN."""
    seen: list[tuple[str, list]] = []

    class Spy:
        def execute(self, sql, params=()):
            seen.append((sql, list(params)))
            return conn.execute(sql, params)

    fn(Spy(), *args)
    return seen


def test_verse_by_reference(conn):
    for sql, args in traced(conn, core.verse_at, 1, 1, 1):
        assert not scans(conn, sql, args), sql


def test_units_of_a_chapter(conn):
    for sql, args in traced(conn, core.units_of_type, "pericope", 1, 1):
        assert not scans(conn, sql, args), sql


def test_book_span_filter(conn):
    where, args = [], []
    _span_book(where, args, 1, None)
    sql = f"SELECT COUNT(*) FROM words WHERE {' AND '.join(where)}"
    assert not [p for p in plan(conn, sql, args) if p.startswith("SCAN verses")]


@pytest.mark.parametrize("cross", [False, True])
def test_discoveries_of_a_book(conn, cross):
    """Searched by book, not by (unit_type, mode) alone, which reads the whole mode."""
    statements = [s for s in traced(conn, core.discoveries, "verse", "fused", 1, cross, 20, 0)
                  if "discoveries" in s[0]]  # fmt: skip
    assert len(statements) == 2  # the count and the page
    for sql, args in statements:
        steps = plan(conn, sql, args)
        assert not scans(conn, sql, args), steps
        searches = [p for p in steps if p.startswith("SEARCH discoveries")]
        assert any("a_book=?" in p for p in searches), steps
        assert any("b_book=?" in p for p in searches), steps
