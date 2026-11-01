// The Hebrew half of `../echoes.ts` (loaded with the Hebrew interface only).
import { countHe, numHe } from '../../fmt'
import { echoEn, fp, gapEn } from '../echoes'

export const echoHe: typeof echoEn = {
  viewLabel: 'תצוגה',
  views: { communities: 'קהילות', directions: 'כיוונים' },
  title: 'מי מהדהד את מי',
  lede: 'הרשת מקשרת פרקים הדומים זה לזה; היא אינה אומרת מי שאב ממי. שלושה ניתוחים יכולים לתת כיוון לזוג פרקים משני ספרים, מן הראיה החזקה אל החלשה: ציטוט המציין את מקורו, קטע מקביל שהלשון והכתיב מצביעים על השואל בו, ולשאר — פרופיל הלשון המאוחרת: הפרק הנראה מאוחר יותר נחשב למהדהד את הנראה מוקדם. כל זוג מקבל את הכיוון מן הראשון שמכריע בו.',
  noData: 'לא חושב בבנייה זו: יש להריץ `bsim echoes` ואחר כך `bsim build-db`.',
  summary: (pairs: number, directed: number) =>
    `${countHe(pairs, 'זוג פרקים אחד משני ספרים', 'שני זוגות פרקים משני ספרים', 'זוגות פרקים משני ספרים')}; ל־${numHe(directed)} ניתן כיוון.`,
  bases: {
    cited: { label: 'ציטוט', hint: 'ציטוט מזוהה בפרק אחד מצביע על פסוק בפרק האחר' },
    borrowed: { label: 'שאילה', hint: 'קטע מקביל שהלשון והכתיב מצביעים על השואל בו' },
    language: { label: 'לשון', hint: 'פרופילי הלשון המאוחרת של שני הפרקים שונים די הצורך' },
    conflict: { label: 'סתירה', hint: 'ציטוט וקטע מקביל מצביעים לכיוונים הפוכים' },
    none: { label: 'לא הוכרע', hint: 'אף שכבה אינה מכריעה: מחוץ לתחום הפרופיל, או קרובים מדי' },
  },
  basisCount: (label: string, n: number) => `${label} ${numHe(n)}`,
  checksTitle: 'בדיקות שנקבעו מראש',
  check: {
    cited: 'הלשון מול הציטוטים',
    spelling: 'הלשון מול הכתיב של המקבילות',
    borrowed: 'הלשון מול הערכות השאילה',
  },
  checkLine: (label: string, agree: number, n: number, p: number) =>
    `${label}: אותו כיוון ב־${numHe(agree)} מתוך ${numHe(n)} (מבחן הסימן p ${fp(p)}).`,
  underpowered: (label: string, n: number) => `${label}: ${countHe(n, 'מקרה אחד', 'שני מקרים', 'מקרים')}, מעט מדי לשיפוט.`,
  checkNote:
    'הערכות השאילה כבר משתמשות באותם מאפייני לשון, ולכן ההסכמה איתן צפויה; בדיקת הכתיב היא הבלתי תלויה (רק הכתיב המלא דויד נמצא בשני הצדדים). כל הבדיקות נשענות גם על סדר הקאנון: השאילות המקובלות הולכות מן הספר המוקדם אל המאוחר, וציטוטים מביטים רק לאחור.',
  backward: (n: number, of: number, gap: number) =>
    `${numHe(n)} מתוך ${countHe(of, 'כיוון לשוני אחד', 'שני כיוונים לשוניים', 'כיוונים לשוניים')} (פרופילים הרחוקים לפחות ${gap}) הולכים נגד סדר הקאנון: הספר המוקדם נראה מאוחר. כיווני חקירה, לא ממצאים — מאפיין אחד יכול לשאת ציון.`,
  cycles: (pairs: string[]) =>
    pairs.length === 0
      ? 'ציטוטים והערכות שאילה אינם מצביעים לשני הכיוונים בין שני ספרים.'
      : `ציטוטים והערכות שאילה מצביעים לשני הכיוונים בין ${pairs.join('; ')}.`,
  booksTitle: 'ספר אל ספר',
  booksLede: 'זוגות פרקים מכוונים, מן הספר שממנו שאבו אל הספר המהדהד אותו.',
  bookPair: (a: string, b: string) => `${a} ← ${b}`,
  sourcesTitle: 'הפרקים שממנו שאבו ביותר',
  sourcesLede: 'תחילה לפי ציטוט או שאילה, אחר כך לפי כל שכבה.',
  chapter: 'פרק',
  lends: 'שאבו ממנו',
  borrows: 'מהדהד',
  explicit: 'ציטוט / שאילה',
  listTitle: 'כל הזוגות',
  filters: { basis: 'ראיה', any: 'הכול', backward: 'רק נגד סדר הקאנון', book: 'ספר' },
  page: (total: number, page: number, pages: number) =>
    `${countHe(total, 'זוג אחד', 'שני זוגות', 'זוגות')} · עמוד ${numHe(page)} מתוך ${numHe(pages)}`,
  none: 'אין כאן.',
  arrow: '←',
  cited: (n: number) => countHe(n, 'ציטוט אחד', 'שני ציטוטים', 'ציטוטים'),
  gap: (g: number) => `פרופיל לשון מאוחרת ${gapEn(g)}`,
  gapTitle: 'ציון הלשון המאוחרת של המהדהד פחות זה של מקורו (של השני פחות הראשון כשלא הוכרע)',
  againstCanon: 'נגד סדר הקאנון',
  compare: 'השוואה',
}
