// Interface strings of the Written and read page: ketiv against qere (DESIGN.md §16.30). English
// first, Hebrew typed against it. `feature` turns an OSHB morphology difference ("number s>p")
// into words.

import type { KqClass, KqGrammar, KqParallel } from '../../api/types'
import { countEn, countHe, numEn, numHe, pct } from '../fmt'

type Codes = Record<string, Record<string, string>>

const CODES_EN: Codes = {
  number: { s: 'singular', p: 'plural', d: 'dual' },
  gender: { m: 'masculine', f: 'feminine', c: 'common', b: 'either' },
  person: { '1': 'first', '2': 'second', '3': 'third' },
  state: { a: 'absolute', c: 'construct', d: 'determined' },
  stem: { q: 'qal', N: 'niphal', p: 'piel', P: 'pual', h: 'hiphil', H: 'hophal', t: 'hithpael' },
  conj: {
    p: 'perfect',
    q: 'perfect with ו',
    i: 'imperfect',
    w: 'imperfect with ו',
    h: 'cohortative',
    j: 'jussive',
    v: 'imperative',
    r: 'participle',
    s: 'passive participle',
    a: 'infinitive absolute',
    c: 'infinitive construct',
  },
  prefix: { c: 'ו', b: 'ב', k: 'כ', l: 'ל', m: 'מ', d: 'ה (article)', i: 'ה (question)', s: 'ש' },
}
const CODES_HE: Codes = {
  number: { s: 'יחיד', p: 'רבים', d: 'זוגי' },
  gender: { m: 'זכר', f: 'נקבה', c: 'משותף', b: 'שני המינים' },
  person: { '1': 'מדבר', '2': 'נוכח', '3': 'נסתר' },
  state: { a: 'נפרד', c: 'נסמך', d: 'מיודע' },
  stem: { q: 'קל', N: 'נפעל', p: 'פיעל', P: 'פועל', h: 'הפעיל', H: 'הופעל', t: 'התפעל' },
  conj: {
    p: 'עבר',
    q: 'עבר מהופך',
    i: 'עתיד',
    w: 'עתיד מהופך',
    h: 'עתיד מוארך',
    j: 'עתיד מקוצר',
    v: 'ציווי',
    r: 'בינוני',
    s: 'בינוני פעול',
    a: 'מקור מוחלט',
    c: 'מקור נטוי',
  },
  prefix: { c: 'ו', b: 'ב', k: 'כ', l: 'ל', m: 'מ', d: 'ה הידיעה', i: 'ה השאלה', s: 'ש' },
}

/** "number s>p" -> "number: singular → plural", with the side that has none as `none` */
const feature = (names: Record<string, string>, codes: Codes, none: string) => (f: string) => {
  const [name, change] = f.split(' ')
  const [a, b] = (change ?? '').split('>')
  const v = (x: string) =>
    x === '-' ? none : name === 'prefix' ? [...x].map((c) => codes.prefix[c] ?? c).join('') : (codes[name]?.[x] ?? x)
  return `${names[name] ?? name}: ${v(a)} → ${v(b)}`
}

const fp = (p: number | null) => (p == null ? '–' : p < 0.001 ? '< 0.001' : p < 0.01 ? p.toFixed(3) : p.toFixed(2))

export const kqEn = {
  title: 'Written and read',
  lede: 'In more than a thousand places the Masoretic text is written one way (ketiv, כתיב) and read another (qere, קרי): the reading is noted in the margin and its vowels are put on the written letters. The written words are kept here beside the read ones, and every pair is described by its letters, its grammar and what a parallel passage writes in the same place.',
  noData: 'Not computed in this build: run `bsim ketiv`, then `bsim build-db`.',
  summary: (n: number) => `${countEn(n, 'place', 'places')} where the text is written one way and read another (OSHB).`,
  findings: 'What the pairs show',
  lookalike: (share: number, exp: number, p: number | null, share2: number | null, exp2: number, p2: number | null) =>
    `${pct(share)} of the one-letter differences are between letters that look alike in the square script (ו / י, ד / ר, ב / כ, ה / ח), against ${pct(exp)} expected from how often the letters occur (p ${fp(p)}). Leaving ו / י aside, ${share2 == null ? '–' : pct(share2)} against ${pct(exp2)} (p ${fp(p2)}).`,
  lateFuller: (late: number, lateN: number, other: number, otherN: number, books: number, p: number | null) =>
    `Where only a vowel letter differs, the written form is the fuller spelling in ${pct(late)} of the pairs in the Late Biblical Hebrew books (${numEn(lateN)}) and ${pct(other)} elsewhere (${numEn(otherN)}): late spelling is fuller. With the late label shuffled among the ${numEn(books)} books, p ${fp(p)}.`,
  parallel: (q: number, k: number, n: number, p: number | null) =>
    `Where a parallel passage has the same word, it writes the reading (qere) ${countEn(q, 'time', 'times')} and the written form (ketiv) ${countEn(k, 'time', 'times')}; ${numEn(n)} write neither (p ${fp(p)} against even odds). The qere is often an attested text, not only a correction.`,
  plural: (plural: number, waw: number) =>
    `${countEn(plural, 'reading makes', 'readings make')} a singular plural; ${numEn(waw)} of them are a written ־ו read as ־יו, which may be the older spelling of the same plural ("his hands").`,
  books: (p: number | null) => `They are spread unevenly over the books (χ² against the books' word counts, p ${fp(p)}).`,
  euphemisms: (n: number) => countEn(n, 'euphemism: a word read in place of one not pronounced', 'euphemisms: words read in place of ones not pronounced'),
  classesTitle: 'Kinds of difference',
  classes: {
    vowel_letter: { label: 'A vowel letter', hint: 'Only א ה ו י inserted or dropped (ידו / ידיו)' },
    swap: { label: 'One letter replaced', hint: 'הוא / היא' },
    vowel_position: { label: 'A vowel letter moved', hint: 'הלוך / הולך' },
    metathesis: { label: 'Letters in another order', hint: 'בעברות / בערבות' },
    division: { label: 'Words divided otherwise', hint: 'אשדת / אש דת' },
    qere_only: { label: 'Read, not written', hint: 'A word the reading adds' },
    ketiv_only: { label: 'Written, not read', hint: 'A word the reading skips' },
    same_letters: { label: 'The same letters', hint: 'Only the vowels differ' },
    other: { label: 'Other', hint: 'Several differences, or another word' },
  } satisfies Record<KqClass, { label: string; hint: string }>,
  grammar: {
    spelling: 'Same word and form',
    form: 'Same word, another form',
    word: 'Another word',
  } satisfies Record<KqGrammar, string>,
  booksTitle: 'By book',
  bookCols: { book: 'Book', words: 'Words', n: 'Ketiv / qere', rate: 'Per 1,000 words', fuller: 'Ketiv fuller' },
  lettersTitle: 'Letters replaced',
  lettersLede: 'One-letter differences by letter pair, against the count expected from the letters’ frequencies; ★ marks letters alike in the square script.',
  letterCols: { pair: 'Letters', n: 'Pairs', expected: 'Expected', ratio: 'Ratio', q: 'q' },
  featuresTitle: 'What changes in the grammar',
  featureCols: { feature: 'Difference', n: 'Pairs' },
  feature: feature(
    { number: 'number', gender: 'gender', person: 'person', state: 'state', stem: 'stem', conj: 'verb form', suffix: 'suffix', prefix: 'prefix', pos: 'part of speech', type: 'type' },
    CODES_EN,
    'none',
  ),
  listTitle: 'Every ketiv and qere',
  filters: { cls: 'Kind', grammar: 'Grammar', parallel: 'Parallel', book: 'Book', any: 'Any', euphemism: 'Euphemisms only' },
  parallelOpt: { qere: 'writes the qere', ketiv: 'writes the ketiv', neither: 'writes neither' } satisfies Record<KqParallel, string>,
  page: (total: number, page: number, pages: number) => `${countEn(total, 'pair', 'pairs')} · page ${numEn(page)} of ${numEn(pages)}`,
  none: 'None here.',
  written: 'written',
  read: 'read',
  nothing: '(nothing)',
  euphemismTag: 'euphemism',
  fullerTag: (side: 'ketiv' | 'qere'): string => (side === 'ketiv' ? 'written fuller' : 'read fuller'),
  partner: (label: string, form: string, side: KqParallel) =>
    `${label} writes ${form}: ${side === 'qere' ? 'the qere' : side === 'ketiv' ? 'the ketiv' : 'neither'}`,
}

export const kqHe: typeof kqEn = {
  title: 'כתיב וקרי',
  lede: 'ביותר מאלף מקומות נכתב נוסח המסורה בדרך אחת (כתיב) ונקרא בדרך אחרת (קרי): הקריאה רשומה בגיליון וניקודה מונח על אותיות הכתיב. כאן נשמרות המילים הכתובות לצד הנקראות, וכל זוג מתואר לפי אותיותיו, לפי הדקדוק שלו ולפי מה שכתוב במקום המקביל בקטע מקביל.',
  noData: 'לא חושב בבנייה זו: הריצו `bsim ketiv` ואחר כך `bsim build-db`.',
  summary: (n: number) => `${countHe(n, 'מקום אחד', 'שני מקומות', 'מקומות')} שבהם הטקסט נכתב כך ונקרא אחרת (OSHB).`,
  findings: 'מה הזוגות מראים',
  lookalike: (share: number, exp: number, p: number | null, share2: number | null, exp2: number, p2: number | null) =>
    `${pct(share)} מההבדלים באות אחת הם בין אותיות הדומות בכתב המרובע (ו / י, ד / ר, ב / כ, ה / ח), לעומת ${pct(exp)} הצפויים לפי שכיחות האותיות (p ${fp(p)}). בלי ו / י: ${share2 == null ? '–' : pct(share2)} לעומת ${pct(exp2)} (p ${fp(p2)}).`,
  lateFuller: (late: number, lateN: number, other: number, otherN: number, books: number, p: number | null) =>
    `כשההבדל הוא באם קריאה בלבד, הכתיב הוא הכתיב המלא ב־${pct(late)} מהזוגות בספרים של לשון המקרא המאוחרת (${numHe(lateN)}) וב־${pct(other)} בשאר (${numHe(otherN)}): הכתיב המאוחר מלא יותר. כשמערבבים את תווית המאוחרים בין ${numHe(books)} הספרים, p ${fp(p)}.`,
  parallel: (q: number, k: number, n: number, p: number | null) =>
    `כשבקטע המקביל יש אותה מילה, הוא כותב את הקרי ${countHe(q, 'פעם אחת', 'פעמיים', 'פעמים')} ואת הכתיב ${countHe(k, 'פעם אחת', 'פעמיים', 'פעמים')}; ${numHe(n)} כותבים צורה שלישית (p ${fp(p)} לעומת סיכוי שווה). הקרי הוא לעתים קרובות נוסח מתועד ולא רק תיקון.`,
  plural: (plural: number, waw: number) =>
    `${countHe(plural, 'קריאה אחת הופכת', 'שתי קריאות הופכות', 'קריאות הופכות')} יחיד לרבים; ${numHe(waw)} מהן הן ־ו כתובה הנקראת ־יו, שאפשר שהיא הכתיב הישן של אותו ריבוי ("ידיו").`,
  books: (p: number | null) => `הם מפוזרים בין הספרים באופן לא אחיד (χ² לעומת מספר המילים בכל ספר, p ${fp(p)}).`,
  euphemisms: (n: number) =>
    countHe(n, 'לשון נקייה אחת: מילה הנקראת במקום מילה שאינה נהגית', 'שתי לשונות נקיות: מילים הנקראות במקום מילים שאינן נהגות', 'לשונות נקיות: מילים הנקראות במקום מילים שאינן נהגות'),
  classesTitle: 'סוגי ההבדל',
  classes: {
    vowel_letter: { label: 'אם קריאה', hint: 'רק א ה ו י נוספו או נשמטו (ידו / ידיו)' },
    swap: { label: 'אות אחת הוחלפה', hint: 'הוא / היא' },
    vowel_position: { label: 'אם קריאה שזזה', hint: 'הלוך / הולך' },
    metathesis: { label: 'אותיות בסדר אחר', hint: 'בעברות / בערבות' },
    division: { label: 'חלוקת מילים אחרת', hint: 'אשדת / אש דת' },
    qere_only: { label: 'קרי ולא כתיב', hint: 'מילה שהקריאה מוסיפה' },
    ketiv_only: { label: 'כתיב ולא קרי', hint: 'מילה שהקריאה מדלגת עליה' },
    same_letters: { label: 'אותן אותיות', hint: 'רק הניקוד שונה' },
    other: { label: 'אחר', hint: 'כמה הבדלים, או מילה אחרת' },
  },
  grammar: {
    spelling: 'אותה מילה ואותה צורה',
    form: 'אותה מילה, צורה אחרת',
    word: 'מילה אחרת',
  },
  booksTitle: 'לפי ספר',
  bookCols: { book: 'ספר', words: 'מילים', n: 'כתיב וקרי', rate: 'לכל 1,000 מילים', fuller: 'כתיב מלא' },
  lettersTitle: 'אותיות שהוחלפו',
  lettersLede: 'הבדלים באות אחת לפי זוג אותיות, לעומת המספר הצפוי לפי שכיחות האותיות; ★ מסמן אותיות הדומות בכתב המרובע.',
  letterCols: { pair: 'אותיות', n: 'זוגות', expected: 'צפוי', ratio: 'יחס', q: 'q' },
  featuresTitle: 'מה משתנה בדקדוק',
  featureCols: { feature: 'הבדל', n: 'זוגות' },
  feature: feature(
    { number: 'מספר', gender: 'מין', person: 'גוף', state: 'מצב', stem: 'בניין', conj: 'צורת הפועל', suffix: 'כינוי', prefix: 'תחילית', pos: 'חלק דיבר', type: 'סוג' },
    CODES_HE,
    'אין',
  ),
  listTitle: 'כל הכתיב והקרי',
  filters: { cls: 'סוג', grammar: 'דקדוק', parallel: 'מקבילה', book: 'ספר', any: 'הכול', euphemism: 'לשון נקייה בלבד' },
  parallelOpt: { qere: 'כותבת את הקרי', ketiv: 'כותבת את הכתיב', neither: 'כותבת צורה אחרת' },
  page: (total: number, page: number, pages: number) =>
    `${countHe(total, 'זוג אחד', 'שני זוגות', 'זוגות')} · עמוד ${numHe(page)} מתוך ${numHe(pages)}`,
  none: 'אין כאן.',
  written: 'כתיב',
  read: 'קרי',
  nothing: '(אין)',
  euphemismTag: 'לשון נקייה',
  fullerTag: (side: 'ketiv' | 'qere') => (side === 'ketiv' ? 'הכתיב מלא' : 'הקרי מלא'),
  partner: (label: string, form: string, side: KqParallel) =>
    `${label} כותב ${form}: ${side === 'qere' ? 'כקרי' : side === 'ketiv' ? 'ככתיב' : 'צורה אחרת'}`,
}
