// Interface strings of the Citations page: verses that say they quote or fulfil another
// (DESIGN.md §16.31). English first, Hebrew typed against it.

import type { CitationFamily } from '../../api/types'
import { countEn, countHe, numEn, numHe, pct } from '../fmt'

const fp = (p: number | null) => (p == null ? '–' : p < 0.001 ? '< 0.001' : p < 0.01 ? p.toFixed(3) : p.toFixed(2))

export const citEn = {
  title: 'Citations',
  lede: 'Some verses say that they repeat or fulfil another text: "as it is written in the book of the law of Moses", "according to the word of the LORD which he spoke by his servant", "as the LORD commanded Moses". For each one the source is sought among the texts it may point to (the Torah, or anything earlier) by its words and its meaning. A source is resolved when the two searches agree on it.',
  noData: 'Not computed in this build: run `bsim citations`, then `bsim build-db`.',
  summary: (n: number, resolved: number) =>
    `${countEn(n, 'verse with a formula of reference', 'verses with a formula of reference')}; ${numEn(resolved)} resolved to one source.`,
  families: {
    written: { label: 'As it is written', hint: 'ככתוב, ככל הכתוב, כתוב בספר: sought in the Torah' },
    word: { label: 'The word fulfilled', hint: 'דבר יהוה אשר דבר (ביד …): sought in anything earlier' },
    command: { label: 'As commanded', hint: 'כאשר צוה יהוה את משה: sought in the Torah' },
  } satisfies Record<CitationFamily, { label: string; hint: string }>,
  familyLine: (label: string, k: number, n: number, share: number, nul: number, p: number | null) =>
    `${label}: ${numEn(k)} of ${numEn(n)} resolved (${pct(share)}), against ${pct(nul)} of random verses of the same books (p ${fp(p)}).`,
  familyNote:
    'A best match alone proves little: almost any verse finds a close one among ten thousand, because the corpus repeats its formulas. So each family is measured against random verses held to the same rules. Where a family does no better than they do, its formula mostly points to a law or a promise in general, not to one verse.',
  gold: (top1: number, found: number, topK: number, k: number, right: number, resolved: number) =>
    `Check: of ${countEn(found, 'citation', 'citations')} whose source scholarship names, ${numEn(top1)} find it first and ${numEn(topK)} within the best ${numEn(k)}; ${numEn(right)} of the ${numEn(resolved)} resolved ones are right.`,
  lag: (verses: number) => `A fulfilled word comes a median ${countEn(verses, 'verse', 'verses')} after its source.`,
  booksTitle: 'Who cites whom',
  booksLede: 'Resolved citations by book: the one direction between passages the text itself states.',
  bookPair: (a: string, b: string, n: number) => `${a} → ${b}: ${numEn(n)}`,
  listTitle: 'Every citation',
  filters: { family: 'Formula', any: 'Any', resolved: 'Resolved only', book: 'Book' },
  page: (total: number, page: number, pages: number) =>
    `${countEn(total, 'citation', 'citations')} · page ${numEn(page)} of ${numEn(pages)}`,
  none: 'None here.',
  resolvedTag: 'resolved',
  unresolvedTag: 'no single source',
  namedTag: (rank: number | null) => (rank == null ? 'named source missed' : rank === 1 ? 'named source found' : `named source at ${rank}`),
  source: 'Source',
  others: 'Other candidates:',
  compare: 'Compare',
}

export const citHe: typeof citEn = {
  title: 'הפניות',
  lede: 'יש פסוקים שאומרים שהם חוזרים על טקסט אחר או מקיימים אותו: "ככתוב בספר תורת משה", "כדבר יהוה אשר דבר ביד עבדו", "כאשר צוה יהוה את משה". לכל אחד מהם המקור מבוקש בין הטקסטים שהוא יכול להפנות אליהם (התורה, או כל מה שקודם לו) לפי מילותיו ולפי משמעותו. מקור נחשב מזוהה כששני החיפושים מסכימים עליו.',
  noData: 'לא חושב בבנייה זו: הריצו `bsim citations` ואחר כך `bsim build-db`.',
  summary: (n: number, resolved: number) =>
    `${countHe(n, 'פסוק אחד עם נוסחת הפניה', 'שני פסוקים עם נוסחת הפניה', 'פסוקים עם נוסחת הפניה')}; ${numHe(resolved)} זוהו עם מקור אחד.`,
  families: {
    written: { label: 'ככתוב', hint: 'ככתוב, ככל הכתוב, כתוב בספר: המקור מבוקש בתורה' },
    word: { label: 'הדבר שהתקיים', hint: 'דבר יהוה אשר דבר (ביד …): המקור מבוקש בכל מה שקודם' },
    command: { label: 'כאשר צוה', hint: 'כאשר צוה יהוה את משה: המקור מבוקש בתורה' },
  },
  familyLine: (label: string, k: number, n: number, share: number, nul: number, p: number | null) =>
    `${label}: ${numHe(k)} מתוך ${numHe(n)} זוהו (${pct(share)}), לעומת ${pct(nul)} מפסוקים אקראיים מאותם ספרים (p ${fp(p)}).`,
  familyNote:
    'התאמה טובה ביותר לבדה מוכיחה מעט: כמעט כל פסוק מוצא פסוק קרוב מבין עשרת אלפים, כי הטקסט חוזר על נוסחאותיו. לכן כל משפחה נמדדת מול פסוקים אקראיים הכפופים לאותם כללים. משפחה שאינה עולה עליהם מפנה ברוב המקרים לחוק או להבטחה בכלל, ולא לפסוק אחד.',
  gold: (top1: number, found: number, topK: number, k: number, right: number, resolved: number) =>
    `בדיקה: מתוך ${countHe(found, 'הפניה אחת', 'שתי הפניות', 'הפניות')} שהמחקר מצביע על מקורן, ${numHe(top1)} מוצאות אותו ראשון ו־${numHe(topK)} בין ${numHe(k)} הטובים; ${numHe(right)} מתוך ${numHe(resolved)} המזוהות נכונות.`,
  lag: (verses: number) => `דבר שהתקיים בא בחציון ${countHe(verses, 'פסוק אחד', 'שני פסוקים', 'פסוקים')} אחרי מקורו.`,
  booksTitle: 'מי מפנה אל מי',
  booksLede: 'הפניות מזוהות לפי ספר: הכיוון היחיד בין קטעים שהטקסט עצמו מצהיר עליו.',
  bookPair: (a: string, b: string, n: number) => `${a} ← ${b}: ${numHe(n)}`,
  listTitle: 'כל ההפניות',
  filters: { family: 'נוסחה', any: 'הכול', resolved: 'מזוהות בלבד', book: 'ספר' },
  page: (total: number, page: number, pages: number) =>
    `${countHe(total, 'הפניה אחת', 'שתי הפניות', 'הפניות')} · עמוד ${numHe(page)} מתוך ${numHe(pages)}`,
  none: 'אין כאן.',
  resolvedTag: 'מזוהה',
  unresolvedTag: 'אין מקור יחיד',
  namedTag: (rank: number | null) => (rank == null ? 'המקור הידוע לא נמצא' : rank === 1 ? 'המקור הידוע נמצא' : `המקור הידוע במקום ${rank}`),
  source: 'מקור',
  others: 'מועמדים נוספים:',
  compare: 'השוואה',
}
