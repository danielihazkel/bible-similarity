// The Hebrew half of `../mirrors.ts` (loaded with the Hebrew interface only).
import { countHe, numHe, pct } from '../../fmt'
import { FN_HE, fp, mirEn, range } from '../mirrors'

export const mirHe: typeof mirEn = {
  views: { units: 'קטעים שלמים', small: 'בקנה מידה קטן' },
  lede: 'הכיאזמוס (א ב … ב׳ א׳) נחשב לתבנית אהובה בסגנון המקראי, אך קטעים שלמים אינם מראים אותו מעבר למקריות. כאן מחפשים אותו במקום שבו התבנית אמורה להימצא, במבחן סדר שאינו נזקק למדד דמיון: זוג מילים חוזרות, או שתי פסוקיות עם אותם שני חלקים, או הופכים את סדרם או חוזרים עליו, וסדר אקראי נותן לשניהם אותו סיכוי.',
  noData: 'לא חושב בבנייה זו: הריצו `bsim mirrors` ואחר כך `bsim build-db`.',
  wordsTitle: 'מילים חוזרות',
  words: (c: number, p: number, share: number, interval: string, pv: string) =>
    `כשפסוק משתמש בשתי מילים פעמיים כל אחת והופעותיהן חופפות, הסדר הפוך (x y … y x) ב־${numHe(c)} פסוקים וחוזר (x y … x y) ב־${numHe(p)} (מבחן סימן p ${pv}); ${pct(share)} מהזוגות הפוכים (בדגימה חוזרת של פרקים: ${interval}). צירוף שחוזר כולו אינו נספר.`,
  wordsGenre: (poetry: number, nP: number, prose: number, nR: number) =>
    `בשירה ${pct(poetry)} הפוכים (${countHe(nP, 'פסוק אחד', 'שני פסוקים', 'פסוקים')}), בפרוזה ${pct(prose)} (${countHe(nR, 'פסוק אחד', 'שני פסוקים', 'פסוקים')}).`,
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
  lists: { clauses: 'זוגות פסוקיות', verses: 'היפוכים מלאים' },
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
  none: 'אין כאן דבר.',
  fp,
  range,
}
