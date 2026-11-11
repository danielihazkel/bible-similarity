"""`bsim prophetic`: the forms of prophetic speech (DESIGN.md §16.92, D154; M165).

Form criticism names a handful of forms the prophets speak in. Five of them have words that mark
them, so they can be looked for by rule over the OSHB lemmas and morphology and the BHSA clauses
(§16.26); each form's words are in config (`prophetic`), fixed before the first run.

- **The messenger formula.** כה אמר יהוה (with אדני, צבאות …) and נאם יהוה: God's name within
  `reach` words after כה אמר or נאם. One finding per formula.
- **The woe saying.** הוי as the first word of a clause, followed by a participle, a noun or an
  adjective (הוי מגיעי בית בבית, Isa 5:8); not the cry over the dead (`mourning`: הוי אחי). It runs
  to the next woe or the end of its paragraph, at most `max_verses` verses.
- **Oracles against the nations.** In the Latter Prophets (`books`), a Masoretic paragraph headed
  משא + a nation's name (`heading_reach`), or naming the nations (`peoples`) at least `min_names`
  times and more than Israel (`israel`), in speech (fewer than `narrative_share` of its clauses
  wayyiqtol). Adjacent paragraphs join into one finding.
- **The covenant lawsuit.** A call to hear (שמעו, האזינו as imperatives) with ריב, or with heaven
  and earth, the mountains or the hills, within `window` verses of it in the same book.
- **The call narrative.** God's commission (שלח with a 2ms object, or לך with a 2ms speaking verb
  in the verse) with, within `window` verses, the objection of the one sent (אהה, מי אנכי, בי אדני,
  אוי לי, לא ידעתי) or God's reassurance (אל תירא, אהיה עמך, אתך אני). The speakers are BHSA's:
  the commission and the reassurance not said by a man BHSA names, the objection not by God (BHSA
  leaves the speaker unknown in the prophets' own accounts, Isa 6 and Ezek 2; the first run asked
  for God by name and found 4 calls).

Findings of the lawsuit and the call that overlap in one book join. **Known answers** (`known`):
the passages the commentaries name for four forms; a form that fills its passage (nations, woe) is
found when its findings cover `known_cover` of the verses, one the passage only locates
(`known_overlap`: a call in a whole chapter, a lawsuit's one verse) when a finding overlaps it.

Writes `artifacts/prophetic/`: `items.parquet` (`item_id, form, book_id, unit_id, first_vid,
last_vid, detail` JSON, `known`), `books.parquet` (`book_id, form, n`), `words.parquet`
(`verse_id, idx, form`: the words that mark each finding, for the reader) and
`prophetic.meta.json`.
"""

from __future__ import annotations

import json
import time
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from bsim.analysis.gematria import headwords
from bsim.config import config_hash, resolve_path, write_meta
from bsim.data.canon import BY_OSIS
from bsim.data.refs import RefIndex

Log = Callable[[str], None]

FORMS = ("messenger", "woe", "nations", "lawsuit", "call")
_PREFIXES = {"C", "R", "Td", "Tr"}


def morph_parts(morph: str) -> tuple[str, str]:
    """An OSHB morph code's main part and its pronoun suffix: `HC/Vqw3ms` -> (`Vqw3ms`, ``),
    `HR/Ncmsc/Sp2mp` -> (`Ncmsc`, `Sp2mp`)."""
    if not isinstance(morph, str) or len(morph) < 2:
        return "", ""
    segs = morph[1:].split("/")
    suffix = next((s for s in segs if s.startswith("S")), "")
    rest = [s for s in segs if not s.startswith("S")]
    main = next((s for s in reversed(rest) if s not in _PREFIXES), rest[-1] if rest else "")
    return main, suffix


def word_table(words: pd.DataFrame) -> pd.DataFrame:
    """One row per OSHB word in text order: its lemma (the last content lemma, else empty), the
    main part of its morph and its suffix."""
    w = words.sort_values(["verse_id", "idx"]).reset_index(drop=True)
    w["lemma"] = [c[-1] if len(c) else "" for c in w.content_lemmas]
    parts = [morph_parts(m) for m in w.morph]
    w["main"] = [p[0] for p in parts]
    w["suffix"] = [p[1] for p in parts]
    return w[["verse_id", "idx", "lemma", "main", "suffix"]]


def is_kind(main: str, kind: str) -> bool:
    """`V-participle`, `V-imperative`, or a part of speech's first letter (`N`, `A`)."""
    if kind == "V-participle":
        return main[:1] == "V" and main[2:3] in ("r", "s")
    if kind == "V-imperative":
        return main[:1] == "V" and main[2:3] == "v"
    return main[:1] == kind


def is_2ms(main: str, suffix: str = "") -> bool:
    return (main[:1] == "V" and main.endswith("2ms")) or suffix.endswith("2ms")


def cover(lo: int, hi: int, spans: list[tuple[int, int]]) -> float:
    """The share of the verses lo..hi inside any of the spans."""
    inside = np.zeros(hi - lo + 1, bool)
    for a, b in spans:
        a, b = max(a, lo), min(b, hi)
        if a <= b:
            inside[a - lo : b - lo + 1] = True
    return float(inside.mean())


def merge(
    spans: list[tuple[int, int, dict]], book_of: dict[int, int]
) -> list[tuple[int, int, dict]]:
    """Spans that overlap or touch in one book joined; their details' flags or-ed, words joined."""
    out: list[tuple[int, int, dict]] = []
    for a, b, d in sorted(spans, key=lambda s: (s[0], s[1])):
        words = {tuple(x) for x in d["words"]}
        if out and book_of[a] == book_of[out[-1][0]] and a <= out[-1][1] + 1:
            pa, pb, prev = out[-1]
            flags = {k: bool(prev.get(k)) or v for k, v in d.items() if isinstance(v, bool)}
            out[-1] = (pa, max(pb, b), {**prev, **flags, "words": sorted({*prev["words"], *words})})
        else:
            out.append((a, b, {**d, "words": sorted(words)}))
    return out


class Text:
    """The words by verse, for the rules."""

    def __init__(self, w: pd.DataFrame, book_of: dict[int, int]) -> None:
        self.w = w
        self.book_of = book_of
        self.by_verse: dict[int, pd.DataFrame] = dict(iter(w.groupby("verse_id", sort=False)))
        self.lemmas = {v: set(g.lemma) for v, g in self.by_verse.items()}

    def verses_with(self, lemmas: list[str]) -> dict[int, list[tuple[int, int]]]:
        """verse_id -> the words of the group, for the verses holding every lemma of it."""
        need = set(lemmas)
        out = {}
        for v, have in self.lemmas.items():
            if need <= have:
                g = self.by_verse[v]
                out[v] = [(v, int(i)) for i in g.idx[g.lemma.isin(need)]]
        return out

    def near(self, v: int, others: dict[int, Any], window: int) -> list[int]:
        """The verses of `others` within `window` verses of v in its book."""
        b = self.book_of[v]
        return [
            u for u in range(v - window, v + window + 1) if u in others and self.book_of.get(u) == b
        ]


def find_messenger(t: Text, mc: dict[str, Any], god: set[str]) -> list[tuple[int, int, dict]]:
    w, out = t.w, []
    lem, vid, idx = w.lemma.to_numpy(), w.verse_id.to_numpy(), w.idx.to_numpy()
    thus, oracle, reach = mc["thus"], mc["oracle"], mc["reach"]
    for i in range(len(w) - 1):
        if lem[i] == thus[0] and lem[i + 1] == thus[1] and vid[i + 1] == vid[i]:
            kind, last = "thus", i + 1
        elif lem[i] == oracle:
            kind, last = "oracle", i
        else:
            continue
        for j in range(last + 1, min(last + 1 + reach, len(w))):
            if vid[j] != vid[i]:
                break
            if lem[j] in god:
                words = [(int(vid[k]), int(idx[k])) for k in range(i, j + 1)]
                out.append((int(vid[i]), int(vid[i]), {"kind": kind, "words": words}))
                break
    return out


def find_woe(t: Text, mc: dict[str, Any], opens: set[tuple[int, int]],
             para_end: dict[int, int]) -> list[tuple[int, int, dict]]:  # fmt: skip
    w, hits = t.w, []
    lem, vid, idx, main = (
        w.lemma.to_numpy(),
        w.verse_id.to_numpy(),
        w.idx.to_numpy(),
        w.main.to_numpy(),
    )
    for i in np.flatnonzero(lem[:-1] == mc["word"]):
        v = int(vid[i])
        if (v, int(idx[i])) not in opens or vid[i + 1] != v or lem[i + 1] in mc["mourning"]:
            continue
        if not any(is_kind(main[i + 1], k) for k in mc["next"]):
            continue
        hits.append((v, [(v, int(idx[i])), (v, int(idx[i + 1]))], str(lem[i + 1])))
    out = []
    for n, (v, words, nxt) in enumerate(hits):
        end = min(para_end.get(v, v), v + mc["max_verses"] - 1)
        if n + 1 < len(hits) and hits[n + 1][0] > v and t.book_of[hits[n + 1][0]] == t.book_of[v]:
            end = min(end, hits[n + 1][0] - 1)
        if out and out[-1][0] == v:  # a second הוי in the verse: one saying
            out[-1][2]["words"] += words
            continue
        out.append((v, max(v, end), {"next": nxt, "words": words}))
    return out


def find_nations(t: Text, mc: dict[str, Any], peri: pd.DataFrame,
                 clauses: pd.DataFrame) -> list[tuple[int, int, dict]]:  # fmt: skip
    books = {BY_OSIS[o].book_id for o in mc["books"]}
    peoples, israel = set(mc["peoples"]), set(mc["israel"])
    narr = clauses.assign(way=clauses.typ.isin(mc["narrative_types"])).groupby("verse_id").way
    way_n, all_n = narr.sum(), narr.size()
    spans = []
    for p in peri[peri.book_id.isin(books)].itertuples():
        vs = [v for v in range(p.start_verse_id, p.end_verse_id + 1) if v in t.by_verse]
        if not vs:
            continue
        g = pd.concat([t.by_verse[v] for v in vs])
        named = g[g.lemma.isin(peoples)]
        n_israel = int(g.lemma.isin(israel).sum())
        heading = []
        for v in vs:
            h = t.by_verse[v].reset_index(drop=True)
            for i in np.flatnonzero(h.lemma.to_numpy() == mc["heading"]):
                after = h.iloc[i + 1 : i + 1 + mc["heading_reach"]]
                if after.lemma.isin(peoples).any():
                    heading.append((v, int(h.idx[i])))
        clauses_n = int(sum(all_n.get(v, 0) for v in vs))
        way = int(sum(way_n.get(v, 0) for v in vs))
        speech = not clauses_n or way / clauses_n < mc["narrative_share"]
        if heading or (speech and len(named) >= mc["min_names"] and len(named) > n_israel):
            counts = named.lemma.value_counts()
            words = heading + [(int(r.verse_id), int(r.idx)) for r in named.itertuples()]
            spans.append((int(p.start_verse_id), int(p.end_verse_id),
                          {"names": {str(k): int(n) for k, n in counts.items()},
                           "heading": bool(heading), "paragraphs": 1, "words": words}))  # fmt: skip
    out: list[tuple[int, int, dict]] = []
    for a, b, d in spans:  # adjacent paragraphs: one finding
        if out and t.book_of[a] == t.book_of[out[-1][0]] and a <= out[-1][1] + 1:
            pa, _, pd_ = out[-1]
            names = dict(pd_["names"])
            for k, n in d["names"].items():
                names[k] = names.get(k, 0) + n
            out[-1] = (pa, b, {"names": dict(sorted(names.items(), key=lambda x: -x[1])),
                               "heading": pd_["heading"] or d["heading"],
                               "paragraphs": pd_["paragraphs"] + 1,
                               "words": pd_["words"] + d["words"]})  # fmt: skip
        else:
            out.append((a, b, d))
    return out


def find_lawsuit(t: Text, mc: dict[str, Any]) -> list[tuple[int, int, dict]]:
    w = t.w
    call = w[w.lemma.isin(mc["hear"]) & w.main.map(lambda m: is_kind(m, "V-imperative"))]
    calls: dict[int, list[tuple[int, int]]] = {}
    for r in call.itertuples():
        calls.setdefault(int(r.verse_id), []).append((int(r.verse_id), int(r.idx)))
    dispute: dict[int, list[tuple[int, int]]] = {}
    for r in w[w.lemma.isin(mc["dispute"])].itertuples():
        dispute.setdefault(int(r.verse_id), []).append((int(r.verse_id), int(r.idx)))
    witness: dict[int, list[tuple[int, int]]] = {}
    for group in mc["witnesses"]:
        for v, ws in t.verses_with(group).items():
            witness.setdefault(v, []).extend(ws)
    out = []
    for v, ws in calls.items():
        d, wi = t.near(v, dispute, mc["window"]), t.near(v, witness, mc["window"])
        if not d and not wi:
            continue
        found = [v, *d, *wi]
        words = ws + [x for u in d for x in dispute[u]] + [x for u in wi for x in witness[u]]
        out.append(
            (min(found), max(found), {"dispute": bool(d), "witnesses": bool(wi), "words": words})
        )
    return merge(out, t.book_of)


def find_call(t: Text, mc: dict[str, Any], god: set[str],
              speaker: dict[tuple[int, int], str]) -> list[tuple[int, int, dict]]:  # fmt: skip
    def by_god(v: int, i: int) -> bool:
        return speaker.get((v, i)) in god

    def by_man(v: int, i: int) -> bool:  # a speaker BHSA names who is not God
        return speaker.get((v, i)) not in (None, *god)

    commission: dict[int, list[tuple[int, int]]] = {}
    for v, g in t.by_verse.items():
        g = g.reset_index(drop=True)
        lem, main, suf, idx = (
            g.lemma.to_numpy(),
            g.main.to_numpy(),
            g.suffix.to_numpy(),
            g.idx.to_numpy(),
        )
        for i in range(len(g)):
            hit = None
            if lem[i] == mc["send"] and main[i][:1] == "V":
                if suf[i].endswith("2ms"):
                    hit = [i]
                else:
                    obj = [j for j in range(i + 1, min(i + 1 + mc["send_reach"], len(g)))
                           if lem[j] in ("853", "854") and suf[j].endswith("2ms")]  # fmt: skip
                    hit = [i, obj[0]] if obj else None
            elif lem[i] in mc["go"] and is_kind(main[i], "V-imperative"):
                say = [j for j in range(i + 1, len(g)) if lem[j] in mc["say"] and is_2ms(main[j])]
                hit = [i, say[0]] if say else None
            if hit and not by_man(v, int(idx[i])):
                commission.setdefault(v, []).extend((v, int(idx[j])) for j in hit)

    def groups(
        specs: list[list[str]], ok: Callable[[int, int], bool]
    ) -> dict[int, list[tuple[int, int]]]:
        out: dict[int, list[tuple[int, int]]] = {}
        for spec in specs:
            for v, ws in t.verses_with(spec).items():
                if ok(*ws[0]):
                    out.setdefault(v, []).extend(ws)
        return out

    objection = groups(mc["objection"], lambda v, i: not by_god(v, i))
    reassurance = groups(mc["reassurance"], lambda v, i: not by_man(v, i))
    out = []
    for v, ws in commission.items():
        o, r = t.near(v, objection, mc["window"]), t.near(v, reassurance, mc["window"])
        if not o and not r:
            continue
        found = [v, *o, *r]
        words = ws + [x for u in o for x in objection[u]] + [x for u in r for x in reassurance[u]]
        out.append(
            (min(found), max(found), {"objection": bool(o), "reassurance": bool(r), "words": words})
        )
    return merge(out, t.book_of)


def run_prophetic(cfg: dict[str, Any], log: Log = print) -> Path:
    pc = cfg["prophetic"]
    proc, art = resolve_path(cfg, "data_processed"), resolve_path(cfg, "artifacts")
    out = art / "prophetic"
    t0 = time.perf_counter()
    path = proc / "syntax_clauses.parquet"
    if not path.exists():
        raise RuntimeError(f"{path} missing; run `bsim syntax` first")
    clauses = pd.read_parquet(path, columns=["clause", "verse_id", "words", "typ", "speaker"])
    verses = pd.read_parquet(
        proc / "verses.parquet", columns=["verse_id", "book_id", "chapter", "verse"]
    )
    units = pd.read_parquet(proc / "units.parquet")
    words = pd.read_parquet(
        proc / "words.parquet", columns=["verse_id", "idx", "content_lemmas", "morph"]
    )
    peri = units[units.unit_type == "pericope"].sort_values("start_verse_id").reset_index(drop=True)
    book_of = dict(zip(verses.verse_id.astype(int), verses.book_id.astype(int), strict=True))
    god = set(pc["god"])

    t = Text(word_table(words), book_of)
    opens = {
        (int(v), int(ws[0]))
        for v, ws in zip(clauses.verse_id, clauses.words, strict=True)
        if len(ws)
    }
    speaker = {}
    for v, ws, s in zip(clauses.verse_id, clauses.words, clauses.speaker, strict=True):
        if isinstance(s, str):
            for i in ws:
                speaker[(int(v), int(i))] = s
    starts = peri.start_verse_id.to_numpy()
    para_end = {}
    for v in book_of:
        k = np.searchsorted(starts, v, side="right") - 1
        if k >= 0 and peri.end_verse_id.iloc[k] >= v:
            para_end[v] = int(peri.end_verse_id.iloc[k])

    found = {
        "messenger": find_messenger(t, pc["messenger"], god),
        "woe": find_woe(t, pc["woe"], opens, para_end),
        "nations": find_nations(t, pc["nations"], peri, clauses),
        "lawsuit": find_lawsuit(t, pc["lawsuit"]),
        "call": find_call(t, pc["call"], god, speaker),
    }
    head = headwords(resolve_path(cfg, "data_raw"))
    for _, _, d in found["nations"]:  # each name with its Strong's headword (pointed)
        d["names"] = [{"lemma": k, "he": head.get(k) or head.get(k.rstrip("abcdefgh"), ""), "n": n}
                      for k, n in d["names"].items()]  # fmt: skip
    rows, marks = [], {}
    for form in FORMS:
        log(f"{form}: {len(found[form])}")
        for a, b, d in found[form]:
            for v, i in d.pop("words"):
                marks.setdefault((int(v), int(i)), form)
            k = np.searchsorted(starts, a, side="right") - 1
            unit = str(peri.unit_id.iloc[k]) if k >= 0 else f"c:{book_of[a]}"
            rows.append((form, book_of[a], unit, int(a), int(b), json.dumps(d, ensure_ascii=False)))
    items = pd.DataFrame(
        rows, columns=["form", "book_id", "unit_id", "first_vid", "last_vid", "detail"]
    )
    items.insert(0, "item_id", np.arange(1, len(items) + 1))

    # known answers
    index = RefIndex(pd.read_parquet(proc / "verses.parquet"))
    known, known_ids = {}, set()
    for form, refs in pc["known"].items():
        f = items[items.form == form]
        spans = list(zip(f.first_vid, f.last_vid, strict=True))
        rows_k = []
        for ref in refs:
            lo, hi = index.resolve(ref)
            hit = f[(f.first_vid <= hi) & (f.last_vid >= lo)]
            share = cover(lo, hi, spans)
            ok = not hit.empty if form in pc["known_overlap"] else share >= pc["known_cover"]
            first = int(hit.item_id.iloc[0]) if not hit.empty else None
            rows_k.append({"ref": ref, "found": bool(ok), "cover": round(share, 3), "item": first})
            if ok:
                known_ids |= set(hit.item_id)
        n = sum(k["found"] for k in rows_k)
        known[form] = {"refs": rows_k, "found": n, "holds": n >= pc["known_share"] * len(rows_k)}
        log(f"known {form}: {n} of {len(rows_k)}")
    items["known"] = items.item_id.isin(known_ids)

    books = items.groupby(["book_id", "form"]).size().rename("n").reset_index()
    reader = pd.DataFrame(
        [(v, i, f) for (v, i), f in sorted(marks.items())], columns=["verse_id", "idx", "form"]
    )

    out.mkdir(parents=True, exist_ok=True)
    items.to_parquet(out / "items.parquet", index=False)
    books.to_parquet(out / "books.parquet", index=False)
    reader.to_parquet(out / "words.parquet", index=False)
    counts = {f: int((items.form == f).sum()) for f in FORMS}
    meta = {
        "config_hash": config_hash(cfg, "prophetic"),
        "built_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "counts": counts,
        "items": int(len(items)),
        "known": known,
        "known_found": sum(k["found"] for k in known.values()),
        "known_total": sum(len(k["refs"]) for k in known.values()),
        "known_holds": all(k["holds"] for k in known.values()),
        "known_cover": pc["known_cover"],
        "known_overlap": list(pc["known_overlap"]),
        "seconds": round(time.perf_counter() - t0, 1),
    }
    write_meta(out / "prophetic.meta.json", meta)
    log(f"done: {len(items)} findings ({meta['seconds']} s) -> {out}")
    return out / "items.parquet"
