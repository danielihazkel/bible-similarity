"""`bsim diffs`: how parallel passages differ, word by word (DESIGN.md §16.8).

Every aligned verse pair of a strong parallel sequence (§16.7: `q ≤ diffs.max_q`, repeats inside
one chapter left out unless `diffs.same_chapter`) is aligned word by word, A = the earlier verse in
canon order. A word is one OSHB word; its key is its content lemmas (`+`-joined; prefix particles
are not lemmas, so וַיֹּאמֶר and אָמַר share a key). A word with no content lemma (a preposition
carrying a suffix: בּוֹ, לָהֶם) is keyed by its prefix lemmas, `~l`, `~c/b` (`key_letters` shows
them). Needleman-Wunsch global alignment: same key `match`, different keys `-mismatch`, a gap
`-gap`. Each position is labelled:

- `same`: same key and same consonants;
- `spelling`: same key, consonants differ only by ו / י after the first letter (plene vs
  defective spelling; a leading ו / י is a conjunction or verb prefix, not a vowel letter);
- `form`: same key, other consonantal differences (prefix, suffix, inflection);
- `substitution`: different keys aligned;
- `omitted` / `added`: a word only in A / only in B;
- `moved`: an omitted word whose key is also added in the same pair (both sides relabelled).

A chain's edge pairs can be only loosely parallel; a global alignment of two unrelated verses is
all substitutions. So a pair is diffed only when at least `diffs.min_shared` of the shorter verse's
words align to a word with the same key (`same`, `spelling` or `form`); looser pairs are counted
in the meta and left out.

Writes `artifacts/diffs/changes.parquet`, one row per non-`same` position: `seq_id, a, b`
(verse ids), `a_book, b_book`, `op`, `a_idx, b_idx` (`words.idx`, NULL on the missing side),
`a_key, b_key`, `a_form, b_form` (consonantal surface); plus `diffs.meta.json` with the per-op
totals and the diffed / loose pair counts.
"""

from __future__ import annotations

import json
import time
from collections import Counter
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from bsim.analysis.stats import g2_table
from bsim.config import config_hash, resolve_path
from bsim.text.normalize import consonantal, match_key

Log = Callable[[str], None]

OPS = ("same", "spelling", "form", "substitution", "omitted", "added", "moved")
KEPT = ("same", "spelling", "form")  # a word that keeps its lemma
CHANGE_COLS = (
    "seq_id",
    "a",
    "b",
    "a_book",
    "b_book",
    "op",
    "a_idx",
    "b_idx",
    "a_key",
    "b_key",
    "a_form",
    "b_form",
)
MATRES = str.maketrans("", "", "וי")


@dataclass(frozen=True)
class Word:
    idx: int  # words.idx
    key: str  # content lemmas, "+"-joined ("" for a word without one)
    form: str  # match_key of the surface (consonants, finals folded)
    text: str = ""  # consonantal surface as written (for display)


@dataclass(frozen=True)
class Op:
    op: str
    a: int | None  # position in A's word list
    b: int | None


PREFIX_LETTERS = {"b": "ב", "c": "ו", "d": "ה", "k": "כ", "l": "ל", "m": "מ", "s": "ש", "i": "ה"}


def word_key(content_lemmas: Sequence[str] | str, lemma: str) -> str:
    parts = content_lemmas.split() if isinstance(content_lemmas, str) else list(content_lemmas)
    return "+".join(parts) if parts else f"~{lemma}"


def key_letters(key: str) -> str | None:
    """The Hebrew letters of a prefix-only key (`~c/l` -> `ול`); None for a lemma key."""
    if not key.startswith("~"):
        return None
    return "".join(PREFIX_LETTERS.get(p, p) for p in key[1:].split("/"))


def _skeleton(form: str) -> str:
    """Consonants without ו / י vowel letters (the first letter is kept)."""
    return form[:1] + form[1:].translate(MATRES)


def _label(wa: Word, wb: Word) -> str:
    if wa.key != wb.key:
        return "substitution"
    if wa.form == wb.form:
        return "same"
    if _skeleton(wa.form) == _skeleton(wb.form):
        return "spelling"
    return "form"


def align_words(
    a: Sequence[Word], b: Sequence[Word], match: float, mismatch: float, gap: float
) -> list[Op]:
    """Needleman-Wunsch over word keys; the traceback prefers diagonal, then omission."""
    n, m = len(a), len(b)
    h = np.zeros((n + 1, m + 1))
    h[:, 0] = -gap * np.arange(n + 1)
    h[0, :] = -gap * np.arange(m + 1)
    for i in range(1, n + 1):
        ka = a[i - 1].key
        for j in range(1, m + 1):
            s = match if ka == b[j - 1].key else -mismatch
            h[i, j] = max(h[i - 1, j - 1] + s, h[i - 1, j] - gap, h[i, j - 1] - gap)
    ops: list[Op] = []
    i, j = n, m
    while i > 0 or j > 0:
        if i > 0 and j > 0:
            s = match if a[i - 1].key == b[j - 1].key else -mismatch
            if np.isclose(h[i, j], h[i - 1, j - 1] + s):
                ops.append(Op(_label(a[i - 1], b[j - 1]), i - 1, j - 1))
                i, j = i - 1, j - 1
                continue
        if i > 0 and np.isclose(h[i, j], h[i - 1, j] - gap):
            ops.append(Op("omitted", i - 1, None))
            i -= 1
        else:
            ops.append(Op("added", None, j - 1))
            j -= 1
    ops.reverse()
    # a word dropped in one place and added in another moved
    omitted = Counter(a[o.a].key for o in ops if o.op == "omitted")
    added = Counter(b[o.b].key for o in ops if o.op == "added")
    moved = {k: min(omitted[k], added[k]) for k in omitted.keys() & added.keys()}
    left, right = dict(moved), dict(moved)
    out = []
    for o in ops:
        if o.op == "omitted" and left.get(a[o.a].key, 0) > 0:
            left[a[o.a].key] -= 1
            o = Op("moved", o.a, None)
        elif o.op == "added" and right.get(b[o.b].key, 0) > 0:
            right[b[o.b].key] -= 1
            o = Op("moved", None, o.b)
        out.append(o)
    return out


def shared_ratio(ops: Sequence[Op], n_a: int, n_b: int) -> float:
    """Share of the shorter verse's words aligned to a word with the same key."""
    shorter = min(n_a, n_b)
    return sum(o.op in KEPT for o in ops) / shorter if shorter else 0.0


def make_word(idx: int, content_lemmas: Sequence[str] | str, lemma: str, surface: str) -> Word:
    return Word(
        idx,
        word_key(content_lemmas, lemma),
        match_key(surface),
        consonantal(surface).replace(" ", ""),
    )


def verse_words(words: pd.DataFrame) -> dict[int, list[Word]]:
    """verse_id -> its words in order (`words`: verse_id, idx, surface, lemma, content_lemmas)."""
    out: dict[int, list[Word]] = {}
    for w in words.sort_values(["verse_id", "idx"], kind="stable").itertuples(index=False):
        out.setdefault(int(w.verse_id), []).append(
            make_word(int(w.idx), w.content_lemmas, w.lemma, w.surface)
        )
    return out


def find_changes(
    sequences: pd.DataFrame,
    words: dict[int, list[Word]],
    cfg: dict[str, Any],
    sides: Counter | None = None,
) -> tuple[pd.DataFrame, Counter, int, int]:
    """(change rows, op totals incl. `same`, diffed verse pairs, loose pairs left out).
    `sides`, when given, counts the words of the diffed pairs by `(side, a_book, b_book, key)`
    (`side` "a" or "b"; key "" = all words; side "pairs": the diffed verse pairs), the base of
    the rewrite rates."""
    d = cfg["diffs"]
    keep = sequences.q <= d["max_q"]
    if not d["same_chapter"]:
        keep &= ~sequences.same_chapter.astype(bool)
    rows, totals, n_pairs, n_loose = [], Counter(), 0, 0
    for s in sequences[keep].itertuples(index=False):
        for a, b, *_ in json.loads(s.pairs):
            wa, wb = words.get(a, []), words.get(b, [])
            ops = align_words(wa, wb, d["match"], d["mismatch"], d["gap"])
            if shared_ratio(ops, len(wa), len(wb)) < d["min_shared"]:
                n_loose += 1
                continue
            n_pairs += 1
            if sides is not None:
                ab = (int(s.a_book), int(s.b_book))
                sides[("pairs", *ab, "")] += 1
                for side, ws in (("a", wa), ("b", wb)):
                    sides[(side, *ab, "")] += len(ws)
                    sides.update((side, *ab, w.key) for w in ws)
            for o in ops:
                totals[o.op] += 1
                if o.op == "same":
                    continue
                rows.append(
                    (
                        int(s.seq_id),
                        a,
                        b,
                        int(s.a_book),
                        int(s.b_book),
                        o.op,
                        None if o.a is None else wa[o.a].idx,
                        None if o.b is None else wb[o.b].idx,
                        None if o.a is None else wa[o.a].key,
                        None if o.b is None else wb[o.b].key,
                        None if o.a is None else wa[o.a].text,
                        None if o.b is None else wb[o.b].text,
                    )
                )
    cols = [*CHANGE_COLS]
    df = pd.DataFrame(rows, columns=cols).astype({"a_idx": "Int64", "b_idx": "Int64"})
    return df, totals, n_pairs, n_loose


REWRITE_OPS = ("substitution", "omitted", "added")


def rewrites(changes: pd.DataFrame, sides: Counter, min_count: int) -> pd.DataFrame:
    """Changes that one book makes consistently against another (DESIGN.md §16.16).

    For each book pair (a_book, b_book) and change (`substitution` a_key -> b_key, `omitted`
    a_key, `added` b_key) seen at least `min_count` times: `n`, the `base` = words with that key
    on the side it starts from (A for substitution / omitted, B for added), `rate` = n / base,
    and Dunning's G² of the 2 x 2 table (word has the key or not) x (undergoes this change or
    not) over that side's words; `p` from χ²(1) when the change is over-represented, else 1;
    `q` = Benjamini–Hochberg over all rows.
    """
    from scipy.stats import chi2

    from bsim.analysis.stats import bh_q

    cols = ["a_book", "b_book", "op", "a_key", "b_key", "n", "base", "rate", "g2", "p", "q"]
    rows = []
    df = changes[changes.op.isin(REWRITE_OPS)]
    for (ab, bb, op), g in df.groupby(["a_book", "b_book", "op"], sort=True):
        side, own = ("b", "b_key") if op == "added" else ("a", "a_key")
        total = sides[(side, ab, bb, "")]
        target = g.b_key if op == "substitution" else None
        op_total = Counter(target) if target is not None else None
        keys = ["a_key", "b_key"] if op == "substitution" else [own]
        for k, n in g.groupby(keys, dropna=False).size().items():
            if n < min_count:
                continue
            key = k[0] if isinstance(k, tuple) else k
            base = sides[(side, ab, bb, key)]
            # column total: all words of that side undergoing this change
            col = op_total[k[1]] if op_total is not None else len(g)
            g2 = g2_table(n, base, col, total)
            expected = base * col / total if total else 0.0
            rows.append(
                (
                    int(ab),
                    int(bb),
                    op,
                    k[0] if op != "added" else None,
                    k[1] if op == "substitution" else (k if op == "added" else None),
                    int(n),
                    int(base),
                    round(n / base, 4) if base else None,
                    round(g2, 3),
                    float(chi2.sf(g2, 1)) if n > expected else 1.0,
                )
            )
    out = pd.DataFrame(rows, columns=cols[:-1])
    out["q"] = bh_q(out.p.to_numpy()) if len(out) else []
    return out.sort_values(["q", "g2"], ascending=[True, False], ignore_index=True)[cols]


def profiles(changes: pd.DataFrame, sides: Counter, pairs: Counter) -> pd.DataFrame:
    """Per book pair: verse pairs and words diffed, each op's count, and the direction of the
    spelling changes (`to_plene`: B adds a ו / י vowel letter, `to_defective`: B drops one)."""
    rows = []
    longer = changes.b_form.str.len() - changes.a_form.str.len()
    spelling = changes.assign(longer=longer)[changes.op == "spelling"]
    by_pair = changes.groupby(["a_book", "b_book"])
    for (ab, bb), n_pairs in sorted(pairs.items()):
        g = by_pair.get_group((ab, bb)) if (ab, bb) in by_pair.groups else changes.iloc[:0]
        ops = Counter(g.op[~((g.op == "moved") & g.a_idx.isna())])  # a moved word counts once
        sp = spelling[(spelling.a_book == ab) & (spelling.b_book == bb)]
        rows.append(
            {
                "a_book": ab,
                "b_book": bb,
                "verse_pairs": n_pairs,
                "a_words": sides[("a", ab, bb, "")],
                "b_words": sides[("b", ab, bb, "")],
                **{op: int(ops[op]) for op in OPS if op != "same"},
                "to_plene": int((sp.longer > 0).sum()),
                "to_defective": int((sp.longer < 0).sum()),
            }
        )
    return pd.DataFrame(rows)


def run_diffs(cfg: dict[str, Any], log: Log = print) -> Path:
    proc = resolve_path(cfg, "data_processed")
    seq_path = resolve_path(cfg, "artifacts") / "sequences" / "verse.parquet"
    if not seq_path.exists():
        raise RuntimeError(f"{seq_path} missing; run `bsim sequences` first")
    t0 = time.perf_counter()
    words = pd.read_parquet(
        proc / "words.parquet", columns=["verse_id", "idx", "surface", "lemma", "content_lemmas"]
    )
    sides: Counter = Counter()
    df, totals, n_pairs, n_loose = find_changes(
        pd.read_parquet(seq_path), verse_words(words), cfg, sides
    )
    pairs = Counter({(ab, bb): n for (side, ab, bb, _), n in sides.items() if side == "pairs"})
    out = resolve_path(cfg, "artifacts") / "diffs"
    out.mkdir(parents=True, exist_ok=True)
    df.to_parquet(out / "changes.parquet")
    rw = rewrites(df, sides, cfg["diffs"]["rewrite_min_count"])
    rw.to_parquet(out / "rewrites.parquet")
    profiles(df, sides, pairs).to_parquet(out / "profiles.parquet")
    meta = {
        "config_hash": config_hash(cfg, "diffs", "sequences"),
        "built_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "verse_pairs": n_pairs,
        "loose_pairs": n_loose,
        "ops": {op: totals[op] for op in OPS},
        "rewrites": int(len(rw)),
        "rewrites_q_below_0.05": int((rw.q <= 0.05).sum()),
        "seconds": round(time.perf_counter() - t0, 1),
    }
    (out / "diffs.meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    log(
        f"done: {n_pairs} verse pairs diffed ({n_loose} too loose), {len(df)} changes"
        f" {meta['ops']} -> {out}"
    )
    return out / "changes.parquet"
