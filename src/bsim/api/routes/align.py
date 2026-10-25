"""Why two verses are alike in meaning (DESIGN.md §16.73): their words linked through the final
semantic encoder's token vectors (`api/align.py`), for Compare."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from bsim.api import queries
from bsim.api.align import align_verses, verse_words
from bsim.api.models.align import AlignResponse, WordLink
from bsim.api.routes._common import Conn, State, verse_or_404
from bsim.api.search import EncoderLoading, EncoderUnavailable, token_encoder

router = APIRouter()


@router.get("/align", response_model=AlignResponse)
def align(a: int, b: int, state: State, conn: Conn) -> dict[str, Any]:
    """The word links between verses a and b (503 while the encoder loads, or without one)."""
    verse_or_404(state, a)
    verse_or_404(state, b)
    ac = state.cfg["serve"]["align"]
    key = (a, b)
    cached = state.align_cache.get(key)
    if cached is not None:
        return cached
    rows = queries.words(conn, [a, b], detail=True)
    rows_a = [r for r in rows if r["verse_id"] == a]
    rows_b = [r for r in rows if r["verse_id"] == b]
    try:
        links = align_verses(rows_a, rows_b, token_encoder(state.encoder), float(ac["min_cos"]),
                             {str(x) for x in ac["stop"]})  # fmt: skip
    except EncoderLoading as e:
        retry = str(state.cfg["serve"]["encoder_retry_s"])
        raise HTTPException(status_code=503, detail=str(e), headers={"Retry-After": retry}) from e
    except EncoderUnavailable as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    fa, fb = verse_words(rows_a).text.split(" "), verse_words(rows_b).text.split(" ")
    out = {
        "a": a,
        "b": b,
        "encoder": state.meta.get("semantic_encoder"),
        "min_cos": float(ac["min_cos"]),
        "links": [
            WordLink(a_display=x["a_display"], b_display=x["b_display"], a_form=fa[x["a_word"]],
                     b_form=fb[x["b_word"]], cos=x["cos"], same_lemma=x["same_lemma"])  # fmt: skip
            for x in links
        ],
    }
    state.align_cache.put(key, out)
    return out
