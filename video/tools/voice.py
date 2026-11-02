"""Narration for a film: one Edge TTS clip per script line, laid out on the film's timeline.

Run: uv run --with edge-tts python video/tools/voice.py a [--voice NAME]
     uv run --with edge-tts python video/tools/voice.py samples
Writes video/out/<film>/vo/<scene>-<n>.mp3 (+ .json: the words' times and the cache key),
vo.wav (48 kHz mono) and timing.json; `samples` writes out/samples/<voice>.mp3 to choose a voice.
A clip is fetched again only when its voice, rate or spoken text changes.
"""

from __future__ import annotations

import argparse
import asyncio
import wave

import edge_tts
import numpy as np
from common import OUT, RATE, ffmpeg, film_dir, load_script, read_json, write_json

SAMPLE_VOICES = [
    "en-US-JennyNeural",
    "en-US-AriaNeural",
    "en-US-AvaNeural",
    "en-US-EmmaNeural",
    "en-GB-SoniaNeural",
]
SAMPLE_TEXT = (
    "The Hebrew Bible has 23,206 verses. Psalm 14 and Psalm 53 are almost the same poem. "
    "Without being told where to look, the system splits Psalms almost exactly where scholars "
    "mark the Elohistic Psalter. The second retriever is semantic, built on Berel three."
)


async def synthesize(text: str, voice: str, rate: str) -> tuple[bytes, list[dict]]:
    """The clip's MP3 bytes and its words: start and duration in seconds."""
    comm = edge_tts.Communicate(text, voice, rate=rate, boundary="WordBoundary")
    audio, words = bytearray(), []
    async for chunk in comm.stream():
        if chunk["type"] == "audio":
            audio += chunk["data"]
        elif chunk["type"] == "WordBoundary":
            words.append(
                {
                    "t": chunk["offset"] / 1e7,  # 100 ns units
                    "d": chunk["duration"] / 1e7,
                    "text": chunk["text"],
                }
            )
    return bytes(audio), words


def decode(path) -> np.ndarray:
    raw = ffmpeg("-i", str(path), "-f", "f32le", "-ac", "1", "-ar", str(RATE), "-")
    return np.frombuffer(raw, dtype=np.float32)


def write_wav(path, samples: np.ndarray) -> None:
    pcm = (np.clip(samples, -1, 1) * 32767).astype("<i2")
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(pcm.tobytes())


async def fetch_clips(film: str, voice: str | None) -> dict:
    script = load_script(film)
    voice = voice or script["voice"]
    rate = script["rate"]
    vo = film_dir(film) / "vo"
    vo.mkdir(exist_ok=True)
    fetched = 0
    for scene in script["scenes"]:
        for i, line in enumerate(scene["lines"]):
            text = line.get("say") or line["en"]
            stem = vo / f"{scene['id']}-{i:02d}"
            key = {"voice": voice, "rate": rate, "text": text}
            meta_path = stem.with_suffix(".json")
            if meta_path.exists() and read_json(meta_path)["key"] == key:
                continue
            audio, words = await synthesize(text, voice, rate)
            stem.with_suffix(".mp3").write_bytes(audio)
            write_json(meta_path, {"key": key, "words": words})
            fetched += 1
    print(f"film {film}: {fetched} clips fetched, voice {voice}")
    return script


def lay_out(film: str, script: dict) -> None:
    """Place the clips on one timeline: lead-in, line gaps, scene gaps, tail."""
    timing = script["timing"]
    vo = film_dir(film) / "vo"
    t = timing["lead_in"]
    pieces: list[tuple[float, np.ndarray]] = []
    scenes = []
    for s, scene in enumerate(script["scenes"]):
        if s:
            t += timing["scene_gap"] - timing["line_gap"]
        lines = []
        start = t
        for i, line in enumerate(scene["lines"]):
            stem = vo / f"{scene['id']}-{i:02d}"
            clip = decode(stem.with_suffix(".mp3"))
            words = read_json(stem.with_suffix(".json"))["words"]
            dur = len(clip) / RATE
            # speech inside the clip, without Edge's padding
            speech = (
                [t + words[0]["t"], t + words[-1]["t"] + words[-1]["d"]] if words else [t, t + dur]
            )
            pieces.append((t, clip))
            lines.append(
                {
                    "start": round(t, 3),
                    "end": round(t + dur, 3),
                    "speech": [round(x, 3) for x in speech],
                    "en": line["en"],
                    "he": line["he"],
                    "words": [
                        {"t": round(t + w["t"], 3), "d": round(w["d"], 3), "text": w["text"]}
                        for w in words
                    ],
                }
            )
            t += dur + timing["line_gap"]
        scenes.append(
            {"id": scene["id"], "start": round(start, 3), "end": round(t, 3), "lines": lines}
        )
    total = t - timing["line_gap"] + timing["tail"]
    mix = np.zeros(int(total * RATE) + 1, dtype=np.float32)
    for at, clip in pieces:
        i = int(at * RATE)
        mix[i : i + len(clip)] += clip
    write_wav(film_dir(film) / "vo.wav", mix)
    write_json(
        film_dir(film) / "timing.json",
        {"film": film, "title": script["title"], "duration": round(total, 3), "scenes": scenes},
    )
    m, sec = divmod(total, 60)
    print(f"film {film}: {int(m)}:{sec:05.2f}, {len(pieces)} lines, {len(scenes)} scenes")
    for sc in scenes:
        print(f"  {sc['start']:7.2f}  {sc['id']}")


async def samples() -> None:
    out = OUT / "samples"
    out.mkdir(parents=True, exist_ok=True)
    for voice in SAMPLE_VOICES:
        audio, _ = await synthesize(SAMPLE_TEXT, voice, "-5%")
        (out / f"{voice}.mp3").write_bytes(audio)
        print(out / f"{voice}.mp3")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("film", choices=["a", "b", "samples"])
    parser.add_argument("--voice", help="override the script's voice")
    args = parser.parse_args()
    if args.film == "samples":
        asyncio.run(samples())
        return
    script = asyncio.run(fetch_clips(args.film, args.voice))
    lay_out(args.film, script)


if __name__ == "__main__":
    main()
