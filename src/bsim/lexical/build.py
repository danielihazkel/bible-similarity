"""`bsim lexical`: BM25 indexes, formulas and unit TF-IDF (DESIGN.md §5.1).

Writes to `paths.artifacts`/lexical:
    bm25_lemma.{doc,query}.npz + .vocab.json     verse-level BM25 over content lemmas
    bm25_surface.{doc,query}.npz + .vocab.json   same over surface forms (eval baseline)
    bm25_morph.{doc,query}.npz + .vocab.json     word-shape n-grams (structural mode, §16.5)
    bm25_domain.{doc,query}.npz + .vocab.json    SDBH semantic domains (§16.22; when `bsim lexicon`
                                                 has written word_senses.parquet)
    bm25_lemma_domain.{doc,query}.npz + .vocab.json   bm25_lemma's tokens + the domain tokens at
                                                 `lexical.domain.expansion_weight` (experiment)
    tfidf_domain_{chapter,pericope,parasha}.npz + .ids.json   unit TF-IDF over the same
    tfidf_morph_{chapter,pericope,parasha}.npz + .ids.json   unit TF-IDF over the same
    tfidf_{chapter,pericope,parasha}.npz + .ids.json   unit TF-IDF rows (L2-normalized)
    formulas.parquet                             closed lemma formulas
    lexical_meta.json, lexical_report.md
"""

from __future__ import annotations

import json
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import scipy.sparse as sp

from bsim.config import config_hash, resolve_path
from bsim.data.report import md_table
from bsim.lexical import bm25
from bsim.lexical.domains import domain_streams
from bsim.lexical.formulas import (
    Ngram,
    closed,
    formula_weights,
    formulas_frame,
    frequent_ngrams,
)
from bsim.lexical.morph import morph_streams, ngram_tokens
from bsim.lexical.tfidf import unit_tfidf
from bsim.lexical.tokens import Stream, lemma_streams, surface_streams, with_bigrams
from bsim.text.normalize import consonantal

Log = Callable[[str], None]

# Acceptance checks (TASKS.md M4)
EXPECTED_FORMULA = "1696 3068 413 4872 559"  # וידבר ה' אל משה לאמר
EXPECTED_PARALLEL = ("Psalms 14:1", "Psalms 53:2")


def prepare(
    streams: list[Stream], lex: dict[str, Any]
) -> tuple[list[list[str]], list[np.ndarray], dict[Ngram, int]]:
    """Formula detection + down-weighting, then bigrams: the token/weight lists to index."""
    f = lex["formulas"]
    ngrams = frequent_ngrams(streams, f["min_n"], f["max_n"], f["min_verses"])
    weights = formula_weights(streams, ngrams, f["weight"])
    tokens: list[list[str]] = []
    out_w: list[np.ndarray] = []
    for s, w in zip(streams, weights, strict=True):
        t, w2 = with_bigrams(s.tokens, w) if lex["bigrams"] else (s.tokens, w)
        tokens.append(t)
        out_w.append(w2)
    return tokens, out_w, ngrams


def spot_checks(
    index: bm25.Bm25Index, refs: list[str], queries: list[str], k: int = 5
) -> dict[str, list[tuple[str, float]]]:
    vid = {r: i for i, r in enumerate(refs)}
    found = [q for q in queries if q in vid]
    if not found:
        return {}
    idx, sc = bm25.topk_cpu(index, np.array([vid[q] for q in found]), k)
    return {
        q: [(refs[t], float(s)) for t, s in zip(idx[i], sc[i], strict=True)]
        for i, q in enumerate(found)
    }


def write_report(
    path: Path,
    sizes: dict[str, int],
    formulas: pd.DataFrame,
    checks: dict[str, dict[str, list[tuple[str, float]]]],
    cfg: dict[str, Any],
) -> None:
    f = cfg["lexical"]["formulas"]
    by_n = formulas.n.value_counts().sort_index()
    parts = [
        "# Lexical report",
        "",
        f"Built {datetime.now(UTC).isoformat(timespec='seconds')}; "
        f"BM25 k1={cfg['lexical']['bm25']['k1']} b={cfg['lexical']['bm25']['b']}, "
        f"bigrams={cfg['lexical']['bigrams']}, formulas n={f['min_n']}..{f['max_n']} "
        f"in > {f['min_verses']} verses, weight {f['weight']}.",
        "",
        "## Sizes",
        md_table(["item", "value"], [[k, v] for k, v in sizes.items()]),
        "",
        "## Closed lemma formulas per n",
        md_table(["n", "formulas"], [[n, c] for n, c in by_n.items()]),
        "",
        f"`{EXPECTED_FORMULA}` (וידבר ה' אל משה לאמר) present: "
        f"**{'yes' if (formulas.formula == EXPECTED_FORMULA).any() else 'NO'}**",
        "",
        "## Top 30 formulas by verse count",
        md_table(
            ["formula (lemmas)", "Hebrew", "n", "verses", "example"],
            [
                [r.formula, r.he, r.n, r.n_verses, r.example_ref]
                for r in formulas.head(30).itertuples()
            ],
        ),
    ]
    for system, per_query in checks.items():
        parts += ["", f"## Spot checks: {system} top-5"]
        for q, hits in per_query.items():
            parts += [
                "",
                f"**{q}**",
                md_table(
                    ["rank", "verse", "score"],
                    [[i + 1, ref, f"{s:.2f}"] for i, (ref, s) in enumerate(hits)],
                ),
            ]
    path.write_text("\n".join(parts) + "\n", encoding="utf-8")


def run_lexical(cfg: dict[str, Any], log: Log = print) -> None:
    proc = resolve_path(cfg, "data_processed")
    out = resolve_path(cfg, "artifacts") / "lexical"
    lex = cfg["lexical"]
    k1, b = lex["bm25"]["k1"], lex["bm25"]["b"]

    if not (proc / "words.parquet").exists():
        raise RuntimeError(f"{proc / 'words.parquet'} missing; run `bsim build-corpus` first")
    verses = pd.read_parquet(proc / "verses.parquet", columns=["verse_id", "ref"])
    words = pd.read_parquet(
        proc / "words.parquet", columns=["verse_id", "idx", "surface", "content_lemmas", "morph"]
    )
    units = pd.read_parquet(proc / "units.parquet", columns=["unit_id", "unit_type"])
    members = pd.read_parquet(proc / "unit_members.parquet")
    n = len(verses)
    refs = verses.sort_values("verse_id").ref.tolist()

    log("lemma streams and formulas")
    lemmas = lemma_streams(words, n)
    lem_tokens, lem_weights, ngrams = prepare(lemmas, lex)
    surfaces: list[list[str]] = [[] for _ in range(n)]
    for w in words.sort_values(["verse_id", "idx"]).itertuples(index=False):
        surfaces[w.verse_id].append(consonantal(w.surface))
    formulas = formulas_frame(closed(ngrams), lemmas, surfaces, refs)

    log("BM25 (lemmas)")
    lemma_index = bm25.build_bm25(lem_tokens, lem_weights, k1, b)
    log("BM25 (surface forms)")
    surf_tokens, surf_weights, surf_ngrams = prepare(surface_streams(words, n), lex)
    surface_index = bm25.build_bm25(surf_tokens, surf_weights, k1, b)
    log("BM25 (word-shape n-grams)")
    morph_tokens = [ngram_tokens(t, lex["morph"]["max_n"]) for t in morph_streams(words, n)]
    morph_weights = [np.ones(len(t)) for t in morph_tokens]
    morph_index = bm25.build_bm25(morph_tokens, morph_weights, k1, b)

    domain_tokens: list[list[str]] | None = None
    if (proc / "word_senses.parquet").exists():
        log("BM25 (semantic domains)")
        dc = lex["domain"]
        lemma_words = pd.read_parquet(
            proc / "words.parquet", columns=["verse_id", "idx", "content_lemmas"]
        )
        domain_tokens, domain_weights = domain_streams(
            pd.read_parquet(proc / "word_senses.parquet"),
            lemma_words,
            n,
            dc["ancestor_weight"],
            dc["content_only"],
        )
        domain_index = bm25.build_bm25(domain_tokens, domain_weights, k1, b)
        beta = dc["expansion_weight"]
        expanded_index = bm25.build_bm25(
            [a + d for a, d in zip(lem_tokens, domain_tokens, strict=True)],
            [
                np.concatenate([a, d * beta])
                for a, d in zip(lem_weights, domain_weights, strict=True)
            ],
            k1,
            b,
        )
    else:
        log(f"  {proc / 'word_senses.parquet'} missing (`bsim lexicon`): no bm25_domain")

    out.mkdir(parents=True, exist_ok=True)
    bm25.save(lemma_index, out, "bm25_lemma")
    bm25.save(surface_index, out, "bm25_surface")
    bm25.save(morph_index, out, "bm25_morph")
    if domain_tokens is not None:
        bm25.save(domain_index, out, "bm25_domain")
        bm25.save(expanded_index, out, "bm25_lemma_domain")
    formulas.to_parquet(out / "formulas.parquet", index=False)

    sizes = {
        "verses": n,
        "bm25_lemma vocabulary": len(lemma_index.vocab),
        "bm25_surface vocabulary": len(surface_index.vocab),
        "bm25_morph vocabulary": len(morph_index.vocab),
        "lemma n-grams over threshold": len(ngrams),
        "closed lemma formulas": len(formulas),
        "surface n-grams over threshold": len(surf_ngrams),
        **({"bm25_domain vocabulary": len(domain_index.vocab)} if domain_tokens else {}),
        "lemma tokens down-weighted": f"{np.mean(np.concatenate(lem_weights) < 1):.1%}",
    }
    for unit_type in [t for t in cfg["units"]["types"] if t != "verse"]:
        log(f"TF-IDF ({unit_type})")
        ids = units[units.unit_type == unit_type].unit_id.tolist()
        x = unit_tfidf(lem_tokens, lem_weights, members, ids)
        sp.save_npz(out / f"tfidf_{unit_type}.npz", x)
        (out / f"tfidf_{unit_type}.ids.json").write_text(json.dumps(ids), encoding="utf-8")
        xm = unit_tfidf(morph_tokens, morph_weights, members, ids)
        sp.save_npz(out / f"tfidf_morph_{unit_type}.npz", xm)
        (out / f"tfidf_morph_{unit_type}.ids.json").write_text(json.dumps(ids), encoding="utf-8")
        if domain_tokens is not None:
            xd = unit_tfidf(domain_tokens, domain_weights, members, ids)
            sp.save_npz(out / f"tfidf_domain_{unit_type}.npz", xd)
            (out / f"tfidf_domain_{unit_type}.ids.json").write_text(json.dumps(ids), "utf-8")
        sizes[f"{unit_type} units (TF-IDF)"] = len(ids)

    queries = cfg["eval"]["spot_checks"]
    checks = {
        "bm25_lemma": spot_checks(lemma_index, refs, queries),
        "bm25_surface": spot_checks(surface_index, refs, queries),
    }
    corpus_meta = json.loads((proc / "corpus_meta.json").read_text(encoding="utf-8"))
    meta = {
        "config_hash": config_hash(cfg, "lexical"),
        "corpus_config_hash": corpus_meta["config_hash"],
        "vocab": {
            "bm25_lemma": len(lemma_index.vocab),
            "bm25_surface": len(surface_index.vocab),
            "bm25_morph": len(morph_index.vocab),
            **({"bm25_domain": len(domain_index.vocab)} if domain_tokens else {}),
        },
        "built_at": datetime.now(UTC).isoformat(timespec="seconds"),
    }
    (out / "lexical_meta.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    write_report(out / "lexical_report.md", sizes, formulas, checks, cfg)

    if not (formulas.formula == EXPECTED_FORMULA).any():
        log(f"  warning: expected formula {EXPECTED_FORMULA} not detected")
    src, tgt = EXPECTED_PARALLEL
    top = [r for r, _ in spot_checks(lemma_index, refs, [src]).get(src, [])]
    if tgt not in top:
        log(f"  warning: {tgt} not in the bm25_lemma top-5 of {src}: {top}")
    log(f"done: {len(formulas)} formulas, lemma vocab {len(lemma_index.vocab)}; wrote {out}")
