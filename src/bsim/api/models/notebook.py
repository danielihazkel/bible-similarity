"""Response models of `api/routes/notebook.py` (DESIGN.md §10)."""

from __future__ import annotations

from pydantic import BaseModel

from bsim.api.models.common import ApiModel, UnitSummary, Verse


class NotebookEntry(ApiModel):
    """A unit you kept, with your note (DESIGN.md §16.47)."""

    unit: UnitSummary
    note: str
    collections: list[int]  # collection ids
    created_at: str
    updated_at: str
    verse: Verse | None  # the text, for a verse


class NotebookCollection(ApiModel):
    collection_id: int
    name: str
    description: str
    n_entries: int  # entries of the current build (an older build's units are left out)
    created_at: str
    updated_at: str


class NotebookResponse(ApiModel):
    writable: bool  # serve.labels_writable: the notebook shares the labels file
    entries: list[NotebookEntry]  # canon order
    collections: list[NotebookCollection]  # by name
    hidden: int  # entries whose unit this build lacks (kept in the file, not shown)


class NoteIn(BaseModel):
    """The note of an entry (PUT /notebook/entries/{unit_id}); null keeps the note it has."""

    note: str | None = None


class CollectionIn(BaseModel):
    name: str
    description: str = ""
