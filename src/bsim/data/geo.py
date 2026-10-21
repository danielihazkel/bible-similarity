"""The gazetteer's two sources (DESIGN.md §16.56), read from `paths.data_raw/geo/`.

- **TIPNR** (STEPBible, *Translators Individualised Proper Names with all References*, CC BY
  4.0): every proper name of the Bible, one record per individual or place
  (`$========== PLACE`, `PERSON`, `OTHER`). A record's first line holds its unique name
  (`Abel-beth-maacah@2Sa.20.14-2Ch`), for a place the OpenBible name and a map link. Each
  `– Named` line under it gives one name: its disambiguated Strong's number (`H0059H`), the
  Hebrew and every reference (English versification, STEP book abbreviations). One Strong's
  number may belong to several records (the Abel of 1 Sam 6:18 and the Abel of 2 Sam 20:18),
  told apart by their references. A PERSON record's first line also gives the family: parents
  (`father + mother`), siblings, partners, offspring, the tribe or nation of the father and the
  type (Male, Female, Group), each relative by unique name with a marker: `(?)` a choice made
  where the text is ambiguous, `(a)` an ancestor rather than the parent, `(d)` a group descended
  from them, `(f)` a place they founded (`TipnrFamily`, read for `bsim genealogy`, §16.63).
- **OpenBible.info Bible Geocoding** (`ancient.jsonl`, CC BY 4.0): one record per ancient place
  (`friendly_id`, types, the TIPNR ids it links to) with its proposed modern identifications, each
  voted on (`score.vote_total`, 0 to 1000) and resolved to a point (`lonlat`).

Only reading is done here; `analysis/places.py` joins them to the text.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from bsim.data.canon import BY_OSIS

# STEP's book abbreviations -> OSIS (the Hebrew Bible only; the rest are skipped)
STEP_BOOKS = {
    **{o: o for o in ("Gen", "Lev", "Num", "Neh", "Job", "Isa", "Jer", "Lam", "Dan", "Hos", "Mic",
                      "Hab", "Hag", "Mal")},
    "Exo": "Exod", "Deu": "Deut", "Jos": "Josh", "Jdg": "Judg", "Rut": "Ruth", "1Sa": "1Sam",
    "2Sa": "2Sam", "1Ki": "1Kgs", "2Ki": "2Kgs", "1Ch": "1Chr", "2Ch": "2Chr", "Ezr": "Ezra",
    "Est": "Esth", "Psa": "Ps", "Pro": "Prov", "Ecc": "Eccl", "Sng": "Song", "Ezk": "Ezek",
    "Jol": "Joel", "Amo": "Amos", "Oba": "Obad", "Jon": "Jonah", "Nam": "Nah", "Zep": "Zeph",
    "Zec": "Zech",
}  # fmt: skip
_HEAD = re.compile(r"=+\s*(PERSON|PLACE|OTHER)")
# a map link's `@lat,lon,zoomz` (`@0,14z` has no point: 14 is the zoom)
_MAP = re.compile(r"@(-?\d+(?:\.\d+)?),(-?\d+(?:\.\d+)?),\d+z")
# a compound name's later part: `H6010K«H6010=עֵמֶק` (the Strong's number, the form)
_PART = re.compile(r"H(\d+)[A-Za-z]?=([^=]*)$")
_REF = re.compile(r"^([1-3]?[A-Z][a-z]{1,2})\.(\d+)\.(\d+)$")
# a reference with the letter of its occurrence in the verse (`Exo.7.10a`, `Exo.7.10b`)
_REF_ANY = re.compile(r"^([1-3]?[A-Z][a-z]{1,2})\.(\d+)\.(\d+)[a-z]?$")
# a relative: `Zerah@Gen.38.30-Mat(a)`, `Tehinnah@1Ch.4.12=H8468`, `Jahdai@1Ch.2.47(?)`
_RELATIVE = re.compile(r"^(?P<uid>[^@]+@[^=()\s]+)(?:=[HG]\w+)?(?:\((?P<marker>[a-z?]+)\))?$")


@dataclass
class TipnrName:
    strong: int  # base Strong's number (`H0059H` -> 59)
    dstrong: str  # as written, disambiguated
    hebrew: str  # pointed (the first spelling given; a compound's parts in TIPNR's order)
    refs: list[tuple[int, int, int]]  # (book_id, chapter, verse), English numbering
    # a compound name's parts, (base Strong's number, pointed form), as TIPNR gives them:
    # the name, then the words added to it (`חֶבְרוֹן+H6010K«H6010=עֵמֶק`, the valley of Hebron)
    parts: list[tuple[int, str]] = field(default_factory=list)
    kind: str = "Named"  # the line's significance: Named, Spelled, Group, Mentioned, Aramaic, ...
    # every reference as given (book_id, chapter, verse), English numbering: with those marked by
    # their occurrence (`Exo.7.10a`) and a psalm title's verse 0, which `refs` leaves out / moves
    eng_refs: list[tuple[int, int, int]] = field(default_factory=list)


@dataclass
class TipnrRelative:
    uid: str  # the relative's unique name
    marker: str = ""  # ? | a | d | f (TIPNR's markers; `d?` both)


@dataclass
class TipnrFamily:
    """A PERSON record's family columns."""

    description: str
    father: TipnrRelative | None = None
    mother: TipnrRelative | None = None
    siblings: list[TipnrRelative] = field(default_factory=list)
    partners: list[TipnrRelative] = field(default_factory=list)
    offspring: list[TipnrRelative] = field(default_factory=list)
    tribe: str = ""  # the tribe or nation of the father (`Tribe of Judah`, `Edom`), "" if none
    type: str = ""  # Male | Female | Group


@dataclass
class TipnrRecord:
    uid: str  # unique name, `Abel-beth-maacah@2Sa.20.14-2Ch`
    category: str  # PERSON | PLACE | OTHER
    openbible: str = ""  # places: the OpenBible name
    lonlat: tuple[float, float] | None = None  # places: the map link's point
    names: list[TipnrName] = field(default_factory=list)
    family: TipnrFamily | None = None  # PERSON records


def relatives(field_: str) -> list[TipnrRelative]:
    """The relatives of a family column (comma-separated unique names with markers)."""
    out = []
    for item in field_.split(","):
        m = _RELATIVE.match(item.strip())
        if m:
            out.append(TipnrRelative(m["uid"], m["marker"] or ""))
    return out


def read_family(first: list[str]) -> TipnrFamily:
    """The family of a PERSON record from the fields of its first line."""
    f = [*first, *[""] * (9 - len(first))]
    father, _, mother = f[2].partition("+")
    dad, mum = relatives(father), relatives(mother)
    tribe = f[6].strip().lstrip(">").strip()
    return TipnrFamily(
        description=f[1].strip(),
        father=dad[0] if dad else None,
        mother=mum[0] if mum else None,
        siblings=relatives(f[3]),
        partners=relatives(f[4]),
        offspring=relatives(f[5]),
        tribe=tribe,
        type=f[8].strip(),
    )


def eng_ref(ref: str) -> tuple[int, int, int] | None:
    """`Exo.7.10a` -> (book_id, 7, 10) as written, English numbering (a psalm title stays verse
    0); None outside the Hebrew Bible."""
    m = _REF_ANY.match(ref.strip())
    if not m or m.group(1) not in STEP_BOOKS:
        return None
    return BY_OSIS[STEP_BOOKS[m.group(1)]].book_id, int(m.group(2)), int(m.group(3))


def step_ref(ref: str) -> tuple[int, int, int] | None:
    """`2Sa.20.14` -> (book_id, 20, 14); None outside the Hebrew Bible. A psalm title's verse 0
    is read as verse 1."""
    m = _REF.match(ref.strip())
    if not m or m.group(1) not in STEP_BOOKS:
        return None
    book = BY_OSIS[STEP_BOOKS[m.group(1)]].book_id
    # a psalm's title is its verse 0 in English numbering, verse 1 in Hebrew
    return book, int(m.group(2)), max(int(m.group(3)), 1)


def read_tipnr(path: Path) -> list[TipnrRecord]:
    """Every record of the TIPNR file, with its Hebrew names and their references."""
    text = path.read_text(encoding="utf-8").replace("\r\n", "\n")
    out = []
    for block in text.split("\n$")[1:]:
        lines = block.split("\n")
        m = _HEAD.match(lines[0])
        if not m or len(lines) < 2:
            continue
        first = lines[1].split("\t")
        if "@" not in first[0] or "=" not in first[0]:
            continue
        rec = TipnrRecord(uid=first[0].rsplit("=", 1)[0].strip(), category=m.group(1))
        if rec.category == "PLACE":
            rec.openbible = first[1].strip() if len(first) > 1 else ""
            point = next((p for f in first[2:6] if (p := _MAP.search(f))), None)
            if point:
                rec.lonlat = (float(point.group(2)), float(point.group(1)))
        elif rec.category == "PERSON":
            rec.family = read_family(first)
        for ln in lines[2:]:
            if not ln.startswith("–") or ln.startswith("– Total"):
                continue
            f = [x for x in ln.split("\t") if x.strip()]
            if len(f) < 5 or not f[2].startswith("H"):
                continue
            dstrong = f[2].split("«")[0].strip()
            digits = re.match(r"H(\d+)", dstrong)
            if not digits:
                continue
            refs = [r for x in f[4].split(";") if (r := step_ref(x)) is not None]
            eng = [r for x in f[4].split(";") if (r := eng_ref(x)) is not None]
            # the first of its spellings (`יְרוּשָׁלִַם, יְרוּשְׁלֵם`); a compound's later parts
            # are written `+H6010K«H6010=עֵמֶק`
            raw = f[2].split("=", 1)[1].split("+") if "=" in f[2] else [""]
            parts = [(int(digits.group(1)), raw[0].split(",")[0].strip())]
            for x in raw[1:]:
                m = _PART.search(x)
                if m:
                    parts.append((int(m.group(1)), m.group(2).split(",")[0].strip()))
            hebrew = " ".join(form for _, form in parts if form)
            rec.names.append(TipnrName(int(digits.group(1)), dstrong, hebrew, refs,
                                       parts if len(parts) > 1 else [],
                                       f[0].lstrip("–").strip(), eng))  # fmt: skip
        out.append(rec)
    return out


@dataclass
class Identification:
    lon: float
    lat: float
    score: int  # votes, 0..1000
    kind: str  # its class (settlement, natural, ...)


@dataclass
class AncientPlace:
    id: str
    friendly_id: str
    types: list[str]
    tipnr: list[str]  # TIPNR unique names it links to
    refs: list[tuple[int, int, int]]  # its verses (English numbering)
    identifications: list[Identification]  # best voted first

    @property
    def best(self) -> Identification | None:
        return self.identifications[0] if self.identifications else None


def read_openbible(path: Path) -> list[AncientPlace]:
    """Every ancient place of `ancient.jsonl` with its located identifications, best voted first."""
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        d = json.loads(line)
        link = (d.get("linked_data") or {}).get("s3b25cf") or {}  # the TIPNR source
        tipnr = [link["id"]] if "id" in link else list(link.get("ids", []))
        idents = []
        for ident in d.get("identifications", []):
            res = ident.get("resolutions", [])
            point = next((r["lonlat"] for r in res if r.get("lonlat")), None)
            if point:
                lon, lat = (float(x) for x in point.split(","))
                score = int((ident.get("score") or {}).get("vote_total", 0))
                idents.append(Identification(lon, lat, score, ident.get("class", "")))
        idents.sort(key=lambda i: -i.score)
        refs = [r for v in d.get("verses", []) if (r := _osis_ref(v.get("osis", ""))) is not None]
        out.append(AncientPlace(d["id"], d["friendly_id"], list(d.get("types", [])), tipnr,
                                refs, idents))  # fmt: skip
    return out


def _osis_ref(ref: str) -> tuple[int, int, int] | None:
    parts = ref.split(".")
    if len(parts) != 3 or parts[0] not in BY_OSIS or not (parts[1] + parts[2]).isdigit():
        return None
    return BY_OSIS[parts[0]].book_id, int(parts[1]), int(parts[2])
