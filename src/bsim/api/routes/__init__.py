"""`/api` endpoints (DESIGN.md §10), one router per feature. Bad parameters -> 422, unknown
ids -> 404."""

from fastapi import APIRouter

from bsim.api.routes import (
    core,
    corpus,
    domains,
    export,
    parallels,
    phrases,
    poetics,
    senses,
)

router = APIRouter(prefix="/api")
for _module in (core, phrases, parallels, poetics, corpus, domains, senses, export):
    router.include_router(_module.router)
