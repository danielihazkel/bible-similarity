"""The Message Batches core every Claude job shares (DESIGN.md §16.81; series L).

A job builds its items (one row per request, with a `custom_id`) and its requests; this module
writes the estimate, refuses a submission over the job's `budget_usd`, submits, writes the batch
id before polling (so a stopped run resumes the same batch instead of paying twice), polls,
and merges each answer onto its item. Reading an answer is the job's: it passes `check`, which
turns the decoded JSON into the row's fields, or None when the answer is not what the schema
promised.

Also here: the pointed text a verse is sent in, the rationale cleaner (D134), the AUC a
calibration is judged by, and the cost of the tokens a run used.
"""

from __future__ import annotations

import json
import re
import time
import unicodedata
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

Log = Callable[[str], None]
Check = Callable[[dict[str, Any]], dict[str, Any] | None]

CANTILLATION = re.compile("[֑-ֽ֯]")  # the accents and meteg; the points stay
_HE = "[֐-׿\\-־']"  # a Hebrew letter or mark, or a hyphen / maqaf / geresh after one
# an English gloss right after a Hebrew word: (from your hand), ("be angry"), , "deeds"
GLOSS_PAREN = re.compile(r"(?<=" + _HE + r")[\s,]*\((?=[^()]*[A-Za-z])[^()]*\)")
GLOSS_QUOTE = re.compile(r"(?<=" + _HE + r")[\s,]*[\"“][A-Za-z][^\"”]*[\"”]")
TAG = re.compile(r"</?[A-Za-z_]+>")
# what is left of a gloss in running prose: "in Isaiah it means rebellious children"
GLOSS_PROSE = re.compile(r"\bmean(s|ing|t)?\b|translat|\bi\.e\.|\bliterally\b", re.IGNORECASE)


def pointed(text: str) -> str:
    """A verse's text with its vowel points and without its cantillation marks."""
    return unicodedata.normalize("NFC", CANTILLATION.sub("", text))


def clean_rationale(text: str | None) -> str | None:
    """A rationale fit to show (D134): English glosses after Hebrew words removed, and none at
    all when it still glosses in its prose. The model is told never to translate, and in the
    first run 82 of 600 rationales glossed a word all the same, and 3 glossed in their prose."""
    if not text:
        return None
    text = TAG.sub("", text)  # a stray </rationale> (1 of 600 in the Hebrew run)
    text = GLOSS_QUOTE.sub("", GLOSS_PAREN.sub("", text))
    return None if GLOSS_PROSE.search(text) else re.sub(r"\s+([,.;:])", r"\1", text).strip()


def undirected(a: np.ndarray, b: np.ndarray) -> set[tuple[int, int]]:
    return {(min(x, y), max(x, y)) for x, y in zip(a.tolist(), b.tolist(), strict=True)}


def auc(gold: np.ndarray, score: np.ndarray) -> float | None:
    from sklearn.metrics import roc_auc_score

    if gold.all() or not gold.any():
        return None
    return round(float(roc_auc_score(gold, score)), 4)


def make_client() -> Any:
    try:
        import anthropic
    except ImportError as e:
        raise RuntimeError("the anthropic SDK is an extra: `uv sync --extra llm`") from e
    return anthropic.Anthropic()


# --- one request, one answer ------------------------------------------------------------------


def make_request(
    custom_id: str, system: str, user: str, schema: dict[str, Any], lc: dict[str, Any]
) -> dict[str, Any]:
    """One Message Batches request (plain dicts, as the SDK takes them): no temperature, no
    prefill; the answer in `schema` (`output_config.format`)."""
    return {
        "custom_id": custom_id,
        "params": {
            "model": lc["model"],
            "max_tokens": lc["max_tokens"],
            "system": system,
            "output_config": {
                "effort": lc["effort"],
                "format": {"type": "json_schema", "schema": schema},
            },
            "messages": [{"role": "user", "content": user}],
        },
    }


def parse_message(message: Any, check: Check) -> dict[str, Any]:
    """A succeeded result's message as a row: its tokens, a `status` (ok, refusal, max_tokens,
    unreadable) and, when ok, the fields `check` made of the JSON answer."""
    usage = getattr(message, "usage", None)
    row: dict[str, Any] = {
        "input_tokens": int(getattr(usage, "input_tokens", 0) or 0),
        "output_tokens": int(getattr(usage, "output_tokens", 0) or 0),
    }
    if message.stop_reason in ("refusal", "max_tokens"):
        return {**row, "status": message.stop_reason}
    text = next((b.text for b in message.content if b.type == "text"), None)
    try:
        data = json.loads(text or "")
    except json.JSONDecodeError:
        return {**row, "status": "unreadable"}
    fields = check(data) if isinstance(data, dict) else None
    if fields is None:
        return {**row, "status": "unreadable"}
    return {**row, "status": "ok", **fields}


# --- cost --------------------------------------------------------------------------------------


def usd(input_tokens: float, output_tokens: float, price: dict[str, float]) -> float:
    return round((input_tokens * price["input"] + output_tokens * price["output"]) / 1e6, 2)


def estimate(requests: list[dict], lc: dict[str, Any]) -> dict[str, float]:
    """The cost of a batch before it is sent: input by characters (`chars_per_token`), output at
    `typical_output_tokens` (measured on the job's last run where there is one; M144 answered in
    152 tokens, thinking included) or at the `max_tokens` cap, at the batch `price_per_mtok`."""
    price = lc["price_per_mtok"]
    chars = sum(
        len(r["params"]["system"]) + len(r["params"]["messages"][0]["content"]) for r in requests
    )
    inp = chars / lc["chars_per_token"]
    n = len(requests)
    return {
        "input_tokens_est": round(inp),
        "typical_usd": usd(inp, n * lc["typical_output_tokens"], price),
        "max_usd": usd(inp, n * lc["max_tokens"], price),
        "budget_usd": float(lc["budget_usd"]),
    }


def within_budget(est: dict[str, float]) -> bool:
    return est["typical_usd"] <= est["budget_usd"]


# --- the run -----------------------------------------------------------------------------------


@dataclass
class Collected:
    """A collected batch: the items with each answer's row merged on, and the batch's state."""

    df: pd.DataFrame
    state: dict[str, Any]


def run_batch(
    out: Path,
    lc: dict[str, Any],
    prepare: Callable[[], tuple[pd.DataFrame, list[dict]]],
    check: Check,
    log: Log = print,
    dry_run: bool = False,
    client: Any = None,
    sleep: Callable[[float], None] = time.sleep,
    items_file: str = "items.parquet",
    describe: Callable[[pd.DataFrame], str] | None = None,
) -> Collected | dict[str, Any]:
    """Submit `prepare()`'s requests (or resume the batch `out/batch.json` names) and collect.

    A dry run writes `requests.jsonl` and the items, sends nothing and returns the estimate. A
    submission whose typical estimate is above `lc["budget_usd"]` is refused. After collecting,
    the caller writes its files and then `mark_collected`, so a crash in between collects again
    instead of paying again."""
    out.mkdir(parents=True, exist_ok=True)
    state_path = out / "batch.json"
    state = json.loads(state_path.read_text("utf-8")) if state_path.exists() else None
    if state and state.get("collected"):
        state = None  # a finished batch: a new run starts a new one

    if state is None:
        items, requests = prepare()
        est = estimate(requests, lc)
        what = describe(items) if describe else f"{len(requests)} requests"
        log(
            f"{what} to {lc['model']}; about ${est['typical_usd']:.2f}, at most"
            f" ${est['max_usd']:.2f} (budget ${est['budget_usd']:.2f})"
        )
        if dry_run:
            with (out / "requests.jsonl").open("w", encoding="utf-8") as f:
                for r in requests:
                    f.write(json.dumps(r, ensure_ascii=False) + "\n")
            items.to_parquet(out / items_file, index=False)
            log(f"dry run: requests written to {out / 'requests.jsonl'}; nothing sent")
            return {"dry_run": True, "requests": len(requests), **est}
        if not within_budget(est):
            raise RuntimeError(
                f"the estimate ${est['typical_usd']:.2f} is above budget_usd"
                f" ${est['budget_usd']:.2f}; nothing sent"
            )
        client = client or make_client()
        items.to_parquet(out / items_file, index=False)
        batch = client.messages.batches.create(requests=requests)
        state = {
            "batch_id": batch.id,
            "created_at": datetime.now(UTC).isoformat(timespec="seconds"),
            "model": lc["model"],
            "requests": len(requests),
            "estimate": est,
            "collected": False,
        }
        state_path.write_text(json.dumps(state, indent=2) + "\n", "utf-8")
        log(f"batch {batch.id} submitted")
    else:
        log(f"resuming batch {state['batch_id']} ({state['created_at']})")
        client = client or make_client()

    deadline = time.monotonic() + lc["max_wait_hours"] * 3600
    while True:
        batch = client.messages.batches.retrieve(state["batch_id"])
        if batch.processing_status == "ended":
            break
        if time.monotonic() > deadline:
            raise RuntimeError(
                f"batch {state['batch_id']} still {batch.processing_status}; rerun to resume"
            )
        c = batch.request_counts
        log(f"  {batch.processing_status}: {c.processing} processing, {c.succeeded} done")
        sleep(lc["poll_seconds"])

    items = pd.read_parquet(out / items_file)
    rows: dict[str, dict[str, Any]] = {}
    for r in client.messages.batches.results(state["batch_id"]):
        if r.result.type == "succeeded":
            rows[r.custom_id] = parse_message(r.result.message, check)
        else:
            rows[r.custom_id] = {"status": r.result.type}
    res = pd.DataFrame([{"custom_id": k, **v} for k, v in rows.items()])
    df = items.merge(res, on="custom_id", how="left") if len(res) else items.copy()
    df["status"] = df.status.fillna("missing") if "status" in df else "missing"
    for col in ("input_tokens", "output_tokens"):
        df[col] = df[col].fillna(0).astype(int) if col in df else 0
    return Collected(df=df, state=state)


def mark_collected(out: Path, state: dict[str, Any]) -> None:
    state["collected"] = True
    (out / "batch.json").write_text(json.dumps(state, indent=2) + "\n", "utf-8")


def usage(df: pd.DataFrame, lc: dict[str, Any]) -> dict[str, Any]:
    """The tokens a collected run used and what they cost (and the mean answer, for the next
    estimate's `typical_output_tokens`)."""
    tin, tout = int(df.input_tokens.sum()), int(df.output_tokens.sum())
    answered = int((df.output_tokens > 0).sum())
    return {
        "input_tokens": tin,
        "output_tokens": tout,
        "mean_output_tokens": round(tout / answered) if answered else None,
        "usd": usd(tin, tout, lc["price_per_mtok"]),
    }


def ensure_columns(df: pd.DataFrame, columns: dict[str, Any]) -> pd.DataFrame:
    """The answer's columns present even when no answer was read (a batch of errors)."""
    for col, default in columns.items():
        if col not in df:
            df[col] = default
    return df
