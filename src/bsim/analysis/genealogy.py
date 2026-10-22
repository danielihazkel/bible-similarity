"""`bsim genealogy`: the family tree of everyone the Hebrew Bible names (DESIGN.md §16.63).

- **Who.** TIPNR's PERSON records with a Hebrew name in the Hebrew Bible (`data/geo.py`): people,
  groups (the nations of Gen 10, clans) and the unnamed it needs as links (`– Mentioned`, "a wife
  of Hezron"). A person's verses are its references in English numbering moved to ours
  (`data/kjv.py`), each snapped to the nearest verse within `max_shift` that names it; the name's
  words there are its tokens (none for the unnamed).
- **Links.** A child's parents (`father + mother`) and a parent's offspring, merged: the role is
  the parent's (father, mother; a group's parent is its father), the kind `son` unless TIPNR marks
  an ancestor or a descended group (`descendant`); `(?)` is kept as `doubt`. Partners are
  `spouse` links and siblings `sibling` links (the panel's, not the tree's); a place a person
  founded (`(f)`) is listed on the person.
- **Proof verses.** A link's candidates are the verses naming both, ranked by the strongest cue in
  them (`cues`): the child, בן / בת and the parent within `construct_span` words in that order
  (`construct`, "יהושע בן נון"); בני / בנות right before the parent and the child after
  (`sons_of`); a form of ילד (`begot`); any son, daughter, father or mother word (`kin`); none
  (`together`). For a spouse: אשה next to either name (`wife`). Ties go to the nearer names, then
  canon order; the first `proof_k` are kept. A link without a candidate is unproved.
- **The review.** `curation/genealogy/*.yaml` (`paths.curation`), one file per block of
  `genealogy.blocks`, checks links against the Hebrew: each `confirmed`, `fixed`, `added` or
  `rejected`, with its own proof verses if given (Sefaria references, Hebrew numbering); added
  people (`anon:` keys); conflicts, whose readings name a parent and its verses, the first drawn;
  cue verses looked at and passed over (`missed`); identities (`same:`), one person under several
  TIPNR keys, `merged` into one (before any link is decided; a merged person with two fathers
  needs a conflict) or `possible` (both kept, cross-referred). The cross-book steps' files
  (`cross_blocks`) have no verse range. Every key, reference and status is checked and any error
  stops the build (`RuntimeError`).
- **The tree.** Each person gets one primary parent: a conflict's first reading, else the father
  (an adoptive one last, Gen 48:5), else the mother; the other parent links are cross-links. A
  person left without one who married in (a spouse, or a parent only of children drawn under the
  other parent) is drawn beside the spouse; anyone else is attached to the eponym of its tribe or
  nation (`tribes`) by an `unstated` link, else put under "unattached", by the book that first
  names them. `root` (Adam) heads the tree. A cycle is an error.

Writes `artifacts/genealogy/`: `persons.parquet`, `links.parquet`, `proofs.parquet`,
`conflicts.parquet`, `identities.parquet`, `blocks.parquet` and `genealogy.meta.json`.
`bsim genealogy-review <block>` writes the block's review sheet to `review/<block>.md`
(`run_genealogy_review`).
"""

from __future__ import annotations

import json
import re
import time
from collections import Counter, defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

from bsim.config import config_hash, resolve_path
from bsim.data.canon import BOOKS
from bsim.data.geo import TipnrRecord, read_tipnr
from bsim.data.kjv import English
from bsim.data.refs import parse_ref
from bsim.text.normalize import consonantal

Log = Callable[[str], None]

PARENT_ROLES = ("father", "mother")
ROLES = (*PARENT_ROLES, "spouse", "sibling", "unstated")
LINK_KINDS = ("son", "descendant", "adopted", "levirate", "founder", "unstated")
STATUSES = ("confirmed", "fixed", "added", "rejected")
CONFLICT_KINDS = ("bible", "descendant")
IDENTITY_STATUSES = ("merged", "possible")
PERSON_KINDS = ("person", "group", "anon", "virtual")
UNATTACHED = "virtual:unattached"

SON = {"1121a", "1323"}  # בן, בת
BEGET = {"3205"}  # ילד
KIN = SON | {"1", "517"}  # בן, בת, אב, אם
WIFE = {"802"}  # אשה
_NUM = re.compile(r"\d+")


@dataclass
class Word:
    idx: int  # its place in the verse
    display: int | None  # its display token
    strongs: frozenset[int]  # the Strong's numbers of its content lemmas
    content: frozenset[str]  # its content lemmas (`1121a`)


@dataclass
class Person:
    key: str  # TIPNR's unique name, or a curated `anon:` key (never shown)
    he: str  # Hebrew name, consonants ("" for the unnamed)
    sex: str | None  # m | f
    kind: str  # person | group | anon | virtual
    tribe: str = ""
    strongs: set[int] = field(default_factory=set)
    verses: dict[int, list[int]] = field(default_factory=dict)  # verse_id -> word idx of its name
    founded: list[str] = field(default_factory=list)  # TIPNR places it founded


@dataclass
class Link:
    parent: str  # spouse / sibling: the two people
    child: str
    role: str
    kind: str = "son"
    doubt: bool = False
    marker: str = ""
    sides: set[str] = field(default_factory=set)  # parent | offspring | partners | siblings
    order: int | None = None  # the child's place in the parent's offspring
    status: str = "tipnr"  # tipnr | confirmed | fixed | added | rejected | reading
    source: str = "tipnr"  # tipnr | curated | tribe
    proof: list[int] | None = None  # curated proof verses, in order
    conflict: int | None = None
    drawn: bool = False  # a conflict's first reading: the one the tree draws
    block: str | None = None

    @property
    def reviewed(self) -> bool:
        return self.status != "tipnr"


def verse_words(words: pd.DataFrame) -> dict[int, list[Word]]:
    out: dict[int, list[Word]] = defaultdict(list)
    w = words.sort_values(["verse_id", "idx"])
    for vid, idx, disp, content in zip(w.verse_id, w.idx, w.display_idx, w.content_lemmas,
                                       strict=True):  # fmt: skip
        cs = frozenset(str(c) for c in content)
        nums = frozenset(int(m.group()) for c in cs if (m := _NUM.match(c)))
        out[int(vid)].append(Word(int(idx), None if pd.isna(disp) else int(disp), nums, cs))
    return out


def name_tokens(ws: list[Word], strongs: set[int]) -> list[int]:
    return [w.idx for w in ws if w.strongs & strongs]


def person_verses(
    rec: TipnrRecord,
    english: English,
    vwords: dict[int, list[Word]],
    max_shift: int,
) -> tuple[dict[int, list[int]], int]:
    """A record's verses (verse_id -> word idx of its name there) and how many of its references
    named it nowhere within `max_shift` (kept, without tokens)."""
    out: dict[int, list[int]] = {}
    unmatched = 0
    for n in rec.names:
        for ref in n.eng_refs:
            vid = english(*ref)
            if vid is None:
                continue
            if n.kind == "Mentioned":  # unnamed: the verse that speaks of them
                out.setdefault(vid, [])
                continue
            book = ref[0]
            for d in [0, *[s * k for k in range(1, max_shift + 1) for s in (-1, 1)]]:
                ws = vwords.get(vid + d, [])
                toks = name_tokens(ws, {n.strong})
                if toks and english.book_at.get(vid + d) == book:
                    out[vid + d] = sorted({*out.get(vid + d, []), *toks})
                    break
            else:
                unmatched += 1
                out.setdefault(vid, [])
    return dict(sorted(out.items())), unmatched


def cue(ws: list[Word], ps: list[int], cs: list[int], role: str, span: int) -> tuple[str, int]:
    """The strongest cue of a verse for a link, and the distance between the two names."""
    dist = min((abs(p - c) for p in ps for c in cs), default=10**6)
    if role == "spouse":
        wife = [w.idx for w in ws if w.content & WIFE]
        near = any(abs(x - y) == 1 for x in wife for y in [*ps, *cs])
        return ("wife" if near else "together"), dist
    son = [w.idx for w in ws if w.content & SON]
    if any(c < s < p and p - c <= span for c in cs for s in son for p in ps):
        return "construct", dist
    if any(p == s + 1 and any(c > p for c in cs) for s in son for p in ps):
        return "sons_of", dist
    if any(w.content & BEGET for w in ws):
        return "begot", dist
    if any(w.content & KIN for w in ws):
        return "kin", dist
    return "together", dist


def rank_proofs(
    link: Link,
    a: Person,
    b: Person,
    vwords: dict[int, list[Word]],
    weights: dict[str, int],
    span: int,
    near: int = 0,
) -> list[tuple[int, str, list[int]]]:
    """A link's candidate verses, best first: (verse_id, cue, word idx of both names). With no
    verse naming both: the child's verses with the parent named up to `near` verses before
    (`nearby`, a list's heading: "ובני אלפעל" and the sons in the next verse)."""
    rows = []
    for vid in sorted(set(a.verses) & set(b.verses)):
        ws = vwords.get(vid, [])
        ps, cs = a.verses[vid], b.verses[vid]
        c, dist = cue(ws, ps, cs, link.role, span)
        rows.append((-int(weights[c]), dist, vid, c, sorted({*ps, *cs})))
    if not rows:
        for vid in sorted(b.verses):
            d = next((d for d in range(1, near + 1) if vid - d in a.verses), None)
            if d is not None:
                rows.append((-int(weights["nearby"]), d, vid, "nearby", b.verses[vid]))
    rows.sort()
    return [(vid, c, toks) for _, _, vid, c, toks in rows]


def display_tokens(ws: list[Word], idx: list[int]) -> list[int]:
    want = set(idx)
    return sorted({w.display for w in ws if w.idx in want and w.display is not None})


# --- the review files ----------------------------------------------------------------------


class CurationError(RuntimeError):
    pass


def read_curation(folder: Path) -> list[dict[str, Any]]:
    """Every review file of `folder` (sorted by name), each with its `file`."""
    if not folder.exists():
        return []
    out = []
    for p in sorted(folder.glob("*.yaml")):
        doc = yaml.safe_load(p.read_text("utf-8")) or {}
        if not isinstance(doc, dict):
            raise CurationError(f"{p.name}: not a mapping")
        out.append({**doc, "file": p.name})
    return out


def verse_of_ref(ref: str, vid_of: dict[tuple[int, int, int], int]) -> int:
    """`I Chronicles 3:19` (Sefaria title, Hebrew numbering) -> verse_id."""
    r = parse_ref(ref)
    if r.v1 is None or (r.c1, r.v1) != (r.c2, r.v2):
        raise ValueError(f"{ref!r} is not one verse")
    vid = vid_of.get((r.book.book_id, r.c1, r.v1))
    if vid is None:
        raise ValueError(f"no verse {ref!r}")
    return vid


_ARROW = re.compile(r"^\s*(?P<child>\S+)\s*<-\s*(?P<parent>\S+)\s*$")


def merge_person(
    keep: str, gone: str, persons: dict[str, Person], links: dict[tuple[str, str, str], Link]
) -> None:
    """Fold `gone` into `keep` (the review's `same:`, merged): its verses and names join, its links
    move over, two links that become one fold, and a link between the two is dropped."""
    a, b = persons[keep], persons.pop(gone)
    for v, toks in b.verses.items():
        a.verses[v] = sorted({*a.verses.get(v, []), *toks})
    a.verses = dict(sorted(a.verses.items()))
    a.strongs |= b.strongs
    a.founded += [x for x in b.founded if x not in a.founded]
    a.he, a.sex, a.tribe = a.he or b.he, a.sex or b.sex, a.tribe or b.tribe
    for k in [k for k in links if gone in k[:2]]:
        lk = links.pop(k)
        parent, child = (keep if x == gone else x for x in k[:2])
        if parent == child:
            continue
        if lk.role in ("spouse", "sibling") and child < parent:
            parent, child = child, parent
        lk.parent, lk.child = parent, child
        have = links.setdefault((parent, child, lk.role), lk)
        if have is not lk:
            have.sides |= lk.sides
            have.doubt |= lk.doubt
            have.marker = "".join(sorted(set(have.marker) | set(lk.marker)))
            have.order = lk.order if have.order is None else have.order


def apply_curation(
    docs: list[dict[str, Any]],
    persons: dict[str, Person],
    links: dict[tuple[str, str, str], Link],
    blocks: dict[str, tuple[int, int]],
    vid_of: dict[tuple[int, int, int], int],
    cross: frozenset[str] = frozenset(),
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    """Apply the review files to `persons` and `links` (in place). Returns the conflicts, the
    blocks' rows and the identities; every problem found is raised at the end, together.

    The files' people come first, then the identities (`same:`): a merge folds the other keys into
    the first before any link is decided, and the merged keys still name the person. A link the
    merge made of two may be decided once under each pair of keys if both agree. `cross` are the
    blocks of the cross-book steps, which have no verse range."""
    errors: list[str] = []
    conflicts: list[dict[str, Any]] = []
    rows: list[dict[str, Any]] = []
    seen_blocks: dict[str, str] = {}
    # id(link) -> the file whose `links` or conflict decided it, the keys it named, the status
    decided: dict[int, tuple[str, tuple[str, str], str]] = {}
    alias: dict[str, str] = {}  # a merged key -> the key it was merged into
    identities: list[dict[str, Any]] = []

    def canon(key: str) -> str:
        return alias.get(key, key)

    def err(where: str, msg: str) -> None:
        errors.append(f"{where}: {msg}")

    def refs(where: str, items: Any) -> list[int] | None:
        if items is None:
            return None
        if not isinstance(items, list) or not items:
            err(where, "proof must be a non-empty list of references")
            return None
        out = []
        for r in items:
            try:
                out.append(verse_of_ref(str(r), vid_of))
            except ValueError as e:
                err(where, str(e))
        return out

    def known(where: str, key: Any) -> bool:
        if not isinstance(key, str) or (key not in persons and key not in alias):
            err(where, f"unknown person {key!r}")
            return False
        return True

    def note_of(where: str, c: dict[str, Any]) -> dict[str, str]:
        note = c.get("note") or {}
        if note and set(note) != {"en", "he"}:
            err(where, "a note has both en and he, or is left out")
        return note

    def parent_links(child: str, parent: str) -> list[Link]:
        return [lk for r in (*PARENT_ROLES, "spouse") if (lk := links.get((parent, child, r)))]

    valid = []
    for doc in docs:
        f = doc["file"]
        block = doc.get("block")
        if block not in blocks and block not in cross:
            err(f, f"unknown block {block!r} (genealogy.blocks, genealogy.cross_blocks)")
            continue
        if block in seen_blocks:
            err(f, f"block {block} is also in {seen_blocks[block]}")
        seen_blocks[block] = f
        valid.append(doc)
        for i, p in enumerate(doc.get("people") or []):
            where = f"{f} people[{i}]"
            key = p.get("key") if isinstance(p, dict) else None
            if not isinstance(key, str):
                err(where, "a person needs a key")
                continue
            if key in persons:  # a correction to TIPNR's
                for k in ("he", "sex"):
                    if k in p:
                        setattr(persons[key], k, p[k])
                continue
            if not key.startswith("anon:"):
                err(where, f"a new person's key starts with anon: ({key!r})")
                continue
            kind = p.get("kind", "anon")
            if kind not in ("person", "group", "anon") or p.get("sex") not in ("m", "f", None):
                err(where, "kind is person, group or anon; sex m or f")
                continue
            persons[key] = Person(key, str(p.get("he", "")), p.get("sex"), kind)

    # the identities: the merges first, so that every link is decided between merged persons
    possible = []
    for doc in valid:
        for i, s in enumerate(doc.get("same") or []):
            where = f"{doc['file']} same[{i}]"
            ks = s.get("keys") if isinstance(s, dict) else None
            st = s.get("status") if isinstance(s, dict) else None
            if not isinstance(ks, list) or len(ks) < 2 or st not in IDENTITY_STATUSES:
                err(where, f"lists two keys or more and a status, one of {IDENTITY_STATUSES}")
                continue
            note = note_of(where, s)
            if not all([known(where, k) for k in ks]):
                continue
            proof = refs(where, s.get("proof"))
            if proof is None:
                if "proof" not in s:
                    err(where, "an identification needs its proof verses")
                continue
            ident = {"status": st, "keys": ks, "proof": proof, "block": doc["block"],
                     "note_en": note.get("en"), "note_he": note.get("he")}  # fmt: skip
            if st == "possible":
                possible.append((where, ident))
                continue
            keep = canon(ks[0])
            for k in ks[1:]:
                gone = canon(k)
                if gone == keep:
                    err(where, f"{k} is merged into {ks[0]} already")
                    continue
                merge_person(keep, gone, persons, links)
                alias[gone] = keep
                for x, y in alias.items():
                    if y == gone:
                        alias[x] = keep
            identities.append(ident)
    for where, ident in possible:
        first, *others = (canon(k) for k in ident["keys"])
        if first in others:
            err(where, f"{ident['keys']} name one person, merged elsewhere")
            continue
        identities.append(ident)

    for doc in valid:
        f, block = doc["file"], doc["block"]
        status = doc.get("status", "draft")
        if status not in ("draft", "reviewed"):
            err(f, f"status must be draft or reviewed, not {status!r}")
        n_links = 0
        for i, item in enumerate(doc.get("links") or []):
            where = f"{f} links[{i}]"
            if isinstance(item, str):
                m = _ARROW.match(item)
                if not m:
                    err(where, f"{item!r}: write `child <- parent`")
                    continue
                item = {"child": m["child"], "parent": m["parent"], "status": "confirmed"}
            child, parent = item.get("child"), item.get("parent")
            if not (known(where, child) & known(where, parent)):
                continue
            named = (child, parent)
            child, parent = canon(child), canon(parent)
            st = item.get("status", "confirmed")
            if st not in STATUSES:
                err(where, f"status {st!r} is not one of {STATUSES}")
                continue
            role, kind = item.get("role"), item.get("kind")
            if role is not None and role not in (*PARENT_ROLES, "spouse"):
                err(where, f"role {role!r}")
                continue
            if kind is not None and kind not in LINK_KINDS:
                err(where, f"kind {kind!r}")
                continue
            pair = parent_links(child, parent)
            have = pair if role is None else [lk for lk in pair if lk.role == role]
            if not have and st == "fixed" and role in PARENT_ROLES:  # fixed to the other role
                have = [lk for lk in pair if lk.role in PARENT_ROLES]
            proof = refs(where, item.get("proof"))
            if st == "added":
                if have:
                    err(where, f"{child} <- {parent} is in TIPNR: confirm or fix it")
                    continue
                if role is None:
                    role = "mother" if persons[parent].sex == "f" else "father"
                lk = Link(parent, child, role, kind or "son", source="curated")
                links[(parent, child, role)] = lk
            else:
                if not have:
                    err(where, f"no link {child} <- {parent} to {st}: add it")
                    continue
                lk = have[0]
                if id(lk) in decided:
                    f0, named0, st0 = decided[id(lk)]
                    if named0 != named and st0 == st:  # two links, one since a merge: they agree
                        n_links += 1
                        continue
                    if named0 != named:
                        err(where, f"{child} <- {parent} is {st0} in {f0} under the keys merged"
                                   f" into these: decide it once")  # fmt: skip
                    else:
                        err(where, f"{named[0]} <- {named[1]} is already decided in {f0}:"
                                   " leave it out")  # fmt: skip
                    continue
                if st == "fixed" and role is not None and role != lk.role:
                    del links[(lk.parent, lk.child, lk.role)]
                    lk.role = role
                    links[(parent, child, role)] = lk
                if kind is not None:
                    lk.kind = kind
            lk.status, lk.block = st, block
            decided[id(lk)] = (f, named, st)
            if proof is not None:
                lk.proof = proof
            n_links += 1
        n_conf = 0
        for i, c in enumerate(doc.get("conflicts") or []):
            where = f"{f} conflicts[{i}]"
            kind, child = c.get("kind"), c.get("child")
            readings = c.get("readings") or []
            if kind not in CONFLICT_KINDS:
                err(where, f"kind {kind!r} is not one of {CONFLICT_KINDS}")
                continue
            if not known(where, child):
                continue
            named_child, child = child, canon(child)
            if (
                not isinstance(readings, list)
                or not readings
                or (kind == "bible" and len(readings) < 2)
            ):
                err(where, "a conflict lists its readings (a bible conflict at least two)")
                continue
            note = note_of(where, c)
            out = []
            for j, r in enumerate(readings):
                w = f"{where} readings[{j}]"
                parent = r.get("parent") if isinstance(r, dict) else None
                if not known(w, parent):
                    continue
                named, parent = (named_child, parent), canon(parent)
                have = [lk for lk in parent_links(child, parent) if lk.role in PARENT_ROLES]
                proof = refs(w, r.get("proof"))
                if have:
                    lk = have[0]
                    if lk.status == "tipnr":
                        lk.status = "confirmed"
                else:
                    role = r.get("role") or ("mother" if persons[parent].sex == "f" else "father")
                    lk = Link(parent, child, role, "son", status="reading", source="curated")
                    links[(parent, child, role)] = lk
                if r.get("kind") in LINK_KINDS:
                    lk.kind = r["kind"]
                if proof is not None:
                    lk.proof = proof
                lk.conflict, lk.block = len(conflicts) + 1, lk.block or block
                lk.drawn = not out
                decided.setdefault(id(lk), (f, named, "reading"))
                out.append(lk)
            conflicts.append({
                "conflict_id": len(conflicts) + 1, "kind": kind, "child": child, "block": block,
                "readings": out, "note_en": note.get("en"), "note_he": note.get("he"),
            })  # fmt: skip
            n_conf += 1
        missed = doc.get("missed") or []
        for i, m in enumerate(missed):
            if not isinstance(m, dict) or "ref" not in m or not m.get("reason"):
                err(f"{f} missed[{i}]", "each has a ref and a reason")
            else:
                refs(f"{f} missed[{i}]", [m["ref"]])
        if block in blocks:
            lo, hi = blocks[block]
            rows.append({"block": block, "first_vid": lo, "last_vid": hi, "status": status,
                         "n_links": n_links, "n_conflicts": n_conf, "n_missed": len(missed),
                         "file": f})  # fmt: skip

    # a merged person with two fathers (or mothers) needs a conflict that names them
    named_in: dict[str, set[str]] = defaultdict(set)
    for c in conflicts:
        named_in[c["child"]] |= {lk.parent for lk in c["readings"]}
    for k in {canon(i["keys"][0]) for i in identities if i["status"] == "merged"}:
        for role in PARENT_ROLES:
            ps = {lk.parent for lk in links.values() if lk.child == k and lk.role == role
                  and lk.status != "rejected" and lk.kind != "adopted"}  # fmt: skip
            if len(ps) > 1 and not ps <= named_in[k]:
                err(k, f"merged, it has {len(ps)} {role}s ({', '.join(sorted(ps))}):"
                       " a conflict lists them as readings")  # fmt: skip
    if errors:
        raise CurationError("the review files have errors:\n  " + "\n  ".join(errors))
    for i in identities:
        i["persons"] = list(dict.fromkeys(canon(k) for k in i["keys"]))
    return conflicts, rows, identities


def missed_refs(docs: list[dict[str, Any]], vid_of: dict[tuple[int, int, int], int]) -> set[int]:
    return {verse_of_ref(str(m["ref"]), vid_of) for d in docs for m in d.get("missed") or []}


# --- building ------------------------------------------------------------------------------


def family_links(records: list[TipnrRecord], keep: set[str]) -> dict[tuple[str, str, str], Link]:
    """TIPNR's family columns as links between kept persons, both sides merged."""
    sex = {
        r.uid: {"Male": "m", "Female": "f"}.get(r.family.type)
        for r in records if r.family is not None
    }  # fmt: skip
    links: dict[tuple[str, str, str], Link] = {}

    def add(parent: str, child: str, role: str, marker: str, side: str, order: int | None = None):
        if parent not in keep or child not in keep or parent == child:
            return
        if role in ("spouse", "sibling") and child < parent:
            parent, child = child, parent
        k = (parent, child, role)
        lk = links.get(k)
        if lk is None:
            kind = "descendant" if {"a", "d"} & set(marker) else "son"
            lk = links[k] = Link(parent, child, role, kind if role in PARENT_ROLES else role)
        lk.sides.add(side)
        lk.doubt |= "?" in marker
        lk.marker = "".join(sorted(set(lk.marker) | set(marker)))
        if order is not None:
            lk.order = order

    for r in records:
        fam = r.family
        if fam is None or r.uid not in keep:
            continue
        if fam.father:
            add(fam.father.uid, r.uid, "father", fam.father.marker, "parent")
        if fam.mother:
            add(fam.mother.uid, r.uid, "mother", fam.mother.marker, "parent")
        role = "mother" if sex.get(r.uid) == "f" else "father"
        for i, o in enumerate(fam.offspring):
            if "f" not in o.marker:
                add(r.uid, o.uid, role, o.marker, "offspring", i)
        for p in fam.partners:
            add(r.uid, p.uid, "spouse", p.marker, "partners")
        for s in fam.siblings:
            add(r.uid, s.uid, "sibling", s.marker, "siblings")
    return links


def choose_primary(links: dict[tuple[str, str, str], Link]) -> dict[str, Link]:
    """child -> the parent link the tree draws."""
    cands: dict[str, list[Link]] = defaultdict(list)
    for lk in links.values():
        if lk.role in PARENT_ROLES and lk.status != "rejected":
            cands[lk.child].append(lk)

    def rank(lk: Link) -> tuple[int, int, int, int, int, str]:
        return (
            0 if lk.drawn else 1,  # a conflict's first reading
            0 if lk.kind != "adopted" else 1,  # an adoptive father is a cross-link (Gen 48:5)
            0 if lk.role == "father" else 1,
            0 if lk.status != "reading" else 1,  # a conflict's other readings are cross-links
            0 if "parent" in lk.sides or lk.source == "curated" else 1,  # the child's own column
            lk.parent,
        )

    return {child: min(ls, key=rank) for child, ls in cands.items()}


def check_cycles(primary: dict[str, Link]) -> list[list[str]]:
    """Cycles of the primary tree (each as the keys around it)."""
    found, state = [], {}
    for start in primary:
        path, k = [], start
        while k in primary and state.get(k) is None:
            state[k] = start
            path.append(k)
            k = primary[k].parent
        if state.get(k) == start and k in path:
            found.append(path[path.index(k) :])
        for p in path:
            state[p] = "done"
    return found


def run_genealogy(cfg: dict[str, Any], log: Log = print) -> Path:
    gc = cfg["genealogy"]
    proc, art = resolve_path(cfg, "data_processed"), resolve_path(cfg, "artifacts")
    raw = resolve_path(cfg, "data_raw") / "geo"
    out = art / "genealogy"
    t0 = time.perf_counter()
    tipnr_path = raw / Path(cfg["sources"]["tipnr"]["files"][0]).name
    if not tipnr_path.exists():
        raise FileNotFoundError(f"{tipnr_path} is missing: run `bsim download --only geo`")

    verses = pd.read_parquet(
        proc / "verses.parquet", columns=["verse_id", "book_id", "chapter", "verse"]
    )
    vid_of = {
        (int(b), int(c), int(v)): int(i)
        for i, b, c, v in zip(
            verses.verse_id, verses.book_id, verses.chapter, verses.verse, strict=True
        )
    }
    english = English(vid_of, {b.book_id: b.osis for b in BOOKS})
    words = pd.read_parquet(
        proc / "words.parquet", columns=["verse_id", "idx", "content_lemmas", "display_idx"]
    )
    vwords = verse_words(words)
    records = read_tipnr(tipnr_path)
    shift = int(gc["max_shift"])

    # who: TIPNR's persons with a Hebrew name in the Hebrew Bible
    persons: dict[str, Person] = {}
    unmatched = 0
    for r in records:
        fam = r.family
        if fam is None or not any(n.eng_refs for n in r.names):
            continue
        named = [n for n in r.names if n.kind != "Mentioned" and n.hebrew.strip(". ")]
        verses_of, miss = person_verses(r, english, vwords, shift)
        if not verses_of:
            continue
        unmatched += miss
        kind = "group" if fam.type == "Group" else ("person" if named else "anon")
        p = Person(
            r.uid, consonantal(named[0].hebrew) if named else "",
            {"Male": "m", "Female": "f"}.get(fam.type), kind, fam.tribe,
            {n.strong for n in named}, verses_of,
            [o.uid for o in fam.offspring if "f" in o.marker],
        )  # fmt: skip
        persons[r.uid] = p
    links = family_links(records, set(persons))

    # the review
    blocks = {
        b: (verse_of_ref(str(lo), vid_of), verse_of_ref(str(hi), vid_of))
        for b, (lo, hi) in (gc.get("blocks") or {}).items()
        if _in_corpus(str(lo), vid_of) and _in_corpus(str(hi), vid_of)
    }
    docs = read_curation(resolve_path(cfg, "curation") / "genealogy")
    cross = frozenset(str(b) for b in gc.get("cross_blocks") or [])
    conflicts, block_rows, identities = apply_curation(docs, persons, links, blocks, vid_of, cross)

    # the tree: one primary parent each, the rest attached to their tribe
    primary = choose_primary(links)
    cycles = check_cycles(primary)
    if cycles:
        raise RuntimeError(f"the tree has cycles: {cycles[:5]}")
    # a merged key in the config names the person it was merged into
    merged_into = {k: i["persons"][0] for i in identities if i["status"] == "merged"
                   for k in i["keys"]}  # fmt: skip
    root = merged_into.get(str(gc["root"]), str(gc["root"]))
    if root not in persons:
        raise RuntimeError(f"genealogy.root {root!r} is no person")
    tribes = {str(k): merged_into.get(str(v), str(v)) for k, v in (gc.get("tribes") or {}).items()}
    bad = sorted(v for v in tribes.values() if v not in persons)
    if bad:
        raise RuntimeError(f"genealogy.tribes names unknown persons: {bad}")

    def ancestors(k: str) -> set[str]:
        seen = set()
        while k in primary and k not in seen:
            seen.add(k)
            k = primary[k].parent
        return seen | {k}

    # who married in: a spouse, or a parent only of children drawn under the other parent
    partners: dict[str, set[str]] = defaultdict(set)
    drawn_parent: set[str] = set()
    for lk in links.values():
        if lk.status == "rejected":
            continue
        if lk.role == "spouse":
            partners[lk.parent].add(lk.child)
            partners[lk.child].add(lk.parent)
        elif lk.role in PARENT_ROLES and primary.get(lk.child) is lk:
            drawn_parent.add(lk.parent)
    for lk in links.values():
        if (lk.role in PARENT_ROLES and lk.status != "rejected" and lk.kind != "adopted"
                and primary.get(lk.child) is not lk):  # fmt: skip
            partners[lk.parent].add(primary[lk.child].parent)  # the parent the child is drawn under
    placement = {k: "tree" for k in primary}
    placement[root] = "root"
    persons[UNATTACHED] = Person(UNATTACHED, "", None, "virtual")
    book_node: dict[str, int] = {}

    def hang(k: str) -> None:
        """Attach a person without a parent: to the eponym of its tribe, else under unattached."""
        label = persons[k].tribe
        eponym = tribes.get(label.replace("(?)", "").strip())
        if eponym is not None and eponym != k and k not in ancestors(eponym):
            lk = Link(eponym, k, "unstated", "unstated", doubt="(?)" in label, source="tribe")
            placement[k] = "tribe"
        else:
            # under "unattached", by the book that first names them
            book = english.book_at.get(min(persons[k].verses), 0) if persons[k].verses else 0
            node = f"virtual:book:{book}"
            if node not in persons:
                persons[node] = Person(node, "", None, "virtual")
                book_node[node] = book
                links[(UNATTACHED, node, "unstated")] = primary[node] = Link(
                    UNATTACHED, node, "unstated", "unstated", source="tribe"
                )
                placement[node] = "virtual"
            lk = Link(node, k, "unstated", "unstated", source="tribe")
            placement[k] = "unattached"
        links[(lk.parent, lk.child, lk.role)] = lk
        primary[k] = lk

    loose = [k for k in sorted(persons) if k not in primary and k not in (root, UNATTACHED)]
    married = [k for k in loose if partners[k] and k not in drawn_parent]
    for k in loose:
        if k not in married:
            hang(k)
    # a couple neither of whom has a parent: the husband is placed, the wife beside him
    for k in sorted(married, key=lambda k: (persons[k].sex == "f", k)):
        if any(x in placement and placement[x] != "spouse" for x in partners[k]):
            placement[k] = "spouse"  # drawn beside the spouse, not as a node of its own
        else:
            hang(k)
    placement[UNATTACHED] = "virtual"

    # numbered in canon order of first verse (TIPNR's names are join keys, never shown)
    def first(p: Person) -> int:
        return min(p.verses) if p.verses else 10**9

    order = sorted(persons.values(), key=lambda p: (p.kind == "virtual", book_node.get(p.key, -1),
                                                    first(p), p.key))  # fmt: skip
    pid = {p.key: i + 1 for i, p in enumerate(order)}

    # proof verses
    weights = {str(k): int(v) for k, v in gc["cues"].items()}
    span, k_keep = int(gc["construct_span"]), int(gc["proof_k"])
    near = int(gc["near_verses"])
    link_rows, proof_rows = [], []
    best_cue: Counter[str] = Counter()
    ranked = sorted(links.values(), key=lambda lk: (pid[lk.child], lk.role, pid[lk.parent]))
    for i, lk in enumerate(ranked, start=1):
        a, b = persons[lk.parent], persons[lk.child]
        cands: list[tuple[int, str, list[int]]] = []
        if lk.role in (*PARENT_ROLES, "spouse"):
            cands = rank_proofs(lk, a, b, vwords, weights, span, near)
        source = "auto"
        if lk.proof is not None:
            ws_of = {v: vwords.get(v, []) for v in lk.proof}
            got = []
            for v in lk.proof:
                ps = a.verses.get(v) or name_tokens(ws_of[v], a.strongs)
                cs = b.verses.get(v) or name_tokens(ws_of[v], b.strongs)
                got.append((v, cue(ws_of[v], ps, cs, lk.role, span)[0], sorted({*ps, *cs})))
            cands, source = got, "curated"
        for rank, (v, c, toks) in enumerate(cands[:k_keep] if source == "auto" else cands):
            proof_rows.append({"link_id": i, "rank": rank + 1, "verse_id": v, "cue": c,
                               "tokens": json.dumps(display_tokens(vwords.get(v, []), toks)),
                               "source": source})  # fmt: skip
        top = cands[0][1] if cands else None
        if lk.role in PARENT_ROLES:
            best_cue[top or "unproved"] += 1
        link_rows.append({
            "link_id": i, "parent_id": pid[lk.parent], "child_id": pid[lk.child],
            "role": lk.role, "kind": lk.kind, "drawn": primary.get(lk.child) is lk,
            "doubt": lk.doubt, "marker": lk.marker, "status": lk.status, "source": lk.source,
            "block": lk.block, "conflict_id": lk.conflict, "seq": lk.order,
            "n_candidates": len(cands), "cue": top,
        })  # fmt: skip
    links_df = pd.DataFrame(link_rows)
    links_df = links_df.astype({"conflict_id": "Int64", "seq": "Int64"})
    for c in ("block", "cue"):
        links_df[c] = links_df[c].astype(object)
    link_id = {(lk.parent, lk.child, lk.role): i + 1 for i, lk in enumerate(ranked)}

    reviewed = defaultdict(lambda: True)
    for lk in links.values():
        if lk.role in PARENT_ROLES and lk.status == "tipnr":
            reviewed[lk.child] = False
    persons_df = pd.DataFrame([{
        "person_id": pid[p.key], "key": p.key, "he": p.he, "sex": p.sex, "kind": p.kind,
        "tribe": p.tribe or None, "first_vid": min(p.verses) if p.verses else None,
        "n_verses": len(p.verses), "reviewed": bool(reviewed[p.key]) and p.kind != "virtual",
        "placement": placement[p.key], "book_id": book_node.get(p.key),
        "founded": json.dumps(p.founded),
    } for p in order])  # fmt: skip
    persons_df = persons_df.astype({"first_vid": "Int64", "book_id": "Int64"})
    for c in ("sex", "tribe"):
        persons_df[c] = persons_df[c].astype(object)
    conflicts_df = pd.DataFrame(
        [{"conflict_id": c["conflict_id"], "kind": c["kind"], "child_id": pid[c["child"]],
          "block": c["block"],
          "readings": json.dumps([link_id[(lk.parent, lk.child, lk.role)] for lk in c["readings"]]),
          "note_en": c["note_en"], "note_he": c["note_he"]} for c in conflicts],
        columns=["conflict_id", "kind", "child_id", "block", "readings", "note_en", "note_he"],
    )  # fmt: skip
    for c in ("note_en", "note_he"):
        conflicts_df[c] = conflicts_df[c].astype(object)

    def named_at(v: int, who: list[str]) -> dict[str, Any]:
        ws = vwords.get(v, [])
        toks = {t for k in who for t in persons[k].verses.get(v) or []}
        toks |= {t for k in who if not persons[k].verses.get(v)
                 for t in name_tokens(ws, persons[k].strongs)}  # fmt: skip
        return {"verse_id": v, "tokens": display_tokens(ws, sorted(toks))}

    ident_rows = []
    for ident in identities:
        one, *others = ident["persons"]
        for other in others if ident["status"] == "possible" else [None]:
            who = [one] if other is None else [one, other]
            ident_rows.append({
                "identity_id": len(ident_rows) + 1, "status": ident["status"],
                "person_id": pid[one], "other_id": None if other is None else pid[other],
                "keys": json.dumps(ident["keys"], ensure_ascii=False),
                "proofs": json.dumps([named_at(v, who) for v in ident["proof"]]),
                "block": ident["block"], "note_en": ident["note_en"], "note_he": ident["note_he"],
            })  # fmt: skip
    identities_df = pd.DataFrame(
        ident_rows,
        columns=["identity_id", "status", "person_id", "other_id", "keys", "proofs", "block",
                 "note_en", "note_he"],
    ).astype({"other_id": "Int64"})  # fmt: skip
    for c in ("note_en", "note_he"):
        identities_df[c] = identities_df[c].astype(object)
    done = {r["block"]: r for r in block_rows}
    blocks_df = pd.DataFrame(
        [done.get(b, {"block": b, "first_vid": lo, "last_vid": hi, "status": "todo",
                      "n_links": 0, "n_conflicts": 0, "n_missed": 0, "file": None})
         for b, (lo, hi) in blocks.items()],
        columns=["block", "first_vid", "last_vid", "status", "n_links", "n_conflicts",
                 "n_missed", "file"],
    )  # fmt: skip
    blocks_df["file"] = blocks_df["file"].astype(object)
    proofs_df = pd.DataFrame(
        proof_rows, columns=["link_id", "rank", "verse_id", "cue", "tokens", "source"]
    )

    out.mkdir(parents=True, exist_ok=True)
    persons_df.to_parquet(out / "persons.parquet")
    links_df.to_parquet(out / "links.parquet")
    proofs_df.to_parquet(out / "proofs.parquet")
    conflicts_df.to_parquet(out / "conflicts.parquet")
    identities_df.to_parquet(out / "identities.parquet")
    blocks_df.to_parquet(out / "blocks.parquet")
    parent = links_df[links_df.role.isin(PARENT_ROLES) & (links_df.status != "rejected")]
    meta = {
        "config_hash": config_hash(cfg, "genealogy", "sources.tipnr"),
        "built_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "persons": int((persons_df.kind != "virtual").sum()),
        "kinds": {k: int((persons_df.kind == k).sum()) for k in PERSON_KINDS[:3]},
        "links": {r: int((links_df.role == r).sum()) for r in ROLES},
        "parent_links": len(parent),
        "proved": int((parent.cue.notna() & (parent.cue != "nearby")).sum()),
        "best_cue": {k: int(best_cue.get(k, 0)) for k in (*weights, "unproved")},
        "descendant_links": int((parent.kind == "descendant").sum()),
        "doubtful_links": int(parent.doubt.sum()),
        "placement": {
            k: int((persons_df.placement == k).sum())
            for k in ("root", "tree", "tribe", "spouse", "unattached")
        },
        "unmatched_refs": unmatched,
        "conflicts": {k: int((conflicts_df.kind == k).sum()) for k in CONFLICT_KINDS},
        "identities": {k: int((identities_df.status == k).sum()) for k in IDENTITY_STATUSES},
        "reviewed_links": int((parent.status.isin([*STATUSES, "reading"])).sum()),
        "blocks": {s: int((blocks_df.status == s).sum()) for s in ("todo", "draft", "reviewed")},
        "seconds": round(time.perf_counter() - t0, 1),
    }
    (out / "genealogy.meta.json").write_text(
        json.dumps(meta, indent=2, ensure_ascii=False), "utf-8"
    )
    log(
        f"done: {meta['persons']:,} people ({meta['kinds']}); {meta['parent_links']:,} parent"
        f" links, {meta['proved']:,} with a verse naming both (best cue {meta['best_cue']});"
        f" placed {meta['placement']}; {meta['reviewed_links']:,} reviewed,"
        f" {sum(meta['conflicts'].values())} conflicts, identities {meta['identities']}"
        f" ({meta['seconds']} s) -> {out}"
    )
    return out


def _in_corpus(ref: str, vid_of: dict[tuple[int, int, int], int]) -> bool:
    try:
        verse_of_ref(ref, vid_of)
    except ValueError:
        return False
    return True


# --- the review sheet ----------------------------------------------------------------------


def run_genealogy_review(cfg: dict[str, Any], block: str, log: Log = print) -> Path:
    """`review/<block>.md`: every link whose best verse is in the block (or, unproved, whose
    child is first named there), the people first named there without a parent, and the cue
    verses of the block no link uses as proof."""
    gc = cfg["genealogy"]
    if block not in (gc.get("blocks") or {}):
        raise RuntimeError(f"unknown block {block!r}: one of {list(gc.get('blocks') or {})}")
    proc, art = resolve_path(cfg, "data_processed"), resolve_path(cfg, "artifacts")
    folder = art / "genealogy"
    if not (folder / "links.parquet").exists():
        raise RuntimeError("run `bsim genealogy` first")
    verses = pd.read_parquet(
        proc / "verses.parquet",
        columns=["verse_id", "book_id", "chapter", "verse", "ref", "display_tokens"],
    )
    vid_of = {
        (int(b), int(c), int(v)): int(i)
        for i, b, c, v in zip(
            verses.verse_id, verses.book_id, verses.chapter, verses.verse, strict=True
        )
    }
    lo_ref, hi_ref = gc["blocks"][block]
    lo, hi = verse_of_ref(str(lo_ref), vid_of), verse_of_ref(str(hi_ref), vid_of)
    ref = dict(zip(verses.verse_id, verses.ref, strict=True))
    toks = dict(zip(verses.verse_id, verses.display_tokens, strict=True))
    persons = pd.read_parquet(folder / "persons.parquet").set_index("person_id")
    links = pd.read_parquet(folder / "links.parquet")
    proofs = pd.read_parquet(folder / "proofs.parquet")
    conflicts = pd.read_parquet(folder / "conflicts.parquet")
    docs = read_curation(resolve_path(cfg, "curation") / "genealogy")
    missed = missed_refs(docs, vid_of)

    def who(i: int) -> str:
        p = persons.loc[i]
        name = p.he or "(unnamed)"
        return f"{name} `{p.key}`"

    def marked(v: int, tokens: list[int]) -> str:
        ws = list(toks[v])
        for t in tokens:
            if 0 <= t < len(ws):
                ws[t] = f"«{ws[t]}»"
        return " ".join(ws)

    best = proofs[proofs["rank"] == 1].set_index("link_id")
    rows = []
    for lk in links.itertuples():
        if lk.role not in (*PARENT_ROLES, "spouse", "unstated"):
            continue
        if lk.link_id in best.index:
            v = int(best.loc[lk.link_id].verse_id)
        else:
            fv = persons.loc[lk.child_id].first_vid
            v = int(fv) if pd.notna(fv) else -1
        if lo <= v <= hi:
            rows.append((v, lk))
    rows.sort(key=lambda x: (x[0], x[1].child_id, x[1].role))
    lines = [f"# Review sheet: {block} ({ref[lo]} – {ref[hi]})", "",
             "Each link with its best verse in the block; `child <- parent` lines for the "
             "review file. Names are marked «» in the verses.", ""]  # fmt: skip
    lines += [f"## Links ({len(rows)})", ""]
    for _, lk in rows:
        flags = [x for x in (lk.kind if lk.kind != "son" else "", "doubt" if lk.doubt else "",
                             f"status {lk.status}" if lk.status != "tipnr" else "",
                             "drawn" if lk.drawn else "cross-link") if x]  # fmt: skip
        pk, ck = persons.loc[lk.parent_id].key, persons.loc[lk.child_id].key
        lines.append(f"- **{lk.role}**: {who(lk.child_id)} <- {who(lk.parent_id)}"
                     f" ({', '.join(flags)})")  # fmt: skip
        lines.append(f"  - `{ck} <- {pk}`")
        ps = proofs[proofs.link_id == lk.link_id]
        if ps.empty:
            lines.append("  - no verse names both")
        for p in ps.itertuples():
            lines.append(
                f"  - {ref[p.verse_id]} [{p.cue}]: {marked(p.verse_id, json.loads(p.tokens))}"
            )
    first = persons[(persons.first_vid >= lo) & (persons.first_vid <= hi)]
    tree = links[links.drawn & links.role.isin(PARENT_ROLES)]
    roots = first[~first.index.isin(tree.child_id)]
    lines += ["", f"## First named here without a parent link ({len(roots)})", ""]
    for i, p in roots.iterrows():
        att = links[(links.child_id == i) & (links.role == "unstated")]
        to = who(int(att.parent_id.iloc[0])) if len(att) else "-"
        lines.append(f"- {who(i)} ({p.kind}, tribe {p.tribe or '-'}) attached to {to}"
                     f" at {ref.get(p.first_vid, '?')}")  # fmt: skip
    used = set(proofs.verse_id)
    words = pd.read_parquet(
        proc / "words.parquet",
        columns=["verse_id", "idx", "content_lemmas", "morph", "display_idx"],
    )
    words = words[(words.verse_id >= lo) & (words.verse_id <= hi)]
    vw = verse_words(words)
    name_at = {
        (int(v), int(i))
        for v, i, m in zip(words.verse_id, words.idx, words.morph, strict=True)
        if isinstance(m, str) and "Np" in m
    }
    cue_verses = []
    for v, ws in sorted(vw.items()):
        if v in used or v in missed:
            continue
        names = [w.idx for w in ws if (v, w.idx) in name_at]
        son = [w.idx for w in ws if w.content & SON]
        beget = any(w.content & BEGET for w in ws)
        if (any(abs(s - n) == 1 for s in son for n in names) or beget) and len(names) >= 2:
            cue_verses.append((v, names))
    lines += ["", f"## Cue verses no link uses ({len(cue_verses)})", "",
              "בן / בת next to a name, or ילד, with two names or more; list the ones that are "
              "no link under `missed` with a reason.", ""]  # fmt: skip
    for v, names in cue_verses:
        disp = display_tokens(vw[v], names)
        lines.append(f"- {ref[v]}: {marked(v, disp)}")
    here = conflicts[conflicts.block == block]
    lines += ["", f"## Conflicts recorded ({len(here)})", ""]
    for c in here.itertuples():
        lines.append(f"- {c.kind}: {who(c.child_id)}, readings {c.readings}")
    # the identities of the people first named here (a merged person under its first key)
    ids_path = folder / "identities.parquet"
    idents = pd.read_parquet(ids_path) if ids_path.exists() else pd.DataFrame()
    if len(idents):
        idents = idents[idents.person_id.isin(first.index) | idents.other_id.isin(first.index)]
    lines += ["", f"## Identities recorded ({len(idents)})", ""]
    for x in idents.itertuples():
        other = f" ~ {who(int(x.other_id))}" if pd.notna(x.other_id) else ""
        keys = ", ".join(json.loads(x.keys))
        lines.append(f"- {x.status}: {who(x.person_id)}{other}, keys {keys}")
    path = folder / "review" / f"{block}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", "utf-8")
    log(f"{len(rows)} links, {len(roots)} without a parent, {len(cue_verses)} cue verses unused"
        f" -> {path}")  # fmt: skip
    return path
