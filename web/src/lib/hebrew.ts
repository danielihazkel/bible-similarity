// Client-side display modes for the fully pointed MAM text (DESIGN.md §11).

export type TextMode = 'teamim' | 'niqqud' | 'consonants'

export const TEXT_MODES: { value: TextMode; label: string; title: string }[] = [
  { value: 'teamim', label: 'טְעָמִ֑ים', title: 'Vowels and cantillation marks' },
  { value: 'niqqud', label: 'נִקּוּד', title: 'Vowels only' },
  { value: 'consonants', label: 'אותיות', title: 'Consonants only' },
]

const MAQAF = '\u05BE'
// Cantillation marks U+0591–U+05AF, plus meteg U+05BD (an accent-like stress mark).
const TEAMIM = /[\u0591-\u05AF\u05BD]/g
// Vowels, dagesh/mappiq, rafe, shin/sin dots, upper/lower dots, qamats qatan.
const NIQQUD = /[\u05B0-\u05BC\u05BF\u05C1\u05C2\u05C4\u05C5\u05C7]/g
// Combining grapheme joiner: MAM uses it to order marks.
const CGJ = /\u034F/g

/** Strip marks for `mode`; maqaf, sof pasuq and paseq are kept in every mode. */
export function displayForm(token: string, mode: TextMode): string {
  if (mode === 'teamim') return token
  const s = token.replace(TEAMIM, '')
  return mode === 'niqqud' ? s : s.replace(NIQQUD, '').replace(CGJ, '')
}

/** True when `token` ends with a maqaf, i.e. binds to the next word without a space. */
export const endsWithMaqaf = (token: string) => token.endsWith(MAQAF)

/** Rebuild verse text from display tokens: a space after every token not ending in a maqaf. */
export function joinTokens(tokens: string[]): string {
  return tokens.map((t, i) => (i < tokens.length - 1 && !endsWithMaqaf(t) ? `${t} ` : t)).join('')
}

/** Hebrew letters for the on-screen keypad (finals after their base letters). */
export const KEYPAD_LETTERS = 'אבגדהוזחטיכךלמםנןסעפףצץקרשת'.split('')
