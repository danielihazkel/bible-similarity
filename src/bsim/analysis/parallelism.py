"""`bsim parallelism`: how parallel the two halves of each verse are (DESIGN.md §16.9).

The te'amim divide every verse into cola (`text.accents`: etnahta; oleh-ve-yored in the poetic
books). For each pair of consecutive cola four relation features are measured:

- `cos`: cosine of the two cola, embedded with the final semantic encoder;
- `shared`: content lemmas the two cola share (poetry restates with other words, prose repeats);
- `shape`: overlap of their grammatical-shape tokens (`lexical.morph.word_token`), as a share of
  the longer colon;
- `balance`: shorter / longer colon length in display tokens.

A verse's features are the means over its pairs. Which combination marks parallelism is learned,
not hand-weighted: the poetic books carry their own accent system (Psalms, Proverbs, Job), so a
logistic regression (standardized features, `C`) is trained to tell their verses from narrative
and law (`train_negative` books). Only relations between the halves are features, never words,
book or verse length, so the model scores parallel structure rather than vocabulary. `prob` is
its probability for every verse with at least two cola; the other books (the prophets, Song,
Lamentations, ...) are never seen in training.

Checks (meta): the leave-one-poetic-book-out AUC, and where the poems embedded in prose books
(`known_poems`: Gen 49, Ex 15, Deut 32, ...) rank among the chapters of the narrative / law books
(they are negatives in training, so this is conservative).

Writes `artifacts/parallelism/verses.parquet`: `verse_id, n_cola, cola` (JSON inclusive display
token spans), `pauses` (JSON accent names), `cos, shared, shape, balance, prob` (NULL for one
colon), plus `parallelism.meta.json`.
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

from bsim.config import config_hash, resolve_path
from bsim.data.canon import BOOKS, BY_OSIS
from bsim.lexical.morph import word_token
from bsim.retrieve.topk import CSLS_SUFFIX, get_device
from bsim.text.accents import cola, pauses, poetic
from bsim.text.normalize import consonantal

Log = Callable[[str], None]

FEATURES = ("cos", "shared", "shape", "balance")


def segment(verses: pd.DataFrame) -> tuple[list[list[tuple[int, int]]], list[list[str]]]:
    """Per verse: colon spans and the names of the pauses between them."""
    osis = {b.book_id: b.osis for b in BOOKS}
    spans, names = [], []
    for toks, book, chapter, verse in zip(
        verses.display_tokens, verses.book_id, verses.chapter, verses.verse, strict=True
    ):
        toks = list(toks)
        p = poetic(osis[book], chapter, verse)
        spans.append(cola(toks, p))
        names.append([n for _, n in pauses(toks, p)])
    return spans, names


def token_bags(words: pd.DataFrame) -> tuple[dict, dict]:
    """(verse_id, display_idx) -> content lemmas, and -> shape tokens."""
    lemmas: dict[tuple[int, int], list[str]] = {}
    shapes: dict[tuple[int, int], list[str]] = {}
    for w in words.dropna(subset=["display_idx"]).itertuples(index=False):
        k = (int(w.verse_id), int(w.display_idx))
        lemmas.setdefault(k, []).extend(w.content_lemmas)
        shapes.setdefault(k, []).append(word_token(w.morph))
    return lemmas, shapes


def pair_features(
    a_lemmas: set[str], b_lemmas: set[str], a_shapes: Counter, b_shapes: Counter, cos: float
) -> dict[str, float]:
    na, nb = sum(a_shapes.values()), sum(b_shapes.values())
    return {
        "cos": cos,
        "shared": float(len(a_lemmas & b_lemmas)),
        "shape": sum((a_shapes & b_shapes).values()) / max(1, na, nb),
        "balance": min(na, nb) / max(1, na, nb),
    }


def verse_features(
    vid: int,
    spans: list[tuple[int, int]],
    emb: np.ndarray,
    lemmas: dict,
    shapes: dict,
) -> dict[str, float]:
    """Mean pair features of a verse; `emb` = its cola embeddings in order."""
    bags = [
        (
            {x for t in range(s, e + 1) for x in lemmas.get((vid, t), [])},
            Counter(x for t in range(s, e + 1) for x in shapes.get((vid, t), [])),
        )
        for s, e in spans
    ]
    pairs = [
        pair_features(
            bags[k][0], bags[k + 1][0], bags[k][1], bags[k + 1][1], float(emb[k] @ emb[k + 1])
        )
        for k in range(len(spans) - 1)
    ]
    return {f: float(np.mean([p[f] for p in pairs])) for f in FEATURES}


def fit_model(x: np.ndarray, y: np.ndarray, c: float) -> Any:
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler

    return make_pipeline(StandardScaler(), LogisticRegression(C=c, max_iter=1000)).fit(x, y)


def held_out_auc(df: pd.DataFrame, positive: list[str], c: float) -> dict[str, float]:
    """Leave one poetic book out (with a slice of the negatives) and score it."""
    from sklearn.metrics import roc_auc_score

    out = {}
    neg_books = sorted(df.loc[df.y == 0, "osis"].unique())
    for k, hold in enumerate(positive):
        held_neg = neg_books[k :: len(positive)]
        test = df.osis.eq(hold) | df.osis.isin(held_neg)
        model = fit_model(df.loc[~test, list(FEATURES)].to_numpy(), df.y[~test].to_numpy(), c)
        prob = model.predict_proba(df.loc[test, list(FEATURES)].to_numpy())[:, 1]
        out[hold] = round(float(roc_auc_score(df.y[test], prob)), 4)
    return out


def known_poem_ranks(
    df: pd.DataFrame, negative: list[str], poems: list[str], min_verses: int
) -> dict[str, Any]:
    """Rank of each known embedded poem among the chapters of the negative books."""
    ch = (
        df[df.osis.isin(negative)]
        .groupby(["osis", "chapter"])
        .agg(prob=("prob", "mean"), n=("prob", "size"))
        .reset_index()
    )
    ch = ch[ch.n >= min_verses].sort_values("prob", ascending=False, ignore_index=True)
    ch["name"] = ch.osis + " " + ch.chapter.astype(str)
    ranks = {p: int(ch.index[ch.name == p][0]) + 1 for p in poems if (ch.name == p).any()}
    return {"chapters": int(len(ch)), "ranks": ranks}


Encode = Callable[[list[str]], np.ndarray]  # texts -> L2-normalized float32 rows


def run_parallelism(cfg: dict[str, Any], log: Log = print, encode_fn: Encode | None = None) -> Path:
    """`encode_fn` replaces the encoder (tests)."""
    proc = resolve_path(cfg, "data_processed")
    pc = cfg["parallelism"]
    verses = pd.read_parquet(
        proc / "verses.parquet",
        columns=["verse_id", "book_id", "chapter", "verse", "display_tokens"],
    )
    words = pd.read_parquet(
        proc / "words.parquet", columns=["verse_id", "display_idx", "content_lemmas", "morph"]
    )
    t0 = time.perf_counter()
    spans, names = segment(verses)
    multi = [vid for vid, s in enumerate(spans) if len(s) >= 2]
    log(f"cola: {Counter(len(s) for s in spans)}; {len(multi)} verses with 2+ cola")

    texts, first = [], {}
    for vid in multi:
        toks = list(verses.display_tokens.iloc[vid])
        first[vid] = len(texts)
        texts += [consonantal(" ".join(toks[s : e + 1])) for s, e in spans[vid]]
    base = (pc["encoder"] or cfg["final_systems"]["semantic"]).removesuffix(CSLS_SUFFIX)
    emb = encode_fn(texts) if encode_fn else encode_cola(cfg, base, texts, log)

    lemmas, shapes = token_bags(words)
    feats = [
        verse_features(
            vid, spans[vid], emb[first[vid] : first[vid] + len(spans[vid])], lemmas, shapes
        )
        for vid in multi
    ]
    df = pd.DataFrame(feats).assign(verse_id=multi)
    osis = {b.book_id: b.osis for b in BOOKS}
    df = df.merge(verses[["verse_id", "book_id", "chapter"]], on="verse_id")
    df["osis"] = df.book_id.map(osis)
    pos, neg = list(pc["train_positive"]), list(pc["train_negative"])
    unknown = [o for o in pos + neg if o not in BY_OSIS]
    if unknown:
        raise RuntimeError(f"parallelism: unknown books {unknown}")
    train = df[df.osis.isin(pos + neg)].assign(y=lambda d: d.osis.isin(pos).astype(int))
    model = fit_model(train[list(FEATURES)].to_numpy(), train.y.to_numpy(), pc["C"])
    df["prob"] = model.predict_proba(df[list(FEATURES)].to_numpy())[:, 1]
    aucs = held_out_auc(train, pos, pc["C"])
    poems = known_poem_ranks(df, neg, list(pc["known_poems"]), pc["min_chapter_verses"])

    out_df = verses[["verse_id"]].assign(
        n_cola=[len(s) for s in spans],
        cola=[json.dumps([list(x) for x in s]) for s in spans],
        pauses=[json.dumps(n) for n in names],
    )
    out_df = out_df.merge(df[["verse_id", *FEATURES, "prob"]], on="verse_id", how="left")
    out = resolve_path(cfg, "artifacts") / "parallelism"
    out.mkdir(parents=True, exist_ok=True)
    out_df.to_parquet(out / "verses.parquet")
    lr = model[-1]
    meta = {
        "config_hash": config_hash(cfg, "parallelism", "final_systems"),
        "built_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "encoder": base,
        "cola": {str(k): v for k, v in sorted(Counter(len(s) for s in spans).items())},
        "train_verses": int(len(train)),
        "coefficients": dict(zip(FEATURES, (round(float(c), 4) for c in lr.coef_[0]), strict=True)),
        "held_out_auc": aucs,
        "known_poems": poems,
        "book_means": {
            o: round(float(g.prob.mean()), 4) for o, g in df.groupby("osis", sort=False)
        },
        "seconds": round(time.perf_counter() - t0, 1),
    }
    (out / "parallelism.meta.json").write_text(
        json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    log(
        f"done: AUC held out {aucs}; known poems among {poems['chapters']} prose chapters:"
        f" {poems['ranks']} ({meta['seconds']} s) -> {out / 'verses.parquet'}"
    )
    return out / "verses.parquet"


def encode_cola(cfg: dict[str, Any], system: str, texts: list[str], log: Log) -> np.ndarray:
    from bsim.embed.encoders import encode, load_encoder

    spec = cfg["encoders"]["systems"].get(system)
    if spec is None:
        raise RuntimeError(f"parallelism encoder {system!r} is not in encoders.systems")
    device = get_device(cfg["encoders"]["device"])
    log(f"embedding {len(texts)} cola with {system} on {device}")
    model = load_encoder(spec, cfg["text"]["max_seq_length"], str(device))
    return encode(model, texts, cfg["encoders"]["batch_size"])
