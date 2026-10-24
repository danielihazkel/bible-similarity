"""`bsim binomials`: fixed word pairs and their order (DESIGN.md §16.72).

Hebrew pairs words in a set order: שמים וארץ, איש ואשה, כסף וזהב. Some orders are frozen, some
turn round; Behaghel's law says the shorter word tends to come first, and the late books are said
to turn some pairs (זהב וכסף in Chronicles against the older כסף וזהב).

- **Pairs.** Two words side by side in a verse, the second with ו, both of one of `kinds` (common
  nouns, proper names or adjectives, by the morphology; numbers, gentilics and Aramaic left out),
  the first not in the construct state, their lemmas different. A *binomial* is a pair of lemmas
  found at least `min_pairs` times in either order; its commoner order is its *own*, the share
  in it its *fixedness* (a tie has no own order and is left out of the claims).
- **Length.** Each word as written, its prefixes taken off (the ו, a preposition, the article;
  the article after ב / ל / כ is not written): its letters (consonants) and its syllables (the
  full vowels and shureq; shewa and the hataf vowels not counted). A word's length in a binomial
  is its median over the binomial's occurrences.
- **Claims fixed in advance.** (1) In a binomial's own order the shorter word comes first more
  often than the longer (binomials whose words differ in length; one-sided sign test), in
  letters and in syllables both. (2) The rarer order is commoner in the late books
  (`dating.late`) than in the early ones (`dating.early`): the difference of the two rates
  against the period labels permuted within each binomial (`shuffles`). Known: each of `known` in
  its order at least `fixed` of the time; `known_late` (זהב וכסף) a larger share of its pair in
  the late books than in the early.

Writes `artifacts/binomials/`: `types.parquet` (`pair, first, second, first_form, second_form,
kind, n, n_own, fixed, first_letters, second_letters, first_syll, second_syll, n_early, rev_early,
n_late, rev_late`), `occurrences.parquet` (`pair, verse_id, own, a_tok, b_tok`: up to
`examples` of a binomial's occurrences in each order, evenly spaced through the canon) and
`binomials.meta.json`.
"""

from __future__ import annotations

import json
import time
import unicodedata
from collections import Counter
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from scipy.stats import binomtest

from bsim.analysis.stats import empirical_p, permute_within
from bsim.config import config_hash, resolve_path
from bsim.data.canon import BY_OSIS
from bsim.text.normalize import consonantal

Log = Callable[[str], None]
FULL_VOWELS = {chr(c) for c in range(0x05B4, 0x05BC)}  # hiriq .. qubuts (holam both forms)
DAGESH, VAV = "ּ", "ו"


def is_letter(ch: str) -> bool:
    return "א" <= ch <= "ת"


def n_prefixes(parts: list[str]) -> int:
    """The prefix letters written: one per prefix, but the article after ב / ל / כ is not."""
    pre = parts[:-1]
    return sum(1 for i, p in enumerate(pre) if not (p == "d" and i > 0 and pre[i - 1] in "blk"))


def strip_prefixes(surface: str, n: int) -> str:
    """The word without its first `n` letters (and their marks)."""
    s = unicodedata.normalize("NFC", surface)
    seen = 0
    for i, ch in enumerate(s):
        if is_letter(ch):
            if seen == n:
                return s[i:]
            seen += 1
    return ""


def letters(s: str) -> int:
    return sum(is_letter(ch) for ch in s)


def syllables(s: str) -> int:
    """Full vowels, and a ו with dagesh and no vowel of its own (shureq) after a letter."""
    s = unicodedata.normalize("NFD", s)
    n, prev_letter, i = 0, False, 0
    while i < len(s):
        ch = s[i]
        if is_letter(ch):
            marks = []
            j = i + 1
            while j < len(s) and not is_letter(s[j]):
                marks.append(s[j])
                j += 1
            vowels = sum(m in FULL_VOWELS for m in marks)
            if ch == VAV and DAGESH in marks and vowels == 0 and prev_letter:
                n += 1
            n += vowels
            prev_letter = True
            i = j
        else:
            i += 1
    return n


def kind_of(code: str, kinds: dict[str, str]) -> str | None:
    return kinds.get(code[:2])


def construct(code: str) -> bool:
    return code[:1] in "NA" and code[:2] != "Np" and len(code) > 4 and code[4] == "c"


def find_pairs(words: pd.DataFrame, kinds: dict[str, str]) -> pd.DataFrame:
    """Every pair: `verse_id, a, b` (lemmas), `kind, a_tok, b_tok, a_len, b_len, a_syll,
    b_syll, a_form, b_form`."""
    rows = []
    vid = words.verse_id.to_numpy()
    lem = words.lemma.astype(str).tolist()
    mor = words.morph.fillna("").astype(str).tolist()
    sur = words.surface.astype(str).tolist()
    tok = words.display_idx.tolist()
    parts = [[(p.split() or [""])[0] for p in x.split("/")] for x in lem]
    codes = [m[1:].split("/") if m else [] for m in mor]

    def core(i: int) -> tuple[str, str]:
        k = len(parts[i]) - 1
        return parts[i][k], codes[i][k] if k < len(codes[i]) else ""

    for i in range(len(lem) - 1):
        if vid[i] != vid[i + 1] or not mor[i].startswith("H") or not mor[i + 1].startswith("H"):
            continue
        if "c" not in parts[i + 1][:-1]:
            continue
        la, ca = core(i)
        lb, cb = core(i + 1)
        ka, kb = kind_of(ca, kinds), kind_of(cb, kinds)
        if ka is None or ka != kb or la == lb or construct(ca):
            continue
        wa = strip_prefixes(sur[i], n_prefixes(parts[i]))
        wb = strip_prefixes(sur[i + 1], n_prefixes(parts[i + 1]))
        rows.append((int(vid[i]), la, lb, ka, tok[i], tok[i + 1], letters(wa), letters(wb),
                     syllables(wa), syllables(wb), consonantal(wa), consonantal(wb)))  # fmt: skip
    cols = ["verse_id", "a", "b", "kind", "a_tok", "b_tok", "a_len", "b_len", "a_syll", "b_syll",
            "a_form", "b_form"]  # fmt: skip
    return pd.DataFrame(rows, columns=cols)


def shorter_first(first: np.ndarray, second: np.ndarray) -> dict[str, Any]:
    """Of the binomials whose words differ in length, how many put the shorter first, and the
    one-sided sign test."""
    diff = first - second
    m = int((diff != 0).sum())
    k = int((diff < 0).sum())
    p = float(binomtest(k, m, 0.5, alternative="greater").pvalue) if m else 1.0
    return {"differ": m, "shorter_first": k, "share": round(k / m, 4) if m else None, "p": p}


def run_binomials(cfg: dict[str, Any], log: Log = print) -> Path:
    bc, dc = cfg["binomials"], cfg["dating"]
    proc, art = resolve_path(cfg, "data_processed"), resolve_path(cfg, "artifacts")
    t0 = time.perf_counter()
    verses = pd.read_parquet(proc / "verses.parquet", columns=["verse_id", "book_id"])
    words = pd.read_parquet(
        proc / "words.parquet",
        columns=["verse_id", "idx", "surface", "lemma", "morph", "display_idx"],
    ).sort_values(["verse_id", "idx"], kind="stable")
    kinds = {str(k): str(v) for k, v in bc["kinds"].items()}
    pairs = find_pairs(words, kinds)
    book = dict(zip(verses.verse_id, verses.book_id, strict=True))
    early = {BY_OSIS[b].book_id for b in dc["early"]}
    late = {BY_OSIS[b].book_id for b in dc["late"]}
    pairs["book_id"] = pairs.verse_id.map(book)
    pairs["period"] = np.where(pairs.book_id.isin(late), "late",
                               np.where(pairs.book_id.isin(early), "early", "other"))  # fmt: skip
    lo = np.where(pairs.a < pairs.b, pairs.a, pairs.b)
    hi = np.where(pairs.a < pairs.b, pairs.b, pairs.a)
    pairs["pair"] = pd.Series(lo, dtype=str) + "+" + pd.Series(hi, dtype=str)
    pairs["lo_first"] = pairs.a.to_numpy() == lo
    counts = pairs.groupby("pair").size()
    keep = counts[counts >= int(bc["min_pairs"])].index
    occ = pairs[pairs.pair.isin(keep)].copy()

    trows = []
    own_first: dict[str, bool] = {}
    for pair, g in occ.groupby("pair", sort=True):
        n = len(g)
        n_lo = int(g.lo_first.sum())
        if 2 * n_lo == n:
            continue  # a tie: no own order
        lo_own = 2 * n_lo > n
        own_first[pair] = lo_own
        first_lem, second_lem = (pair.split("+") if lo_own else pair.split("+")[::-1])
        own = g.lo_first == lo_own

        def stat(lemma: str, col: str, g: pd.DataFrame = g) -> float:
            vals = np.concatenate(
                [g.loc[g.a == lemma, f"a_{col}"], g.loc[g.b == lemma, f"b_{col}"]]
            )
            return float(np.median(vals))

        def form(lemma: str, g: pd.DataFrame = g) -> str:
            c = Counter([*g.loc[g.a == lemma, "a_form"], *g.loc[g.b == lemma, "b_form"]])
            return c.most_common(1)[0][0]

        e, la = g.period == "early", g.period == "late"
        trows.append({
            "pair": pair, "first": first_lem, "second": second_lem,
            "first_form": form(first_lem), "second_form": form(second_lem),
            "kind": g.kind.iloc[0], "n": n, "n_own": int(own.sum()),
            "fixed": round(float(own.mean()), 4),
            "first_letters": stat(first_lem, "len"), "second_letters": stat(second_lem, "len"),
            "first_syll": stat(first_lem, "syll"), "second_syll": stat(second_lem, "syll"),
            "n_early": int(e.sum()), "rev_early": int((e & ~own).sum()),
            "n_late": int(la.sum()), "rev_late": int((la & ~own).sum()),
        })  # fmt: skip
    types = pd.DataFrame(trows)
    occ = occ[occ.pair.isin(own_first)].copy()
    occ["own"] = occ.lo_first.to_numpy() == occ.pair.map(own_first).to_numpy()

    # (1) the shorter word first
    alpha = float(bc["alpha"])
    by_letters = shorter_first(types.first_letters.to_numpy(), types.second_letters.to_numpy())
    by_syll = shorter_first(types.first_syll.to_numpy(), types.second_syll.to_numpy())
    short_holds = all(x["share"] is not None and x["share"] > 0.5 and x["p"] <= alpha
                      for x in (by_letters, by_syll))  # fmt: skip
    log(f"{len(pairs)} pairs, {len(types)} binomials; shorter first: letters"
        f" {by_letters['shorter_first']}/{by_letters['differ']} (p {by_letters['p']:.3g}),"
        f" syllables {by_syll['shorter_first']}/{by_syll['differ']}"
        f" (p {by_syll['p']:.3g})")  # fmt: skip

    # (2) the rarer order in the late books
    sub = occ[occ.period.isin(["early", "late"])]
    rev = (~sub.own).to_numpy()
    is_late = (sub.period == "late").to_numpy()
    groups = pd.factorize(sub.pair)[0]

    def diff(lab: np.ndarray) -> float:
        return float(rev[lab].mean() - rev[~lab].mean()) if lab.any() and (~lab).any() else 0.0

    observed = diff(is_late)
    rng = np.random.default_rng(bc["seed"])
    reps = int(bc["shuffles"])
    null = np.array([diff(permute_within(is_late, groups, rng)) for _ in range(reps)])
    p_late = empirical_p(observed - 1e-12, null)
    late_holds = bool(observed > 0 and p_late <= alpha)
    # described: the same without the known pair (כסף וזהב), whose turn is the textbook case
    kpair = "+".join(sorted(str(x) for x in bc["known_late"]))
    rest = (sub.pair != kpair).to_numpy()
    rev_r, late_r, groups_r = rev[rest], is_late[rest], groups[rest]

    def diff_r(lab: np.ndarray) -> float:
        return float(rev_r[lab].mean() - rev_r[~lab].mean()) if lab.any() and (~lab).any() else 0.0

    obs_r = diff_r(late_r)
    null_r = np.array([diff_r(permute_within(late_r, groups_r, rng)) for _ in range(reps)])
    without = {"difference": round(obs_r, 4), "p": empirical_p(obs_r - 1e-12, null_r),
               "rate_early": float(rev_r[~late_r].mean()) if (~late_r).any() else None,
               "rate_late": float(rev_r[late_r].mean()) if late_r.any() else None}  # fmt: skip
    rate_early = float(rev[~is_late].mean()) if (~is_late).any() else None
    rate_late = float(rev[is_late].mean()) if is_late.any() else None
    log(f"rarer order: early {rate_early}, late {rate_late} (p {p_late:.4g}); without the known"
        f" pair p {without['p']:.4g}")

    # known
    by_pair = {(r["first"], r["second"]): r for r in trows}
    known = []
    for first, second, fixed in bc["known"]:
        r = by_pair.get((str(first), str(second)))
        rr = by_pair.get((str(second), str(first)))
        share = r["fixed"] if r else (round(1 - rr["fixed"], 4) if rr else None)
        n = (r or rr or {}).get("n", 0)
        holds = share is not None and share >= fixed
        known.append({"first": str(first), "second": str(second), "n": n, "share": share,
                      "fixed": float(fixed), "holds": holds})  # fmt: skip
    kf, ks = (str(x) for x in bc["known_late"])
    kl = pairs[((pairs.a == kf) & (pairs.b == ks)) | ((pairs.a == ks) & (pairs.b == kf))]
    late_known = {"first": kf, "second": ks}
    for period in ("early", "late"):
        g = kl[kl.period == period]
        late_known[f"n_{period}"] = len(g)
        late_known[f"share_{period}"] = round(float((g.a == kf).mean()), 4) if len(g) else None
    se, sl = late_known["share_early"], late_known["share_late"]
    late_known["holds"] = se is not None and sl is not None and sl > se
    known_holds = all(k["holds"] for k in known) and bool(late_known["holds"])
    log(f"known: {[(k['share'], k['n']) for k in known]}; זהב first early {se}, late {sl}")

    ex = int(bc["examples"])
    def spread(g: pd.DataFrame) -> pd.DataFrame:
        """Up to `ex` occurrences evenly spaced through the canon (the first and the last kept)."""
        if len(g) <= ex:
            return g
        return g.iloc[np.unique(np.linspace(0, len(g) - 1, ex).round().astype(int))]

    occ = occ.sort_values(["pair", "own", "verse_id"], ascending=[True, False, True],
                          kind="stable")  # fmt: skip
    occ_out = pd.concat(
        [spread(g) for _, g in occ.groupby(["pair", "own"], sort=False)], ignore_index=True
    )[["pair", "verse_id", "own", "a_tok", "b_tok"]]
    for c in ("a_tok", "b_tok"):
        occ_out[c] = pd.array(occ_out[c], dtype="Int64")

    out = art / "binomials"
    out.mkdir(parents=True, exist_ok=True)
    types.to_parquet(out / "types.parquet", index=False)
    occ_out.to_parquet(out / "occurrences.parquet", index=False)
    meta = {
        "config_hash": config_hash(cfg, "binomials", "dating"),
        "built_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "pairs": len(pairs), "binomials": len(types), "min_pairs": int(bc["min_pairs"]),
        "both_ways": int((types.n_own < types.n).sum()) if len(types) else 0,
        "letters": by_letters, "syllables": by_syll, "short_holds": short_holds,
        "rate_early": rate_early, "rate_late": rate_late,
        "n_early": int((~is_late).sum()), "n_late": int(is_late.sum()),
        "difference": round(observed, 4), "expected": round(float(null.mean()), 4),
        "late_p": p_late, "late_holds": late_holds, "without_known": without,
        "known": known, "known_late": late_known, "known_holds": known_holds,
        "examples": ex, "shuffles": reps, "alpha": alpha,
        "seconds": round(time.perf_counter() - t0, 1),
    }  # fmt: skip
    (out / "binomials.meta.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False),
                                             "utf-8")  # fmt: skip
    log(f"done: shorter first {'holds' if short_holds else 'not borne out'}, late"
        f" {'holds' if late_holds else 'not borne out'}, known"
        f" {'holds' if known_holds else 'not borne out'} ({meta['seconds']} s) -> {out}")
    return out / "types.parquet"
