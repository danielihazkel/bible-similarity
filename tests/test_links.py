import json

import numpy as np
import pandas as pd
import pytest

from bsim.config import load_config, resolve_path
from bsim.data.canon import BY_SEFARIA
from bsim.data.links import (
    SPLITS,
    _book_pair_counts,
    _fractions,
    _max_book_share,
    assign_split,
    build_links,
    check_leakage,
    expand,
    split_books,
)
from bsim.data.refs import RefIndex

TOY_BOOKS = ["Genesis", "Exodus", "II Samuel", "Psalms"]  # chapter 1, 10 verses each


def _toy() -> tuple[RefIndex, np.ndarray]:
    rows = [(BY_SEFARIA[name].book_id, 1, v) for name in TOY_BOOKS for v in range(1, 11)]
    verses = pd.DataFrame(
        [(i, *r) for i, r in enumerate(rows)], columns=["verse_id", "book_id", "chapter", "verse"]
    )
    return RefIndex(verses), verses.book_id.to_numpy()


def _vid(name: str, v: int) -> int:
    return TOY_BOOKS.index(name) * 10 + v - 1


def _build(*links: tuple[str, str] | tuple[str, str, str]):
    rows = pd.DataFrame(
        [(r[0], r[1], r[2] if len(r) > 2 else "") for r in links],
        columns=["ref1", "ref2", "connection_type"],
    )
    index, book_ids = _toy()
    return build_links(rows, index, book_ids, cartesian_max=3, window=2)


def _pairs(df: pd.DataFrame, level: str = "verse") -> set[tuple[int, int]]:
    d = df[df.level == level]
    return set(zip(d.src_vid, d.tgt_vid, strict=True))


def test_expand_rules():
    assert expand(0, 2, 10, 12, 3) == ("positional", [(0, 10), (1, 11), (2, 12)])
    assert expand(0, 0, 10, 12, 3) == ("cartesian", [(0, 10), (0, 11), (0, 12)])
    assert expand(0, 1, 10, 14, 3) == ("unit", [])


def test_positional_parallel_both_directions():
    df, stats = _build(("II Samuel 1:1-5", "Psalms 1:2-6"))
    expected = {(_vid("II Samuel", v), _vid("Psalms", v + 1)) for v in range(1, 6)}
    assert _pairs(df) == expected | {(b, a) for a, b in expected}
    assert set(df.rule) == {"positional"}
    assert stats.rules == {"positional": 1}
    assert (df.src_end_vid == df.src_vid).all() and (df.tgt_end_vid == df.tgt_vid).all()


def test_cartesian_small_ranges():
    df, _ = _build(("Genesis 1:1", "Exodus 1:2-4"))
    g = _vid("Genesis", 1)
    assert {p for p in _pairs(df) if p[0] == g} == {(g, _vid("Exodus", v)) for v in (2, 3, 4)}
    assert len(df) == 6


def test_unit_level_link_keeps_ranges():
    df, stats = _build(("Genesis 1:1-2", "Exodus 1:1-5"))
    assert stats.rules == {"unit": 1}
    assert _pairs(df) == set()
    unit = df[df.level == "unit"].set_index("src_vid")
    g, e = _vid("Genesis", 1), _vid("Exodus", 1)
    assert tuple(unit.loc[g, ["tgt_vid", "src_end_vid", "tgt_end_vid"]]) == (e, g + 1, e + 4)
    assert tuple(unit.loc[e, ["tgt_vid", "src_end_vid", "tgt_end_vid"]]) == (g, e + 4, g + 1)


def test_self_and_neighbour_pairs_dropped():
    df, stats = _build(
        ("Genesis 1:5", "Genesis 1:5"),  # self
        ("Genesis 1:1", "Genesis 1:3"),  # within ±2
        ("Genesis 1:1", "Genesis 1:4"),  # kept
        ("Genesis 1:10", "Exodus 1:1"),  # adjacent ids, different books: kept
        ("Genesis 1:1-5", "Genesis 1:3-9"),  # overlapping unit link
    )
    assert stats.self_pairs == 1
    assert stats.near_pairs == 1
    assert stats.unit_overlap == 1
    assert _pairs(df) == {
        (_vid("Genesis", 1), _vid("Genesis", 4)),
        (_vid("Genesis", 4), _vid("Genesis", 1)),
        (_vid("Genesis", 10), _vid("Exodus", 1)),
        (_vid("Exodus", 1), _vid("Genesis", 10)),
    }


def test_symmetric_and_deduplicated():
    df, _ = _build(
        ("Genesis 1:1", "Psalms 1:1", "related"),
        ("Psalms 1:1", "Genesis 1:1", "quotation"),
        ("Genesis 1:1", "Psalms 1:1"),
        ("Genesis 1:7-8", "Exodus 1:2-3"),
        ("Genesis 1:7", "Exodus 1:2"),  # same pair via positional and the line above
    )
    assert not df.duplicated(["src_vid", "tgt_vid", "level"]).any()
    assert _pairs(df) == {(b, a) for a, b in _pairs(df)}
    row = df[(df.src_vid == _vid("Psalms", 1)) & (df.tgt_vid == _vid("Genesis", 1))]
    assert row.connection_type.tolist() == ["quotation,related"]


def test_invalid_refs_reported():
    df, stats = _build(("Genesis 1:99", "Exodus 1:1"), ("Genesis 1:1", "Exodus 3"))
    assert df.empty
    assert stats.invalid == ["Genesis 1:99", "Exodus 3"]


def test_assign_split_precedence():
    assign = np.array([0, 1, 2])  # book 0 train, 1 dev, 2 test
    out = assign_split(np.array([0, 0, 1, 2, 0]), np.array([0, 1, 2, 1, 2]), assign)
    assert out.tolist() == ["train", "dev", "test", "test", "test"]


def _synthetic_counts(seed: int = 0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    m = np.triu(rng.poisson(3, (39, 39)) * (rng.random((39, 39)) < 0.3))
    m[:5, :5] *= 8  # a few heavy "Torah" books, as in the real data
    return m


def test_split_books_deterministic_and_balanced():
    m = _synthetic_counts()
    ratios = {"train": 0.75, "dev": 0.10, "test": 0.15}
    a1, f1 = split_books(m, ratios, seed=13, restarts=5, max_book_share=0.35)
    a2, f2 = split_books(m, ratios, seed=13, restarts=5, max_book_share=0.35)
    assert a1.tolist() == a2.tolist()
    assert np.allclose(f1, _fractions(m, a1)) and np.allclose(f1, f2)
    assert np.abs(f1 - [0.75, 0.10, 0.15]).max() < 0.02
    assert {1, 2} <= set(a1.tolist())
    assert (_max_book_share(m, a1)[1:] <= 0.35 + 0.02).all()


def test_no_train_link_touches_dev_or_test_book():
    df, _ = _build(
        ("Genesis 1:1", "Exodus 1:5"),
        ("Genesis 1:2-3", "Psalms 1:4-5"),
        ("II Samuel 1:1", "Psalms 1:9"),
        ("Genesis 1:6", "Genesis 1:9"),
        ("Exodus 1:1-2", "II Samuel 1:1-6"),  # unit level
    )
    _, book_ids = _toy()
    assign = np.zeros(39, dtype=np.int64)
    assign[BY_SEFARIA["Exodus"].book_id] = 1
    assign[BY_SEFARIA["Psalms"].book_id] = 2
    df["split"] = assign_split(
        book_ids[df.src_vid.to_numpy()], book_ids[df.tgt_vid.to_numpy()], assign
    )
    check_leakage(df, book_ids, assign)
    train = df[df.split == "train"]
    assert set(book_ids[train.src_vid]) | set(book_ids[train.tgt_vid]) <= {
        BY_SEFARIA["Genesis"].book_id,
        BY_SEFARIA["II Samuel"].book_id,
    }
    assert set(df.split) == set(SPLITS)

    df.loc[df.split == "dev", "split"] = "train"
    with pytest.raises(RuntimeError):
        check_leakage(df, book_ids, assign)


def test_built_links_have_no_leakage():
    """Same check on the real artifact, if `bsim build-links` has been run."""
    out = resolve_path(load_config(), "data_processed")
    if not (out / "links.parquet").exists():
        pytest.skip("links.parquet not built")
    links = pd.read_parquet(out / "links.parquet")
    verses = pd.read_parquet(out / "verses.parquet", columns=["verse_id", "book_id"])
    book_ids = verses.sort_values("verse_id").book_id.to_numpy()
    books = json.loads((out / "splits.json").read_text(encoding="utf-8"))["books"]
    assign = np.zeros(39, dtype=np.int64)
    for name, split in books.items():
        assign[BY_SEFARIA[name].book_id] = SPLITS.index(split)
    check_leakage(links, book_ids, assign)
    expected = assign_split(
        book_ids[links.src_vid.to_numpy()], book_ids[links.tgt_vid.to_numpy()], assign
    )
    assert (links.split.to_numpy() == expected).all()
    assert {"dev", "test"} <= set(links[links.level == "verse"].split)
    m = _book_pair_counts(links, book_ids)
    assert m.sum() == ((links.level == "verse") & (links.src_vid < links.tgt_vid)).sum()
