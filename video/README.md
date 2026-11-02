# video — two short films about the project

Two films of about five minutes each, in English with English and Hebrew subtitles:

- **A, "Every verse, every echo"**: for general and curious viewers (`script/a-general.yaml`)
- **B, "One GPU, 23,206 verses"**: for developers and ML people (`script/b-dev.yaml`)

They are drawn in a line-art style (after mg-styles-15's "02 · Line Art", MIT): one champagne-gold line on a midnight ground, traced by a pen. Captures of the viewer appear inside frames the pen draws. Every number and every shape drawn from the data (the verse field, the parallels, the family tree, the map, the dates) is read from `artifacts/results.sqlite` or `docs/RESULTS.md` by `tools/extract.py`. Scripture appears on screen in Hebrew only. The narration and both subtitle files name verses by reference and never translate them.

## Build

Needs the pipeline's `artifacts/results.sqlite`, ffmpeg on the PATH, Node 20+, Microsoft Edge (the renderer drives the installed Edge, as `web/e2e` does) and internet access for the voice and the fonts. Run from the repo root:

```bash
uv run python video/tools/extract.py                 # data → video/out/data/*.json
uv run python video/tools/assets.py                  # fonts (OFL) and opentype.js → video/out/assets
uv run --with edge-tts python video/tools/voice.py a # narration → out/a/vo.wav, timing.json
uv run python video/tools/music.py a                 # the score, ducked under the narration → out/a/mix.wav
uv run python video/tools/subs.py a --preview        # out/a/a.en.srt, a.he.srt (+ preview.mp4: audio + subtitles)
cd video && npm ci
node tools/render.mjs a --stills                     # one still per scene → out/a/stills/
node tools/render.mjs a [--burn]                     # the film → out/a/a.mp4 (+ a.en.mp4, a.he.mp4 burned)
```

Use `b` for the second film. `voice.py samples` writes one sample per candidate voice to `out/samples/`.

## How it fits together

| file | what it does |
|---|---|
| `script/*.yaml` | the narration line by line (`en`, `he`, `say` for the voice), each scene's visual and capture, the timing gaps and the `music:` settings |
| `tools/voice.py` | Edge TTS, one cached clip per line, laid on one timeline: `timing.json` holds every line's start, end and word times |
| `tools/music.py` | an original score (Karplus–Strong lyre, drone, ney, frame drum) in the script's mode on the scene windows, ducked under speech, −14 LUFS; `music.file` uses a track of your own instead |
| `tools/subs.py` | the cues from the timing; long lines split at the same place in both languages; Hebrew rows wrapped in RLM marks |
| `film/main.js` | the page: `window.renderAt(t)` draws the frame at `t` as a pure function of time, from `timing.json` |
| `film/lib.js` | the pen (paths drawn by length, slowing at corners), glyph outlines traced from the fonts, type, numbers |
| `film/scenes-a.js`, `scenes-b.js` | one function per scene id; `s.cue(i)` is when the scene's i-th line is spoken |
| `tools/render.mjs` | serves `video/`, renders in headless Edge with several pages at once, and encodes with ffmpeg; captures of the viewer are read from `out/captures/<id>/` |

`out/` is gitignored: it holds results, Hebrew text, audio and renders.

## Credits and licences

The style and the frame-by-frame technique follow [mg-styles-15](https://github.com/Vincentwei1021/mg-styles-15) (MIT); the code here is written for this project. The fonts are Cormorant Garamond, Frank Ruhl Libre and JetBrains Mono (SIL Open Font License) and the glyph outlines come from opentype.js (MIT). The voice is Microsoft Edge's neural TTS (`edge-tts`). The data's licences are listed in the main README.
