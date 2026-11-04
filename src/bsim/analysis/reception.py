"""`bsim reception`: where the Mishnah, the Tosefta and the two Talmuds cite the Bible (DESIGN.md
§16.77).

- **Citations.** Sefaria's links (CC BY 4.0) between a rabbinic passage and a verse: only that one
  cites the other, never the rabbinic text itself. A link's rabbinic side is of a corpus
  (`reception.corpora`) when its Sefaria category and its title are the text's own, not a
  commentary's (`exclude`), an explanation's or another edition's (a title in parentheses); the
  Bavli's titles are cited by folio (`folio`). Its biblical side is a verse of the canon, or a
  range of at most `max_span` verses, each counted (a chapter or a passage is not counted per
  verse). A citation is one passage (as Sefaria cites it: Berakhot 2a:1) with one verse, counted
  once whatever the links' number or direction.
- **Claims fixed in advance.** (1) In the Mishnah the Torah's law (`legal`) is cited more per verse
  than its narrative: the ratio of the two means, against the law's verses shifted circularly
  round each book of the Torah (`shifts`; the blocks stay whole, and Leviticus, all law, and
  Genesis, none, do not move). (2) The Bavli leans to the law less than the Mishnah: the
  Mishnah's ratio less the Bavli's, against the corpus of each of their Torah citations shuffled
  between the two. (3) Known: every pair of `known` is found.

Writes `artifacts/reception/`: `citations.parquet` (`corpus, title, cite, cite_he, url, verse_id`,
one row per citation), `verses.parquet` (`verse_id, mishnah, tosefta, bavli, yerushalmi, total`:
every verse cited), `chapters.parquet` (`book_id, chapter, unit_id, verses, mishnah, tosefta,
bavli, yerushalmi, total`: every chapter), `books.parquet` (the same per book) and
`reception.meta.json`.
"""

from __future__ import annotations

import re
import time
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from bsim.analysis.stats import empirical_p
from bsim.config import config_hash, resolve_path, write_meta
from bsim.data.canon import BOOKS, BY_SEFARIA, hebrew_numeral
from bsim.data.refs import RefIndex

Log = Callable[[str], None]

CORPORA = ("mishnah", "tosefta", "bavli", "yerushalmi")
_COLS = ["Citation 1", "Citation 2", "Text 1", "Text 2", "Category 1", "Category 2"]

# the corpora's names, and the tractates', in Hebrew (Sefaria's English titles; apostrophes dropped)
CORPUS_HE = {"mishnah": "משנה", "tosefta": "תוספתא", "bavli": "בבלי", "yerushalmi": "ירושלמי"}
TRACTATES_HE = {
    "Berakhot": "ברכות", "Peah": "פאה", "Demai": "דמאי", "Kilayim": "כלאים", "Sheviit": "שביעית",
    "Terumot": "תרומות", "Maasrot": "מעשרות", "Maaser Sheni": "מעשר שני", "Challah": "חלה",
    "Orlah": "ערלה", "Bikkurim": "ביכורים", "Shabbat": "שבת", "Eruvin": "עירובין",
    "Pesachim": "פסחים", "Shekalim": "שקלים", "Yoma": "יומא", "Sukkah": "סוכה", "Beitzah": "ביצה",
    "Rosh Hashanah": "ראש השנה", "Taanit": "תענית", "Megillah": "מגילה", "Moed Katan": "מועד קטן",
    "Chagigah": "חגיגה", "Yevamot": "יבמות", "Ketubot": "כתובות", "Nedarim": "נדרים",
    "Nazir": "נזיר", "Sotah": "סוטה", "Gittin": "גיטין", "Kiddushin": "קידושין",
    "Bava Kamma": "בבא קמא", "Bava Metzia": "בבא מציעא", "Bava Batra": "בבא בתרא",
    "Sanhedrin": "סנהדרין", "Makkot": "מכות", "Shevuot": "שבועות", "Eduyot": "עדויות",
    "Avodah Zarah": "עבודה זרה", "Avot": "אבות", "Pirkei Avot": "פרקי אבות", "Horayot": "הוריות",
    "Zevachim": "זבחים", "Menachot": "מנחות", "Chullin": "חולין", "Bekhorot": "בכורות",
    "Arakhin": "ערכין", "Temurah": "תמורה", "Keritot": "כריתות", "Meilah": "מעילה",
    "Tamid": "תמיד", "Middot": "מדות", "Kinnim": "קינים", "Kelim": "כלים",
    "Kelim Kamma": "כלים בבא קמא", "Kelim Metzia": "כלים בבא מציעא",
    "Kelim Batra": "כלים בבא בתרא", "Oholot": "אהלות", "Negaim": "נגעים", "Parah": "פרה",
    "Tahorot": "טהרות", "Mikvaot": "מקואות", "Niddah": "נדה", "Makhshirin": "מכשירין",
    "Zavim": "זבים", "Tevul Yom": "טבול יום", "Yadayim": "ידים", "Oktzin": "עוקצים",
    "Oktsin": "עוקצים",
}  # fmt: skip

_PREFIX = {"mishnah": "Mishnah ", "tosefta": "Tosefta ", "yerushalmi": "Jerusalem Talmud "}
_LOC = re.compile(r"^(?P<title>.+?) (?P<loc>\d[\d:ab-]*)$")
_FOLIO = re.compile(r"^(?P<daf>\d+)(?P<side>[ab])")


def corpus_of(category: str, title: str, cite: str, rc: dict[str, Any]) -> str | None:
    """The corpus a link's rabbinic side belongs to, or None (a commentary, another edition...)."""
    if re.search(rc["exclude"], title):
        return None
    for name, (cat, pattern) in rc["corpora"].items():
        if category != cat or not re.match(pattern, title):
            continue
        if name == "bavli" and not re.search(rc["folio"], cite):
            continue
        return name
    return None


def tractate(corpus: str, title: str) -> str:
    """The tractate's name: the title without its corpus (`Mishnah Berakhot` -> `Berakhot`)."""
    t = title.removeprefix(_PREFIX.get(corpus, ""))
    return "Avot" if t == "Pirkei Avot" else t.replace("'", "")


def cite_he(corpus: str, title: str, cite: str) -> str:
    """A citation in Hebrew: `משנה ברכות א:ג`, `בבלי ברכות ב ע״א`, `ירושלמי ברכות א:א`
    (a folio's or a halakha's segment left out, as the printed editions cite them)."""
    m = _LOC.match(cite)
    name = TRACTATES_HE.get(tractate(corpus, title), tractate(corpus, title))
    head = "פרקי אבות" if title == "Pirkei Avot" else f"{CORPUS_HE[corpus]} {name}"
    if not m:
        return head
    loc = m["loc"].split("-")[0]
    if corpus == "bavli":
        f = _FOLIO.match(loc)
        if not f:
            return head
        return f"{head} {hebrew_numeral(int(f['daf']))} {'ע״א' if f['side'] == 'a' else 'ע״ב'}"
    parts = [int(x) for x in loc.split(":") if x.isdigit()][:2]
    return f"{head} {':'.join(hebrew_numeral(x) for x in parts)}" if parts else head


def sefaria_url(cite: str) -> str:
    """The passage on Sefaria, in Hebrew only (`Berakhot 2a:1` -> `.../Berakhot.2a.1?lang=he`)."""
    m = _LOC.match(cite)
    path = f"{m['title']}.{m['loc'].replace(':', '.')}" if m else cite
    return f"https://www.sefaria.org/{path.replace(' ', '_')}?lang=he"


# midrashim cited by the family tree's rabbinic identifications (K13): the Hebrew title and how
# many levels of a Sefaria reference the printed editions cite (`Bereshit Rabbah 61:4`: two)
MIDRASH_HE = {
    "Bereshit Rabbah": ("בראשית רבה", 2), "Shemot Rabbah": ("שמות רבה", 2),
    "Vayikra Rabbah": ("ויקרא רבה", 2), "Bamidbar Rabbah": ("במדבר רבה", 2),
    "Devarim Rabbah": ("דברים רבה", 2), "Sifrei Bamidbar": ("ספרי במדבר", 1),
    "Sifrei Devarim": ("ספרי דברים", 1), "Shir HaShirim Rabbah": ("שיר השירים רבה", 2),
    "Ruth Rabbah": ("רות רבה", 2), "Esther Rabbah": ("אסתר רבה", 2),
    "Kohelet Rabbah": ("קהלת רבה", 2), "Eichah Rabbah": ("איכה רבה", 2),
    "Pirkei DeRabbi Eliezer": ("פרקי דרבי אליעזר", 1),
}  # fmt: skip


def source_he(cite: str) -> str | None:
    """Any rabbinic reference in Hebrew: a Bavli folio, a Mishnah, Tosefta or Yerushalmi
    reference, or a midrash of `MIDRASH_HE`; None when its title is none of these."""
    m = _LOC.match(cite)
    if not m:
        return None
    title, loc = m["title"], m["loc"].split("-")[0]
    if title in MIDRASH_HE:
        he, levels = MIDRASH_HE[title]
        parts = [int(x) for x in loc.split(":") if x.isdigit()][:levels]
        return f"{he} {':'.join(hebrew_numeral(x) for x in parts)}"
    for corpus, prefix in _PREFIX.items():
        if title.startswith(prefix) and tractate(corpus, title) in TRACTATES_HE:
            return cite_he(corpus, title, cite)
    if title == "Pirkei Avot":
        return cite_he("mishnah", title, cite)
    if title in TRACTATES_HE and _FOLIO.match(loc):
        return cite_he("bavli", title, cite)
    return None


def page_of(cite: str) -> str:
    """A reference's page: its last level dropped (`Sotah 11b:12` -> `Sotah 11b`,
    `Bereshit Rabbah 61:4` -> `Bereshit Rabbah 61`)."""
    return re.sub(r":\d+(-\d+)?$", "", cite.strip())


def page_links(paths: list[Path], pages: set[str], index: RefIndex) -> dict[str, set[int]]:
    """The verses Sefaria's links tie to each of `pages` (any of its passages, a link to at
    most three verses)."""
    out: dict[str, set[int]] = {p: set() for p in pages}
    for p in paths:
        df = pd.read_csv(p, usecols=_COLS, dtype=str, keep_default_na=False)
        for a, b in (("1", "2"), ("2", "1")):
            side = df[df[f"Text {b}"].isin(BY_SEFARIA)]
            page = side[f"Citation {a}"].map(page_of)
            hit = page.isin(pages)
            for pg, ref in zip(page[hit], side.loc[hit, f"Citation {b}"], strict=True):
                try:
                    s, e = index.resolve(ref)
                except ValueError:
                    continue
                if e - s < 3:
                    out[pg] |= set(range(s, e + 1))
    return out


def read_citations(paths: list[Path], rc: dict[str, Any], index: RefIndex
                   ) -> tuple[pd.DataFrame, dict[str, int]]:  # fmt: skip
    """One row per citation (corpus, title, cite, verse_id) and the counts of what was left out."""
    rows: list[tuple[str, str, str, int]] = []
    dropped = {"long": 0, "invalid": 0}
    for p in paths:
        df = pd.read_csv(p, usecols=_COLS, dtype=str, keep_default_na=False)
        for a, b in (("1", "2"), ("2", "1")):
            side = df[df[f"Text {b}"].isin(BY_SEFARIA) & df[f"Category {a}"].isin(
                {c for c, _ in rc["corpora"].values()})]  # fmt: skip
            for cat, title, cite, ref in zip(
                side[f"Category {a}"], side[f"Text {a}"], side[f"Citation {a}"],
                side[f"Citation {b}"], strict=True,
            ):  # fmt: skip
                corpus = corpus_of(cat, title, cite, rc)
                if corpus is None:
                    continue
                try:
                    s, e = index.resolve(ref)
                except ValueError:
                    dropped["invalid"] += 1
                    continue
                if e - s + 1 > int(rc["max_span"]):
                    dropped["long"] += 1
                    continue
                rows.extend((corpus, title, cite, v) for v in range(s, e + 1))
    out = pd.DataFrame(rows, columns=["corpus", "title", "cite", "verse_id"]).drop_duplicates()
    order = {c: i for i, c in enumerate(CORPORA)}
    out = out.sort_values(["verse_id", "corpus", "cite"], key=lambda c: c.map(order) if c.name ==
                          "corpus" else c, kind="stable").reset_index(drop=True)  # fmt: skip
    return out, dropped


def legal_mask(verses: pd.DataFrame, refs: list[str], index: RefIndex) -> np.ndarray:
    """Per verse (in `verses` order): in one of the law's blocks."""
    on = np.zeros(int(verses.verse_id.max()) + 1, dtype=bool)
    for r in refs:
        s, e = index.resolve(r)
        on[s : e + 1] = True
    return on[verses.verse_id.to_numpy()]


def law_ratio(counts: np.ndarray, legal: np.ndarray) -> float:
    """Mean citations per verse of the law over the narrative's (NaN when either has none)."""
    lo = counts[~legal].mean() if (~legal).any() else np.nan
    hi = counts[legal].mean() if legal.any() else np.nan
    return float(hi / lo) if lo > 0 else float("nan")


def shifted(legal: np.ndarray, books: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    """The law's verses shifted circularly round each book (by a random offset each)."""
    out = legal.copy()
    for b in np.unique(books):
        i = np.flatnonzero(books == b)
        out[i] = np.roll(legal[i], int(rng.integers(len(i))))
    return out


def run_reception(cfg: dict[str, Any], log: Log = print) -> Path:
    rc = cfg["reception"]
    raw, proc, art = (resolve_path(cfg, k) for k in ("data_raw", "data_processed", "artifacts"))
    t0 = time.perf_counter()
    verses = pd.read_parquet(proc / "verses.parquet", columns=["verse_id", "book_id", "chapter",
                                                               "verse"])  # fmt: skip
    index = RefIndex(verses)
    pattern = re.compile(cfg["sources"]["sefaria"]["links_regex"])
    paths = sorted(p for p in (raw / "sefaria" / "links").glob("*.csv")
                   if pattern.match(f"links/{p.name}"))  # fmt: skip
    cit, dropped = read_citations(paths, rc, index)
    cit["cite_he"] = [cite_he(c, t, x) for c, t, x in zip(cit.corpus, cit.title, cit.cite,
                                                          strict=True)]  # fmt: skip
    cit["url"] = cit.cite.map(sefaria_url)
    log(
        f"{len(cit)} citations of {cit.verse_id.nunique()} verses from {len(paths)} files"
        f" ({dropped['long']} links to longer passages, {dropped['invalid']} unresolved, left out)"
    )
    unknown = sorted({tractate(c, t) for c, t in zip(cit.corpus, cit.title, strict=True)}
                     - set(TRACTATES_HE))  # fmt: skip
    if unknown:
        log(f"tractates without a Hebrew name: {unknown}")

    # per verse, chapter and book
    per = cit.pivot_table(index="verse_id", columns="corpus", values="cite", aggfunc="count",
                          fill_value=0).reindex(columns=list(CORPORA), fill_value=0)  # fmt: skip
    per["total"] = per.sum(axis=1)
    per = per.astype(int).reset_index()
    full = verses.merge(per, on="verse_id", how="left").fillna(0)
    for c in (*CORPORA, "total"):
        full[c] = full[c].astype(int)
    by_ch = full.groupby(["book_id", "chapter"], as_index=False).agg(
        verses=("verse_id", "size"), **{c: (c, "sum") for c in (*CORPORA, "total")}
    )
    by_ch["unit_id"] = [f"c:{b}:{c}" for b, c in zip(by_ch.book_id, by_ch.chapter, strict=True)]
    by_book = full.groupby("book_id", as_index=False).agg(
        verses=("verse_id", "size"), **{c: (c, "sum") for c in (*CORPORA, "total")}
    )

    # (1) and (2): the Torah's law against its narrative
    torah_ids = {b.book_id for b in BOOKS if b.section == "Torah"}
    torah = full[full.book_id.isin(torah_ids)].sort_values("verse_id")
    legal = legal_mask(torah, list(rc["legal"]), index)
    books_t = torah.book_id.to_numpy()
    rng = np.random.default_rng(int(rc["seed"]))
    reps = int(rc["shifts"])
    ratios = {c: law_ratio(torah[c].to_numpy(dtype=float), legal) for c in (*CORPORA, "total")}
    m_counts = torah.mishnah.to_numpy(dtype=float)
    null1 = [law_ratio(m_counts, shifted(legal, books_t, rng)) for _ in range(reps)]
    p_law = empirical_p(ratios["mishnah"], np.asarray(null1))
    alpha = float(rc["alpha"])
    law_holds = bool(ratios["mishnah"] > 1 and p_law <= alpha)
    log(
        "Torah, citations per verse of the law over the narrative: "
        + ", ".join(f"{c} {ratios[c]:.2f}" for c in (*CORPORA, "total"))
        + f"; the Mishnah's against {reps} shifts p {p_law:.4g}"
    )

    # the Torah's citations of the Mishnah and the Bavli, each its corpus, shuffled between them
    pos = {v: i for i, v in enumerate(torah.verse_id)}
    mb = cit[cit.corpus.isin(["mishnah", "bavli"]) & cit.verse_id.isin(pos)]
    at = mb.verse_id.map(pos).to_numpy()
    is_m = (mb.corpus == "mishnah").to_numpy()
    n_v = len(torah)

    def gap(lab: np.ndarray) -> float:
        cm = np.bincount(at[lab], minlength=n_v).astype(float)
        cb = np.bincount(at[~lab], minlength=n_v).astype(float)
        return law_ratio(cm, legal) - law_ratio(cb, legal)

    gap_obs = gap(is_m)
    null2 = [gap(rng.permutation(is_m)) for _ in range(reps)]
    p_gap = empirical_p(gap_obs, np.asarray(null2))
    gap_holds = bool(gap_obs > 0 and p_gap <= alpha)
    log(f"the Mishnah's ratio less the Bavli's {gap_obs:.3f} (p {p_gap:.4g})")

    # (3) known citations
    found = set(zip(cit.cite, cit.verse_id, strict=True))
    known = []
    for cite, ref in rc["known"]:
        v = index.resolve(ref)[0]
        known.append({"cite": cite, "ref": ref, "verse_id": v, "found": (cite, v) in found})
    known_holds = all(k["found"] for k in known)
    log(f"known: {[(k['cite'], k['ref'], k['found']) for k in known]}")

    out = art / "reception"
    out.mkdir(parents=True, exist_ok=True)
    cit[["corpus", "title", "cite", "cite_he", "url", "verse_id"]].to_parquet(
        out / "citations.parquet", index=False
    )
    per.to_parquet(out / "verses.parquet", index=False)
    by_ch[["book_id", "chapter", "unit_id", "verses", *CORPORA, "total"]].to_parquet(
        out / "chapters.parquet", index=False
    )
    by_book.to_parquet(out / "books.parquet", index=False)
    meta = {
        "config_hash": config_hash(cfg, "reception", "sources.sefaria"),
        "built_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "citations": len(cit), "verses_cited": int(per.verse_id.nunique()),
        "by_corpus": {c: int((cit.corpus == c).sum()) for c in CORPORA},
        "passages": {c: int(cit[cit.corpus == c].cite.nunique()) for c in CORPORA},
        "dropped_long": dropped["long"], "dropped_invalid": dropped["invalid"],
        "legal_verses": int(legal.sum()), "narrative_verses": int((~legal).sum()),
        "ratios": {c: round(r, 4) for c, r in ratios.items()},
        "law_p": p_law, "law_holds": law_holds,
        "gap": round(gap_obs, 4), "gap_p": p_gap, "gap_holds": gap_holds,
        "known": known, "known_holds": known_holds,
        "max_span": int(rc["max_span"]), "shifts": reps, "alpha": alpha,
        "seconds": round(time.perf_counter() - t0, 1),
    }  # fmt: skip
    write_meta(out / "reception.meta.json", meta)
    log(
        f"done: law {'holds' if law_holds else 'not borne out'}, Mishnah over Bavli"
        f" {'holds' if gap_holds else 'not borne out'}, known"
        f" {'holds' if known_holds else 'not borne out'} ({meta['seconds']} s) -> {out}"
    )
    return out
