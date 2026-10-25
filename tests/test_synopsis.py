"""Parallel sequences chained into synopses (`/synopses`, DESIGN.md §16.74)."""

import pytest
from fastapi.testclient import TestClient

from bsim.api.app import create_app
from bsim.api.synopsis import Chain, chains_of, groups, layout, passages
from bsim.fixture import fixture_encoder


def chain(seq_id, a_book, b_book, pairs):
    return Chain(seq_id, a_book, b_book, pairs)


def run(a, b, n):
    return [(a + i, b + i) for i in range(n)]


def test_chains_of():
    rows = [
        {
            "seq_id": 2,
            "a_book": 0,
            "b_book": 1,
            "direction": "forward",
            "same_chapter": 0,
            "q": 0.01,
            "pairs": [[1, 9, 1.0, 0]],
        },
        {
            "seq_id": 1,
            "a_book": 0,
            "b_book": 1,
            "direction": "forward",
            "same_chapter": 0,
            "q": 0.2,
            "pairs": [[1, 9, 1.0]],
        },
        {
            "seq_id": 3,
            "a_book": 0,
            "b_book": 0,
            "direction": "forward",
            "same_chapter": 1,
            "q": 0.0,
            "pairs": [[1, 2, 1.0]],
        },
        {
            "seq_id": 4,
            "a_book": 0,
            "b_book": 1,
            "direction": "reverse",
            "same_chapter": 0,
            "q": 0.0,
            "pairs": [[1, 9, 1.0]],
        },
    ]
    assert [c.seq_id for c in chains_of(rows, 0.05, False)] == [2]
    assert [c.seq_id for c in chains_of(rows, 0.05, True)] == [2, 3]
    assert chains_of(rows, 0.5, False)[0].pairs == [(1, 9)]


def test_passages_and_groups():
    one = chain(1, 0, 1, run(10, 110, 4))  # 10-13 ~ 110-113
    two = chain(2, 0, 2, run(15, 210, 3))  # 15-17: two verses after the first's side
    far = chain(3, 3, 4, run(310, 410, 4))
    ps = passages([one, two, far], join=1)
    assert [(p.book, p.start, p.end) for p in ps] == [
        (0, 10, 13),
        (0, 15, 17),
        (1, 110, 113),
        (2, 210, 212),
        (3, 310, 313),
        (4, 410, 413),
    ]
    merged = passages([one, two, far], join=2)
    assert (0, 10, 17) in [(p.book, p.start, p.end) for p in merged]
    # a single chain is its ladder, not a synopsis
    assert groups([one, two, far], join=1, min_chains=2) == []
    assert [[c.seq_id for c in g] for g in groups([one, two, far], 2, 2)] == [[1, 2]]


def test_layout_three_witnesses():
    # A (book 5) runs parallel to B and to C: one row per verse of A, three columns
    s = layout([chain(1, 5, 7, run(100, 300, 4)), chain(2, 5, 9, run(100, 500, 4))], join=0)
    assert s.syn_id == 1 and s.seq_ids == [1, 2] and s.lead_book == 5
    assert s.rows == [[100 + i, 300 + i, 500 + i] for i in range(4)]
    assert s.breaks == 0 and s.dropped == 0
    assert not any(any(r) for r in s.reordered)


def test_layout_transitive_and_skipped():
    # A ~ B and B ~ C: A and C meet in B's rows; A skips a verse of B (it has a row of its own)
    ab = chain(1, 1, 2, [(10, 20), (11, 22), (12, 23)])
    bc = chain(2, 2, 3, run(20, 30, 4))
    s = layout([ab, bc], join=0)
    assert s.lead_book == 2  # B: the passage both chains touch
    assert s.rows == [[20, 10, 30], [21, None, 31], [22, 11, 32], [23, 12, 33]]


def test_layout_shared_column_out_of_order():
    # 1 Chr 16 against Psalms 105 and then 96: the psalms share a column, 96 out of its order
    h1 = chain(1, 9, 5, run(500, 300, 3))
    h2 = chain(2, 9, 5, run(503, 200, 3))
    s = layout([h1, h2], join=1)
    assert s.lead_book == 9 and len(s.columns) == 2
    assert [(p.start, p.end) for p in s.columns[1]] == [(300, 302), (200, 202)]
    assert [r[1] for r in s.rows] == [300, 301, 302, 200, 201, 202]
    assert [r[1] for r in s.reordered] == [False] * 3 + [True] + [False] * 2


def test_layout_one_passage_once_a_row():
    # the second chain would put two verses of one passage (10-14) in a row: its pairs left out
    ab = chain(1, 1, 2, run(10, 20, 3))
    ba = chain(2, 2, 1, [(20, 12), (21, 13), (22, 14)])
    s = layout([ab, ba], join=0)
    assert s.dropped == 3
    assert all(sum(v is not None and 10 <= v <= 14 for v in r) <= 1 for r in s.rows)


@pytest.fixture
def client(built):
    cfg, _ = built
    return TestClient(create_app(cfg, encoder=fixture_encoder, log=lambda _: None))


def test_synopses_endpoint(client):
    body = client.get("/api/synopses").json()
    assert body["max_q"] == 0.5
    [s] = body["items"]
    # the fixture's two chains (0-1 ~ 3-4, 1-2 ~ 5) through verse 1; the pair (2, 5) left out
    assert s["syn_id"] == 1 and s["seq_ids"] == [1, 2] and s["dropped"] == 1
    assert [c["book_id"] for c in s["columns"]] == [0, 0, 1] and s["n_rows"] == 3
    assert s["n_aligned"] == 2 and s["columns"][0]["label"]


def test_synopsis_endpoint(client):
    body = client.get("/api/synopses/1").json()
    assert body["base"] == 0
    verses = [[c["verse"] for c in r] for r in body["rows"]]
    assert verses == [[0, 3, None], [1, 4, 5], [2, None, None]]
    first = body["rows"][0]
    # verse 3 marked against verse 0; verse 0 where any column differs
    assert first[1]["marks"] and first[0]["marks"]
    assert set(body["verses"]) == {"0", "1", "2", "3", "4", "5"}
    other = client.get("/api/synopses/1?base=2").json()
    assert other["base"] == 2 and other["rows"][0][1]["marks"] == {}  # no base verse in that row
    assert client.get("/api/synopses/1?base=3").status_code == 422
    assert client.get("/api/synopses/2").status_code == 404
