"""The film's score: an ancient-sounding bed laid on the narration's scene windows, then the mix.

Run: uv run python video/tools/music.py a        (after voice.py)
Writes video/out/<film>/music.wav (the score alone) and mix.wav (narration + score, ducked under
speech, -14 LUFS / -1 dBTP, 48 kHz stereo). Everything comes from the script's `music:` block;
`music.file` replaces the composed score with a track of your own, looped and faded.

The score, all synthesized and seeded: a kinnor-like lyre (Karplus-Strong plucked strings), a
tanpura-like drone on the root and fifth, a ney (breathy flute) in the hero and the outro, and a
tof (frame drum) in the hero, in the script's mode (maqam Hijaz / Ahava Rabbah by default).
"""

from __future__ import annotations

import argparse
import json
import math
import re
import subprocess
import wave

import numpy as np
from common import RATE, ffmpeg, film_dir, load_script, read_json
from scipy.signal import butter, oaconvolve, sosfilt

# --- instruments -----------------------------------------------------------------------------


def pluck(freq: float, dur: float, rng: np.random.Generator, vel=0.7, t60=3.0, bright=0.6):
    """Karplus-Strong string, computed one period at a time (vectorized within the period)."""
    n = max(2, round(RATE / freq - 0.5))  # the two-tap average adds half a sample
    length = int(dur * RATE)
    g = 10 ** (-3 / (t60 * freq))  # loss per period for the given T60
    # the string when let go, plucked at `pos`: its shape (a triangle, harmonics falling 12 dB an
    # octave) blended by `bright` with its velocity (a pulse, 6 dB an octave), plus a little noise
    pos = 0.15 + 0.2 * rng.random()
    x = np.arange(n) / n
    shape = np.where(x < pos, x / pos, (1 - x) / (1 - pos))
    speed = np.where(x < pos, 1 / pos, -1 / (1 - pos))
    shape, speed = (s - s.mean() for s in (shape, speed))
    burst = (1 - bright) * shape / shape.std() + bright * speed / speed.std()
    burst += 0.15 * bright * rng.uniform(-1, 1, n)
    burst -= burst.mean()  # no DC: the loop would carry it as a slow thump
    y = np.zeros(length + n + 1)
    y[1 : n + 1] = burst
    for k in range(n + 1, length + 1, n):
        end = min(k + n, length + 1)
        m = end - k
        y[k:end] = 0.5 * g * (y[k - n : k - n + m] + y[k - n - 1 : k - n - 1 + m])
    y = y[1 : length + 1]
    # the loop's whole-sample delay sounds RATE / (n + 0.5); play it back a touch faster or
    # slower so the string sounds `freq` exactly (up to ~7 cents off at A4 otherwise)
    speed = freq / (RATE / (n + 0.5))
    y = np.interp(np.arange(length) * speed, np.arange(length), y, right=0.0)
    y -= y.mean()
    fade = min(len(y), int(0.05 * RATE))
    y[-fade:] *= np.linspace(1, 0, fade)
    return (vel * y / (np.abs(y).max() + 1e-9)).astype(np.float32)


def ney(notes: list[tuple[float, float]], rng: np.random.Generator, vel=0.5):
    """A breathy flute line: (frequency, seconds) notes joined by short glides."""
    total = int(sum(d for _, d in notes) * RATE)
    freq = np.empty(total)
    i = 0
    for k, (f, d) in enumerate(notes):
        m = int(d * RATE) if k < len(notes) - 1 else total - i
        freq[i : i + m] = f
        glide = min(int(0.12 * RATE), m)
        if k:
            freq[i : i + glide] = np.linspace(notes[k - 1][0], f, glide)
        i += m
    t = np.arange(total) / RATE
    vib = 1 + 0.004 * np.sin(2 * np.pi * 5.2 * t) * np.clip(t / 1.5, 0, 1)
    phase = 2 * np.pi * np.cumsum(freq * vib) / RATE
    tone = np.sin(phase) + 0.25 * np.sin(2 * phase) + 0.08 * np.sin(3 * phase)
    breath = sosfilt(butter(2, [1200, 4000], "bandpass", fs=RATE, output="sos"),
                     rng.normal(0, 1, total))  # fmt: skip
    env = np.ones(total)
    att, rel = int(0.5 * RATE), int(1.2 * RATE)
    env[:att] = np.linspace(0, 1, att) ** 2
    env[-rel:] *= np.linspace(1, 0, rel) ** 1.5
    # each note swells a little
    i = 0
    for _f, d in notes:
        m = min(int(d * RATE), total - i)
        env[i : i + m] *= 0.85 + 0.15 * np.sin(np.linspace(0, np.pi, m))
        i += m
    y = (tone + 0.06 * breath) * env
    return (vel * y / (np.abs(y).max() + 1e-9)).astype(np.float32)


def drum(rng: np.random.Generator, dum: bool, vel=0.7):
    """Tof: a low skin thump (dum) or a dry rim slap (tek)."""
    if dum:
        n = int(0.6 * RATE)
        t = np.arange(n) / RATE
        f = 55 + 60 * np.exp(-t / 0.03)
        y = np.sin(2 * np.pi * np.cumsum(f) / RATE) * np.exp(-t / 0.22)
        y += 0.15 * rng.normal(0, 1, n) * np.exp(-t / 0.01)
    else:
        n = int(0.2 * RATE)
        t = np.arange(n) / RATE
        noise = sosfilt(butter(2, [700, 3500], "bandpass", fs=RATE, output="sos"),
                        rng.normal(0, 1, n))  # fmt: skip
        y = noise * np.exp(-t / 0.035) + 0.3 * np.sin(2 * np.pi * 330 * t) * np.exp(-t / 0.05)
    return (vel * y / (np.abs(y).max() + 1e-9)).astype(np.float32)


def room(rng: np.random.Generator, seconds=2.6, t60=2.2):
    """A stereo impulse response: decaying noise that darkens as it fades, after a pre-delay."""
    n = int(seconds * RATE)
    t = np.arange(n) / RATE
    ir = np.zeros((n, 2), dtype=np.float32)
    pre = int(0.018 * RATE)
    for ch in range(2):
        noise = rng.normal(0, 1, n)
        bright = sosfilt(butter(1, 5000, fs=RATE, output="sos"), noise)
        dark = sosfilt(butter(1, 900, fs=RATE, output="sos"), noise)
        mix = np.exp(-t / 0.5)  # high frequencies die first
        tail = (bright * mix + dark * (1 - mix)) * 10 ** (-3 * t / t60)
        ir[pre:, ch] = tail[: n - pre]
    return ir / np.sqrt((ir**2).sum(axis=0))


# --- composition -----------------------------------------------------------------------------


class Score:
    def __init__(self, duration: float, seed: int):
        self.buf = np.zeros((int(duration * RATE) + RATE, 2), dtype=np.float32)
        self.rng = np.random.default_rng(seed)

    def add(self, at: float, sig: np.ndarray, gain=1.0, pan=0.0):
        i = int(at * RATE)
        if i >= len(self.buf):
            return
        sig = sig[: len(self.buf) - i] * gain
        left, right = math.cos((pan + 1) * math.pi / 4), math.sin((pan + 1) * math.pi / 4)
        self.buf[i : i + len(sig), 0] += sig * left
        self.buf[i : i + len(sig), 1] += sig * right


def pitch(cfg: dict, degree: int) -> float:
    """Frequency of a scale degree (0 = the root, 7 = an octave up, negative = below)."""
    mode = cfg["mode"]
    octave, step = divmod(degree, len(mode))
    return cfg["root"] * 2 ** (octave + mode[step] / 12)


def energy_curve(cfg: dict, timing: dict) -> np.ndarray:
    """Per-second energy, 0–1, from the scenes' `energy` values, smoothed over a few seconds."""
    secs = int(timing["duration"]) + 2
    e = np.full(secs, cfg.get("default_energy", 0.5))
    for scene in timing["scenes"]:
        e[int(scene["start"]) : int(scene["end"]) + 1] = cfg["energy"].get(
            scene["id"], cfg.get("default_energy", 0.5)
        )
    k = np.hanning(7)
    return np.convolve(np.pad(e, 3, mode="edge"), k / k.sum(), mode="valid")


def lyre_phrases(score: Score, cfg: dict, timing: dict, energy: np.ndarray, beat: float):
    rng = score.rng
    stable = {0, 3, 4}  # root, fourth, fifth (degrees within the octave)
    lo, hi = cfg["lyre_range"]
    t = 1.5 * beat
    degree = 4
    end = timing["duration"] - 4
    while t < end:
        e = float(energy[min(int(t), len(energy) - 1)])
        notes = rng.integers(4, 8)
        for k in range(notes):
            last = k == notes - 1
            if last:  # settle on the nearest stable degree
                cands = [d for d in range(lo, hi + 1) if d % len(cfg["mode"]) in stable]
                degree = min(cands, key=lambda d: abs(d - degree))
            else:
                degree += int(rng.choice([-2, -1, -1, 1, 1, 2, 0, 3, -3],
                                         p=[.12, .22, .1, .22, .1, .1, .04, .05, .05]))  # fmt: skip
                degree = int(np.clip(degree, lo, hi + (2 if e > 0.8 else 0)))
            lengths, odds = [0.5, 1, 1, 1.5, 2], [0.25, 0.35, 0.1, 0.2, 0.1]
            beats = 2.5 if last else float(rng.choice(lengths, p=odds))
            vel = float(rng.uniform(0.45, 0.85)) * (0.75 + 0.35 * e)
            pan = float(rng.uniform(-0.35, 0.35))
            f = pitch(cfg, degree)
            if rng.random() < 0.18:  # a grace note from the step above
                g = pluck(pitch(cfg, degree + 1), 0.5, rng, vel * 0.5, t60=1.0, bright=0.5)
                score.add(t - 0.07, g, pan=pan)
            score.add(t, pluck(f, 4.0, rng, vel, t60=2.8, bright=0.45 + 0.25 * vel), pan=pan)
            if rng.random() < 0.3 * e:  # a lower octave or fifth under it
                under = degree - (len(cfg["mode"]) if rng.random() < 0.5 else 4)
                score.add(t + 0.02, pluck(pitch(cfg, under), 4.0, rng, vel * 0.6, t60=3.0,
                                          bright=0.35), pan=-pan)  # fmt: skip
            t += beats * beat
        t += beat * (1 + round(rng.uniform(2, 6) * (1.1 - e)))
        t = round(t / beat) * beat  # back on the pulse


def drone(score: Score, cfg: dict, timing: dict, energy: np.ndarray, beat: float):
    """Tanpura-like: fifth, root, root, low root, every four beats, plus a quiet sine bed."""
    rng = score.rng
    cycle = [4 - len(cfg["mode"]), 0, 0, -len(cfg["mode"])]
    t, i = 0.05, 0
    end = timing["duration"] - 1.0
    while t < end:
        e = float(energy[min(int(t), len(energy) - 1)])
        sig = pluck(pitch(cfg, cycle[i % 4]), 6.0, rng, 0.35, t60=5.0, bright=0.3)
        score.add(t, sig, gain=0.55 + 0.35 * e, pan=[-0.2, 0.1, -0.1, 0.2][i % 4])
        t += beat
        i += 1
    n = len(score.buf)
    tt = np.arange(n) / RATE
    bed = sum(
        a * np.sin(2 * np.pi * pitch(cfg, d) * tt * (1 + det))
        for d, a, det in [(-7, 0.5, 0), (-7, 0.35, 0.0015), (-3, 0.25, 0), (0, 0.12, -0.001)]
    )
    swell = 0.6 + 0.4 * np.sin(2 * np.pi * tt / 23.0)
    fade = np.clip(tt / 4, 0, 1) * np.clip((timing["duration"] - tt) / 3, 0, 1)
    score.buf += (0.05 * bed * swell * fade)[:, None].astype(np.float32)


def scene_marks(score: Score, cfg: dict, timing: dict):
    """A soft root-and-fifth dyad and a low dum where each scene begins (the first at t = 0)."""
    rng = score.rng
    for k, scene in enumerate(timing["scenes"]):
        at = 0.03 if k == 0 else scene["start"] - 0.25
        score.add(at, pluck(pitch(cfg, 0), 5.0, rng, 0.8, t60=4.0, bright=0.55), pan=-0.15)
        score.add(at + 0.03, pluck(pitch(cfg, 4), 5.0, rng, 0.6, t60=4.0, bright=0.5), pan=0.15)
        score.add(at, drum(rng, True, 0.55))


def hero(score: Score, cfg: dict, timing: dict, beat: float):
    """The tof's maqsum rhythm and a ney line over the hero scene."""
    rng = score.rng
    sc = next(s for s in timing["scenes"] if s["id"] == cfg["hero"])
    start = math.ceil(sc["start"] / beat) * beat
    end = sc["end"] + 2 * beat
    bars = int((end - start) / (4 * beat))
    pattern = [(0, True), (1, False), (3, False), (4, True), (6, False)]  # in eighths of a bar
    for b in range(bars):
        ramp = min(1.0, (b + 1) / 3, (bars - b) / 2)
        for eighth, dum in pattern:
            at = start + (b * 8 + eighth) * beat / 2
            vel = (0.75 if dum else 0.4) * ramp * float(rng.uniform(0.85, 1.0))
            score.add(at, drum(rng, dum, vel), pan=0 if dum else 0.1)
    line = [(d, b) for d, b in cfg["ney_hero"]]
    notes = [(pitch(cfg, d), b * beat) for d, b in line]
    score.add(start + 4 * beat, ney(notes, rng, 0.42), pan=0.15)


def outro(score: Score, cfg: dict, timing: dict, beat: float):
    """A ney descent onto the root and a rising arpeggio that rings into the tail."""
    rng = score.rng
    sc = timing["scenes"][-1]
    notes = [(pitch(cfg, d), b * beat) for d, b in cfg["ney_outro"]]
    score.add(sc["start"], ney(notes, rng, 0.38), pan=0.15)
    arp_at = timing["duration"] - 5.0
    for k, d in enumerate([0, 4, 7, 9, 11, 14]):
        f = pitch(cfg, d - 7)
        score.add(arp_at + k * 0.16, pluck(f, 6.0, rng, 0.7, t60=5.0, bright=0.55),
                  pan=-0.3 + 0.12 * k)  # fmt: skip
    score.add(arp_at, drum(rng, True, 0.5))


def compose(cfg: dict, timing: dict) -> np.ndarray:
    beat = 60 / cfg["tempo"]
    score = Score(timing["duration"], cfg["seed"])
    energy = energy_curve(cfg, timing)
    drone(score, cfg, timing, energy, beat)
    lyre_phrases(score, cfg, timing, energy, beat)
    scene_marks(score, cfg, timing)
    hero(score, cfg, timing, beat)
    outro(score, cfg, timing, beat)
    dry = score.buf
    ir = room(score.rng)
    wet = np.stack([oaconvolve(dry[:, ch], ir[:, ch])[: len(dry)] for ch in (0, 1)], axis=1)
    mix = (1 - cfg["reverb"]) * dry + cfg["reverb"] * wet * 3.0
    # no rumble under 35 Hz, and a softer top
    mix = sosfilt(butter(2, 35, "highpass", fs=RATE, output="sos"), mix, axis=0)
    mix = sosfilt(butter(1, 7000, fs=RATE, output="sos"), mix, axis=0).astype(np.float32)
    n = int(timing["duration"] * RATE)
    mix = mix[:n]
    fade = int(1.2 * RATE)
    mix[-fade:] *= np.linspace(1, 0, fade)[:, None] ** 2
    return mix


def from_file(path: str, duration: float) -> np.ndarray:
    raw = ffmpeg("-stream_loop", "-1", "-i", path, "-t", f"{duration}", "-f", "f32le",
                 "-ac", "2", "-ar", str(RATE), "-")  # fmt: skip
    y = np.frombuffer(raw, dtype=np.float32).reshape(-1, 2).copy()
    fi, fo = int(1.0 * RATE), int(2.5 * RATE)
    y[:fi] *= np.linspace(0, 1, fi)[:, None]
    y[-fo:] *= np.linspace(1, 0, fo)[:, None]
    return y


# --- mixing ----------------------------------------------------------------------------------


def duck_curve(timing: dict, n: int, depth_db: float) -> np.ndarray:
    """Gain over time: `depth_db` down while the narration speaks, eased in and out."""
    mask = np.zeros(n, dtype=np.float32)
    for scene in timing["scenes"]:
        for line in scene["lines"]:
            a, b = line["speech"]
            mask[max(0, int((a - 0.15) * RATE)) : int((b + 0.35) * RATE)] = 1
    k = int(0.25 * RATE)  # a moving average, by cumulative sum (a convolution this long is slow)
    c = np.concatenate([[0.0], np.cumsum(np.pad(mask, (k // 2, k - k // 2), mode="edge"))])
    mask = ((c[k:] - c[:-k]) / k)[:n]
    return (10 ** (depth_db * mask / 20)).astype(np.float32)


def rms(x: np.ndarray) -> float:
    return float(np.sqrt(np.mean(np.square(x)) + 1e-12))


def read_wav(path) -> np.ndarray:
    with wave.open(str(path)) as w:
        pcm = np.frombuffer(w.readframes(w.getnframes()), dtype="<i2")
    return pcm.astype(np.float32) / 32767


def write_wav(path, x: np.ndarray) -> None:
    pcm = (np.clip(x, -1, 1) * 32767).astype("<i2")
    with wave.open(str(path), "wb") as w:
        w.setnchannels(x.shape[1] if x.ndim == 2 else 1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(pcm.tobytes())


def loudnorm(src, dst, lufs: float, tp: float) -> dict:
    """Two-pass ffmpeg loudnorm: measure, then apply linearly."""
    spec = f"I={lufs}:TP={tp}:LRA=11"
    log = subprocess_stderr("-i", str(src), "-af", f"loudnorm={spec}:print_format=json",
                            "-f", "null", "-")  # fmt: skip
    m = json.loads(re.search(r"\{[^{}]*\}", log, re.S).group(0))
    ffmpeg("-i", str(src), "-af",
           f"loudnorm={spec}:measured_I={m['input_i']}:measured_TP={m['input_tp']}"
           f":measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}"
           f":offset={m['target_offset']}:linear=true",
           "-ar", str(RATE), "-c:a", "pcm_s16le", str(dst))  # fmt: skip
    return m


def subprocess_stderr(*args: str) -> str:
    cmd = ["ffmpeg", "-hide_banner", "-nostdin", "-y", *args]
    return subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=600).stderr


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("film", choices=["a", "b"])
    args = parser.parse_args()
    cfg = load_script(args.film)["music"]
    out = film_dir(args.film)
    timing = read_json(out / "timing.json")
    music = from_file(cfg["file"], timing["duration"]) if cfg.get("file") else compose(cfg, timing)
    music /= np.abs(music).max() + 1e-9
    write_wav(out / "music.wav", music * 0.8)

    vo = read_wav(out / "vo.wav")
    n = min(len(vo), len(music))
    vo, music = vo[:n], music[:n]
    speech = vo[np.abs(vo) > 0.01]
    # the bed sits `level_db` under the narration, and dips by `duck_db` while it speaks
    music *= rms(speech) / rms(music) * 10 ** (cfg["level_db"] / 20)
    music *= duck_curve(timing, n, cfg["duck_db"])[:, None]
    mix = music + vo[:, None]
    mix /= max(1.0, float(np.abs(mix).max()) / 0.95)
    write_wav(out / "mix.raw.wav", mix)
    m = loudnorm(out / "mix.raw.wav", out / "mix.wav", cfg["lufs"], cfg["true_peak"])
    (out / "mix.raw.wav").unlink()
    print(f"film {args.film}: music.wav, mix.wav (measured {m['input_i']} LUFS -> {cfg['lufs']})")


if __name__ == "__main__":
    main()
