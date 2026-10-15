"""`bsim masorah`: the Masorah's counts, computed on our text (DESIGN.md §16.55).

The scribes "counted all the letters of the Torah" (Kiddushin 30a): the ו of גחון (Lev 11:42) is
its middle letter, דרש דרש (Lev 10:16) its middle words, Lev 13:33 its middle verse; the
Masorah's summaries give Lev 8:8 as the middle verse, the middle verse of each book and the verse
total of each book. Counting the same things on our text checks its letters and its
versification against the tradition: how far each middle lands from ours, and why a total
differs.

- **Two texts**, both from the MAM display tokens (consonants, final forms kept; a paseq is no
  word, a maqaf separates words): `ketiv`, what is written, and `qere`, what is read. MAM shows
  the qere, but keeps the written letters of many words (`mam-kq-trivial`, the perpetual הוא),
  so at every ketiv / qere of `bsim ketiv` (OSHB) each text gets its side wherever MAM shows
  the other; a word written but not read goes after the word before it.
- **Middles** (`masorah.middles`): a span (a book, or a section of the canon) counted in letters,
  words or verses; its middle is at (n − 1) / 2 from 0, between two units when n is even. The
  tradition's is the letter, the word(s) (between two words: halfway) or the verse it names. The
  distance is theirs minus ours, in units and in verses; it *lands* within `tolerance` units.
- **Totals**: our verses for each book of the Masorah (`masorah.books`: Samuel, Kings, the Twelve,
  Ezra–Nehemiah and Chronicles are one book each), the sections and the whole
  (`masorah.sections`, in verses, words or letters), against the figures given; a book that
  differs carries the reason given in the config (a code the viewer explains).

Writes `artifacts/masorah/`: `middles.parquet` (per claim and text: the tradition's place, ours,
the distance), `totals.parquet` (each total against ours), `books.parquet` (per book: verses, and
words and letters in each text) and `masorah.meta.json`.
"""

from __future__ import annotations

import json
import time
from collections import defaultdict
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from bsim.config import config_hash, resolve_path
from bsim.data.canon import BOOKS, BY_SEFARIA
from bsim.data.refs import RefIndex
from bsim.text.normalize import consonantal, fold_finals

Log = Callable[[str], None]

TEXTS = ("ketiv", "qere")
UNITS = ("letter", "word", "verse")
SECTIONS = {
    s: [b.book_id for b in BOOKS if b.section == s] for s in ("Torah", "Prophets", "Writings")
}


def book_span(names: list[str] | str) -> tuple[int, int]:
    """First and last book_id of a section (Torah, Prophets, Writings), a book or [first, last]."""
    if isinstance(names, str):
        if names in SECTIONS:
            return SECTIONS[names][0], SECTIONS[names][-1]
        names = [names]
    try:
        ids = [BY_SEFARIA[n].book_id for n in names]
    except KeyError as e:
        raise ValueError(f"masorah: unknown book {e.args[0]!r}") from None
    if ids[0] > ids[-1]:
        raise ValueError(f"masorah: books {names} out of order")
    return ids[0], ids[-1]


def _key(words: list[str]) -> str:
    return fold_finals("".join(words))


def texts(
    verses: pd.DataFrame, words: pd.DataFrame, pairs: pd.DataFrame
) -> tuple[dict[str, pd.DataFrame], dict[str, Any]]:
    """The written and the read text, word by word: `verse_id, tok` (the display token it stands
    for; -1 for a written word MAM does not show) and `word` (its consonants, finals kept)."""
    disp = {
        (int(v), int(i)): int(d)
        for v, i, d in zip(words.verse_id, words.idx, words.display_idx, strict=True)
        if pd.notna(d)
    }
    tokens = dict(zip(verses.verse_id, verses.display_tokens, strict=True))
    # text -> verse -> {token: words standing in for it}, {token: words after it (-1: first)}
    replace: dict[str, dict[int, dict[int, list[str]]]] = {t: defaultdict(dict) for t in TEXTS}
    after: dict[str, dict[int, dict[int, list[str]]]] = {t: defaultdict(dict) for t in TEXTS}
    changed = dict.fromkeys(TEXTS, 0)
    unaligned = 0
    for r in pairs.itertuples(index=False):
        vid = int(r.verse_id)
        side = {
            "ketiv": consonantal(r.ketiv or "").split(),
            "qere": consonantal(r.qere or "").split(),
        }
        if r.n_qere:
            toks = sorted({disp[k] for i in range(r.n_qere) if (k := (vid, r.pos + i)) in disp})
            if not toks:
                unaligned += 1
                continue
            shown = _key([consonantal(tokens[vid][t]).replace(" ", "") for t in toks])
            for t in TEXTS:
                if shown != _key(side[t]):
                    replace[t][vid] |= {toks[0]: side[t]} | {k: [] for k in toks[1:]}
                    changed[t] += 1
        elif side["ketiv"]:  # written, not read
            if (vid, r.pos - 1) in disp:
                anchor = disp[(vid, r.pos - 1)]
            elif (vid, r.pos) in disp:
                anchor = disp[(vid, r.pos)] - 1
            else:
                unaligned += 1
                continue
            after["ketiv"][vid].setdefault(anchor, []).extend(side["ketiv"])
            changed["ketiv"] += 1
    out = {}
    for t in TEXTS:
        rows: list[tuple[int, int, str]] = []
        for vid in verses.verse_id:
            vid = int(vid)
            rep, aft = replace[t].get(vid, {}), after[t].get(vid, {})
            rows += [(vid, -1, w) for w in aft.get(-1, [])]
            for i, tok in enumerate(tokens[vid]):
                ws = rep[i] if i in rep else consonantal(tok).split()
                rows += [(vid, i, w) for w in ws]
                rows += [(vid, -1, w) for w in aft.get(i, [])]
        out[t] = pd.DataFrame(rows, columns=["verse_id", "tok", "word"])
    return out, {"pairs": len(pairs), "changed": changed, "unaligned": unaligned}


def _find(text: pd.DataFrame, vid: int, word: str) -> tuple[int, int]:
    """Row positions of the first run of words in verse `vid` that reads `word` (finals folded)."""
    want = [fold_finals(w) for w in consonantal(word).split()]
    rows = np.flatnonzero(text.verse_id.to_numpy() == vid)
    got = [fold_finals(w) for w in text.word.to_numpy()[rows]]
    for i in range(len(got) - len(want) + 1):
        if got[i : i + len(want)] == want:
            return int(rows[i]), int(rows[i + len(want) - 1])
    raise ValueError(f"masorah: {word!r} is not in verse {vid}")


def middle(
    claim: dict[str, Any], vid: int, span: tuple[int, int], verses: pd.DataFrame,
    text: pd.DataFrame | None,
) -> dict[str, Any]:  # fmt: skip
    """Where the tradition's middle of a span is against ours (`text` is None for verses)."""
    unit = claim["unit"]
    first, last = span
    vids = verses.verse_id[(verses.book_id >= first) & (verses.book_id <= last)].to_numpy()
    if not len(vids) or not vids[0] <= vid <= vids[-1]:
        raise ValueError(f"masorah: {claim['ref']} is not in {claim['span']}")
    out: dict[str, Any] = {"trad_vid": vid, "trad_tok": None, "trad_word": None,
                           "trad_letter": None, "mid_tok": None, "mid_word": None,
                           "mid_letter": None}  # fmt: skip
    if unit == "verse":
        n = len(vids)
        trad = float(np.searchsorted(vids, vid))
        mid_vid = int(vids[(n - 1) // 2])
    else:
        assert text is not None
        lo, hi = np.searchsorted(text.verse_id.to_numpy(), [vids[0], vids[-1] + 1])
        a, b = _find(text, vid, claim["word"])
        found = text.word.iloc[a : b + 1].tolist()
        out |= {"trad_tok": int(text.tok.iloc[a]), "trad_word": " ".join(found)}
        if unit == "word":
            n = int(hi - lo)
            trad = (a + b) / 2 - lo
            m = lo + (n - 1) // 2
        else:
            lens = text.word.str.len().to_numpy()[lo:hi]
            ends = np.cumsum(lens)
            n = int(ends[-1])
            k = int(claim["letter"])
            if not 1 <= k <= len(found[0]):
                raise ValueError(f"masorah: {claim['word']!r} has no letter {k}")
            trad = float(ends[a - lo] - lens[a - lo] + k - 1)
            out["trad_letter"] = k
            at = (n - 1) // 2
            w = int(np.searchsorted(ends, at, side="right"))
            m = lo + w
            out["mid_letter"] = int(at - (ends[w] - lens[w])) + 1
        mid_vid = int(text.verse_id.iloc[m])
        out |= {"mid_tok": int(text.tok.iloc[m]), "mid_word": str(text.word.iloc[m])}
    mid = (n - 1) / 2
    return out | {"n": n, "trad_pos": trad, "mid_pos": mid, "distance": trad - mid,
                  "mid_vid": mid_vid, "verses_apart": int(vid - mid_vid)}  # fmt: skip


def run_masorah(cfg: dict[str, Any], log: Log = print) -> Path:
    mc = cfg["masorah"]
    proc, art = resolve_path(cfg, "data_processed"), resolve_path(cfg, "artifacts")
    out = art / "masorah"
    t0 = time.perf_counter()
    tol = float(mc["tolerance"])
    if mc["text"] not in TEXTS:
        raise ValueError(f"masorah.text must be one of {TEXTS}")
    pairs_path = art / "ketiv" / "pairs.parquet"
    if not pairs_path.exists():
        raise FileNotFoundError(f"{pairs_path} is missing: run `bsim ketiv` first")

    verses = pd.read_parquet(
        proc / "verses.parquet",
        columns=["verse_id", "book_id", "chapter", "verse", "display_tokens"],
    ).sort_values("verse_id", ignore_index=True)
    words = pd.read_parquet(proc / "words.parquet", columns=["verse_id", "idx", "display_idx"])
    pairs = pd.read_parquet(
        pairs_path, columns=["verse_id", "pos", "n_ketiv", "n_qere", "ketiv", "qere"]
    ).sort_values(["verse_id", "pos"], kind="stable")
    index = RefIndex(verses)
    text, applied = texts(verses, words, pairs)

    # the middles, every claim in each text (verses: once)
    mid_rows = []
    for i, c in enumerate(mc["middles"]):
        if c["unit"] not in UNITS:
            raise ValueError(f"masorah.middles: unit {c['unit']!r} is not one of {UNITS}")
        span = book_span(c["span"])
        vid = index.resolve(c["ref"])[0]
        for t in [None] if c["unit"] == "verse" else TEXTS:
            m = middle(c, vid, span, verses, None if t is None else text[t])
            mid_rows.append({"claim": i, "span": c["span"], "unit": c["unit"], "text": t,
                             "source": c["source"], "ref": c["ref"],
                             "holds": abs(m["distance"]) <= tol} | m)  # fmt: skip
    middles = pd.DataFrame(mid_rows)
    for col in ("text", "trad_word", "mid_word"):
        middles[col] = middles[col].astype(object)
    for col in ("trad_tok", "trad_letter", "mid_tok", "mid_letter"):
        middles[col] = middles[col].astype("Int64")

    # per book: verses, and words and letters in each text
    books = verses.groupby("book_id").size().rename("verses").to_frame()
    for t in TEXTS:
        w = text[t].assign(book_id=text[t].verse_id.map(verses.set_index("verse_id").book_id))
        g = w.groupby("book_id")
        books[f"words_{t}"] = g.size()
        books[f"letters_{t}"] = g.word.apply(lambda s: int(s.str.len().sum()))
    books = books.reset_index().astype(int)

    def ours(first: int, last: int, unit: str, t: str | None) -> int:
        b = books[(books.book_id >= first) & (books.book_id <= last)]
        col = "verses" if unit == "verses" else f"{unit}_{t}"
        return int(b[col].sum())

    total_rows = []
    for c in mc["books"]:
        first, last = book_span(c["books"])
        span = index.resolve(c["ref"]) if c.get("ref") else (None, None)
        got = ours(first, last, "verses", None)
        total_rows.append({"scope": "book", "name": c.get("name"), "first_book": first,
                           "last_book": last, "unit": "verses", "text": None,
                           "source": "masorah", "tradition": int(c["verses"]), "ours": got,
                           "reason": c.get("reason"), "ref": c.get("ref"),
                           "ref_first": span[0], "ref_last": span[1],
                           "also": json.dumps([int(x) for x in c.get("also", [])])})  # fmt: skip
        if got != int(c["verses"]) and not c.get("reason"):
            log(f"  note: {c['books']} has {got} verses against {c['verses']}, no reason given")
    covered = {}  # first book -> (the Masorah's total, its books)
    for c in mc["books"]:
        span = book_span(c["books"])
        covered[span[0]] = (int(c["verses"]), span)
    for c in mc["sections"]:
        first, last = book_span(c["books"])
        unit = c["unit"]
        if unit not in ("verses", "words", "letters"):
            raise ValueError(f"masorah.sections: unit {unit!r}")
        # verses: the sum of the Masorah's book totals there, when its books tile the span
        book_sum = None
        if unit == "verses":
            b, s = first, 0
            while b <= last and b in covered and covered[b][1][1] <= last:
                s += covered[b][0]
                b = covered[b][1][1] + 1
            book_sum = s if b == last + 1 else None
        for t in [None] if unit == "verses" else TEXTS:
            total_rows.append({"scope": "section", "name": c["name"], "first_book": first,
                               "last_book": last, "unit": unit, "text": t,
                               "source": c["source"], "tradition": int(c["value"]),
                               "ours": ours(first, last, unit, t), "reason": None, "ref": None,
                               "ref_first": None, "ref_last": None, "also": "[]",
                               "book_sum": book_sum})  # fmt: skip
    totals = pd.DataFrame(total_rows)
    totals["diff"] = totals.ours - totals.tradition
    for col in ("name", "text", "reason", "ref"):
        totals[col] = totals[col].astype(object)
    for col in ("ref_first", "ref_last", "book_sum"):
        totals[col] = totals[col].astype("Int64")
    totals = totals[
        ["scope", "name", "first_book", "last_book", "unit", "text", "source", "tradition",
         "ours", "diff", "book_sum", "reason", "ref", "ref_first", "ref_last", "also"]
    ]  # fmt: skip

    # the findings: the first Torah claim of each unit, in `masorah.text`
    checks: dict[str, Any] = {}
    for unit in UNITS:
        sel = middles[(middles.span == "Torah") & (middles.unit == unit)]
        if unit != "verse":
            sel = sel[sel.text == mc["text"]]
        if len(sel):
            r = sel.iloc[0]
            checks[unit] = {
                "ref": r.ref, "n": int(r.n), "distance": float(r.distance),
                "verses_apart": int(r.verses_apart), "holds": bool(r.holds),
            }  # fmt: skip
    bk = totals[totals.scope == "book"]
    checks["books"] = {"n": len(bk), "agree": int((bk["diff"] == 0).sum()),
                       "max_diff": int(bk["diff"].abs().max()) if len(bk) else 0,
                       "reasoned": int(((bk["diff"] != 0) & bk.reason.notna()).sum())}  # fmt: skip
    torah = SECTIONS["Torah"]
    tb = books[books.book_id.isin(torah)]

    out.mkdir(parents=True, exist_ok=True)
    middles.to_parquet(out / "middles.parquet")
    totals.to_parquet(out / "totals.parquet")
    books.to_parquet(out / "books.parquet")
    meta = {
        "config_hash": config_hash(cfg, "masorah"),
        "built_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "tolerance": tol,
        "text": mc["text"],
        "kq": applied,
        "torah": {"verses": int(tb.verses.sum())}
        | {f"{u}_{t}": int(tb[f"{u}_{t}"].sum()) for u in ("words", "letters") for t in TEXTS},
        "bible": {"verses": int(books.verses.sum())}
        | {f"{u}_{t}": int(books[f"{u}_{t}"].sum()) for u in ("words", "letters") for t in TEXTS},
        "checks": checks,
        "seconds": round(time.perf_counter() - t0, 1),
    }
    (out / "masorah.meta.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False), "utf-8")
    c = checks
    log(
        f"done: Torah {meta['torah']['verses']:,} verses, {meta['torah']['words_ketiv']:,} words"
        f" and {meta['torah']['letters_ketiv']:,} letters written ({applied['changed']['ketiv']}"
        f" ketiv / {applied['changed']['qere']} qere words changed, {applied['unaligned']}"
        f" unaligned); middle letter {c['letter']['distance']:+,.1f}, words"
        f" {c['word']['distance']:+,.1f}, verse {c['verse']['distance']:+.1f}; books"
        f" {c['books']['agree']}/{c['books']['n']} agree ({meta['seconds']} s) -> {out}"
    )
    return out
