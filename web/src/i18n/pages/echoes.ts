// Interface strings of the Network page's Directions view: a direction on the cross-book echoes
// (DESIGN.md §16.36). English first, Hebrew typed against it.

import type { EchoBasis } from '../../api/types'
import { countEn, countHe, numEn, numHe } from '../fmt'

const fp = (p: number) => (p < 0.001 ? '< 0.001' : p < 0.01 ? p.toFixed(3) : p.toFixed(2))
const gapEn = (g: number) => (g > 0 ? '+' : '−') + Math.abs(g).toFixed(2)

export const echoEn = {
  viewLabel: 'View',
  views: { communities: 'Communities', directions: 'Directions' },
  title: 'Who echoes whom',
  lede: 'The network links chapters that resemble each other; it does not say which drew on which. Three analyses can give a pair of chapters from two books a direction, from the strongest evidence to the weakest: a citation that names its source, a parallel passage whose borrower the language and spelling point to, and, for the rest, the Late Biblical Hebrew profile — the later-looking chapter is taken to echo the earlier-looking one. A pair takes the first of these that decides it.',
  noData: 'Not computed in this build: run `bsim echoes`, then `bsim build-db`.',
  summary: (pairs: number, directed: number) =>
    `${countEn(pairs, 'pair of chapters from two books', 'pairs of chapters from two books')}; ${numEn(directed)} given a direction.`,
  bases: {
    cited: { label: 'Cited', hint: 'a resolved citation in one chapter points to a verse of the other' },
    borrowed: { label: 'Borrowed', hint: 'a parallel passage whose language and spelling point to the borrower' },
    language: { label: 'Language', hint: 'the late-language profiles of the two chapters differ enough' },
    conflict: { label: 'Conflict', hint: 'a citation and a parallel passage point opposite ways' },
    none: { label: 'Undecided', hint: 'no layer decides: out of the profile’s domain, or too close' },
  } satisfies Record<EchoBasis, { label: string; hint: string }>,
  basisCount: (label: string, n: number) => `${label} ${numEn(n)}`,
  checksTitle: 'Checks fixed in advance',
  check: {
    cited: 'Language against the citations',
    spelling: 'Language against the spelling of the parallels',
    borrowed: 'Language against the borrowing estimates',
  },
  checkLine: (label: string, agree: number, n: number, p: number) =>
    `${label}: the same direction in ${numEn(agree)} of ${numEn(n)} (sign test p ${fp(p)}).`,
  underpowered: (label: string, n: number) => `${label}: ${countEn(n, 'case', 'cases')}, too few to judge.`,
  checkNote:
    'The borrowing estimates already use the same language features, so that agreement is expected; the spelling check is the independent one (only the full spelling דויד is on both sides). Every check leans on the canon order too: the accepted borrowings run from the earlier book to the later, and citations look only backwards.',
  backward: (n: number, of: number, gap: number) =>
    `${numEn(n)} of the ${countEn(of, 'language direction', 'language directions')} (profiles at least ${gap} apart) run against the canon order: the earlier book looks later. Leads, not findings — one feature can carry a score.`,
  cycles: (pairs: string[]) =>
    pairs.length === 0
      ? 'Citations and borrowing estimates never point both ways between two books.'
      : `Citations and borrowing estimates point both ways between ${pairs.join('; ')}.`,
  booksTitle: 'Book to book',
  booksLede: 'Directed pairs of chapters, from the book drawn on to the book echoing it.',
  bookPair: (a: string, b: string) => `${a} → ${b}`,
  sourcesTitle: 'Chapters drawn on most',
  sourcesLede: 'Cited or borrowed from first, then by any layer.',
  chapter: 'Chapter',
  lends: 'Drawn on',
  borrows: 'Echoes',
  explicit: 'Cited / borrowed',
  listTitle: 'Every pair',
  filters: { basis: 'Evidence', any: 'Any', backward: 'Against the canon order only', book: 'Book' },
  page: (total: number, page: number, pages: number) =>
    `${countEn(total, 'pair', 'pairs')} · page ${numEn(page)} of ${numEn(pages)}`,
  none: 'None here.',
  /** drawn on → echoing (reading direction) */
  arrow: '→',
  cited: (n: number) => countEn(n, 'citation', 'citations'),
  gap: (g: number) => `late-language profile ${gapEn(g)}`,
  gapTitle: 'The late-language score of the echo minus that of its source (of b minus a when undecided)',
  againstCanon: 'against the canon order',
  compare: 'Compare',
}

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
