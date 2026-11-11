// The Hebrew half of `../precision.ts` (loaded with the Hebrew interface only).
import { numHe } from '../../fmt'
import type { prcEn } from '../precision'

const range = (lo: number | null, hi: number | null) => (lo === null || hi === null ? '' : ` [${lo.toFixed(2)}, ${hi.toFixed(2)}]`)

export const prcHe: typeof prcEn = {
  head: 'באיזו תדירות הוא צודק, לפי הקריאה של Claude',
  summary: (precision, lo, hi) =>
    `${Math.round(precision * 100)}% נכונים${range(lo, hi)} ממה שהעמוד הזה מציג, לפי הקריאה של Claude במדגם`,
  rows: {
    shown: (judged, population) =>
      judged === population ? `כל ${numHe(judged)} המוצגים כאן` : `${numHe(judged)} שנבחרו מתוך ${numHe(population ?? 0)} המוצגים כאן`,
    marked: (judged, population) =>
      judged === population ? `כל ${numHe(judged)} המסומנים כחזקים` : `${numHe(judged)} שנבחרו מתוך ${numHe(population ?? 0)} המסומנים כחזקים`,
    strongest: (judged, population) =>
      population === null ? `${numHe(judged)} שנבחרו מן הממצאים החזקים ביותר` : `${numHe(judged)} שנבחרו מתוך ${numHe(population)} החזקים ביותר`,
  },
  result: (right, wrong, unsure, precision, lo, hi) =>
    `נכונים ${numHe(right)}, שגויים ${numHe(wrong)}${unsure ? `, לא הוכרעו ${numHe(unsure)}` : ''}` +
    (precision === null ? '' : `: דיוק ${precision.toFixed(2)}${range(lo, hi)}`),
  ci: 'הטווח הוא רווח סמך של 95%; תשובה שלא הוכרעה אינה נספרת לשום צד.',
  run: (model, date, places, known) =>
    `${model}, ${date}. הכיול שלו: המקומות שהבעלים בדק ביד, ${places} נכונים; התשובות הידועות, ${known}.`,
  caveat: 'בדיקה של מודל אחד שהפסוקים לפניו, לא תקן זהב.',
  tableTitle: 'באיזו תדירות הניתוחים צודקים',
  tableLede:
    'לכל ניתוח שלהלן Claude שפט מדגם ממה שהעמוד שלו מציג כברירת מחדל, וממה שהעמוד מסמן כחזק: שיעור מה שנמצא נכון, עם רווח סמך של 95%. בדיקה של מודל אחד שהפסוקים לפניו, לא תקן זהב.',
  cols: { detector: 'ניתוח', listed: 'מוצגים', shown: 'נכונים ממה שמוצג', marked: 'נכונים מן המסומנים כחזקים' },
  share: (precision, lo, hi, judged) =>
    precision === null ? '–' : `${Math.round(precision * 100)}%${range(lo, hi)} (נשפטו ${numHe(judged)})`,
  detectors: {
    etiologies: 'מדרשי שמות',
    brackets: 'חזרה מקשרת',
    retold: 'דיבור שמסופר שוב',
    binomials: 'צמדי מילים',
    typescenes: 'רצפי פעולות',
    acrostics: 'אקרוסטיכונים',
    wordplay: 'משחקי לשון',
    allusions: 'מילים נדירות על פני פסוקים ספורים',
    refrains: 'פזמונים חוזרים',
    sayings: 'משלים מספריים מדורגים',
    lists: 'רשימות',
    mirrors: 'כיאזם בתוך פסוק',
    ciphers: 'אתב״ש ואלב״ם',
    seams: 'מעברי סגנון',
  },
}
