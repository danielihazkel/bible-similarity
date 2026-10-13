"""`bsim pentateuch`: an unsupervised P / non-P split of Genesis-Numbers (DESIGN.md §16.43).

Source criticism holds that a Priestly writer (P) and older non-Priestly sources were woven
together in Genesis-Numbers. Koppel, Dershowitz and colleagues split the text in two without
being told where P is, from the choice between synonyms (which a writer makes without thinking
of the topic) and then function words, and found the split close to the scholars' P. The test
here, framed so that it can fail:

1. **Step 1, chunks.** Each book is cut into chunks of `chunk_verses` verses. A chunk is
   described by its choices within each `synonyms` set (the share of each member it uses, minus
   the set's share in Genesis-Numbers; a set it does not use counts 0). The chunks' first
   principal component splits them in two; the `core_share` of each side scoring furthest out are
   the core.
2. **Step 2, verses.** A logistic regression on the core chunks' verses, over the synonym members
   and the `n_function` most frequent function words (prefixes and the parts of speech
   `function_pos`), each per word of the verse, gives every verse a probability; it is averaged
   over ±`smooth` verses of its book and the verse goes to the side above 0.5. The side holding
   most of Leviticus is called P-like (decided without the reference).
3. **Held out:** the divine names (`held_out`) are never features.

Checks fixed in advance, each against the split shifted circularly within each book (`draws`;
the runs of the split are kept, their place is random): (1) Cohen's kappa of the split with the
reference P (`p`, Noth as commonly tabulated, entered by hand; `unassigned` verses left out) over
Genesis-Numbers; (2) the same within Genesis alone, where both sources tell stories, so law
against narrative cannot carry it; (3) in `names_window` (Genesis-Exodus 6:1, before P has the
name revealed) the share of יהוה among the divine names is lower on the P-like side.
Robustness: `grid` (chunk size × smoothing).

Writes `artifacts/pentateuch/`: `verses.parquet` (`verse_id, book_id, chapter, verse, prob, side,
reference, core`), `chapters.parquet` (`unit_id, book_id, chapter, verses, p_like, assigned,
p_ref`) and `pentateuch.meta.json`.
"""

from __future__ import annotations

import json
import time
from collections import Counter
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from bsim.analysis.stats import empirical_p
from bsim.config import config_hash, resolve_path
from bsim.data.canon import BY_SEFARIA
from bsim.data.refs import RefIndex

Log = Callable[[str], None]
YHWH = frozenset({"3068", "3050"})
ELOHIM = frozenset({"430", "410", "7706"})
PREFIX_HE = {"c": "ו", "d": "ה", "l": "ל", "b": "ב", "m": "מ", "k": "כ", "i": "ה?", "s": "ש"}


def verse_tokens(
    words: pd.DataFrame, held_out: set[str], function_pos: set[str]
) -> tuple[dict[int, Counter], dict[int, int], dict[int, tuple[int, int]], Counter]:
    """Per verse: token counts (`d`, `d@stem` for verbs, `p:x` for prefixes), its words, its
    (יהוה, אלהים / אל / שדי) counts; and the function-word token counts of the whole text."""
    toks: dict[int, Counter] = {}
    n_words: dict[int, int] = {}
    names: dict[int, tuple[int, int]] = {}
    func: Counter = Counter()
    for vid, lemma, morph in zip(words.verse_id, words.lemma, words.morph, strict=True):
        vid = int(vid)
        c = toks.setdefault(vid, Counter())
        n_words[vid] = n_words.get(vid, 0) + 1
        codes = morph[1:].split("/") if isinstance(morph, str) and morph else []
        for k, part in enumerate(str(lemma).split("/")):
            code = codes[k] if k < len(codes) else ""
            d = "".join(ch for ch in part if ch.isdigit())
            if not d:
                key = f"p:{part.strip()}"
                c[key] += 1
                func[key] += 1
                continue
            if d in YHWH or d in ELOHIM:
                y, e = names.get(vid, (0, 0))
                names[vid] = (y + (d in YHWH), e + (d in ELOHIM))
            if d in held_out:
                continue
            c[d] += 1
            if code[:1] == "V" and len(code) > 1:
                c[f"{d}@{code[1]}"] += 1
            if code[:1] in function_pos:
                func[d] += 1
    return toks, n_words, names, func


def choice_matrix(counts: np.ndarray, sets: list[list[int]]) -> np.ndarray:
    """Rows (chunks) of member counts -> each set's member shares minus the set's overall shares
    (0 where the row does not use the set)."""
    cols = []
    for members in sets:
        sub = counts[:, members].astype(float)
        tot = sub.sum(axis=1, keepdims=True)
        overall = sub.sum(axis=0) / max(sub.sum(), 1)
        share = np.where(tot > 0, sub / np.maximum(tot, 1) - overall, 0.0)
        cols.append(share)
    return np.hstack(cols) if cols else np.zeros((len(counts), 0))


def first_component(x: np.ndarray) -> np.ndarray:
    """Scores on the first principal component (sign as the SVD returns it)."""
    xc = x - x.mean(axis=0)
    _, _, vt = np.linalg.svd(xc, full_matrices=False)
    return xc @ vt[0]


def chunk_ids(book: np.ndarray, size: int) -> np.ndarray:
    """Consecutive chunks of `size` verses within each book (in verse order)."""
    out = np.zeros(len(book), int)
    nxt, pos, prev = -1, 0, None
    for i, b in enumerate(book):
        if b != prev or pos == size:
            nxt += 1
            pos = 0
        out[i] = nxt
        pos += 1
        prev = b
    return out


def smooth_within(prob: np.ndarray, book: np.ndarray, k: int) -> np.ndarray:
    if k <= 0:
        return prob.copy()
    s = pd.Series(prob)
    return s.groupby(book).transform(
        lambda g: g.rolling(2 * k + 1, center=True, min_periods=1).mean()
    ).to_numpy()


def kappa(a: np.ndarray, b: np.ndarray) -> float:
    """Cohen's kappa of two boolean labelings."""
    a, b = np.asarray(a, bool), np.asarray(b, bool)
    n = len(a)
    if n == 0:
        return float("nan")
    po = np.mean(a == b)
    pa, pb = a.mean(), b.mean()
    pe = pa * pb + (1 - pa) * (1 - pb)
    return float((po - pe) / (1 - pe)) if pe < 1 else 0.0


def name_gap(p_side: np.ndarray, yhwh: np.ndarray, elohim: np.ndarray) -> float:
    """Share of יהוה among the divine names on the non-P side minus on the P-like side."""

    def share(sel: np.ndarray) -> float:
        y, e = yhwh[sel].sum(), elohim[sel].sum()
        return y / (y + e) if y + e else float("nan")

    return float(share(~p_side) - share(p_side))


def circular(side: np.ndarray, book: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    out = side.copy()
    for b in np.unique(book):
        idx = np.flatnonzero(book == b)
        out[idx] = np.roll(side[idx], int(rng.integers(len(idx))))
    return out


def split(
    syn: np.ndarray, func: np.ndarray, n_words: np.ndarray, book: np.ndarray, sets: list[list[int]],
    chunk_verses: int, core_share: float, smooth: int, leviticus: np.ndarray,
) -> dict[str, Any]:  # fmt: skip
    """Steps 1 and 2: (prob of the P-like side per verse, the side, the core verses, chunk
    scores)."""
    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import StandardScaler

    ch = chunk_ids(book, chunk_verses)
    n_chunks = ch.max() + 1
    counts = np.zeros((n_chunks, syn.shape[1]))
    np.add.at(counts, ch, syn)
    score = first_component(choice_matrix(counts, sets))
    core = np.zeros(n_chunks, bool)
    side_of_chunk = score > 0
    for s in (True, False):
        idx = np.flatnonzero(side_of_chunk == s)
        if len(idx):
            k = max(1, int(round(core_share * len(idx))))
            far = idx[np.argsort(-np.abs(score[idx]))[:k]]
            core[far] = True
    x = np.hstack([syn, func]) / np.maximum(n_words, 1)[:, None]
    x = StandardScaler().fit_transform(x)
    train = core[ch]
    model = LogisticRegression(C=1.0, max_iter=2000)
    model.fit(x[train], side_of_chunk[ch][train])
    prob = smooth_within(model.predict_proba(x)[:, 1], book, smooth)
    side = prob > 0.5
    if side[leviticus].mean() < 0.5:  # the side holding most of Leviticus is P-like
        prob, side = 1 - prob, ~side
        flip = -1
    else:
        flip = 1
    return {"prob": prob, "side": side, "core": train, "coef": flip * model.coef_[0],
            "chunks": n_chunks}  # fmt: skip


def run_pentateuch(cfg: dict[str, Any], log: Log = print) -> Path:
    sc = cfg["pentateuch"]
    proc, art = resolve_path(cfg, "data_processed"), resolve_path(cfg, "artifacts")
    out = art / "pentateuch"
    t0 = time.perf_counter()
    rng = np.random.default_rng(sc["seed"])
    for f in ("verses.parquet", "words.parquet"):
        if not (proc / f).exists():
            raise RuntimeError(f"{proc / f} missing; run `bsim build-corpus` first")
    books = [BY_SEFARIA[b].book_id for b in sc["books"]]
    all_verses = pd.read_parquet(
        proc / "verses.parquet", columns=["verse_id", "book_id", "chapter", "verse"]
    )
    verses = all_verses[all_verses.book_id.isin(books)].sort_values("verse_id", ignore_index=True)
    words = pd.read_parquet(proc / "words.parquet", columns=["verse_id", "idx", "lemma", "morph"])
    words = words[words.verse_id.isin(verses.verse_id)].sort_values(["verse_id", "idx"])
    toks, n_w, names, func_counts = verse_tokens(
        words, {str(x) for x in sc["held_out"]}, set(sc["function_pos"])
    )

    # features
    members = [m for _, ms in sc["synonyms"] for m in ms]
    sets, pos = [], 0
    for _, ms in sc["synonyms"]:
        sets.append(list(range(pos, pos + len(ms))))
        pos += len(ms)
    func_words = [k for k, _ in func_counts.most_common(sc["n_function"])]
    vids = verses.verse_id.to_numpy()
    syn = np.array([[toks.get(v, {}).get(m, 0) for m in members] for v in vids], float)
    func = np.array([[toks.get(v, {}).get(f, 0) for f in func_words] for v in vids], float)
    n_words = np.array([n_w.get(v, 0) for v in vids], float)
    book = verses.book_id.to_numpy()
    lev = book == BY_SEFARIA["Leviticus"].book_id
    yhwh = np.array([names.get(v, (0, 0))[0] for v in vids], float)
    elohim = np.array([names.get(v, (0, 0))[1] for v in vids], float)

    # the reference
    index = RefIndex(all_verses)

    def mask(refs: list[str]) -> np.ndarray:
        m = np.zeros(len(vids), bool)
        for r in refs:
            a, b = index.resolve(r)
            m |= (vids >= a) & (vids <= b)
        return m

    ref_p, unassigned, window = mask(sc["p"]), mask(sc["unassigned"]), mask(sc["names_window"])
    assigned = ~unassigned
    gen = book == BY_SEFARIA["Genesis"].book_id

    def scores(side: np.ndarray) -> dict[str, float]:
        return {
            "kappa": kappa(side[assigned], ref_p[assigned]),
            "kappa_genesis": kappa(side[assigned & gen], ref_p[assigned & gen]),
            "names": name_gap(side[window], yhwh[window], elohim[window]),
        }

    def tested(side: np.ndarray, draws: int) -> dict[str, Any]:
        obs = scores(side)
        null = [scores(circular(side, book, rng)) for _ in range(draws)]
        return {
            key: {"observed": obs[key],
                  "null": float(np.nanmean([n[key] for n in null])),
                  "p": empirical_p(obs[key], np.array([n[key] for n in null]))}
            for key in obs
        }  # fmt: skip

    res = split(syn, func, n_words, book, sets, sc["chunk_verses"], sc["core_share"],
                sc["smooth"], lev)  # fmt: skip
    side = res["side"]
    tests = tested(side, sc["draws"])
    a = assigned
    confusion = {
        "p_like_p": int((side & ref_p & a).sum()),
        "p_like_non": int((side & ~ref_p & a).sum()),
        "non_p": int((~side & ref_p & a).sum()),
        "non_non": int((~side & ~ref_p & a).sum()),
    }
    by_book = {}
    for name, b in zip(sc["books"], books, strict=True):
        sel = assigned & (book == b)
        by_book[name] = {
            "verses": int(sel.sum()),
            "agree": float(np.mean(side[sel] == ref_p[sel])) if sel.any() else None,
            "p_like": float(side[book == b].mean()),
            "p_ref": float(ref_p[sel].mean()) if sel.any() else None,
        }

    def share(sel: np.ndarray) -> float | None:
        y, e = yhwh[sel].sum(), elohim[sel].sum()
        return float(y / (y + e)) if y + e else None

    names_detail = {
        "p_like": {"yhwh": int(yhwh[window & side].sum()),
                   "elohim": int(elohim[window & side].sum()),
                   "share": share(window & side)},
        "non_p": {"yhwh": int(yhwh[window & ~side].sum()),
                  "elohim": int(elohim[window & ~side].sum()),
                  "share": share(window & ~side)},
        "reference_p": share(window & ref_p & assigned),
        "reference_non": share(window & ~ref_p & assigned),
    }  # fmt: skip
    keys = members + func_words

    def strongest(order: np.ndarray) -> list[dict[str, Any]]:
        """The 12 heaviest tokens in `order`; a word that is both a synonym member and a function
        word is two columns of the model and is listed once."""
        seen: list[dict[str, Any]] = []
        for i in order:
            if keys[i] not in {f["token"] for f in seen}:
                seen.append({"token": keys[i], "weight": float(res["coef"][i])})
            if len(seen) == 12:
                break
        return seen

    order = np.argsort(res["coef"])
    features = {"p_like": strongest(order[::-1]), "non_p": strongest(order)}
    syn_use = [
        {"name": name, "members": ms,
         "p_like": [int(syn[side, members.index(m)].sum()) for m in ms],
         "non_p": [int(syn[~side, members.index(m)].sum()) for m in ms]}
        for name, ms in sc["synonyms"]
    ]  # fmt: skip

    grid = []
    for cv in sc["grid"]["chunk_verses"]:
        for sm in sc["grid"]["smooth"]:
            r = split(syn, func, n_words, book, sets, cv, sc["core_share"], sm, lev)
            t = tested(r["side"], 200)
            grid.append({"chunk_verses": cv, "smooth": sm,
                         **{f"{k}": t[k]["observed"] for k in t},
                         **{f"{k}_p": t[k]["p"] for k in t}})  # fmt: skip

    out.mkdir(parents=True, exist_ok=True)
    ref = np.where(unassigned, None, np.where(ref_p, "P", "nonP"))
    vdf = verses.assign(
        prob=res["prob"], side=np.where(side, "P", "nonP"), reference=ref, core=res["core"]
    )
    vdf.to_parquet(out / "verses.parquet")
    vdf["unit_id"] = [f"c:{b}:{c}" for b, c in zip(vdf.book_id, vdf.chapter, strict=True)]
    vdf["is_p"] = side
    vdf["ref_p"] = np.where(unassigned, np.nan, ref_p.astype(float))
    chapters = (
        vdf.groupby(["unit_id", "book_id", "chapter"], sort=False)
        .agg(verses=("verse_id", "size"), p_like=("is_p", "mean"),
             assigned=("ref_p", "count"), p_ref=("ref_p", "mean"))
        .reset_index()
    )  # fmt: skip
    chapters.to_parquet(out / "chapters.parquet")
    meta = {
        "config_hash": config_hash(cfg, "pentateuch"),
        "built_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "verses": int(len(vids)),
        "assigned": int(assigned.sum()),
        "reference_p": int((ref_p & assigned).sum()),
        "p_like": int(side.sum()),
        "chunks": int(res["chunks"]),
        "core_verses": int(res["core"].sum()),
        "synonym_sets": len(sets),
        "function_words": func_words,
        "alpha": sc["alpha"],
        "draws": sc["draws"],
        "agreement": float(np.mean(side[assigned] == ref_p[assigned])),
        "tests": tests,
        "confusion": confusion,
        "books": by_book,
        "names": names_detail,
        "features": features,
        "synonyms": syn_use,
        "grid": grid,
        "prefixes": PREFIX_HE,
        "seconds": round(time.perf_counter() - t0, 1),
    }
    text = json.dumps(meta, indent=2, ensure_ascii=False)
    (out / "pentateuch.meta.json").write_text(text, "utf-8")
    t = tests
    log(
        f"done: {meta['verses']} verses, {meta['p_like']} P-like ({meta['reference_p']} P of"
        f" {meta['assigned']} assigned); agreement {meta['agreement']:.3f}; kappa"
        f" {t['kappa']['observed']:.3f} vs {t['kappa']['null']:.3f} (p {t['kappa']['p']:.4f});"
        f" Genesis {t['kappa_genesis']['observed']:.3f} vs {t['kappa_genesis']['null']:.3f}"
        f" (p {t['kappa_genesis']['p']:.4f}); names gap {t['names']['observed']:.3f} vs"
        f" {t['names']['null']:.3f} (p {t['names']['p']:.4f}) ({meta['seconds']} s) -> {out}"
    )
    return out
