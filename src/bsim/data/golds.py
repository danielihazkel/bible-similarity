"""`bsim build-golds`: the verse pairs of the second and third gold sets (DESIGN.md §16.41).

OpenBible's cross-references (§16.13) and ETCBC's parallel passages (§16.34), split by the
Sefaria book rule. Built right after `build-links`, before training: their train splits are extra
training pairs for the semantic model (`train.supervised.extra_pairs`), their dev splits are
scored by `bsim eval-openbible` / `bsim eval-etcbc` once the systems exist.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

Log = Callable[[str], None]


def run_build_golds(cfg: dict[str, Any], log: Log = print) -> None:
    from bsim.eval.etcbc import build_etcbc_links
    from bsim.eval.openbible import build_openbible_links

    build_openbible_links(cfg, log)
    build_etcbc_links(cfg, log)
