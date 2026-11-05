"""`bsim llm-ui-review`: Claude reviews the Hebrew interface, page group by page group (DESIGN.md
§16.89, D145; series L8).

The Hebrew catalogs (D54: an interface language, not a translation; scripture is Hebrew in both)
were written beside the English ones and checked by tests for shape only: the same keys, value
kinds and function arities, plurals and numerals spot-checked. Nothing checked the Hebrew itself.
Here each page group's English and Hebrew files (and the core catalogs) are sent together, with
the project's rules for the interface language (DESIGN.md's D54 and §11's catalog paragraph) and
the Hebrew glossary as the terminology, and Claude returns the strings worth changing: grammar,
gender and number agreement, a term used otherwise than the glossary's, wording a Hebrew reader
would not write, a meaning that differs from the English.

The answers are a report (`artifacts/llm_ui/review.md`) for the owner: no catalog is changed
here. Interface strings only; no verse is sent.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd

from bsim.config import PROJECT_ROOT, config_hash, resolve_path, write_meta
from bsim.eval.llm_batch import (
    Collected,
    Log,
    make_request,
    mark_collected,
    run_batch,
    usage,
)

OUT = "llm_ui"
KINDS = ("grammar", "agreement", "term", "wording", "meaning", "consistency")
SCHEMA = {
    "type": "object",
    "properties": {
        "issues": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "key": {"type": "string"},
                    "kind": {"type": "string", "enum": list(KINDS)},
                    "current": {"type": "string"},
                    "suggested": {"type": "string"},
                    "reason": {"type": "string"},
                },
                "required": ["key", "kind", "current", "suggested", "reason"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["issues"],
    "additionalProperties": False,
}
SYSTEM = """You review the Hebrew interface of a web application for studying the Hebrew Bible \
(similar verses, literary patterns, statistics). Each request gives one group of interface \
strings in English (the source) and in Hebrew, as TypeScript objects; some values are functions \
that build a string from numbers or names.

Report only the Hebrew strings worth changing:
- grammar: a mistake of Hebrew grammar or spelling;
- agreement: gender or number that does not agree (in functions, check the plural branches);
- term: a term used otherwise than the glossary's Hebrew term for it;
- wording: correct, but not what a Hebrew reader of scholarly prose would write (calques, \
word order);
- meaning: the Hebrew says something other than the English;
- consistency: the same thing named differently within the group.

Rules:
- Follow the project's rules for the interface language given below. Hebrew Bible text quoted in \
the strings stays as it is; do not suggest translating anything into English.
- key is the property path as written in the file (for example `discoveries.rankFor`). current is \
the Hebrew as it is now (for a function, its template text), suggested the Hebrew you propose, \
reason one short sentence in English.
- Do not report a string that is fine. Report nothing rather than a matter of taste. An empty list \
is a good answer."""


def catalog_pairs(web: Path) -> list[tuple[str, Path, Path]]:
    """`(group, English file, Hebrew file)`: the core catalogs and each page group."""
    i18n = web / "src" / "i18n"
    pairs = [("core", i18n / "en.ts", i18n / "he.ts")]
    for he in sorted((i18n / "pages" / "he").glob("*.ts")):
        en = i18n / "pages" / he.name
        if en.exists():
            pairs.append((he.stem, en, he))
    return pairs


def rules(design: Path) -> str:
    """The project's rules for the interface language, quoted from DESIGN.md."""
    lines = design.read_text("utf-8").splitlines()
    keep = [
        ln
        for ln in lines
        if ln.startswith("| D54 |") or ln.startswith("- Interface language (`src/i18n/`)")
    ]
    if len(keep) < 2:
        raise RuntimeError("DESIGN.md's D54 row or §11 catalog paragraph not found")
    return "\n\n".join(keep)


def build_items(cfg: dict[str, Any], log: Log) -> tuple[pd.DataFrame, dict[str, str]]:
    web, design = PROJECT_ROOT / "web", PROJECT_ROOT / "docs" / "DESIGN.md"
    if not web.exists():
        raise RuntimeError(f"{web} missing")
    pairs = catalog_pairs(web)
    glossary = (web / "src" / "i18n" / "pages" / "he" / "glossary.ts").read_text("utf-8")
    context = (
        f"The project's rules for the interface language:\n\n{rules(design)}\n\n"
        f"The Hebrew glossary (the terminology):\n\n```ts\n{glossary}\n```"
    )
    rows, prompts = [], {}
    for i, (group, en, he) in enumerate(pairs):
        cid = f"ui-{i}"
        rows.append({"custom_id": cid, "group": group, "en": str(en), "he": str(he)})
        prompts[cid] = (
            f"{context}\n\nThe group `{group}` in English:\n\n```ts\n{en.read_text('utf-8')}\n```"
            f"\n\nThe group `{group}` in Hebrew:\n\n```ts\n{he.read_text('utf-8')}\n```"
        )
    log(f"{len(rows)} groups (the core catalogs and {len(rows) - 1} page groups)")
    return pd.DataFrame(rows), prompts


def answer(data: dict[str, Any]) -> dict[str, Any] | None:
    issues = data.get("issues")
    if not isinstance(issues, list):
        return None
    keep = [
        i
        for i in issues
        if isinstance(i, dict) and i.get("kind") in KINDS and i.get("suggested") != i.get("current")
    ]
    return {"issues": keep, "n_issues": len(keep)}


def run_llm_ui(
    cfg: dict[str, Any],
    log: Log = print,
    dry_run: bool = False,
    client: Any = None,
    sleep: Callable[[float], None] = time.sleep,
) -> dict[str, Any]:
    lc = cfg["llm_ui"]
    out = resolve_path(cfg, "artifacts") / OUT

    def prepare() -> tuple[pd.DataFrame, list[dict]]:
        items, prompts = build_items(cfg, log)
        reqs = [make_request(c, SYSTEM, prompts[c], SCHEMA, lc) for c in items.custom_id]
        return items, reqs

    got = run_batch(
        out, lc, prepare, answer, log=log, dry_run=dry_run, client=client, sleep=sleep,
        items_file="items.parquet",
    )  # fmt: skip
    if not isinstance(got, Collected):
        return got
    df = got.df
    if "issues" not in df:
        df["issues"] = [[] for _ in range(len(df))]
    df["issues"] = [i if isinstance(i, list) else [] for i in df.issues]
    issues = [{"group": g, **i} for g, lst in zip(df.group, df.issues, strict=True) for i in lst]
    meta = {
        "model": got.state["model"],
        "batch_id": got.state["batch_id"],
        "submitted_at": got.state["created_at"],
        "collected_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "status": {str(k): int(v) for k, v in df.status.value_counts().items()},
        "groups": len(df),
        "issues": len(issues),
        "by_kind": {k: sum(i["kind"] == k for i in issues) for k in KINDS},
        "usage": usage(df, lc),
        "config_hash": config_hash(cfg, "llm_ui"),
    }
    pd.DataFrame(issues).to_parquet(out / "issues.parquet", index=False)
    write_meta(out / "llm_ui.meta.json", meta)
    write_report(out / "review.md", issues, meta)
    mark_collected(out, got.state)
    log(f"{meta['issues']} suggestions in {meta['groups']} groups {meta['by_kind']};"
        f" about ${meta['usage']['usd']:.2f}; see {out / 'review.md'}")  # fmt: skip
    return meta


def write_report(path: Path, issues: list[dict[str, Any]], meta: dict[str, Any]) -> None:
    lines = [
        "# The Hebrew interface: Claude's suggestions",
        "",
        f"{meta['issues']} suggestions in {meta['groups']} groups ({meta['model']}): suggestions"
        " only; a catalog changes only after the owner agrees.",
        "",
    ]
    by_group: dict[str, list[dict[str, Any]]] = {}
    for i in issues:
        by_group.setdefault(i["group"], []).append(i)
    for group, lst in by_group.items():
        lines += [f"## {group} ({len(lst)})", ""]
        for i in lst:
            lines.append(f"- [ ] `{i['key']}` ({i['kind']}): {i['current']} → {i['suggested']}"
                         f" — {i['reason']}")  # fmt: skip
        lines.append("")
    path.write_text("\n".join(lines) + "\n", "utf-8")
