"""English and Hebrew subtitles from a film's narration timeline (run voice.py first).

Run: uv run python video/tools/subs.py a [--preview]
Writes video/out/<film>/<film>.en.srt and <film>.he.srt (UTF-8 with BOM), the same cues in both.
A script line longer than one cue (two rows of MAX_ROW characters) is split in both languages at
the same place; its time is shared in proportion to the English characters. --preview also writes
preview.mp4: the mix (music.py) or else the narration on the film's ground colour, with both
files as soft subtitle tracks.
"""

from __future__ import annotations

import argparse
import math
import re

from common import ffmpeg, film_dir, read_json

MAX_ROW = 42  # characters per subtitle row; two rows per cue
MIN_CUE = 1.0  # seconds a cue stays up, at least
HOLD = 0.4  # seconds a cue stays after its speech, unless the next one starts
RLM = "‏"  # keeps Hebrew punctuation on the right side in players
SPLIT_AFTER = re.compile(r"[,:;.?!]$")


def split_words(text: str, parts: int) -> list[str]:
    """Split `text` into `parts` runs of whole words, balanced by length, preferring punctuation."""
    words = text.split()
    if parts <= 1 or len(words) < parts:
        return [text]
    total = len(text)
    cuts, start = [], 0
    for p in range(1, parts):
        target = total * p / parts
        best, best_cost = None, math.inf
        pos = 0
        for i, w in enumerate(words[:-1]):
            pos += len(w) + 1
            if i < start:
                continue
            cost = abs(pos - target) - (8 if SPLIT_AFTER.search(w) else 0)
            if cost < best_cost:
                best, best_cost = i + 1, cost
        cuts.append(best)
        start = best
    bounds = [0, *cuts, len(words)]
    return [" ".join(words[a:b]) for a, b in zip(bounds, bounds[1:], strict=False)]


def wrap(text: str) -> list[str]:
    """One or two rows, split near the middle."""
    if len(text) <= MAX_ROW:
        return [text]
    return split_words(text, 2)


def cues_for(lines: list[dict]) -> list[tuple[float, float, str, str]]:
    cues = []
    for line in lines:
        en, he = line["en"], line["he"]
        parts = max(math.ceil(len(en) / (2 * MAX_ROW)), math.ceil(len(he) / (2 * MAX_ROW)))
        en_parts, he_parts = split_words(en, parts), split_words(he, parts)
        if len(en_parts) != len(he_parts):
            en_parts, he_parts = [en], [he]
        s0, s1 = line["speech"]
        chars = sum(len(p) for p in en_parts)
        t, done = s0, 0
        for e, h in zip(en_parts, he_parts, strict=True):
            done += len(e)
            end = s0 + (s1 - s0) * done / chars
            cues.append((t, end, e, h))
            t = end
    out = []
    for i, (a, b, e, h) in enumerate(cues):
        nxt = cues[i + 1][0] if i + 1 < len(cues) else math.inf
        end = min(max(b + HOLD, a + MIN_CUE), nxt - 0.04)
        out.append((a, end, e, h))
    return out


def stamp(t: float) -> str:
    ms = round(t * 1000)
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def srt(cues, lang: str) -> str:
    blocks = []
    for n, (a, b, en, he) in enumerate(cues, 1):
        rows = wrap(en) if lang == "en" else [f"{RLM}{r}{RLM}" for r in wrap(he)]
        blocks.append(f"{n}\n{stamp(a)} --> {stamp(b)}\n" + "\n".join(rows) + "\n")
    return "\n".join(blocks)


def check(cues) -> list[str]:
    problems = []
    for i, (a, b, en, he) in enumerate(cues):
        if b <= a:
            problems.append(f"cue {i + 1}: ends before it starts")
        if i and a < cues[i - 1][1]:
            problems.append(f"cue {i + 1}: overlaps the previous cue")
        for lang, text in (("en", en), ("he", he)):
            rows = wrap(text)
            if len(rows) > 2 or any(len(r) > MAX_ROW + 6 for r in rows):
                problems.append(f"cue {i + 1} ({lang}): too long: {text}")
    return problems


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("film", choices=["a", "b"])
    parser.add_argument("--preview", action="store_true")
    args = parser.parse_args()
    out = film_dir(args.film)
    timing = read_json(out / "timing.json")
    cues = cues_for([line for scene in timing["scenes"] for line in scene["lines"]])
    for lang in ("en", "he"):
        (out / f"{args.film}.{lang}.srt").write_text(srt(cues, lang), encoding="utf-8-sig")
    problems = check(cues)
    print(f"film {args.film}: {len(cues)} cues", *problems, sep="\n  ")
    if args.preview:
        ffmpeg(
            "-f", "lavfi", "-i", f"color=c=0x0B1320:s=1280x720:r=2:d={timing['duration']}",
            "-i", str(out / ("mix.wav" if (out / "mix.wav").exists() else "vo.wav")),
            "-i", str(out / f"{args.film}.en.srt"),
            "-i", str(out / f"{args.film}.he.srt"),
            "-map", "0", "-map", "1", "-map", "2", "-map", "3",
            "-c:v", "libx264", "-preset", "ultrafast", "-tune", "stillimage",
            "-c:a", "aac", "-b:a", "192k", "-c:s", "mov_text",
            "-metadata:s:s:0", "language=eng", "-metadata:s:s:1", "language=heb",
            str(out / "preview.mp4"),
        )  # fmt: skip
        print(f"  {out / 'preview.mp4'}")


if __name__ == "__main__":
    main()
