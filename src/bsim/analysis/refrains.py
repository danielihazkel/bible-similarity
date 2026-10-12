"""`bsim refrains`: phrases that come back inside a passage (DESIGN.md §16.40).

A refrain is a phrase a passage repeats at intervals: ולא שבתם עדי נאם יהוה closes each plague of
Amos 4:6-11, כי לעולם חסדו every verse of Psalm 136. The shared-phrase analysis (§16.1) pairs
verses across the canon, and the Leitworte (§16.2) count single words; neither looks for a phrase
that recurs nearby.

- **Tokens.** Each verse becomes its lemmas in order, prefixes dropped (ו, ה, ב, ל, כ, מ, ש vary
  freely between the repeats of one refrain: ולא / לא, בכל / כל).
- **Seeds and runs.** Every `min_tokens` lemmas in a row inside a verse holding at least
  `min_content` nouns, verbs or adjectives (names do not count: ישמעאל בן נתניה is a man named
  through his story, not a phrase) is a seed; the verses of one book holding it, chained while
  consecutive ones are at most `max_gap` verses apart, form a run; a run in at least `min_count`
  verses is a candidate. Its burst: the Poisson chance of that many verses in its span given the
  seed's rate in the book, so a formula spread through a book (ויאמר יהוה אל משה) is not a
  refrain where it merely recurs.
- **Chance.** The verse order is shuffled within each book (`shuffles`) and the runs found again;
  the false discovery rate of a burst is the shuffled count at least as strong over the observed
  one. Candidates at most `alpha` are refrains, each extended to the longest phrase all its verses
  share; one refrain per verse set and phrase.
- **Checks fixed in advance.** (1) `known`: refrains scholarship names (Genesis 1, Amos 1-2 and 4,
  Isaiah 9-10, Psalms 42-43, 80, 107, 136, Song of Songs), each found when one refrain is in
  `min_count` of the verses named. (2) Regular spacing: the coefficient of variation of the gaps
  against the same number of occurrences placed at random between the first and the last
  (`draws`; a refrain too short for any placement to reach `alpha` is not tested); the share
  regular at `alpha` against `alpha`. (3) At the turns: each occurrence's sharper neighbouring
  gap (§16.29, the gap before or after the verse) against random verses of the same span. (2)
  and (3) use the *distinct* refrains: the strongest of each group sharing a verse.

Writes `artifacts/refrains/`: `refrains.parquet` (`refrain_id` = 1 strongest, `book_id, k,
first_vid, last_vid, n_tokens, p, q, cv, regular_p, turn, strongest, known, text, lemmas`),
`occurrences.parquet` (`refrain_id, verse_id, first, last`: display tokens, inclusive) and
`refrains.meta.json`.
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
from scipy import stats

from bsim.config import config_hash, resolve_path

Log = Callable[[str], None]
CONTENT = frozenset("NVA")


def token_stream(words: pd.DataFrame) -> pd.DataFrame:
    """One row per lemma, prefixes dropped: `verse_id, idx` (its word), `pos` (in the verse),
    `lemma`, `content` (a noun, verb or adjective; not a name)."""
    rows = []
    for vid, idx, lemma, morph in zip(
        words.verse_id, words.idx, words.lemma, words.morph, strict=True
    ):
        parts = str(lemma).split("/")
        codes = morph[1:].split("/") if isinstance(morph, str) and morph else []
        for k, part in enumerate(parts):
            lem = part.replace(" ", "")
            if not lem[:1].isdigit():
                continue  # a prefix
            m = codes[k] if k < len(codes) else ""
            rows.append((int(vid), int(idx), lem, m[:1] in CONTENT and not m.startswith("Np")))
    t = pd.DataFrame(rows, columns=["verse_id", "idx", "lemma", "content"])
    t["pos"] = t.groupby("verse_id").cumcount()
    return t


def seeds(t: pd.DataFrame, n: int, min_content: int) -> pd.DataFrame:
    """Every `n` lemmas in a row inside a verse with at least `min_content` content lemmas:
    `key` (the lemmas packed into one integer), `verse_id`, `start`; first one per verse."""
    ids, vocab = pd.factorize(t.lemma)
    bits = max(1, int(np.ceil(np.log2(len(vocab) + 1))))
    if n * bits > 63:
        raise ValueError(f"min_tokens {n} too long to pack {len(vocab)} lemmas")
    vid = t.verse_id.to_numpy()
    m = len(t) - n + 1
    if m <= 0:
        return pd.DataFrame(columns=["key", "verse_id", "start"])
    same = vid[: m] == vid[n - 1 :]
    key = np.zeros(m, dtype=np.int64)
    for k in range(n):
        key = (key << bits) | ids[k : k + m]
    c = np.concatenate([[0], np.cumsum(t.content.to_numpy(dtype=np.int64))])
    ok = same & (c[n:] - c[:m] >= min_content)
    g = pd.DataFrame({"key": key[ok], "verse_id": vid[: m][ok], "start": t.pos.to_numpy()[: m][ok]})
    return g.drop_duplicates(["key", "verse_id"]).reset_index(drop=True)


def find_runs(
    g: pd.DataFrame, n_book: np.ndarray, max_gap: int, min_count: int
) -> pd.DataFrame:
    """Runs of one seed in one book (`g`: `key, verse_id, book_id, df`): `key, book_id, k, first,
    last, verses` (a tuple) and the burst `p`; the strongest run per verse set."""
    g = g.sort_values(["key", "verse_id"], kind="stable")
    key, vid, book = g.key.to_numpy(), g.verse_id.to_numpy(), g.book_id.to_numpy()
    new = np.ones(len(g), dtype=bool)
    new[1:] = (key[1:] != key[:-1]) | (book[1:] != book[:-1]) | (vid[1:] - vid[:-1] > max_gap)
    run = np.cumsum(new)
    size = np.bincount(run)[run]
    keep = size >= min_count
    if not keep.any():
        return pd.DataFrame(columns=["key", "book_id", "k", "first", "last", "verses", "p"])
    r = g[keep].assign(run=run[keep])
    out = r.groupby("run", sort=False).agg(
        key=("key", "first"),
        book_id=("book_id", "first"),
        df=("df", "first"),
        k=("verse_id", "size"),
        first=("verse_id", "min"),
        last=("verse_id", "max"),
        verses=("verse_id", tuple),
    )
    lam = (out["last"] - out["first"] + 1) * out["df"] / n_book[out.book_id.to_numpy()]
    out["p"] = stats.poisson.sf(out.k - 1, lam)
    out = out.sort_values(["p", "key"], kind="stable").drop_duplicates("verses")
    return out.drop(columns="df").reset_index(drop=True)


def fdr(observed: np.ndarray, null: list[np.ndarray]) -> np.ndarray:
    """Estimated false discovery rate of each observed p: the mean shuffled count at most p over
    the observed count at most p, made monotone (a q-value)."""
    obs = np.asarray(observed, dtype=np.float64)
    if len(obs) == 0:
        return obs
    pooled = np.sort(np.concatenate(null)) if null else np.array([])
    order = np.argsort(obs, kind="stable")
    sp = obs[order]
    expected = np.searchsorted(pooled, sp, side="right") / max(len(null), 1)
    found = np.searchsorted(sp, sp, side="right")
    ratio = np.minimum(1.0, expected / found)
    q = np.minimum.accumulate(ratio[::-1])[::-1]
    out = np.empty_like(q)
    out[order] = q
    return out


def extend(
    verses: tuple[int, ...], starts: list[int], n: int, lemmas: dict[int, list[str]]
) -> tuple[list[int], int]:
    """The longest phrase all occurrences share around the seed: new starts and length."""
    starts = list(starts)
    while all(s > 0 for s in starts) and len(
        {lemmas[v][s - 1] for v, s in zip(verses, starts, strict=True)}
    ) == 1:
        starts = [s - 1 for s in starts]
        n += 1
    while all(s + n < len(lemmas[v]) for v, s in zip(verses, starts, strict=True)) and len(
        {lemmas[v][s + n] for v, s in zip(verses, starts, strict=True)}
    ) == 1:
        n += 1
    return starts, n


def spacing_p(
    vids: list[int], draws: int, alpha: float, rng: np.random.Generator
) -> tuple[float, float | None]:
    """The coefficient of variation of the gaps, and the share of random placements of the inner
    occurrences between the first and last at least as even (None: too few placements for the
    test to reach `alpha`)."""
    v = np.sort(np.asarray(vids))
    gaps = np.diff(v)
    cv = float(gaps.std() / gaps.mean())
    k, room = len(v), int(v[-1] - v[0] - 1)
    if room <= k - 2:
        return cv, None
    inner = np.sort(np.argsort(rng.random((draws, room)), axis=1)[:, : k - 2], axis=1) + v[0] + 1
    pos = np.hstack([np.full((draws, 1), v[0]), inner, np.full((draws, 1), v[-1])])
    g = np.diff(pos, axis=1)
    null = g.std(axis=1) / g.mean(axis=1)
    # untestable when even the most even placement is too common to reach `alpha`
    if (1 + np.sum(null <= null.min() + 1e-12)) / (1 + draws) > alpha:
        return cv, None
    return cv, float((1 + np.sum(null <= cv + 1e-12)) / (1 + draws))


def side_scores(score: dict[int, float], book_of: dict[int, int], v: int) -> float | None:
    """The sharper of the gaps before and after verse `v` (None: neither scored)."""
    s = [score[v]] if v in score else []
    if v + 1 in score and book_of.get(v + 1) == book_of.get(v):
        s.append(score[v + 1])
    return max(s) if s else None


def run_refrains(cfg: dict[str, Any], log: Log = print) -> Path:
    rc = cfg["refrains"]
    proc, art = resolve_path(cfg, "data_processed"), resolve_path(cfg, "artifacts")
    out = art / "refrains"
    t0 = time.perf_counter()
    rng = np.random.default_rng(rc["seed"])
    verses = pd.read_parquet(
        proc / "verses.parquet", columns=["verse_id", "book_id", "ref", "display_tokens"]
    )
    words = pd.read_parquet(
        proc / "words.parquet", columns=["verse_id", "idx", "lemma", "morph", "display_idx"]
    ).sort_values(["verse_id", "idx"])
    t = token_stream(words)
    n, min_count = rc["min_tokens"], rc["min_count"]
    book_of = dict(zip(verses.verse_id, verses.book_id, strict=True))
    n_book = np.bincount(verses.book_id.to_numpy())

    g = seeds(t, n, rc["min_content"])
    g["book_id"] = g.verse_id.map(book_of).to_numpy()
    g["df"] = g.groupby(["key", "book_id"]).verse_id.transform("size")
    g = g[g.df >= min_count].reset_index(drop=True)
    runs = find_runs(g, n_book, rc["max_gap"], min_count)

    # chance: the verse order shuffled within each book
    null = []
    vid_all = verses.verse_id.to_numpy()
    for _ in range(rc["shuffles"]):
        new = np.empty(int(vid_all.max()) + 1, dtype=np.int64)
        for _, ids in verses.groupby("book_id").verse_id:
            ids = ids.to_numpy()
            new[ids] = rng.permutation(ids)
        null.append(find_runs(g.assign(verse_id=new[g.verse_id.to_numpy()]), n_book,
                              rc["max_gap"], min_count).p.to_numpy())  # fmt: skip
    runs["q"] = fdr(runs.p.to_numpy(), null)
    hits = runs[runs.q <= rc["alpha"]].reset_index(drop=True)

    # each refrain extended to the longest phrase its verses share
    lemmas = {v: list(s) for v, s in t.groupby("verse_id").lemma}
    word_of = {v: list(s) for v, s in t.groupby("verse_id").idx}
    start = dict(zip(zip(g.key, g.verse_id, strict=True), g.start, strict=True))
    display = {
        (v, i): d
        for v, i, d in zip(words.verse_id, words.idx, words.display_idx, strict=True)
        if pd.notna(d)
    }
    tokens_of = dict(zip(verses.verse_id, verses.display_tokens, strict=True))
    rows = []
    for h in hits.itertuples(index=False):
        vs = h.verses
        starts, length = extend(vs, [start[h.key, v] for v in vs], n, lemmas)
        phrase = tuple(lemmas[vs[0]][starts[0] : starts[0] + length])
        spans = []
        for v, s in zip(vs, starts, strict=True):
            ds = [display[v, w] for w in word_of[v][s : s + length] if (v, w) in display]
            spans.append((v, int(min(ds)), int(max(ds))) if ds else (v, None, None))
        rows.append((h.book_id, vs, phrase, length, h.p, h.q, spans))
    ref = pd.DataFrame(rows, columns=["book_id", "verses", "phrase", "n_tokens", "p", "q", "spans"])
    ref = ref.sort_values(["p", "n_tokens"], ascending=[True, False], kind="stable")
    ref = ref.drop_duplicates(["verses", "phrase"]).reset_index(drop=True)
    ref["refrain_id"] = np.arange(1, len(ref) + 1)
    ref["k"] = ref.verses.map(len)
    ref["first_vid"] = ref.verses.map(min)
    ref["last_vid"] = ref.verses.map(max)
    ref["lemmas"] = ref.phrase.map(" ".join)

    def text(spans: list[tuple[int, int | None, int | None]]) -> str:
        v, a, b = spans[0]
        if a is None:
            return ""
        toks = list(tokens_of[v])[a : b + 1]
        return "".join(x + ("" if x.endswith("־") or i == len(toks) - 1 else " ")
                       for i, x in enumerate(toks))  # fmt: skip

    ref["text"] = ref.spans.map(text)

    # distinct refrains: the strongest of each group sharing a verse
    taken: set[int] = set()
    distinct = []
    for vs in ref.verses:
        d = not taken.intersection(vs)
        distinct.append(d)
        if d:
            taken.update(vs)
    ref["strongest"] = pd.Series(distinct, index=ref.index, dtype=bool)

    # (2) regular spacing
    sp = [spacing_p(list(vs), rc["draws"], rc["alpha"], rng) for vs in ref.verses]
    ref["cv"] = [c for c, _ in sp]
    ref["regular_p"] = pd.array([p for _, p in sp], dtype="Float64")
    d = ref[ref.strongest & ref.regular_p.notna()]
    n_reg = int((d.regular_p <= rc["alpha"]).sum())
    regular = {
        "testable": int(len(d)),
        "regular": n_reg,
        "share": n_reg / len(d) if len(d) else None,
        "p": float(stats.binomtest(n_reg, len(d), rc["alpha"], alternative="greater").pvalue)
        if len(d)
        else None,
    }

    # (3) at the turns of §16.29
    gaps_path = art / "segments" / "gaps.parquet"
    turns: dict[str, Any] | None = None
    ref["turn"] = pd.array([None] * len(ref), dtype="Float64")
    if gaps_path.exists():
        gaps = pd.read_parquet(gaps_path, columns=["verse_id", "score"])
        score = dict(zip(gaps.verse_id, gaps.score, strict=True))

        def mean_side(vs: Any) -> float | None:
            s = [x for v in vs if (x := side_scores(score, book_of, int(v))) is not None]
            return float(np.mean(s)) if s else None

        ref["turn"] = pd.array([mean_side(vs) for vs in ref.verses], dtype="Float64")
        dd = ref[ref.strongest]
        obs = [x for vs in dd.verses for v in vs
               if (x := side_scores(score, book_of, v)) is not None]  # fmt: skip
        sims = np.zeros(rc["draws"])
        total = np.zeros(rc["draws"])
        for vs in dd.verses:
            lo, hi = min(vs), max(vs)
            span = np.arange(lo, hi + 1)
            vals = np.array([side_scores(score, book_of, int(v)) for v in span], dtype=float)
            ok = ~np.isnan(vals)
            if not ok.any():
                continue
            vals = vals[ok]
            k = min(len(vs), len(vals))
            pick = np.argsort(rng.random((rc["draws"], len(vals))), axis=1)[:, :k]
            sims += vals[pick].sum(axis=1)
            total += k
        null_mean = sims / np.maximum(total, 1)
        turns = {
            "n": len(obs),
            "observed": float(np.mean(obs)) if obs else None,
            "expected": float(null_mean.mean()),
            "p": float((1 + np.sum(null_mean >= np.mean(obs))) / (1 + rc["draws"]))
            if obs
            else None,
        }

    # (1) the refrains scholarship names
    vid_of = dict(zip(verses.ref, verses.verse_id, strict=True))
    known, known_of = [], {}
    for name, refs in rc["known"]:
        named = {vid_of[x] for x in refs}
        best = None
        for r in ref.itertuples(index=False):
            if len(named.intersection(r.verses)) >= min_count:
                best = r
                break  # strongest first
        known.append(
            {
                "name": name,
                "verses": sorted(named),
                "first": refs[0],
                "last": refs[-1],
                "refrain_id": int(best.refrain_id) if best is not None else None,
                "text": best.text if best is not None else None,
                "k": int(best.k) if best is not None else None,
                "q": float(best.q) if best is not None else None,
            }
        )
        if best is not None:
            known_of.setdefault(int(best.refrain_id), name)
    ref["known"] = ref.refrain_id.map(known_of)

    out.mkdir(parents=True, exist_ok=True)
    occ = [
        (int(r.refrain_id), v, a, b)
        for r in ref.itertuples(index=False)
        for v, a, b in r.spans
        if a is not None
    ]
    pd.DataFrame(occ, columns=["refrain_id", "verse_id", "first", "last"]).to_parquet(
        out / "occurrences.parquet"
    )
    cols = ["refrain_id", "book_id", "k", "first_vid", "last_vid", "n_tokens", "p", "q", "cv",
            "regular_p", "turn", "strongest", "known", "text", "lemmas"]  # fmt: skip
    ref[cols].to_parquet(out / "refrains.parquet")
    at = float(hits.p.max()) if len(hits) else 0.0
    meta = {
        "config_hash": config_hash(cfg, "refrains"),
        "built_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "min_tokens": n,
        "min_count": min_count,
        "max_gap": rc["max_gap"],
        "alpha": rc["alpha"],
        "shuffles": rc["shuffles"],
        "candidates": int(len(runs)),
        "detect": {
            "observed": int(len(hits)),
            "expected": float(np.mean([np.sum(x <= at) for x in null])) if len(hits) else 0.0,
        },
        "refrains": int(len(ref)),
        "distinct": int(ref.strongest.sum()),
        "known": known,
        "known_found": sum(k["refrain_id"] is not None for k in known),
        "known_share": rc["known_share"],
        "regular": regular,
        "turns": turns,
        "seconds": round(time.perf_counter() - t0, 1),
    }
    (out / "refrains.meta.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False), "utf-8")
    log(
        f"done: {meta['refrains']} refrains ({meta['distinct']} distinct) from"
        f" {meta['candidates']} runs, {meta['detect']['expected']:.1f} expected by chance; known"
        f" {meta['known_found']} / {len(known)}; regular {regular['regular']} / "
        f"{regular['testable']}; turns {turns} ({meta['seconds']} s) -> {out}"
    )
    return out
