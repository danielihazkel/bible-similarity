// The Hebrew half of `../reception.ts` (loaded with the Hebrew interface only).
import { countHe, numHe } from '../../fmt'
import { fp, rcEn, type Corpus } from '../reception'

export const rcHe: typeof rcEn = {
  title: 'בעיני חז״ל',
  lede: 'היכן המשנה, התוספתא ושני התלמודים מצטטים את המקרא, פסוק אחר פסוק. אילו ספרים, פרקים ופסוקים קראו חז״ל יותר מכול? כל ציטוט מקושר למקומו בספריא, בעברית; הטקסטים של חז״ל עצמם אינם מוצגים כאן.',
  source: 'הציטוטים מתוך הקישורים של ספריא',
  sourceLicence: 'CC BY 4.0',
  sourceNote: ': איזה קטע מצטט איזה פסוק.',
  notComputed: 'הציטוטים בספרות חז״ל לא חושבו בבנייה הזו (הריצו bsim reception).',
  described: (citations: number, verses: number, passages: number) =>
    `${countHe(citations, 'ציטוט אחד', 'שני ציטוטים', 'ציטוטים')} (קטע מספרות חז״ל עם פסוק) של ${countHe(verses, 'פסוק אחד', 'שני פסוקים', 'פסוקים')}, מתוך ${countHe(passages, 'קטע אחד', 'שני קטעים', 'קטעים')}.`,
  checksTitle: 'בדיקות שנקבעו מראש',
  holds: 'אושש',
  fails: 'לא אושש',
  law: {
    title: 'המשנה מצטטת את החוק שבתורה יותר מסיפוריה',
    text: (ratio: number, p: number, shifts: number, legal: number, narrative: number) =>
      `לכל פסוק, המשנה מצטטת את גושי החוק שבתורה (${countHe(legal, 'פסוק אחד', 'שני פסוקים', 'פסוקים')}: ספר הברית, ויקרא, חוקי במדבר, החוקה שבדברים) פי ${ratio.toFixed(2)} משאר ${numHe(narrative)} הפסוקים. מול אותם גושים כשהם מוזזים בתוך ספריהם ${numHe(shifts)} פעמים: p ${fp(p)}.`,
  },
  bavli: {
    title: 'הבבלי, עם האגדה שבו, נוטה אל החוק פחות',
    text: (mishnah: number, bavli: number, gap: number, p: number) =>
      `החוק מול שאר התורה, לכל פסוק: ${mishnah.toFixed(2)} במשנה, ${bavli.toFixed(2)} בבבלי. הפער של ${gap.toFixed(2)} מול ציטוטי התורה של שני הקבצים כשהם מעורבבים ביניהם: p ${fp(p)}.`,
  },
  known: {
    title: 'ציטוטים שהמסורת מכירה',
    found: 'נמצא',
    missing: 'לא נמצא',
  },
  ratiosTitle: 'החוק מול שאר התורה, לכל פסוק',
  corpora: { mishnah: 'משנה', tosefta: 'תוספתא', bavli: 'בבלי', yerushalmi: 'ירושלמי' } as Record<Corpus, string>,
  all: 'כל הארבעה',
  corpusLabel: 'מצוטט ב',
  stripTitle: 'פרק אחר פרק',
  stripHint: 'כל ריבוע פרק, כהה יותר ככל שפסוקיו מצוטטים יותר; בחרו פרק כדי לקרוא אותו עם ציטוטיו.',
  stripLabel: (book: string) => `${book}: הציטוטים לכל פסוק בכל פרק`,
  chapterTitle: (chapter: string, n: number, verses: number) => `${chapter}: ${countHe(n, 'ציטוט אחד', 'שני ציטוטים', 'ציטוטים')}, ${(n / verses).toFixed(2)} לפסוק`,
  legend: { label: 'ציטוטים לפסוק', none: 'אין', range: (lo: number, hi: number | null) => (hi === null ? `${lo.toFixed(1)}+` : `${lo.toFixed(1)}–${hi.toFixed(1)}`) },
  booksTitle: 'כל ספר',
  cols: { book: 'ספר', verses: 'פסוקים', total: 'ציטוטים', perVerse: 'לפסוק', verse: 'פסוק' },
  topTitle: 'הפסוקים המצוטטים ביותר',
  topIn: (book: string) => `הפסוקים המצוטטים ביותר ב${book}`,
  allBooks: 'כל הספרים',
  unitTitle: (label: string) => `מי מצטט את ${label}`,
  unitNone: 'אף קטע במשנה, בתוספתא או בתלמודים אינו מצטט את הפסוקים האלה בקישורים של ספריא.',
  allVerses: 'חזרה לכל הפסוקים',
  onSefaria: '(בספריא, בלשונית חדשה)',
  readWith: 'לקריאה עם הציטוטים',
  limits: (span: number, long: number) =>
    `קישור הוא של ספריא: ציטוט, רמז, או קטע שעורך קשר לפסוק. קישור ליותר מ־${numHe(span)} פסוקים (פרק, קטע; ${numHe(long)} כאלה) אינו נספר לכל פסוק. פירושים על הטקסטים האלה, מהדורות אחרות והרי״ף אינם נספרים.`,
  layerTitle: (n: number, parts: string) => `מצוטט ${countHe(n, 'פעם אחת', 'פעמיים', 'פעמים')} בספרות חז״ל: ${parts}`,
  layerKey: 'ליד כל פסוק, כמה קטעים במשנה, בתוספתא ובתלמודים מצטטים אותו; בחרו בו לרשימה.',
  layerNone: 'אף פסוק כאן אינו מצוטט.',
}
