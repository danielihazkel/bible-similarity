"""`bsim borrowing`: which side of a parallel passage looks like the borrower (DESIGN.md §16.27).

For every cross-book parallel sequence that `bsim diffs` aligned word by word (A = the passage
earlier in the canon), four signs, each fixed before looking at any result, say whether B looks
later than A (+1), earlier (−1) or neither (0):

    language   the Late Biblical Hebrew features of `bsim dating` (§16.24) over each side's
               verses, rates shrunk to the corpus, each feature's difference B − A in units of
               its spread over chapters, signed by its literature direction
               (`borrowing.language_signs`: more late words, fewer אנכי, ... = later), summed
    spelling   among the `spelling` changes, B fuller (more ו / י) than A or the reverse
    smoothing  among the `substitution` changes, B's word commoner than A's (a borrower
               replaces the rare or difficult word: lectio difficilior), by corpus frequency
    expansion  B adds more words than it omits (lectio brevior)
A diff sign needs `min_ops` changes of its kind. The votes' sum gives the direction (A → B if
positive, B → A if negative, else unclear).

Check: `borrowing.known` lists book pairs whose direction most scholars accept (Samuel–Kings →
Chronicles, Psalms → 1 Chr 16, 2 Kings → Jer 52, …). Each sign and the vote are scored on them
(agreement, sign test). Every known direction runs from the earlier book in the canon to the
later, so canon order would score perfectly too; the signs never see canon order, but a sign
that tracks "late in the canon" passes this check for that reason as well.

Writes `artifacts/borrowing/{sequences,books}.parquet` and `borrowing.meta.json`.
"""

from __future__ import annotations

import json
import math
import time
from collections import Counter
from collections.abc import Callable
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from bsim.analysis.dating import RATES, priors, rates, sign_test, word_flags
from bsim.config import config_hash, resolve_path
from bsim.data.canon import BY_OSIS
from bsim.text.normalize import consonantal

Log = Callable[[str], None]
SIGNS = ("language", "spelling", "smoothing", "expansion")


def vote(x: float, eps: float = 1e-9) -> int:
    return 0 if abs(x) <= eps or math.isnan(x) else (1 if x > 0 else -1)


def spelling_sign(ops: pd.DataFrame, min_ops: int) -> tuple[float, int]:
    """(mean over spelling changes of +1 when B's form is longer, −1 when A's is; their count)."""
    s = ops[ops.op == "spelling"]
    if len(s) < min_ops:
        return math.nan, len(s)
    d = [
        vote(len(consonantal(str(b))) - len(consonantal(str(a))))
        for a, b in zip(s.a_form, s.b_form, strict=True)
    ]
    return float(np.mean(d)), len(s)


def smoothing_sign(ops: pd.DataFrame, freq: dict[str, int], min_ops: int) -> tuple[float, int]:
    """(mean over substitutions of the sign of log-frequency B − A; their count). Keys without a
    content lemma (`~l`) are left out; a `+`-joined key counts its rarest lemma."""

    def f(key: Any) -> float | None:
        if not isinstance(key, str) or key.startswith("~"):
            return None
        counts = [freq.get(k, 0) for k in key.split("+")]
        return math.log(1 + min(counts))

    s = ops[ops.op == "substitution"]
    d = []
    for a, b in zip(s.a_key, s.b_key, strict=True):
        fa, fb = f(a), f(b)
        if fa is not None and fb is not None:
            d.append(vote(fb - fa))
    if len(d) < min_ops:
        return math.nan, len(d)
    return float(np.mean(d)), len(d)


def expansion_sign(ops: pd.DataFrame, n_words: int, min_ops: int) -> float:
    """(added − omitted) / words of the aligned pairs (NaN under `min_ops` of either)."""
    added, omitted = int((ops.op == "added").sum()), int((ops.op == "omitted").sum())
    if added + omitted < min_ops or n_words == 0:
        return math.nan
    return (added - omitted) / n_words


def language_sign(
    a: pd.Series, b: pd.Series, prior: dict[str, float], shrink: float, sd: pd.Series, signs: dict
) -> float:
    """Σ sign_f · (rate_f(B) − rate_f(A)) / sd_f over the language features."""
    r = rates(pd.DataFrame([a, b]), prior, shrink)
    return float(sum(signs[f] * (r[f].iloc[1] - r[f].iloc[0]) / sd[f] for f in signs if sd[f] > 0))


def known_direction(a_book: int, b_book: int, known: list[dict[str, str]]) -> str | None:
    for k in known:
        s, t = BY_OSIS[k["source"]].book_id, BY_OSIS[k["target"]].book_id
        if (s, t) == (a_book, b_book):
            return "a_to_b"
        if (t, s) == (a_book, b_book):
            return "b_to_a"
    return None


def agreement(scores: pd.Series, truth: pd.Series) -> dict[str, Any]:
    """How often a score's sign matches the known direction (+1 = A → B), zeros left out."""
    t = truth.map({"a_to_b": 1, "b_to_a": -1})
    v = scores.map(vote)
    ok = (v != 0) & t.notna()
    agree = int((v[ok] == t[ok]).sum())
    n = int(ok.sum())
    return {"agree": agree, "n": n, "p": float(f"{sign_test(agree, n):.3g}") if n else None}


def run_borrowing(cfg: dict[str, Any], log: Log = print) -> Path:
    t0 = time.perf_counter()
    bc, dc = cfg["borrowing"], cfg["dating"]
    proc, art = resolve_path(cfg, "data_processed"), resolve_path(cfg, "artifacts")
    for k in bc["known"]:
        for o in (k["source"], k["target"]):
            if o not in BY_OSIS:
                raise RuntimeError(f"borrowing: unknown book {o!r}")
    seq_path, diff_path = art / "sequences" / "verse.parquet", art / "diffs" / "changes.parquet"
    for p, cmd in ((seq_path, "sequences"), (diff_path, "diffs")):
        if not p.exists():
            raise RuntimeError(f"{p} missing; run `bsim {cmd}` first")
    seqs = pd.read_parquet(seq_path)
    changes = pd.read_parquet(diff_path)
    seqs = seqs[seqs.seq_id.isin(set(changes.seq_id)) & (seqs.a_book != seqs.b_book)]

    verses = pd.read_parquet(proc / "verses.parquet", columns=["verse_id", "book_id", "chapter"])
    words = pd.read_parquet(
        proc / "words.parquet", columns=["verse_id", "surface", "lemma", "morph", "content_lemmas"]
    )
    flags = word_flags(words, {str(x) for x in dc["lexemes"]})
    per_verse = flags.groupby("verse_id").sum().reindex(verses.verse_id, fill_value=0)
    chap_key = (verses.book_id.astype(str) + ":" + verses.chapter.astype(str)).to_numpy()
    per_chap = per_verse.groupby(chap_key).sum()
    per_chap = per_chap[per_chap.word >= dc["min_words"]]
    prior = priors(per_chap)
    sd = rates(per_chap, prior, dc["shrink"]).std()
    signs = {f: int(s) for f, s in bc["language_signs"].items() if f in RATES}
    freq = Counter(lem for cl in words.content_lemmas for lem in cl)
    n_words = per_verse.word

    rows = []
    for s in seqs.itertuples(index=False):
        pairs = json.loads(s.pairs) if isinstance(s.pairs, str) else list(s.pairs)
        a_ids = sorted({int(p[0]) for p in pairs})
        b_ids = sorted({int(p[1]) for p in pairs})
        ops = changes[changes.seq_id == s.seq_id]
        diffed = ops[["a", "b"]].drop_duplicates()
        aligned_words = int(n_words.loc[sorted(set(diffed.a))].sum())
        lang = language_sign(
            per_verse.loc[a_ids].sum(), per_verse.loc[b_ids].sum(), prior, dc["shrink"], sd, signs
        )
        spell, n_spell = spelling_sign(ops, bc["min_ops"])
        smooth, n_subst = smoothing_sign(ops, freq, bc["min_ops"])
        expand = expansion_sign(ops, aligned_words, bc["min_ops"])
        rows.append(
            {
                "seq_id": int(s.seq_id),
                "a_book": int(s.a_book),
                "b_book": int(s.b_book),
                "a_start": int(s.a_start),
                "a_end": int(s.a_end),
                "b_start": int(s.b_start),
                "b_end": int(s.b_end),
                "n_pairs": int(s.n_pairs),
                "language": round(lang, 4),
                "spelling": None if math.isnan(spell) else round(spell, 4),
                "smoothing": None if math.isnan(smooth) else round(smooth, 4),
                "expansion": None if math.isnan(expand) else round(expand, 4),
                "n_spelling": n_spell,
                "n_substitution": n_subst,
                "known": known_direction(int(s.a_book), int(s.b_book), bc["known"]),
            }
        )
    out = pd.DataFrame(rows)
    if out.empty:
        raise RuntimeError("borrowing: no cross-book parallel sequences with word-level diffs")

    known = out[out.known.notna()]
    checks = {sign: agreement(known[sign].astype(float), known.known) for sign in SIGNS}
    alpha = bc["select_p"]
    used = select_signs(known, alpha)
    held_out = cross_check(known, alpha)
    checks["all_signs"] = agreement(votes(known, list(SIGNS)), known.known)
    out["votes"] = votes(out, used).astype(int)
    out["n_votes"] = sum((out[s].astype(float).map(vote) != 0).astype(int) for s in used)
    out["direction"] = direction(out.votes)
    known = out[out.known.notna()]
    groups = (
        known.assign(ok=lambda d: d.direction == d.known)
        .groupby(["a_book", "b_book"])
        .agg(sequences=("seq_id", "size"), right=("ok", "sum"))
        .reset_index()
    )
    books = (
        out.groupby(["a_book", "b_book"])
        .agg(
            sequences=("seq_id", "size"),
            n_pairs=("n_pairs", "sum"),
            votes=("votes", "sum"),
            a_to_b=("direction", lambda d: int((d == "a_to_b").sum())),
            b_to_a=("direction", lambda d: int((d == "b_to_a").sum())),
            known=("known", "first"),
        )
        .reset_index()
    )
    books["direction"] = np.where(
        books.votes > 0, "a_to_b", np.where(books.votes < 0, "b_to_a", "unclear")
    )
    out_dir = art / "borrowing"
    out_dir.mkdir(parents=True, exist_ok=True)
    out.to_parquet(out_dir / "sequences.parquet")
    books.to_parquet(out_dir / "books.parquet")
    meta = {
        "config_hash": config_hash(cfg, "borrowing", "dating"),
        "sequences": len(out),
        "book_pairs": len(books),
        "known_sequences": len(known),
        "checks": checks,
        "used_signs": used,
        "held_out": held_out,
        "used_vote": agreement(known.votes.astype(float), known.known),
        "known_groups": groups.astype(int).to_dict("records"),
        "seconds": round(time.perf_counter() - t0, 1),
    }
    (out_dir / "borrowing.meta.json").write_text(json.dumps(meta, indent=2) + "\n", "utf-8")
    log(
        f"{len(out)} cross-book parallels over {len(books)} book pairs; known direction:"
        f" {len(known)} sequences"
    )
    for sign, c in checks.items():
        log(f"  {sign}: right {c['agree']} / {c['n']} (sign test p {c['p']})")
    log(
        f"  signs used: {', '.join(used)}; chosen without each book pair and scored on it:"
        f" right {held_out['agree']} / {held_out['n']} (p {held_out['p']}),"
        f" {held_out['unclear']} unclear"
    )
    return out_dir


def votes(df: pd.DataFrame, signs: list[str]) -> pd.Series:
    """Sum of the signs' votes per row (a missing sign votes 0)."""
    if not signs:
        return pd.Series(0, index=df.index)
    return sum(df[s].astype(float).map(vote) for s in signs)


def direction(v: pd.Series) -> np.ndarray:
    return np.where(v > 0, "a_to_b", np.where(v < 0, "b_to_a", "unclear"))


def select_signs(known: pd.DataFrame, alpha: float) -> list[str]:
    """The signs right more often than not on the known directions, with sign test p < alpha."""
    out = []
    for s in SIGNS:
        c = agreement(known[s].astype(float), known.known)
        if c["n"] and c["agree"] * 2 > c["n"] and c["p"] < alpha:
            out.append(s)
    return out


def cross_check(known: pd.DataFrame, alpha: float) -> dict[str, Any]:
    """Each known book pair voted on with the signs selected on the other pairs: an honest
    accuracy of choosing the signs on the check itself."""
    right = n = unclear = 0
    for _, g in known.groupby(["a_book", "b_book"]):
        used = select_signs(known.drop(g.index), alpha)
        d = direction(votes(g, used))
        unclear += int((d == "unclear").sum())
        decided = d != "unclear"
        n += int(decided.sum())
        right += int((d[decided] == g.known.to_numpy()[decided]).sum())
    return {
        "agree": right,
        "n": n,
        "unclear": unclear,
        "p": float(f"{sign_test(right, n):.3g}") if n else None,
    }
