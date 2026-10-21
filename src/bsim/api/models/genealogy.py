"""Response models of `api/routes/genealogy.py` (DESIGN.md §10, §16.63)."""

from __future__ import annotations

from typing import Any, Literal

from bsim.api.models.common import ApiModel, Verse

Sex = Literal["m", "f"]
PersonKind = Literal["person", "group", "anon", "virtual"]
Placement = Literal["root", "tree", "tribe", "spouse", "unattached", "virtual"]
TreeRole = Literal["father", "mother", "unstated"]
LinkRole = Literal["father", "mother", "spouse", "sibling", "unstated"]
LinkKind = Literal["son", "descendant", "adopted", "levirate", "founder", "unstated", "spouse",
                   "sibling"]  # fmt: skip
LinkStatus = Literal["tipnr", "confirmed", "fixed", "added", "rejected", "reading"]
Cue = Literal["construct", "sons_of", "wife", "begot", "kin", "together", "nearby"]
ConflictKind = Literal["bible", "descendant"]


class TreeNode(ApiModel):
    """A person drawn as a node of the tree, compact (§16.63)."""

    person_id: int
    he: str  # Hebrew name, consonants ("" for the unnamed and the "unattached" groups)
    sex: Sex | None
    kind: PersonKind
    placement: Placement
    parent: int | None  # the drawn parent; None for a root (Adam, "unattached")
    role: TreeRole | None  # the drawn link's
    link_kind: LinkKind | None
    seq: int | None  # its place among the parent's children (TIPNR's offspring order)
    mother: int | None  # drawn under its father: its mother (the mother headers)
    book_id: int | None  # an "unattached" group: the book that first names its people
    reviewed: bool  # every parent link of it checked (§16.63, the review)
    doubt: bool  # STEPBible's (?) on the drawn link
    conflict: bool  # the text gives it more than one parent
    spouses: list[int]  # the people drawn beside it


class TreeSpouse(ApiModel):
    """A person drawn beside a spouse rather than as a node."""

    person_id: int
    he: str
    sex: Sex | None
    kind: PersonKind
    reviewed: bool


class CrossLink(ApiModel):
    """A parent link the tree does not draw: the other parent, another reading."""

    parent: int
    child: int
    role: Literal["father", "mother"]
    kind: LinkKind


class SkeletonResponse(ApiModel):
    meta: dict[str, Any]  # counts: persons, links, proofs by cue, placement, the review
    nodes: list[TreeNode]  # person_id order (canon order of first verse; the groups last)
    spouses: list[TreeSpouse]
    cross: list[CrossLink]


class PersonRef(ApiModel):
    person_id: int
    he: str
    sex: Sex | None
    kind: PersonKind
    placement: Placement


class ProofVerse(ApiModel):
    verse: Verse
    tokens: list[int]  # display tokens of both names
    cue: Cue | None
    source: Literal["auto", "curated"]


class FamilyLink(ApiModel):
    """One link of the person's, with the person at its other end and its proof verses."""

    link_id: int
    person: PersonRef  # the other end: a parent, spouse or child
    role: LinkRole
    kind: LinkKind
    drawn: bool  # the link the tree draws (else a cross-link)
    doubt: bool
    marker: str  # TIPNR's: "?", "a" (an ancestor), "d" (a descended group)
    status: LinkStatus
    source: Literal["tipnr", "curated", "tribe"]
    cue: Cue | None  # its best proof's cue; None: unproved
    n_candidates: int  # verses naming both
    conflict_id: int | None
    proofs: list[ProofVerse]  # best first; `nearby` is a hint, not proof


class ChildGroup(ApiModel):
    other: PersonRef | None  # the children's other parent (None: not named)
    children: list[FamilyLink]  # the parent's links to them, in the parent's order


class Conflict(ApiModel):
    conflict_id: int
    kind: ConflictKind
    block: str | None
    readings: list[FamilyLink]  # the first is the one the tree draws
    note_en: str | None
    note_he: str | None


class PersonInfo(ApiModel):
    person_id: int
    he: str
    sex: Sex | None
    kind: PersonKind
    placement: Placement
    first_vid: int | None
    n_verses: int
    reviewed: bool
    book_id: int | None


class PersonDetail(ApiModel):
    person: PersonInfo
    first_label: str | None
    first_label_he: str | None
    parents: list[FamilyLink]  # the drawn one first
    attached: FamilyLink | None  # hung on a tribe's eponym or under "unattached": link not stated
    spouses: list[FamilyLink]
    children: list[ChildGroup]  # by the other parent, in the order of their first child
    siblings: list[PersonRef]
    members: list[PersonRef]  # hung on it by a link not stated: its tribe's people, a book's
    conflicts: list[Conflict]


class PersonMatch(ApiModel):
    person_id: int
    he: str
    sex: Sex | None
    kind: PersonKind
    placement: Placement
    first_vid: int | None
    n_verses: int
    exact: bool  # the whole name matched (else a name starts with it)
    relation: Literal["child", "tribe", "spouse"] | None  # what `of_he` is to it
    of_he: str | None  # its drawn parent, its tribe's eponym or its spouse
    first_label: str | None
    first_label_he: str | None


class PersonLookup(ApiModel):
    query: str
    items: list[PersonMatch]  # whole names first, the most named first
