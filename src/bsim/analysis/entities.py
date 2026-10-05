"""`bsim entities`: people and places, who appears with whom (DESIGN.md §16.11).

OSHB tags every name as a proper noun (`Np`) without saying whether it is a person or a place, so
each name lemma is classified from its contexts (`classify`):

- place cues: directional ה (`Sd`: מִצְרַיְמָה), a preceding עִיר / אֶרֶץ, the prefixes בְּ / מִן;
- person cues: a neighbouring בֵּן / בַּת ("X son of Y"), a preceding verb of speech (וַיֹּאמֶר משֶׁה).

`place = 3·directional + 3·city/land + in/from`, `person = 2·son/daughter + 3·speech` (shares of
the name's occurrences); `person` (tribes and peoples included: "sons of Ammon") or `place` when
one score is `dominance` times the other and above `min_cue`, `mixed` when both are, `unclear`
without cues (mostly rare names in lists). Divine names (`skip_lemmas`) are left out.

With `bsim lexicon` (DESIGN.md §16.22) Strong's part of speech decides first: `n-pr-m` / `n-pr-f`
make a person, `n-pr-loc` a place; a name Strong's gives both readings (Gilead, Ephraim), or none,
keeps the cue reading (`kind_source`: lexicon | cues). The cue reading is kept as `kind_cues`, and
the meta reports how often the two agree where both decide.

Who appears with whom: two names co-occur when they share a verse. For every pair seen in at least
`min_together` verses, Dunning's G² against independence (verse counts) measures how much more
often they meet than their frequencies predict; each name keeps its `partners` strongest links.

Writes `artifacts/entities/`: `entities.parquet` (`lemma, he, kind, n_mentions, n_verses,
first_vid, last_vid, place, person, kind_cues, kind_source`), `mentions.parquet` (`lemma,
verse_id, n`) and `links.parquet` (`a, b, n_verses, expected, g2`, both directions), plus
`entities.meta.json`.
"""

from __future__ import annotations

import json
import math
import time
from collections import Counter
from collections.abc import Callable
from datetime import UTC, datetime
from itertools import combinations
from pathlib import Path
from typing import Any

import pandas as pd

from bsim.config import config_hash, resolve_path
from bsim.data.lexicon import strong_key

Log = Callable[[str], None]

SON = {"1121a", "1323"}  # בן, בת
CITY_LAND = {"5892", "776"}  # עיר, ארץ
SPEECH = {"559", "1696"}  # אמר, דבר


def is_name(morph: str | None) -> bool:
    return isinstance(morph, str) and any(p.startswith("Np") for p in morph[1:].split("/"))


def name_cues(words: pd.DataFrame) -> pd.DataFrame:
    """One row per name occurrence: `lemma, verse_id` and the boolean context cues."""
    w = words.sort_values(["verse_id", "idx"], ignore_index=True)
    first = w.content_lemmas.map(lambda c: c[0] if len(c) else "")
    same_prev = w.verse_id.shift(1) == w.verse_id
    same_next = w.verse_id.shift(-1) == w.verse_id
    prev, nxt = first.shift(1).fillna(""), first.shift(-1).fillna("")
    names = w.morph.map(is_name) & (w.content_lemmas.map(len) == 1)
    morph = w.morph.fillna("")
    prefix = w.lemma.str.split("/").map(lambda p: len(p) > 1 and p[0] in ("b", "m"))
    return pd.DataFrame(
        {
            "lemma": first[names],
            "verse_id": w.verse_id[names],
            "directional": morph[names].str.contains("Sd", regex=False),
            "city_land": (prev.isin(CITY_LAND) & same_prev)[names],
            "in_from": prefix[names],
            "son": ((prev.isin(SON) & same_prev) | (nxt.isin(SON) & same_next))[names],
            "speech": (prev.isin(SPEECH) & same_prev)[names],
        }
    ).reset_index(drop=True)


def classify(place: float, person: float, dominance: float, min_cue: float) -> str:
    if place < min_cue and person < min_cue:
        return "unclear"
    if person >= dominance * place:
        return "person"
    if place >= dominance * person:
        return "place"
    return "mixed"


def lexicon_kinds(proc: Path) -> dict[str, str] | None:
    """Strong key -> person / place / both from Strong's parts of speech; None without
    `bsim lexicon`."""
    path = proc / "lexicon_lemmas.parquet"
    if not path.exists():
        return None
    lm = pd.read_parquet(path).dropna(subset=["name_kind"])
    return dict(zip(lm.strong, lm.name_kind, strict=True))


def agreement(lex: list[str | None], cues: list[str]) -> dict[str, Any]:
    """Where Strong's and the cues both decide person / place: how often they agree."""
    both = [(a, b) for a, b in zip(lex, cues, strict=True) if a in KINDS and b in KINDS]
    table = Counter(f"{a}/{b}" for a, b in both)
    return {
        "decided_by_both": len(both),
        "agree": round(sum(a == b for a, b in both) / len(both), 4) if both else None,
        "lexicon/cues": dict(sorted(table.items())),
    }


KINDS = ("person", "place")


def g2(k: int, n_a: int, n_b: int, n: int) -> float:
    """Dunning's log-likelihood of a 2x2 table: k verses with both, n_a / n_b with each, n total."""
    cells = [(k, n_a * n_b / n), (n_a - k, n_a * (n - n_b) / n)]
    cells += [(n_b - k, (n - n_a) * n_b / n), (n - n_a - n_b + k, (n - n_a) * (n - n_b) / n)]
    return 2 * sum(o * math.log(o / e) for o, e in cells if o > 0 and e > 0)


def links(
    verse_names: dict[int, set[str]], n_verses: dict[str, int], n_total: int, min_together: int
) -> pd.DataFrame:
    """`a, b, n_verses, expected, g2` for name pairs sharing ≥ `min_together` verses (a < b)."""
    together: Counter[tuple[str, str]] = Counter()
    for names in verse_names.values():
        together.update(combinations(sorted(names), 2))
    rows = []
    for (a, b), k in together.items():
        if k < min_together:
            continue
        expected = n_verses[a] * n_verses[b] / n_total
        if k > expected:
            rows.append((a, b, k, expected, g2(k, n_verses[a], n_verses[b], n_total)))
    return pd.DataFrame(rows, columns=["a", "b", "n_verses", "expected", "g2"])


def top_partners(pairs: pd.DataFrame, per_name: int) -> pd.DataFrame:
    """Both directions of every link, each name's `per_name` strongest kept."""
    both = pd.concat([pairs, pairs.rename(columns={"a": "b", "b": "a"})], ignore_index=True)
    both = both.sort_values(["a", "g2", "b"], ascending=[True, False, True])
    return both.groupby("a", sort=False).head(per_name).reset_index(drop=True)


def run_entities(cfg: dict[str, Any], log: Log = print) -> Path:
    from bsim.store.db import lemma_display_forms

    proc = resolve_path(cfg, "data_processed")
    ec = cfg["entities"]
    n_total = len(pd.read_parquet(proc / "verses.parquet", columns=["verse_id"]))
    words = pd.read_parquet(
        proc / "words.parquet",
        columns=["verse_id", "idx", "surface", "lemma", "content_lemmas", "morph"],
    )
    t0 = time.perf_counter()
    cues = name_cues(words)
    cues = cues[~cues.lemma.isin(set(ec["skip_lemmas"]))]
    g = cues.groupby("lemma").agg(
        n_mentions=("verse_id", "size"),
        n_verses=("verse_id", "nunique"),
        first_vid=("verse_id", "min"),
        last_vid=("verse_id", "max"),
        directional=("directional", "mean"),
        city_land=("city_land", "mean"),
        in_from=("in_from", "mean"),
        son=("son", "mean"),
        speech=("speech", "mean"),
    )
    g["place"] = 3 * g.directional + 3 * g.city_land + g.in_from
    g["person"] = 2 * g.son + 3 * g.speech
    g["kind"] = [
        classify(pl, pe, ec["dominance"], ec["min_cue"])
        for pl, pe in zip(g.place, g.person, strict=True)
    ]
    g["kind_cues"] = g["kind"]
    g["kind_source"] = "cues"
    lex = lexicon_kinds(proc)
    lex_kind: list[str | None] = [None] * len(g)
    if lex is None:
        log("  no lexicon (`bsim lexicon`): names typed from context cues only")
    else:
        lex_kind = [lex.get(strong_key(lemma)) for lemma in g.index]
        decided = [k in KINDS for k in lex_kind]
        g.loc[decided, "kind"] = [k for k in lex_kind if k in KINDS]
        g.loc[decided, "kind_source"] = "lexicon"
    he = dict(zip(*lemma_display_forms(words)[["lemma", "he_lemma"]].T.values, strict=True))
    g["he"] = g.index.map(he)
    ents = g.reset_index()[
        [
            "lemma",
            "he",
            "kind",
            "n_mentions",
            "n_verses",
            "first_vid",
            "last_vid",
            "place",
            "person",
            "kind_cues",
            "kind_source",
        ]
    ].round({"place": 4, "person": 4})

    mentions = cues.groupby(["lemma", "verse_id"]).size().rename("n").reset_index()
    verse_names = mentions.groupby("verse_id").lemma.agg(set).to_dict()
    pairs = links(
        verse_names, dict(zip(ents.lemma, ents.n_verses, strict=True)), n_total, ec["min_together"]
    )
    kept = top_partners(pairs, ec["partners"]).round({"expected": 4, "g2": 4})

    out = resolve_path(cfg, "artifacts") / "entities"
    out.mkdir(parents=True, exist_ok=True)
    ents.to_parquet(out / "entities.parquet")
    mentions.to_parquet(out / "mentions.parquet")
    kept.to_parquet(out / "links.parquet")
    meta = {
        "config_hash": config_hash(cfg, "entities"),
        "built_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "names": int(len(ents)),
        "kinds": dict(Counter(ents.kind)),
        "kind_sources": dict(Counter(ents.kind_source)),
        "lexicon_vs_cues": agreement(lex_kind, g["kind_cues"].tolist()),
        "mentions": int(ents.n_mentions.sum()),
        "pairs": int(len(pairs)),
        "links_kept": int(len(kept)),
        "seconds": round(time.perf_counter() - t0, 1),
    }
    (out / "entities.meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    log(
        f"done: {meta['names']} names {meta['kinds']}, {meta['pairs']} linked pairs"
        f" ({meta['links_kept']} kept) in {meta['seconds']} s -> {out}"
    )
    return out
