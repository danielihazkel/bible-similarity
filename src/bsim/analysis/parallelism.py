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

Finer structure (DESIGN.md §16.18):

- `clauses`: the spans between the pauses of accent level 1–2 (`text.accents.clauses`);
- `next_prob`: a bicolon may span two verses. For two consecutive one-colon verses of a chapter,
  the same four features are measured between the verses and scored with the same model;
  `next_prob` sits on the first verse (NULL elsewhere);
- word pairs: the content lemmas that recur across the two members of parallel lines (verse
  halves with `prob ≥ parallel_at`, verse pairs with `next_prob ≥ parallel_at`) more than their
  frequencies predict — the fixed word pairs of Hebrew poetry (ארץ // תבל, יעקב // ישראל).
  Ordered pairs (x in the first member, y in the second, x ≠ y, function words skipped) seen at
  least `pair_min_count` times in at least `pair_min_chapters` chapters (one list's formulas, an
  itinerary or an offering table, stay out); Dunning's G² over the member pairs, p from χ²(1) when
  over-represented, Benjamini–Hochberg q.

Typing (DESIGN.md §16.22, with `bsim lexicon`): each pair of parallel members is `antithetic`
when a lemma of one half and a different lemma of the other are SDBH antonyms (צדיק / רשע,
חכם / כסיל), else `synonymous` when they are SDBH synonyms or two different lemmas share a
semantic domain; a verse takes its strongest pair's type. The check that the negation cue of
D49 failed: the antithetic share of Prov 10–15 (`typing_check`) against the other parallel
lines (one-sided Fisher), and the overall antithetic share against `typing_null_reps` shuffles
that pair each first half with another line's second half.

Writes `artifacts/parallelism/verses.parquet`: `verse_id, n_cola, cola` (JSON inclusive display
token spans), `pauses` (JSON accent names), `cos, shared, shape, balance, prob` (NULL for one
colon), `clauses` (JSON spans), `next_prob`; `word_pairs.parquet` (`a_lemma, b_lemma, n,
expected, g2, p, q, reverse`, the count of the pair in the other order, and `examples`, JSON
verse ids); `relation` (antithetic | synonymous | NULL) and `relation_pairs` (JSON
`[a, b, kind]`, kind antonym | synonym | domain) on parallel verses; plus `parallelism.meta.json`.
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

from bsim.analysis.stats import bh_q, g2_table
from bsim.config import config_hash, resolve_path
from bsim.data.canon import BOOKS, BY_OSIS
from bsim.data.lexicon import strong_key
from bsim.lexical.morph import word_token
from bsim.retrieve.topk import CSLS_SUFFIX, get_device
from bsim.text.accents import clauses, cola, pauses, poetic
from bsim.text.normalize import consonantal

Log = Callable[[str], None]

FEATURES = ("cos", "shared", "shape", "balance")


def segment(
    verses: pd.DataFrame,
) -> tuple[list[list[tuple[int, int]]], list[list[str]], list[list[tuple[int, int]]]]:
    """Per verse: colon spans, the names of the pauses between them, and clause spans."""
    osis = {b.book_id: b.osis for b in BOOKS}
    spans, names, finer = [], [], []
    for toks, book, chapter, verse in zip(
        verses.display_tokens, verses.book_id, verses.chapter, verses.verse, strict=True
    ):
        toks = list(toks)
        p = poetic(osis[book], chapter, verse)
        spans.append(cola(toks, p))
        names.append([n for _, n in pauses(toks, p)])
        finer.append(clauses(toks, p))
    return spans, names, finer


def bag(vid: int, span: tuple[int, int], lemmas: dict, shapes: dict) -> tuple[set, Counter]:
    s, e = span
    return (
        {x for t in range(s, e + 1) for x in lemmas.get((vid, t), [])},
        Counter(x for t in range(s, e + 1) for x in shapes.get((vid, t), [])),
    )


def word_pairs(
    members: list[tuple[set[str], set[str], int]],
    skip: set[str],
    min_count: int,
    chapter_of: dict[int, int] | None = None,
    min_chapters: int = 1,
) -> pd.DataFrame:
    """Over-represented ordered lemma pairs across the two members of parallel lines
    (`members`: first member's lemmas, second's, verse id); a pair must occur in at least
    `min_chapters` chapters (`chapter_of`: verse id -> chapter key), which keeps the formulas of
    one list (an itinerary, an offering table) out."""
    from scipy.stats import chi2

    n_first: Counter[str] = Counter()
    n_second: Counter[str] = Counter()
    pair: Counter[tuple[str, str]] = Counter()
    chapters: dict[tuple[str, str], set[int]] = {}
    examples: dict[tuple[str, str], list[int]] = {}
    for a, b, vid in members:
        a, b = a - skip, b - skip
        n_first.update(a)
        n_second.update(b)
        for x in a:
            for y in b:
                if x != y:
                    pair[(x, y)] += 1
                    if chapter_of is not None:
                        chapters.setdefault((x, y), set()).add(chapter_of[vid])
                    ex = examples.setdefault((x, y), [])
                    if len(ex) < 5:
                        ex.append(vid)
    total = len(members)
    rows = []
    for (x, y), n in pair.items():
        if n < min_count or (chapter_of is not None and len(chapters[(x, y)]) < min_chapters):
            continue
        r, c = n_first[x], n_second[y]
        expected = r * c / total
        g2 = g2_table(n, r, c, total)
        p = float(chi2.sf(g2, 1)) if n > expected else 1.0
        rows.append(
            (
                x,
                y,
                n,
                round(expected, 3),
                round(float(g2), 3),
                p,
                pair.get((y, x), 0),
                json.dumps(examples[(x, y)]),
            )
        )
    df = pd.DataFrame(
        rows, columns=["a_lemma", "b_lemma", "n", "expected", "g2", "p", "reverse", "examples"]
    )
    df["q"] = bh_q(df.p.to_numpy()) if len(df) else []
    return df.sort_values(["q", "g2"], ascending=[True, False], ignore_index=True)


Relations = tuple[set[tuple[str, str]], set[tuple[str, str]]]  # antonym, synonym (Strong keys)


def load_relations(proc: Path, words: pd.DataFrame) -> tuple[Relations, dict] | None:
    """SDBH antonym / synonym pairs, and (verse_id, display_idx) -> {(strong, domain)} of the
    content words; None without `bsim lexicon`."""
    rel_path, sense_path = proc / "lexicon_relations.parquet", proc / "word_senses.parquet"
    if not (rel_path.exists() and sense_path.exists()):
        return None
    rel = pd.read_parquet(rel_path)
    pairs = {k: set(zip(g.a, g.b, strict=True)) for k, g in rel.groupby("kind")}
    senses = pd.read_parquet(sense_path, columns=["verse_id", "idx", "strong", "domains"])
    w = words.dropna(subset=["display_idx"])
    content = {
        (v, i): (int(d), {strong_key(c) for c in cl})
        for v, i, d, cl in zip(w.verse_id, w.idx, w.display_idx, w.content_lemmas, strict=True)
    }
    domains: dict[tuple[int, int], set[tuple[str, str]]] = {}
    for v, i, s, ds in zip(senses.verse_id, senses.idx, senses.strong, senses.domains, strict=True):
        hit = content.get((v, i))
        if hit is not None and s in hit[1]:
            domains.setdefault((v, hit[0]), set()).update((s, d) for d in ds)
    return (pairs.get("antonym", set()), pairs.get("synonym", set())), domains


def span_domains(vid: int, span: tuple[int, int], domains: dict) -> set[tuple[str, str]]:
    s, e = span
    return {x for t in range(s, e + 1) for x in domains.get((vid, t), ())}


def line_relation(
    a: set[str], b: set[str], a_dom: set, b_dom: set, rel: Relations
) -> tuple[str | None, list[tuple[str, str, str]]]:
    """The type of two parallel members and the word pairs that make it, as the members'
    content lemmas (`rel` and the domain sets are keyed by `strong_key`)."""
    ant, syn = rel
    ka = {strong_key(x): x for x in sorted(a)}
    kb = {strong_key(x): x for x in sorted(b)}
    found = sorted(
        (ka[x], kb[y], "antonym") for x in ka for y in kb if x != y and (x, y) in ant
    )
    if found:
        return "antithetic", found
    found = sorted(
        (ka[x], kb[y], "synonym") for x in ka for y in kb if x != y and (x, y) in syn
    )
    found += sorted(
        {
            (ka.get(x, x), kb.get(y, y), "domain")
            for x, d in a_dom
            for y, e in b_dom
            if d == e and x != y and x not in kb and y not in ka and (x, y) not in syn
        }
    )
    return ("synonymous", found) if found else (None, [])


def typing_check(
    lines: list[tuple[int, str | None]],
    members: list[tuple[set, set, set, set]],
    rel: Relations,
    in_check: Callable[[int], bool],
    reps: int,
    seed: int,
) -> dict[str, Any]:
    """Antithetic share of the checked chapters vs the other parallel lines (one-sided Fisher),
    and overall vs second halves shuffled between lines."""
    from scipy.stats import fisher_exact

    anti = np.array([r == "antithetic" for _, r in lines], dtype=bool)
    inside = np.array([in_check(v) for v, _ in lines], dtype=bool)
    a, b = int(anti[inside].sum()), int(inside.sum())
    c, d = int(anti[~inside].sum()), int((~inside).sum())
    p = float(fisher_exact([[a, b - a], [c, d - c]], alternative="greater")[1]) if b and d else 1.0
    rng = np.random.default_rng(seed)
    observed = [line_relation(*m, rel)[0] == "antithetic" for m in members]
    null = []
    for _ in range(reps):
        perm = rng.permutation(len(members))
        null.append(
            np.mean(
                [
                    line_relation(m[0], members[j][1], m[2], members[j][3], rel)[0] == "antithetic"
                    for m, j in zip(members, perm, strict=True)
                ]
            )
        )
    share = float(np.mean(observed)) if observed else 0.0
    return {
        "lines": len(lines),
        "antithetic": int(anti.sum()),
        "synonymous": int(sum(r == "synonymous" for _, r in lines)),
        "antithetic_share": round(float(anti.mean()), 4) if len(lines) else 0.0,
        "member_pairs": len(members),
        "pair_antithetic_share": round(share, 4),
        "null_share": round(float(np.mean(null)), 4) if null else None,
        "null_p": float((1 + sum(x >= share for x in null)) / (1 + reps)) if null else None,
        "check_share": round(a / b, 4) if b else None,
        "check_lines": b,
        "rest_share": round(c / d, 4) if d else None,
        "check_p": p,
    }


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


def lemma_pos(words: pd.DataFrame) -> dict[str, str]:
    """Each content lemma's most common part of speech (OSHB letter)."""
    from bsim.store.db import lemma_parts_pos  # store.db imports the analysis modules

    pos: dict[str, Counter[str]] = {}
    for lemma, morph in zip(words.lemma, words.morph, strict=True):
        for lem, p in lemma_parts_pos(lemma, morph).items():
            pos.setdefault(lem, Counter())[p] += 1
    return {lem: c.most_common(1)[0][0] for lem, c in pos.items()}


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
        proc / "words.parquet",
        columns=["verse_id", "idx", "display_idx", "lemma", "content_lemmas", "morph"],
    )
    t0 = time.perf_counter()
    spans, names, finer = segment(verses)
    multi = [vid for vid, s in enumerate(spans) if len(s) >= 2]
    log(f"cola: {Counter(len(s) for s in spans)}; {len(multi)} verses with 2+ cola")
    chapter_key = verses.book_id.to_numpy() * 1000 + verses.chapter.to_numpy()
    cross = [
        vid
        for vid in range(len(spans) - 1)
        if len(spans[vid]) == 1
        and len(spans[vid + 1]) == 1
        and chapter_key[vid] == chapter_key[vid + 1]
    ]
    single = sorted({v for vid in cross for v in (vid, vid + 1)})
    log(f"{len(cross)} pairs of consecutive one-colon verses")

    texts, first = [], {}
    for vid in multi + single:
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

    # bicola across two verses: the same features between consecutive one-colon verses
    nxt = []
    for vid in cross:
        a = bag(vid, spans[vid][0], lemmas, shapes)
        b = bag(vid + 1, spans[vid + 1][0], lemmas, shapes)
        f = pair_features(a[0], b[0], a[1], b[1], float(emb[first[vid]] @ emb[first[vid + 1]]))
        nxt.append([f[k] for k in FEATURES])
    next_prob = dict(
        zip(cross, model.predict_proba(np.array(nxt))[:, 1] if nxt else [], strict=True)
    )

    # fixed word pairs across the members of parallel lines
    at = pc["parallel_at"]
    skip_pos = set(cfg["structure"]["leitwort_skip_pos"])
    skip = {lem for lem, p in lemma_pos(words).items() if p in skip_pos}
    members = []
    for vid, prob in zip(df.verse_id, df.prob, strict=True):
        if prob >= at:
            b = [bag(vid, sp, lemmas, shapes)[0] for sp in spans[vid]]
            members += [(b[k], b[k + 1], vid) for k in range(len(b) - 1)]
    for vid, prob in next_prob.items():
        if prob >= at:
            members.append(
                (
                    bag(vid, spans[vid][0], lemmas, shapes)[0],
                    bag(vid + 1, spans[vid + 1][0], lemmas, shapes)[0],
                    vid,
                )
            )
    # synonymous / antithetic lines from the SDBH lexicon
    relation: dict[int, str | None] = {}
    relation_pairs: dict[int, list] = {}
    typing = None
    lex = load_relations(proc, words)
    if lex is None:
        log("  no lexicon (`bsim lexicon`): parallel lines are not typed")
    else:
        rel, domains = lex
        rank = {"antithetic": 2, "synonymous": 1, None: 0}
        lines, typed = [], []
        for vid, prob in zip(df.verse_id, df.prob, strict=True):
            if prob < at:
                continue
            best, found = None, []
            for k in range(len(spans[vid]) - 1):
                sa, sb = spans[vid][k], spans[vid][k + 1]
                m = (
                    bag(vid, sa, lemmas, shapes)[0],
                    bag(vid, sb, lemmas, shapes)[0],
                    span_domains(vid, sa, domains),
                    span_domains(vid, sb, domains),
                )
                typed.append(m)
                r, pairs = line_relation(*m, rel)
                if rank[r] > rank[best]:
                    best, found = r, pairs
                elif r == best:
                    found += pairs
            relation[vid], relation_pairs[vid] = best, found[: pc["typing_max_pairs"]]
            lines.append((vid, best))
        book_of = dict(zip(verses.verse_id, verses.book_id, strict=True))
        chap_of = dict(zip(verses.verse_id, verses.chapter, strict=True))
        check = {BY_OSIS[o].book_id: rng for o, rng in pc["typing_check"].items()}

        def in_check(vid: int) -> bool:
            r = check.get(book_of[vid])
            return r is not None and r[0] <= chap_of[vid] <= r[1]

        typing = typing_check(lines, typed, rel, in_check, pc["typing_null_reps"], pc["seed"])
        log(
            f"typed {typing['lines']} parallel verses: {typing['antithetic']} antithetic, "
            f"{typing['synonymous']} synonymous; antithetic member pairs "
            f"{typing['pair_antithetic_share']:.1%} vs {typing['null_share']:.1%} shuffled; "
            f"{pc['typing_check']}: {typing['check_share']:.1%} of verses vs "
            f"{typing['rest_share']:.1%} elsewhere (p {typing['check_p']:.2g})"
        )

    chapter_of = dict(zip(verses.verse_id, chapter_key.tolist(), strict=True))
    pairs_df = word_pairs(members, skip, pc["pair_min_count"], chapter_of, pc["pair_min_chapters"])
    poems = known_poem_ranks(df, neg, list(pc["known_poems"]), pc["min_chapter_verses"])

    out_df = verses[["verse_id"]].assign(
        n_cola=[len(s) for s in spans],
        cola=[json.dumps([list(x) for x in s]) for s in spans],
        pauses=[json.dumps(n) for n in names],
        clauses=[json.dumps([list(x) for x in s]) for s in finer],
        next_prob=[next_prob.get(v) for v in verses.verse_id],
        relation=[relation.get(v) for v in verses.verse_id],
        relation_pairs=[
            json.dumps([list(p) for p in relation_pairs[v]]) if v in relation_pairs else None
            for v in verses.verse_id
        ],
    )
    out_df = out_df.merge(df[["verse_id", *FEATURES, "prob"]], on="verse_id", how="left")
    out = resolve_path(cfg, "artifacts") / "parallelism"
    out.mkdir(parents=True, exist_ok=True)
    out_df.to_parquet(out / "verses.parquet")
    pairs_df.to_parquet(out / "word_pairs.parquet")
    lr = model[-1]
    meta = {
        "config_hash": config_hash(
            cfg, "parallelism", "final_systems", "structure.leitwort_skip_pos"
        ),
        "built_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "encoder": base,
        "cola": {str(k): v for k, v in sorted(Counter(len(s) for s in spans).items())},
        "train_verses": int(len(train)),
        "coefficients": dict(zip(FEATURES, (round(float(c), 4) for c in lr.coef_[0]), strict=True)),
        "held_out_auc": aucs,
        "known_poems": poems,
        "cross_pairs": len(cross),
        "cross_parallel": int(sum(p >= at for p in next_prob.values())),
        "parallel_members": len(members),
        "word_pairs": int(len(pairs_df)),
        "word_pairs_q_below_0.05": int((pairs_df.q <= 0.05).sum()) if len(pairs_df) else 0,
        "typing": typing,
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
