// Interface strings of the word-pairs page (DESIGN.md §16.72): fixed pairs of words (שמים וארץ),
// their order, their words' lengths and the late books' turns. English first, Hebrew typed
// against it. The pairs are quoted in Hebrew, isolated in the English sentences.

import { numEn, numHe } from '../fmt'

// three places below 0.1, so that a p just above 0.05 does not print as 0.05
const fp = (p: number) => (p < 0.001 ? '< 0.001' : p < 0.1 ? p.toFixed(3) : p.toFixed(2))
const pct = (x: number | null) => (x === null ? '–' : `${Math.round(x * 100)}%`)

export type BnShow = 'all' | 'both'
export type BnOrder = 'common' | 'turned'

export const bnEn = {
  title: 'Word pairs',
  lede: 'Hebrew pairs some words in a set order: ⁨שמים וארץ⁩, ⁨איש ואשה⁩, ⁨כסף וזהב⁩. Some orders are frozen, some turn round. Here are the pairs of nouns, names or adjectives joined by ⁨ו⁩ that recur, with how fixed each order is, the length of each word, and where the order turns.',
  notComputed: 'The word pairs were not computed in this build (run bsim binomials).',
  checksTitle: 'Checks fixed in advance',
  holds: 'Borne out',
  fails: 'Not borne out',
  short: {
    title: 'The shorter word comes first',
    text: (lk: number, lm: number, lp: number, sk: number, sm: number, sp: number) =>
      `Of the pairs whose words differ in length, the shorter word stands first in ${numEn(lk)} of ${numEn(lm)} counted in letters (p ${fp(lp)}) and ${numEn(sk)} of ${numEn(sm)} counted in syllables (p ${fp(sp)}). Both were to hold.`,
  },
  late: {
    title: 'The late books turn the pairs',
    text: (early: number | null, late: number | null, p: number, without: number) =>
      `A pair stands in its rarer order ${pct(early)} of the time in the early books (Genesis to Kings) and ${pct(late)} in the late (Chronicles, Ezra, Nehemiah, Esther, Daniel), with the periods shuffled within each pair (p ${fp(p)}). Without ⁨כסף וזהב⁩: p ${fp(without)}.`,
  },
  known: {
    title: 'Heaven and earth, man and woman, gold and silver',
    text: (sky: number | null, man: number | null, early: number | null, late: number | null) =>
      `⁨שמים וארץ⁩ in that order ${pct(sky)} of the time, ⁨איש ואשה⁩ ${pct(man)}; ⁨זהב וכסף⁩ rather than ⁨כסף וזהב⁩ ${pct(early)} of the time in the early books, ${pct(late)} in the late.`,
  },
  listTitle: (n: number, min: number) => `The ${numEn(n)} pairs found at least ${numEn(min)} times`,
  show: { label: 'Show', all: 'All', both: 'Found both ways' },
  order: { label: 'Order', common: 'Commonest', turned: 'Most turned' },
  kind: { noun: 'nouns', name: 'names', adjective: 'adjectives' } as Record<string, string>,
  cols: {
    pair: 'Pair, in its own order',
    kind: 'Kind',
    n: 'Found',
    fixed: 'In this order',
    letters: 'Letters',
    syll: 'Syllables',
    early: 'Turned, early books',
    late: 'Turned, late books',
  },
  of: (k: number, n: number) => (n ? `${numEn(k)} / ${numEn(n)}` : '–'),
  showPair: (pair: string) => `Where ${pair} is found`,
  pairTitle: (pair: string) => `${pair}: where it is found`,
  ownOrder: 'In its own order',
  rarerOrder: 'Turned round',
  listed: (n: number) => `(up to ${numEn(n)} of each listed)`,
  close: 'Close',
  empty: 'No pair here.',
  limits: 'A pair is two words side by side: ⁨את השמים ואת הארץ⁩, with ⁨את⁩ between, is not counted.',
}

export const bnHe: typeof bnEn = {
  title: 'צמדי מילים',
  lede: 'העברית מצמדת מילים מסוימות בסדר קבוע: שמים וארץ, איש ואשה, כסף וזהב. יש סדרים קפואים ויש שמתהפכים. כאן הצמדים של שמות עצם, שמות פרטיים או תארים שמחוברים בו׳ וחוזרים, עם מידת הקביעות של כל סדר, אורך כל מילה, והיכן הסדר מתהפך.',
  notComputed: 'צמדי המילים לא חושבו בבנייה הזו (הריצו bsim binomials).',
  checksTitle: 'בדיקות שנקבעו מראש',
  holds: 'אושש',
  fails: 'לא אושש',
  short: {
    title: 'המילה הקצרה באה ראשונה',
    text: (lk: number, lm: number, lp: number, sk: number, sm: number, sp: number) =>
      `מן הצמדים שמילותיהם שונות באורכן, הקצרה עומדת ראשונה ב־${numHe(lk)} מתוך ${numHe(lm)} כשסופרים אותיות (p ${fp(lp)}) וב־${numHe(sk)} מתוך ${numHe(sm)} כשסופרים הברות (p ${fp(sp)}). שתיהן היו צריכות להתקיים.`,
  },
  late: {
    title: 'הספרים המאוחרים הופכים את הצמדים',
    text: (early: number | null, late: number | null, p: number, without: number) =>
      `צמד עומד בסדרו הנדיר ב־${pct(early)} מהפעמים בספרים המוקדמים (בראשית עד מלכים) וב־${pct(late)} במאוחרים (דברי הימים, עזרא, נחמיה, אסתר, דניאל), מול תקופות מעורבבות בתוך כל צמד (p ${fp(p)}). בלי כסף וזהב: p ${fp(without)}.`,
  },
  known: {
    title: 'שמים וארץ, איש ואשה, זהב וכסף',
    text: (sky: number | null, man: number | null, early: number | null, late: number | null) =>
      `שמים וארץ בסדר הזה ב־${pct(sky)} מהפעמים, איש ואשה ב־${pct(man)}; זהב וכסף במקום כסף וזהב ב־${pct(early)} מהפעמים בספרים המוקדמים, ב־${pct(late)} במאוחרים.`,
  },
  listTitle: (n: number, min: number) => `${numHe(n)} הצמדים שנמצאו ${numHe(min)} פעמים לפחות`,
  show: { label: 'הצגה', all: 'הכול', both: 'בשני הסדרים' },
  order: { label: 'סדר', common: 'השכיחים', turned: 'המתהפכים' },
  kind: { noun: 'שמות עצם', name: 'שמות פרטיים', adjective: 'תארים' } as Record<string, string>,
  cols: {
    pair: 'הצמד, בסדרו',
    kind: 'סוג',
    n: 'נמצא',
    fixed: 'בסדר הזה',
    letters: 'אותיות',
    syll: 'הברות',
    early: 'הפוך, ספרים מוקדמים',
    late: 'הפוך, ספרים מאוחרים',
  },
  of: (k: number, n: number) => (n ? `${numHe(k)} / ${numHe(n)}` : '–'),
  showPair: (pair: string) => `היכן נמצא ${pair}`,
  pairTitle: (pair: string) => `${pair}: היכן הוא נמצא`,
  ownOrder: 'בסדרו',
  rarerOrder: 'הפוך',
  listed: (n: number) => `(עד ${numHe(n)} מכל סדר)`,
  close: 'סגירה',
  empty: 'אין כאן צמד.',
  limits: 'צמד הוא שתי מילים סמוכות: את השמים ואת הארץ, עם את ביניהן, אינו נספר.',
}
