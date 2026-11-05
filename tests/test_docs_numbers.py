"""The numbers RESULTS.md gives for the current build, checked against that build's meta files.

Each entry is a phrase of RESULTS.md (a regex whose one group is the number as printed) and the
meta value it reports, formatted the way the text prints it. A paragraph keeps its earlier runs as
history; only sentences about the current build are listed here. Skipped where the artifacts are
not there (CI has none): run it locally after a rebuild, before the docs are committed.
"""

import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "docs" / "RESULTS.md"
ART = ROOT / "artifacts"


def meta(path: str, *keys: str):
    v = json.loads((ART / path).read_text("utf-8"))
    for k in keys:
        v = v[k]
    return v


def f3(x: float) -> str:
    return f"{x:.3f}"


def pct(x: float) -> str:
    return f"{round(100 * x)}"


CHECKS = [
    # the dev table (refreshed M115): fused verse nDCG@10
    (
        r"\| fused \| [\d.]+ \| [\d.]+ \| [\d.]+ \| [\d.]+ \| [\d.]+ \| ([\d.]+) \| 884 \|",
        "eval/metrics.json",
        ("splits", "dev", "results", "verse", "fused", "ndcg@10"),
        f3,
    ),
    (
        r"Dev nDCG@10 \(current build\): lexical [\d.]+, fused ([\d.]+)",
        "eval/etcbc.json",
        ("results", "fused", "etcbc", "ndcg@10"),
        f3,
    ),
    (
        r"Dev nDCG@10 \(current build\): lexical ([\d.]+)",
        "eval/etcbc.json",
        ("results", "lexical", "etcbc", "ndcg@10"),
        f3,
    ),
    (
        r"held out (\d+) / \d+ right, \d+ undecided \(p 9",
        "borrowing/borrowing.meta.json",
        ("held_out", "agree"),
        str,
    ),
    (
        r"held out \d+ / \d+ right, (\d+) undecided \(p 9",
        "borrowing/borrowing.meta.json",
        ("held_out", "unclear"),
        str,
    ),
    (
        r"agrees with the spelling sign in (\d+) of \d+ \(p 5e-7\)",
        "echoes/echoes.meta.json",
        ("checks", "spelling", "agree"),
        str,
    ),
    (
        r"(\d+) language directions run against the canon; the same",
        "echoes/echoes.meta.json",
        ("language_backward",),
        str,
    ),
    (
        r"lose the copy they had found and stay unresolved: (\d+) resolved",
        "citations/citations.meta.json",
        ("resolved",),
        str,
    ),
    (
        r"as commanded (\d+) % against \d+ % \(p 0\.0096\) and the gold check unchanged",
        "citations/citations.meta.json",
        ("families", "command", "share"),
        pct,
    ),
    (
        r"still (\d+) of 10 \(Neh 3 reached",
        "forms/forms.meta.json",
        ("lists", "known_found"),
        str,
    ),
    (
        r"short of the two thirds that count as found\), (\d+) lists over",
        "forms/forms.meta.json",
        ("lists", "observed"),
        str,
    ),
    (
        r"held-out AUC Job ([\d.]+), Ps",
        "parallelism/parallelism.meta.json",
        ("held_out_auc", "Job"),
        f3,
    ),
    (
        r"נא \*\*\+7\.0 points\*\* within books \(14\.3 % against 8\.8 %, (\d+) / 140",
        "dialogue/dialogue.meta.json",
        ("tests", "particle", "up", "count"),
        str,
    ),
    (
        r"602 random dev pairs: AUC ([\d.]+) \(holds\)",
        "llm_pool/llm_pool.meta.json",
        ("calibration", "auc"),
        f3,
    ),
    (
        r"\| fused \| [\d.]+ \| [\d.]+ \| ([\d.]+) \| [\d.]+ \| [\d.]+ \|\n\| fused_rerank",
        "eval/llm_pool.json",
        ("rows", 2, "llm_ndcg10"),
        f3,
    ),
]


@pytest.mark.skipif(not (ART / "eval" / "metrics.json").exists(), reason="no build artifacts")
@pytest.mark.parametrize(("pattern", "path", "keys", "fmt"), CHECKS, ids=[c[1] for c in CHECKS])
def test_results_quote_the_build(pattern, path, keys, fmt):
    text = RESULTS.read_text("utf-8")
    found = re.search(pattern, text)
    assert found, f"phrase not in RESULTS.md: {pattern}"
    assert found.group(1) == fmt(meta(path, *keys)), f"{path} {'.'.join(keys)}"
