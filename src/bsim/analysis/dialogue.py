"""`bsim dialogue`: who speaks to whom (DESIGN.md §16.44).

`bsim syntax` gives every quotation its speaker and, since §16.44, its addressee and how it was
found (`explicit`: the introduction's אל / ל complement or the object of צוה; `vocative`;
`pronoun`: אליו resolved to the other party; `turn`: a bare ויאמר answering the previous
speaker). This stage turns them into conversations:

- **Quotations:** one row per quotation with its speaker, addressee, words, "your servant" forms
  (`deference` lemmas with a second-person suffix), imperatives and imperatives followed by נא.
  A quotation's words are those whose innermost clause is in it; its extent runs until the text
  is back at a shallower level or the next quotation at its level starts.
- **Pairs:** per book, speaker -> addressee with quotations and words (`n_reliable`: those with a
  `reliable` addressee).
- **Exchanges:** runs of quotations at one level of one book, each starting at most
  `exchange_gap` clauses after the previous one's extent, between exactly two known speakers who
  both speak. Defined by the speakers alone, so the `turn` rule (which assumes alternation) does
  not make them.

Rank: God (`syntax.divine`) 2, a king (`kings`) 1, anyone else 0. Checks fixed in advance
(`checks`, one-sided at `alpha`):
1. **deference**: "your servant" per 1,000 words, in quotations addressed up (to a higher rank
   than the speaker's) minus the rest, among quotations with a `reliable` addressee not spoken
   by God; null: the "up" label permuted over the quotations of each book (`shuffles`).
2. **particle**: the share of imperatives followed by נא, the same way.
3. **last_word**: among exchanges between parties of different rank, how many the higher one
   ends, against its share of the turns (each exchange's last turn drawn at random from its
   turns, `shuffles` times).
Sensitivity: checks 1-2 over every addressee source. Described without a verdict: who opens,
and whether the higher party's turns are longer (sign test).

Writes `artifacts/dialogue/`: `quotations.parquet`, `pairs.parquet`, `exchanges.parquet` and
`dialogue.meta.json`.
"""

from __future__ import annotations

import json
import re
import time
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

import numpy as np
import pandas as pd
from scipy.stats import binomtest

from bsim.analysis.stats import empirical_p, permute_within
from bsim.config import config_hash, resolve_path
from bsim.data.lexicon import strong_key

Log = Callable[[str], None]
IMPERATIVE = re.compile(r"V[a-zA-Z]v")
SECOND_PERSON = "Sp2"
DIVINE = "divine"


def word_marks(words: pd.DataFrame, deference: set[str], particle: str) -> pd.DataFrame:
    """`verse_id, idx, deference, imperative, particle` per OSHB word: a `deference` lemma with a
    second-person suffix ("your servant"), an imperative, an imperative whose next word is the
    `particle` (נא)."""
    keys = [[strong_key(x) for x in cl] for cl in words.content_lemmas]
    morph = words.morph.fillna("")
    dfr = [
        bool(set(k) & deference) and SECOND_PERSON in m for k, m in zip(keys, morph, strict=True)
    ]
    imp = morph.str.contains(IMPERATIVE).to_numpy()
    is_particle = np.array([particle in k for k in keys])
    same_verse = np.r_[words.verse_id.to_numpy()[1:] == words.verse_id.to_numpy()[:-1], False]
    nxt = np.r_[is_particle[1:], False] & same_verse
    return pd.DataFrame({
        "verse_id": words.verse_id.to_numpy(),
        "idx": words.idx.to_numpy(),
        "deference": np.array(dfr, bool),
        "imperative": imp,
        "particle": imp & nxt,
    })  # fmt: skip


def quotations(clauses: pd.DataFrame, marks: pd.DataFrame, verses: pd.DataFrame) -> pd.DataFrame:
    """One row per quotation: `quote, book_id, chapter, verse_id, last_verse_id, depth, start,
    narrated, start, end, speaker, speaker_source, addressee, addressee_source, n_words,
    deference, imperatives, particle` (`narrated`: introduced by the narrator; `start` / `end`:
    clause positions of its first clause and the end of its extent)."""
    c = clauses.sort_values("clause", ignore_index=True)
    depth = c.txt.str.len().to_numpy()
    quote = c.quote.to_numpy()
    book = c.verse_id.map(verses.set_index("verse_id").book_id).to_numpy()
    starts = np.flatnonzero(quote == c.clause.to_numpy())
    # a quotation's extent: until the text is shallower or the next quotation at its level starts
    ends = np.empty(len(starts), np.int64)
    n = len(c)
    for k, s in enumerate(starts):
        d, j = depth[s], s + 1
        while j < n and book[j] == book[s] and depth[j] >= d and not (
            depth[j] == d and quote[j] == c.clause[j]
        ):
            j += 1
        ends[k] = j - 1
    # words: each OSHB word in its innermost (last) clause
    w = c[["quote", "verse_id", "words"]].explode("words").dropna(subset=["words"])
    w = w.assign(idx=w.words.astype(np.int64)).drop_duplicates(["verse_id", "idx"], keep="last")
    w = w[w.quote >= 0].merge(marks, on=["verse_id", "idx"], how="left").fillna(False)
    agg = w.groupby("quote").agg(
        n_words=("idx", "size"),
        deference=("deference", "sum"),
        imperatives=("imperative", "sum"),
        particle=("particle", "sum"),
    )
    s = c.iloc[starts]
    last_verse = [int(c.verse_id.iloc[e]) for e in ends]
    q = pd.DataFrame({
        "quote": s.clause.to_numpy(),
        "book_id": book[starts],
        "chapter": s.verse_id.map(verses.set_index("verse_id").chapter).to_numpy(),
        "verse_id": s.verse_id.to_numpy(),
        "last_verse_id": last_verse,
        "depth": depth[starts],
        "narrated": s.txt.str[-2:-1].eq("N").to_numpy(),
        "start": starts,
        "end": ends,
        "speaker": s.speaker.to_numpy(),
        "speaker_source": s.speaker_source.to_numpy(),
        "addressee": s.addressee.to_numpy(),
        "addressee_source": s.addressee_source.to_numpy(),
    })  # fmt: skip
    q = q.join(agg, on="quote")
    for col in ("n_words", "deference", "imperatives", "particle"):
        q[col] = q[col].fillna(0).astype(np.int64)
    return q


def rank_of(lemma: Any, divine: set[str], kings: set[str]) -> int:
    """2 for God, 1 for a king, else 0."""
    if not isinstance(lemma, str):
        return 0
    k = strong_key(lemma)
    return 2 if k in divine or lemma == DIVINE else 1 if k in kings else 0


def party_of(lemma: Any, divine: set[str]) -> Any:
    """The divine names are one party, `divine`; anyone else is their lemma."""
    return DIVINE if isinstance(lemma, str) and strong_key(lemma) in divine else lemma


def exchanges(q: pd.DataFrame, gap: int) -> list[list[int]]:
    """Row labels of `q` for each exchange: consecutive quotations the narrator introduces
    (`narrated`), at one level of one book, each starting at most `gap` clauses after the previous
    one's extent, between exactly two known parties (`speaker_party`) who both speak. An unknown or
    a third speaker, or a turn addressed (`addressee_party`) to someone other than the other party,
    closes the run and opens the next."""
    out: list[list[int]] = []
    cols = ["speaker_party", "addressee_party", "start", "end"]
    for _, g in q[q.narrated].sort_values("start").groupby(["book_id", "depth"], sort=False):
        run: list[int] = []
        parties: list[str] = []
        prev_end = None
        for i, spk, adr, start, end in zip(g.index, *(g[c] for c in cols), strict=True):
            known = isinstance(spk, str)
            linked = prev_end is not None and start - prev_end - 1 <= gap
            others = [x for x in parties if x != spk]
            fits = (
                known
                and linked
                and (spk in parties or len(parties) < 2)
                and (not isinstance(adr, str) or adr == spk or not others or adr == others[0])
            )
            if fits:
                run.append(i)
                if spk not in parties:
                    parties.append(spk)
            else:
                if len(parties) == 2:
                    out.append(run)
                run, parties = ([i], [spk]) if known else ([], [])
            prev_end = end
        if len(parties) == 2:
            out.append(run)
    return out


def up_test(
    value: np.ndarray,
    denom: np.ndarray,
    up: np.ndarray,
    book: np.ndarray,
    shuffles: int,
    rng: np.random.Generator,
    scale: float,
) -> dict[str, Any]:
    """`scale` x (sum of `value` / sum of `denom` over `up`, minus the same over the rest), against
    `up` permuted over the rows of each book."""

    def rate(sel: np.ndarray) -> float:
        d = denom[sel].sum()
        return float(value[sel].sum() / d) if d else float("nan")

    def stat(u: np.ndarray) -> float:
        return scale * (rate(u) - rate(~u))

    obs = stat(up)
    null = np.array([stat(permute_within(up, book, rng)) for _ in range(shuffles)])
    null = null[~np.isnan(null)]
    return {
        "observed": round(obs, 4),
        "null": round(float(null.mean()), 4) if len(null) else None,
        "p": empirical_p(obs, null) if not np.isnan(obs) else None,
        "up": {"rate": round(scale * rate(up), 4), "count": int(value[up].sum()),
               "of": int(denom[up].sum()), "quotations": int(up.sum())},
        "rest": {"rate": round(scale * rate(~up), 4), "count": int(value[~up].sum()),
                 "of": int(denom[~up].sum()), "quotations": int((~up).sum())},
    }  # fmt: skip


def turn_test(
    higher: np.ndarray, share: np.ndarray, shuffles: int, rng: np.random.Generator
) -> dict[str, Any]:
    """How many exchanges the higher party ends (or opens), against each exchange's turn drawn at
    random from its turns (the higher party's `share` of them)."""
    obs = int(higher.sum())
    null = (rng.random((shuffles, len(share))) < share).sum(axis=1)
    return {
        "observed": obs,
        "expected": round(float(share.sum()), 2),
        "exchanges": int(len(share)),
        "p": empirical_p(obs, null),
    }


def exchange_table(q: pd.DataFrame, gap: int, divine: set[str], kings: set[str]) -> pd.DataFrame:
    """One row per exchange: `exchange, book_id, chapter, verse_id, last_verse_id, a` (who opens),
    `b, a_rank, b_rank, turns, a_turns, a_words, b_words, last` (who speaks last)."""
    rows = []
    for k, ids in enumerate(exchanges(q, gap)):
        g = q.loc[ids]
        a = g.speaker_party.iloc[0]
        b = next(s for s in g.speaker_party if s != a)
        is_a = (g.speaker_party == a).to_numpy()
        rows.append({
            "exchange": k,
            "book_id": int(g.book_id.iloc[0]),
            "chapter": int(g.chapter.iloc[0]),
            "verse_id": int(g.verse_id.iloc[0]),
            "last_verse_id": int(g.last_verse_id.max()),
            "a": a,
            "b": b,
            "a_rank": rank_of(a, divine, kings),
            "b_rank": rank_of(b, divine, kings),
            "turns": len(g),
            "a_turns": int(is_a.sum()),
            "a_words": int(g.n_words[is_a].sum()),
            "b_words": int(g.n_words[~is_a].sum()),
            "last": g.speaker_party.iloc[-1],
        })  # fmt: skip
    return pd.DataFrame(rows, columns=list(EXCHANGE_COLUMNS))


EXCHANGE_COLUMNS = (
    "exchange", "book_id", "chapter", "verse_id", "last_verse_id", "a", "b", "a_rank", "b_rank",
    "turns", "a_turns", "a_words", "b_words", "last",
)  # fmt: skip


def turn_checks(ex: pd.DataFrame, shuffles: int, rng: np.random.Generator) -> dict[str, Any]:
    """Over exchanges between parties of different rank: the last word and the opening (against
    the higher party's share of the turns), and whose turns are longer (sign test)."""
    une = ex[ex.a_rank != ex.b_rank]
    a_high = (une.a_rank > une.b_rank).to_numpy()
    high = np.where(a_high, une.a, une.b)
    b_turns = (une.turns - une.a_turns).to_numpy()
    share = np.where(a_high, une.a_turns, b_turns) / une.turns.to_numpy()
    a_mean = une.a_words.to_numpy() / une.a_turns.to_numpy()
    b_mean = une.b_words.to_numpy() / b_turns
    hi, lo = np.where(a_high, a_mean, b_mean), np.where(a_high, b_mean, a_mean)
    longer, shorter = int((hi > lo).sum()), int((hi < lo).sum())
    return {
        "unequal": int(len(une)),
        "last_word": turn_test(une["last"].to_numpy() == high, share, shuffles, rng),
        "opener": turn_test(a_high, share, shuffles, rng),
        "lengths": {
            "longer": longer,
            "shorter": shorter,
            "median_higher": round(float(np.median(hi)), 1) if len(une) else None,
            "median_lower": round(float(np.median(lo)), 1) if len(une) else None,
            "p": float(binomtest(longer, longer + shorter).pvalue) if longer + shorter else None,
        },
    }


def pair_table(q: pd.DataFrame, reliable: list[str]) -> pd.DataFrame:
    """Per book, speaker -> addressee (parties: the divine names are one) with quotations, words
    and how many have a `reliable` addressee (self-address left out)."""
    known = q[
        q.speaker_party.notna() & q.addressee_party.notna() & (q.speaker_party != q.addressee_party)
    ]
    return (
        known.assign(
            reliable=known.addressee_source.isin(reliable),
            speaker=known.speaker_party,
            addressee=known.addressee_party,
        )
        .groupby(["book_id", "speaker", "addressee"])
        .agg(n_quotes=("quote", "size"), n_words=("n_words", "sum"),
             n_reliable=("reliable", "sum"))
        .reset_index()
        .astype({"n_reliable": np.int64})
        .sort_values(["book_id", "n_quotes", "n_words"], ascending=[True, False, False],
                     ignore_index=True)
    )  # fmt: skip


def run_dialogue(cfg: dict[str, Any], log: Log = print) -> dict[str, Any]:
    t0 = time.perf_counter()
    dc, sc = cfg["dialogue"], cfg["syntax"]
    proc, art = resolve_path(cfg, "data_processed"), resolve_path(cfg, "artifacts")
    out = art / "dialogue"
    clauses = pd.read_parquet(proc / "syntax_clauses.parquet")
    if "addressee" not in clauses.columns:
        raise RuntimeError("syntax_clauses.parquet has no addressees; rerun `bsim syntax`")
    words = pd.read_parquet(
        proc / "words.parquet", columns=["verse_id", "idx", "morph", "content_lemmas"]
    )
    verses = pd.read_parquet(proc / "verses.parquet", columns=["verse_id", "book_id", "chapter"])
    marks = word_marks(words, {strong_key(x) for x in dc["deference"]}, dc["particle"])
    q = quotations(clauses, marks, verses)
    divine, kings = {strong_key(x) for x in sc["divine"]}, {strong_key(x) for x in dc["kings"]}
    q["speaker_party"] = [party_of(s, divine) for s in q.speaker]
    q["addressee_party"] = [party_of(s, divine) for s in q.addressee]
    q["speaker_rank"] = [rank_of(s, divine, kings) for s in q.speaker]
    q["addressee_rank"] = [rank_of(s, divine, kings) for s in q.addressee]
    rng = np.random.default_rng(dc["seed"])

    def checks(sel: pd.Series) -> dict[str, Any]:
        s = q[sel & q.addressee.notna() & (q.speaker_rank < 2)]
        up = (s.addressee_rank > s.speaker_rank).to_numpy()
        book = s.book_id.to_numpy()
        n = dc["shuffles"]
        return {
            "deference": up_test(s.deference.to_numpy(), s.n_words.to_numpy(), up, book, n, rng,
                                 1000.0),
            "particle": up_test(s.particle.to_numpy(), s.imperatives.to_numpy(), up, book, n, rng,
                                1.0),
        }  # fmt: skip

    tests = checks(q.addressee_source.isin(dc["reliable"]))
    sensitivity = checks(q.addressee.notna())
    ex = exchange_table(q, dc["exchange_gap"], divine, kings)
    turns = turn_checks(ex, dc["shuffles"], rng)
    pairs = pair_table(q, dc["reliable"])

    out.mkdir(parents=True, exist_ok=True)
    q.to_parquet(out / "quotations.parquet")
    pairs.to_parquet(out / "pairs.parquet")
    ex.to_parquet(out / "exchanges.parquet")

    def holds(t: dict[str, Any], above: float) -> bool | None:
        return None if t["p"] is None else bool(t["p"] <= dc["alpha"] and t["observed"] > above)

    last = turns["last_word"]
    meta = {
        "config_hash": config_hash(cfg, "dialogue"),
        "built_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "quotations": int(len(q)),
        "with_addressee": int(q.addressee.notna().sum()),
        "addressee": {s: int((q.addressee_source == s).sum())
                      for s in ("explicit", "vocative", "pronoun", "turn")},
        "reliable": dc["reliable"],
        "hand_check": dc["hand_check"],
        "pairs": int(len(pairs)),
        "exchanges": int(len(ex)),
        "unequal": turns["unequal"],
        "shuffles": dc["shuffles"],
        "alpha": dc["alpha"],
        "tests": {
            "deference": {**tests["deference"], "holds": holds(tests["deference"], 0)},
            "particle": {**tests["particle"], "holds": holds(tests["particle"], 0)},
            "last_word": {**last, "holds": holds(last, last["expected"])},
        },
        "sensitivity": sensitivity,
        "opener": turns["opener"],
        "lengths": turns["lengths"],
        "seconds": round(time.perf_counter() - t0, 1),
    }  # fmt: skip
    text = json.dumps(meta, indent=2, ensure_ascii=False)
    (out / "dialogue.meta.json").write_text(text, "utf-8")
    t = meta["tests"]
    log(
        f"{len(q)} quotations, {meta['with_addressee']} with an addressee; {len(ex)} exchanges"
        f" ({turns['unequal']} unequal); deference {t['deference']['observed']}"
        f" (p {t['deference']['p']}), particle {t['particle']['observed']}"
        f" (p {t['particle']['p']}), last word {last['observed']} vs {last['expected']}"
        f" (p {last['p']})"
    )
    return meta
