"""`bsim compare-builds OLD NEW`: what changed between two results DBs (DESIGN.md §16.49).

Both files are opened read-only and attached to one in-memory SQLite connection, so every count is
a query and no table is loaded into Python. For each table:
    schema    present in one build only; columns added or removed
    rows      the row counts
    keyed     a table with a primary key is joined on it: rows only in OLD, only in NEW, and the
              rows whose other columns differ, exactly and beyond `float_tol` (a relative
              tolerance on REAL columns, so a sum taken in another order is not a change), with a
              few example keys and the columns that differ
    unkeyed   a table without one is compared as a multiset of whole rows (exact): rows only in
              OLD, only in NEW, and whether the same rows come in another order
`meta` (the build's key -> JSON statistics) is compared value by value, as flattened JSON paths;
keys in `volatile_meta` (the build time) are reported apart. This is what M54 did by hand.
"""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterator
from pathlib import Path
from typing import Any

META = "meta"


def _q(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def _connect(old: Path, new: Path) -> sqlite3.Connection:
    for p in (old, new):
        if not p.exists():
            raise RuntimeError(f"{p} not found")
    con = sqlite3.connect("file::memory:", uri=True)  # uri: the files are attached read-only
    for alias, p in (("o", old), ("n", new)):
        con.execute(f"ATTACH DATABASE ? AS {alias}", (f"{p.resolve().as_uri()}?mode=ro",))
    return con


def _tables(con: sqlite3.Connection, db: str) -> list[str]:
    rows = con.execute(
        f"SELECT name FROM {db}.sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
    )
    return sorted(r[0] for r in rows)


def _columns(con: sqlite3.Connection, db: str, table: str) -> list[tuple[str, str, int]]:
    """(name, declared type, position in the primary key or 0)."""
    info = con.execute(f"PRAGMA {db}.table_info({_q(table)})")
    return [(r[1], (r[2] or "").upper(), r[5]) for r in info]


def _count(con: sqlite3.Connection, sql: str) -> int:
    return int(con.execute(sql).fetchone()[0])


def _real(declared: str) -> bool:
    return any(t in declared for t in ("REAL", "FLOA", "DOUB"))


def _differs(col: tuple[str, str, int], tol: float) -> str:
    """SQL: column `col` of `o` and `n` differ (beyond `tol` for a REAL column: relative, and
    absolute below 1)."""
    a, b = f"o.{_q(col[0])}", f"n.{_q(col[0])}"
    if not _real(col[1]) or tol <= 0:
        return f"{a} IS NOT {b}"
    return (
        f"(({a} IS NULL) <> ({b} IS NULL) OR "
        f"abs({a} - {b}) > {tol!r} * max(1.0, abs({a}), abs({b})))"
    )


def compare_table(
    con: sqlite3.Connection, table: str, tol: float, examples: int
) -> dict[str, Any]:
    cols_o, cols_n = _columns(con, "o", table), _columns(con, "n", table)
    names_o, names_n = [c[0] for c in cols_o], [c[0] for c in cols_n]
    common = [c for c in cols_o if c[0] in set(names_n)]
    out: dict[str, Any] = {
        "rows_old": _count(con, f"SELECT count(*) FROM o.{_q(table)}"),
        "rows_new": _count(con, f"SELECT count(*) FROM n.{_q(table)}"),
        "columns_added": [c for c in names_n if c not in names_o],
        "columns_removed": [c for c in names_o if c not in names_n],
    }
    key = [c[0] for c in sorted((c for c in common if c[2]), key=lambda c: c[2])]
    pk_new = [c[0] for c in sorted((c for c in cols_n if c[2]), key=lambda c: c[2])]
    sel = ", ".join(_q(c[0]) for c in common)
    if key and key == pk_new:
        on = " AND ".join(f"o.{_q(k)} IS n.{_q(k)}" for k in key)
        o, n = f"o.{_q(table)}", f"n.{_q(table)}"
        rest = [c for c in common if not c[2]]
        out["key"] = key
        out["only_old"] = _count(
            con, f"SELECT count(*) FROM {o} o WHERE NOT EXISTS (SELECT 1 FROM {n} n WHERE {on})"
        )
        out["only_new"] = _count(
            con, f"SELECT count(*) FROM {n} n WHERE NOT EXISTS (SELECT 1 FROM {o} o WHERE {on})"
        )
        exact = " OR ".join(_differs(c, 0) for c in rest) or "0"
        beyond = [_differs(c, tol) for c in rest]
        where = " OR ".join(beyond) or "0"
        join = f"FROM {o} o JOIN {n} n ON {on}"
        out["changed"] = _count(con, f"SELECT count(*) {join} WHERE {exact}")
        out["changed_beyond_tol"] = _count(con, f"SELECT count(*) {join} WHERE {where}")
        out["examples"] = []
        if out["changed_beyond_tol"]:
            shown = ", ".join([f"o.{_q(k)}" for k in key] + beyond)
            for r in con.execute(f"SELECT {shown} {join} WHERE {where} LIMIT {int(examples)}"):
                flags = r[len(key) :]
                out["examples"].append(
                    {
                        "key": list(r[: len(key)]),
                        "columns": [c[0] for c, f in zip(rest, flags, strict=True) if f],
                    }
                )
    else:
        out["key"] = None
        out["only_old"], out["only_new"] = _multiset_diff(con, table, sel)
        out["reordered"] = bool(
            out["only_old"] == 0
            and out["only_new"] == 0
            and out["rows_old"] == out["rows_new"]
            and not _same_order(con, table, sel)
        )
    out["same"] = bool(
        out["rows_old"] == out["rows_new"]
        and not out["columns_added"]
        and not out["columns_removed"]
        and out["only_old"] == 0
        and out["only_new"] == 0
        and not out.get("changed")
        and not out.get("reordered")
    )
    return out


def _multiset_diff(con: sqlite3.Connection, table: str, sel: str) -> tuple[int, int]:
    """Rows of OLD beyond their count in NEW, and the reverse (duplicates counted; one sort)."""
    t = _q(table)
    r = con.execute(
        "SELECT coalesce(sum(max(c, 0)), 0), coalesce(sum(max(-c, 0)), 0) FROM ("
        f"SELECT sum(s) AS c FROM (SELECT {sel}, 1 AS s FROM o.{t} "
        f"UNION ALL SELECT {sel}, -1 FROM n.{t}) GROUP BY {sel})"
    ).fetchone()
    return int(r[0]), int(r[1])


def _same_order(con: sqlite3.Connection, table: str, sel: str) -> bool:
    """The two tables hold their rows in the same rowid order."""
    a = con.execute(f"SELECT {sel} FROM o.{_q(table)} ORDER BY rowid")
    b = con.execute(f"SELECT {sel} FROM n.{_q(table)} ORDER BY rowid")
    while True:
        x, y = a.fetchmany(10_000), b.fetchmany(10_000)
        if x != y:
            return False
        if not x:
            return True


def _flatten(value: Any, path: str = "") -> Iterator[tuple[str, Any]]:
    if isinstance(value, dict) and value:
        for k, v in value.items():
            yield from _flatten(v, f"{path}.{k}" if path else str(k))
    else:
        yield path, value


def _meta(con: sqlite3.Connection, db: str) -> dict[str, Any]:
    if META not in _tables(con, db):
        return {}
    out = {}
    for key, value in con.execute(f"SELECT key, value FROM {db}.{META}"):
        try:
            out[key] = json.loads(value)
        except (TypeError, ValueError):
            out[key] = value
    return out


def compare_meta(
    old: dict[str, Any], new: dict[str, Any], volatile: list[str], examples: int
) -> dict[str, Any]:
    changed = {}
    for key in sorted(set(old) & set(new) - set(volatile)):
        if old[key] == new[key]:
            continue
        fo, fn = dict(_flatten(old[key])), dict(_flatten(new[key]))
        paths = sorted(p for p in set(fo) | set(fn) if fo.get(p, ...) != fn.get(p, ...))
        changed[key] = {
            "paths": len(paths),
            "examples": [
                {"path": p, "old": fo.get(p), "new": fn.get(p)} for p in paths[:examples]
            ],
        }
    return {
        "added": sorted(set(new) - set(old)),
        "removed": sorted(set(old) - set(new)),
        "changed": changed,
        "volatile": {k: [old.get(k), new.get(k)] for k in volatile if old.get(k) != new.get(k)},
    }


def compare_builds(cfg: dict[str, Any], old: Path, new: Path) -> dict[str, Any]:
    cb = cfg["compare_builds"]
    tol, examples = float(cb["float_tol"]), int(cb["examples"])
    con = _connect(old, new)
    try:
        t_old, t_new = _tables(con, "o"), _tables(con, "n")
        both = sorted(set(t_old) & set(t_new) - {META})
        tables = {t: compare_table(con, t, tol, examples) for t in both}
        meta = compare_meta(_meta(con, "o"), _meta(con, "n"), cb["volatile_meta"], examples)
    finally:
        con.close()
    return {
        "old": str(old),
        "new": str(new),
        "float_tol": tol,
        "tables_added": sorted(set(t_new) - set(t_old)),
        "tables_removed": sorted(set(t_old) - set(t_new)),
        "tables": tables,
        "meta": meta,
        "identical": bool(
            not set(t_old) ^ set(t_new)
            and all(t["same"] for t in tables.values())
            and not (meta["added"] or meta["removed"] or meta["changed"])
        ),
    }


def report(out: dict[str, Any]) -> str:
    tables = out["tables"]
    differ = {t: r for t, r in tables.items() if not r["same"]}
    lines = [
        f"# {out['old']} -> {out['new']}",
        "",
        f"{len(tables)} tables in both: {len(tables) - len(differ)} the same, {len(differ)} differ"
        f" (REAL columns compared within a relative {out['float_tol']:g})."
        + (f" Only in NEW: {', '.join(out['tables_added'])}." if out["tables_added"] else "")
        + (f" Only in OLD: {', '.join(out['tables_removed'])}." if out["tables_removed"] else ""),
    ]
    if differ:
        lines += [
            "",
            "| table | rows old | rows new | only old | only new | changed (beyond tol) | note |",
            "|---|---|---|---|---|---|---|",
        ]
        for t, r in differ.items():
            note = []
            if r["columns_added"]:
                note.append(f"columns added: {', '.join(r['columns_added'])}")
            if r["columns_removed"]:
                note.append(f"columns removed: {', '.join(r['columns_removed'])}")
            if r["key"] is None:
                order = "; same rows, another order" if r.get("reordered") else ""
                note.append(f"no key: whole rows{order}")
            for e in r.get("examples", []):
                note.append(f"{e['key']}: {', '.join(e['columns'])}")
            changed = "–" if r["key"] is None else f"{r['changed']:,} ({r['changed_beyond_tol']:,})"
            lines.append(
                f"| {t} | {r['rows_old']:,} | {r['rows_new']:,} | {r['only_old']:,} | "
                f"{r['only_new']:,} | {changed} | {'; '.join(note)} |"
            )
    m = out["meta"]
    lines += ["", "## meta", ""]
    if m["added"]:
        lines.append(f"- added: {', '.join(m['added'])}")
    if m["removed"]:
        lines.append(f"- removed: {', '.join(m['removed'])}")
    for key, c in m["changed"].items():
        shown = "; ".join(f"{e['path']}: {e['old']!r} -> {e['new']!r}" for e in c["examples"])
        lines.append(f"- {key}: {c['paths']} value(s) changed. {shown}")
    if not (m["added"] or m["removed"] or m["changed"]):
        apart = f" (apart from {', '.join(m['volatile'])})" if m["volatile"] else ""
        lines.append(f"- the same{apart}")
    lines += ["", "Identical." if out["identical"] else "Different."]
    return "\n".join(lines) + "\n"
