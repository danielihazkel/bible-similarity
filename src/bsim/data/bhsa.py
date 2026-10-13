"""ETCBC BHSA clauses and phrases, aligned to OSHB words (DESIGN.md §16.26).

The BHSA (Biblia Hebraica Stuttgartensia Amstelodamensis, ETCBC; CC BY-NC 4.0) is a syntactic
database of the WLC: every word belongs to a phrase with a function (Pred, Subj, Objc, Cmpl,
Adju, Time, Loca, ...), every phrase to a clause with a type (Way0, WXQt, NmCl, InfC, ...), a
kind (verbal / nominal / without predication) and a text type (`domain`: narrative N, discursive
D, quotation Q; `txt`: the embedding, e.g. `NQ` for a quotation inside narrative). `bsim
download --only syntax` fetches the needed Text-Fabric feature files at a pinned commit;
glosses are not fetched (D5).

Text-Fabric files (`read_tf`): a header of `@` lines, a blank line, then one line per node,
`[nodes<TAB>]value` for node features and `[nodes<TAB>]targets` for edges; omitted nodes are the
previous node + 1, and `nodes` / `targets` may be ranges (`5-9`) and lists (`1,3-4`).

Alignment (`align_verse`): BHSA words follow the ketiv and split off prefixes (ב, ו, ה) as words
of their own, the article after a preposition with no consonants; OSHB words keep prefixes and
read the qere. Per verse, the two consonant strings (finals folded) are aligned with difflib,
each BHSA word goes to the OSHB word that most of its consonants fall in, and a word with none
matched (the hidden article, a ketiv / qere difference) to its neighbour's.

`bsim syntax` writes, under `paths.data_processed`:
    syntax_clauses.parquet   clause, verse_id, words (OSHB idx list), typ, kind, domain, txt,
                             rela, speech (txt has Q), speaker, speaker_source, quote
                             (the quotation's first clause or -1), addressee,
                             addressee_source
    syntax_phrases.parquet   phrase, clause, verse_id, words, typ, function
    syntax_meta.json         counts, alignment check, the speaker rule's coverage
"""

from __future__ import annotations

import json
import re
import time
from collections import Counter
from collections.abc import Callable, Iterable
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from bsim.config import resolve_path
from bsim.data.lexicon import strong_key
from bsim.text.normalize import consonantal, fold_finals

Log = Callable[[str], None]

# BHSA (Latin) book names -> OSIS
BOOKS = {
    "Genesis": "Gen", "Exodus": "Exod", "Leviticus": "Lev", "Numeri": "Num",
    "Deuteronomium": "Deut", "Josua": "Josh", "Judices": "Judg", "Samuel_I": "1Sam",
    "Samuel_II": "2Sam", "Reges_I": "1Kgs", "Reges_II": "2Kgs", "Jesaia": "Isa",
    "Jeremia": "Jer", "Ezechiel": "Ezek", "Hosea": "Hos", "Joel": "Joel", "Amos": "Amos",
    "Obadia": "Obad", "Jona": "Jonah", "Micha": "Mic", "Nahum": "Nah", "Habakuk": "Hab",
    "Zephania": "Zeph", "Haggai": "Hag", "Sacharia": "Zech", "Maleachi": "Mal",
    "Psalmi": "Ps", "Iob": "Job", "Proverbia": "Prov", "Ruth": "Ruth", "Canticum": "Song",
    "Ecclesiastes": "Eccl", "Threni": "Lam", "Esther": "Esth", "Daniel": "Dan",
    "Esra": "Ezra", "Nehemia": "Neh", "Chronica_I": "1Chr", "Chronica_II": "2Chr",
}  # fmt: skip


def _nodes(spec: str) -> list[int]:
    out: list[int] = []
    for part in spec.split(","):
        a, _, b = part.partition("-")
        out.extend(range(int(a), int(b or a) + 1))
    return out


def _unescape(v: str) -> str:
    return v.replace("\\t", "\t").replace("\\n", "\n").replace("\\\\", "\\")


def read_tf(path: Path) -> dict[int, Any]:
    """A Text-Fabric feature: node -> value (node feature) or node -> target list (edge)."""
    lines = path.read_text("utf-8").split("\n")
    edge = lines[0].strip() == "@edge"
    i = next(k for k, line in enumerate(lines) if not line.startswith("@")) + 1  # skip blank
    out: dict[int, Any] = {}
    node = 0
    if lines and lines[-1] == "":
        lines.pop()  # the file's final newline
    for line in lines[i:]:
        fields = line.split("\t")
        if edge:
            if line == "":
                continue
            nodes, targets = (
                ([node + 1], fields[0])
                if len(fields) == 1
                else (
                    _nodes(fields[0]),
                    fields[1],
                )
            )
            for n in nodes:
                out[n] = _nodes(targets)
        else:
            nodes, value = (
                ([node + 1], fields[0])
                if len(fields) == 1
                else (
                    _nodes(fields[0]),
                    fields[1],
                )
            )
            for n in nodes:
                out[n] = _unescape(value)
        node = nodes[-1]
    return out


def read_otype(path: Path) -> dict[str, tuple[int, int]]:
    """Node type -> (first, last) node."""
    out = {}
    for line in path.read_text("utf-8").split("\n"):
        if line and not line.startswith("@") and "\t" in line:
            span, typ = line.split("\t")
            a, _, b = span.partition("-")
            out[typ] = (int(a), int(b or a))
    return out


def cons(word: str) -> str:
    """Consonants of a word, finals folded (both BHSA and OSHB spellings)."""
    return fold_finals(re.sub(r"[^א-ת]", "", consonantal(word)))


def align_verse(bhsa: list[str], oshb: list[str]) -> list[int]:
    """OSHB word index of every BHSA word of a verse (both given as consonant strings)."""
    a = "".join(bhsa)
    b = "".join(oshb)
    a_word = np.repeat(np.arange(len(bhsa)), [len(w) for w in bhsa])
    b_word = np.repeat(np.arange(len(oshb)), [len(w) for w in oshb])
    votes: list[Counter] = [Counter() for _ in bhsa]
    for m in SequenceMatcher(None, a, b, autojunk=False).get_matching_blocks():
        for k in range(m.size):
            votes[a_word[m.a + k]][b_word[m.b + k]] += 1
    out = [v.most_common(1)[0][0] if v else -1 for v in votes]
    # unmatched words (no consonants, ketiv / qere): the next matched word's, else the previous
    nxt = -1
    for i in range(len(out) - 1, -1, -1):
        if out[i] == -1:
            out[i] = nxt
        else:
            nxt = out[i]
    prev = 0
    for i, o in enumerate(out):
        if o == -1:
            out[i] = prev
        prev = out[i]
    return out


def load_bhsa(raw: Path, features: Iterable[str]) -> tuple[dict[str, tuple[int, int]], dict]:
    """(otype ranges, feature -> node map) of the downloaded BHSA files."""
    otype = read_otype(raw / "otype.tf")
    return otype, {f: read_tf(raw / f"{f}.tf") for f in features}


FEATURES = (
    "oslots", "book", "chapter", "verse", "g_cons_utf8", "lex", "sp",
    "typ", "kind", "domain", "txt", "rela", "function", "mother", "ps", "gn", "vt",
    "nu", "prs", "prs_ps", "prs_gn", "prs_nu",
)  # fmt: skip
NO_SUFFIX = ("", "absent", "n/a", "NA")  # `prs` values meaning no pronominal suffix


def verse_words(
    otype: dict[str, tuple[int, int]], F: dict[str, dict], verse_of_osis: dict[str, int]
) -> tuple[dict[int, list[int]], int]:
    """verse_id -> its BHSA words in order (a verse_id may join several WLC verses), and how many
    BHSA verses have no verse_id."""
    v0, v1 = otype["verse"]
    out: dict[int, list[int]] = {}
    missing = 0
    for v in range(v0, v1 + 1):
        osis = f"{BOOKS[F['book'][v]]}.{F['chapter'][v]}.{F['verse'][v]}"
        vid = verse_of_osis.get(osis)
        if vid is None:
            missing += 1
            continue
        out.setdefault(vid, []).extend(F["oslots"][v])
    return out, missing


def run_syntax(cfg: dict[str, Any], log: Log = print) -> dict[str, Any]:
    t0 = time.perf_counter()
    sc = cfg["syntax"]
    raw, proc = resolve_path(cfg, "data_raw") / "bhsa", resolve_path(cfg, "data_processed")
    missing_tf = [f for f in ("otype", *FEATURES) if not (raw / f"{f}.tf").exists()]
    if missing_tf:
        raise RuntimeError(
            f"{raw}: {', '.join(missing_tf)} missing; run `bsim download --only syntax` first"
        )
    otype, F = load_bhsa(raw, FEATURES)
    log(f"BHSA: {otype['word'][1]} words, {otype['clause'][1] - otype['clause'][0] + 1} clauses")
    verses = pd.read_parquet(proc / "verses.parquet", columns=["verse_id", "oshb_osis"])
    verse_of_osis: dict[str, int] = {}
    for vid, refs in zip(verses.verse_id, verses.oshb_osis, strict=True):
        for r in refs:
            verse_of_osis.setdefault(r, int(vid))
    words = pd.read_parquet(
        proc / "words.parquet", columns=["verse_id", "idx", "surface", "content_lemmas"]
    )
    oshb = dict(iter(words.groupby("verse_id", sort=False)))
    by_verse, missing = verse_words(otype, F, verse_of_osis)

    # every BHSA word -> (verse_id, OSHB word idx)
    w_verse = np.full(otype["word"][1] + 1, -1, dtype=np.int64)
    w_idx = np.full(otype["word"][1] + 1, -1, dtype=np.int64)
    exact = total = 0
    for vid, ws in by_verse.items():
        g = oshb.get(vid)
        if g is None:
            continue
        b = [cons(F["g_cons_utf8"].get(w, "")) for w in ws]
        o = [cons(s) for s in g.surface]
        exact += "".join(b) == "".join(o)
        total += 1
        idx = g.idx.to_numpy()
        for w, k in zip(ws, align_verse(b, o), strict=True):
            w_verse[w], w_idx[w] = vid, idx[k]
    log(
        f"aligned {total} verses ({exact} with the same consonants; {missing} BHSA verses unmapped)"
    )

    content = {
        (int(v), int(i)): list(cl)
        for v, i, cl in zip(words.verse_id, words.idx, words.content_lemmas, strict=True)
    }

    def lemma(w: int) -> str | None:
        cl = content.get((int(w_verse[w]), int(w_idx[w])))
        return cl[0] if cl else None

    # who can speak: a name, a participle used as a noun (והנגשים), or a noun whose SDBH sense
    # here is a being (people, groups, leaders, deities, animals) or a name of a person or deity;
    # without `bsim lexicon`, any noun
    being = _beings(proc, sc["speaker_domains"])

    def can_speak(w: int) -> bool:
        if F["sp"].get(w) == "nmpr" or F["vt"].get(w) == "ptca":
            return True
        if F["sp"].get(w) != "subs":
            return False
        return being is None or (int(w_verse[w]), int(w_idx[w])) in being

    clauses, phrases, atom_clause = _units(otype, F, w_verse, w_idx)
    _speakers(clauses, phrases, atom_clause, F, lemma, can_speak, sc)

    cdf = pd.DataFrame(clauses).drop(columns=["slots", "atoms"])
    cdf = cdf[cdf.verse_id >= 0].reset_index(drop=True)
    pdf = pd.DataFrame(phrases).drop(columns=["slots"])
    pdf = pdf[pdf.verse_id >= 0].reset_index(drop=True)
    cdf.to_parquet(proc / "syntax_clauses.parquet")
    pdf.to_parquet(proc / "syntax_phrases.parquet")
    q = cdf[cdf.speech]
    meta = {
        "bhsa_commit": cfg["sources"]["bhsa"]["commit"],
        "verses_aligned": total,
        "verses_same_consonants": exact,
        "bhsa_verses_unmapped": missing,
        "clauses": len(cdf),
        "phrases": len(pdf),
        "speech_clauses": len(q),
        "speaker": {
            "explicit": int((q.speaker_source == "explicit").sum()),
            "carried": int((q.speaker_source == "carried").sum()),
            "enclosing": int((q.speaker_source == "enclosing").sum()),
            "unknown": int(q.speaker.isna().sum()),
        },
        "seconds": round(time.perf_counter() - t0, 1),
    }
    (proc / "syntax_meta.json").write_text(json.dumps(meta, indent=2) + "\n", "utf-8")
    s = meta["speaker"]
    log(
        f"{len(cdf)} clauses, {len(pdf)} phrases; {len(q)} in direct speech, speaker explicit"
        f" {s['explicit']}, carried {s['carried']}, enclosing {s['enclosing']}, unknown"
        f" {s['unknown']}"
    )
    return meta


def _units(otype, F, w_verse, w_idx):
    """Clause and phrase records over OSHB words (a unit crossing verses keeps its first verse's
    words), and clause_atom -> clause."""
    S = F["oslots"]
    word_clause: dict[int, int] = {}
    clauses = []
    c0, c1 = otype["clause"]
    for c in range(c0, c1 + 1):
        slots = S[c]
        for w in slots:
            word_clause[w] = c
        vid = int(w_verse[slots[0]])
        clauses.append(
            {
                "clause": c,
                "verse_id": vid,
                "words": sorted({int(w_idx[w]) for w in slots if w_verse[w] == vid}),
                "typ": F["typ"].get(c, ""),
                "kind": F["kind"].get(c, ""),
                "domain": F["domain"].get(c, ""),
                "txt": F["txt"].get(c, ""),
                "rela": F["rela"].get(c, ""),
                "slots": slots,
                "atoms": [],
            }
        )
    by_clause = {r["clause"]: r for r in clauses}
    atom_clause: dict[int, int] = {}
    a0, a1 = otype["clause_atom"]
    for a in range(a0, a1 + 1):
        c = word_clause[S[a][0]]
        atom_clause[a] = c
        by_clause[c]["atoms"].append(a)
    phrases = []
    p0, p1 = otype["phrase"]
    for p in range(p0, p1 + 1):
        slots = S[p]
        vid = int(w_verse[slots[0]])
        phrases.append(
            {
                "phrase": p,
                "clause": word_clause[slots[0]],
                "verse_id": vid,
                "words": sorted({int(w_idx[w]) for w in slots if w_verse[w] == vid}),
                "typ": F["typ"].get(p, ""),
                "function": F["function"].get(p, ""),
                "slots": slots,
            }
        )
    return clauses, phrases, atom_clause


def _beings(proc: Path, prefixes: list[str]) -> set[tuple[int, int]] | None:
    """(verse_id, idx) of OSHB words with a sense in one of the `prefixes` domains (None without
    `word_senses.parquet`)."""
    path = proc / "word_senses.parquet"
    if not path.exists():
        return None
    s = pd.read_parquet(path, columns=["verse_id", "idx", "domains"])
    pre = tuple(prefixes)
    return {
        (int(v), int(i))
        for v, i, ds in zip(s.verse_id, s.idx, s.domains, strict=True)
        if any(d.startswith(pre) for d in ds)
    }


def _subject_head(slots: list[int], can_speak, lemma, pass_through: set[str]) -> int | None:
    """The word of a subject phrase that names its speaker: the first that can speak, moving on
    past a `pass_through` head to a later one (בני ישראל -> ישראל)."""
    heads = [w for w in slots if can_speak(w)]
    if not heads:
        return None
    if strong_key(lemma(heads[0]) or "") in pass_through and len(heads) > 1:
        return heads[1]
    return heads[0]


def _speakers(clauses, phrases, atom_clause, F, lemma, can_speak, sc) -> None:
    """Mark direct speech (`txt` ending in Q), who speaks it and to whom.

    A quotation starts at a clause whose first clause atom's mother lies in a clause of a shallower
    text level: that clause introduces it (through an infinitive such as לאמר, `infinitive_hop`,
    to the clause the infinitive depends on). The speaker is the head noun or name of the
    introduction's subject phrase (`explicit`); an introduction without one whose verb is in the
    third person (ויאמר) takes the subject of the nearest of the `speaker_lookback` clauses before
    it at its level that has one and agrees with the verb in gender (`carried`; number is left
    out: collectives such as העם take plural verbs). A quotation with no speaker of its own (a
    first or second person introduction, ואמרת; no introduction found) is inside the nearest
    enclosing quotation that has one (`enclosing`). The speaker holds for the clauses of the
    quotation at its level; `quote` is the quotation's first clause (-1 outside speech).

    The addressee (§16.44) of a quotation is, in order: the head of its introduction's first
    complement opened by one of `addressee_preps` (ויאמר יהוה אל משה) or, after a verb of
    `addressee_object_verbs` (ויצו), of its object (`explicit`); else a being called by a
    vocative in the quotation (`vocative`); else the pronoun on that preposition or verb (אליו,
    ויצוהו), resolved (`pronoun`): "me" in an introduction inside a quotation is that quotation's
    speaker and "you" its addressee; "him / them" is the other party of the previous quotation at
    the same level ending at most `addressee_turn_gap` clauses before (its speaker, or its
    addressee when the same person speaks again), else the nearest being named (subject, object
    or complement) in the `speaker_lookback` clauses before the introduction at its level that is
    not the speaker and agrees with the pronoun; else, for an introduction with no complement at
    all (ויאמר, ויען), that same other party of the previous quotation (`turn`).
    """
    by_clause = {r["clause"]: r for r in clauses}
    pos = {r["clause"]: i for i, r in enumerate(clauses)}
    sp, lex, ps, gn = F["sp"], F["lex"], F["ps"], F["gn"]
    prs, prs_ps, prs_gn, prs_nu, nu = (F[k] for k in ("prs", "prs_ps", "prs_gn", "prs_nu", "nu"))
    pass_through = set(sc["pass_through"])
    preps, obj_verbs = set(sc["addressee_preps"]), set(sc["addressee_object_verbs"])
    to_through = set(sc["addressee_pass_through"])
    subj: dict[int, int] = {}  # clause -> head word (BHSA) of its subject phrase
    pred_lex: dict[int, str] = {}
    pred_ps: dict[int, str] = {}
    pred_verb: dict[int, int] = {}
    to: dict[int, list[int]] = {}  # clause -> its first complement opened by a preposition
    obj: dict[int, list[int]] = {}  # clause -> its first object (a phrase, or a verb's suffix)
    voct: dict[int, list[int]] = {}  # clause -> its first vocative
    named: dict[int, list[int]] = {}  # clause -> beings heading its subject, objects, complements
    for p in phrases:
        c, f, slots = p["clause"], p["function"], p["slots"]
        if f == "Subj" and c not in subj:
            head = _subject_head(slots, can_speak, lemma, pass_through)
            if head is not None:
                subj[c] = head
        if f in ("Pred", "PreO", "PreS") and c not in pred_lex:
            verb = next((w for w in slots if sp.get(w) == "verb"), None)
            if verb is not None:
                pred_lex[c] = lex.get(verb, "")
                pred_ps[c] = ps.get(verb, "")
                pred_verb[c] = verb
        if f == "Cmpl" and c not in to and lex.get(slots[0]) in preps:
            to[c] = slots
        if f in ("Objc", "PreO") and c not in obj:
            obj[c] = slots
        if f == "Voct" and c not in voct:
            voct[c] = slots
        if f in ("Subj", "Objc", "Cmpl"):
            head = _subject_head(slots, can_speak, lemma, to_through)
            if head is not None:
                named.setdefault(c, []).append(head)

    def agrees(verb: int | None, noun: int) -> bool:
        """Gender agrees where both are marked (a name is often unmarked)."""
        if verb is None:
            return True
        a, b = gn.get(verb, ""), gn.get(noun, "")
        return not (a in ("m", "f") and b in ("m", "f") and a != b)

    def agrees_pron(pron: int, noun: int) -> bool:
        """A pronoun agrees in gender where both are marked; a singular one never stands for a
        plural noun (a plural one may: collectives)."""
        a, b = prs_gn.get(pron, ""), gn.get(noun, "")
        if a in ("m", "f") and b in ("m", "f") and a != b:
            return False
        return not (prs_nu.get(pron) == "sg" and nu.get(noun) == "pl")

    mother = F["mother"]

    def intro_of(r) -> int | None:
        m = mother.get(r["atoms"][0]) if r["atoms"] else None
        intro = atom_clause.get(m[0]) if m else None
        if intro is None or len(by_clause[intro]["txt"]) >= len(r["txt"]):
            return None
        ir = by_clause[intro]
        if ir["typ"] == "InfC" and pred_lex.get(intro) in sc["infinitive_hop"] and ir["atoms"]:
            m2 = mother.get(ir["atoms"][0])
            if m2 and m2[0] in atom_clause:
                intro = atom_clause[m2[0]]
        return intro

    def carried(intro: int) -> int | None:
        if pred_ps.get(intro) in ("p1", "p2"):
            return None
        depth, seen = len(by_clause[intro]["txt"]), 0
        for i in range(pos[intro] - 1, max(pos[intro] - 200, -1), -1):
            c = clauses[i]
            if len(c["txt"]) != depth:
                continue
            if c["clause"] in subj:
                head = subj[c["clause"]]
                return head if agrees(pred_verb.get(intro), head) else None
            seen += 1
            if seen >= sc["speaker_lookback"]:
                return None
        return None

    def enclosing(levels: dict, depth: int) -> tuple[str | None, str | None]:
        """The speaker of the nearest enclosing quotation, for one without its own (the words
        God gives Moses to say, ואמרת אלהם)."""
        outer = [d for d, lv in levels.items() if d < depth and lv[0]]
        return (levels[max(outer)][0], "enclosing") if outer else (None, None)

    # speakers, and the quotations in order: (first clause, depth, introduction, the quotation
    # enclosing it, book)
    quotes: list[tuple[int, int, int | None, int | None, str | None]] = []
    levels: dict[int, tuple[str | None, str | None, int]] = {}  # depth -> speaker, source, quote
    book = None
    for r in clauses:
        b = F["book"].get(r["slots"][0])
        if b != book:
            book, levels = b, {}
        depth = len(r["txt"])
        r["speech"] = r["txt"].endswith("Q")
        # a quotation ends when the text is back at a shallower level
        levels = {d: s for d, s in levels.items() if d <= depth}
        r["speaker"], r["speaker_source"], r["quote"] = None, None, -1
        if r["speech"]:
            intro = intro_of(r)
            if intro is not None or depth not in levels:
                if intro is not None:
                    head, source = subj.get(intro), "explicit"
                    if head is None:
                        head, source = carried(intro), "carried"
                    spk = lemma(head) if head is not None else None
                    levels = {d: s for d, s in levels.items() if d < depth}
                    who = (spk, source) if spk else enclosing(levels, depth)
                else:
                    who = enclosing(levels, depth)
                outer = [d for d in levels if d < depth]
                parent = levels[max(outer)][2] if outer else None
                quotes.append((r["clause"], depth, intro, parent, book))
                levels[depth] = (*who, r["clause"])
            r["speaker"], r["speaker_source"], r["quote"] = levels[depth]

    # addressees, quotation by quotation
    end: dict[int, int] = {}
    first_voct: dict[int, int] = {}
    for i, r in enumerate(clauses):
        q = r["quote"]
        if q < 0:
            continue
        end[q] = i
        if q not in first_voct and r["clause"] in voct:
            head = _subject_head(voct[r["clause"]], can_speak, lemma, to_through)
            if head is not None:
                first_voct[q] = head
    to_whom: dict[int, tuple[str | None, str | None]] = {}
    last: dict[tuple[str | None, int], int] = {}  # (book, depth) -> the latest quotation

    def other_party(q: int, at: int, depth: int, book: str | None) -> str | None:
        """The other party of the previous quotation at this level, if it ended near `at`."""
        prev = last.get((book, depth))
        if prev is None or at - end[prev] > sc["addressee_turn_gap"]:
            return None
        spk = by_clause[q]["speaker"]
        p_spk, p_to = by_clause[prev]["speaker"], to_whom[prev][0]
        if not (spk and p_spk):
            return None
        return p_spk if p_spk != spk else (p_to if p_to != spk else None)

    def named_before(intro: int, spk: str | None, pron: int, since: int = -1) -> str | None:
        """The nearest being named before the introduction at its level (after `since`)."""
        depth, seen = len(by_clause[intro]["txt"]), 0
        for i in range(pos[intro] - 1, max(pos[intro] - 200, since, -1), -1):
            c = clauses[i]
            if len(c["txt"]) != depth:
                continue
            for head in named.get(c["clause"], []):
                lem = lemma(head)
                if lem and lem != spk and agrees_pron(pron, head):
                    return lem
            seen += 1
            if seen >= sc["speaker_lookback"]:
                return None
        return None

    for q, depth, intro, parent, book in quotes:
        spk = by_clause[q]["speaker"]
        addr: str | None = None
        source: str | None = None
        pron = None
        phrase = None
        if intro is not None:
            phrase = to.get(intro)
            if phrase is None and pred_lex.get(intro) in obj_verbs:
                phrase = obj.get(intro)
        if phrase is not None:
            head = _subject_head(phrase, can_speak, lemma, to_through)
            if head is not None:
                addr, source = lemma(head), "explicit"
            else:
                pron = next((w for w in phrase if prs.get(w, "absent") not in NO_SUFFIX), None)
        if addr is None and q in first_voct:
            addr, source = lemma(first_voct[q]), "vocative"
        if addr is None and pron is not None:
            person = prs_ps.get(pron)
            if person in ("p1", "p2"):
                if parent is not None:
                    addr = by_clause[parent]["speaker"] if person == "p1" else to_whom[parent][0]
            else:
                # someone named in the story since the previous quotation (a new scene), else
                # the other party of that quotation, else anyone named before
                prev = last.get((book, depth))
                since = end[prev] if prev is not None else -1
                addr = (
                    named_before(intro, spk, pron, since)
                    or other_party(q, pos[intro], depth, book)
                    or named_before(intro, spk, pron)
                )
            source = "pronoun" if addr else None
        if addr is None and phrase is None and intro is not None:
            # a conversation in a story, not a messenger formula (כה אמר יהוה) inside a speech
            if by_clause[intro]["txt"].endswith("N"):
                addr = other_party(q, pos[intro], depth, book)
            source = "turn" if addr else None
        to_whom[q] = (addr, source)
        last[(book, depth)] = q
    for r in clauses:
        r["addressee"], r["addressee_source"] = to_whom.get(r["quote"], (None, None))
