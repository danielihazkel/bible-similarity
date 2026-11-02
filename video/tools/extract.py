"""The data the films draw, read from the results DB and the pipeline (never typed by hand).

Run: uv run python video/tools/extract.py
Writes video/out/data/*.json (gitignored: it holds Hebrew text and results):
  field     every verse's book, book starts, and cross-book echo arcs (fused rank-1 pairs)
  pairs     Psalm 14 / 53 and II Samuel 22 / Psalm 18, verse by verse, with their Hebrew
  verses    the few Hebrew verses set on screen (te'amim kept only where a scene needs them)
  tree      the line from Adam to David and the children branching off it
  land      the basemap around the Land of Israel, the best-attested places, a story's path
  chrono    the dated events from Adam to the Exodus
  lists     one verse's top matches by words, by meaning and fused (film B's fusion scene)
  stages    the pipeline's stage graph (film B)
  numbers   the figures the narration quotes, from the DB's meta and docs/RESULTS.md
"""

from __future__ import annotations

import json
import random
import re
import sqlite3
from pathlib import Path

from common import OUT, VIDEO, write_json

ROOT = VIDEO.parent
DB = ROOT / "artifacts" / "results.sqlite"
TEAMIM = re.compile("[֑-ֽ֯]")  # cantillation marks and meteg; niqqud stays
BBOX = (33.6, 29.4, 37.2, 34.0)  # lon / lat around the Land of Israel


def connect() -> sqlite3.Connection:
    return sqlite3.connect(f"file:{DB.as_posix()}?mode=ro", uri=True)


def vid(c, ref: str) -> int:
    return c.execute("select verse_id from verses where ref = ?", (ref,)).fetchone()[0]


def numeral(n: int) -> str:
    """Hebrew letters for a chapter or verse number (טו and טז, not יה and יו)."""
    out = ""
    for value, letter in ((400, "ת"), (300, "ש"), (200, "ר"), (100, "ק")):
        while n >= value:
            out, n = out + letter, n - value
    if n in (15, 16):
        return out + {15: "טו", 16: "טז"}[n]
    tens, ones = divmod(n, 10)
    return out + " יכלמנסעפצ"[tens].strip() + " אבגדהוזחט"[ones].strip()


def he_ref(c, v: int) -> str:
    q = "select b.he_name, v.chapter, v.verse from verses v join books b using (book_id)"
    book, ch, vs = c.execute(q + " where v.verse_id = ?", (v,)).fetchone()
    return f"{book} {numeral(ch)} {numeral(vs)}"


def verse(c, v: int, teamim=False) -> dict:
    q = "select ref, text_display from verses where verse_id = ?"
    ref, text = c.execute(q, (v,)).fetchone()
    text = re.sub(r"<[^>]+>", "", text)
    return {"id": v, "ref": ref, "he": text if teamim else TEAMIM.sub("", text)}


def field(c) -> dict:
    q = "select book_id, name, he_name, section from books order by book_id"
    books = c.execute(q).fetchall()
    vb = [b for (b,) in c.execute("select book_id from verses order by verse_id")]
    starts = [vb.index(b) for b, *_ in books]
    rows = c.execute(
        "select src_id, tgt_id, score from matches"  # match ids are 'v:<verse_id>'
        " where unit_type = 'verse' and mode = 'fused' and rank <= 3"
    ).fetchall()
    rows = [(int(a[2:]), int(b[2:]), s) for a, b, s in rows]
    rows = sorted(((a, b, s) for a, b, s in rows if vb[a] != vb[b]), key=lambda r: -r[2])
    seen, unique = set(), []
    for a, b, s in rows:
        key = (min(a, b), max(a, b))
        if key not in seen:
            seen.add(key)
            unique.append((*key, s))
    rng = random.Random(7)
    rest = unique[300:]
    arcs = unique[:300] + rng.sample(rest, min(500, len(rest)))
    return {
        "n": len(vb),
        "book": vb,
        "books": [
            {"id": b, "en": n, "he": h, "section": s, "start": st}
            for (b, n, h, s), st in zip(books, starts, strict=True)
        ],
        "arcs": [[a, b, round(s, 4)] for a, b, s in arcs],
    }


def pairs(c) -> dict:
    out = {}
    # II Samuel 22 / Psalm 18: the stored parallel sequence
    a0 = vid(c, "II Samuel 22:1")
    seq = c.execute(
        "select pairs from sequences where a_start = ? and direction = 'forward'"
        " order by n_pairs desc limit 1",
        (a0,),
    ).fetchone()
    out["sam_ps"] = [[a, b] for a, b, *_ in json.loads(seq[0])]
    # Psalm 14 / 53: each verse's best fused match inside the other psalm
    p14 = [v for (v,) in c.execute(
        "select verse_id from verses where book_id = (select book_id from books"
        " where name = 'Psalms') and chapter = 14 order by verse")]  # fmt: skip
    p53 = [v for (v,) in c.execute(
        "select verse_id from verses where book_id = (select book_id from books"
        " where name = 'Psalms') and chapter = 53 order by verse")]  # fmt: skip
    ps = []
    targets = ",".join(f"'v:{t}'" for t in p53)
    for v in p14:
        row = c.execute(
            "select tgt_id from matches where unit_type = 'verse' and mode = 'fused'"
            f" and src_id = ? and tgt_id in ({targets}) order by rank limit 1",
            (f"v:{v}",),
        ).fetchone()
        if row:
            ps.append([v, int(row[0][2:])])
    out["ps14_53"] = ps
    out["ps14"], out["ps53"] = p14, p53
    out["sam22"] = list(range(a0, a0 + 51))
    ps18 = vid(c, "Psalms 18:1")
    out["ps18"] = list(range(ps18, ps18 + 51))
    out["text"] = {
        "ps14_1": verse(c, vid(c, "Psalms 14:1")),
        "ps53_2": verse(c, vid(c, "Psalms 53:2")),
    }
    return out


def verses(c) -> dict:
    return {
        "gen1_1": verse(c, 0, teamim=True),  # the reader scene splits it at the atnah
        "gen1_1_plain": verse(c, 0),
        "gen3_9": verse(c, vid(c, "Genesis 3:9"), teamim=True),  # speech, God to Adam
        "lam3_1": verse(c, vid(c, "Lamentations 3:1"), teamim=True),
        "ps119_1": verse(c, vid(c, "Psalms 119:1")),
    }


def tree(c) -> dict:
    he = dict(c.execute("select person_id, he from genealogy_persons"))
    fathers = {}
    children: dict[int, list[int]] = {}
    for parent, child, kind in c.execute(
        "select parent_id, child_id, kind from genealogy_links"
        " where role = 'father' and kind in ('son', 'descendant', 'founder')"
        " order by seq"
    ):
        fathers.setdefault(child, parent)
        if kind == "son":
            children.setdefault(parent, []).append(child)
    adam = c.execute("select person_id from genealogy_persons where key like 'Adam@Gen.2%'")
    adam = adam.fetchone()[0]
    david = c.execute("select person_id from genealogy_persons where key like 'David@Rut%'")
    david = david.fetchone()[0]
    line = [david]
    while line[-1] != adam and line[-1] in fathers and len(line) < 80:
        line.append(fathers[line[-1]])
    line.reverse()
    on_line = set(line)
    branches = []
    for p in line:
        kids = [k for k in dict.fromkeys(children.get(p, [])) if k not in on_line][:7]
        branches.append([{"id": k, "he": he.get(k, "")} for k in kids])
    conflicts = {k for (k,) in c.execute("select child_id from genealogy_conflicts")}
    proofs = []  # the first proof verse of each link down the line
    for parent, child in zip(line, line[1:], strict=False):
        row = c.execute(
            "select p.verse_id from genealogy_links l join genealogy_proofs p using (link_id)"
            " where l.parent_id = ? and l.child_id = ? order by p.rank limit 1",
            (parent, child),
        ).fetchone()
        proofs.append(he_ref(c, row[0]) if row else "")
    return {
        "reaches_adam": line[0] == adam,
        # people on the line or branching off it whose parent or name two passages dispute
        "conflicts": [
            p for p in [*line, *(k["id"] for b in branches for k in b)] if p in conflicts
        ],
        "line": [{"id": p, "he": he.get(p, "")} for p in line],
        "proofs": proofs,
        "branches": branches,
    }


def land(c) -> dict:
    x0, y0, x1, y1 = BBOX

    def runs(rings, closed):
        """Each ring cut into the runs of points inside the frame (plus a margin), so the pen
        draws only coast that is on screen and no line jumps across where points were left out.
        A ring wholly inside stays closed."""
        m = 0.4
        out = []
        for ring in rings:
            inside = [x0 - m <= x <= x1 + m and y0 - m <= y <= y1 + m for x, y in ring]
            pts = [[round(x, 3), round(y, 3)] for x, y in ring]
            if all(inside):
                out.append({"pts": pts, "closed": closed})
                continue
            cur = []
            for pt, ok in zip(pts, inside, strict=True):
                if ok:
                    cur.append(pt)
                elif cur:
                    if len(cur) > 1:
                        out.append({"pts": cur, "closed": False})
                    cur = []
            if len(cur) > 1:
                out.append({"pts": cur, "closed": False})
        return out

    shapes = []
    for layer, name, rings in c.execute("select layer, name, rings from map_shapes"):
        kept = runs(json.loads(rings), closed=layer != "rivers")
        if kept:
            shapes.append({"layer": layer, "name": name, "runs": kept})
    places = [
        {"id": i, "he": h, "lat": la, "lon": lo, "n": n}
        for i, h, la, lo, n in c.execute(
            "select place_id, he, lat, lon, n_verses from places where lat is not null"
            " and lon between ? and ? and lat between ? and ? and score >= 500"
            " order by n_verses desc limit 140",
            (x0, x1, y0, y1),
        )
    ]
    # a story crossing the land: the centre of each chapter of I and II Samuel
    path = [
        {"book": b, "chapter": ch, "lat": la, "lon": lo, "top": top}
        for b, ch, la, lo, top in c.execute(
            "select a.book_id, a.chapter, a.lat, a.lon, p.he from place_arc_chapters a"
            " left join places p on p.place_id = a.top_place"
            " where a.book_id in (select book_id from books where name in"
            " ('I Samuel', 'II Samuel')) and a.lat is not null order by a.first_vid"
        )
    ]
    return {"bbox": BBOX, "shapes": shapes, "places": places, "path": path}


def chrono(c) -> dict:
    events = [
        {"event": e, "he": n, "year": y, "conflict": bool(k)}
        for e, n, y, k in c.execute(
            "select event, name, year, conflict from chronology_events"
            " where used = 1 and event not like '%.death' order by year"
        )
    ]
    known = json.loads(c.execute("select value from meta where key = 'chronology'").fetchone()[0])
    return {"events": events, "known": known["known"]}


def retold(c) -> dict:
    """Samuel and Kings told again in Chronicles: the parallel runs beyond chance."""
    names = ("I Samuel", "II Samuel", "I Kings", "II Kings", "I Chronicles", "II Chronicles")
    books = {}
    for n in names:
        b, first, last = c.execute(
            "select v.book_id, min(v.verse_id), max(v.verse_id) from verses v"
            " join books b on b.book_id = v.book_id where b.name = ?",
            (n,),
        ).fetchone()
        books[n] = {"id": b, "first": first, "last": last}
    ids = {v["id"]: n for n, v in books.items()}
    runs = [
        {"a": a, "a_end": ae, "b": b, "b_end": be, "n": n}
        for a, ae, b, be, ab, bb, n in c.execute(
            "select a_start, a_end, b_start, b_end, a_book, b_book, n_pairs from sequences"
            " where q <= 0.05 order by a_start"
        )
        if ids.get(ab, "").endswith(("Samuel", "Kings")) and ids.get(bb, "").endswith("Chronicles")
    ]
    return {"books": books, "runs": runs}


def findings(c) -> dict:
    cut1, cut2, s1, s2, s3, p = c.execute(
        "select cut1, cut2, share1, share2, share3, p from divine_books"
        " where book_id = (select book_id from books where name = 'Psalms')"
    ).fetchone()
    judges = [
        {"judge": j, "he": h, "slots": n}
        for j, h, n in c.execute(
            "select episode, judge, n_slots from frameworks_episodes order by seq"
        )
    ]
    return {
        "psalms": {"cut1": cut1, "cut2": cut2, "shares": [s1, s2, s3], "p": p},
        "judges": judges,
    }


def lists(c) -> dict:
    v = vid(c, "Psalms 14:1")
    out = {"query": verse(c, v)}
    for mode in ("lexical", "semantic", "fused"):
        hits = c.execute(
            "select tgt_id, score from matches where unit_type = 'verse' and mode = ?"
            " and src_id = ? order by rank limit 8",
            (mode, f"v:{v}"),
        ).fetchall()
        out[mode] = [{"ref": verse(c, int(t[2:]))["ref"], "score": round(s, 4)} for t, s in hits]
    return out


def stages() -> dict:
    from bsim.pipeline import DEPS, STAGES

    order = list(STAGES)
    return {"order": order, "deps": {s: sorted(DEPS.get(s, ())) for s in order}}


def numbers(c) -> dict:
    meta = {k: json.loads(v) for k, v in c.execute("select key, value from meta")}
    results = (ROOT / "docs" / "RESULTS.md").read_text(encoding="utf-8")

    def row(section: str, system: str) -> list[float]:
        part = results.split(section, 1)[1]
        line = re.search(rf"^\| {re.escape(system)} \|(.+)$", part, re.M).group(1)
        return [float(x) for x in re.findall(r"\d+\.\d+", line)]

    test = results.split("## Test", 1)[1].split("## Dev", 1)[0]
    test_verse = test.split("### verse", 1)[1]

    def test_row(system):
        line = re.search(rf"^\| {re.escape(system)} \|(.+)$", test_verse, re.M).group(1)
        return [float(x) for x in re.findall(r"\d+\.\d+", line)]

    return {
        "rows": meta["row_counts"],
        "similar_ms": meta["similar_benchmark"]["median_ms"],
        "stages": len(stages()["order"]),
        "test_ndcg10": {s: test_row(s)[5] for s in ("fused", "bm25_lemma", "berel_sup_csls")},
        "dev_ndcg10": {
            s: row("## Dev", s)[5]
            for s in ("fused", "bm25_lemma", "berel_sup_csls", "berel_mean", "berel_sup")
        },
    }


def dev(c) -> dict:
    """Film B: the book split, the Pentateuch split against the critics' P, and the figures
    the narration quotes, from the DB's meta and docs/RESULTS.md."""
    splits = json.loads((ROOT / "data" / "processed" / "splits.json").read_text(encoding="utf-8"))
    books = [
        {"en": n, "he": h, "verses": k, "split": splits["books"][n]}
        for n, h, k in c.execute(
            "select b.name, b.he_name, count(*) from books b join verses v using (book_id)"
            " group by b.book_id order by b.book_id"
        )
    ]
    # Genesis–Numbers in 300 stretches: the share of P-like verses, found and the critics'
    rows = c.execute("select side, reference from pentateuch_verses order by verse_id").fetchall()
    bins = 300
    strip = []
    for i in range(bins):
        part = rows[i * len(rows) // bins : (i + 1) * len(rows) // bins]
        strip.append(
            [
                round(sum(r[0] == "P" for r in part) / len(part), 3),
                round(sum(r[1] == "P" for r in part) / len(part), 3),
            ]
        )
    meta = {k: json.loads(v) for k, v in c.execute("select key, value from meta")}
    results = (ROOT / "docs" / "RESULTS.md").read_text(encoding="utf-8")

    def find(pattern: str) -> list[float]:
        m = re.search(pattern, results)
        if not m:
            raise ValueError(f"not in RESULTS.md: {pattern}")
        return [float(x.replace("−", "-")) for x in m.groups()]

    def table(section: str, level: str, system: str) -> float:
        part = results.split(section, 1)[1].split(f"### {level}", 1)[1]
        line = re.search(rf"^\| {re.escape(system)} \|(.+)$", part, re.M).group(1)
        return float(re.findall(r"\d+\.\d+", line)[5])  # nDCG@10

    num = r"([+−-]?\d+\.\d+)"
    rerank = find(rf"fused_rerank − fused nDCG@10: {num}, 95 % CI \[{num}, {num}\]")
    encoders = {
        name: find(rf"{re.escape(name)} {num} / {num} / {num}")[0]
        for name in ("DictaBERT base", "large", "multilingual-E5", "Qwen3")
    }
    test = {
        level: {
            "fused": table("## Test", level, "fused"),
            "lexical": table("## Test", level, "bm25_lemma" if level == "verse" else "tfidf"),
            "semantic": table(
                "## Test", level, "berel_sup_csls" if level == "verse" else "berel_sup_csls_bma"
            ),
        }
        for level in ("verse", "chapter", "pericope")
    }
    dev_verse = {
        s_: table("## Dev", "verse", s_)
        for s_ in (
            "berel_mean",
            "berel_simcse",
            "berel_sup",
            "berel_sup_csls",
            "bm25_lemma",
            "fused",
        )
    }
    return {
        "books": books,
        "strip": strip,
        "kappa": meta["pentateuch"]["tests"]["kappa"],
        "nmi": meta["psalms"]["genre_test"],
        "rerank": rerank,
        "encoders": encoders,
        "test": test,
        "dev_verse": dev_verse,
        "matches": sum(v for k, v in meta["row_counts"].items() if k.startswith("matches/")),
        "words": meta["row_counts"]["words"],
        "similar_ms": meta["similar_benchmark"]["median_ms"],
    }


def main() -> None:
    out = OUT / "data"
    out.mkdir(parents=True, exist_ok=True)
    with connect() as c:
        parts = {
            "field": field(c),
            "pairs": pairs(c),
            "verses": verses(c),
            "tree": tree(c),
            "land": land(c),
            "chrono": chrono(c),
            "lists": lists(c),
            "retold": retold(c),
            "findings": findings(c),
            "dev": dev(c),
            "stages": stages(),
            "numbers": numbers(c),
        }
    for name, data in parts.items():
        write_json(out / f"{name}.json", data)
        print(f"{name:8s} {(out / f'{name}.json').stat().st_size / 1024:8.1f} KB")
    t = parts["tree"]
    print(f"tree: {len(t['line'])} generations, reaches Adam: {t['reaches_adam']}")


if __name__ == "__main__":
    Path(OUT).mkdir(exist_ok=True)
    main()
