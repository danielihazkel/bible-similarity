"""Clause-shape tokens for the `syntax` mode: `bm25_syntax`, `tfidf_syntax` (DESIGN.md §16.26).

Every BHSA clause of a verse (`bsim syntax`) gives, in order:
    C:{typ}                 its clause type (WayX, xQtX, NmCl, InfC, ...)
    P:{typ}:{functions}     the type with the functions of its phrases in order
                            (`Way0:Conj-Pred-Objc-Cmpl`): the clause's shape, whatever its words
    R:{rela}                its relation to another clause, when it has one (Objc, Attr, Adju, ...)
    T:{N|Q|D}               its text type: narrative, quotation or discourse
    S:{typ}>{typ}           the type of the clause before it in the verse and its own
Two verses then match when they are built alike — `ויאמר X אל Y` + a quoted command, a
participle clause after a wayyiqtol chain, a `לא` + yiqtol prohibition — not when they share
words. `structural` (§16.5) sees word shapes; this sees how the words group into phrases and
clauses.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def clause_tokens(typ: str, functions: list[str], rela: str, txt: str) -> list[str]:
    out = [f"C:{typ}", f"P:{typ}:{'-'.join(functions)}"]
    if rela and rela != "NA":
        out.append(f"R:{rela}")
    if txt:
        out.append(f"T:{txt[-1]}")
    return out


def syntax_streams(
    clauses: pd.DataFrame, phrases: pd.DataFrame, n: int
) -> tuple[list[list[str]], list[np.ndarray]]:
    """Per verse the clause tokens (weight 1 each), clauses in order."""
    funcs: dict[int, list[str]] = {}
    for c, f in zip(phrases.clause, phrases.function, strict=True):
        funcs.setdefault(int(c), []).append(f)
    tokens: list[list[str]] = [[] for _ in range(n)]
    prev: dict[int, str] = {}
    for c, v, typ, rela, txt in zip(
        clauses.clause, clauses.verse_id, clauses.typ, clauses.rela, clauses.txt, strict=True
    ):
        v = int(v)
        tokens[v] += clause_tokens(typ, funcs.get(int(c), []), rela, txt)
        if v in prev:
            tokens[v].append(f"S:{prev[v]}>{typ}")
        prev[v] = typ
    return tokens, [np.ones(len(t)) for t in tokens]
