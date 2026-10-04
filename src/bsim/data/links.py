"""`bsim build-links`: Sefaria links -> gold verse pairs + book-level splits (DESIGN.md §8.1–8.2).

Writes to `paths.data_processed`:
    links.parquet     src_vid, tgt_vid, src_end_vid, tgt_end_vid, level, rule, connection_type,
                      split
                      (both directions; verse rows have *_end_vid == *_vid, unit rows keep ranges)
    splits.json       book -> split assignment, achieved fractions, config hash
    links_report.md   counts per split / book / connection type, dropped and invalid refs
"""

from __future__ import annotations

import json
from collections import Counter
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from bsim.config import config_hash, resolve_path
from bsim.data.canon import BOOKS, BY_SEFARIA
from bsim.data.refs import RefIndex
from bsim.data.report import md_table

Log = Callable[[str], None]

SPLITS = ("train", "dev", "test")  # index = precedence: a pair takes the max of its books
_COLS = ["Citation 1", "Citation 2", "Conection Type", "Text 1", "Text 2"]  # sic "Conection"


# --- reading -------------------------------------------------------------------------------


def read_links(paths: Iterable[Path]) -> pd.DataFrame:
    """Rows whose two texts are both canon books (Category "Tanakh" also covers commentaries)."""
    frames = []
    for p in paths:
        df = pd.read_csv(p, usecols=_COLS, dtype=str, keep_default_na=False)
        frames.append(df[df["Text 1"].isin(BY_SEFARIA) & df["Text 2"].isin(BY_SEFARIA)])
    if not frames:
        raise RuntimeError("no links*.csv files found")
    out = pd.concat(frames, ignore_index=True)
    return out.rename(
        columns={"Citation 1": "ref1", "Citation 2": "ref2", "Conection Type": "connection_type"}
    )[["ref1", "ref2", "connection_type"]]


# --- expansion -----------------------------------------------------------------------------


def expand(
    s1: int, e1: int, s2: int, e2: int, cartesian_max: int
) -> tuple[str, list[tuple[int, int]]]:
    """(rule, verse pairs): positional for equal lengths, Cartesian for small ranges, else unit."""
    n1, n2 = e1 - s1 + 1, e2 - s2 + 1
    if n1 == n2:
        return "positional", [(s1 + i, s2 + i) for i in range(n1)]
    if n1 <= cartesian_max and n2 <= cartesian_max:
        return "cartesian", [(a, b) for a in range(s1, e1 + 1) for b in range(s2, e2 + 1)]
    return "unit", []


def is_near(a: int, b: int, book_ids: np.ndarray, window: int) -> bool:
    """Same book and within ±window verses (self-pairs included)."""
    return bool(book_ids[a] == book_ids[b]) and abs(a - b) <= window


@dataclass
class LinkStats:
    rows: int = 0
    invalid: list[str] = field(default_factory=list)
    rules: Counter[str] = field(default_factory=Counter)
    self_pairs: int = 0
    near_pairs: int = 0
    unit_overlap: int = 0


def build_links(
    rows: pd.DataFrame,
    index: RefIndex,
    book_ids: np.ndarray,
    cartesian_max: int,
    window: int,
) -> tuple[pd.DataFrame, LinkStats]:
    """Resolve, expand, filter, symmetrize and dedupe link rows (without the split column)."""
    stats = LinkStats(rows=len(rows))
    out: list[tuple[int, int, int, int, str, str, str]] = []
    for ref1, ref2, ctype in rows[["ref1", "ref2", "connection_type"]].itertuples(index=False):
        try:
            s1, e1 = index.resolve(ref1)
        except ValueError:
            stats.invalid.append(ref1)
            continue
        try:
            s2, e2 = index.resolve(ref2)
        except ValueError:
            stats.invalid.append(ref2)
            continue
        rule, pairs = expand(s1, e1, s2, e2, cartesian_max)
        stats.rules[rule] += 1
        if rule == "unit":
            if book_ids[s1] == book_ids[s2] and s1 <= e2 and s2 <= e1:
                stats.unit_overlap += 1
                continue
            out.append((s1, s2, e1, e2, "unit", rule, ctype))
            out.append((s2, s1, e2, e1, "unit", rule, ctype))
            continue
        for a, b in pairs:
            if a == b:
                stats.self_pairs += 1
            elif is_near(a, b, book_ids, window):
                stats.near_pairs += 1
            else:
                out.append((a, b, a, b, "verse", rule, ctype))
                out.append((b, a, b, a, "verse", rule, ctype))

    cols = ["src_vid", "tgt_vid", "src_end_vid", "tgt_end_vid", "level", "rule", "connection_type"]
    df = pd.DataFrame(out, columns=cols)
    keys = cols[:5]
    df = (
        df.groupby(keys, sort=True)
        .agg(
            # positional wins over cartesian when the same pair arises from both
            rule=(
                "rule",
                lambda s: sorted(set(s), key=["positional", "cartesian", "unit"].index)[0],
            ),
            connection_type=("connection_type", lambda s: ",".join(sorted({t for t in s if t}))),
        )
        .reset_index()
    )
    for c in cols[:4]:
        df[c] = df[c].astype("int32")
    return df, stats


# --- splits --------------------------------------------------------------------------------


def _book_pair_counts(links: pd.DataFrame, book_ids: np.ndarray) -> np.ndarray:
    """n_books x n_books counts of undirected verse pairs (upper triangle incl. diagonal)."""
    v = links[(links.level == "verse") & (links.src_vid < links.tgt_vid)]
    a, b = book_ids[v.src_vid.to_numpy()], book_ids[v.tgt_vid.to_numpy()]
    lo, hi = np.minimum(a, b), np.maximum(a, b)
    m = np.zeros((len(BOOKS), len(BOOKS)), dtype=np.int64)
    np.add.at(m, (lo, hi), 1)
    return m


def _split_counts(m: np.ndarray, assign: np.ndarray) -> np.ndarray:
    """Pairs per split; a pair takes the max (test > dev > train) of its two books."""
    pair_split = np.maximum.outer(assign, assign)
    return np.bincount(pair_split.ravel(), weights=m.ravel(), minlength=len(SPLITS))


def _fractions(m: np.ndarray, assign: np.ndarray) -> np.ndarray:
    counts = _split_counts(m, assign)
    return counts / max(counts.sum(), 1)


def _max_book_share(m: np.ndarray, assign: np.ndarray) -> np.ndarray:
    """Per split: the largest share of that split's pairs touching any single one of its books."""
    sym = m + m.T - np.diag(np.diag(m))
    counts = _split_counts(m, assign)
    out = np.zeros(len(SPLITS))
    for s in range(len(SPLITS)):
        books = assign == s
        if counts[s] and books.any():
            # pairs touching book b land in split s iff the other book's split is <= s
            touching = sym[np.ix_(books, assign <= s)].sum(1)
            out[s] = touching.max() / counts[s]
    return out


def split_books(
    m: np.ndarray, ratios: dict[str, float], seed: int, restarts: int, max_book_share: float
) -> tuple[np.ndarray, np.ndarray]:
    """Seeded book assignment balancing pair fractions; returns (assign, fractions).

    `m` holds undirected verse-pair counts per book pair. Loss = L1 distance of the achieved
    pair fractions to `ratios`, plus how far any single book exceeds `max_book_share` of the
    dev or test pairs (so neither is dominated by one book), plus 1 if dev or test is empty.
    Each restart draws a random assignment (books with links ~ `ratios`), then applies
    single-book moves and two-book swaps while they lower the loss; the best restart is kept.
    """
    target = np.array([ratios[s] for s in SPLITS])
    incidence = m.sum(0) + m.sum(1)
    active = np.flatnonzero(incidence)

    def loss(assign: np.ndarray) -> float:
        frac = _fractions(m, assign)
        share = _max_book_share(m, assign)[1:]
        empty = float((_split_counts(m, assign)[1:] == 0).any())
        return float(
            np.abs(frac - target).sum() + np.clip(share - max_book_share, 0, None).sum() + empty
        )

    best: tuple[float, np.ndarray] | None = None
    for r in range(restarts):
        rng = np.random.default_rng(seed + r)
        assign = np.zeros(len(m), dtype=np.int64)
        assign[active] = rng.choice(len(SPLITS), len(active), p=target)
        current = loss(assign)
        improved = True
        while improved:
            improved = False
            for b in rng.permutation(active):
                keep = assign[b]
                for s in range(len(SPLITS)):
                    if s == keep:
                        continue
                    assign[b] = s
                    trial = loss(assign)
                    if trial < current - 1e-12:
                        current, keep, improved = trial, s, True
                assign[b] = keep
            for b in active:
                for c in active:
                    if assign[b] < assign[c]:
                        assign[b], assign[c] = assign[c], assign[b]
                        trial = loss(assign)
                        if trial < current - 1e-12:
                            current, improved = trial, True
                        else:
                            assign[b], assign[c] = assign[c], assign[b]
        if best is None or current < best[0] - 1e-12:
            best = (current, assign.copy())
    assert best is not None
    assign = best[1]
    if (_split_counts(m, assign)[1:] == 0).any():
        raise RuntimeError("book split left dev or test without pairs")
    return assign, _fractions(m, assign)


def assign_split(src_book: np.ndarray, tgt_book: np.ndarray, assign: np.ndarray) -> np.ndarray:
    """Per-pair split name: test if either book is test, else dev if either is dev, else train."""
    return np.array(SPLITS)[np.maximum(assign[src_book], assign[tgt_book])]


def check_leakage(links: pd.DataFrame, book_ids: np.ndarray, assign: np.ndarray) -> None:
    """No train row may touch a dev or test book (on either side, either range end)."""
    train = links[links.split == "train"]
    for col in ("src_vid", "tgt_vid", "src_end_vid", "tgt_end_vid"):
        bad = assign[book_ids[train[col].to_numpy()]] != 0
        if bad.any():
            raise RuntimeError(f"{int(bad.sum())} train links touch a dev/test book ({col})")


# --- report --------------------------------------------------------------------------------


def write_report(
    path: Path,
    cfg: dict[str, Any],
    links: pd.DataFrame,
    stats: LinkStats,
    book_ids: np.ndarray,
    assign: np.ndarray,
    fractions: np.ndarray,
) -> None:
    ratios = cfg["splits"]["ratios"]
    und = links[links.src_vid < links.tgt_vid]
    verse = und[und.level == "verse"]
    unit = und[und.level == "unit"]
    all_verse = links[links.level == "verse"]
    m = _book_pair_counts(links, book_ids)
    shares = _max_book_share(m, assign)

    parts = [
        "# Links report",
        "",
        f"Built {datetime.now(UTC).isoformat(timespec='seconds')}; seed {cfg['seed']}. "
        "Pairs are counted undirected (`links.parquet` stores both directions).",
        "",
        "## Input",
        md_table(
            ["item", "count"],
            [
                ["book↔book link rows", stats.rows],
                ["invalid refs (row dropped)", len(stats.invalid)],
                *[[f"rows expanded as {r}", n] for r, n in sorted(stats.rules.items())],
                ["self pairs dropped", stats.self_pairs],
                [
                    f"same-book pairs within ±{cfg['retrieval']['neighbor_window']} dropped",
                    stats.near_pairs,
                ],
                ["overlapping same-book unit links dropped", stats.unit_overlap],
                ["verse pairs kept", len(verse)],
                ["unit links kept", len(unit)],
            ],
        ),
        "",
        "## Per split",
        md_table(
            [
                "split",
                "books",
                "verse pairs",
                "share",
                "target",
                "largest book share",
                "unit links",
                "query verses",
            ],
            [
                [
                    s,
                    int((assign == i).sum()),
                    int((verse.split == s).sum()),
                    f"{fractions[i]:.1%}",
                    f"{ratios[s]:.0%}",
                    f"{shares[i]:.0%}",
                    int((unit.split == s).sum()),
                    int(all_verse[all_verse.split == s].src_vid.nunique()),
                ]
                for i, s in enumerate(SPLITS)
            ],
        ),
        "",
        "## Per book",
    ]
    a, b = book_ids[verse.src_vid.to_numpy()], book_ids[verse.tgt_vid.to_numpy()]
    rows = []
    for book in BOOKS:
        i = book.book_id
        rows.append(
            [
                book.sefaria,
                SPLITS[assign[i]],
                int(((a == i) | (b == i)).sum()),
                int(((a == i) & (b == i)).sum()),
            ]
        )
    parts.append(md_table(["book", "split", "pairs touching", "within-book pairs"], rows))
    parts += ["", "## Per connection type (verse pairs)"]
    types = verse.assign(t=verse.connection_type.replace("", "(none)").str.split(",")).explode("t")
    ct = (
        types.groupby(["t", "split"])
        .size()
        .unstack(fill_value=0)
        .reindex(columns=SPLITS, fill_value=0)
    )
    ct = ct.loc[ct.sum(1).sort_values(ascending=False).index]
    parts.append(md_table(["type", *SPLITS], [[t, *map(int, r)] for t, r in ct.iterrows()]))
    parts += [
        "",
        "## Invalid refs",
        ", ".join(f"`{r}`" for r in sorted(set(stats.invalid))) or "none",
    ]
    path.write_text("\n".join(parts) + "\n", encoding="utf-8")


# --- driver --------------------------------------------------------------------------------


def run_build_links(cfg: dict[str, Any], log: Log = print) -> pd.DataFrame:
    raw = resolve_path(cfg, "data_raw")
    out = resolve_path(cfg, "data_processed")
    verses_path = out / "verses.parquet"
    if not verses_path.exists():
        raise RuntimeError(f"{verses_path} not found; run `bsim build-corpus` first")
    verses = pd.read_parquet(verses_path, columns=["verse_id", "book_id", "chapter", "verse"])
    book_ids = verses.sort_values("verse_id").book_id.to_numpy()

    files = sorted((raw / "sefaria" / "links").glob("links*.csv"))
    log(f"reading {len(files)} link files")
    rows = read_links(files)

    log(f"expanding {len(rows)} book-to-book links")
    links, stats = build_links(
        rows,
        RefIndex(verses),
        book_ids,
        cfg["links"]["cartesian_max"],
        cfg["retrieval"]["neighbor_window"],
    )

    log("splitting books")
    sp = cfg["splits"]
    assign, fractions = split_books(
        _book_pair_counts(links, book_ids),
        sp["ratios"],
        cfg["seed"],
        sp["restarts"],
        sp["max_book_share"],
    )
    links["split"] = assign_split(
        book_ids[links.src_vid.to_numpy()], book_ids[links.tgt_vid.to_numpy()], assign
    )
    # A unit range never crosses a book, so the start vid decides the book; check all ends anyway.
    check_leakage(links, book_ids, assign)

    out.mkdir(parents=True, exist_ok=True)
    links.to_parquet(out / "links.parquet", index=False)
    und = links[(links.level == "verse") & (links.src_vid < links.tgt_vid)]
    splits = {
        "seed": cfg["seed"],
        "ratios": sp["ratios"],
        "config_hash": config_hash(cfg, "seed", "links", "splits"),
        "built_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "books": {b.sefaria: SPLITS[assign[b.book_id]] for b in BOOKS},
        "verse_pairs": {s: int((und.split == s).sum()) for s in SPLITS},
        "fractions": {s: round(float(f), 4) for s, f in zip(SPLITS, fractions, strict=True)},
    }
    (out / "splits.json").write_text(
        json.dumps(splits, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    write_report(out / "links_report.md", cfg, links, stats, book_ids, assign, fractions)

    per_split = ", ".join(f"{s} {n}" for s, n in splits["verse_pairs"].items())
    log(
        f"done: {len(und)} verse pairs ({per_split}), "
        f"{int(((links.level == 'unit') & (links.src_vid < links.tgt_vid)).sum())} unit links, "
        f"{len(stats.invalid)} invalid refs"
    )
    return links
