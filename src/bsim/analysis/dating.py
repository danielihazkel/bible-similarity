"""`bsim dating`: a Late Biblical Hebrew profile of every chapter (DESIGN.md §16.24).

Late Biblical Hebrew (LBH: Chronicles, Ezra–Nehemiah, Esther, Daniel) differs from the Hebrew of
Genesis–Kings (Standard, SBH) in words, grammar and spelling (Hurvitz, Polzin, Rooker). Whether
such features can date a text is disputed (Young, Rezetko & Ehrensvärd), so this is a profile, not
a date: how much a chapter's language resembles the undisputed late books.

Per chapter, over its Hebrew words (Aramaic words, morph `A…`, left out; chapters with fewer than
`min_words` Hebrew words are not scored), each feature of `dating.features` is a rate, shrunk
towards the training mean by `shrink` pseudo-counts (`(k + a·μ) / (n + a)`), so a chapter without
the context of a feature (no David, no first-person pronoun) sits at the mean:

- `lbh_lexemes`: the LBH words of `lexemes` (מלכות, אגרת, מדינה, דת, יחש, …) per word;
- `anokhi`: אנכי among the first-person singular pronouns (אני / אנכי);
- `inf_abs`: infinitive absolutes among the verbs;
- `et_suffix`: את with a pronoun suffix (אתו) against a suffix on the verb (ויקחהו);
- `directional_he`: the directional ה (מצרימה) per word;
- `cohortative_wayyiqtol`: first-person singular wayyiqtols written with a final ה (ואשלחה);
- `david_plene`: דויד among the spellings of David.

A logistic regression (standardized, `C`) learns `late` books against `early` ones; `score` is its
probability for every chapter. Checks, in the meta:

- leave-one-book-out AUC over the training books, with all features and grammar / spelling only
  (without `lbh_lexemes`, whose words also carry topics: Persian courts, letters, decrees);
- the synoptic test: trained without Samuel, Kings and Chronicles, the model scores both sides of
  every parallel sequence between Samuel–Kings and Chronicles (`bsim sequences`): the same
  content, two states of the language. The share of pairs where Chronicles scores later, with a
  two-sided sign test;
- chapters of the poetic books (`poetic`), and any chapter whose verse halves are parallel in at
  least `poetic_share` of its verses (`bsim parallelism`: poems inside prose), are flagged
  `out_of_domain`: the model is calibrated on prose, and poetry also drops את and the directional
  ה.

`drivers` lists the features that push a chapter's score up most (coefficient × standardized
value, positive only), so every score can be read back to its evidence.

Writes `artifacts/dating/chapters.parquet` (`unit_id, book_id, chapter, n_words, role` early |
late | scored, `out_of_domain`, one column per feature, `score, drivers` JSON), `books.parquet`
(`book_id, role, out_of_domain, n_chapters, score` = the mean, `low, high` = its 10th / 90th
chapter percentiles, the features' book rates), `dating.meta.json`.
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

from bsim.config import config_hash, resolve_path
from bsim.data.canon import BOOKS, BY_OSIS
from bsim.text.normalize import consonantal

Log = Callable[[str], None]

FEATURES = (
    "lbh_lexemes",
    "anokhi",
    "inf_abs",
    "et_suffix",
    "directional_he",
    "cohortative_wayyiqtol",
    "david_plene",
)
GRAMMAR = tuple(f for f in FEATURES if f != "lbh_lexemes")


def word_flags(words: pd.DataFrame, lexemes: set[str]) -> pd.DataFrame:
    """Per Hebrew word the counts (numerator, denominator) each feature needs."""
    morph = words.morph.fillna("").astype(str)
    hebrew = ~morph.str.startswith("A")
    w = words[hebrew]
    parts = [m[1:].split("/") for m in morph[hebrew]]
    lem = [[x.replace(" ", "") for x in str(lemma).split("/")] for lemma in w.lemma]
    bare = [[x.rstrip("abcdefgh") for x in p] for p in lem]
    cons = [consonantal(s) for s in w.surface.astype(str)]
    verb = [next((x for x in p if x.startswith("V")), "") for p in parts]
    vtype = [v[2] if len(v) > 2 else "" for v in verb]
    suffix = [any(x.startswith("Sp") for x in p) for p in parts]
    first_person = [("1cs" in "".join(p)) for p in parts]
    out = pd.DataFrame(
        {
            "verse_id": w.verse_id.to_numpy(),
            "word": 1,
            "lex": [any(x in lexemes for x in b) for b in bare],
            "anokhi": [("595" in b) for b in bare],
            "pron_1cs": [("595" in b) or ("589" in b) for b in bare],
            "inf_abs": [t == "a" for t in vtype],
            "verb": [bool(v) for v in verb],
            "et_suffix": [("853" in b) and s for b, s in zip(bare, suffix, strict=True)],
            "verb_suffix": [bool(v) and s for v, s in zip(verb, suffix, strict=True)],
            "directional_he": ["Sd" in p for p in parts],
            "way1cs": [t == "w" and f for t, f in zip(vtype, first_person, strict=True)],
            "way1cs_h": [
                t == "w" and f and c.endswith("ה")
                for t, f, c in zip(vtype, first_person, cons, strict=True)
            ],
            "david": [("1732" in b) for b in bare],
            "david_plene": [("1732" in b) and "דויד" in c for b, c in zip(bare, cons, strict=True)],
        }
    )
    return out.astype({c: int for c in out.columns if c != "verse_id"})


# feature -> (numerator, denominator) columns of `word_flags`
RATES = {
    "lbh_lexemes": ("lex", "word"),
    "anokhi": ("anokhi", "pron_1cs"),
    "inf_abs": ("inf_abs", "verb"),
    "et_suffix": ("et_suffix", "et_or_verb_suffix"),
    "directional_he": ("directional_he", "word"),
    "cohortative_wayyiqtol": ("way1cs_h", "way1cs"),
    "david_plene": ("david_plene", "david"),
}


def rates(counts: pd.DataFrame, prior: dict[str, float], shrink: float) -> pd.DataFrame:
    """Shrunk feature rates of aggregated counts: `(k + a·μ) / (n + a)`."""
    c = counts.assign(et_or_verb_suffix=counts.et_suffix + counts.verb_suffix)
    return pd.DataFrame(
        {f: (c[num] + shrink * prior[f]) / (c[den] + shrink) for f, (num, den) in RATES.items()},
        index=counts.index,
    )


def priors(counts: pd.DataFrame) -> dict[str, float]:
    """Pooled rate of every feature over `counts` (the training chapters)."""
    c = counts.sum().to_dict()
    c["et_or_verb_suffix"] = c["et_suffix"] + c["verb_suffix"]
    return {f: c[num] / max(c[den], 1) for f, (num, den) in RATES.items()}


def fit(x: np.ndarray, y: np.ndarray, c: float) -> Any:
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler

    return make_pipeline(StandardScaler(), LogisticRegression(C=c, max_iter=1000)).fit(x, y)


def held_out_auc(x: pd.DataFrame, y: np.ndarray, books: np.ndarray, c: float) -> dict[str, Any]:
    """Leave-one-book-out probabilities of the training chapters: pooled AUC and, per book, the
    mean probability of its chapters when it was held out."""
    from sklearn.metrics import roc_auc_score

    prob = np.empty(len(y))
    for b in np.unique(books):
        out = books == b
        prob[out] = fit(x[~out].to_numpy(), y[~out], c).predict_proba(x[out].to_numpy())[:, 1]
    return {
        "auc": round(float(roc_auc_score(y, prob)), 4),
        "books": {str(b): round(float(prob[books == b].mean()), 4) for b in np.unique(books)},
    }


def sign_test(wins: int, n: int) -> float:
    from scipy.stats import binomtest

    return float(binomtest(wins, n, 0.5).pvalue) if n else 1.0


def synoptic_test(
    cfg: dict[str, Any],
    per_verse: pd.DataFrame,
    x: pd.DataFrame,
    y: np.ndarray,
    train: pd.Series,
    books: np.ndarray,
    prior: dict[str, float],
    log: Log,
) -> dict[str, Any]:
    """Both sides of the parallel sequences between `synoptic.a` and `synoptic.b` books, scored
    by models that saw neither: how often the `b` side (Chronicles) scores later."""
    dc = cfg["dating"]
    sy = dc["synoptic"]
    a_books = {BY_OSIS[o].book_id for o in sy["a"]}
    b_books = {BY_OSIS[o].book_id for o in sy["b"]}
    path = resolve_path(cfg, "artifacts") / "sequences" / "verse.parquet"
    empty = {"pairs": 0, "later": 0, "p": 1.0, "later_grammar": 0, "p_grammar": 1.0, "examples": []}
    if not path.exists():
        log(f"  {path} missing (`bsim sequences`): no synoptic test")
        return empty
    seq = pd.read_parquet(path)
    if "direction" in seq:
        seq = seq[seq.direction == "forward"]
    seq = seq[seq.q <= sy["max_q"]]
    keep = train & ~np.isin(books, list(a_books | b_books))
    full = fit(x[keep].to_numpy(), y[keep], dc["C"])
    grammar = fit(x.loc[keep, list(GRAMMAR)].to_numpy(), y[keep], dc["C"])
    rows = []
    for r in seq.itertuples():
        if {r.a_book, r.b_book} & a_books and {r.a_book, r.b_book} & b_books:
            if r.a_book in b_books:  # orient: a = Samuel-Kings, b = Chronicles
                sides = ((r.b_start, r.b_end), (r.a_start, r.a_end))
            else:
                sides = ((r.a_start, r.a_end), (r.b_start, r.b_end))
            counts = pd.DataFrame(
                [per_verse.loc[s:e].sum() for s, e in sides], index=["early", "late"]
            )
            if counts.word.min() < sy["min_words"]:
                continue
            f = rates(counts, prior, dc["shrink"])
            p_full = full.predict_proba(f.to_numpy())[:, 1]
            p_gram = grammar.predict_proba(f[list(GRAMMAR)].to_numpy())[:, 1]
            rows.append((sides, p_full, p_gram, int(counts.word.min())))
    if not rows:
        return empty
    later = sum(int(p[1] > p[0]) for _, p, _, _ in rows)
    later_g = sum(int(g[1] > g[0]) for _, _, g, _ in rows)
    gaps = sorted(rows, key=lambda r: -(r[1][1] - r[1][0]))
    return {
        "pairs": len(rows),
        "later": later,
        "p": sign_test(later, len(rows)),
        "later_grammar": later_g,
        "p_grammar": sign_test(later_g, len(rows)),
        "mean_early": round(float(np.mean([p[0] for _, p, _, _ in rows])), 4),
        "mean_late": round(float(np.mean([p[1] for _, p, _, _ in rows])), 4),
        "examples": [
            {
                "early": [int(s[0][0]), int(s[0][1])],
                "late": [int(s[1][0]), int(s[1][1])],
                "early_score": round(float(p[0]), 4),
                "late_score": round(float(p[1]), 4),
            }
            for s, p, _, _ in gaps[: sy["examples"]]
        ],
    }


def poetic_chapters(cfg: dict[str, Any], verses: pd.DataFrame) -> set[str]:
    """`book:chapter` keys whose share of parallel verse halves reaches `dating.poetic_share`."""
    path = resolve_path(cfg, "artifacts") / "parallelism" / "verses.parquet"
    if not path.exists():
        return set()
    par = pd.read_parquet(path, columns=["verse_id", "prob"]).merge(verses, on="verse_id")
    par = par.dropna(subset=["prob"]).assign(
        parallel=lambda d: d.prob >= cfg["parallelism"]["parallel_at"]
    )
    share = par.groupby(["book_id", "chapter"]).parallel.mean()
    n = verses.groupby(["book_id", "chapter"]).size()
    share = (share * par.groupby(["book_id", "chapter"]).size() / n).dropna()
    return {f"{b}:{c}" for (b, c), s in share.items() if s >= cfg["dating"]["poetic_share"]}


def drivers(model: Any, x: pd.DataFrame, top: int) -> list[str]:
    """Per row the features pushing the score up most (coefficient × standardized value)."""
    scaler, lr = model[0], model[-1]
    contrib = (x.to_numpy() - scaler.mean_) / scaler.scale_ * lr.coef_[0]
    out = []
    for row in contrib:
        order = np.argsort(-row)
        out.append(json.dumps([FEATURES[i] for i in order[:top] if row[i] > 0.25]))
    return out


def run_dating(cfg: dict[str, Any], log: Log = print) -> Path:
    proc = resolve_path(cfg, "data_processed")
    dc = cfg["dating"]
    t0 = time.perf_counter()
    for o in [*dc["early"], *dc["late"], *dc["poetic"], *dc["synoptic"]["a"], *dc["synoptic"]["b"]]:
        if o not in BY_OSIS:
            raise RuntimeError(f"dating: unknown book {o!r}")
    verses = pd.read_parquet(proc / "verses.parquet", columns=["verse_id", "book_id", "chapter"])
    words = pd.read_parquet(
        proc / "words.parquet", columns=["verse_id", "surface", "lemma", "morph"]
    )
    flags = word_flags(words, {str(x) for x in dc["lexemes"]})
    per_verse = flags.groupby("verse_id").sum()
    per_verse = per_verse.reindex(verses.verse_id, fill_value=0)
    chap_key = verses.book_id.astype(str) + ":" + verses.chapter.astype(str)
    per_chap = per_verse.groupby(chap_key.to_numpy()).sum()
    chapters = verses.drop_duplicates(["book_id", "chapter"]).assign(
        unit_id=lambda d: "c:" + d.book_id.astype(str) + ":" + d.chapter.astype(str)
    )
    chapters.index = chapters.book_id.astype(str) + ":" + chapters.chapter.astype(str)
    per_chap = per_chap.reindex(chapters.index)
    early = {BY_OSIS[o].book_id for o in dc["early"]}
    late = {BY_OSIS[o].book_id for o in dc["late"]}
    poetic = {BY_OSIS[o].book_id for o in dc["poetic"]}
    role = np.where(
        chapters.book_id.isin(late),
        "late",
        np.where(chapters.book_id.isin(early), "early", "scored"),
    )
    scored = per_chap.word >= dc["min_words"]
    train = scored & (role != "scored")
    for cls in ("early", "late"):
        if not (train & (role == cls)).any():
            raise RuntimeError(f"dating: no {cls} chapter with {dc['min_words']} Hebrew words")
    prior = priors(per_chap[train])
    x = rates(per_chap, prior, dc["shrink"])
    y = (role == "late").astype(int)
    books = chapters.book_id.to_numpy()

    model = fit(x[train].to_numpy(), y[train], dc["C"])
    score = pd.Series(np.nan, index=x.index)
    score[scored] = model.predict_proba(x[scored].to_numpy())[:, 1]
    loo = held_out_auc(x[train], y[train], books[train], dc["C"])
    loo_grammar = held_out_auc(x.loc[train, list(GRAMMAR)], y[train], books[train], dc["C"])
    # chapters of the training books are scored by the model that did not see their book
    held = pd.Series(np.nan, index=x.index)
    for b in np.unique(books[train]):
        out = train & (books == b)
        m = fit(x[train & ~out].to_numpy(), y[train & ~out], dc["C"])
        held[out] = m.predict_proba(x[out].to_numpy())[:, 1]
    score[train] = held[train]  # never a chapter's own book in its model

    synoptic = synoptic_test(cfg, per_verse, x, y, train, books, prior, log)

    out_df = chapters.assign(
        n_words=per_chap.word.to_numpy(),
        role=role,
        out_of_domain=(
            chapters.book_id.isin(poetic) | chapters.index.isin(poetic_chapters(cfg, verses))
        ).to_numpy(),
        score=score.to_numpy(),
        drivers=drivers(model, x, dc["drivers"]),
    )
    for f in FEATURES:
        out_df[f] = x[f].to_numpy()
    out_df = out_df[
        [
            "unit_id",
            "book_id",
            "chapter",
            "n_words",
            "role",
            "out_of_domain",
            *FEATURES,
            "score",
            "drivers",
        ]
    ].reset_index(drop=True)
    book_counts = per_verse.groupby(verses.book_id.to_numpy()).sum()
    book_rates = rates(book_counts, prior, dc["shrink"])
    book_rows = []
    for b in BOOKS:
        s = out_df[(out_df.book_id == b.book_id) & out_df.score.notna()].score
        book_rows.append(
            {
                "book_id": b.book_id,
                "role": "late"
                if b.book_id in late
                else "early"
                if b.book_id in early
                else "scored",
                "out_of_domain": b.book_id in poetic,
                "n_chapters": int(len(s)),
                "score": float(s.mean()) if len(s) else None,
                "low": float(s.quantile(0.1)) if len(s) else None,
                "high": float(s.quantile(0.9)) if len(s) else None,
                **{f: float(book_rates.loc[b.book_id, f]) for f in FEATURES},
            }
        )
    lr = model[-1]
    out = resolve_path(cfg, "artifacts") / "dating"
    out.mkdir(parents=True, exist_ok=True)
    out_df.to_parquet(out / "chapters.parquet")
    pd.DataFrame(book_rows).to_parquet(out / "books.parquet")
    meta = {
        "config_hash": config_hash(cfg, "dating"),
        "built_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "features": list(FEATURES),
        "coefficients": dict(zip(FEATURES, (round(float(c), 4) for c in lr.coef_[0]), strict=True)),
        "prior": {f: round(v, 6) for f, v in prior.items()},
        "train_chapters": {
            "early": int((train & (role == "early")).sum()),
            "late": int((train & (role == "late")).sum()),
        },
        "held_out_auc": loo["auc"],
        "held_out_auc_grammar": loo_grammar["auc"],
        "held_out_books": loo["books"],
        "synoptic": synoptic,
        "seconds": round(time.perf_counter() - t0, 1),
    }
    (out / "dating.meta.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False), "utf-8")
    log(
        f"done: held-out AUC {loo['auc']} (grammar / spelling only {loo_grammar['auc']}); "
        f"synoptic: Chronicles later in {synoptic['later']} of {synoptic['pairs']} parallels "
        f"(p {synoptic['p']:.2g}; grammar only {synoptic['later_grammar']}) "
        f"in {meta['seconds']} s -> {out}"
    )
    return out
