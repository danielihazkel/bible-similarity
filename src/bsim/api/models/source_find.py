"""Models of `api/routes/source_find.py` (DESIGN.md §10, §11.1)."""

from __future__ import annotations

from bsim.api.models.common import ApiModel, Verse


class SourceExample(ApiModel):
    key: str  # its name in the viewer's catalog
    text: str


class SourceExamples(ApiModel):
    max_chars: int
    examples: list[SourceExample]


class SourceQuery(ApiModel):
    text: str


class SourceVerse(ApiModel):
    verse: Verse
    tokens: list[int]  # the verse's display tokens matched
    text_tokens: list[int]  # the text's tokens they matched


class SourcePassage(ApiModel):
    first: int  # the text's tokens the passage spans, inclusive
    last: int
    score: float  # the matched words' log(N / df), less mismatches and gaps
    matched: int  # words matched
    verses: list[SourceVerse]  # one per verse, in order (several: verses quoted one after another)
    alternatives: list[Verse]  # other verses with the same words as well (a one-verse passage)


class SourceResponse(ApiModel):
    tokens: list[str]  # the text, split as the verses' display tokens are
    passages: list[SourcePassage]  # in the text's order
