"""`bsim witnesses`: the Samaritan Pentateuch and the Dead Sea Scrolls against the MT, word by
word (DESIGN.md §16.78).

Two other witnesses to the text, both Text-Fabric datasets under CC BY-NC 4.0 (like the BHSA):
the Samaritan Pentateuch of the Halle Samaritanus project (DT-UCPH / CACCHT: MS Dublin Chester
Beatty 751 and MS Garizim 1, `sources.samaritan`), and the biblical scrolls from Martin Abegg's
data (ETCBC, `sources.scrolls`). Both follow the WLC's verse numbers, so a verse is found by
`verses.oshb_osis` (several WLC verses may make one verse_id).

- **Words.** Both datasets split prefixes off as words of their own; a graphic word is rebuilt by
  joining a word to the next when nothing follows it (`trailer`, `after`). A word is its letters,
  finals folded. A scroll's word is *read* when none of its letters was reconstructed by an editor
  (`rec`) and none is less certain than `max_unc` (`unc`, 1-4); the reconstructed words stay in
  the alignment as anchors (editors restore them from the MT) but are never evidence.
- **Alignment.** Each witness verse is aligned to the MT verse (OSHB words, the qere read where
  there is one) by Needleman-Wunsch over word skeletons (`diffs.align_words`): a word's key is
  its letters without the ו / י inside it (the first and last letter kept). The positions get
  `diffs.OPS` labels: `same`, `spelling` (same skeleton, other vowel letters), `form` (one
  skeleton is the other with one prefix letter more, ובכלמהש, or one ending letter, ההוימנכת),
  `substitution`, `omitted` (in the
  MT only), `added` (in the witness only), `moved`. A scroll's position counts only when its
  word is read; an omission when the witness words either side of it are read.
- **Pluses.** A run of `added` positions with `plus_min` or more read words is a plus: text the
  witness has and the MT lacks. A reconstructed word inside the run does not break it (the first
  run broke runs there, and missed 4QSam-a's Nahash paragraph: both runs reported).
- **Claim** (fixed before the first run): the Samaritan Pentateuch's pluses fall in verses that
  have a parallel elsewhere in the Torah (a strong parallel sequence of `bsim sequences`, as
  `diffs` reads them: `q <= diffs.max_q`, not inside one chapter, both sides in the Torah) more
  than in the others, the harmonising of Exod 20 with Deut 5 and of Numbers with Deut 1-3. The
  statistic is the rate of plus verses among the parallel verses over the rate among the rest;
  the null shifts the parallel label circularly round each book (`shifts`), so its blocks stay
  blocks. Holds when the ratio is above 1 and p <= `alpha`.
- **Known answers** (`known`): readings a witness is known to have (a plus of at least so many
  words, or a word it reads where the MT has another), each a check of the reading and the
  alignment; and the Samaritan Flood in year 1307 of its own chronology (`chronology_known`).
- **Two chronologies.** The Samaritan ages of Gen 5 and 11 are read by `chronology.phrases` from
  its words (`sp_lex`: the lexemes of number words and their Strong's keys), each event of
  `chronology.events` whose verse is in the Torah computed again from them, beside the MT's
  (`artifacts/chronology/events.parquet`).

Writes `artifacts/witnesses/`: `verses.parquet` (witness, verse_id, the witness's words as JSON
`[{t, r, op, mt}]`: letters, read, the position's op, the MT word's display token; the counts),
`changes.parquet` (one row per non-`same` position that counts), `books.parquet`,
`scrolls.parquet`, `chronology.parquet` and `witnesses.meta.json`.
"""

from __future__ import annotations

import json
import re
import time
import unicodedata
from bisect import bisect_right
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from bsim.analysis.chronology import Word as NumWord
from bsim.analysis.chronology import phrases
from bsim.analysis.diffs import OPS, Word, align_words
from bsim.analysis.stats import empirical_p
from bsim.config import config_hash, resolve_path, write_meta
from bsim.data.bhsa import read_otype, read_tf
from bsim.data.canon import BOOKS
from bsim.data.refs import RefIndex
from bsim.text.normalize import match_key

Log = Callable[[str], None]

SP = "sp"  # the Samaritan Pentateuch's witness name; a scroll's is its siglum (`1Qisaa`)
COUNTED = ("spelling", "form", "substitution", "omitted", "added", "moved")
MATRES = str.maketrans("", "", "וי")
PREFIXES, ENDINGS = set("ובכלמהש"), set("ההוימנכת")
SP_FILES = ("otype", "oslots", "book", "chapter", "verse", "g_cons_utf8", "trailer", "lex", "nu")
DSS_FILES = ("otype", "oslots", "scroll", "book", "chapter", "verse", "glyph", "after", "rec",
             "unc")  # fmt: skip
YEAR_LEX = "CNH/"  # שנה
PREFIX_LEX = {"W": "c", "B": "b", "L": "l", "K": "k", "M": "m", "H": "d"}  # SP lexemes -> OSHB


@dataclass(frozen=True)
class WWord:
    """A witness's graphic word."""

    letters: str  # finals folded
    read: bool = True  # every letter preserved and certain enough
    lex: tuple[str, ...] = ()  # SP: its units' lexemes (prefixes first)
    nu: str = ""  # SP: the last unit's number (sg, pl, du)


def letters_of(s: str) -> str:
    """A word's letters, finals folded (presentation forms such as שׁ U+FB2A decomposed)."""
    return match_key(unicodedata.normalize("NFD", s))


def skeleton(form: str) -> str:
    """A word without its ו / י inside it (vowel letters); the first and the last letter kept, as
    a final ו / י is as often a suffix (שמו, "his name"; changed after the first run, which took
    every ו / י after the first letter, §16.78)."""
    if len(form) <= 2:
        return form
    return form[0] + form[1:-1].translate(MATRES) + form[-1]


def word_of(letters: str, idx: int = -1) -> Word:
    """A word for `diffs.align_words`, keyed by its skeleton."""
    return Word(idx, skeleton(letters), letters, letters)


def label(op: str, a: str, b: str) -> str:
    """`substitution` -> `form` when one skeleton is the other with one prefix or ending letter
    more (ו conjunction, ה article, a suffix)."""
    if op != "substitution":
        return op
    sa, sb = skeleton(a), skeleton(b)
    short, long_ = sorted((sa, sb), key=len)
    if (
        len(long_) == len(short) + 1
        and short
        and (
            (long_[1:] == short and long_[0] in PREFIXES)
            or (long_[:-1] == short and long_[-1] in ENDINGS)
        )
    ):
        return "form"
    return op


Position = tuple[str, int | None, int | None]  # (op, MT position, witness position)


def align(mt: list[str], wit: list[WWord], cfg: dict[str, Any]) -> list[Position]:
    """(op, MT position, witness position) for every position of the verse pair."""
    wc = cfg["witnesses"]
    ops = align_words([word_of(t) for t in mt], [word_of(w.letters) for w in wit],
                      wc["match"], wc["mismatch"], wc["gap"])  # fmt: skip
    out = []
    for o in ops:
        op = label(o.op, mt[o.a], wit[o.b].letters) if o.op == "substitution" else o.op
        out.append((op, o.a, o.b))
    return out


def counts(ops: list[Position], wit: list[WWord]) -> list[bool]:
    """Whether each position counts: its witness word is read; an omission when the witness
    words either side are read (a scroll's gap is no evidence)."""
    out = []
    for k, (_, _, b) in enumerate(ops):
        if b is not None:
            out.append(wit[b].read)
            continue
        before = next((ops[j][2] for j in range(k - 1, -1, -1) if ops[j][2] is not None), None)
        after = next((ops[j][2] for j in range(k + 1, len(ops)) if ops[j][2] is not None), None)
        out.append(before is not None and after is not None and wit[before].read
                   and wit[after].read)  # fmt: skip
    return out


def longest_plus(ops: list[Position], ok: list[bool]) -> int:
    """The largest plus: the read words of a run of `added` positions (a reconstructed word in
    the run does not break it: it is unknown, not evidence against; changed after the first
    run, which broke runs there, §16.78)."""
    best = run = 0
    for (op, _, _), c in zip(ops, ok, strict=True):
        run = run + int(c) if op == "added" else 0
        best = max(best, run)
    return best


# --- reading the datasets ----------------------------------------------------------------------


def _containing(starts: list[int], nodes: list[int], first: int) -> int:
    return nodes[bisect_right(starts, first) - 1]


def read_samaritan(raw: Path, books: dict[str, str]) -> dict[str, list[WWord]]:
    """WLC osis (`Gen.5.3`) -> the Samaritan verse's graphic words."""
    ot = read_otype(raw / "otype.tf")
    F = {f: read_tf(raw / f"{f}.tf") for f in SP_FILES[1:]}
    slots = F["oslots"]

    def by_first(kind: str) -> tuple[list[int], list[int]]:
        ns = list(range(ot[kind][0], ot[kind][1] + 1))
        pairs = sorted((slots[n][0], n) for n in ns)
        return [p for p, _ in pairs], [n for _, n in pairs]

    bs, bn = by_first("book")
    cs, cn = by_first("chapter")
    vs, vn = by_first("verse")
    out: dict[str, list[WWord]] = {}
    unit: list[int] = []
    for w in range(ot["word"][0], ot["word"][1] + 1):
        unit.append(w)
        if F["trailer"].get(w, "") == "" and w < ot["word"][1]:
            continue
        first = slots[unit[0]][0]
        v = _containing(vs, vn, first)
        book = books[F["book"][_containing(bs, bn, first)]]
        osis = f"{book}.{F['chapter'][_containing(cs, cn, first)]}.{F['verse'][v]}"
        letters = letters_of("".join(F["g_cons_utf8"].get(u, "") for u in unit))
        if letters:
            out.setdefault(osis, []).append(WWord(letters, True, tuple(F["lex"].get(u, "")
                                                                         for u in unit),
                                                  F["nu"].get(unit[-1], "")))  # fmt: skip
        unit = []
    return out


def read_scrolls(raw: Path, books: dict[str, str], max_unc: int
                 ) -> dict[tuple[str, str], list[WWord]]:  # fmt: skip
    """(scroll, WLC osis) -> the scroll's graphic words of the verse, in order."""
    ot = read_otype(raw / "otype.tf")
    F = {f: read_tf(raw / f"{f}.tf") for f in DSS_FILES[1:]}
    slots = F["oslots"]
    sc = sorted((slots[n][0], F["scroll"][n]) for n in range(ot["scroll"][0], ot["scroll"][1] + 1))
    s_first, s_name = [a for a, _ in sc], [b for _, b in sc]
    out: dict[tuple[str, str], list[WWord]] = {}
    unit: list[int] = []
    for w in range(ot["word"][0], ot["word"][1] + 1):
        if w not in F["book"]:  # not biblical, or no verse
            unit = []
            continue
        unit.append(w)
        if F["after"].get(w, "") == "" and w < ot["word"][1] and w + 1 in F["book"]:
            continue
        book = books.get(F["book"][unit[0]])
        if book is not None:
            signs = [s for u in unit for s in slots[u]]
            kept = [s for s in signs if re.fullmatch("[א-ת]", letters_of(F["glyph"].get(s, "")))]
            letters = letters_of("".join(F["glyph"][s] for s in kept))
            read = bool(kept) and all(not F["rec"].get(s) and int(F["unc"].get(s, 0)) <= max_unc
                                      for s in kept)  # fmt: skip
            if letters:
                scroll = s_name[bisect_right(s_first, slots[unit[0]][0]) - 1]
                osis = f"{book}.{F['chapter'][unit[0]]}.{F['verse'][unit[0]]}"
                out.setdefault((scroll, osis), []).append(WWord(letters, read))
        unit = []
    return out


# --- the Samaritan chronology --------------------------------------------------------------------


def num_words(ws: list[WWord], sp_lex: dict[str, str], sp_tens: dict[str, str]
              ) -> list[NumWord]:  # fmt: skip
    """The Samaritan words as `chronology.phrases` reads them: Strong's keys of `sp_lex`, and
    of `sp_tens` for a unit's plural (ETCBC files ארבעים under ארבע)."""
    out = []
    for i, w in enumerate(ws):
        pre = [PREFIX_LEX.get(x, "") for x in w.lex[:-1]]
        lx = w.lex[-1] if w.lex else ""
        core = sp_tens[lx] if w.nu == "pl" and lx in sp_tens else sp_lex.get(lx, "")
        if (
            w.letters.removeprefix("ו") == "מאת"
            and i + 1 < len(ws)
            and ws[i + 1].lex[-1:] == (YEAR_LEX,)
        ):  # the dataset parses a hundred before שנה as מן + את (Gen 25:7, 35:28)
            core, pre = sp_lex["M>H/"], ["c"] if w.letters.startswith("ו") else []
        number = {"du": "d", "sg": "s"}.get(w.nu, "p")
        out.append(NumWord(core, f"Ncm{number}a", "c" in pre, None, False, "k" in pre))
    return out


def sp_chronology(cfg: dict[str, Any], sp: dict[str, list[WWord]], osis_of: dict[int, str],
                  index: RefIndex, book_of: dict[int, int], mt_events: pd.DataFrame
                  ) -> pd.DataFrame:  # fmt: skip
    """Each event of `chronology.events` in the Torah, in the MT and in the Samaritan."""
    cc, wc = cfg["chronology"], cfg["witnesses"]
    numbers = {str(k): int(v) for k, v in cc["numbers"].items()}
    sp_lex = {str(k): str(v) for k, v in wc["sp_lex"].items()}
    sp_tens = {str(k): str(v) for k, v in wc["sp_tens"].items()}
    mt_year = dict(zip(mt_events[mt_events.used].event, mt_events[mt_events.used].year,
                       strict=True))  # fmt: skip
    year: dict[str, int] = {}
    rows = []
    for seq, ev in enumerate(cc["events"]):
        eid, frm, ref = ev[0], ev[1], ev[2]
        n, sign = (int(ev[3]) if len(ev) > 3 else 0), (int(ev[4]) if len(ev) > 4 else 1)
        if frm is None:
            year[eid] = 0
            rows.append((seq, eid, None, None, 0, int(mt_year.get(eid, 0))))
            continue
        vid = index.resolve(ref)[0]
        if BOOKS[int(book_of[vid])].section != "Torah" or frm not in year:
            continue
        ph = phrases(num_words(sp.get(osis_of.get(vid, ""), []), sp_lex, sp_tens), numbers)
        if len(ph) < n or eid in year:
            continue
        value = ph[n - 1].value
        year[eid] = year[frm] + sign * value
        rows.append((seq, eid, vid, value, year[eid], mt_year.get(eid)))
    df = pd.DataFrame(rows, columns=["seq", "event", "verse_id", "sp_value", "sp_year", "mt_year"])
    names = {str(k): str(v) for k, v in cc["names"].items()}
    df.insert(2, "name", [names.get(e.split(".")[0]) for e in df.event])
    df.insert(3, "death", [e.endswith(".death") for e in df.event])
    for c in ("verse_id", "sp_value", "mt_year"):
        df[c] = pd.array(df[c], dtype="Int64")
    return df


# --- the run -------------------------------------------------------------------------------------


def parallel_verses(seq: pd.DataFrame, cfg: dict[str, Any], torah: set[int]) -> set[int]:
    """Torah verses in a strong parallel sequence with another Torah passage (as `diffs`)."""
    d = cfg["diffs"]
    keep = (seq.q <= d["max_q"]) & ~seq.same_chapter.astype(bool)
    out: set[int] = set()
    for s in seq[keep].itertuples(index=False):
        for a, b, *_ in json.loads(s.pairs):
            if a in torah and b in torah:
                out |= {int(a), int(b)}
    return out


def shifted(labels: np.ndarray, books: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    out = labels.copy()
    for b in np.unique(books):
        i = np.flatnonzero(books == b)
        out[i] = np.roll(labels[i], int(rng.integers(len(i))))
    return out


def rate_ratio(plus: np.ndarray, lab: np.ndarray) -> float:
    a = plus[lab].mean() if lab.any() else np.nan
    b = plus[~lab].mean() if (~lab).any() else np.nan
    return float(a / b) if b > 0 else float("nan")


def run_witnesses(cfg: dict[str, Any], log: Log = print) -> Path:
    wc = cfg["witnesses"]
    raw, proc, art = (resolve_path(cfg, k) for k in ("data_raw", "data_processed", "artifacts"))
    t0 = time.perf_counter()
    for key, files in (("samaritan", SP_FILES), ("scrolls", DSS_FILES)):
        missing = [f for f in files if not (raw / key / f"{f}.tf").exists()]
        if missing:
            raise FileNotFoundError(f"{raw / key} lacks {missing}: run `bsim download --only"
                                    " witnesses`")  # fmt: skip
    verses = pd.read_parquet(proc / "verses.parquet", columns=["verse_id", "book_id", "chapter",
                                                               "verse", "oshb_osis"])  # fmt: skip
    index = RefIndex(verses)
    book_of = dict(zip(verses.verse_id, verses.book_id, strict=True))
    vids_of: dict[str, list[int]] = {}
    osis_of: dict[int, str] = {}
    for vid, osis in zip(verses.verse_id, verses.oshb_osis, strict=True):
        for o in [] if osis is None else [str(x) for x in osis]:
            vids_of.setdefault(o, []).append(int(vid))
            osis_of.setdefault(int(vid), o)
    words = pd.read_parquet(proc / "words.parquet",
                            columns=["verse_id", "idx", "surface", "display_idx"])  # fmt: skip
    words = words.sort_values(["verse_id", "idx"], kind="stable")
    mt: dict[int, list[tuple[int, str]]] = {}  # verse_id -> (display token, letters) per word
    for vid, sf, d in zip(words.verse_id, words.surface, words.display_idx, strict=True):
        k = match_key(str(sf))
        if k and not pd.isna(d):
            mt.setdefault(int(vid), []).append((int(d), k))

    sp = read_samaritan(raw / "samaritan", {str(k): str(v) for k, v in wc["sp_books"].items()})
    scrolls = read_scrolls(raw / "scrolls", {str(k): str(v) for k, v in wc["books"].items()},
                           int(wc["max_unc"]))  # fmt: skip
    log(f"read: the Samaritan {len(sp)} verses; the scrolls {len(scrolls)} scroll verses")

    # a witness verse per verse_id: WLC verses of one verse_id joined, in order
    def by_vid(texts: dict[str, list[WWord]]) -> dict[int, list[WWord]]:
        out: dict[int, list[WWord]] = {}
        for o, ws in texts.items():
            for vid in vids_of.get(o, [])[:1]:
                out.setdefault(vid, []).extend(ws)
        return out

    witnesses: dict[str, dict[int, list[WWord]]] = {SP: by_vid(sp)}
    per_scroll: dict[str, dict[str, list[WWord]]] = {}
    for (s, o), ws in scrolls.items():
        per_scroll.setdefault(s, {})[o] = ws
    for s, texts in sorted(per_scroll.items()):
        witnesses[s] = by_vid(texts)
    unmatched = len([o for o in sp if o not in vids_of])

    vrows, crows = [], []
    for wit, texts in witnesses.items():
        for vid in sorted(texts):
            ws = texts[vid]
            mw = mt.get(vid, [])
            ops = align([t for _, t in mw], ws, cfg)
            ok = counts(ops, ws)
            pos = [None] * len(ws)
            c = Counter()
            for (op, a, b), keep in zip(ops, ok, strict=True):
                if b is not None:
                    pos[b] = (op, None if a is None else mw[a][0])
                if keep:
                    c[op] += 1
                    if op != "same":
                        crows.append((wit, vid, op, None if a is None else mw[a][0],
                                      None if a is None else mw[a][1],
                                      None if b is None else ws[b].letters, b))  # fmt: skip
            toks = [{"t": w.letters, "r": w.read, "op": p[0], "mt": p[1]}
                    for w, p in zip(ws, pos, strict=True)]  # fmt: skip
            vrows.append({
                "witness": wit, "verse_id": vid, "book_id": int(book_of[vid]),
                "n_words": len(ws), "n_read": sum(w.read for w in ws),
                **{op: int(c[op]) for op in OPS}, "plus": longest_plus(ops, ok),
                "words": json.dumps(toks, ensure_ascii=False),
            })  # fmt: skip
    vdf = pd.DataFrame(vrows)
    cdf = pd.DataFrame(crows, columns=["witness", "verse_id", "op", "mt_tok", "mt_text", "w_text",
                                       "w_pos"])  # fmt: skip
    cdf = cdf.astype({"mt_tok": "Int64", "w_pos": "Int64"})
    vdf["variants"] = vdf[[*COUNTED]].sum(axis=1) - vdf["spelling"]

    # the books and the scrolls
    vdf["kind"] = np.where(vdf.witness == SP, SP, "scroll")

    def n_pluses(p: pd.Series) -> int:
        return int((p >= int(wc["plus_min"])).sum())

    books = vdf.groupby(["kind", "book_id"]).agg(
        verses=("verse_id", "nunique"), words=("n_words", "sum"), read=("n_read", "sum"),
        **{op: (op, "sum") for op in COUNTED}, pluses=("plus", n_pluses),
    ).reset_index()  # fmt: skip
    sc = vdf[vdf.kind == "scroll"].groupby("witness").agg(
        verses=("verse_id", "size"), first_vid=("verse_id", "min"), words=("n_words", "sum"),
        read=("n_read", "sum"), same=("same", "sum"),
        **{op: (op, "sum") for op in COUNTED},
        pluses=("plus", n_pluses),
    ).reset_index().rename(columns={"witness": "scroll"})  # fmt: skip
    sc["book_id"] = [int(book_of[v]) for v in sc.first_vid]
    sc = sc.sort_values(["read", "scroll"], ascending=[False, True]).reset_index(drop=True)

    # the claim: the Samaritan pluses in the Torah's parallel verses
    seq = pd.read_parquet(art / "sequences" / "verse.parquet")
    spv = vdf[vdf.witness == SP].sort_values("verse_id")
    torah = set(spv.verse_id.astype(int))
    par = parallel_verses(seq, cfg, torah)
    plus = (spv.plus >= int(wc["plus_min"])).to_numpy()
    lab = spv.verse_id.isin(par).to_numpy()
    bk = spv.book_id.to_numpy()
    observed = rate_ratio(plus, lab)
    rng = np.random.default_rng(int(wc["seed"]))
    null = np.array([rate_ratio(plus, shifted(lab, bk, rng)) for _ in range(int(wc["shifts"]))])
    p = empirical_p(observed, null)
    alpha = float(wc["alpha"])
    holds = bool(observed > 1 and p <= alpha)
    log(f"the Samaritan's pluses: {int(plus.sum())} verses; in the {int(lab.sum())} parallel"
        f" verses {plus[lab].mean():.4f}, elsewhere {plus[~lab].mean():.4f}: ratio"
        f" {observed:.2f} against {np.nanmean(null):.2f} shifted (p {p:.3g})")  # fmt: skip

    # the Samaritan chronology
    ev_path = art / "chronology" / "events.parquet"
    chron = sp_chronology(cfg, sp, osis_of, index, book_of, pd.read_parquet(ev_path))
    sp_year = dict(zip(chron.event, chron.sp_year, strict=True))

    # the known answers
    known = []
    by = {(r.witness, r.verse_id): r for r in vdf.itertuples(index=False)}
    for k in wc["known"]:
        vid = index.resolve(k["ref"])[0]
        r = by.get((k["witness"], vid))
        if r is None:
            ok = False
        elif "plus" in k:
            ok = int(r.plus) >= int(k["plus"])
        else:
            here = cdf[(cdf.witness == k["witness"]) & (cdf.verse_id == vid)
                       & cdf.op.isin(["substitution", "added", "form"])]  # fmt: skip
            ok = bool((here.w_text == match_key(str(k["reads"]))).any())
        known.append({"witness": k["witness"], "ref": k["ref"], "verse_id": vid,
                      "plus": k.get("plus"), "reads": k.get("reads"), "found": ok,
                      "note": k.get("note")})  # fmt: skip
    ck = wc["chronology_known"]
    chron_known = [{"event": e, "expected": int(y), "year": sp_year.get(e),
                    "holds": sp_year.get(e) == int(y)} for e, y in ck.items()]  # fmt: skip
    known_holds = all(k["found"] for k in known) and all(c["holds"] for c in chron_known)
    log("known: " + ", ".join(f"{k['witness']} {k['ref']} {'found' if k['found'] else 'MISSED'}"
                              for k in known)
        + "; " + ", ".join(f"Samaritan {c['event']} {c['year']} ({c['expected']})"
                           for c in chron_known))  # fmt: skip

    out = art / "witnesses"
    out.mkdir(parents=True, exist_ok=True)
    vdf.drop(columns=["kind"]).to_parquet(out / "verses.parquet")
    cdf.to_parquet(out / "changes.parquet")
    books.to_parquet(out / "books.parquet")
    sc.to_parquet(out / "scrolls.parquet")
    chron.to_parquet(out / "chronology.parquet")
    spm = vdf[vdf.witness == SP]
    scm = vdf[vdf.witness != SP]
    meta = {
        "config_hash": config_hash(cfg, "witnesses", "diffs.max_q", "chronology.events",
                                   "chronology.numbers", "sources.samaritan", "sources.scrolls"),
        "built_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "samaritan": {"verses": int(len(spm)), "words": int(spm.n_words.sum()),
                      **{op: int(spm[op].sum()) for op in OPS}, "unmatched_verses": unmatched},
        "scrolls": {"scrolls": int(len(sc)), "verses": int(len(scm)),
                    "words": int(scm.n_words.sum()), "read": int(scm.n_read.sum()),
                    **{op: int(scm[op].sum()) for op in OPS}},
        "plus_min": int(wc["plus_min"]), "max_unc": int(wc["max_unc"]),
        "sp_pluses": int(plus.sum()), "parallel_verses": int(lab.sum()),
        "plus_in_parallel": round(float(plus[lab].mean()), 4) if lab.any() else None,
        "plus_elsewhere": round(float(plus[~lab].mean()), 4) if (~lab).any() else None,
        "ratio": round(observed, 3), "null_mean": round(float(np.nanmean(null)), 3), "p": p,
        "shifts": int(wc["shifts"]), "alpha": alpha, "holds": holds,
        "known": known, "chronology_known": chron_known, "known_holds": known_holds,
        "seconds": round(time.perf_counter() - t0, 1),
    }  # fmt: skip
    write_meta(out / "witnesses.meta.json", meta)
    log(f"done: {len(vdf):,} witness verses, {len(cdf):,} variants counted ({meta['seconds']} s)"
        f" -> {out}")  # fmt: skip
    return out
