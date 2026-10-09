"""`bsim segments`: do the traditional divisions fall where the text turns? (DESIGN.md §16.29)

Every boundary between two verses of a book (a *gap*, identified by the verse after it) gets a
cohesion score from the text alone, then the divisions the tradition drew are placed on it:
the paragraph breaks of the MAM (Aleppo-based) and of the OSHB (Leningrad) — open פ and closed
ס — the medieval chapter divisions, the parashot and the style seams of §16.12.

- **Cohesion.** For a window of `w` verses on each side of the gap, the cosine of their summed
  idf-weighted content-lemma counts (lexical) and of their summed verse embeddings of the final
  semantic system (semantic). A gap where the text turns has low similarity across it.
- **Depth** (TextTiling, Hearst 1997): how far the similarity at the gap lies below the highest
  points reached by climbing the curve on each side; ties (a depth of 0 on every local peak of
  similarity) are broken by the dissimilarity. Each depth becomes a percentile within its book,
  and the score of a gap is the within-book percentile of the sum of the two (lexical,
  semantic): 0.5 is a typical gap, near 1 the strongest turns of the book.
- **Window.** Chosen from `segments.window_grid` on the dev books only: the window under which
  the MAM breaks score highest.

Tests (`segments.shuffles` within-book permutations; label masks shuffled across the gaps of
each book keep every book's count): the mean score of each kind of division against chance,
and contrasts between kinds (open vs closed, breaks both traditions mark vs one, chapter starts
with vs without a paragraph break) with the labels shuffled among the gaps of the two kinds. A
calibration shuffle is scored like the observed labels. Agreement as segmentation: per book,
the top-K gaps (K = the reference's boundaries) against the MAM breaks and the chapters, Pk and
WindowDiff (Beeferman et al. 1999; Pevzner & Hearst 2002) against K random gaps. Style seams:
the share lying within `near_seam` verses of a paragraph break or chapter start, against random
gaps of the same books.

Lists (`kind`): `turn` (an unmarked turn: a local peak scoring ≥ `turn_min` with no division
within one verse), `cut` (a chapter start with no paragraph break in either tradition, scoring
≤ `cut_max`: the chapter cuts through cohesive text) and `quiet` (a MAM paragraph break scoring
≤ `quiet_max`). Descriptive: cohesion is one reason to divide a text, not the only one (a
liturgical reading, a list, a scribe's habit), and the windows blur turns a verse or two.

Writes `artifacts/segments/`: `gaps.parquet`, `books.parquet` (agreement per book and
reference) and `segments.meta.json` (window choice, tests, contrasts, seams, calibration).
"""

from __future__ import annotations

import json
import time
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from scipy import sparse
from scipy.stats import rankdata

from bsim.analysis.stats import empirical_p, permute_within
from bsim.config import config_hash, resolve_path
from bsim.data.canon import BOOKS

Log = Callable[[str], None]

GAP_COLUMNS = [
    "book_id",
    "verse_id",
    "lex",
    "sem",
    "lex_depth",
    "sem_depth",
    "score",
    "mam",
    "oshb",
    "chapter",
    "parasha",
    "seam",
    "kind",
]
BOOK_COLUMNS = ["book_id", "ref", "k", "pk", "pk_null", "pk_p", "wd", "wd_null", "wd_p"]


def lemma_matrix(words: pd.DataFrame, n: int) -> sparse.csr_matrix:
    """Verses x content lemmas, counts weighted by idf over verses."""
    lem = words[["verse_id", "content_lemmas"]].explode("content_lemmas").dropna()
    codes, vocab = pd.factorize(lem.content_lemmas)
    x = sparse.csr_matrix(
        (np.ones(len(lem)), (lem.verse_id.to_numpy(), codes)), shape=(n, len(vocab))
    )
    x.sum_duplicates()
    df = np.asarray((x > 0).sum(axis=0)).ravel()
    return sparse.csr_matrix(x.multiply(np.log(n / np.maximum(df, 1))))


def window_cosines(m: Any, w: int) -> np.ndarray:
    """Cosine of the summed rows of `w` verses before and after every gap of one book.

    `m` (verses x dims, dense or sparse) is in reading order; entry k-1 is the gap before verse
    k (windows stop at the book's edges); 0 where a side has no content."""
    n = m.shape[0]
    if n < 2:
        return np.zeros(0)
    k = np.arange(1, n)
    left = sparse.csr_matrix(_band(np.maximum(0, k - w), k, n))
    right = sparse.csr_matrix(_band(k, np.minimum(n, k + w), n))
    a, b = left @ m, right @ m
    if sparse.issparse(a):
        dot = np.asarray(a.multiply(b).sum(axis=1)).ravel()
        na = np.sqrt(np.asarray(a.multiply(a).sum(axis=1)).ravel())
        nb = np.sqrt(np.asarray(b.multiply(b).sum(axis=1)).ravel())
    else:
        dot = np.einsum("ij,ij->i", a, b)
        na, nb = np.linalg.norm(a, axis=1), np.linalg.norm(b, axis=1)
    den = na * nb
    return np.divide(dot, den, out=np.zeros_like(dot, dtype=np.float64), where=den > 0)


def _band(lo: np.ndarray, hi: np.ndarray, n: int) -> sparse.coo_matrix:
    """Rows of ones over columns lo[i]..hi[i]-1."""
    lens = hi - lo
    rows = np.repeat(np.arange(len(lo)), lens)
    cols = np.concatenate([np.arange(a, b) for a, b in zip(lo, hi, strict=True)])
    return sparse.coo_matrix((np.ones(len(rows)), (rows, cols)), shape=(len(lo), n))


def depth_scores(sim: np.ndarray) -> np.ndarray:
    """TextTiling depth: (left peak − sim) + (right peak − sim), each peak reached by climbing
    the curve while it does not fall."""
    n = len(sim)
    left, right = sim.copy(), sim.copy()
    for i in range(1, n):  # a climb from i that steps to i-1 goes on as the climb from i-1
        if sim[i - 1] >= sim[i]:
            left[i] = left[i - 1]
    for i in range(n - 2, -1, -1):
        if sim[i + 1] >= sim[i]:
            right[i] = right[i + 1]
    return (left - sim) + (right - sim)


def percentile(x: np.ndarray) -> np.ndarray:
    """Mid-rank percentiles in (0, 1); ties share their mean rank."""
    return (rankdata(x) - 0.5) / max(1, len(x))


def book_scores(lex: np.ndarray, sem: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Lexical and semantic depths (ties broken by dissimilarity) and the combined score."""
    dl = depth_scores(lex) + 1e-6 * (1 - lex)
    ds = depth_scores(sem) + 1e-6 * (1 - sem)
    return dl, ds, percentile(percentile(dl) + percentile(ds))


def pk_windowdiff(ref: np.ndarray, hyp: np.ndarray, k: int) -> tuple[float, float]:
    """Pk and WindowDiff of two boolean boundary arrays over the gaps of one text."""
    cr = np.concatenate([[0], np.cumsum(ref)])
    ch = np.concatenate([[0], np.cumsum(hyp)])
    n = len(ref) - k + 1
    if n <= 0:
        return float("nan"), float("nan")
    br = cr[k : k + n] - cr[:n]
    bh = ch[k : k + n] - ch[:n]
    return float(np.mean((br > 0) != (bh > 0))), float(np.mean(br != bh))


def agreement(
    score: np.ndarray, ref: np.ndarray, reps: int, rng: np.random.Generator
) -> dict[str, float] | None:
    """The top-K gaps by score against `ref` (K boundaries), vs K random gaps."""
    n, kref = len(ref), int(ref.sum())
    if kref == 0 or kref >= n:
        return None
    k = max(2, round((n + 1) / (kref + 1) / 2))  # half the mean reference segment, in verses
    hyp = np.zeros(n, dtype=bool)
    hyp[np.argsort(-score, kind="stable")[:kref]] = True
    pk, wd = pk_windowdiff(ref, hyp, k)
    null = np.empty((reps, 2))
    rnd = np.zeros(n, dtype=bool)
    for r in range(reps):
        rnd[:] = False
        rnd[rng.choice(n, kref, replace=False)] = True
        null[r] = pk_windowdiff(ref, rnd, k)
    return {
        "k": k,
        "pk": pk,
        "pk_null": float(null[:, 0].mean()),
        "pk_p": empirical_p(-pk, -null[:, 0]),
        "wd": wd,
        "wd_null": float(null[:, 1].mean()),
        "wd_p": empirical_p(-wd, -null[:, 1]),
    }


def group_tests(
    score: np.ndarray,
    book: np.ndarray,
    masks: dict[str, np.ndarray],
    reps: int,
    rng: np.random.Generator,
) -> dict[str, dict[str, float]]:
    """Mean score of each label mask against the masks shuffled across each book's gaps."""
    obs = {g: float(score[m].mean()) if m.any() else float("nan") for g, m in masks.items()}
    null = {g: np.empty(reps) for g in masks}
    for r in range(reps):
        s = permute_within(score, book, rng)
        for g, m in masks.items():
            null[g][r] = s[m].mean() if m.any() else np.nan
    return {
        g: {
            "n": int(masks[g].sum()),
            "score": obs[g],
            "null": float(np.nanmean(null[g])) if masks[g].any() else float("nan"),
            "p": empirical_p(obs[g], null[g]) if masks[g].any() else float("nan"),
        }
        for g in masks
    }


def contrast(
    score: np.ndarray,
    book: np.ndarray,
    a: np.ndarray,
    b: np.ndarray,
    reps: int,
    rng: np.random.Generator,
) -> dict[str, float]:
    """mean(a) − mean(b), against the a / b labels shuffled among their gaps in each book."""
    u = a | b
    s, bk, la = score[u], book[u], a[u]
    if not la.any() or la.all():
        return {"a": float("nan"), "b": float("nan"), "diff": float("nan"), "p": float("nan")}
    diff = float(s[la].mean() - s[~la].mean())
    null = np.empty(reps)
    for r in range(reps):
        lp = permute_within(la, bk, rng)
        null[r] = s[lp].mean() - s[~lp].mean()
    return {
        "a": float(s[la].mean()),
        "b": float(s[~la].mean()),
        "diff": diff,
        "p": empirical_p(diff, null),
    }


def seam_test(
    seam: np.ndarray, marked: np.ndarray, book: np.ndarray, near: int, reps: int, rng
) -> dict[str, float]:
    """Share of style seams within `near` gaps of a marked division, vs random gaps per book."""
    near_mark = np.zeros(len(marked), dtype=bool)
    for b in np.unique(book):
        idx = np.flatnonzero(book == b)
        mk = marked[idx].astype(int)
        c = np.concatenate([[0], np.cumsum(mk)])
        i = np.arange(len(idx))
        lo, hi = np.maximum(0, i - near), np.minimum(len(idx), i + near + 1)
        near_mark[idx] = (c[hi] - c[lo]) > 0
    if not seam.any():
        return {"n": 0, "share": float("nan"), "null": float("nan"), "p": float("nan")}
    obs = float(near_mark[seam].mean())
    null = np.array([near_mark[permute_within(seam, book, rng)].mean() for _ in range(reps)])
    return {
        "n": int(seam.sum()),
        "share": obs,
        "null": float(null.mean()),
        "p": empirical_p(obs, null),
    }


def local_peak(score: np.ndarray, book: np.ndarray, radius: int) -> np.ndarray:
    """Whether each gap holds the highest score within ± `radius` gaps of its own book."""
    out = np.zeros(len(score), dtype=bool)
    for b in np.unique(book):
        idx = np.flatnonzero(book == b)
        s = score[idx]
        pad = np.concatenate([np.full(radius, -np.inf), s, np.full(radius, -np.inf)])
        win = np.lib.stride_tricks.sliding_window_view(pad, 2 * radius + 1)
        out[idx] = s >= win.max(axis=1)
    return out


def near(mask: np.ndarray, book: np.ndarray, radius: int) -> np.ndarray:
    """Whether a gap of the same book within ± `radius` gaps (itself included) is in `mask`."""
    out = np.zeros(len(mask), dtype=bool)
    for b in np.unique(book):
        idx = np.flatnonzero(book == b)
        c = np.concatenate([[0], np.cumsum(mask[idx].astype(int))])
        i = np.arange(len(idx))
        lo, hi = np.maximum(0, i - radius), np.minimum(len(idx), i + radius + 1)
        out[idx] = (c[hi] - c[lo]) > 0
    return out


def curves(lem: sparse.csr_matrix, emb: np.ndarray, verses: pd.DataFrame, w: int) -> pd.DataFrame:
    """Every gap of every book with its cosines, depths and score under window `w`."""
    parts = []
    for book, g in verses.groupby("book_id", sort=True):
        vids = g.verse_id.to_numpy()
        if len(vids) < 2:
            continue
        lex = window_cosines(lem[vids], w)
        sem = window_cosines(emb[vids], w)
        dl, ds, score = book_scores(lex, sem)
        parts.append(
            pd.DataFrame(
                {
                    "book_id": int(book),
                    "verse_id": vids[1:],
                    "lex": lex,
                    "sem": sem,
                    "lex_depth": dl,
                    "sem_depth": ds,
                    "score": score,
                }
            )
        )
    return pd.concat(parts, ignore_index=True)


def gap_labels(verses: pd.DataFrame, units: pd.DataFrame, seam_vids: set[int]) -> pd.DataFrame:
    """The divisions at every gap (the verse after it): MAM / OSHB break, chapter, parasha,
    seam. A paragraph break is stored on the verse before it (`break_after`)."""
    v = verses.sort_values("verse_id").reset_index(drop=True)
    same_book = v.book_id.to_numpy()[1:] == v.book_id.to_numpy()[:-1]
    prev, nxt = v.iloc[:-1][same_book], v.iloc[1:][same_book]

    def brk(col: str) -> list[str | None]:
        return [b if isinstance(b, str) else None for b in prev[col]]

    parasha = set(units.loc[units.unit_type == "parasha", "start_verse_id"].astype(int))
    vid = nxt.verse_id.to_numpy()
    return pd.DataFrame(
        {
            "verse_id": vid,
            "mam": brk("break_after"),
            "oshb": brk("oshb_break"),
            "chapter": (nxt.chapter.to_numpy() != prev.chapter.to_numpy()).astype(int),
            "parasha": np.isin(vid, list(parasha)).astype(int),
            "seam": np.isin(vid, list(seam_vids)).astype(int),
        }
    )


def label_masks(gaps: pd.DataFrame) -> dict[str, np.ndarray]:
    mam, oshb = gaps.mam.notna().to_numpy(), gaps.oshb.notna().to_numpy()
    chapter = gaps.chapter.to_numpy().astype(bool)
    return {
        "mam": mam,
        "mam_pe": (gaps.mam == "pe").to_numpy(),
        "mam_samekh": (gaps.mam == "samekh").to_numpy(),
        "oshb": oshb,
        "oshb_pe": (gaps.oshb == "pe").to_numpy(),
        "oshb_samekh": (gaps.oshb == "samekh").to_numpy(),
        "agreed": mam & oshb,
        "single": mam ^ oshb,
        "chapter": chapter,
        "chapter_break": chapter & (mam | oshb),
        "chapter_only": chapter & ~mam & ~oshb,
        "parasha": gaps.parasha.to_numpy().astype(bool),
        "seam": gaps.seam.to_numpy().astype(bool),
        "unmarked": ~mam & ~oshb & ~chapter,
    }


def kinds(gaps: pd.DataFrame, sc: dict[str, Any]) -> np.ndarray:
    """turn / cut / quiet / None for every gap (see the module docstring)."""
    m = label_masks(gaps)
    score, book = gaps.score.to_numpy(), gaps.book_id.to_numpy()
    marked = m["mam"] | m["oshb"] | m["chapter"] | m["parasha"]
    turn = (
        (score >= sc["turn_min"])
        & ~near(marked, book, 1)
        & local_peak(score, book, sc["turn_peak"])
    )
    cut = m["chapter_only"] & (score <= sc["cut_max"])
    quiet = m["mam"] & (score <= sc["quiet_max"])
    out = np.full(len(gaps), None, dtype=object)
    out[turn], out[cut], out[quiet] = "turn", "cut", "quiet"
    return out


def run_segments(cfg: dict[str, Any], log: Log = print) -> Path:
    from bsim.analysis.structure import embeddings_path

    sc = cfg["segments"]
    proc, art = resolve_path(cfg, "data_processed"), resolve_path(cfg, "artifacts")
    t0 = time.perf_counter()
    verses = pd.read_parquet(
        proc / "verses.parquet",
        columns=["verse_id", "book_id", "chapter", "break_after", "oshb_break"],
    ).sort_values("verse_id")
    words = pd.read_parquet(proc / "words.parquet", columns=["verse_id", "content_lemmas"])
    units = pd.read_parquet(proc / "units.parquet", columns=["unit_type", "start_verse_id"])
    seam_path = art / "seams" / "seams.parquet"
    seam_vids = (
        set(pd.read_parquet(seam_path).verse_id.astype(int)) if seam_path.exists() else set()
    )
    emb_path = embeddings_path(cfg)
    if not emb_path.exists():
        raise RuntimeError(f"{emb_path} missing; run `bsim embed` for the semantic system first")
    emb = np.load(emb_path).astype(np.float64)
    emb /= np.maximum(np.linalg.norm(emb, axis=1, keepdims=True), 1e-12)
    lem = lemma_matrix(words, len(verses))
    labels = gap_labels(verses, units, seam_vids)

    splits = json.loads((proc / "splits.json").read_text("utf-8"))["books"]
    dev = {b.book_id for b in BOOKS if splits.get(b.sefaria) == "dev"}

    # the window: MAM breaks scoring highest on the dev books
    grid: dict[int, float] = {}
    for w in sc["window_grid"]:
        g = curves(lem, emb, verses, w).merge(labels, on="verse_id")
        d = g[g.book_id.isin(dev)]
        grid[w] = round(float(d.loc[d.mam.notna(), "score"].mean()), 4)
    window = max(grid, key=lambda w: (grid[w], -w))
    log(f"window {window} (dev mean score at MAM breaks by window: {grid})")

    gaps = curves(lem, emb, verses, window).merge(labels, on="verse_id")
    gaps["kind"] = kinds(gaps, sc)
    rng = np.random.default_rng(sc["seed"])
    reps = sc["shuffles"]
    score, book = gaps.score.to_numpy(), gaps.book_id.to_numpy()
    masks = label_masks(gaps)

    groups = group_tests(score, book, masks, reps, rng)
    by_signal = {sig: percentile_in_book(gaps, f"{sig}_depth") for sig in ("lex", "sem")}
    for g, m in masks.items():  # the two signals alone, described
        for sig, pct in by_signal.items():
            groups[g][sig] = float(pct[m].mean()) if m.any() else float("nan")
    contrasts = {
        "pe_samekh": contrast(score, book, masks["mam_pe"], masks["mam_samekh"], reps, rng),
        "agreed_single": contrast(score, book, masks["agreed"], masks["single"], reps, rng),
        "chapter": contrast(score, book, masks["chapter_break"], masks["chapter_only"], reps, rng),
    }
    # calibration: the MAM labels shuffled once inside each book, tested as if observed
    fake = permute_within(masks["mam"], book, rng)
    calibration = group_tests(score, book, {"mam": fake}, reps, rng)["mam"]
    marked = masks["mam"] | masks["chapter"]
    seams = {**seam_test(masks["seam"], marked, book, sc["near_seam"], reps, rng)}
    seams["near"] = sc["near_seam"]

    rows = []
    for b, g in gaps.groupby("book_id", sort=True):
        s = g.score.to_numpy()
        for ref, r in (("mam", g.mam.notna().to_numpy()), ("chapter", g.chapter.to_numpy() > 0)):
            res = agreement(s, r, reps, rng)
            if res:
                rows.append({"book_id": int(b), "ref": ref, **res})
    books = pd.DataFrame(rows, columns=BOOK_COLUMNS)
    summary = {}
    for ref, g in books.groupby("ref"):
        summary[ref] = {
            "books": int(len(g)),
            "pk": round(float(g.pk.mean()), 4),
            "pk_null": round(float(g.pk_null.mean()), 4),
            "wd": round(float(g.wd.mean()), 4),
            "wd_null": round(float(g.wd_null.mean()), 4),
            "better": int((g.pk_p <= 0.05).sum()),
        }

    out = art / "segments"
    out.mkdir(parents=True, exist_ok=True)
    gaps = gaps[GAP_COLUMNS]
    for c in ("lex", "sem", "lex_depth", "sem_depth", "score"):
        gaps[c] = gaps[c].round(4)
    gaps.to_parquet(out / "gaps.parquet")
    books.round(4).to_parquet(out / "books.parquet")
    kind_counts = gaps.kind.value_counts().to_dict()
    meta = {
        "config_hash": config_hash(cfg, "segments", "final_systems"),
        "built_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "window": window,
        "window_grid": {str(k): v for k, v in grid.items()},
        "dev_books": sorted(dev),
        "gaps": int(len(gaps)),
        "groups": _rounded(groups),
        "contrasts": _rounded(contrasts),
        "calibration": _rounded(calibration),
        "seams": _rounded(seams),
        "agreement": summary,
        "kinds": {k: int(kind_counts.get(k, 0)) for k in ("turn", "cut", "quiet")},
        "seconds": round(time.perf_counter() - t0, 1),
    }
    (out / "segments.meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    log(
        f"done: {len(gaps)} gaps, window {window}; MAM breaks {groups['mam']['score']:.3f}"
        f" (p {groups['mam']['p']:.3g}); {meta['kinds']} ({meta['seconds']} s) -> {out}"
    )
    return out


def percentile_in_book(gaps: pd.DataFrame, col: str) -> np.ndarray:
    return gaps.groupby("book_id")[col].transform(lambda s: percentile(s.to_numpy())).to_numpy()


def _rounded(x: Any) -> Any:
    if isinstance(x, dict):
        return {k: _rounded(v) for k, v in x.items()}
    if isinstance(x, float):
        return None if np.isnan(x) else round(x, 4)
    return x
