"""`bsim echoes`: a direction on the echoes between books (DESIGN.md §16.36).

The network of echoes (§16.17) says which chapters resemble each other, not which drew on which.
Three earlier analyses can give a cross-book chapter pair a direction, from the strongest kind of
evidence to the weakest:

- **cited:** a resolved citation (§16.31) in one chapter points to a verse of the other — the
  text's own claim (sources are earlier in the canon by construction);
- **borrowed:** a parallel sequence over the two chapters with a direction estimate (§16.27,
  language and spelling voting; `unclear` sequences give none);
- **language:** both chapters inside the domain of the Late Biblical Hebrew profile (§16.24) and
  their scores at least `language_gap` apart: the later-looking chapter is taken to echo the
  earlier-looking one. The only layer that never sees the canon order, and the weakest: a profile
  of the language is not a date, and a similar pair need not be a borrowing at all.

A pair takes the first layer that decides it; when cited and borrowed disagree it is a
`conflict`. Pairs come from the chapter network's cross-book edges plus the chapter pairs of the
citations and sequences that the network misses (weight `explicit_weight`).

Checks fixed in advance (`meta.checks`): the language direction against the citations, against
the spelling sign of the borrowing sequences (spelling is not among the profile's features, though
the plene דויד is) and against the borrowing directions (not independent: the borrowing vote uses
the same language features). A check with fewer than `min_check` decided cases is reported as
underpowered. Also: how many language directions run against the canon order, and the cycles of the
book graph drawn from the explicit layers alone (two books each drawing on the other).

Writes `artifacts/echoes/{edges,books,chapters}.parquet` plus `echoes.meta.json`.
"""

from __future__ import annotations

import json
import math
import time
from collections import defaultdict
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import networkx as nx
import numpy as np
import pandas as pd

from bsim.analysis.dating import sign_test
from bsim.config import config_hash, resolve_path

Log = Callable[[str], None]

EDGE_COLUMNS = [
    "edge_id",
    "a",
    "b",
    "a_book",
    "b_book",
    "a_start",
    "a_end",
    "b_start",
    "b_end",
    "weight",
    "n_cited",
    "borrowed",
    "gap",
    "language",
    "direction",
    "basis",
]
BOOK_COLUMNS = ["src_book", "dst_book", "cited", "borrowed", "language"]
CHAPTER_COLUMNS = ["unit_id", "book_id", "lends", "borrows", "lends_explicit", "borrows_explicit"]
BASES = ("cited", "borrowed", "language")


def sign(x: float) -> int:
    return 0 if x == 0 or math.isnan(x) else (1 if x > 0 else -1)


def language_vote(gap: float, min_gap: float) -> float:
    """+1 when b looks later by at least `min_gap`, −1 when a does, 0 when closer, NaN unscored."""
    if math.isnan(gap):
        return math.nan
    return 0.0 if abs(gap) < min_gap else float(sign(gap))


def orient(n_cited: int, borrowed: int, language: float) -> tuple[int, str]:
    """(direction, basis): +1 = a → b (b echoes a), −1 = b → a, 0 = none; first deciding layer."""
    explicit = {s for s in (1 if n_cited else 0, borrowed) if s}
    if len(explicit) > 1:
        return 0, "conflict"
    if n_cited:
        return 1, "cited"
    if borrowed:
        return borrowed, "borrowed"
    if not math.isnan(language) and language:
        return int(language), "language"
    return 0, "none"


def check(votes: list[tuple[float, int]], min_n: int) -> dict[str, Any]:
    """Language votes against a reference direction: agreement and sign test over decided cases."""
    decided = [(v, r) for v, r in votes if not math.isnan(v) and v and r]
    n, agree = len(decided), sum(int(v == r) for v, r in decided)
    return {
        "n": n,
        "agree": agree,
        "p": float(f"{sign_test(agree, n):.3g}"),
        "underpowered": n < min_n,
    }


def chapter_pairs(
    spans: list[tuple[int, int, int, int]], chapter_of: np.ndarray
) -> dict[tuple[str, str], int]:
    """(a, b) chapter ids → summed direction of the spans `(src_lo, src_hi, dst_lo, dst_hi)` over
    them, a before b in the canon, +1 per span running a → b."""
    out: dict[tuple[str, str], int] = defaultdict(int)
    for s0, s1, d0, d1 in spans:
        for x in dict.fromkeys(chapter_of[s0 : s1 + 1]):
            for y in dict.fromkeys(chapter_of[d0 : d1 + 1]):
                if x == y:
                    continue
                key, s = ((x, y), 1) if x < y else ((y, x), -1)
                out[key] += s
    return dict(out)


def chapter_balance(directed: pd.DataFrame, order: dict[str, int]) -> pd.DataFrame:
    """Per chapter: directed pairs it is the source of (`lends`) and the echo of (`borrows`), all
    layers and the explicit ones (cited, borrowed), in canon order."""
    src = np.where(directed.direction > 0, directed.a, directed.b)
    dst = np.where(directed.direction > 0, directed.b, directed.a)
    book = dict(zip(directed.a, directed.a_book, strict=True))
    book |= dict(zip(directed.b, directed.b_book, strict=True))
    explicit = directed.basis.isin(["cited", "borrowed"]).to_numpy()
    counts = {
        "lends": pd.Series(src).value_counts(),
        "borrows": pd.Series(dst).value_counts(),
        "lends_explicit": pd.Series(src[explicit]).value_counts(),
        "borrows_explicit": pd.Series(dst[explicit]).value_counts(),
    }
    units = sorted(book, key=order.__getitem__)
    return pd.DataFrame(
        {"unit_id": units, "book_id": [int(book[u]) for u in units]}
        | {k: [int(v.get(u, 0)) for u in units] for k, v in counts.items()}
    )


def book_cycles(edges: pd.DataFrame, max_len: int) -> list[list[int]]:
    """Directed cycles (up to `max_len` books) of the book graph of the cited / borrowed edges."""
    g = nx.DiGraph()
    for r in edges[edges.basis.isin(["cited", "borrowed"])].itertuples():
        src, dst = (r.a_book, r.b_book) if r.direction > 0 else (r.b_book, r.a_book)
        g.add_edge(int(src), int(dst))
    cycles = [c for c in nx.simple_cycles(g) if len(c) <= max_len]
    return sorted([c[c.index(min(c)) :] + c[: c.index(min(c))] for c in cycles])


def run_echoes(cfg: dict[str, Any], log: Log = print) -> Path:
    ec = cfg["echoes"]
    proc, art = resolve_path(cfg, "data_processed"), resolve_path(cfg, "artifacts")
    t0 = time.perf_counter()
    units = pd.read_parquet(proc / "units.parquet")
    chapters = units[units.unit_type == "chapter"].sort_values("start_verse_id")
    n_verses = int(chapters.end_verse_id.max()) + 1
    # chapter ids sort in canon order through their position
    pos = {u: i for i, u in enumerate(chapters.unit_id)}
    chapter_of = np.empty(n_verses, dtype=np.int64)
    for i, (s, e) in enumerate(zip(chapters.start_verse_id, chapters.end_verse_id, strict=True)):
        chapter_of[s : e + 1] = i
    ids = chapters.unit_id.to_numpy()
    book = dict(zip(chapters.unit_id, chapters.book_id, strict=True))
    span = {u: (s, e) for u, s, e in chapters[["unit_id", "start_verse_id", "end_verse_id"]].values}

    net = pd.read_parquet(art / "network" / "edges.parquet")
    net = net[(net.unit_type == "chapter")]
    net = net[[book[a] != book[b] for a, b in zip(net.a, net.b, strict=True)]]
    weight = {
        (min(pos[a], pos[b]), max(pos[a], pos[b])): w
        for a, b, w in zip(net.a, net.b, net.weight, strict=True)
    }

    cites = pd.read_parquet(art / "citations" / "citations.parquet")
    cites = cites[(cites.resolved == 1) & (cites.book_id != cites.target_book)]
    cited = chapter_pairs(
        [
            (int(t), int(t), int(v), int(v))
            for v, t in zip(cites.verse_id, cites.target_vid, strict=True)
        ],
        chapter_of,
    )
    seqs = pd.read_parquet(art / "borrowing" / "sequences.parquet")
    decided = seqs[seqs.direction.isin(["a_to_b", "b_to_a"])]
    borrowed = chapter_pairs(
        [
            (r.a_start, r.a_end, r.b_start, r.b_end)
            if r.direction == "a_to_b"
            else (r.b_start, r.b_end, r.a_start, r.a_end)
            for r in decided.itertuples()
        ],
        chapter_of,
    )

    dating = pd.read_parquet(art / "dating" / "chapters.parquet")
    dating = dating[~dating.out_of_domain & dating.score.notna()]
    score = dict(zip(dating.unit_id, dating.score, strict=True))

    rows = []
    pairs = sorted(set(weight) | set(cited) | set(borrowed))
    for i, j in pairs:
        a, b = ids[i], ids[j]
        gap = score[b] - score[a] if a in score and b in score else math.nan
        n_cited = cited.get((i, j), 0)
        bor = sign(borrowed.get((i, j), 0))
        lang = language_vote(gap, ec["language_gap"])
        direction, basis = orient(n_cited, bor, lang)
        rows.append(
            {
                "a": a,
                "b": b,
                "a_book": book[a],
                "b_book": book[b],
                "a_start": span[a][0],
                "a_end": span[a][1],
                "b_start": span[b][0],
                "b_end": span[b][1],
                "weight": weight.get((i, j), ec["explicit_weight"]),
                "n_cited": n_cited,
                "borrowed": bor,
                "gap": round(gap, 4) if not math.isnan(gap) else math.nan,
                "language": lang,
                "direction": direction,
                "basis": basis,
            }
        )
    edges = pd.DataFrame(rows, columns=EDGE_COLUMNS[1:])
    edges.insert(0, "edge_id", np.arange(1, len(edges) + 1))
    edges["language"] = edges.language.astype("Int64")
    directed = edges[edges.direction != 0]

    # books: directed edges per (source, echo) book pair and layer
    src = np.where(directed.direction > 0, directed.a_book, directed.b_book)
    dst = np.where(directed.direction > 0, directed.b_book, directed.a_book)
    books = (
        pd.crosstab([src, dst], directed.basis.to_numpy())
        .reindex(columns=list(BASES), fill_value=0)
        .rename_axis(index=["src_book", "dst_book"], columns=None)
        .reset_index()
    )
    books = books.sort_values(["src_book", "dst_book"]).reset_index(drop=True)

    chap_df = chapter_balance(directed, pos)

    # checks: the language direction against the explicit layers
    lang = edges.language.astype("float64").to_numpy()
    by_cited = check(
        [(v, 1) for v, c in zip(lang, edges.n_cited, strict=True) if c], ec["min_check"]
    )
    by_borrowed = check(list(zip(lang, edges.borrowed, strict=True)), ec["min_check"])
    spelling = []
    min_ops = cfg["borrowing"]["min_ops"]
    for r in seqs.itertuples():
        if r.n_spelling < min_ops or math.isnan(r.spelling):
            continue
        sa = [
            score[ids[c]]
            for c in dict.fromkeys(chapter_of[r.a_start : r.a_end + 1])
            if ids[c] in score
        ]
        sb = [
            score[ids[c]]
            for c in dict.fromkeys(chapter_of[r.b_start : r.b_end + 1])
            if ids[c] in score
        ]
        gap = float(np.mean(sb) - np.mean(sa)) if sa and sb else math.nan
        spelling.append((language_vote(gap, ec["language_gap"]), sign(r.spelling)))
    by_spelling = check(spelling, ec["min_check"])
    lang_edges = edges[edges.basis == "language"]
    cycles = book_cycles(edges, ec["max_cycle"])

    out = art / "echoes"
    out.mkdir(parents=True, exist_ok=True)
    edges[EDGE_COLUMNS].to_parquet(out / "edges.parquet")
    books[BOOK_COLUMNS].to_parquet(out / "books.parquet")
    chap_df[CHAPTER_COLUMNS].to_parquet(out / "chapters.parquet")
    meta = {
        "config_hash": config_hash(cfg, "echoes", "borrowing.min_ops"),
        "built_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "language_gap": ec["language_gap"],
        "pairs": int(len(edges)),
        "network_pairs": int(len(weight)),
        "in_domain": int(edges.gap.notna().sum()),
        "bases": {b: int((edges.basis == b).sum()) for b in (*BASES, "conflict", "none")},
        "checks": {"cited": by_cited, "spelling": by_spelling, "borrowed": by_borrowed},
        "language_forward": int((lang_edges.direction > 0).sum()),
        "language_backward": int((lang_edges.direction < 0).sum()),
        "cycles": cycles,
        "seconds": round(time.perf_counter() - t0, 1),
    }
    (out / "echoes.meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    log(
        f"done: {meta['pairs']} cross-book chapter pairs, directed "
        + ", ".join(f"{k} {v}" for k, v in meta["bases"].items())
        + f"; language vs cited {by_cited['agree']}/{by_cited['n']},"
        f" vs spelling {by_spelling['agree']}/{by_spelling['n']} (p {by_spelling['p']}),"
        f" vs borrowed {by_borrowed['agree']}/{by_borrowed['n']};"
        f" against the canon {meta['language_backward']} of {len(lang_edges)};"
        f" {len(cycles)} cycles ({meta['seconds']} s) -> {out}"
    )
    return out
