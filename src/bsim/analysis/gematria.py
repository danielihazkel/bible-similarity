"""`bsim gematria`: the letter values of the text's words, lemmas and verses (DESIGN.md §16.53).

Gematria reads a word as the sum of its letters' values (`text/gematria.py`: the standard
values, mispar gadol, ordinal and katan). Here every word form, lemma and verse gets its value in
each system, so the viewer can show what equals what (אליעזר = 318, נחש = משיח = 358). This is
a lookup, not a finding: whether equal values link related words is a separate test.

- **Words** are the MAM display tokens (the text as shown, qere read), consonants only, so a form
  is a written word with its prefixes (והארץ); a maqaf joins nothing (each side is a token).
- **Verses**: the sum of their words, with their letters and words counted.
- **Lemmas**: the content lemmas of the OSHB words, valued by their Strong's headword
  (HebrewStrong.xml, as `bsim roots` reads it); a lemma without one by its commonest form
  (`lemma_gloss.he_lemma`).
- **Known values** (`gematria.known`): traditional equivalences, each text with its standard
  value. They check the tables: the stage stops when one does not hold.

Writes `artifacts/gematria/`: `forms.parquet` (`form`, the four values, `n_words, n_verses`,
`verses`: its first `form_verses` verse ids as JSON), `lemmas.parquet` (`lemma, he, source`, the
four values, `n_words`), `verses.parquet` (`verse_id, book_id`, the four values, `n_letters,
n_words`) and `gematria.meta.json`.
"""

from __future__ import annotations

import json
import time
from collections import Counter, defaultdict
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd

from bsim.config import config_hash, resolve_path
from bsim.data.lexicon import strong_key
from bsim.store.lexicon import lemma_display_forms
from bsim.text.gematria import SYSTEMS, letters, values

Log = Callable[[str], None]


def check_known(known: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Each `{text, value}` with its computed standard value; raises when one differs."""
    out = []
    for k in known:
        got = values(str(k["text"]))["standard"]
        if got != int(k["value"]):
            raise RuntimeError(f"gematria.known: {k['text']} is {got}, not {k['value']}")
        out.append({"text": str(k["text"]), "value": got})
    return out


def headwords(raw: Path) -> dict[str, str]:
    """Strong's number -> its HebrewStrong.xml headword; empty when the file is missing."""
    path = raw / "lexicon" / "HebrewStrong.xml"
    if not path.exists():
        return {}
    from bsim.analysis.roots import read_derivations

    der = read_derivations(path)
    return {s: w for s, w in zip(der.strong, der.word, strict=True) if letters(w)}


def form_table(verses: pd.DataFrame, keep: int) -> pd.DataFrame:
    """Every word form of the display tokens: its values, counts and first verses."""
    n_words: Counter[str] = Counter()
    where: dict[str, list[int]] = defaultdict(list)
    for vid, toks in zip(verses.verse_id, verses.display_tokens, strict=True):
        for t in toks:
            f = letters(t)
            if not f:
                continue
            n_words[f] += 1
            seen = where[f]
            if not seen or seen[-1] != vid:
                seen.append(int(vid))
    rows = [
        {
            "form": f,
            **values(f),
            "n_words": n,
            "n_verses": len(where[f]),
            "verses": json.dumps(where[f][:keep]),
        }
        for f, n in sorted(n_words.items())
    ]
    return pd.DataFrame(rows, columns=["form", *SYSTEMS, "n_words", "n_verses", "verses"])


def verse_table(verses: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for vid, book, toks in zip(verses.verse_id, verses.book_id, verses.display_tokens, strict=True):
        forms = [f for f in (letters(t) for t in toks) if f]
        rows.append(
            {
                "verse_id": int(vid),
                "book_id": int(book),
                **values("".join(forms)),
                "n_letters": sum(len(f) for f in forms),
                "n_words": len(forms),
            }
        )
    return pd.DataFrame(rows, columns=["verse_id", "book_id", *SYSTEMS, "n_letters", "n_words"])


def lemma_table(words: pd.DataFrame, head: dict[str, str]) -> pd.DataFrame:
    """Each content lemma valued by its Strong's headword, else by its commonest form."""
    shown = lemma_display_forms(words)
    rows = []
    for lemma, form, n in zip(shown.lemma, shown.he_lemma, shown.n_words, strict=True):
        he = head.get(strong_key(lemma))
        source = "strong" if he else "form"
        he = he or form
        if letters(he):
            rows.append(
                {"lemma": lemma, "he": he, "source": source, **values(he), "n_words": int(n)}
            )
    return pd.DataFrame(rows, columns=["lemma", "he", "source", *SYSTEMS, "n_words"])


def run_gematria(cfg: dict[str, Any], log: Log = print) -> Path:
    gc = cfg["gematria"]
    proc, art = resolve_path(cfg, "data_processed"), resolve_path(cfg, "artifacts")
    out = art / "gematria"
    t0 = time.perf_counter()
    known = check_known(gc["known"])
    verses = pd.read_parquet(
        proc / "verses.parquet", columns=["verse_id", "book_id", "display_tokens"]
    ).sort_values("verse_id")
    words = pd.read_parquet(
        proc / "words.parquet",
        columns=["verse_id", "idx", "surface", "lemma", "content_lemmas", "morph"],
    )
    forms = form_table(verses, int(gc["form_verses"]))
    vt = verse_table(verses)
    head = headwords(resolve_path(cfg, "data_raw"))
    lemmas = lemma_table(words, head)

    out.mkdir(parents=True, exist_ok=True)
    forms.to_parquet(out / "forms.parquet")
    lemmas.to_parquet(out / "lemmas.parquet")
    vt.to_parquet(out / "verses.parquet")
    meta = {
        "config_hash": config_hash(cfg, "gematria"),
        "built_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "systems": list(SYSTEMS),
        "forms": len(forms),
        "words": int(forms.n_words.sum()),
        "lemmas": len(lemmas),
        "lemmas_by_headword": int((lemmas.source == "strong").sum()),
        "verses": len(vt),
        "known": known,
        "seconds": round(time.perf_counter() - t0, 1),
    }
    (out / "gematria.meta.json").write_text(
        json.dumps(meta, indent=2, ensure_ascii=False), "utf-8"
    )
    log(
        f"done: {meta['forms']:,} word forms ({meta['words']:,} words), {meta['lemmas']:,} lemmas"
        f" ({meta['lemmas_by_headword']:,} by Strong's headword), {meta['verses']:,} verses;"
        f" {len(known)} known values hold ({meta['seconds']} s) -> {out}"
    )
    return out
