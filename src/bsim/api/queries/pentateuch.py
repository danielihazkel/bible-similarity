"""Read-only SQL helpers of `api/routes/pentateuch.py` (DESIGN.md §9)."""

from __future__ import annotations

import sqlite3
from typing import Any

from bsim.api.queries.common import _dicts, count


def pentateuch_chapters_page(
    conn: sqlite3.Connection, book_id: int | None, limit: int, offset: int
) -> tuple[int, list[dict[str, Any]]]:
    """Chapters of the P / non-P split in canon order, with their unit labels."""
    where, args = ("WHERE s.book_id = ?", [book_id]) if book_id is not None else ("", [])
    base = f"FROM pentateuch_chapters s JOIN units u ON u.unit_id = s.unit_id {where}"
    total = count(conn, f"SELECT COUNT(*) {base}", args)
    cur = conn.execute(
        f"SELECT s.*, u.label_en, u.label_he {base} ORDER BY s.book_id, s.chapter LIMIT ? OFFSET ?",
        [*args, limit, offset],
    )
    return total, _dicts(cur)
