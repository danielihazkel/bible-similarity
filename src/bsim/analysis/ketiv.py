"""`bsim ketiv`: what is written against what is read (DESIGN.md §16.30).

Every ketiv / qere of the OSHB (`data.oshb.kq_pairs`: the written words, which the corpus leaves
out, and the read words it keeps) is described three ways:

- **Letters** (`cls`, on the consonants, final forms folded): `qere_only` (read, not written),
  `ketiv_only` (written, not read), `division` (the words are divided differently), and for one
  word against one: `vowel_letter` (the two differ only by inserting or dropping א ה ו י; `fuller`
  says which side has more letters), `swap` (one letter replaced; `letters` = ketiv>qere),
  `vowel_position` (a vowel letter in another place: הולך / הלוך), `metathesis` (consonants in
  another order: בעברות / בערבות), `same_letters` (a difference in vowels only)
  and `other`.
- **Grammar** (`grammar`, from the OSHB lemmas and morphology of both sides): `spelling` (same
  lemma and same form), `form` (same lemma, another form; `features` lists what differs, e.g.
  `number s>p`, `suffix 3ms>3mp`) and `word` (another lemma). `euphemism`: a lemma pair in
  `ketiv.euphemisms`, the words the reading tradition does not pronounce.
- **Parallels:** where the verse is word-aligned to a parallel passage (the strong sequences of
  §16.7, aligned as in §16.8), the partner word as *written* there (its own ketiv, if it has
  one) is compared with both sides: `parallel` = `qere` / `ketiv` / `neither`.

Tests (named after a first look at the data, so reported as descriptions with their p):
look-alike letters (`ketiv.lookalike`, alike in the square script) among the one-letter swaps
against the share letter frequencies give them (binomial), also without ו / י; every letter
pair against its expected count (binomial, BH q); in the Late Biblical Hebrew books
(`dating.late`), whether the written side is the fuller spelling more often than elsewhere
(books permuted, `ketiv.shuffles`); whether the parallels side with the qere or the ketiv
(binomial against even odds); how unevenly ketiv / qere spread over the books (χ² against their
word counts).

Writes `artifacts/ketiv/`: `pairs.parquet`, `letters.parquet`, `books.parquet` and
`ketiv.meta.json`.
"""

from __future__ import annotations

import difflib
import json
import re
import time
from collections import Counter
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from lxml import etree
from scipy.stats import binom, binomtest, chisquare

from bsim.analysis.diffs import align_words, shared_ratio, verse_words
from bsim.analysis.stats import bh_q, empirical_p
from bsim.config import config_hash, resolve_path
from bsim.data.canon import BOOKS, BY_OSIS
from bsim.data.oshb import NS, kq_pairs, parse_verse
from bsim.text.normalize import consonantal, fold_finals

Log = Callable[[str], None]

MATRES = set("אהוי")
LETTERS = "אבגדהוזחטיכלמנסעפצקרשת"
PAIR_COLUMNS = [
    "kq_id",
    "verse_id",
    "book_id",
    "pos",
    "n_ketiv",
    "n_qere",
    "ketiv",
    "qere",
    "ketiv_c",
    "qere_c",
    "ketiv_lemma",
    "qere_lemma",
    "ketiv_morph",
    "qere_morph",
    "cls",
    "fuller",
    "letters",
    "grammar",
    "features",
    "euphemism",
    "parallel",
    "partner_vid",
    "partner_form",
]
LETTER_COLUMNS = ["pair", "n", "expected", "ratio", "p", "q", "lookalike"]
BOOK_COLUMNS = ["book_id", "n", "words", "rate", "vowel_letter", "ketiv_fuller", *[
    "swap", "division", "other_cls", "form", "word"]]  # fmt: skip


def letters_of(words: list[str]) -> str:
    """Consonants of a word list, joined, final forms folded."""
    return fold_finals(consonantal(" ".join(words)).replace(" ", ""))


def letter_class(n_ketiv: int, n_qere: int, k: str, q: str) -> tuple[str, str | None, str | None]:
    """(cls, fuller, letters) of one ketiv / qere from its consonants (see the module doc)."""
    if n_ketiv == 0:
        return "qere_only", None, None
    if n_qere == 0:
        return "ketiv_only", None, None
    if n_ketiv != n_qere:
        return "division", None, None
    if k == q:
        return "same_letters", None, None
    ops = difflib.SequenceMatcher(None, k, q, autojunk=False).get_opcodes()
    changed = "".join(k[a:b] + q[c:d] for t, a, b, c, d in ops if t != "equal")
    pure = all(t in ("equal", "insert", "delete") for t, *_ in ops)
    if len(k) != len(q) and pure and set(changed) <= MATRES:
        return "vowel_letter", "ketiv" if len(k) > len(q) else "qere", None
    if len(k) == len(q):
        diff = [(a, b) for a, b in zip(k, q, strict=True) if a != b]
        if len(diff) == 1:
            return "swap", None, f"{diff[0][0]}>{diff[0][1]}"
        if sorted(k) == sorted(q):
            strip = {ord(c): None for c in MATRES}
            same_base = k.translate(strip) == q.translate(strip)
            return ("vowel_position" if same_base else "metathesis"), None, None
    return "other", None, None


def morph_features(code: str) -> dict[str, str]:
    """The inflection of an OSHB morphology code: the main morpheme (the last one that is not a
    suffix) and a pronominal suffix. E.g. `HC/Vqw3ms` -> pos V, stem q, conj w, person 3, ..."""
    parts = code[1:].split("/") if code else []
    main = next((p for p in reversed(parts) if p and p[0] != "S"), "")
    out: dict[str, str] = {}
    if main:
        pos, rest = main[0], main[1:]
        out["pos"] = pos
        if pos == "V" and len(rest) >= 2:
            out["stem"], out["conj"] = rest[0], rest[1]
            tail = rest[2:]
            keys = (
                ("gender", "number", "state") if rest[1] in "rs" else ("person", "gender", "number")
            )
            out.update({k: c for k, c in zip(keys, tail, strict=False)})
        elif pos in "NA" and rest:
            out["type"] = rest[0]
            out.update(
                {k: c for k, c in zip(("gender", "number", "state"), rest[1:], strict=False)}
            )
        elif pos == "P" and rest:
            out["type"] = rest[0]
            keys = ("person", "gender", "number") if rest[0] == "p" else ("gender", "number")
            out.update({k: c for k, c in zip(keys, rest[1:], strict=False)})
        elif rest:
            out["type"] = rest
    sfx = [p for p in parts if p.startswith("S")]
    if sfx:
        out["suffix"] = sfx[-1][1:] if sfx[-1][1:2] != "p" else sfx[-1][2:]
    return out


def prefixes(lemma: str) -> str:
    """The prefix particles of an OSHB lemma (`c/b/6076 b` -> `cb`)."""
    return "".join(p for p in lemma.split("/") if p and not p[0].isdigit() and len(p) == 1)


def feature_diffs(kl: str, ql: str, km: str, qm: str) -> list[str]:
    """`feature k>q` for every inflection feature (and the prefixes) that differ (`-` = none)."""
    a, b = morph_features(km), morph_features(qm)
    out = [
        f"{k} {a.get(k, '-')}>{b.get(k, '-')}"
        for k in sorted(a.keys() | b.keys())
        if a.get(k) != b.get(k)
    ]
    pa, pb = prefixes(kl), prefixes(ql)
    if pa != pb:
        out.append(f"prefix {pa or '-'}>{pb or '-'}")
    return out


def numbers(lemmas: str) -> set[str]:
    return set(re.findall(r"\d+", lemmas))


def grammar_class(kl: str, ql: str, km: str, qm: str) -> str:
    """`word` (another lemma), `spelling` (same lemmas and forms) or `form`."""
    if numbers(kl) != numbers(ql):
        return "word"
    return "spelling" if (kl, km) == (ql, qm) else "form"


def letter_pairs(swaps: pd.Series, freq: dict[str, float], lookalike: set[str]) -> pd.DataFrame:
    """Every unordered letter pair: swaps observed against the count letter frequencies give."""
    obs = Counter("".join(sorted(s.replace(">", ""))) for s in swaps.dropna())
    n = sum(obs.values())
    norm = 1 - sum(p * p for p in freq.values())
    rows = []
    for i, a in enumerate(LETTERS):
        for b in LETTERS[i + 1 :]:
            pair = "".join(sorted(a + b))
            share = 2 * freq.get(a, 0) * freq.get(b, 0) / norm
            k = obs.get(pair, 0)
            rows.append(
                (pair, k, n * share, (k / (n * share)) if share else np.nan,
                 float(binom.sf(k - 1, n, share)) if k else 1.0, pair in lookalike)
            )  # fmt: skip
    df = pd.DataFrame(rows, columns=["pair", "n", "expected", "ratio", "p", "lookalike"])
    df["q"] = bh_q(df.p.to_numpy())
    return df.sort_values(["n", "pair"], ascending=[False, True])[LETTER_COLUMNS]


def lookalike_test(swaps: pd.Series, freq: dict[str, float], pairs: set[str]) -> dict[str, Any]:
    """Share of one-letter swaps between look-alike letters against frequency odds."""
    keys = ["".join(sorted(s.replace(">", ""))) for s in swaps.dropna()]
    norm = 1 - sum(p * p for p in freq.values())

    def share(ps: set[str]) -> float:
        return sum(2 * freq.get(p[0], 0) * freq.get(p[1], 0) for p in ps) / norm

    out = {}
    for name, ps in (("all", pairs), ("without_wy", pairs - {"וי"})):
        keep = [k for k in keys if name == "all" or k != "וי"]
        n, k, e = len(keep), sum(x in ps for x in keep), share(ps)
        if name != "all":  # the swaps left once ו / י is set aside, against odds renormalised
            e = e / (1 - share({"וי"}))
        out[name] = {
            "n": n,
            "lookalike": k,
            "share": k / n if n else None,
            "expected": e,
            "p": float(binom.sf(k - 1, n, e)) if n and k else 1.0,
        }
    return out


def late_fuller(pairs: pd.DataFrame, late: set[int], reps: int, rng) -> dict[str, Any]:
    """Among vowel-letter pairs: is the ketiv the fuller spelling more often in the late books?
    Null: the late label permuted over the books with such pairs."""
    vl = pairs[pairs.cls == "vowel_letter"]
    by_book = vl.groupby("book_id").fuller.agg(lambda s: ((s == "ketiv").sum(), len(s)))
    books = np.array(by_book.index)
    kf = np.array([x[0] for x in by_book])
    nn = np.array([x[1] for x in by_book])
    is_late = np.isin(books, list(late))

    def stat(lab: np.ndarray) -> float:
        return kf[lab].sum() / nn[lab].sum() - kf[~lab].sum() / nn[~lab].sum()

    if not is_late.any() or is_late.all():
        return {"late": None, "other": None, "diff": None, "p": None}
    obs = stat(is_late)
    null = np.array([stat(rng.permutation(is_late)) for _ in range(reps)])
    return {
        "late": float(kf[is_late].sum() / nn[is_late].sum()),
        "late_n": int(nn[is_late].sum()),
        "other": float(kf[~is_late].sum() / nn[~is_late].sum()),
        "other_n": int(nn[~is_late].sum()),
        "diff": float(obs),
        "p": empirical_p(obs, null),
        "books": int(len(books)),
    }


def parallel_readings(
    pairs: pd.DataFrame, words: pd.DataFrame, sequences: pd.DataFrame, cfg: dict[str, Any]
) -> pd.DataFrame:
    """`parallel`, `partner_vid`, `partner_form` for the one-word ketiv / qere of verses aligned
    to a parallel: the partner as written (its own ketiv when it has one)."""
    d = cfg["diffs"]
    keep = sequences.q <= d["max_q"]
    if not d["same_chapter"]:
        keep &= ~sequences.same_chapter.astype(bool)
    vw = verse_words(words)
    single = pairs[(pairs.n_ketiv == 1) & (pairs.n_qere == 1)]
    ketiv_at = {
        (v, p): k for v, p, k in zip(single.verse_id, single.pos, single.ketiv_c, strict=True)
    }
    found: dict[tuple[int, int], tuple[str, int, str]] = {}
    for s in sequences[keep].itertuples(index=False):
        for a, b, *_ in json.loads(s.pairs):
            for x, y in ((a, b), (b, a)):
                wx = vw.get(x, [])
                here = [i for i, _ in enumerate(wx) if (x, i) in ketiv_at and (x, i) not in found]
                if not here:
                    continue
                wy = vw.get(y, [])
                ops = align_words(wx, wy, d["match"], d["mismatch"], d["gap"])
                if shared_ratio(ops, len(wx), len(wy)) < d["min_shared"]:
                    continue
                partner = {o.a: o.b for o in ops if o.a is not None and o.b is not None}
                for i in here:
                    if i not in partner:
                        continue
                    j = partner[i]
                    written = ketiv_at.get((y, j), fold_finals(wy[j].form))
                    k, q = ketiv_at[(x, i)], fold_finals(wx[i].form)
                    label = "ketiv" if written == k else "qere" if written == q else "neither"
                    found[(x, i)] = (label, y, written)
    out = pairs[["verse_id", "pos"]].apply(
        lambda r: found.get((r.verse_id, r.pos), (None, None, None)), axis=1, result_type="expand"
    )
    out.columns = ["parallel", "partner_vid", "partner_form"]
    return out


def read_pairs(raw: Path, verses: pd.DataFrame) -> pd.DataFrame:
    """Every ketiv / qere of the OSHB books, with its verse id and word position. Where several
    OSHB verses make one verse (the Decalogue, Num 25:19 + 26:1) the read words of the earlier
    ones are counted before the later one's."""
    vid = {o: v for v, os_ in zip(verses.verse_id, verses.oshb_osis, strict=True) for o in os_}
    seen: Counter[int] = Counter()  # read words of the verse's OSHB verses so far
    rows = []
    for b in BOOKS:
        for verse in etree.parse(str(raw / f"{b.osis}.xml")).iter(f"{NS}verse"):
            v = vid[verse.get("osisID")]
            offset = seen[v]
            seen[v] += len(parse_verse(verse, "qere").words)
            for p in kq_pairs(verse):
                k = [w.surface for w in p.ketiv]
                q = [w.surface for w in p.qere]
                rows.append(
                    {
                        "verse_id": v,
                        "book_id": b.book_id,
                        "pos": p.pos + offset,
                        "n_ketiv": len(k),
                        "n_qere": len(q),
                        "ketiv": " ".join(k),
                        "qere": " ".join(q),
                        "ketiv_c": letters_of(k),
                        "qere_c": letters_of(q),
                        "ketiv_lemma": " ".join(w.lemma for w in p.ketiv),
                        "qere_lemma": " ".join(w.lemma for w in p.qere),
                        "ketiv_morph": " ".join(w.morph for w in p.ketiv),
                        "qere_morph": " ".join(w.morph for w in p.qere),
                    }
                )
    return pd.DataFrame(rows)


def run_ketiv(cfg: dict[str, Any], log: Log = print) -> Path:
    kc = cfg["ketiv"]
    proc, art = resolve_path(cfg, "data_processed"), resolve_path(cfg, "artifacts")
    raw = resolve_path(cfg, "data_raw") / "oshb"
    t0 = time.perf_counter()
    verses = pd.read_parquet(proc / "verses.parquet", columns=["verse_id", "book_id", "oshb_osis"])
    words = pd.read_parquet(
        proc / "words.parquet",
        columns=["verse_id", "idx", "surface", "lemma", "content_lemmas", "kq"],
    )
    pairs = read_pairs(raw, verses)
    _check_positions(pairs, words)
    cls = [
        letter_class(a, b, k, q)
        for a, b, k, q in zip(pairs.n_ketiv, pairs.n_qere, pairs.ketiv_c, pairs.qere_c, strict=True)
    ]
    pairs["cls"], pairs["fuller"], pairs["letters"] = (
        zip(*cls, strict=True) if cls else ([], [], [])
    )
    pairs["grammar"] = [
        None if a == 0 or b == 0 else grammar_class(kl, ql, km, qm)
        for a, b, kl, ql, km, qm in zip(
            pairs.n_ketiv, pairs.n_qere, pairs.ketiv_lemma, pairs.qere_lemma,
            pairs.ketiv_morph, pairs.qere_morph, strict=True,
        )
    ]  # fmt: skip
    pairs["features"] = [
        json.dumps(feature_diffs(kl, ql, km, qm)) if g == "form" and a == b == 1 else "[]"
        for g, a, b, kl, ql, km, qm in zip(
            pairs.grammar, pairs.n_ketiv, pairs.n_qere, pairs.ketiv_lemma, pairs.qere_lemma,
            pairs.ketiv_morph, pairs.qere_morph, strict=True,
        )
    ]  # fmt: skip
    euph = [(str(a), str(b)) for a, b in kc["euphemisms"]]
    pairs["euphemism"] = [
        int(any(a in numbers(kl) and b in numbers(ql) for a, b in euph))
        for kl, ql in zip(pairs.ketiv_lemma, pairs.qere_lemma, strict=True)
    ]
    seq_path = art / "sequences" / "verse.parquet"
    if seq_path.exists():
        par = parallel_readings(pairs, words, pd.read_parquet(seq_path), cfg)
        pairs = pd.concat([pairs, par], axis=1)
    else:
        pairs["parallel"], pairs["partner_vid"], pairs["partner_form"] = None, None, None
    pairs = pairs.sort_values(["verse_id", "pos"], kind="stable").reset_index(drop=True)
    pairs.insert(0, "kq_id", np.arange(1, len(pairs) + 1))
    pairs["partner_vid"] = pairs.partner_vid.astype("Int64")

    # letter frequencies of the written text (the corpus with the ketiv letters)
    text = "".join(fold_finals(consonantal(s).replace(" ", "")) for s in words.surface)
    counts = Counter(c for c in text if c in LETTERS)
    total = sum(counts.values())
    freq = {c: counts[c] / total for c in LETTERS}
    lookalike = {"".join(sorted(p)) for p in kc["lookalike"]}
    swaps = pairs.loc[pairs.cls == "swap", "letters"]
    letters = letter_pairs(swaps, freq, lookalike)
    rng = np.random.default_rng(kc["seed"])
    late = {BY_OSIS[o].book_id for o in cfg["dating"]["late"]}

    n_words = words.verse_id.map(verses.set_index("verse_id").book_id).value_counts()
    rows = []
    for b in BOOKS:
        g = pairs[pairs.book_id == b.book_id]
        vl = g[g.cls == "vowel_letter"]
        nw = int(n_words.get(b.book_id, 0))
        rows.append(
            {
                "book_id": b.book_id,
                "n": len(g),
                "words": nw,
                "rate": 1000 * len(g) / nw if nw else 0.0,
                "vowel_letter": len(vl),
                "ketiv_fuller": float((vl.fuller == "ketiv").mean()) if len(vl) else None,
                "swap": int((g.cls == "swap").sum()),
                "division": int(g.cls.isin(["division", "qere_only", "ketiv_only"]).sum()),
                "other_cls": int(
                    g.cls.isin(["other", "metathesis", "vowel_position", "same_letters"]).sum()
                ),
                "form": int((g.grammar == "form").sum()),
                "word": int((g.grammar == "word").sum()),
            }
        )
    books = pd.DataFrame(rows, columns=BOOK_COLUMNS)
    obs = books.n.to_numpy()
    exp = books.words.to_numpy() / books.words.sum() * obs.sum()
    chi = chisquare(obs, exp) if obs.sum() else None

    par = pairs.parallel.value_counts().to_dict()
    decided = par.get("qere", 0) + par.get("ketiv", 0)
    feats = Counter(f for fs in pairs.features for f in json.loads(fs))
    # a written ־ו read ־יו: the plural "his ...s", which the ketiv may spell defectively
    plural = pairs.features.str.contains('"number s>p"')
    waw = plural & pairs.ketiv_c.str.endswith("ו") & pairs.qere_c.str.endswith("יו")
    checks = {
        "lookalike": lookalike_test(swaps, freq, lookalike),
        "late_fuller": late_fuller(pairs, late, kc["shuffles"], rng),
        "parallel": {
            "qere": int(par.get("qere", 0)),
            "ketiv": int(par.get("ketiv", 0)),
            "neither": int(par.get("neither", 0)),
            "p": float(binomtest(par.get("qere", 0), decided, 0.5).pvalue) if decided else None,
        },
        "plural_suffix": {"plural": int(plural.sum()), "waw_yw": int(waw.sum())},
        "books": {
            "chi2": float(chi.statistic) if chi is not None else None,
            "p": float(chi.pvalue) if chi is not None else None,
        },
    }
    out = art / "ketiv"
    out.mkdir(parents=True, exist_ok=True)
    pairs[PAIR_COLUMNS].to_parquet(out / "pairs.parquet")
    letters.to_parquet(out / "letters.parquet")
    books.to_parquet(out / "books.parquet")
    meta = {
        "config_hash": config_hash(cfg, "ketiv", "diffs", "sequences"),
        "built_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "pairs": int(len(pairs)),
        "classes": {k: int(v) for k, v in pairs.cls.value_counts().items()},
        "grammar": {k: int(v) for k, v in pairs.grammar.value_counts().items()},
        "euphemisms": int(pairs.euphemism.sum()),
        "features": [[f, n] for f, n in feats.most_common(kc["features_top"])],
        "checks": _clean(checks),
        "seconds": round(time.perf_counter() - t0, 1),
    }
    (out / "ketiv.meta.json").write_text(
        json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    log(
        f"done: {len(pairs)} ketiv / qere {meta['classes']}; parallels {checks['parallel']}"
        f" ({meta['seconds']} s) -> {out}"
    )
    return out


def _check_positions(pairs: pd.DataFrame, words: pd.DataFrame) -> None:
    """Every read word of a pair must be a qere word of the corpus at that position."""
    q = set(zip(words.verse_id[words.kq == "q"], words.idx[words.kq == "q"], strict=True))
    bad = [
        (v, p)
        for v, p, n in zip(pairs.verse_id, pairs.pos, pairs.n_qere, strict=True)
        if n and (v, p) not in q
    ]
    if bad:
        raise RuntimeError(
            f"{len(bad)} ketiv / qere positions do not match the corpus, e.g. {bad[:3]}"
        )


def _clean(x: Any) -> Any:
    if isinstance(x, dict):
        return {k: _clean(v) for k, v in x.items()}
    if isinstance(x, float):
        return None if np.isnan(x) else float(f"{x:.6g}")  # small p-values keep their digits
    if isinstance(x, np.integer):
        return int(x)
    return x
