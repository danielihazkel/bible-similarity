// The Hebrew half of `../masorah.ts` (loaded with the Hebrew interface only).
import { countHe, numHe } from '../../fmt'
import { fd, msrEn, unitHe } from '../masorah'
import type { Unit } from '../masorah'

export const msrHe: typeof msrEn = {
  title: 'מניין המסורה',
  lede: 'הראשונים נקראו סופרים „שהיו סופרים כל האותיות שבתורה” (קידושין ל ע״א): וא״ו דגחון חציין של אותיות, דרש דרש חציין של תיבות. הערות המסורה מוסרות את הפסוק שבאמצע כל ספר ואת מספר פסוקיו. כאן אותם דברים נמנים בנוסח הזה, באותיות הכתיב ובאותיות הקרי: היכן נופל כל אמצע לעומת האמצע שלנו, ומדוע סכום שונה. זו בדיקה של הנוסח ושל חלוקת הפסוקים, לא מבחן מול המקרה.',
  noData: 'לא חושב בבנייה זו: יש להריץ `bsim masorah` ואחר כך `bsim build-db`.',
  summary: (verses: number, wk: number, lk: number, wq: number, lq: number) =>
    `כפי שנמנים כאן, בתורה ${numHe(verses)} פסוקים: בכתיב ${numHe(wk)} תיבות ו־${numHe(lk)} אותיות; בקרי ${numHe(wq)} תיבות ו־${numHe(lq)} אותיות.`,
  kq: (pairs: number, k: number, q: number) =>
    `שני הנוסחים נבדלים ב־${numHe(pairs)} המקומות שבהם כתב יד לנינגרד כותב דבר אחד וקורא אחר. הנוסח המוצג כאן קורא את הקרי אבל שומר על אותיות הכתיב של תיבות אחדות, ולכן ${countHe(k, 'תיבה אחת נכתבה', 'שתי תיבות נכתבו', 'תיבות נכתבו')} מחדש בנוסח הכתיב ו־${numHe(q)} בנוסח הקרי.`,
  text: 'אותיות',
  texts: { ketiv: 'כתיב', qere: 'קרי' },
  middlesTitle: 'האמצעים',
  middlesLede: (tol: number) =>
    `אמצעו של רצף של n אותיות, תיבות או פסוקים הוא במחציתו, בין שתיים מהן כש־n זוגי. אמצע שהמסורת מונה פוגע כשהוא רחוק לכל היותר ${countHe(tol, 'יחידה אחת', 'שתי יחידות', 'יחידות')} מהאמצע שלנו.`,
  torah: 'התורה',
  units: { letter: 'האות שבאמצע', word: 'התיבות שבאמצע', verse: 'הפסוק שבאמצע' },
  heading: (span: string, unit: string) => `${span}: ${unit}`,
  sources: { masorah: 'המסורה', talmud: 'קידושין ל ע״א', soferim: 'מסכת סופרים ט:ג', printed: 'המניין הנדפס בסוף ספר דברים' },
  verdict: { holds: 'פוגע', fails: 'רחוק' },
  tradLetter: (k: number, word: string) => `האות ה־${numHe(k)} של ${word}`,
  tradWords: (words: string) => {
    const w = words.split(' ')
    return w.length === 2 ? `בין ${w[0]} ל־${w[1]}` : words
  },
  says: (source: string) => `לפי ${source}:`,
  ours: 'כאן:',
  oursLetter: (k: number, word: string) => `האות ה־${numHe(k)} של ${word}`,
  position: (unit: Unit, pos: number, n: number, even: boolean) => {
    const name = { letter: 'אות', word: 'תיבה', verse: 'פסוק' }[unit]
    return even ? `בין ${name} ${numHe(pos)} ל־${numHe(pos + 1)} מתוך ${numHe(n)}` : `${name} ${numHe(pos)} מתוך ${numHe(n)}`
  },
  distance: (unit: Unit, d: number, verses: number) =>
    d === 0
      ? 'הוא האמצע שלנו בדיוק.'
      : `הוא נופל ${Number.isInteger(d) ? countHe(Math.abs(d), ...unitHe[unit]) : `${fd(d, numHe)} ${unitHe[unit][2]}`} ${d > 0 ? 'אחרי' : 'לפני'} האמצע שלנו${unit !== 'verse' && verses !== 0 ? `, ${countHe(Math.abs(verses), 'פסוק אחד', 'שני פסוקים', 'פסוקים')} ${verses > 0 ? 'הלאה' : 'אחורה'}` : ''}.`,
  tradVerse: 'מקומו לפי המסורת',
  ourVerse: 'האמצע שלנו',
  totalsTitle: 'הפסוקים בכל ספר',
  totalsLede:
    'המסורה חותמת כל ספר במספר פסוקיו; שמואל, מלכים, תרי עשר, עזרא–נחמיה ודברי הימים הם ספר אחד כל אחד. המספרים הם אלה שמוסרים רוב כתבי היד, כפי שגינצבורג מקבץ אותם; מספרים אחרים שהם מוסרים מצוינים.',
  cols: { book: 'ספר', tradition: 'המסורה', ours: 'כאן', diff: 'הפרש', why: 'מדוע', also: 'כתבי יד אחרים' },
  groups: {
    samuel: 'שמואל',
    kings: 'מלכים',
    twelve: 'תרי עשר',
    ezra: 'עזרא–נחמיה',
    chronicles: 'דברי הימים',
    torah: 'תורה',
    prophets: 'נביאים',
    writings: 'כתובים',
    bible: 'המקרא כולו',
  },
  reasons: {
    split: 'המסורה מונה את הפסוק הזה כשניים (יש בו שני טעמים):',
    decalogue: 'עשרת הדברות מחולקות אחרת: 12 פסוקים במניין המסורה, 13 כאן:',
    absent: 'מניין המסורה אינו כולל שני פסוקים שיש בנוסח הזה (כתבי יד שיש בהם אותם מוסרים אותו סכום):',
    untraced: 'מניין פרק אחר פרק נותן את המספר שבנוסח הזה; מהיכן ההפרש במסורה אינו ידוע.',
    witnesses: 'כתבי היד חלוקים, ומספר אחר שהם מוסרים הוא שבנוסח הזה.',
  },
  agree: 'שווה',
  booksAgree: (agree: number, n: number) => `ב־${numHe(agree)} מתוך ${numHe(n)} הספרים הסכום הוא של המסורה.`,
  sectionsTitle: 'החלקים והמקרא כולו',
  sectionsLede:
    'הסכומים שנמסרו לחלקי המקרא ולמקרא כולו, ולתורה גם בתיבות ובאותיות. כשהמסורה מוסרת את סכומי ספרי החלק, סכומם מוצג: סכומי החלקים לא תמיד מתקבלים מהם.',
  sectionCols: { section: 'חלק', count: 'מניין', source: 'מוסר', tradition: 'נמסר', ours: 'כאן', diff: 'הפרש', bookSum: 'ספריו יחד' },
  totalUnits: { verses: 'פסוקים', words: 'תיבות', letters: 'אותיות' },
  countOf: (unit: string, text: string | null) => (text ? `${unit} (${text})` : unit),
  booksTitle: 'מניין כל ספר',
  booksCols: { book: 'ספר', verses: 'פסוקים', wordsK: 'תיבות בכתיב', wordsQ: 'תיבות בקרי', lettersK: 'אותיות בכתיב', lettersQ: 'אותיות בקרי' },
}
