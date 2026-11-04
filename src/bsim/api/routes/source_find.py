"""The source finder (DESIGN.md §11.1, D131): the biblical phrases of a pasted Hebrew text, each
with its verses (`api/source_find.py`)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from bsim.api import queries
from bsim.api.models.source_find import (
    SourceExample,
    SourceExamples,
    SourcePassage,
    SourceQuery,
    SourceResponse,
    SourceVerse,
)
from bsim.api.routes._common import Conn, State
from bsim.api.source_find import Normaliser, index_for, source_find
from bsim.text.normalize import consonantal

router = APIRouter()


@router.get("/source-find/examples", response_model=SourceExamples)
def source_examples(state: State) -> dict[str, Any]:
    """The texts the viewer offers to try, and the longest text taken."""
    sf = state.cfg["source_find"]
    return {
        "max_chars": int(sf["max_chars"]),
        "examples": [SourceExample(key=e["key"], text=e["text"]) for e in sf.get("examples") or []],
    }


@router.post("/source-find", response_model=SourceResponse)
def source_find_route(body: SourceQuery, state: State, conn: Conn) -> dict[str, Any]:
    """The text's biblical phrases, each with its verses and the words matched (422: the text is
    longer than `source_find.max_chars`)."""
    sf = state.cfg["source_find"]
    if len(body.text) > int(sf["max_chars"]):
        raise HTTPException(
            status_code=422,
            detail={"code": "too_long", "max_chars": int(sf["max_chars"]),
                    "message": f"the text is longer than {sf['max_chars']} characters"},
        )  # fmt: skip
    norm = Normaliser(sf)

    def texts() -> list[str]:
        return [t for (t,) in conn.execute("SELECT text_plain FROM verses ORDER BY verse_id")]

    index = index_for(state.db_path, texts, norm)
    tokens, at, found = source_find(body.text, index, norm, sf)
    ids = {h.verse_id for p in found for h in p.hits} | {
        a for p in found for h in p.hits for a in h.alternatives
    }
    verses = queries.verses_by_id(conn, sorted(ids))

    def lettered(vid: int) -> list[int]:  # the display tokens with letters: the index's words
        return [i for i, t in enumerate(verses[vid]["display_tokens"]) if consonantal(t)]

    out = []
    for p in found:
        out.append(SourcePassage(
            first=at[p.q_first], last=at[p.q_last], score=round(p.score, 2), matched=p.matched,
            verses=[SourceVerse(verse=verses[h.verse_id],
                                tokens=[lettered(h.verse_id)[i] for i in h.v_pos],
                                text_tokens=[at[i] for i in h.q_pos]) for h in p.hits],
            alternatives=[verses[a] for h in p.hits for a in h.alternatives],
        ))  # fmt: skip
    return {"tokens": tokens, "passages": out}
