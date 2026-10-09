"""`/api` endpoints (DESIGN.md §10), one router per feature. Bad parameters -> 422, unknown
ids -> 404."""

from fastapi import APIRouter

from bsim.api.routes import (
    borrowing,
    core,
    corpus,
    dating,
    domains,
    dossier,
    export,
    labels,
    parallels,
    phrases,
    poetics,
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
    dossier,
    export,
):
    router.include_router(_module.router)
