"""Who speaks where: narration, direct speech and its speakers per chapter and book (DESIGN.md
§16.26).

From the BHSA clauses of `bsim syntax` (`data/bhsa.py`), every OSHB word takes its clause's text
type (`txt`'s last letter: N narration, Q quotation, D discourse; anything else unknown) and, in a
quotation, its speaker. Per chapter and per book, shares of words:
    narration, speech, discourse      by text type (they and the unknown rest sum to 1)
    divine                            speech whose speaker is one of `syntax.divine` (יהוה, ...)
    attributed                        speech with any speaker found
and per book the speakers with their words (`n_explicit`: from the introduction's own subject,
the rest carried from an earlier clause). Built by `bsim build-db` (cheap; no stage of its own).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from bsim.data.lexicon import strong_key

SHARES = ("narration", "speech", "discourse", "divine", "attributed")


def word_types(clauses: pd.DataFrame) -> pd.DataFrame:
    """`verse_id, idx, ttype, speaker, explicit` per OSHB word (a word split over clauses keeps
    its last clause)."""
    c = (
        clauses.assign(ttype=clauses.txt.str[-1].fillna(""))
        .explode("words")
        .dropna(subset=["words"])
    )
    c = c.assign(idx=c.words.astype(int), explicit=c.speaker_source == "explicit")
    c = c.drop_duplicates(["verse_id", "idx"], keep="last")
    return c[["verse_id", "idx", "ttype", "speaker", "explicit"]].reset_index(drop=True)


def _shares(w: pd.DataFrame, keys: list[str]) -> pd.DataFrame:
    g = w.assign(
        narration=w.ttype == "N",
        speech=w.ttype == "Q",
        discourse=w.ttype == "D",
        attributed=(w.ttype == "Q") & w.speaker.notna(),
    ).groupby(keys)
    out = g[list(SHARES)].mean().round(4)
    return out.assign(n_words=g.size()).reset_index()


def speech_tables(
    clauses: pd.DataFrame, verses: pd.DataFrame, divine: list[str]
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """(chapters, books, speakers): see the module docstring."""
    w = word_types(clauses).merge(
        verses[["verse_id", "book_id", "chapter"]], on="verse_id", how="left"
    )
    gods = set(divine)
    w["divine"] = (w.ttype == "Q") & w.speaker.map(
        lambda s: isinstance(s, str) and strong_key(s) in gods
    )
    chapters = _shares(w, ["book_id", "chapter"])
    chapters.insert(
        0,
        "unit_id",
        [f"c:{b}:{c}" for b, c in zip(chapters.book_id, chapters.chapter, strict=True)],
    )
    books = _shares(w, ["book_id"])
    sp = w[(w.ttype == "Q") & w.speaker.notna()]
    speakers = (
        sp.groupby(["book_id", "speaker"])
        .agg(n_words=("idx", "size"), n_explicit=("explicit", "sum"))
        .reset_index()
        .rename(columns={"speaker": "lemma"})
        .astype({"n_explicit": np.int64})
        .sort_values(["book_id", "n_words"], ascending=[True, False], ignore_index=True)
    )
    return chapters, books, speakers
