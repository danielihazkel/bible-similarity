import pandas as pd
import pytest

from bsim.data.canon import BY_SEFARIA
from bsim.data.refs import Ref, RefIndex, parse_range, parse_ref


@pytest.mark.parametrize(
    ("ref", "expected"),
    [
        ("Genesis 1:1", ("Genesis", 1, 1, 1, 1)),
        ("Genesis 1:1-6", ("Genesis", 1, 1, 1, 6)),
        ("Genesis 1:1-6:8", ("Genesis", 1, 1, 6, 8)),
        ("Genesis 23", ("Genesis", 23, None, 23, None)),
        ("Judges 4-5", ("Judges", 4, None, 5, None)),
        ("Song of Songs 2:3-5", ("Song of Songs", 2, 3, 2, 5)),
        ("I Samuel 17", ("I Samuel", 17, None, 17, None)),
        ("II Chronicles 3:1-4:2", ("II Chronicles", 3, 1, 4, 2)),
        ("  Psalms 18:2 ", ("Psalms", 18, 2, 18, 2)),
    ],
)
def test_parse_ref_forms(ref, expected):
    book, c1, v1, c2, v2 = expected
    assert parse_ref(ref) == Ref(BY_SEFARIA[book], c1, v1, c2, v2)


@pytest.mark.parametrize(
    "ref",
    [
        "Rashi on Genesis 1:1",  # not a canon book
        "Genesis 1:2:3",  # three-level (commentary) ref
        "Genesis 2:5-3",  # end before start
        "Genesis 5-3",
        "Genesis 4-5:2",
        "Genesis",
        "Genesis 1:a",
        "",
    ],
)
def test_parse_ref_rejects(ref):
    with pytest.raises(ValueError):
        parse_ref(ref)


def test_parse_range_requires_verses():
    assert parse_range("Judges 4:1-5:2")[1:] == ((4, 1), (5, 2))
    with pytest.raises(ValueError):
        parse_range("Judges 4-5")


def _index() -> RefIndex:
    # Genesis 1 (3 verses), Genesis 2 (2 verses), Exodus 1 (4 verses)
    rows = [(0, 1, v) for v in range(1, 4)] + [(0, 2, v) for v in (1, 2)]
    rows += [(1, 1, v) for v in range(1, 5)]
    verses = pd.DataFrame(
        [(i, b, c, v) for i, (b, c, v) in enumerate(rows)],
        columns=["verse_id", "book_id", "chapter", "verse"],
    )
    return RefIndex(verses)


def test_resolve():
    idx = _index()
    assert idx.resolve("Genesis 1:2") == (1, 1)
    assert idx.resolve("Genesis 1:2-2:1") == (1, 3)
    assert idx.resolve("Genesis 1") == (0, 2)
    assert idx.resolve("Genesis 1-2") == (0, 4)
    assert idx.resolve("Exodus 1:3-4") == (7, 8)
    assert idx.resolve(parse_ref("Exodus 1")) == (5, 8)


@pytest.mark.parametrize(
    "ref", ["Genesis 21:2047-2073", "Genesis 1:2-9", "Genesis 3", "Exodus 1:5", "Exodus 1-2"]
)
def test_resolve_rejects_missing_verses(ref):
    with pytest.raises(ValueError):
        _index().resolve(ref)
