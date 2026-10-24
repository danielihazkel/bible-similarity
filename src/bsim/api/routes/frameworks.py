"""The narrative frameworks (DESIGN.md §16.71): the judges' cycle in each episode, every king's
verdict and regnal slots, and the checks."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from bsim.api import queries
from bsim.api.models.frameworks import Episode, FrameworkKing, FrameworksResponse, SlotHit
from bsim.api.routes._common import Conn, State

router = APIRouter()


@router.get("/frameworks", response_model=FrameworksResponse)
def frameworks(state: State, conn: Conn) -> dict[str, Any]:
    """The episodes with their slots and the kings with their verdicts (404: the stage did not
    run)."""
    m = state.meta.get("frameworks")
    if not m:
        raise HTTPException(status_code=404, detail="the frameworks were not computed")
    episodes = queries.frameworks_episodes(conn)
    slots = queries.frameworks_slots(conn)
    kings = queries.frameworks_kings(conn)
    regnal = list(m["regnal"])
    ids = [e["first_vid"] for e in episodes] + [s["verse_id"] for s in slots]
    ids += [k[c] for k in kings for c in ("verdict_vid", *regnal)]
    verses = queries.verses_by_id(conn, [i for i in ids if i is not None])

    def hit(slot: str, vid: int | None) -> SlotHit:
        v = verses.get(vid) if vid is not None else None
        return SlotHit(slot=slot, verse_id=vid if v else None, ref=v["ref"] if v else None,
                       ref_he=v["ref_he"] if v else None)  # fmt: skip

    found = {(s["episode"], s["slot"]): s["verse_id"] for s in slots}
    keep = ("slots", "open", "rho", "cycle_p", "cycle_holds", "known_cycle", "known_cycle_holds",
            "verdicts", "good", "bad", "within", "within_all", "between", "difference",
            "expected", "verdict_p", "verdict_holds", "known_verdicts", "known_verdicts_holds",
            "regnal", "by_kingdom", "shuffles", "alpha")  # fmt: skip
    return {
        **{k: m[k] for k in keep},
        "episodes": [
            Episode(
                **{k: e[k] for k in ("episode", "judge", "seq", "first_vid", "last_vid",
                                     "n_slots", "share")},  # fmt: skip
                ref=verses[e["first_vid"]]["ref"],
                ref_he=verses[e["first_vid"]]["ref_he"],
                slots=[hit(s, found.get((e["episode"], s))) for s in m["slots"]],
            )
            for e in episodes
            if e["first_vid"] in verses
        ],
        "kings": [
            FrameworkKing(
                **{c: k[c] for c in ("king", "name", "kingdom", "seq", "first_vid", "verdict")},
                verdict_verse=verses.get(k["verdict_vid"]) if k["verdict_vid"] is not None
                else None,
                slots=[hit(s, k[s]) for s in regnal],
            )
            for k in kings
        ],
    }
