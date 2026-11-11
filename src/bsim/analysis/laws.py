"""`bsim laws`: the law codes side by side (DESIGN.md §16.93, D155; M166).

The Pentateuch gives some laws more than once: the release of a Hebrew slave in the Covenant Code
(Exod 21:2-11), the Holiness Code (Lev 25:39-46) and Deuteronomy (15:12-18), each in its own words.
This stage cuts the codes into laws, says how each is put, finds the laws of one code that another
gives again, and sets them side by side word by word.

- **Codes and laws.** Each code is a set of verse ranges (`codes`); its laws are its Masoretic
  paragraphs (pericopes) clipped to the ranges.
- **Form.** Casuistic when a clause in the law's first `opening` verses opens with כי or אם (`if`)
  and a yiqtol follows within `if_reach` words (וכי יגנב איש …; the first run took every כי, and
  Exod 34:10's כי נורא הוא, "for it is awesome", made the ritual decalogue casuistic); else
  apodictic when it has לא + yiqtol, אל + jussive (`not`) or מות יומת (`die`); else other (a
  frame, an exhortation, a list). The address: the person of most of its finite verbs, 2ms, 2mp
  or 3rd (`mixed` on a tie).
- **Matching.** Two verses are linked when one is among the other's first `top_k` neighbours on the
  stored fused verse list. A pair of laws in two codes is matched when it has at least `min_links`
  linked verse pairs and one law is among the other's `best` in its code, by the fused scores of
  the links over √(n₁·n₂).
- **Side by side.** A matched pair is aligned word by word (`diffs.align_words`, the `diffs`
  scores) over its linked verses, from the first to the last on each side (span to span, as
  `retold.py` aligns a retelling), each side cut to `max_words`.
- **Known answers.** Laws the commentaries set side by side (`known`): each pair of a group's
  members counts, found when a matched pair joins a law overlapping one and a law overlapping the
  other; the groups hold when `known_share` of the member pairs are found. Beside it, stricter
  (`strict`, `known_strict`): the aligned verses themselves touch each passage.

Writes `artifacts/laws/`: `laws.parquet` (`law_id, code, unit_id, book_id, first_vid, last_vid,
n_verses, form, casuistic, apodictic, address, v2ms, v2mp, v3`), `pairs.parquet` (`pair_id, a, b`
law ids, `code_a, code_b, links, score, a_first, a_last, b_first, b_last` (the aligned spans), the
op counts, `kept` (the share of aligned positions keeping their lemma), `known` (a group or
None)), `marks.parquet` (`pair_id, side, verse_id, display_idx, op`), `codes.parquet` (`code,
laws, verses, casuistic, apodictic, other, v2ms, v2mp, v3, mixed`) and `laws.meta.json`.
"""

from __future__ import annotations

import time
from collections import Counter, defaultdict
from collections.abc import Callable
from datetime import UTC, datetime
from itertools import combinations
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from bsim.analysis.diffs import KEPT, OPS, align_words, make_word
from bsim.analysis.prophetic import morph_parts
from bsim.config import config_hash, resolve_path, write_meta
from bsim.data.refs import RefIndex

Log = Callable[[str], None]

FORMS = ("casuistic", "apodictic", "other")
ADDRESS = ("2ms", "2mp", "3")
FINITE = set("pqiwjhv")  # OSHB verb types with a person: perfect, sequential perfect, imperfect,
# wayyiqtol, jussive, cohortative, imperative


def cut_laws(codes: dict[str, list[str]], peri: pd.DataFrame, index: RefIndex) -> pd.DataFrame:
    """Each code's paragraphs clipped to its ranges, in canon order."""
    rows = []
    for code, refs in codes.items():
        for ref in refs:
            lo, hi = index.resolve(ref)
            hit = peri[(peri.start_verse_id <= hi) & (peri.end_verse_id >= lo)]
            for p in hit.itertuples():
                a, b = max(lo, int(p.start_verse_id)), min(hi, int(p.end_verse_id))
                rows.append((code, str(p.unit_id), int(p.book_id), a, b))
    laws = pd.DataFrame(rows, columns=["code", "unit_id", "book_id", "first_vid", "last_vid"])
    laws = laws.sort_values("first_vid").reset_index(drop=True)
    laws.insert(0, "law_id", np.arange(1, len(laws) + 1))
    laws["n_verses"] = laws.last_vid - laws.first_vid + 1
    return laws


def verb_person(main: str) -> str | None:
    """`2ms`, `2mp` or `3` for a finite verb's main morph part (`Vqi2ms`, `Vqv2mp`), else None."""
    if main[:1] != "V" or main[2:3] not in FINITE:
        return None
    person, gn = main[3:4], main[4:6]
    if person == "3":
        return "3"
    if person == "2" and gn in ("ms", "mp"):
        return f"2{gn}"
    return None


def law_form(
    words: pd.DataFrame, opens: set[tuple[int, int]], first: int, fc: dict[str, Any]
) -> dict[str, Any]:
    """The form flags and the address of one law's words (`verse_id, idx, lemma, main`, in
    order)."""
    lem, main = words.lemma.to_numpy(), words.main.to_numpy()
    vid, idx = words.verse_id.to_numpy(), words.idx.to_numpy()

    def protasis(i: int) -> bool:  # a yiqtol soon after in the verse (כי יגנב, אם בגפו יבא)
        after = range(i + 1, min(i + 1 + fc["if_reach"], len(main)))
        return any(vid[j] == vid[i] and main[j][:1] == "V" and main[j][2:3] == "i" for j in after)

    casuistic = any(
        lem[i] in fc["if"] and (int(vid[i]), int(idx[i])) in opens and protasis(i)
        for i in range(len(words))
        if vid[i] < first + fc["opening"]
    )
    apodictic = False
    for i in range(len(words) - 1):
        nxt = main[i + 1]
        if (
            lem[i] in fc["not"]
            and nxt[:1] == "V"
            and nxt[2:3] in ("i", "j")
            or lem[i] == fc["die"] == lem[i + 1]
            and main[i][2:3] == "a"
            and nxt[2:3] == "i"
        ):
            apodictic = True
    persons = Counter(p for p in map(verb_person, main) if p)
    top = persons.most_common()
    address = None
    if top:
        address = "mixed" if len(top) > 1 and top[0][1] == top[1][1] else top[0][0]
    form = "casuistic" if casuistic else "apodictic" if apodictic else "other"
    return {"form": form, "casuistic": casuistic, "apodictic": apodictic, "address": address,
            **{f"v{a}": persons.get(a, 0) for a in ADDRESS}}  # fmt: skip


def link_laws(
    topk: pd.DataFrame, law_of: dict[int, int], code_of: dict[int, str], top_k: int
) -> dict[tuple[int, int], dict[tuple[int, int], float]]:
    """(law a, law b), a < b, in two codes -> {(verse of a, verse of b): fused score}."""
    t = topk[topk["rank"] <= top_k]
    src = t.src_id.str.slice(2).astype(int).to_numpy()
    tgt = t.tgt_id.str.slice(2).astype(int).to_numpy()
    out: dict[tuple[int, int], dict[tuple[int, int], float]] = defaultdict(dict)
    for s, g, sc in zip(src, tgt, t.score.to_numpy(), strict=True):
        la, lb = law_of.get(int(s)), law_of.get(int(g))
        if la is None or lb is None or code_of[la] == code_of[lb]:
            continue
        (la, va), (lb, vb) = sorted(((la, int(s)), (lb, int(g))))
        links = out[(la, lb)]
        links[(va, vb)] = max(links.get((va, vb), 0.0), float(sc))
    return out


def match_laws(
    links: dict[tuple[int, int], dict[tuple[int, int], float]],
    size: dict[int, int],
    code_of: dict[int, str],
    lc: dict[str, Any],
) -> dict[tuple[int, int], float]:
    """The matched pairs and their scores: enough links, and one law among the other's best in its
    code."""
    score = {
        k: sum(v.values()) / np.sqrt(size[k[0]] * size[k[1]])
        for k, v in links.items()
        if len(v) >= lc["min_links"]
    }
    ranked: dict[tuple[int, str], list[tuple[float, int]]] = defaultdict(list)
    for (a, b), s in score.items():
        ranked[(a, code_of[b])].append((s, b))
        ranked[(b, code_of[a])].append((s, a))
    best = {
        key: {law for _, law in sorted(c, key=lambda x: (-x[0], x[1]))[: lc["best"]]}
        for key, c in ranked.items()
    }
    return {
        (a, b): s
        for (a, b), s in score.items()
        if b in best[(a, code_of[b])] or a in best[(b, code_of[a])]
    }


def run_laws(cfg: dict[str, Any], log: Log = print) -> Path:
    lc, dc = cfg["laws"], cfg["diffs"]
    proc, art = resolve_path(cfg, "data_processed"), resolve_path(cfg, "artifacts")
    out = art / "laws"
    t0 = time.perf_counter()
    topk_path = art / "topk" / "verse" / "fused.parquet"
    clauses_path = proc / "syntax_clauses.parquet"
    for path, stage in ((topk_path, "fuse"), (clauses_path, "syntax")):
        if not path.exists():
            raise RuntimeError(f"{path} missing; run `bsim {stage}` first")
    verses = pd.read_parquet(proc / "verses.parquet")
    units = pd.read_parquet(proc / "units.parquet")
    peri = units[units.unit_type == "pericope"].sort_values("start_verse_id")
    index = RefIndex(verses)
    laws = cut_laws(lc["codes"], peri, index)
    log(f"{len(laws)} laws in {laws.code.nunique()} codes")

    words = pd.read_parquet(
        proc / "words.parquet",
        columns=["verse_id", "idx", "surface", "lemma", "content_lemmas", "morph", "display_idx"],
    ).sort_values(["verse_id", "idx"])
    words["key_lemma"] = [c[-1] if len(c) else "" for c in words.content_lemmas]
    words["main"] = [morph_parts(m)[0] for m in words.morph]
    clauses = pd.read_parquet(clauses_path, columns=["verse_id", "words"])
    opens = {(int(v), int(ws[0])) for v, ws in zip(clauses.verse_id, clauses.words, strict=True)
             if len(ws)}  # fmt: skip
    by_verse = dict(iter(words.groupby("verse_id", sort=False)))

    def law_words(a: int, b: int) -> pd.DataFrame:
        parts = [by_verse[v] for v in range(a, b + 1) if v in by_verse]
        return pd.concat(parts) if parts else words.iloc[:0]

    forms = []
    for r in laws.itertuples():
        w = law_words(r.first_vid, r.last_vid).rename(columns={"key_lemma": "lemma", "lemma": "_l"})
        forms.append(law_form(w, opens, r.first_vid, lc["form"]))
    laws = pd.concat([laws, pd.DataFrame(forms)], axis=1)

    # links and matches over the fused verse list
    law_of = {
        v: int(r.law_id) for r in laws.itertuples() for v in range(r.first_vid, r.last_vid + 1)
    }
    code_of = dict(zip(laws.law_id, laws.code, strict=True))
    size = dict(zip(laws.law_id, laws.n_verses, strict=True))
    links = link_laws(pd.read_parquet(topk_path), law_of, code_of, lc["top_k"])
    matched = match_laws(links, size, code_of, lc)
    log(f"{len(matched)} matched pairs ({len(links)} law pairs linked)")

    # each matched pair side by side, over its linked verses
    first_of = dict(zip(laws.law_id, laws.first_vid, strict=True))
    rows, marks = [], []
    in_order = sorted(matched.items(), key=lambda x: (first_of[x[0][0]], first_of[x[0][1]]))
    for n, ((a, b), s) in enumerate(in_order):
        lk = links[(a, b)]
        va, vb = [v for v, _ in lk], [v for _, v in lk]
        span = {"a": (min(va), max(va)), "b": (min(vb), max(vb))}
        side_words = {k: law_words(*span[k]).head(lc["max_words"]) for k in span}
        ws = {
            k: [make_word(int(i), c, lem, sf) for i, c, lem, sf in
                zip(w.idx, w.content_lemmas, w.lemma, w.surface, strict=True)]
            for k, w in side_words.items()
        }  # fmt: skip
        ops = align_words(ws["a"], ws["b"], dc["match"], dc["mismatch"], dc["gap"])
        count = Counter(o.op for o in ops)
        for o in ops:
            if o.op == "same":
                continue
            for side, i in (("a", o.a), ("b", o.b)):
                if i is None:
                    continue
                d = side_words[side].display_idx.iloc[i]
                if not pd.isna(d):
                    marks.append(
                        (n + 1, side, int(side_words[side].verse_id.iloc[i]), int(d), o.op)
                    )
        kept = sum(count[o] for o in KEPT) / len(ops) if ops else 0.0
        rows.append({
            "pair_id": n + 1, "a": a, "b": b, "code_a": code_of[a], "code_b": code_of[b],
            "links": len(lk), "score": round(float(s), 5),
            "a_first": span["a"][0], "a_last": span["a"][1],
            "b_first": span["b"][0], "b_last": span["b"][1],
            **{o: count[o] for o in OPS}, "kept": round(kept, 3),
        })  # fmt: skip
    cols = ["pair_id", "a", "b", "code_a", "code_b", "links", "score", "a_first", "a_last",
            "b_first", "b_last", *OPS, "kept"]  # fmt: skip
    pairs = pd.DataFrame(rows, columns=cols)

    # the known pairs
    span_of = {int(r.law_id): (r.first_vid, r.last_vid) for r in laws.itertuples()}

    def overlaps(law: int, rng: tuple[int, int]) -> bool:
        return touch(*span_of[law], rng)

    def touch(lo: int, hi: int, rng: tuple[int, int]) -> bool:
        return lo <= rng[1] and hi >= rng[0]

    known, known_of = [], {}
    for group, refs in lc["known"].items():
        ranges = {ref: index.resolve(ref) for ref in refs}
        members = []
        for x, y in combinations(refs, 2):
            hit = [
                int(p.pair_id)
                for p in pairs.itertuples()
                if (overlaps(p.a, ranges[x]) and overlaps(p.b, ranges[y]))
                or (overlaps(p.a, ranges[y]) and overlaps(p.b, ranges[x]))
            ]
            # stricter, reported beside it: the aligned verses themselves touch each passage (a
            # law is a whole paragraph, so Exod 23:8 / Deut 16:19 on bribes joins the festivals)
            strict = any(
                (touch(p.a_first, p.a_last, ranges[x]) and touch(p.b_first, p.b_last, ranges[y]))
                or (touch(p.a_first, p.a_last, ranges[y]) and touch(p.b_first, p.b_last, ranges[x]))
                for p in pairs.itertuples()
            )
            members.append({"a": x, "b": y, "found": bool(hit), "strict": strict, "pairs": hit})
            for h in hit:
                known_of.setdefault(h, group)
        found = sum(m["found"] for m in members)
        known.append({"group": group, "members": members, "found": found, "of": len(members)})
        log(f"known {group}: {found} of {len(members)}")
    pairs["known"] = pairs.pair_id.map(known_of)
    k_found, k_of = sum(k["found"] for k in known), sum(k["of"] for k in known)
    k_strict = sum(m["strict"] for k in known for m in k["members"])

    def profile(g: pd.DataFrame) -> pd.Series:
        return pd.Series({
            "laws": len(g), "verses": int(g.n_verses.sum()),
            **{f: int((g.form == f).sum()) for f in FORMS},
            **{f"v{a}": int((g.address == a).sum()) for a in ADDRESS},
            "mixed": int((g.address == "mixed").sum()),
        })  # fmt: skip

    codes = laws.groupby("code", sort=False).apply(profile, include_groups=False).reset_index()
    order = {c: i for i, c in enumerate(lc["codes"])}
    codes = codes.sort_values("code", key=lambda s: s.map(order)).reset_index(drop=True)

    out.mkdir(parents=True, exist_ok=True)
    laws.to_parquet(out / "laws.parquet", index=False)
    pairs.to_parquet(out / "pairs.parquet", index=False)
    pd.DataFrame(marks, columns=["pair_id", "side", "verse_id", "display_idx", "op"]).to_parquet(
        out / "marks.parquet", index=False
    )
    codes.to_parquet(out / "codes.parquet", index=False)
    meta = {
        "config_hash": config_hash(cfg, "laws", "diffs.match", "diffs.mismatch", "diffs.gap"),
        "built_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "laws": int(len(laws)),
        "pairs": int(len(pairs)),
        "linked": len(links),
        "top_k": lc["top_k"],
        "min_links": lc["min_links"],
        "forms": {f: int((laws.form == f).sum()) for f in FORMS},
        "known": known,
        "known_found": k_found,
        "known_total": k_of,
        "known_holds": k_found >= lc["known_share"] * k_of,
        "known_strict": k_strict,
        "kept_mean": round(float(pairs.kept.mean()), 3) if len(pairs) else None,
        "seconds": round(time.perf_counter() - t0, 1),
    }
    write_meta(out / "laws.meta.json", meta)
    log(f"done: {len(laws)} laws, {len(pairs)} matched pairs, known {k_found} of {k_of}"
        f" ({meta['seconds']} s) -> {out}")  # fmt: skip
    return out / "pairs.parquet"
