"""Parse OSHB OSIS XML into per-verse word lists (DESIGN.md §1.1, §3).

Ketiv/qere: a ketiv word is `<w type="x-ketiv">`, followed by
`<note type="variant"><catchWord/><rdg type="x-qere">…qere words…</rdg></note>`. One qere may
replace several ketiv words, a qere may stand alone (qere wela ketiv), and the qere reading may
be empty (ketiv wela qere). All other notes (textual notes, alternative accents, exegesis) are
ignored. `kq` picks which reading becomes the verse's words; `kq_pairs` keeps both sides of
every ketiv / qere (the ketiv / qere analysis, DESIGN.md §16.30).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from lxml import etree

NS = "{http://www.bibletechnologies.net/2003/OSIS/namespace}"
_CONTENT = re.compile(r"^(\d+)\+?(?: ([a-z]))?$")


@dataclass(frozen=True)
class Word:
    oshb_id: str
    surface: str  # pointed, morpheme separators removed
    lemma: str  # raw OSHB lemma, e.g. "c/1961"
    morph: str
    content_lemmas: tuple[str, ...]  # numeric lemmas with sense letter, e.g. ("1121a",)
    kq: str | None  # None, "k" (ketiv) or "q" (qere)


@dataclass
class OshbVerse:
    chapter: int
    verse: int
    osis: str  # e.g. "Gen.1.1"
    words: list[Word] = field(default_factory=list)
    breaks: list[str] = field(default_factory=list)  # "pe" / "samekh" segs, in order


def content_lemmas(lemma: str) -> tuple[str, ...]:
    """Keep numeric (content) morphemes; drop prefix particles. `1121 a` -> `1121a`."""
    out = []
    for morpheme in lemma.split("/"):
        m = _CONTENT.match(morpheme.strip())
        if m:
            out.append(m[1] + (m[2] or ""))
    return tuple(out)


def _word(el: etree._Element, kq: str | None) -> Word:
    lemma = el.get("lemma", "")
    return Word(
        oshb_id=el.get("id", ""),
        surface="".join(el.itertext()).replace("/", ""),
        lemma=lemma,
        morph=el.get("morph", ""),
        content_lemmas=content_lemmas(lemma),
        kq=kq,
    )


def parse_verse(verse_el: etree._Element, kq: str = "qere") -> OshbVerse:
    if kq not in ("qere", "ketiv"):
        raise ValueError(f"kq must be 'qere' or 'ketiv', got {kq!r}")
    osis = verse_el.get("osisID")
    _, c, v = osis.split(".")
    out = OshbVerse(int(c), int(v), osis)
    for el in verse_el:
        if el.tag == f"{NS}w":
            if el.get("type") == "x-ketiv":
                if kq == "ketiv":
                    out.words.append(_word(el, "k"))
            else:
                out.words.append(_word(el, None))
        elif el.tag == f"{NS}note" and el.get("type") == "variant":
            if kq == "qere":
                for rdg in el.iter(f"{NS}rdg"):
                    if rdg.get("type") == "x-qere":
                        out.words.extend(_word(w, "q") for w in rdg.iter(f"{NS}w"))
        elif el.tag == f"{NS}seg" and el.get("type") in ("x-pe", "x-samekh"):
            out.breaks.append(el.get("type")[2:])
    return out


@dataclass
class KqPair:
    """One ketiv / qere: the written words, the read words (either may be empty) and `pos`,
    the index in the verse's qere-reading words of the first read word (or of the word the
    reading would follow, for a ketiv without qere)."""

    osis: str
    pos: int
    ketiv: list[Word] = field(default_factory=list)
    qere: list[Word] = field(default_factory=list)


def kq_pairs(verse_el: etree._Element) -> list[KqPair]:
    """Every ketiv / qere of one verse, in order: the ketiv words before a variant note pair
    with that note's qere words."""
    osis = verse_el.get("osisID")
    out: list[KqPair] = []
    pending: list[Word] = []
    pos = 0  # words of the qere reading so far
    for el in verse_el:
        if el.tag == f"{NS}w":
            if el.get("type") == "x-ketiv":
                pending.append(_word(el, "k"))
                continue
            pos += 1
        elif el.tag == f"{NS}note" and el.get("type") == "variant":
            qere = [
                _word(w, "q")
                for rdg in el.iter(f"{NS}rdg")
                if rdg.get("type") == "x-qere"
                for w in rdg.iter(f"{NS}w")
            ]
            out.append(KqPair(osis, pos, pending, qere))
            pos += len(qere)
            pending = []
    return out


def parse_book(path: str | Path, kq: str = "qere") -> list[OshbVerse]:
    """All verses of one OSHB book file, in document order."""
    tree = etree.parse(str(path))
    return [parse_verse(v, kq) for v in tree.iter(f"{NS}verse")]
