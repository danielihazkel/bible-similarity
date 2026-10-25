"""Parallel sequences chained into a synopsis of three or more witnesses (DESIGN.md §16.74).

A parallel sequence (§16.7) aligns two passages verse by verse; the ladder shows them two at a
time. Where one passage runs parallel to two others (II Kings 18–20 to Isaiah 36–39 and to II
Chronicles 32–33, I Chronicles 16 to Psalms 96 and 105), the chains are joined:

- **Groups.** Forward chains with q ≤ `max_q` (repeats inside one chapter left out unless
  `same_chapter`); a chain's two sides are *passages*, and passages of one book that overlap or
  lie within `join` verses of each other are one. Chains sharing a passage are one synopsis; a
  synopsis has at least `min_chains` chains (a single chain is its ladder). Its id is its first
  chain's.
- **Rows.** Verses aligned by any of its chains share a row (transitively: A ~ B and B ~ C put A,
  B and C in one row), the strongest chain first and a pair left out that would put one passage
  twice in a row; every verse of a chain's two spans has a row, a skipped verse its own. A
  chain keeps each side in reading order; the rows follow the *lead* book (the book of the
  passage most chains touch, then the one with most aligned verses, then the earlier), a row
  without the lead book's verse right after the row before it in its chain (at a chain's start,
  right before the next lead row). Where the chains disagree on the
  order (a cycle), the earliest remaining row is placed and the break counted.
- **Columns.** A passage is one column; passages of one book whose rows do not meet share a
  column (Psalms 96 and 105 against I Chronicles 16). The lead book's column comes first. A cell
  that goes back from the verse above it in its column (another book told in the lead's order)
  is flagged.
"""

from __future__ import annotations

import heapq
from collections import Counter, defaultdict
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Chain:
    seq_id: int
    a_book: int
    b_book: int
    pairs: list[tuple[int, int]]  # aligned (a, b) verse ids, in chain order

    def sides(self) -> list[tuple[int, int, int]]:
        """(book, first, last) of the a side and of the b side."""
        a = [p[0] for p in self.pairs]
        b = [p[1] for p in self.pairs]
        return [(self.a_book, min(a), max(a)), (self.b_book, min(b), max(b))]


@dataclass
class Passage:
    book: int
    start: int
    end: int
    chains: set[int] = field(default_factory=set)


@dataclass
class Synopsis:
    syn_id: int
    seq_ids: list[int]
    lead_book: int
    columns: list[list[Passage]]  # the passages of each column, in row order
    rows: list[list[int | None]]  # per row, per column: the verse (one passage once a row)
    reordered: list[list[bool]]  # per row, per column: the cell goes back from the verse above it
    breaks: int  # rows placed against a chain's order
    dropped: int  # aligned pairs left out (they would put one passage twice in a row)


def chains_of(rows: Iterable[dict[str, Any]], max_q: float, same_chapter: bool) -> list[Chain]:
    """The `sequences` rows (pairs as `[[a, b, w, ...], ...]`) a synopsis is built from."""
    out = []
    for r in rows:
        if r["direction"] != "forward" or r["q"] > max_q:
            continue
        if r["same_chapter"] and not same_chapter:
            continue
        pairs = [(int(p[0]), int(p[1])) for p in r["pairs"]]
        out.append(Chain(int(r["seq_id"]), int(r["a_book"]), int(r["b_book"]), pairs))
    return sorted(out, key=lambda c: c.seq_id)


def passages(chains: Sequence[Chain], join: int) -> list[Passage]:
    """The chains' sides, one book's overlapping or near sides (≤ `join` verses apart) merged."""
    sides = sorted((b, s, e, c.seq_id) for c in chains for b, s, e in c.sides())
    out: list[Passage] = []
    for b, s, e, sid in sides:
        if out and out[-1].book == b and s <= out[-1].end + join:
            out[-1].end = max(out[-1].end, e)
            out[-1].chains.add(sid)
        else:
            out.append(Passage(b, s, e, {sid}))
    return out


def groups(chains: Sequence[Chain], join: int, min_chains: int) -> list[list[Chain]]:
    """Chains joined through shared passages, each group of at least `min_chains` chains,
    in order of their first chain."""
    parent = {c.seq_id: c.seq_id for c in chains}

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for p in passages(chains, join):
        first, *rest = sorted(p.chains)
        for sid in rest:
            parent[find(sid)] = find(first)
    by_root: dict[int, list[Chain]] = defaultdict(list)
    for c in chains:
        by_root[find(c.seq_id)].append(c)
    out = [g for g in by_root.values() if len(g) >= min_chains]
    return sorted(out, key=lambda g: g[0].seq_id)


def _lead(chains: Sequence[Chain], ps: Sequence[Passage]) -> int:
    aligned: Counter[int] = Counter()
    for c in chains:
        aligned[c.a_book] += len({a for a, _ in c.pairs})
        aligned[c.b_book] += len({b for _, b in c.pairs})
    best = max(ps, key=lambda p: (len(p.chains), aligned[p.book], -p.book))
    return best.book


def layout(chains: Sequence[Chain], join: int) -> Synopsis:
    """One group of chains as rows and columns (see the module docstring)."""
    ps = passages(chains, join)
    book_of: dict[int, int] = {}
    passage_of: dict[int, int] = {}
    for i, p in enumerate(ps):
        for v in range(p.start, p.end + 1):
            book_of[v] = p.book
            passage_of[v] = i
    # rows: verses joined through the aligned pairs
    parent = {v: v for v in book_of}

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    held = {v: {passage_of[v]} for v in book_of}  # a row's passages, at its root
    dropped = 0
    for c in sorted(chains, key=lambda c: c.seq_id):
        for a, b in c.pairs:
            ra, rb = find(a), find(b)
            if ra == rb:
                continue
            if held[ra] & held[rb]:  # one passage twice in a row
                dropped += 1
                continue
            parent[rb] = ra
            held[ra] |= held[rb]
    members: dict[int, list[int]] = defaultdict(list)
    for v in book_of:
        members[find(v)].append(v)
    # order: each chain's side read in order, skipped verses included
    succ: dict[int, set[int]] = defaultdict(set)
    indeg: Counter[int] = Counter()
    in_chain: set[int] = set()
    steps = []
    for c in chains:
        for _, s, e in c.sides():
            in_chain.update(range(s, e + 1))
            steps += [(v, v + 1) for v in range(s, e)]
    # a passage's verses between two chains follow the verse before them (and do not hold back
    # the next chain)
    steps += [(v, v + 1) for p in ps for v in range(p.start, p.end) if v + 1 not in in_chain]
    for v, w in steps:
        g, h = find(v), find(w)
        if g != h and h not in succ[g]:
            succ[g].add(h)
            indeg[h] += 1
    lead = _lead(chains, ps)
    lead_key = {
        g: min(v for v in vs if book_of[v] == lead)
        for g, vs in members.items()
        if any(book_of[v] == lead for v in vs)
    }

    def ahead(g: int) -> int:
        """The first lead row after a row that starts a chain without the lead book."""
        seen, stack, keys = {g}, [g], []
        while stack:
            for h in succ[stack.pop()]:
                if h in lead_key:
                    keys.append(lead_key[h])
                elif h not in seen:
                    seen.add(h)
                    stack.append(h)
        return min(keys, default=min(members[g]))

    def entry(g: int, inherited: int | None) -> tuple[int, int, int]:
        if g in lead_key:
            return (lead_key[g], 0, min(members[g]))
        if inherited is not None:
            return (inherited, 1, min(members[g]))
        return (ahead(g), -1, min(members[g]))

    heap = [entry(g, None) + (g,) for g in members if indeg[g] == 0]
    heapq.heapify(heap)
    placed: list[int] = []
    done: set[int] = set()
    breaks = 0
    while len(placed) < len(members):
        if not heap:  # a cycle: place the earliest remaining row
            g = min((g for g in members if g not in done), key=lambda g: entry(g, None))
            heap.append(entry(g, None) + (g,))
            breaks += 1
        k0, _, _, g = heapq.heappop(heap)
        if g in done:
            continue
        done.add(g)
        placed.append(g)
        for h in succ[g]:
            indeg[h] -= 1
            if indeg[h] == 0 and h not in done:
                heapq.heappush(heap, entry(h, k0) + (h,))
    row_of = {g: i for i, g in enumerate(placed)}
    # columns: one book's passages share a column while their rows do not meet, a passage
    # going on with the column it continues in reading order (else the first)
    rows_of = [{row_of[find(v)] for v in range(p.start, p.end + 1)} for p in ps]
    order = sorted(range(len(ps)), key=lambda i: (ps[i].book != lead, ps[i].book, min(rows_of[i])))
    cols: list[list[int]] = []
    for i in order:
        fits = [
            col
            for col in cols
            if ps[col[0]].book == ps[i].book and not any(rows_of[i] & rows_of[j] for j in col)
        ]
        before = [col for col in fits if max(ps[j].end for j in col) < ps[i].start]
        if before:
            max(before, key=lambda col: max(ps[j].end for j in col)).append(i)
        elif fits:
            fits[0].append(i)
        else:
            cols.append([i])
    col_of = {i: k for k, col in enumerate(cols) for i in col}
    grid: list[list[int | None]] = [[None] * len(cols) for _ in placed]
    for g, i in row_of.items():
        for v in members[g]:
            grid[i][col_of[passage_of[v]]] = v
    reordered = [[False] * len(cols) for _ in placed]
    for k in range(len(cols)):
        last = -1
        for i, row in enumerate(grid):
            v = row[k]
            if v is not None:
                reordered[i][k] = v < last
                last = v
    columns = [[ps[i] for i in sorted(col, key=lambda i: min(rows_of[i]))] for col in cols]
    return Synopsis(
        syn_id=min(c.seq_id for c in chains),
        seq_ids=sorted(c.seq_id for c in chains),
        lead_book=lead,
        columns=columns,
        rows=grid,
        reordered=reordered,
        breaks=breaks,
        dropped=dropped,
    )


def synopses(chains: Sequence[Chain], join: int, min_chains: int) -> list[Synopsis]:
    return [layout(g, join) for g in groups(chains, join, min_chains)]
