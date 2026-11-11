"""`bsim theophoric`: personal names built on a name of God, and how they are spelled where
(DESIGN.md §16.90, D152; M163).

Many names carry God's name: ירמיהו / ירמיה (Jeremiah), יהורם / יורם (Jehoram, Joram), ישמעאל.
Spelling them is a known marker of date: the long ending ‑יהו is the older (Kings, Jeremiah), the
short ‑יה the later (Ezra–Nehemiah, Chronicles), though both stand side by side in most books.

- **The names.** HebrewStrong's person names (`n-pr-m`, `n-pr-f`) whose entry derives them from
  יה / יהוה (3050, 3068) or from אל (410), or calls them a form of such a name (יורם, "a form of"
  יהורם).
- **Each occurrence's form.** The word's consonants without its prefixes, finals folded: a
  Yahwistic name ends in ‑יהו (`yahu`) or ‑יה (`yah`), or starts with יהו‑ (`yeho`) or יו‑
  (`yo`); a name with אל starts (`el_first`) or ends (`el_last`) with it.
- **The claim, fixed before the first run.** Late books (`dating.late`) spell the ending short
  more often than early ones (`dating.early`) for the same names: the share of ‑יה among the
  endings, late minus early, against the book groups shuffled over each name's occurrences
  (`shuffles`), one-sided at `alpha`.
- **Known answers.** Jeremiah and Kings spell the ending mostly long, Ezra and Nehemiah mostly
  short (`known`: a book and the side its share must fall on).

The share of short endings is also a feature of the LBH profile (`yah_short`, §16.24).

Writes `artifacts/theophoric/`: `names.parquet` (`lemma, he, divine` yah | el, `n` and one count
per form), `books.parquet` (`book_id` and the counts of each form), `theophoric.meta.json`.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from bsim.analysis.stats import empirical_p
from bsim.config import config_hash, resolve_path, write_meta
from bsim.data.canon import BY_OSIS
from bsim.store.lexicon import strip_prefixes
from bsim.text.normalize import consonantal, fold_finals

Log = Callable[[str], None]
FORMS = ("yahu", "yah", "yeho", "yo", "el_first", "el_last")
YAH = ("3050", "3068", "3069")  # יה, יהוה (and its reading as אדני)
EL = ("410",)


def _key(s: str | None) -> str:
    return (s or "").lstrip("H")


def names(path: Path) -> pd.DataFrame:
    """`lemma, he, divine`: HebrewStrong's person names built on יה / יהוה (`yah`) or אל (`el`),
    with the names called "a form of" one of them."""
    from lxml import etree

    root = etree.parse(str(path)).getroot()
    ns = root.nsmap[None]
    w_tag = f"{{{ns}}}w"
    rows, forms = [], {}
    for e in root.iterfind(f"{{{ns}}}entry"):
        w = e.find(w_tag)
        if w is None or not (w.get("pos") or "").startswith("n-pr-") or w.get("pos") == "n-pr-loc":
            continue
        src = e.find(f"{{{ns}}}source")
        kids = list(src) if src is not None else []
        links = [_key(c.get("src")) for c in kids if c.tag == w_tag and c.get("src")]
        text = "".join(src.itertext()).lower() if src is not None else ""
        lemma = _key(e.get("id"))
        divine = (
            "yah" if any(x in YAH for x in links) else "el" if any(x in EL for x in links) else None
        )
        if divine:
            rows.append((lemma, w.text or "", divine))
        elif links and text.strip().startswith("a form of"):
            forms[lemma] = (w.text or "", links[0])
    found = {r[0]: r[2] for r in rows}
    rows += [(lem, he, found[src]) for lem, (he, src) in forms.items() if src in found]
    return pd.DataFrame(rows, columns=["lemma", "he", "divine"]).drop_duplicates("lemma")


def form_of(word: str, divine: str) -> str | None:
    """The form of a name built on God's name, from its consonants (prefixes stripped)."""
    if divine == "yah":
        if word.endswith("יהו"):
            return "yahu"
        if word.endswith("יה"):
            return "yah"
        if word.startswith("יהו"):
            return "yeho"
        if word.startswith("יו"):
            return "yo"
        return None
    if word.startswith("אל"):
        return "el_first"
    if word.endswith("אל"):
        return "el_last"
    return None


def occurrences(words: pd.DataFrame, theo: pd.DataFrame) -> pd.DataFrame:
    """`verse_id, lemma, form`: every occurrence of a name of `theo` with a form."""
    divine = dict(zip(theo.lemma, theo.divine, strict=True))
    rows = []
    for v, lemma, surface, morph in zip(
        words.verse_id, words.lemma, words.surface, words.morph, strict=True
    ):
        if not isinstance(morph, str) or "Np" not in morph:
            continue
        for part in str(lemma).split("/"):
            k = part.replace(" ", "").rstrip("+")
            if k in divine:
                word = fold_finals(consonantal(strip_prefixes(str(surface), str(lemma))))
                f = form_of(word.replace(" ", ""), divine[k])
                if f:
                    rows.append((int(v), k, f))
                break
    return pd.DataFrame(rows, columns=["verse_id", "lemma", "form"])


def short_share(occ: pd.DataFrame, late: np.ndarray) -> float:
    """Short ‑יה among the endings in late books, less the same share in early ones."""
    end = occ.form.isin(["yahu", "yah"]).to_numpy()
    short = (occ.form == "yah").to_numpy()
    a, b = end & late, end & ~late
    return float(short[a].sum() / max(a.sum(), 1) - short[b].sum() / max(b.sum(), 1))


def run_theophoric(cfg: dict[str, Any], log: Log = print) -> Path:
    tc, dc = cfg["theophoric"], cfg["dating"]
    proc, art = resolve_path(cfg, "data_processed"), resolve_path(cfg, "artifacts")
    raw = resolve_path(cfg, "data_raw")
    out = art / "theophoric"
    t0 = time.perf_counter()
    theo = names(raw / "lexicon" / "HebrewStrong.xml")
    theo = theo[~theo.lemma.isin({str(x) for x in tc["exclude"]})].reset_index(drop=True)
    verses = pd.read_parquet(proc / "verses.parquet", columns=["verse_id", "book_id"])
    words = pd.read_parquet(
        proc / "words.parquet", columns=["verse_id", "lemma", "surface", "morph"]
    )
    occ = occurrences(words, theo)
    book_of = dict(zip(verses.verse_id, verses.book_id, strict=True))
    occ["book_id"] = occ.verse_id.map(book_of)
    log(f"{len(theo)} names built on God's name, {len(occ)} occurrences")

    # the claim: the same names, late books against early ones, the groups shuffled within names
    early = {BY_OSIS[b].book_id for b in dc["early"]}
    late = {BY_OSIS[b].book_id for b in dc["late"]}
    ends = occ[occ.form.isin(["yahu", "yah"]) & occ.book_id.isin(early | late)]
    ends = ends.reset_index(drop=True)
    is_late = ends.book_id.isin(late).to_numpy()
    observed = short_share(ends, is_late)
    rng = np.random.default_rng(tc["seed"])
    groups = [g.to_numpy() for _, g in ends.groupby("lemma").groups.items()]
    null = np.empty(tc["shuffles"])
    for s in range(tc["shuffles"]):
        lab = is_late.copy()
        for idx in groups:
            lab[idx] = rng.permutation(lab[idx])
        null[s] = short_share(ends, lab)
    p = empirical_p(observed, null)
    claim = {
        "early_short": float((ends.form[~is_late] == "yah").mean()) if (~is_late).any() else None,
        "late_short": float((ends.form[is_late] == "yah").mean()) if is_late.any() else None,
        "difference": round(observed, 4),
        "null_mean": round(float(null.mean()), 4),
        "p": p,
        "holds": bool(observed > null.mean() and p <= tc["alpha"]),
        "occurrences": int(len(ends)),
        "names": int(ends.lemma.nunique()),
    }
    log(f"short ending: early {claim['early_short']}, late {claim['late_short']}, p {p:.4g}")

    # per name and per book
    counts = lambda g: pd.Series({f: int((g.form == f).sum()) for f in FORMS})  # noqa: E731
    per_name = occ.groupby("lemma").apply(counts, include_groups=False).reset_index()
    name_df = theo.merge(per_name, on="lemma", how="inner")
    name_df["n"] = name_df[list(FORMS)].sum(axis=1)
    name_df = name_df.sort_values(["n", "lemma"], ascending=[False, True]).reset_index(drop=True)
    book_df = occ.groupby("book_id").apply(counts, include_groups=False).reset_index()

    known = []
    for k in tc["known"]:
        ids = [BY_OSIS[b].book_id for b in k["books"]]
        c = book_df[book_df.book_id.isin(ids)][["yahu", "yah"]].sum()
        share = float(c.yah / (c.yah + c.yahu)) if c.yah + c.yahu else None
        ok = share is not None and (share < 0.5 if k["side"] == "long" else share > 0.5)
        known.append({"books": k["books"], "side": k["side"], "short": share,
                      "endings": int(c.yah + c.yahu), "holds": bool(ok)})  # fmt: skip
    log("known: " + ", ".join(f"{'+'.join(k['books'])} {k['side']} {k['holds']}" for k in known))

    out.mkdir(parents=True, exist_ok=True)
    name_df.to_parquet(out / "names.parquet", index=False)
    book_df.to_parquet(out / "books.parquet", index=False)
    meta = {
        "config_hash": config_hash(cfg, "theophoric", "dating"),
        "built_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "names": int(len(name_df)),
        "occurrences": int(len(occ)),
        "forms": {f: int((occ.form == f).sum()) for f in FORMS},
        "claim": claim,
        "shuffles": int(tc["shuffles"]),
        "alpha": tc["alpha"],
        "known": known,
        "known_holds": all(k["holds"] for k in known),
        "seconds": round(time.perf_counter() - t0, 1),
    }
    write_meta(out / "theophoric.meta.json", meta)
    log(f"done: {len(name_df)} names, {len(occ)} occurrences ({meta['seconds']} s) -> {out}")
    return out / "names.parquet"
