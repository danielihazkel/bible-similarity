"""`bsim gematria-links`: do equal letter values link related words? (DESIGN.md §16.59)

Gematria pairs words of equal value (נחש = משיח = 358, יין = סוד = 70) and reads the pairing as a
link in meaning. The values come from `bsim gematria` (§16.53); this stage tests the reading,
with everything fixed in `gematria_links` before the first run.

- **Words** are content lemmas valued by their headword (`gematria.lemmas`), names left out, at
  least `min_count` occurrences and two letters, with an SDBH domain profile, a root family and a
  vector (below). Two lemmas spelled with the same letters (homographs, anagrams) have equal
  values by construction, not by gematria: such pairs are counted but left out of the test.
- **Relatedness**, three ways: `domains`, the cosine of the two lemmas' SDBH domain profiles
  (the domains tagged on their occurrences, weighted); `root`, one root family (`bsim roots`,
  §16.38); `vector`, the cosine of their BEREL vectors (as §16.23: the encoder's last hidden
  state over the word's subword tokens in its verse, averaged over up to `max_occ` occurrences
  drawn with the seed).
- **The test**: the mean relatedness of the equal-value pairs against `draws` sets of matched
  pairs. A matched pair keeps one lemma of the pair (either, at random) and replaces the other by
  a lemma of the same letter count and frequency band (`bands`, occurrences) whose value differs
  and which is not spelled with the first one's letters. One-sided: `p` is the share of draws as
  related. The claim fixed in advance is that equal values link nothing (expected not to hold
  on any measure).
- **A check of the measures** (a known answer): pairs of one root family, matched the same way,
  are closer on domains and vectors than chance.
- **The traditional equivalences** (`equivalences`): each pair's relatedness, ranked among all
  equal-value pairs.
- **Genesis 1:1** (`verse`): the properties claimed for its value and counts (2701 = 37 × 73, a
  triangular number; 7 words, 28 letters) counted over every verse. The look-elsewhere control:
  every verse described by its own numbers (word count, letter count, the largest prime factor
  of its value); how many verses are, as Gen 1:1 is, the only one with their description.

Writes `artifacts/gematria_links/`: `pairs.parquet` (every equal-value pair: `a, b, value,
same_letters, domains, root, vector`), `tests.parquet` (per test and measure: observed, the
draws' mean and quantiles, `p`), `equivalences.parquet`, `properties.parquet` (per property: the
verses that hold it), `verses.parquet` (the verses holding every property) and
`gematria_links.meta.json`.
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

import numpy as np
import pandas as pd

from bsim.config import config_hash, resolve_path
from bsim.data.lexicon import strong_key
from bsim.data.refs import RefIndex
from bsim.text.ciphers import key as letter_key

Log = Callable[[str], None]

MEASURES = ("domains", "root", "vector")


def largest_prime_factor(n: int) -> int:
    """The largest prime dividing `n` (1 for n < 2)."""
    best, d = 1, 2
    while d * d <= n:
        while n % d == 0:
            best, n = d, n // d
        d += 1
    return n if n > 1 else best


def prime_factors(n: int) -> int:
    """How many primes, with multiplicity, multiply to `n` (0 for n < 2)."""
    k, d = 0, 2
    while d * d <= n and n > 1:
        while n % d == 0:
            k, n = k + 1, n // d
        d += 1
    return k + (n > 1)


def triangular(n: int) -> bool:
    r = math.isqrt(8 * n + 1)
    return n > 0 and r * r == 8 * n + 1


def holds(prop: dict[str, Any], value: int, words: int, letters: int) -> bool:
    """Whether a verse with this value, word and letter count has the property."""
    kind = prop["kind"]
    if kind == "words":
        return words == int(prop["n"])
    if kind == "letters":
        return letters == int(prop["n"])
    if kind == "multiple":
        return value % int(prop["n"]) == 0
    if kind == "triangular":
        return triangular(value)
    if kind == "prime_factors":
        return prime_factors(value) == int(prop["n"])
    raise ValueError(f"gematria_links.verse.properties: unknown kind {kind!r}")


def domain_profiles(ws: pd.DataFrame, keys: list[str]) -> np.ndarray:
    """Each lemma's SDBH domains (weighted over its occurrences), L2-normalized rows."""
    want = set(keys)
    acc: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    for s, doms, wts in zip(ws.strong, ws.domains, ws.weights, strict=True):
        if s in want:
            for d, w in zip(doms, wts, strict=True):
                acc[s][str(d)] += float(w)
    codes = sorted({d for p in acc.values() for d in p})
    col = {d: i for i, d in enumerate(codes)}
    m = np.zeros((len(keys), len(codes)), dtype=np.float32)
    for i, k in enumerate(keys):
        for d, w in acc.get(k, {}).items():
            m[i, col[d]] = w
    n = np.linalg.norm(m, axis=1, keepdims=True)
    return m / np.where(n > 0, n, 1)


def matched_draws(
    a: np.ndarray, b: np.ndarray, cell: np.ndarray, value: np.ndarray, spelled: np.ndarray,
    draws: int, rng: np.random.Generator, tries: int = 8,
) -> tuple[np.ndarray, np.ndarray]:  # fmt: skip
    """`draws` matched pairs per pair (a, b): one side kept at random, the other replaced by a
    lemma of its cell (letter count × band) whose value differs from the kept one's and which
    is not spelled with its letters. Returns (kept, drawn) index arrays (pairs × draws); -1 where
    no partner was found."""
    n = len(a)
    swap = rng.random((n, draws)) < 0.5
    kept = np.where(swap, b[:, None], a[:, None])
    other = np.where(swap, a[:, None], b[:, None])
    pools: dict[int, np.ndarray] = {
        int(c): np.flatnonzero(cell == c) for c in np.unique(cell)
    }
    drawn = np.full((n, draws), -1)
    todo = np.ones((n, draws), dtype=bool)
    for _ in range(tries):
        if not todo.any():
            break
        rows, cols = np.nonzero(todo)
        cells = cell[other[rows, cols]]
        pick = np.empty(len(rows), dtype=np.int64)
        for c in np.unique(cells):
            m = cells == c
            pool = pools[int(c)]
            pick[m] = pool[rng.integers(0, len(pool), m.sum())]
        k = kept[rows, cols]
        ok = (pick != k) & (value[pick] != value[k]) & (spelled[pick] != spelled[k])
        drawn[rows[ok], cols[ok]] = pick[ok]
        todo[rows[ok], cols[ok]] = False
    return kept, drawn


def relatedness(measure: str, i: np.ndarray, j: np.ndarray, sims: dict[str, Any]) -> np.ndarray:
    if measure == "root":
        r = sims["root"]
        return (r[i] == r[j]).astype(np.float32)
    return sims[measure][i, j]


def score_pairs(
    a: np.ndarray, b: np.ndarray, sims: dict[str, Any], cell: np.ndarray, value: np.ndarray,
    spelled: np.ndarray, draws: int, rng: np.random.Generator, measures: tuple[str, ...],
) -> dict[str, dict[str, Any]]:  # fmt: skip
    """Mean relatedness of the pairs against matched draws, per measure."""
    kept, drawn = matched_draws(a, b, cell, value, spelled, draws, rng)
    found = drawn >= 0
    out = {}
    for m in measures:
        obs = float(relatedness(m, a, b, sims).mean())
        r = relatedness(m, kept.ravel(), np.where(found, drawn, 0).ravel(), sims).reshape(
            kept.shape
        )
        null = np.where(found, r, 0).sum(axis=0) / np.maximum(found.sum(axis=0), 1)
        out[m] = {
            "n": len(a),
            "observed": round(obs, 4),
            "null_mean": round(float(null.mean()), 4),
            "null_q05": round(float(np.quantile(null, 0.05)), 4),
            "null_q95": round(float(np.quantile(null, 0.95)), 4),
            "p": float((1 + np.sum(null >= obs)) / (1 + draws)),
            "unmatched": round(float(1 - found.mean()), 4),
        }
    return out


def encode_lemmas(
    cfg: dict[str, Any], words: pd.DataFrame, lemmas: list[str], max_occ: int,
    rng: np.random.Generator, log: Log,
) -> dict[str, np.ndarray]:  # fmt: skip
    """Each lemma's mean BEREL word vector over up to `max_occ` of its occurrences (as a word's
    only content lemma), L2-normalized."""
    from bsim.analysis.senses import encode_words

    gc = cfg["gematria_links"]
    single = words[words.content_lemmas.map(len) == 1]
    single = single.assign(lemma=single.content_lemmas.map(lambda c: str(c[0])))
    single = single[single.lemma.isin(set(lemmas))].sort_values(["lemma", "verse_id", "idx"])
    chosen = []
    for _, g in single.groupby("lemma", sort=True):
        idx = np.arange(len(g))
        if len(g) > max_occ:
            idx = np.sort(rng.choice(len(g), max_occ, replace=False))
        chosen.append(g.iloc[idx])
    occ = pd.concat(chosen)
    wanted: dict[int, set[int]] = defaultdict(set)
    for v, i in zip(occ.verse_id, occ.idx, strict=True):
        wanted[int(v)].add(int(i))
    surf = words.sort_values(["verse_id", "idx"]).groupby("verse_id").surface.agg(list)
    enc_cfg = {**cfg, "senses": {"encoder": gc["encoder"], "max_seq_length": gc["max_seq_length"],
                                 "batch_size": gc["batch_size"]}}  # fmt: skip
    vecs = encode_words(enc_cfg, [(int(v), s) for v, s in surf.items() if int(v) in wanted],
                        wanted, log)  # fmt: skip
    out: dict[str, np.ndarray] = {}
    for lem, g in occ.groupby("lemma", sort=True):
        vs = [vecs[(int(v), int(i))] for v, i in zip(g.verse_id, g.idx, strict=True)
              if (int(v), int(i)) in vecs]  # fmt: skip
        if vs:
            m = np.mean(vs, axis=0)
            out[str(lem)] = (m / max(np.linalg.norm(m), 1e-12)).astype(np.float32)
    return out


def run_gematria_links(
    cfg: dict[str, Any], log: Log = print, vectors: dict[str, np.ndarray] | None = None
) -> Path:
    """`vectors` replaces the encoder (tests): lemma -> vector."""
    gc = cfg["gematria_links"]
    proc, art = resolve_path(cfg, "data_processed"), resolve_path(cfg, "artifacts")
    out = art / "gematria_links"
    t0 = time.perf_counter()
    rng = np.random.default_rng(int(gc["seed"]))
    system, draws, alpha = gc["system"], int(gc["draws"]), float(gc["alpha"])

    lem = pd.read_parquet(art / "gematria" / "lemmas.parquet",
                          columns=["lemma", "he", system, "n_words"])  # fmt: skip
    lem = lem.rename(columns={system: "value"})
    lem["key"] = lem.lemma.map(strong_key)
    lem["spelled"] = lem.he.map(letter_key)
    lem["n_letters"] = lem.spelled.str.len()
    names: set[str] = set()
    lm_path = proc / "lexicon_lemmas.parquet"
    if lm_path.exists():
        lm = pd.read_parquet(lm_path).dropna(subset=["name_kind"])
        names = set(lm.strong)
    roots = pd.read_parquet(art / "roots" / "lemmas.parquet", columns=["lemma", "root"])
    root_of = dict(zip(roots.lemma, roots.root.astype(str), strict=True))
    lem = lem[~lem.key.isin(names) & (lem.n_words >= int(gc["min_count"])) & (lem.n_letters >= 2)
              & lem.lemma.isin(root_of)]  # fmt: skip
    ws = pd.read_parquet(proc / "word_senses.parquet", columns=["strong", "domains", "weights"])
    dom = domain_profiles(ws, lem.key.tolist())
    lem = lem[dom.any(axis=1)]
    words = pd.read_parquet(proc / "words.parquet",
                            columns=["verse_id", "idx", "surface", "content_lemmas"])  # fmt: skip
    if vectors is None:
        vectors = encode_lemmas(cfg, words, lem.lemma.tolist(), int(gc["max_occ"]), rng, log)
    lem = lem[lem.lemma.isin(vectors)].sort_values("lemma").reset_index(drop=True)
    log(f"{len(lem):,} lemmas with a value, domains, a root and a vector")

    # the measures, as matrices over the lemmas
    dom = domain_profiles(ws, lem.key.tolist())
    vec = np.stack([vectors[x] for x in lem.lemma])
    root_codes = pd.factorize(lem.lemma.map(root_of))[0]
    sims: dict[str, Any] = {"domains": dom @ dom.T, "vector": vec @ vec.T, "root": root_codes}
    value = lem.value.to_numpy()
    spelled = pd.factorize(lem.spelled.map(lambda s: "".join(sorted(s))))[0]
    edges = [int(x) for x in gc["bands"]]
    band = np.searchsorted(edges, lem.n_words.to_numpy(), side="right") - 1
    cell = lem.n_letters.to_numpy() * 100 + band

    # every pair of equal value
    pa, pb = [], []
    for _, idx in lem.groupby("value").groups.items():
        ix = sorted(idx)
        for x in range(len(ix)):
            for y in range(x + 1, len(ix)):
                pa.append(ix[x])
                pb.append(ix[y])
    pa_, pb_ = np.array(pa, dtype=np.int64), np.array(pb, dtype=np.int64)
    same = spelled[pa_] == spelled[pb_]
    pairs = pd.DataFrame({
        "a": lem.lemma.to_numpy()[pa_], "b": lem.lemma.to_numpy()[pb_], "value": value[pa_],
        "same_letters": same,
        **{m: np.round(relatedness(m, pa_, pb_, sims), 4) for m in MEASURES},
    })  # fmt: skip
    pairs["root"] = pairs["root"].astype(int)
    a, b = pa_[~same], pb_[~same]
    log(f"  {len(pairs):,} equal-value pairs, {int(same.sum()):,} spelled with the same letters")
    tests = {"equal": score_pairs(a, b, sims, cell, value, spelled, draws, rng, MEASURES)}

    # the check of the measures: pairs of one root family (not spelled alike)
    ra, rb = [], []
    for _, idx in pd.Series(range(len(lem))).groupby(root_codes).groups.items():
        ix = sorted(idx)
        for x in range(len(ix)):
            for y in range(x + 1, len(ix)):
                if spelled[ix[x]] != spelled[ix[y]] and value[ix[x]] != value[ix[y]]:
                    ra.append(ix[x])
                    rb.append(ix[y])
    tests["root_family"] = score_pairs(np.array(ra), np.array(rb), sims, cell, value, spelled,
                                      draws, rng, ("domains", "vector"))  # fmt: skip
    log(f"  {len(ra):,} pairs of one root family (the check)")

    # the traditional equivalences, ranked among the equal-value pairs
    by_he: dict[str, int] = {}
    for i, (s, n) in enumerate(zip(lem.spelled, lem.n_words, strict=True)):
        if s not in by_he or n > lem.n_words[by_he[s]]:
            by_he[s] = i
    eq_pairs = pairs[~pairs.same_letters]
    eq_rows = []
    for x, y in gc["equivalences"]:
        i, j = by_he.get(letter_key(x)), by_he.get(letter_key(y))
        row: dict[str, Any] = {"a_text": x, "b_text": y, "found": i is not None and j is not None}
        if row["found"]:
            row |= {"a": lem.lemma[i], "b": lem.lemma[j], "value": int(value[i]),
                    "equal": bool(value[i] == value[j])}  # fmt: skip
            for m in MEASURES:
                r = float(relatedness(m, np.array([i]), np.array([j]), sims)[0])
                row[m] = round(r, 4)
                row[f"{m}_rank"] = round(float((eq_pairs[m] < r).mean()), 4)
        eq_rows.append(row)
    equivalences = pd.DataFrame(eq_rows)

    # Genesis 1:1 and every verse
    verses = pd.read_parquet(art / "gematria" / "verses.parquet",
                             columns=["verse_id", system, "n_words", "n_letters"])  # fmt: skip
    verses = verses.rename(columns={system: "value"}).sort_values("verse_id")
    vrows = pd.read_parquet(proc / "verses.parquet",
                            columns=["verse_id", "book_id", "chapter", "verse"])  # fmt: skip
    vc = gc["verse"]
    vid = RefIndex(vrows).resolve(vc["ref"])[0]
    vals, nw, nl = (verses[c].to_numpy() for c in ("value", "n_words", "n_letters"))
    props = vc["properties"]
    has = np.array([[holds(p, int(v), int(w), int(n)) for v, w, n in zip(vals, nw, nl,
                                                                         strict=True)]
                    for p in props])  # fmt: skip
    vids = verses.verse_id.to_numpy()
    at = int(np.flatnonzero(vids == vid)[0])
    prop_rows = [{"key": p["key"], "kind": p["kind"], "n": p.get("n"),
                  "holds_here": bool(has[k, at]), "verses": int(has[k].sum())}
                 for k, p in enumerate(props)]  # fmt: skip
    every = has.all(axis=0)
    rates = has.mean(axis=1)
    lpf = np.array([largest_prime_factor(int(v)) for v in vals])
    desc = pd.Series(list(zip(nw.tolist(), nl.tolist(), lpf.tolist(), strict=True)))
    unique = desc.map(desc.value_counts()).to_numpy() == 1
    verse = {
        "ref": vc["ref"], "verse_id": int(vid), "value": int(vals[at]), "words": int(nw[at]),
        "letters": int(nl[at]), "largest_prime": int(lpf[at]), "n_verses": len(vals),
        "all": int(every.sum()), "expected_all": round(float(len(vals) * np.prod(rates)), 4),
        "unique_here": bool(unique[at]), "unique_share": round(float(unique.mean()), 4),
        # the other verses with its own description (word count, letter count, largest prime)
        "twins": [int(x) for x in vids[(desc == desc[at]).to_numpy()] if x != vid],
    }  # fmt: skip
    all_verses = pd.DataFrame({"verse_id": vids[every], "value": vals[every],
                               "n_words": nw[every], "n_letters": nl[every]})  # fmt: skip

    test_rows = [{"test": t, "measure": m, **r} for t, res in tests.items() for m, r in res.items()]
    out.mkdir(parents=True, exist_ok=True)
    pairs.to_parquet(out / "pairs.parquet")
    pd.DataFrame(test_rows).to_parquet(out / "tests.parquet")
    equivalences.to_parquet(out / "equivalences.parquet")
    pd.DataFrame(prop_rows).to_parquet(out / "properties.parquet")
    all_verses.to_parquet(out / "verses.parquet")
    meta = {
        "config_hash": config_hash(cfg, "gematria_links"),
        "built_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "system": system, "draws": draws, "alpha": alpha, "min_count": int(gc["min_count"]),
        "lemmas": len(lem), "pairs": len(pairs), "same_letters": int(same.sum()),
        "tested": int((~same).sum()), "root_pairs": len(ra),
        "tests": tests, "equivalences": equivalences.astype(object)
        .where(equivalences.notna(), None).to_dict("records"),
        "verse": verse, "properties": prop_rows,
        "seconds": round(time.perf_counter() - t0, 1),
    }  # fmt: skip
    meta = json.loads(json.dumps(meta, default=lambda x: x.item() if hasattr(x, "item") else x))
    (out / "gematria_links.meta.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False),
                                                  "utf-8")  # fmt: skip
    e, r = tests["equal"], tests["root_family"]
    log(
        "done: equal values vs matched pairs: "
        + ", ".join(f"{m} {e[m]['observed']:.3f} vs {e[m]['null_mean']:.3f} (p {e[m]['p']:.3f})"
                    for m in MEASURES)  # fmt: skip
        + "; one root (the check): "
        + ", ".join(f"{m} {r[m]['observed']:.3f} vs {r[m]['null_mean']:.3f} (p {r[m]['p']:.3f})"
                    for m in r)  # fmt: skip
        + f"; {vc['ref']}: {verse['all']} verse(s) with every property, unique by its own numbers"
        f" like {100 * verse['unique_share']:.0f}% of verses ({meta['seconds']} s) -> {out}"
    )
    return out

