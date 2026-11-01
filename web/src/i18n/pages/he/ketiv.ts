// The Hebrew half of `../ketiv.ts` (loaded with the Hebrew interface only).
import type { KqParallel } from '../../../api/types'
import { countHe, numHe, pct } from '../../fmt'
import { CODES_HE, feature, fp, kqEn } from '../ketiv'

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
