"""Parse Sefaria MAM text JSON and index schemas (DESIGN.md §1.1, §3.2, §4).

MAM verses are HTML fragments. Cleaning keeps the pointed text with te'amim, shows the qere,
moves the ketiv to `ketiv_note`, drops footnotes and the inverted nun, and records the
`{פ}`/`{ס}` markers (with whether letters follow them, i.e. a mid-verse break).
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from lxml import html

_LETTER = re.compile(r"[\u05d0-\u05ea]")
# Private-use sentinels stand in for the markers until their position in the text is known.
_MARK = {"mam-spi-pe": "\ue000", "mam-spi-samekh": "\ue001"}
_MARK_TYPE = {"\ue000": "pe", "\ue001": "samekh"}
_DROP = {"footnote-marker", "footnote", "mam-spi-invnun"}


@dataclass(frozen=True)
class Break:
    kind: str  # "pe" | "samekh"
    mid_verse: bool


@dataclass
class MamVerse:
    text_display: str
    ketiv_note: str | None = None
    breaks: list[Break] = field(default_factory=list)


def _replace(el: html.HtmlElement, text: str) -> None:
    """Replace `el` by plain `text`, keeping its tail."""
    parent = el.getparent()
    joined = text + (el.tail or "")
    prev = el.getprevious()
    if prev is not None:
        prev.tail = (prev.tail or "") + joined
    else:
        parent.text = (parent.text or "") + joined
    parent.remove(el)


def clean_mam_verse(fragment: str) -> MamVerse:
    root = html.fragment_fromstring(fragment, create_parent="div")
    ketiv: list[str] = []
    # Materialize first: the tree is mutated while walking.
    for el in list(root.iter()):
        if el is root:
            continue
        cls = el.get("class", "")
        if cls in _DROP:
            _replace(el, "")
        elif cls in _MARK:
            _replace(el, _MARK[cls])
        elif cls == "mam-kq-k":
            ketiv.append("".join(el.itertext()).strip().strip("()"))
            _replace(el, "")
        elif cls == "mam-kq-q":
            _replace(el, "".join(el.itertext()).strip().strip("[]"))
        elif el.tag == "br":
            _replace(el, " ")
    raw = "".join(root.itertext())
    breaks = [
        Break(_MARK_TYPE[ch], bool(_LETTER.search(raw[i + 1 :])))
        for i, ch in enumerate(raw)
        if ch in _MARK_TYPE
    ]
    text = " ".join(raw.translate({0xE000: " ", 0xE001: " "}).split())
    return MamVerse(text, ", ".join(ketiv) or None, breaks)


def load_mam(path: str | Path) -> list[list[MamVerse]]:
    """`text[chapter][verse]` of a MAM JSON file, cleaned."""
    with Path(path).open(encoding="utf-8") as f:
        text = json.load(f)["text"]
    return [[clean_mam_verse(v) for v in chapter] for chapter in text]


def load_parashiyot(path: str | Path) -> list[tuple[str, str, str]]:
    """`(sharedTitle, heTitle, wholeRef)` for each `alts.Parasha` node of a schema file."""
    with Path(path).open(encoding="utf-8") as f:
        nodes = json.load(f)["alts"]["Parasha"]["nodes"]
    return [(n["sharedTitle"], n["heTitle"], n["wholeRef"]) for n in nodes]
