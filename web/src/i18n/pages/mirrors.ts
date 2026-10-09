// Interface strings of Structure → Small scale: chiasm in a verse and in a clause pair
// (DESIGN.md §16.33). English first, Hebrew typed against it.

import { countEn, countHe, numEn, numHe, pct } from '../fmt'

const fp = (p: number | null | undefined) => (p == null ? '–' : p < 0.001 ? '< 0.001' : p < 0.01 ? p.toFixed(3) : p.toFixed(2))
const range = (i?: [number, number]) => (i ? `${pct(i[0])}–${pct(i[1])}` : '–')

type Fn = Record<string, string>
const FN_EN: Fn = { Pred: 'verb', Subj: 'subject', Objc: 'object', Cmpl: 'complement', Adju: 'adjunct', Loca: 'place', Time: 'time' }
const FN_HE: Fn = { Pred: 'נשוא', Subj: 'נושא', Objc: 'מושא', Cmpl: 'משלים', Adju: 'תיאור', Loca: 'מקום', Time: 'זמן' }

export const mirEn = {
  views: { units: 'Whole passages', small: 'Small scale' },
  lede: 'Chiasm (A B … B′ A′) is said to be a favourite figure of biblical style, but whole passages show none beyond chance. Here it is sought where the figure is said to live, with an order test that needs no measure of similarity: a pair of repeated words, or two clauses with the same two parts, either mirror their order or repeat it, and a random order makes both equally likely.',
  noData: 'Not computed in this build: run `bsim mirrors`, then `bsim build-db`.',
  wordsTitle: 'Repeated words',
  words: (c: number, p: number, share: number, interval: string, pv: string) =>
    `When a verse uses two words twice each and their occurrences overlap, the order is mirrored (x y … y x) in ${numEn(c)} verses and repeated (x y … x y) in ${numEn(p)} (sign test p ${pv}); ${pct(share)} of the pairs are mirrored (chapters resampled: ${interval}). A phrase repeated as a whole is left out.`,
  wordsGenre: (poetry: number, nP: number, prose: number, nR: number) =>
    `Poetry ${pct(poetry)} mirrored (${countEn(nP, 'verse', 'verses')}), prose ${pct(prose)} (${countEn(nR, 'verse', 'verses')}).`,
  wordsNote: 'Repeated words keep their order more often than they mirror it, in prose and in poetry alike: the figure exists, but it is not the habit.',
  clausesTitle: 'Clause parts',
  clauses: (poetry: number, nP: number, prose: number, nR: number, pv: string) =>
    `Two consecutive clauses of a verse with the same two parts (verb and object, verb and complement, …) reverse their order in ${pct(poetry)} of the pairs in poetry (${numEn(nP)}) and ${pct(prose)} in prose (${numEn(nR)}); with poetry and prose shuffled among chapters, p ${pv}. Poetry varies its word order; prose keeps it.`,
  cols: { pair: 'Parts', n: 'Clause pairs', poetry: 'Poetry mirrored', prose: 'Prose mirrored' },
  fn: (f: string) => FN_EN[f] ?? f,
  pairName: (pair: string) =>
    pair
      .split('-')
      .map((f) => FN_EN[f] ?? f)
      .join(' + '),
  listsTitle: 'Read them',
  lists: { clauses: 'Clause pairs', verses: 'Full mirrors' },
  fullNote: (n: number, k: number) =>
    `${countEn(n, 'verse', 'verses')} where ${numEn(k)} or more words used twice all nest (A B C … C B A). Each is set against its own words shuffled; none is beyond chance once the many verses are counted (q), so they are examples to read, not evidence.`,
  filters: { pair: 'Parts', any: 'Any', mirrored: 'Mirrored only', genre: 'Genre', poetry: 'Poetry', prose: 'Prose' },
  order: (a: string, b: string, mirrored: boolean) =>
    `${FN_EN[a] ?? a} – ${FN_EN[b] ?? b} | ${mirrored ? `${FN_EN[b] ?? b} – ${FN_EN[a] ?? a}` : `${FN_EN[a] ?? a} – ${FN_EN[b] ?? b}`}`,
  mirroredTag: 'mirrored',
  parallelTag: 'same order',
  poetryTag: 'poetry',
  nest: (pairs: number, words: number) => `${numEn(words)} words, ${numEn(pairs)} nested pairs`,
  pq: (p: number, q: number) => `p ${fp(p)} · q ${fp(q)}`,
  page: (n: number, page: number, pages: number) => `${numEn(n)} · page ${page} of ${pages}`,
  none: 'None here.',
  fp,
  range,
}

export const mirHe: typeof mirEn = {
  views: { units: 'קטעים שלמים', small: 'בקנה מידה קטן' },
  lede: 'הכיאזמוס (א ב … ב׳ א׳) נחשב לתבנית אהובה בסגנון המקראי, אך קטעים שלמים אינם מראים אותו מעבר למקריות. כאן הוא מבוקש במקום שבו התבנית אמורה לחיות, במבחן סדר שאינו צריך מדד דמיון: זוג מילים חוזרות, או שתי פסוקיות עם אותם שני חלקים, או הופכים את סדרם או חוזרים עליו, וסדר אקראי נותן לשניהם אותו סיכוי.',
  noData: 'לא חושב בבנייה זו: הריצו `bsim mirrors` ואחר כך `bsim build-db`.',
  wordsTitle: 'מילים חוזרות',
  words: (c: number, p: number, share: number, interval: string, pv: string) =>
    `כשפסוק משתמש בשתי מילים פעמיים כל אחת והופעותיהן חופפות, הסדר הפוך (x y … y x) ב־${numHe(c)} פסוקים וחוזר (x y … x y) ב־${numHe(p)} (מבחן סימן p ${pv}); ${pct(share)} מהזוגות הפוכים (בדגימה חוזרת של פרקים: ${interval}). צירוף שחוזר כולו אינו נספר.`,
  wordsGenre: (poetry: number, nP: number, prose: number, nR: number) =>
    `שירה ${pct(poetry)} הפוכים (${countHe(nP, 'פסוק אחד', 'שני פסוקים', 'פסוקים')}), פרוזה ${pct(prose)} (${countHe(nR, 'פסוק אחד', 'שני פסוקים', 'פסוקים')}).`,
  wordsNote: 'מילים חוזרות שומרות על סדרן לעתים קרובות יותר משהן הופכות אותו, בפרוזה ובשירה כאחת: התבנית קיימת, אבל אינה ההרגל.',
  clausesTitle: 'חלקי הפסוקית',
  clauses: (poetry: number, nP: number, prose: number, nR: number, pv: string) =>
    `שתי פסוקיות סמוכות בפסוק עם אותם שני חלקים (נשוא ומושא, נשוא ומשלים, …) הופכות את סדרם ב־${pct(poetry)} מהזוגות בשירה (${numHe(nP)}) וב־${pct(prose)} בפרוזה (${numHe(nR)}); כשמערבבים שירה ופרוזה בין הפרקים, p ${pv}. השירה משנה את סדר המילים; הפרוזה שומרת עליו.`,
  cols: { pair: 'חלקים', n: 'זוגות פסוקיות', poetry: 'הפוכים בשירה', prose: 'הפוכים בפרוזה' },
  fn: (f: string) => FN_HE[f] ?? f,
  pairName: (pair: string) =>
    pair
      .split('-')
      .map((f) => FN_HE[f] ?? f)
      .join(' + '),
  listsTitle: 'לקריאה',
  lists: { clauses: 'זוגות פסוקיות', verses: 'מראות שלמות' },
  fullNote: (n: number, k: number) =>
    `${countHe(n, 'פסוק אחד', 'שני פסוקים', 'פסוקים')} שבהם ${numHe(k)} מילים או יותר החוזרות פעמיים מקוננות כולן (א ב ג … ג ב א). כל אחד נבחן מול מילותיו מעורבבות; אף אחד אינו מעבר למקריות כשמביאים בחשבון את ריבוי הפסוקים (q), ולכן הם דוגמאות לקריאה ולא ראיה.`,
  filters: { pair: 'חלקים', any: 'הכול', mirrored: 'הפוכים בלבד', genre: 'סוגה', poetry: 'שירה', prose: 'פרוזה' },
  order: (a: string, b: string, mirrored: boolean) =>
    `${FN_HE[a] ?? a} – ${FN_HE[b] ?? b} | ${mirrored ? `${FN_HE[b] ?? b} – ${FN_HE[a] ?? a}` : `${FN_HE[a] ?? a} – ${FN_HE[b] ?? b}`}`,
  mirroredTag: 'הפוך',
  parallelTag: 'אותו סדר',
  poetryTag: 'שירה',
  nest: (pairs: number, words: number) => `${numHe(words)} מילים, ${numHe(pairs)} זוגות מקוננים`,
  pq: (p: number, q: number) => `p ${fp(p)} · q ${fp(q)}`,
  page: (n: number, page: number, pages: number) => `${numHe(n)} · עמוד ${page} מתוך ${pages}`,
  none: 'אין כאן.',
  fp,
  range,
}
