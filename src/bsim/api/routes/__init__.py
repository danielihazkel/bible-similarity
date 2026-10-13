"""`/api` endpoints (DESIGN.md §10), one router per feature. Bad parameters -> 422, unknown
ids -> 404."""

from fastapi import APIRouter

from bsim.api.routes import (
    borrowing,
    citations,
    core,
    corpus,
    dating,
    dialogue,
    domains,
    dossier,
    echoes,
    export,
    findings,
    ketiv,
    labels,
    meter,
    mirrors,
    parallels,
    pentateuch,
    phrases,
    poetics,
    psalms,
    reader,
    refrains,
    roots,
    segments,
    senses,
    syntax,
)

router = APIRouter(prefix="/api")
for _module in (
    core,
    phrases,
    parallels,
    poetics,
    corpus,
    domains,
    senses,
    dating,
    syntax,
    borrowing,
    labels,
    segments,
    ketiv,
    citations,
    echoes,
    mirrors,
    meter,
    roots,
    refrains,
    psalms,
    pentateuch,
    dialogue,
    reader,
    dossier,
    findings,
    export,
):
    router.include_router(_module.router)
