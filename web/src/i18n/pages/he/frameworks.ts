// The Hebrew half of `../frameworks.ts` (loaded with the Hebrew interface only).
import { numHe } from '../../fmt'
import { fp, fwEn, x2 } from '../frameworks'

export const fwHe: typeof fwEn = {
  title: 'מסגרות סיפוריות',
  lede: 'ספר שופטים מספר את התשועות שלו במסגרת אחת: בני ישראל עשו הרע בעיני יהוה, הוא נתן אותם ביד אויב שנים כך וכך, הם זעקו, הוא הקים להם מושיע, והארץ שקטה. ספר מלכים ממסגר כל מלכות באותו אופן: העלייה לכס, גיל המלך ושם אמו, ההערכה, הבמות, חטאות ירבעם, הקבורה. כאן כל מסגרת נבדקת, רכיב אחר רכיב, במילות הכתוב.',
  notComputed: 'המסגרות לא חושבו בבנייה הזו (הריצו bsim frameworks).',
  checksTitle: 'בדיקות שנקבעו מראש',
  holds: 'אושש',
  fails: 'לא אושש',
  cycle: {
    title: 'המחזור מתפרק לאורך ספר שופטים',
    text: (rho: number, n: number, p: number) =>
      `האם חלקם של רכיבי המחזור אצל כל שופט יורד לאורך הספר? rho של ספירמן עם סדר הספר ${x2(rho)}, מול כל הסדרים של ${numHe(n)} הסיפורים (p ${fp(p)}).`,
  },
  cycleKnown: {
    title: 'עתניאל שלם, שמשון שבור',
    text: (othniel: string, samson: string) => `במחזור של עתניאל יש כל הרכיבים (חסרים: ${othniel}); במחזור של שמשון אין זעקה ואין שקט (חסרים: ${samson}).`,
  },
  verdicts: {
    title: 'להערכות של כל ממלכה ניסוח משלה',
    text: (n: number, within: number, between: number, p: number) =>
      `${numHe(n)} ההערכות, עם הפסוקים שאחריהן, מושוות מילה במילה: הערכות של אותה ממלכה דומות ${x2(within)} בממוצע, של ממלכות שונות ${x2(between)}, מול ממלכות מעורבבות (p ${fp(p)}).`,
  },
  verdictsKnown: {
    title: 'ההערכות נקראות נכון',
    text: (found: number, n: number, list: string) => `${numHe(found)} מתוך ${numHe(n)} ההערכות שנקבעו מראש נקראות כצפוי: ${list}.`,
    row: (name: string, expected: string, found: string) => `${name} ${found}${found === expected ? '' : ` (לא ${expected})`}`,
  },
  none: 'אין',
  slot: {
    evil: 'עשו הרע',
    oppression: 'נתנם ביד',
    years: 'שנות שעבוד',
    cry: 'זעקו',
    deliverer: 'הקים מושיע',
    rest: 'שקטה הארץ',
    age: 'גיל',
    mother: 'שם האם',
    high_places: 'הבמות',
    jeroboam: 'חטאות ירבעם',
    burial: 'קבורה',
    verdict_vid: 'הערכה',
  } as Record<string, string>,
  formulas: 'הנוסחאות: ויעשו בני ישראל הרע בעיני יהוה · וימכרם ביד · ויעבדו ... שנה · ויזעקו אל יהוה · ויקם יהוה מושיע · ותשקט הארץ.',
  cycleTitle: 'מחזור השופטים',
  cycleLede: (open: number) => `רכיבי הפתיחה נבדקים ב־${numHe(open)} הפסוקים הראשונים של הסיפור, והשאר בכל הסיפור. סימן מקשר לפסוק.`,
  episode: 'שופט',
  share: 'רכיבים',
  found: (ref: string) => `נמצא ב${ref}`,
  absent: 'חסר',
  kingsTitle: 'הערכות המלכים',
  kingsLede: 'ההערכה היא הפסוק הראשון אחרי נוסחת המלכות שאומר שהמלך עשה הרע, או הישר, בעיני יהוה. בחרו מלך כדי לקרוא אותה.',
  wording: (judah: number | undefined, israel: number | undefined, between: number | null) =>
    `עד כמה ניסוח ההערכות דומה: בתוך יהודה ${judah === undefined ? '–' : x2(judah)}, בתוך ישראל ${israel === undefined ? '–' : x2(israel)}, בין הממלכות ${between === null ? '–' : x2(between)}.`,
  king: 'מלך',
  kingdom: { judah: 'יהודה', israel: 'ישראל' } as Record<string, string>,
  verdict: 'הערכה',
  verdictTag: { good: 'הישר', bad: 'הרע' } as Record<string, string>,
  noVerdict: 'לא נמצאה',
  showKing: (name: string) => `הסיפור של ${name}`,
  kingTitle: (name: string) => `${name}: ההערכה`,
  close: 'סגירה',
  byKingdomTitle: 'מה יש בסיפורי כל ממלכה',
  byKingdomLede: 'החלק ממלכי כל ממלכה שבסיפורם מופיע הרכיב:',
}
