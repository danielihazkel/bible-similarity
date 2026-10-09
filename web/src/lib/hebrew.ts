// Client-side display modes for the fully pointed MAM text (DESIGN.md §11).

export type TextMode = 'teamim' | 'niqqud' | 'consonants'

// Hebrew labels in both interface languages; their titles are in the catalogs (modes.textModes).
export const TEXT_MODES: { value: TextMode; label: string }[] = [
  { value: 'teamim', label: 'טְעָמִ֑ים' },
  { value: 'niqqud', label: 'נִקּוּד' },
  { value: 'consonants', label: 'אותיות' },
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

/** True when `s` contains a Hebrew letter (the API's requirement for free-text search). */
export const hasHebrew = (s: string) => /[\u05D0-\u05EA]/.test(s)

/** Hebrew letters for the on-screen keypad (finals after their base letters). */
export const KEYPAD_LETTERS = 'אבגדהוזחטיכךלמםנןסעפףצץקרשת'.split('')

const ONES = 'אבגדהוזחט'
const TENS = 'יכלמנסעפצ'
const HUNDREDS = 'קרשת'

/** Gematria without geresh marks (15 -> טו, 16 -> טז), as `canon.hebrew_numeral` on the server. */
export function hebrewNumeral(n: number): string {
  if (!Number.isInteger(n) || n < 1 || n >= 1000) return String(n)
  let out = ''
  let h = Math.floor(n / 100)
  const rest = n % 100
  while (h > 4) {
    out += 'ת'
    h -= 4
  }
  if (h) out += HUNDREDS[h - 1]
  if (rest === 15 || rest === 16) return out + (rest === 15 ? 'טו' : 'טז')
  const t = Math.floor(rest / 10)
  const o = rest % 10
  if (t) out += TENS[t - 1]
  if (o) out += ONES[o - 1]
  return out
}

const FINALS: Record<string, string> = { כ: 'ך', מ: 'ם', נ: 'ן', פ: 'ף', צ: 'ץ' }

/** A word's last letter in its final form (forms stored with the finals folded: מלכ -> מלך). */
export function withFinals(word: string): string {
  const last = word.at(-1)
  return last && FINALS[last] ? word.slice(0, -1) + FINALS[last] : word
}
