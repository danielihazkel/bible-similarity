"""`bsim retold`: what changes when something said or told is told again (DESIGN.md §16.68).

The woman tells the serpent what God said in the garden, and adds "nor touch it" (Gen 3:3);
Abraham's servant tells Laban his master's charge, and leaves out "do not take my son back
there" (Gen 24:37-41). Sternberg's "structure of repetition": a retelling shows its teller. Does
speech retold by another speaker change more than speech carried out in narration, where a
command is told again as done?

- **Tellers.** Every word belongs to the narrator or to the speaker of the narrated quotation whose
  extent holds it (`bsim dialogue`; a quotation quoted inside a speech belongs to the one who
  quotes it). A run of one teller is cut into pieces of at most `chunk_tokens` content tokens.
- **Retellings.** For each piece, the windows of earlier verses of its book within `max_back` (as
  many verses as the piece spans, + `margin` either side) that share the most idf with it (lemmas
  in more than `seed_df` of verses left out, at least `seed_min`) are seeds; around each (before
  the piece, not the piece's own teller run) the piece is aligned with Smith-Waterman as `bsim
  phrases` (a token matches by lemma or by form). The best alignment with `min_tokens` and
  `min_score` is a retelling; its part of the piece is masked and the next looked for
  (`per_piece`).
- **Changes.** The two spans (first to last aligned word) are diffed word by word as `bsim diffs`
  (Needleman-Wunsch over lemma keys): the *change rate* is the share of aligned positions that
  are substituted, omitted, added or moved (a change of spelling or form keeps the word).
- **Groups.** `retold` (a speech told again by another known speaker), `repeated` (by the same
  speaker), `carried` (a speech told again by the narrator: command and execution, prediction
  and fulfilment), `told` (narration told in a speech), `narrated` (narration told again by the
  narrator), `unclear` (a speech with an unknown speaker on either side).
- **Claim fixed in advance:** `retold` pairs change more than `carried` pairs, the group labels
  shuffled within quantiles (`bins`) of the aligned length (`shuffles`), one-sided at `alpha`.
- **Known answers.** The retellings of `known` are found: a pair with its source in `source`
  and its retelling in `retelling`.

Writes `artifacts/retold/`: `pairs.parquet` (`pair, book_id, group, src_first, src_last,
src_unit, src_teller, later_first, later_last, later_unit, later_teller, n_tokens, score, n_ops,
n_changed, rate`, a count per op, `known`), `marks.parquet` (`pair, side` (a: the source, b: the
retelling), `verse_id, display_idx, op`: every word that is not the same) and `retold.meta.json`.
"""

from __future__ import annotations

import json
import math
import time
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from scipy import sparse

from bsim.analysis.brackets import Tok, token_forms
from bsim.analysis.diffs import align_words, make_word
from bsim.analysis.phrases import align, token_weights
from bsim.analysis.stats import empirical_p
from bsim.config import config_hash, resolve_path
from bsim.data.refs import RefIndex
from bsim.lexical.tokens import lemma_streams

Log = Callable[[str], None]

NARRATOR = -1
OPS = ("same", "spelling", "form", "substitution", "omitted", "added", "moved")
CHANGED = {"substitution", "omitted", "added", "moved"}
GROUPS = ("retold", "repeated", "carried", "told", "narrated", "unclear")


class Masked(Tok):
    """A token taken out of a piece: it matches nothing."""

    def __eq__(self, other: object) -> bool:
        return False

    __hash__ = None  # type: ignore[assignment]


def teller_units(clauses: pd.DataFrame, quotes: pd.DataFrame) -> np.ndarray:
    """Per clause (in clause order): the narrated quotation whose extent holds it, the outermost
    (NARRATOR outside any); a quotation outside every narrated extent stands for itself."""
    c = clauses.sort_values("clause", ignore_index=True)
    unit = np.full(len(c), NARRATOR, dtype=np.int64)
    for q in quotes[quotes.narrated].sort_values("start").itertuples(index=False):
        if unit[q.start] == NARRATOR:
            span = unit[q.start : q.end + 1]
            span[span == NARRATOR] = q.quote
    alone = (unit == NARRATOR) & (c.quote.to_numpy() >= 0)
    unit[alone] = c.quote.to_numpy()[alone]
    return unit


def word_units(clauses: pd.DataFrame, unit: np.ndarray) -> dict[tuple[int, int], int]:
    """(verse_id, idx) -> its teller unit, by the word's innermost (last) clause."""
    c = clauses.sort_values("clause", ignore_index=True).assign(unit=unit)
    w = c[["verse_id", "words", "unit"]].explode("words").dropna(subset=["words"])
    w = w.drop_duplicates(["verse_id", "words"], keep="last")
    return {(int(v), int(i)): int(u) for v, i, u in zip(w.verse_id, w.words, w.unit, strict=True)}


@dataclass
class Piece:
    t0: int  # global token range [t0, t1)
    t1: int
    unit: int  # its teller: a narrated quotation, or NARRATOR
    run: int  # its run of one teller (the narrator's runs are told apart)
    book: int
    first: int  # first and last verse
    last: int


def runs(tok_unit: np.ndarray, tok_book: np.ndarray) -> np.ndarray:
    """Per token: its run of one teller in one book (numbered in order)."""
    change = np.ones(len(tok_unit), dtype=bool)
    change[1:] = (tok_unit[1:] != tok_unit[:-1]) | (tok_book[1:] != tok_book[:-1])
    return np.cumsum(change) - 1


def pieces(
    tok_unit: np.ndarray, tok_book: np.ndarray, tok_verse: np.ndarray, size: int
) -> list[Piece]:
    """Runs of one teller in one book, cut into equal pieces of at most `size` tokens."""
    out = []
    run = runs(tok_unit, tok_book)
    n = len(tok_unit)
    i = 0
    while i < n:
        j = i
        while j < n and run[j] == run[i]:
            j += 1
        k = math.ceil((j - i) / size)
        bounds = np.linspace(i, j, k + 1).round().astype(int)
        for a, b in zip(bounds[:-1], bounds[1:], strict=True):
            out.append(Piece(int(a), int(b), int(tok_unit[i]), int(run[i]), int(tok_book[i]),
                             int(tok_verse[a]), int(tok_verse[b - 1])))  # fmt: skip
        i = j
    return out


@dataclass
class Text:
    """The tokens in reading order and what the search needs of them."""

    toks: list[Tok]
    wts: list[float]
    run: np.ndarray  # per token
    verse_tok: np.ndarray  # verse v's tokens: [verse_tok[v], verse_tok[v + 1])


def seeds_of(p: Piece, row: sparse.csr_matrix, lo: int, rc: dict[str, Any]) -> list[int]:
    """The centres of the windows of earlier verses (lo .. before the piece; as many verses as the
    piece spans, + margin either side) sharing the most idf with it, at least `seed_min`, each
    farther than the window from a stronger one. A window, not a verse: a retelling in common
    words shares little with any one verse of its source (Gen 24:37-41)."""
    if p.first <= lo:
        return []
    shared = np.zeros(p.first - lo)
    keep = (row.indices >= lo) & (row.indices < p.first)
    shared[row.indices[keep] - lo] = row.data[keep]
    width = p.last - p.first + 1 + 2 * int(rc["margin"])
    window = np.convolve(shared, np.ones(width), mode="same")
    order = np.lexsort((np.arange(len(window)), -window))
    seeds: list[int] = []
    for i in order:
        if window[i] < rc["seed_min"]:
            break
        if all(abs(lo + int(i) - s) > width for s in seeds):
            seeds.append(lo + int(i))
        if len(seeds) == rc["seeds"]:
            break
    return seeds


def find_in_piece(
    p: Piece, seeds: list[int], lo: int, text: Text, rc: dict[str, Any], pc: dict[str, Any]
) -> list[tuple[list[int], list[int], float]]:
    """(source tokens, retelling tokens, score) of each retelling found in a piece: the best
    alignment over the seeds' windows (not the piece's own run), its part masked, again."""
    span = p.last - p.first + 1
    mine = list(text.toks[p.t0 : p.t1])
    mine_w = text.wts[p.t0 : p.t1]
    out = []
    for _ in range(int(rc["per_piece"])):
        best = None
        for s in seeds:
            v0 = max(lo, s - span - rc["margin"])
            v1 = min(p.first - 1, s + span + rc["margin"])
            region = [t for t in range(text.verse_tok[v0], text.verse_tok[v1 + 1])
                      if text.run[t] != p.run]  # fmt: skip
            if not region:
                continue
            al = align(mine, [text.toks[t] for t in region], mine_w,
                       [text.wts[t] for t in region], pc["mismatch"], pc["gap"])  # fmt: skip
            ok = len(al.a_pos) >= rc["min_tokens"] and al.score >= rc["min_score"]
            if ok and (best is None or al.score > best[0].score):
                best = (al, region)
        if best is None:
            break
        al, region = best
        out.append(([region[j] for j in al.b_pos], [p.t0 + i for i in al.a_pos], al.score))
        for i in range(al.a_pos[0], al.a_pos[-1] + 1):
            mine[i] = Masked("", "")
    return out


def group_of(src_kind: str, src_teller: Any, later_kind: str, later_teller: Any) -> str:
    known = isinstance(src_teller, str) and isinstance(later_teller, str)
    if src_kind == "speech" and later_kind == "speech":
        if not known:
            return "unclear"
        return "repeated" if src_teller == later_teller else "retold"
    if src_kind == "speech":
        return "carried"
    return "told" if later_kind == "speech" else "narrated"


def stratified_p(
    rate: np.ndarray, is_a: np.ndarray, strata: np.ndarray, reps: int, rng: np.random.Generator
) -> tuple[float, float]:
    """mean(rate | a) - mean(rate | not a), and its one-sided p with the labels shuffled within
    each stratum."""

    def diff(lab: np.ndarray) -> float:
        return float(rate[lab].mean() - rate[~lab].mean())

    obs = diff(is_a)
    null = np.empty(reps)
    groups = [np.flatnonzero(strata == s) for s in np.unique(strata)]
    lab = is_a.copy()
    for r in range(reps):
        for g in groups:
            lab[g] = rng.permutation(is_a[g])
        null[r] = diff(lab)
    return obs, empirical_p(obs - 1e-12, null)


def run_retold(cfg: dict[str, Any], log: Log = print) -> Path:
    rc, pc, dc = cfg["retold"], cfg["phrases"], cfg["diffs"]
    proc, art = resolve_path(cfg, "data_processed"), resolve_path(cfg, "artifacts")
    t0 = time.perf_counter()
    verses = pd.read_parquet(
        proc / "verses.parquet", columns=["verse_id", "book_id", "chapter", "verse"]
    ).sort_values("verse_id")
    words = pd.read_parquet(
        proc / "words.parquet",
        columns=["verse_id", "idx", "surface", "lemma", "content_lemmas", "display_idx"],
    ).sort_values(["verse_id", "idx"], kind="stable", ignore_index=True)
    clauses = pd.read_parquet(
        proc / "syntax_clauses.parquet", columns=["clause", "verse_id", "words", "quote"]
    )
    quotes = pd.read_parquet(art / "dialogue" / "quotations.parquet")
    n = len(verses)
    book = verses.book_id.to_numpy()
    rng = np.random.default_rng(rc["seed"])

    # tellers
    unit_of = word_units(clauses, teller_units(clauses, quotes))
    teller = dict(zip(quotes.quote, quotes.speaker_party, strict=True))
    words["unit"] = [unit_of.get((int(v), int(i)), NARRATOR)
                     for v, i in zip(words.verse_id, words.idx, strict=True)]  # fmt: skip
    pos = {
        (int(v), int(i)): k for k, (v, i) in enumerate(zip(words.verse_id, words.idx, strict=True))
    }

    # tokens in reading order, with their word, weight and teller
    streams = lemma_streams(words, n)
    weights = token_weights(streams, cfg["lexical"]["formulas"])
    forms = token_forms(words, streams)
    toks, wts, tok_word, tok_verse = [], [], [], []
    for v, s in enumerate(streams):
        for k, (lem, widx) in enumerate(zip(s.tokens, s.word_idx, strict=True)):
            toks.append(Tok(lem, forms[v][k]))
            wts.append(float(weights[v][k]))
            tok_word.append(pos[(v, widx)])
            tok_verse.append(v)
    tok_word_a, tok_verse_a = np.array(tok_word), np.array(tok_verse)
    w_unit = words.unit.to_numpy()
    tok_unit = w_unit[tok_word_a]
    tok_book = book[tok_verse_a]
    ps = pieces(tok_unit, tok_book, tok_verse_a, int(rc["chunk_tokens"]))
    verse_tok = np.searchsorted(tok_verse_a, np.arange(n + 1))  # verse v's tokens: [vt[v], vt[v+1])
    log(f"{len(toks)} tokens, {len(ps)} pieces")

    # seeds: earlier verses sharing the most idf with each piece
    lem_codes, vocab = pd.factorize(pd.Series([t.lemma for t in toks], dtype=object))
    df = np.bincount(np.unique(np.stack([lem_codes, tok_verse_a]), axis=1)[0], minlength=len(vocab))
    idf = np.log(n / np.maximum(df, 1)) * (df <= rc["seed_df"] * n)
    vmat = sparse.csr_matrix((np.ones(len(toks)), (tok_verse_a, lem_codes)), shape=(n, len(vocab)))
    vmat.data[:] = 1
    vmat = sparse.csr_matrix(vmat.multiply(idf[None, :]))
    pid = np.repeat(np.arange(len(ps)), [p.t1 - p.t0 for p in ps])
    piece_tok = np.concatenate([np.arange(p.t0, p.t1) for p in ps]) if ps else np.zeros(0, int)
    pmat = sparse.csr_matrix(
        (np.ones(len(pid)), (pid, lem_codes[piece_tok])), shape=(len(ps), len(vocab))
    )
    pmat.data[:] = 1
    shared = sparse.csr_matrix(pmat @ vmat.T)

    first_of_book = verses.groupby("book_id").verse_id.min()
    text = Text(toks, wts, runs(tok_unit, tok_book), verse_tok)
    rows, marks = [], []
    for k, p in enumerate(ps):
        if p.t1 - p.t0 < rc["min_tokens"]:
            continue
        lo = max(int(first_of_book[p.book]), p.first - int(rc["max_back"]))
        seeds = seeds_of(p, shared.getrow(k), lo, rc)
        for src_t, later_t, score in find_in_piece(p, seeds, lo, text, rc, pc):
            rows.append((k, src_t, later_t, score))

    log(f"{len(rows)} retellings")

    # diff each pair word by word, and group it
    ws = [
        make_word(int(i), c, lem, s)
        for i, c, lem, s in zip(
            words.idx, words.content_lemmas, words.lemma, words.surface, strict=True
        )
    ]
    w_verse = words.verse_id.to_numpy()
    w_disp = words.display_idx.to_numpy()
    out_rows = []
    for n_pair, (k, src_t, later_t, score) in enumerate(rows):
        p = ps[k]
        a0, a1 = tok_word[src_t[0]], tok_word[src_t[-1]]
        b0, b1 = tok_word[later_t[0]], tok_word[later_t[-1]]
        ops = align_words(ws[a0 : a1 + 1], ws[b0 : b1 + 1], dc["match"], dc["mismatch"], dc["gap"])
        count = Counter(o.op for o in ops)
        for o in ops:
            if o.op == "same":
                continue
            for side, i, base in (("a", o.a, a0), ("b", o.b, b0)):
                if i is not None and not pd.isna(w_disp[base + i]):
                    marks.append(
                        (n_pair, side, int(w_verse[base + i]), int(w_disp[base + i]), o.op)
                    )
        src_unit = Counter(int(w_unit[i]) for i in range(a0, a1 + 1)).most_common(1)[0][0]
        src_kind = "narration" if src_unit == NARRATOR else "speech"
        later_kind = "narration" if p.unit == NARRATOR else "speech"
        st = teller.get(src_unit) if src_kind == "speech" else None
        lt = teller.get(p.unit) if later_kind == "speech" else None
        st = st if isinstance(st, str) else None
        lt = lt if isinstance(lt, str) else None
        changed = sum(count[o] for o in CHANGED)
        out_rows.append({
            "pair": n_pair, "book_id": p.book,
            "group": group_of(src_kind, st, later_kind, lt),
            "src_first": int(w_verse[a0]), "src_last": int(w_verse[a1]), "src_unit": src_unit,
            "src_teller": st, "later_first": int(w_verse[b0]), "later_last": int(w_verse[b1]),
            "later_unit": p.unit, "later_teller": lt, "n_tokens": len(later_t),
            "score": round(float(score), 3), "n_ops": len(ops), "n_changed": changed,
            "rate": changed / len(ops) if ops else 0.0, **{o: count[o] for o in OPS},
        })  # fmt: skip
    pairs = pd.DataFrame(out_rows, columns=[
        "pair", "book_id", "group", "src_first", "src_last", "src_unit", "src_teller",
        "later_first", "later_last", "later_unit", "later_teller", "n_tokens", "score", "n_ops",
        "n_changed", "rate", *OPS,
    ])  # fmt: skip

    # the claim: retold against carried, within length strata
    a_grp, b_grp = rc["claim"]
    sel = pairs[pairs.group.isin([a_grp, b_grp])]
    reps, alpha = int(rc["shuffles"]), float(rc["alpha"])
    if (sel.group == a_grp).any() and (sel.group == b_grp).any():
        edges = np.quantile(sel.n_ops, np.linspace(0, 1, int(rc["bins"]) + 1)[1:-1])
        strata = np.searchsorted(edges, sel.n_ops.to_numpy(), side="right")
        diff, p = stratified_p(sel.rate.to_numpy(), (sel.group == a_grp).to_numpy(), strata,
                               reps, rng)  # fmt: skip
    else:
        diff, p = float("nan"), 1.0
    rate = {g: float(pairs[pairs.group == g].rate.mean()) if (pairs.group == g).any() else None
            for g in GROUPS}  # fmt: skip
    holds = bool(diff > 0 and p <= alpha)
    log(
        f"change rate {a_grp} {rate[a_grp]:.3f}, {b_grp} {rate[b_grp]:.3f}:"
        f" difference {diff:.3f}, p {p:.4g}"
    )

    # the known retellings
    index = RefIndex(verses)
    known_rows, known_of = [], set()
    for kn in rc["known"]:
        s0, s1 = index.resolve(kn["source"])
        l0, l1 = index.resolve(kn["retelling"])
        hit = pairs[(pairs.src_first <= s1) & (pairs.src_last >= s0)
                    & (pairs.later_first <= l1) & (pairs.later_last >= l0)]  # fmt: skip
        row: dict[str, Any] = {"source": kn["source"], "retelling": kn["retelling"],
                               "found": not hit.empty, "pairs": [int(x) for x in hit.pair],
                               "group": None, "rate": None}  # fmt: skip
        if not hit.empty:
            known_of |= set(int(x) for x in hit.pair)
            row.update(group=str(hit.group.iloc[0]),
                       rate=float(hit.n_changed.sum() / max(1, hit.n_ops.sum())))  # fmt: skip
        known_rows.append(row)
    pairs["known"] = pairs.pair.isin(known_of)
    known_holds = bool(known_rows) and all(r["found"] for r in known_rows)
    log(f"known: {sum(r['found'] for r in known_rows)} of {len(known_rows)} found")

    out = art / "retold"
    out.mkdir(parents=True, exist_ok=True)
    pairs.to_parquet(out / "pairs.parquet", index=False)
    pd.DataFrame(marks, columns=["pair", "side", "verse_id", "display_idx", "op"]).to_parquet(
        out / "marks.parquet", index=False
    )
    meta = {
        "config_hash": config_hash(
            cfg, "retold", "phrases", "diffs", "lexical", "dialogue", "syntax"
        ),  # fmt: skip
        "built_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "pieces": len(ps),
        "pairs": int(len(pairs)),
        "groups": {g: int((pairs.group == g).sum()) for g in GROUPS},
        "rates": rate,
        "claim": [a_grp, b_grp],
        "difference": None if math.isnan(diff) else round(diff, 4),
        "p": p,
        "shuffles": reps,
        "bins": int(rc["bins"]),
        "alpha": alpha,
        "holds": holds,
        "known": known_rows,
        "known_found": sum(r["found"] for r in known_rows),
        "known_holds": known_holds,
        "seconds": round(time.perf_counter() - t0, 1),
    }
    (out / "retold.meta.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False), "utf-8")
    log(
        f"done: {len(pairs)} retellings {meta['groups']}; the claim"
        f" {'holds' if holds else 'is not borne out'}; the known"
        f" {'found' if known_holds else 'not all found'} ({meta['seconds']} s) -> {out}"
    )
    return out / "pairs.parquet"
