"""`bsim build-corpus`: raw sources -> verses / words / units / unit_members (DESIGN.md §2–§4).

Writes to `paths.data_processed`:
    verses.parquet, words.parquet, units.parquet, unit_members.parquet
    corpus_meta.json   config hash + source commit
    corpus_report.md   counts, alignment coverage, pe/samekh comparison, longest verses
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd

from bsim.config import config_hash, resolve_path
from bsim.data.align import align
from bsim.data.canon import BOOKS, TORAH, VERSE_OVERRIDES, Book, oshb_to_mam
from bsim.data.oshb import OshbVerse, parse_book
from bsim.data.report import md_table
from bsim.data.sefaria import MamVerse, load_mam, load_parashiyot
from bsim.data.units import build_units
from bsim.text.normalize import consonantal, display_tokens, match_key

Log = Callable[[str], None]


@dataclass
class BookData:
    book: Book
    mam: list[list[MamVerse]]
    oshb: dict[tuple[int, int], list[OshbVerse]]  # keyed by MAM (chapter, verse)


def load_book(raw: Path, book: Book, kq: str) -> BookData:
    """Parse both sources for one book and re-key OSHB verses to MAM versification."""
    mam = load_mam(raw / "sefaria" / "text" / f"{book.sefaria}.json")
    if len(mam) != book.n_chapters:
        raise RuntimeError(
            f"{book.sefaria}: MAM has {len(mam)} chapters, expected {book.n_chapters}"
        )
    oshb: dict[tuple[int, int], list[OshbVerse]] = defaultdict(list)
    for v in parse_book(raw / "oshb" / f"{book.osis}.xml", kq):
        oshb[oshb_to_mam(book.osis, v.chapter, v.verse)].append(v)
    return BookData(book, mam, dict(oshb))


def check_versification(data: BookData) -> list[str]:
    """Per-chapter verse-count mismatches between MAM and re-keyed OSHB (empty if none)."""
    problems = []
    mam_keys = {(c, v) for c, ch in enumerate(data.mam, 1) for v in range(1, len(ch) + 1)}
    oshb_keys = set(data.oshb)
    for c, ch in enumerate(data.mam, 1):
        n_oshb = sum(1 for k in oshb_keys if k[0] == c)
        if n_oshb != len(ch):
            problems.append(f"{data.book.sefaria} {c}: MAM {len(ch)} verses, OSHB {n_oshb}")
    extra = sorted(oshb_keys - mam_keys)
    if extra:
        problems.append(f"{data.book.sefaria}: OSHB verses with no MAM verse: {extra[:10]}")
    return problems


def build_tables(books: list[BookData]) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Verse and word tables; `verse_id` is the canon-order ordinal."""
    verse_rows: list[dict[str, Any]] = []
    word_rows: list[dict[str, Any]] = []
    for data in books:
        book = data.book
        for c, chapter in enumerate(data.mam, 1):
            for v, mv in enumerate(chapter, 1):
                verse_id = len(verse_rows)
                sources = data.oshb[(c, v)]
                words = [w for src in sources for w in src.words]
                tokens = display_tokens(mv.text_display)
                mapping = align(
                    [match_key(w.surface) for w in words], [match_key(t) for t in tokens]
                )
                oshb_breaks = [b for src in sources for b in src.breaks]
                verse_rows.append(
                    {
                        "verse_id": verse_id,
                        "book_id": book.book_id,
                        "chapter": c,
                        "verse": v,
                        "ref": f"{book.sefaria} {c}:{v}",
                        "osis": f"{book.osis}.{c}.{v}",
                        "oshb_osis": [src.osis for src in sources],
                        "text_display": mv.text_display,
                        "text_plain": consonantal(mv.text_display),
                        "text_model": " ".join(consonantal(w.surface) for w in words),
                        "ketiv_note": mv.ketiv_note,
                        "display_tokens": tokens,
                        "break_after": mv.breaks[-1].kind if mv.breaks else None,
                        "n_mid_breaks": sum(b.mid_verse for b in mv.breaks),
                        "oshb_break": oshb_breaks[-1] if oshb_breaks else None,
                    }
                )
                for idx, (w, d) in enumerate(zip(words, mapping, strict=True)):
                    word_rows.append(
                        {
                            "verse_id": verse_id,
                            "idx": idx,
                            "oshb_id": w.oshb_id,
                            "surface": w.surface,
                            "lemma": w.lemma,
                            "content_lemmas": list(w.content_lemmas),
                            "morph": w.morph,
                            "kq": w.kq,
                            "display_idx": d,
                        }
                    )
    verses = pd.DataFrame(verse_rows)
    words = pd.DataFrame(word_rows)
    words["display_idx"] = words["display_idx"].astype("Int32")
    return verses, words


def check_membership(verses: pd.DataFrame, units: pd.DataFrame, members: pd.DataFrame) -> None:
    """Every verse belongs to exactly one chapter and exactly one pericope."""
    types = members.merge(units[["unit_id", "unit_type"]], on="unit_id")
    for unit_type in ("chapter", "pericope"):
        counts = types[types.unit_type == unit_type].verse_id.value_counts()
        counts = counts.reindex(verses.verse_id, fill_value=0)
        bad = counts[counts != 1]
        if len(bad):
            raise RuntimeError(
                f"{len(bad)} verses not in exactly one {unit_type}: {bad.index[:10].tolist()}"
            )


def check_expected(cfg: dict[str, Any], verses: pd.DataFrame, units: pd.DataFrame) -> None:
    expected = cfg["corpus"]["expected"]
    actual = {
        "verses": len(verses),
        "chapters": int((units.unit_type == "chapter").sum()),
        "parashiyot": int((units.unit_type == "parasha").sum()),
    }
    wrong = {k: (actual[k], v) for k, v in expected.items() if actual[k] != v}
    if wrong:
        raise RuntimeError(f"unexpected counts (actual, expected): {wrong}")


def longest_verses(cfg: dict[str, Any], verses: pd.DataFrame, n: int = 5) -> pd.DataFrame | None:
    """BEREL token counts of the longest `text_model`s (incl. [CLS]/[SEP]); None if unavailable."""
    try:
        from transformers import AutoTokenizer

        tok = AutoTokenizer.from_pretrained(cfg["encoders"]["berel"])
    except Exception:  # offline, missing cache, ...
        return None
    lengths = [len(ids) for ids in tok(verses.text_model.tolist())["input_ids"]]
    out = verses[["ref", "text_model"]].assign(n_tokens=lengths)
    return out.nlargest(n, "n_tokens")


def write_report(
    path: Path,
    cfg: dict[str, Any],
    verses: pd.DataFrame,
    words: pd.DataFrame,
    units: pd.DataFrame,
    longest: pd.DataFrame | None,
) -> None:
    aligned = words.display_idx.notna()
    coverage = aligned.mean()
    by_type = units.unit_type.value_counts()
    pericopes = units[units.unit_type == "pericope"]
    kq = words.kq.value_counts()
    max_len = cfg["text"]["max_seq_length"]

    parts = [
        "# Corpus report",
        "",
        f"Built {datetime.now(UTC).isoformat(timespec='seconds')}; "
        f"OSHB commit `{cfg['sources']['oshb']['commit'][:7]}`; reading `{cfg['text']['kq']}`.",
        "",
        "## Counts",
        md_table(
            ["item", "count"],
            [
                ["verses", len(verses)],
                ["words (OSHB)", len(words)],
                ["chapters", by_type.get("chapter", 0)],
                ["parashiyot", by_type.get("parasha", 0)],
                ["pericopes", len(pericopes)],
                *[
                    [f"pericopes closed by {m}", c]
                    for m, c in pericopes.marker.value_counts().items()
                ],
                ["mid-verse pe/samekh markers (snapped)", int(verses.n_mid_breaks.sum())],
                ["qere words in text", kq.get("q", 0)],
                ["ketiv words in text", kq.get("k", 0)],
                ["verses with a MAM ketiv note", int(verses.ketiv_note.notna().sum())],
            ],
        ),
        "",
        "## Versification overrides (OSHB -> MAM)",
        md_table(
            ["OSHB", "MAM", "rule"],
            [
                [
                    f"{o} {c}:{first}-{last or 'end'}",
                    f"{mc}:{mv}",
                    "merged into one verse" if collapse else "shifted",
                ]
                for o, c, first, last, mc, mv, collapse in VERSE_OVERRIDES
            ],
        ),
        "",
        f"## Alignment coverage: {coverage:.2%} of OSHB words "
        f"(threshold {cfg['corpus']['min_alignment_coverage']:.0%})",
    ]

    words_book = words.merge(verses[["verse_id", "book_id", "ref"]], on="verse_id")
    words_book["aligned"] = aligned.to_numpy()
    per_book = words_book.groupby("book_id").aligned.mean()
    parts.append(
        md_table(
            ["book", "coverage"], [[BOOKS[b].sefaria, f"{c:.2%}"] for b, c in per_book.items()]
        )
    )
    per_verse = words_book.groupby("ref", sort=False).aligned.agg(["mean", "size"])
    worst = per_verse.sort_values(["mean", "size"], ascending=[True, False]).head(20)
    parts += [
        "",
        "### 20 least-aligned verses",
        md_table(
            ["verse", "coverage", "words"],
            [[ref, f"{r['mean']:.0%}", int(r["size"])] for ref, r in worst.iterrows()],
        ),
        "",
        "## Pe/samekh per book (MAM is authoritative)",
    ]
    rows = []
    for b in BOOKS:
        bv = verses[verses.book_id == b.book_id]
        mam = Counter(bv.break_after.dropna())
        oshb = Counter(bv.oshb_break.dropna())
        rows.append([b.sefaria, mam["pe"], mam["samekh"], oshb["pe"], oshb["samekh"]])
    parts.append(md_table(["book", "MAM pe", "MAM samekh", "OSHB pe", "OSHB samekh"], rows))
    parts += ["", f"## Longest verses in BEREL tokens (max_seq_length = {max_len})"]
    if longest is None:
        parts.append("Not computed: the BEREL tokenizer could not be loaded.")
    else:
        parts.append(
            md_table(
                ["verse", "tokens", "fits"],
                [
                    [r.ref, r.n_tokens, "yes" if r.n_tokens <= max_len else "**NO**"]
                    for r in longest.itertuples()
                ],
            )
        )
    path.write_text("\n".join(parts) + "\n", encoding="utf-8")


def run_build_corpus(cfg: dict[str, Any], log: Log = print) -> None:
    raw = resolve_path(cfg, "data_raw")
    out = resolve_path(cfg, "data_processed")
    kq = cfg["text"]["kq"]

    log("parsing OSHB and MAM")
    books = [load_book(raw, b, kq) for b in BOOKS]
    problems = [p for data in books for p in check_versification(data)]
    if problems:
        raise RuntimeError("verse counts differ between OSHB and MAM:\n  " + "\n  ".join(problems))

    log("building verse and word tables")
    verses, words = build_tables(books)

    log("building units")
    parashiyot = [
        p
        for b in TORAH
        for p in load_parashiyot(raw / "sefaria" / "schemas" / f"{b.sefaria_slug}.json")
    ]
    units, members = build_units(verses, parashiyot)
    check_membership(verses, units, members)
    check_expected(cfg, verses, units)

    log("measuring verse lengths in BEREL tokens")
    longest = longest_verses(cfg, verses)
    if longest is None:
        log("  warning: BEREL tokenizer unavailable; longest-verse check skipped")
    elif longest.n_tokens.max() > cfg["text"]["max_seq_length"]:
        log(
            f"  warning: {longest.iloc[0].ref} has {longest.n_tokens.max()} tokens > max_seq_length"
        )

    out.mkdir(parents=True, exist_ok=True)
    verses.to_parquet(out / "verses.parquet", index=False)
    words.to_parquet(out / "words.parquet", index=False)
    units.to_parquet(out / "units.parquet", index=False)
    members.to_parquet(out / "unit_members.parquet", index=False)
    meta = {
        "config_hash": config_hash(cfg, "sources", "text", "corpus"),
        "oshb_commit": cfg["sources"]["oshb"]["commit"],
        "built_at": datetime.now(UTC).isoformat(timespec="seconds"),
    }
    (out / "corpus_meta.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    write_report(out / "corpus_report.md", cfg, verses, words, units, longest)

    coverage = words.display_idx.notna().mean()
    log(
        f"done: {len(verses)} verses, {len(words)} words, "
        f"{(units.unit_type == 'pericope').sum()} pericopes, alignment {coverage:.2%}"
    )
    threshold = cfg["corpus"]["min_alignment_coverage"]
    if coverage < threshold:
        raise RuntimeError(f"alignment coverage {coverage:.2%} is below {threshold:.0%}")
