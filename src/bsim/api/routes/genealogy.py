"""The family tree (DESIGN.md §16.63): the drawn tree compact, one person's family with the
verses that state each link, and people by name."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from bsim.api import queries
from bsim.api.models.genealogy import (
    ChildGroup,
    Conflict,
    CrossLink,
    FamilyLink,
    PersonDetail,
    PersonInfo,
    PersonLookup,
    PersonMatch,
    PersonRef,
    ProofVerse,
    SkeletonResponse,
    TreeNode,
    TreeSpouse,
)
from bsim.api.routes._common import Conn, State, unprocessable

router = APIRouter()

PARENT_ROLES = ("father", "mother")


@router.get("/genealogy/skeleton", response_model=SkeletonResponse)
def skeleton(state: State, conn: Conn) -> dict[str, Any]:
    """Every person drawn as a node, with the link it hangs by; the people drawn beside a spouse;
    the parent links not drawn. The viewer lays out what is expanded."""
    nodes = queries.genealogy_nodes(conn)
    mothers = queries.genealogy_mothers(conn)
    spouses, beside = queries.genealogy_beside(conn)
    return {
        "meta": state.meta.get("genealogy") or {},
        "nodes": [
            TreeNode(
                **{
                    k: r[k]
                    for k in (
                        "person_id",
                        "he",
                        "sex",
                        "kind",
                        "placement",
                        "parent",
                        "role",
                        "link_kind",
                        "seq",
                        "book_id",
                    )
                },
                mother=mothers.get(r["person_id"]) if r["role"] == "father" else None,
                reviewed=bool(r["reviewed"]),
                doubt=bool(r["doubt"]),
                conflict=bool(r["conflict"]),
                spouses=beside.get(r["person_id"], []),
            )  # fmt: skip
            for r in nodes
        ],
        "spouses": [TreeSpouse(**r | {"reviewed": bool(r["reviewed"])}) for r in spouses],
        "cross": [CrossLink(**r) for r in queries.genealogy_cross(conn)],
    }


@router.get("/genealogy/lookup", response_model=PersonLookup)
def lookup(q: str, conn: Conn, limit: int = 8) -> dict[str, Any]:
    """People by a Hebrew name (pointing ignored), whole names first, the most named first, each
    with the parent, tribe or spouse that tells namesakes apart."""
    if not 1 <= limit <= 50:
        raise unprocessable("limit must be between 1 and 50")
    rows = queries.genealogy_lookup(conn, q, limit)
    labels = queries.verse_labels(
        conn, [r["first_vid"] for r in rows if r["first_vid"] is not None]
    )
    return {
        "query": q,
        "items": [
            PersonMatch(
                **r,
                first_label=labels.get(r["first_vid"], (None, None))[0],
                first_label_he=labels.get(r["first_vid"], (None, None))[1],
            )  # fmt: skip
            for r in rows
        ],
    }


@router.get("/genealogy/person/{person_id}", response_model=PersonDetail)
def person(person_id: int, conn: Conn) -> dict[str, Any]:
    """One person's family: parents, spouses, children by their other parent, siblings, each link
    with its proof verses (both names marked), and the readings where the text disagrees."""
    p = queries.genealogy_person(conn, person_id)
    if p is None:
        raise HTTPException(status_code=404, detail=f"unknown person {person_id}")
    links = queries.genealogy_links_of(conn, person_id)
    up = [lk for lk in links if lk["child_id"] == person_id and lk["role"] in PARENT_ROLES]
    up.sort(key=lambda lk: (not lk["drawn"], PARENT_ROLES.index(lk["role"]), lk["link_id"]))
    attached = next((lk for lk in links if lk["child_id"] == person_id
                     and lk["role"] == "unstated"), None)  # fmt: skip
    wed = [lk for lk in links if lk["role"] == "spouse"]
    down = [lk for lk in links if lk["parent_id"] == person_id and lk["role"] in PARENT_ROLES]
    down.sort(key=lambda lk: (lk["seq"] is None, lk["seq"] or 0, lk["child_id"]))
    hung = [lk["child_id"] for lk in links if lk["parent_id"] == person_id
            and lk["role"] == "unstated"]  # fmt: skip
    conflicts = queries.genealogy_conflicts_of(conn, person_id)
    readings = queries.genealogy_links_by_id(conn, [i for c in conflicts for i in c["readings"]])

    # the children's other parents: a father's children by their mother, and the other way round
    mine = {lk["child_id"]: lk["role"] for lk in down}
    other_of: dict[int, int] = {}
    for lk in queries.genealogy_parent_links(conn, list(mine)):
        if lk["parent_id"] != person_id and lk["role"] != mine[lk["child_id"]]:
            other_of.setdefault(lk["child_id"], lk["parent_id"])
    # siblings: TIPNR's, and the other children of the parents (not of a reading not drawn)
    sibs = [lk["child_id"] if lk["parent_id"] == person_id else lk["parent_id"]
            for lk in links if lk["role"] == "sibling"]  # fmt: skip
    sibs += queries.genealogy_children_of(
        conn, [lk["parent_id"] for lk in up if lk["drawn"] or lk["status"] != "reading"]
    )
    sibs = sorted({s for s in sibs if s != person_id})

    def other(lk: dict[str, Any]) -> int:
        return lk["child_id"] if lk["parent_id"] == person_id else lk["parent_id"]

    every = [*up, *wed, *down, *readings.values(), *([attached] if attached else [])]
    people = queries.genealogy_people(
        conn, [other(lk) for lk in every] + list(other_of.values()) + sibs + hung
    )
    proofs = queries.genealogy_proofs(conn, [lk["link_id"] for lk in every])
    verses = queries.verses_by_id(conn, [v["verse_id"] for ps in proofs.values() for v in ps])

    def ref(i: int) -> PersonRef:
        return PersonRef(**people[i])

    def family(lk: dict[str, Any]) -> FamilyLink:
        return FamilyLink(
            **{k: lk[k] for k in ("link_id", "role", "kind", "marker", "status", "source", "cue",
                                  "n_candidates", "conflict_id")},
            person=ref(other(lk)),
            drawn=bool(lk["drawn"]), doubt=bool(lk["doubt"]),
            proofs=[ProofVerse(verse=verses[v["verse_id"]], tokens=v["tokens"], cue=v["cue"],
                               source=v["source"]) for v in proofs.get(lk["link_id"], [])],
        )  # fmt: skip

    groups: dict[int | None, list[FamilyLink]] = {}
    for lk in down:
        groups.setdefault(other_of.get(lk["child_id"]), []).append(family(lk))
    labels = queries.verse_labels(conn, [p["first_vid"]] if p["first_vid"] is not None else [])
    first = labels.get(p["first_vid"], (None, None))
    return {
        "person": PersonInfo(**p | {"reviewed": bool(p["reviewed"])}),
        "first_label": first[0],
        "first_label_he": first[1],
        "parents": [family(lk) for lk in up],
        "attached": family(attached) if attached else None,
        "spouses": [family(lk) for lk in wed],
        "children": [
            ChildGroup(other=ref(o) if o is not None else None, children=c)
            for o, c in groups.items()
        ],  # fmt: skip
        "siblings": [ref(s) for s in sibs],
        "members": [ref(h) for h in hung],
        "conflicts": [
            Conflict(
                **{k: c[k] for k in ("conflict_id", "kind", "block", "note_en", "note_he")},
                readings=[family(readings[i]) for i in c["readings"] if i in readings],
            )
            for c in conflicts
        ],
    }
