"""Fonts and the glyph-outline library the film page uses, fetched once into video/out/assets.

Run: uv run python video/tools/assets.py
Cormorant Garamond (English titles), Frank Ruhl Libre (Hebrew) and JetBrains Mono (film B's
code) from google/fonts, all under the SIL Open Font License; opentype.js (MIT) to trace glyph
outlines with the pen.
"""

from __future__ import annotations

import urllib.request

from common import OUT

FONTS = "https://raw.githubusercontent.com/google/fonts/main/ofl"
ASSETS = {
    "CormorantGaramond.ttf": f"{FONTS}/cormorantgaramond/CormorantGaramond%5Bwght%5D.ttf",
    "FrankRuhlLibre.ttf": f"{FONTS}/frankruhllibre/FrankRuhlLibre%5Bwght%5D.ttf",
    "JetBrainsMono.ttf": f"{FONTS}/jetbrainsmono/JetBrainsMono%5Bwght%5D.ttf",
    "opentype.min.js": "https://cdn.jsdelivr.net/npm/opentype.js@1.3.4/dist/opentype.min.js",
}


def main() -> None:
    out = OUT / "assets"
    out.mkdir(parents=True, exist_ok=True)
    for name, url in ASSETS.items():
        path = out / name
        if path.exists():
            continue
        with urllib.request.urlopen(url, timeout=60) as r:
            path.write_bytes(r.read())
        print(f"{name}: {path.stat().st_size / 1024:.0f} KB")


if __name__ == "__main__":
    main()
