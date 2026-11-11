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
    (
        r"with the same prompt, definitions and calibration, for \$1\.37\. Calibration: the owner's"
        r" place sample (\d+) / 50 right",
        "llm_audit_pages_m158/llm_audit.meta.json",
        ("calibration", "places_right"),
        lambda x: x.split(" / ")[0],
    ),
    (
        r"the 302 resumptive repetitions at p ≤ 0\.05, (\d+) right of 50",
        "llm_audit_pages_m158/llm_audit.meta.json",
        ("detectors", "brackets", "marked", "right"),
        str,
    ),
    (
        r"\(seed 202\), for \$1\.22\. Calibration: the owner's place sample (\d+) / 50 right",
        "llm_audit_pages/llm_audit.meta.json",
        ("calibration", "places_right"),
        lambda x: x.split(" / ")[0],
    ),
    (
        r"\| naming etiologies \| 65 \(was 111\) \| 50 \| (\d+) \|",
        "llm_audit_pages/llm_audit.meta.json",
        ("detectors", "etiologies", "shown", "right"),
        str,
    ),
    (
        r"the claim itself is not borne out for the same names"
        r" \(late 64 % short, early 26 %, p ([\d.]+)",
        "theophoric/theophoric.meta.json",
        ("claim", "p"),
        f3,
    ),
    (
        r"held-out AUC 0\.948 → 0\.889, without the lexemes 0\.895 → 0\.852,"
        r" Chronicles later in (\d+) →",
        "dating/dating.meta.json",
        ("synoptic", "later"),
        str,
    ),
    (
        r"([\d,]+) pauses of background inside the chain in the narrative books",
        "mainline/mainline.meta.json",
        ("pauses",),
        lambda x: f"{x:,}",
    ),
    (
        r"Claude's reading of 50 pauses drawn from the list, for \$0\.22: (\d+) right",
        "llm_audit_pages_m164/llm_audit.meta.json",
        ("detectors", "mainline", "shown", "right"),
        str,
    ),
    (
        r"by rule over their words, \d+ messenger formulas, (\d+) woe sayings",
        "prophetic/prophetic.meta.json",
        ("counts", "woe"),
        str,
    ),
    (
        r"Claude's reading of 50 findings of the four judged forms, for \$0\.24: (\d+) right",
        "llm_audit_pages_m165/llm_audit.meta.json",
        ("detectors", "prophetic", "shown", "right"),
        str,
    ),
    (
        r"(\d+) law pairs matched across the codes on the fused list",
        "laws/laws.meta.json",
        ("pairs",),
        str,
    ),
    (
        r"set side by side, fixed before the run, (\d+) are found, by the aligned verses",
        "laws/laws.meta.json",
        ("known_found",),
        str,
    ),
    (
        r"by the aligned verses themselves also (\d+);",
        "laws/laws.meta.json",
        ("known_strict",),
        str,
    ),
    (
        r"\| `self` \| fused \| [^|]+ \| ([+−\-][\d.]+) \[",
        "eval/supervision_experiments.json",
        ("results", "self", "gains", "openbible", "fused", "mean"),
        lambda x: f"{x:+.4f}",
    ),
    (
        r"\| `self_ce` \| fused \| [^|]+ \| ([+−\-][\d.]+) \[",
        "eval/supervision_experiments.json",
        ("results", "self_ce", "gains", "openbible", "fused", "mean"),
        lambda x: f"{x:+.4f}",
    ),
]


@pytest.mark.skipif(not (ART / "eval" / "metrics.json").exists(), reason="no build artifacts")
@pytest.mark.parametrize(("pattern", "path", "keys", "fmt"), CHECKS, ids=[c[1] for c in CHECKS])
def test_results_quote_the_build(pattern, path, keys, fmt):
    text = RESULTS.read_text("utf-8")
    found = re.search(pattern, text)
    assert found, f"phrase not in RESULTS.md: {pattern}"
    assert found.group(1) == fmt(meta(path, *keys)), f"{path} {'.'.join(keys)}"
