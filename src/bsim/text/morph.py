"""Decode OSHB morphology codes into Hebrew grammatical descriptions (DESIGN.md §10).

A code is a language letter (`H` Hebrew, `A` Aramaic) followed by `/`-separated morphemes, e.g.
`HC/Vqw3ms` = conjunction + verb qal wayyiqtol 3ms. Each morpheme is a part-of-speech letter plus
positional features (https://hb.openscriptures.org/parsing/HebrewMorphologyCodes.html). Unknown
letters are skipped rather than failing: the description is a reading aid, not a validator.
"""

from __future__ import annotations

POS = {
    "A": "שם תואר",
    "C": "מילת חיבור",
    "D": "תואר הפועל",
    "N": "שם עצם",
    "P": "כינוי",
    "R": "מילת יחס",
    "S": "סיומת",
    "T": "מילית",
    "V": "פועל",
}
# Second letter of A / N / P / R / S / T morphemes.
SUBTYPES = {
    "A": {"a": "", "c": "מספר יסודי", "g": "שם עם", "o": "מספר סודר"},
    "N": {"c": "", "g": "שם עם", "p": "שם פרטי", "x": ""},
    "P": {"d": "רומז", "f": "סתמי", "i": "שאלה", "p": "", "r": "זיקה"},
    "R": {"d": "עם ה הידיעה"},
    "S": {"d": "ה המגמה", "h": "ה יתרה", "n": "נון יתרה", "p": "כינוי חבור"},
    "T": {
        "a": "חיוב",
        "d": "ה הידיעה",
        "e": "זירוז",
        "i": "שאלה",
        "j": "קריאה",
        "m": "רומז",
        "n": "שלילה",
        "o": "את (מושא)",
        "r": "זיקה",
    },
}
STEMS_HE = {
    "q": "קל",
    "N": "נפעל",
    "p": "פיעל",
    "P": "פֻּעַל",
    "h": "הפעיל",
    "H": "הופעל",
    "t": "התפעל",
    "o": "פּוֹלֵל",
    "O": "פּוֹלַל",
    "r": "התפולל",
    "m": "פּוֹעֵל",
    "M": "פּוֹעַל",
    "k": "פַּלֵּל",
    "K": "פֻּלַּל",
    "Q": "קל סביל",
    "l": "פלפל",
    "L": "פָּלְפַּל",
    "f": "התפלפל",
    "D": "נתפעל",
    "j": "פעלעל",
    "i": "פִּלֵּל",
    "u": "הָתְפָּעַל",
    "c": "תפעיל",
    "v": "השתפעל",
    "w": "נתפלל",
    "y": "נתפועל",
    "z": "התפועל",
}
STEMS_AR = {
    "q": "פְּעַל",
    "Q": "פְּעִיל",
    "u": "התפעֵל",
    "p": "פַּעֵל",
    "P": "אתפַּעַל",
    "M": "התפַּעַל",
    "a": "אפעל",
    "h": "הפעל",
    "s": "ספעל",
    "e": "שפעל",
    "H": "הָפְעַל",
    "i": "אתפעֵל",
    "t": "השתפעל",
    "v": "אשתפעל",
    "w": "התאפעל",
    "o": "פולל",
    "z": "אתפועל",
    "r": "התפולל",
    "f": "התפלפל",
    "b": "הֻפְעַל",
    "c": "תפעל",
    "m": "פועל",
    "l": "פלפל",
    "L": "אתפלפל",
    "O": "אתפולל",
    "G": "אִתַּפְעַל",
}
VERB_TYPES = {
    "p": "עבר",
    "q": "עבר מהופך (וקטל)",
    "i": "עתיד",
    "w": "עתיד מהופך (ויקטל)",
    "h": "עתיד מוארך",
    "j": "עתיד מקוצר",
    "v": "ציווי",
    "r": "בינוני פועל",
    "s": "בינוני פעול",
    "a": "מקור מוחלט",
    "c": "מקור נטוי",
}
PERSON = {"1": "גוף ראשון", "2": "גוף שני", "3": "גוף שלישי"}
GENDER = {"m": "זכר", "f": "נקבה", "c": "משותף", "b": "זכר ונקבה"}
NUMBER = {"s": "יחיד", "p": "רבים", "d": "זוגי"}
STATE = {"a": "נפרד", "c": "נסמך", "d": "מיודע"}
LANGUAGES = {"H": "", "A": "ארמית"}


def _features(chars: str) -> list[str]:
    """Person, gender, number, state, each optional, in that order (`x` = not applicable)."""
    out, i = [], 0
    for slot in (PERSON, GENDER, NUMBER, STATE):
        if i < len(chars) and chars[i] == "x":
            i += 1
        elif i < len(chars) and chars[i] in slot:
            out.append(slot[chars[i]])
            i += 1
    return out


def decode_morpheme(code: str, aramaic: bool = False) -> str:
    """One morpheme, e.g. `Vqw3ms` -> `פועל · קל · עתיד מהופך (ויקטל) · גוף שלישי · זכר · יחיד`."""
    if not code or code[0] not in POS:
        return code
    pos, rest = code[0], code[1:]
    parts = [POS[pos]]
    if pos == "V":
        stems = STEMS_AR if aramaic else STEMS_HE
        if rest[:1] in stems:
            parts.append(stems[rest[0]])
        if rest[1:2] in VERB_TYPES:
            parts.append(VERB_TYPES[rest[1]])
        parts += _features(rest[2:])
    elif pos in SUBTYPES:
        sub = SUBTYPES[pos].get(rest[:1])
        if sub is not None:
            if sub:
                parts.append(sub)
            rest = rest[1:]
        parts += _features(rest)
    return " · ".join(parts)


def decode(morph: str | None) -> list[str]:
    """Hebrew description per morpheme; the first is prefixed `ארמית` for Aramaic words."""
    if not morph or morph[0] not in LANGUAGES:
        return []
    aramaic = morph[0] == "A"
    out = [decode_morpheme(m, aramaic) for m in morph[1:].split("/") if m]
    if aramaic and out:
        out[0] = f"{LANGUAGES['A']} · {out[0]}"
    return out
