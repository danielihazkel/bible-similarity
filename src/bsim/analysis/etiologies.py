"""`bsim etiologies`: names given in the text and the words that explain them (DESIGN.md §16.66).

ותקרא שמו ראובן כי אמרה כי ראה יהוה בעניי (Gen 29:32): a naming etiology explains a name by a
word that sounds like it. Does the text's explanation echo
its name more than an explanation given for another name would?

- **Namings.** A form of קרא (`call`, not after a לא) followed within `trigger_within` words by
  שם with a 2nd / 3rd person suffix or in construct (שמו, שם המקום, שם בנו), by למקום, or by a
  pronoun object (לו, אתה) directly before the name; the name is the first proper noun within
  `name_within` words after it (a multi-word name, באר שבע, whole; a preposition before it, or a
  name of God (`skip_names`): no naming). A naming is a place's when מקום, עיר or באר stands
  between the verb and the name.
- **Explanations.** The other content words of the naming's verse (not the verb, שם and the name;
  no conjunction, preposition, particle, pronoun or proper noun), each without its prefixes.
- **Echo.** For a name and an explanation: the most of a name word's consonants found in order in
  one explanation word (at least `min_shared`), as a share of that name word's consonants; the best
  over the name's words and the explanation's words. Gen 29:32 ראובן / ראה: 2 of 5.
- **Claim fixed in advance.** The mean echo of each name with its own explanation exceeds the mean
  with the explanations shuffled among the names (`shuffles`), one-sided at `alpha`. Each naming's
  rank among the explanations (ties counted against it) says how it stands among them; its echo
  against `verse_draws` random verses without a naming gives its own p, BH q over the namings.
- **Known answers.** The etiologies of `known` are found by the formula with their names, and at
  least `known_share` of them echo: their own explanation beats all but `known_rank` of the others.

Writes `artifacts/etiologies/namings.parquet` (`naming, verse_id, book_id, name, kind, name_idx,
name_len, name_first, name_last` (display tokens), `echo_idx, echo_word, echo_disp, words, score,
chance` (the name's mean echo with the other explanations), `rank_p, p, q, known`) and
`etiologies.meta.json`.
"""

from __future__ import annotations

import json
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from functools import cache
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from bsim.analysis.stats import bh_q, empirical_p
from bsim.config import config_hash, resolve_path
from bsim.data.refs import RefIndex
from bsim.store.lexicon import strip_prefixes
from bsim.text.normalize import fold_finals

Log = Callable[[str], None]


def key(part: str) -> str:
    """A lemma part as a Strong's key: no spaces, no `+` (the first word of a multi-word name)."""
    return str(part).replace(" ", "").rstrip("+")


def lemma_parts(lemma: Any) -> list[str]:
    return [key(p) for p in str(lemma).split("/")]


def morph_parts(morph: Any) -> tuple[str, list[str]]:
    """(the main part, the suffixes) of an OSHB morph, the language letter dropped."""
    if not isinstance(morph, str) or len(morph) < 2:
        return "", []
    ps = morph[1:].split("/")
    suffixes = [p for p in ps if p.startswith("S")]
    rest = [p for p in ps if not p.startswith("S")]
    return (rest[-1] if rest else ""), suffixes


def is_proper(morph: Any) -> bool:
    return morph_parts(morph)[0].startswith(("Np", "Ng"))


def form(surface: str, lemma: str) -> str:
    """Consonants without the prefix morphemes, finals folded."""
    return fold_finals(strip_prefixes(surface, str(lemma)))


@cache
def lcs(a: str, b: str) -> int:
    """Length of the longest common subsequence of two strings."""
    prev = [0] * (len(b) + 1)
    for ca in a:
        cur = [0]
        for j, cb in enumerate(b):
            cur.append(prev[j] + 1 if ca == cb else max(prev[j + 1], cur[j]))
        prev = cur
    return prev[-1]


def echo(name: list[str], expl: list[str], min_shared: int) -> tuple[float, int]:
    """The best share of a name word's consonants found in order in one explanation word, and
    that word's position (-1: none reaches `min_shared`; of equal shares, the word with the most
    of its own letters in the name)."""
    best, at = (0.0, 0.0), -1
    for p in name:
        for k, w in enumerate(expl):
            n = lcs(p, w)
            if n >= min_shared and (n / len(p), n / len(w)) > best:
                best, at = (n / len(p), n / len(w)), k
    return best[0], at


@dataclass
class Word:
    idx: int
    surface: str
    lemma: str
    morph: Any
    content: bool
    display_idx: int | None


@dataclass
class Naming:
    verse_id: int
    call: int  # position of the verb in the verse's word list
    span: list[int]  # positions of the name's words
    kind: str  # person | place
    name: list[str] = field(default_factory=list)  # the name's words, consonantal, finals folded
    written: list[str] = field(default_factory=list)  # ... as written
    expl: list[int] = field(default_factory=list)  # positions of the explanation words


def find_namings(ws: list[Word], verse_id: int, ec: dict[str, Any]) -> list[Naming]:
    """The naming formulas of one verse (its words in order)."""
    call, noun, place = key(ec["call"]), key(ec["name_noun"]), key(ec["place_noun"])
    neg, skip = key(ec["negation"]), {key(x) for x in ec["skip_names"]}
    place_words = {key(x) for x in ec["place_words"]}
    parts = [lemma_parts(w.lemma) for w in ws]
    out: list[Naming] = []
    seen: set[int] = set()
    for i in range(len(ws)):
        if call not in parts[i]:
            continue
        if any(neg in parts[k] for k in range(max(0, i - ec["negation_before"]), i)):
            continue
        start, within = None, 0
        for j in range(i + 1, min(len(ws), i + 1 + ec["trigger_within"])):
            ps = parts[j]
            main, suffixes = morph_parts(ws[j].morph)
            # שמו / שמך (a 2nd or 3rd person suffix), שם המקום (construct), למקום
            named = (suffixes and suffixes[0][2:3] in ("2", "3")) or (
                not suffixes and main[-1:] == "c"
            )
            if (ps == [noun] and named) or ps == ["l", place]:
                start, within = j + 1, ec["name_within"]
            elif ps in (["l"], ["853"]) and suffixes:
                start, within = j + 1, 1
            if start is not None:
                break
        if start is None:
            continue
        k = next(
            (
                k
                for k in range(start, min(len(ws), start + within))
                if is_proper(ws[k].morph) or str(ws[k].lemma).endswith("+")
            ),
            None,
        )
        if k is None or k in seen or len(parts[k]) != 1 or parts[k][0] in skip:
            continue
        span = [k]
        while span[-1] + 1 < len(ws) and parts[span[-1] + 1] == parts[k]:
            span.append(span[-1] + 1)
        seen.add(k)
        kind = "place" if any(set(parts[x]) & place_words for x in range(i + 1, k)) else "person"
        n = Naming(verse_id, i, span, kind)
        n.written = [strip_prefixes(ws[x].surface, ws[x].lemma) for x in span]
        n.name = [fold_finals(x) for x in n.written]
        out.append(n)
    return out


def explanation(ws: list[Word], n: Naming, ec: dict[str, Any]) -> list[int]:
    """Positions of the verse's content words outside the formula and the name."""
    return content_words(ws, ec, set(range(n.call, n.span[-1] + 1)))


def content_words(ws: list[Word], ec: dict[str, Any], skip: set[int] | None = None) -> list[int]:
    """Positions of a verse's content words (no particle, pronoun or proper noun) long enough to
    echo a name, but those in `skip`."""
    skip_pos, skip = set(ec["skip_pos"]), skip or set()
    out = []
    for k, w in enumerate(ws):
        if k in skip or not w.content:
            continue
        main = morph_parts(w.morph)[0]
        if main[:1] in skip_pos or main.startswith(("Np", "Ng")):
            continue
        if len(form(w.surface, w.lemma)) >= ec["min_letters"]:
            out.append(k)
    return out


def verse_words(words: pd.DataFrame, vids: set[int]) -> dict[int, list[Word]]:
    """The words of these verses, in order."""
    out: dict[int, list[Word]] = {}
    for vid, g in words[words.verse_id.isin(vids)].groupby("verse_id", sort=True):
        out[int(vid)] = [
            Word(int(r.idx), r.surface, str(r.lemma), r.morph, len(r.content_lemmas) > 0,
                 None if pd.isna(r.display_idx) else int(r.display_idx))
            for r in g.itertuples(index=False)
        ]  # fmt: skip
    return out


def run_etiologies(cfg: dict[str, Any], log: Log = print) -> Path:
    ec = cfg["etiologies"]
    proc, art = resolve_path(cfg, "data_processed"), resolve_path(cfg, "artifacts")
    out = art / "etiologies"
    t0 = time.perf_counter()
    verses = pd.read_parquet(
        proc / "verses.parquet", columns=["verse_id", "book_id", "chapter", "verse"]
    ).sort_values("verse_id")
    words = pd.read_parquet(
        proc / "words.parquet",
        columns=["verse_id", "idx", "surface", "lemma", "content_lemmas", "morph", "display_idx"],
    ).sort_values(["verse_id", "idx"], kind="stable")
    book_of = dict(zip(verses.verse_id, verses.book_id, strict=True))

    # namings: only verses with the verb are scanned
    call = key(ec["call"])
    has_call = {
        int(v) for v, lem in zip(words.verse_id, words.lemma, strict=True)
        if call in lemma_parts(lem)
    }  # fmt: skip
    namings: list[Naming] = []
    by_verse = verse_words(words, has_call)
    for vid, ws in by_verse.items():
        for n in find_namings(ws, vid, ec):
            n.expl = explanation(ws, n, ec)
            namings.append(n)
    log(f"{len(namings)} namings in {len(has_call)} verses with קרא")

    # every name against every explanation
    min_letters, min_shared = int(ec["min_letters"]), int(ec["min_shared"])
    names = [[p for p in n.name if len(p) >= min_letters] for n in namings]
    expls = [
        [form(by_verse[n.verse_id][k].surface, by_verse[n.verse_id][k].lemma) for k in n.expl]
        for n in namings
    ]
    m = len(namings)
    score = np.zeros((m, m))
    best = np.full(m, -1)
    for i in range(m):
        for j in range(m):
            s, at = echo(names[i], expls[j], min_shared)
            score[i, j] = s
            if i == j:
                best[i] = at
    own = np.diag(score).copy()
    off = ~np.eye(m, dtype=bool)
    chance = np.where(m > 1, (score * off).sum(axis=1) / max(1, m - 1), np.nan)
    rank_p = np.array(
        [(1 + (score[i][off[i]] >= own[i]).sum()) / m if m > 1 else np.nan for i in range(m)]
    )

    # each naming against random verses without a naming: its own p
    vrng = np.random.default_rng([ec["seed"], 1])
    pool = np.array(sorted(set(verses.verse_id) - {n.verse_id for n in namings}))
    draws = vrng.choice(pool, size=min(int(ec["verse_draws"]), len(pool)), replace=False)
    drawn = verse_words(words, set(draws.tolist()))
    pool_forms = [
        [form(ws[k].surface, ws[k].lemma) for k in content_words(ws, ec)] for ws in drawn.values()
    ]
    verse_p = np.array(
        [
            (1 + sum(echo(names[i], f, min_shared)[0] >= own[i] for f in pool_forms))
            / (1 + len(pool_forms))
            for i in range(m)
        ]
    )
    q = bh_q(verse_p)

    # the claim: own explanations against shuffled ones
    rng = np.random.default_rng(ec["seed"])
    reps, alpha = int(ec["shuffles"]), float(ec["alpha"])
    if m > 1:
        perms = np.argsort(rng.random((reps, m)), axis=1)
        null = score[np.arange(m)[None, :], perms].mean(axis=1)
        p = empirical_p(float(own.mean()) - 1e-12, null)
        mean_null = float(null.mean())
    else:
        p, mean_null = 1.0, float("nan")
    log(
        f"mean echo {own.mean():.3f} with their own explanations, {mean_null:.3f} shuffled,"
        f" p {p:.4g}"
    )

    # the known etiologies
    index = RefIndex(verses)
    known_rows, known_of = [], {}
    for kn in ec["known"]:
        want = fold_finals(kn["name"]).split()
        try:
            vid = index.resolve(kn["ref"])[0]
        except (ValueError, KeyError):
            vid = None
        hit = next((i for i, n in enumerate(namings) if n.verse_id == vid and n.name == want), None)
        row: dict[str, Any] = {"ref": kn["ref"], "name": kn["name"], "found": hit is not None,
                               "naming": hit, "score": None, "rank_p": None,
                               "echoes": False}  # fmt: skip
        if hit is not None:
            known_of[hit] = True
            row.update(score=float(own[hit]), rank_p=float(rank_p[hit]),
                       echoes=bool(rank_p[hit] <= ec["known_rank"]))  # fmt: skip
        known_rows.append(row)
    known_found = sum(r["found"] for r in known_rows)
    known_echo = sum(r["echoes"] for r in known_rows)
    n_known = len(known_rows)
    known_holds = (
        bool(n_known) and known_found == n_known and (known_echo >= ec["known_share"] * n_known)
    )
    log(f"known: {known_found} of {n_known} found, {known_echo} echo their name")

    def disp(n: Naming, k: int) -> int | None:
        return by_verse[n.verse_id][k].display_idx

    df = pd.DataFrame(
        {
            "naming": np.arange(m, dtype=int),
            "verse_id": [n.verse_id for n in namings],
            "book_id": [int(book_of[n.verse_id]) for n in namings],
            "name": [" ".join(n.written) for n in namings],
            "kind": [n.kind for n in namings],
            "name_idx": [by_verse[n.verse_id][n.span[0]].idx for n in namings],
            "name_len": [len(n.span) for n in namings],
            "name_first": [disp(n, n.span[0]) for n in namings],
            "name_last": [disp(n, n.span[-1]) for n in namings],
            "echo_idx": [
                by_verse[n.verse_id][n.expl[b]].idx if b >= 0 else None
                for n, b in zip(namings, best, strict=True)
            ],
            "echo_word": [
                strip_prefixes(
                    by_verse[n.verse_id][n.expl[b]].surface, by_verse[n.verse_id][n.expl[b]].lemma
                )
                if b >= 0
                else None
                for n, b in zip(namings, best, strict=True)
            ],
            "echo_disp": [
                disp(n, n.expl[b]) if b >= 0 else None for n, b in zip(namings, best, strict=True)
            ],
            "words": [len(n.expl) for n in namings],
            "score": own.round(4),
            "chance": np.round(chance, 4),
            "rank_p": rank_p,
            "p": verse_p,
            "q": q,
            "known": [i in known_of for i in range(m)],
        }
    ).astype({c: "Int64" for c in ("name_first", "name_last", "echo_idx", "echo_disp")})

    out.mkdir(parents=True, exist_ok=True)
    df.to_parquet(out / "namings.parquet", index=False)
    meta = {
        "config_hash": config_hash(cfg, "etiologies"),
        "built_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "namings": m,
        "places": int((df.kind == "place").sum()),
        "explained": int((df.words > 0).sum()),
        "mean_own": round(float(own.mean()), 4) if m else None,
        "mean_null": round(mean_null, 4) if m > 1 else None,
        "p": p,
        "shuffles": reps,
        "verse_draws": len(pool_forms),
        "alpha": alpha,
        "holds": bool(m > 1 and own.mean() > mean_null and p <= alpha),
        "leads": int((df.q <= alpha).sum()),
        "known": known_rows,
        "known_found": known_found,
        "known_echo": known_echo,
        "known_rank": ec["known_rank"],
        "known_share": ec["known_share"],
        "known_holds": known_holds,
        "seconds": round(time.perf_counter() - t0, 1),
    }
    (out / "etiologies.meta.json").write_text(
        json.dumps(meta, indent=2, ensure_ascii=False), "utf-8"
    )
    log(
        f"done: {m} namings ({meta['places']} places); the echo"
        f" {'holds' if meta['holds'] else 'is not borne out'}, {meta['leads']} at q ≤ {alpha};"
        f" the known {'hold' if known_holds else 'fail'}"
        f" ({meta['seconds']} s) -> {out}"
    )
    return out / "namings.parquet"
