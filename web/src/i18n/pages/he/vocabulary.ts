// The Hebrew half of `../vocabulary.ts` (loaded with the Hebrew interface only).
import { numHe } from '../../fmt'
import { fp, vcEn, x2 } from '../vocabulary'

export const vcHe: typeof vcEn = {
  title: 'אוצר המילים לאורך המקרא',
  lede: 'כשקוראים לפי סדר הספרים, כל ספר מביא מילים שלא נמצאו לפניו. בראשית מביא את רוב אוצר המילים; ספר שנקרא מאוחר יותר מביא פחות, יהיה גילו אשר יהיה. כאן המילים החדשות של כל ספר מוצבות מול מה שאורכו ומקומו צופים, ומול סדרים אקראיים של הספרים, כדי שמקומו בסדר לא יכריע.',
  notComputed: 'אוצר המילים לא חושב בבנייה הזו (הריצו bsim vocabulary).',
  checksTitle: 'בדיקות שנקבעו מראש',
  holds: 'אושש',
  fails: 'לא אושש',
  late: {
    title: 'הספרים המאוחרים מביאים יותר מילים חדשות',
    text: (late: number, early: number, p: number, splits: number) =>
      `לספרים המאוחרים (דברי הימים, עזרא, נחמיה, אסתר, דניאל) חידוש ממוצע של ${x2(late)}, לספרים המוקדמים (בראשית עד מלכים) ${x2(early)}: מול כל אחת מ־${numHe(splits)} הדרכים לחלק את הספרים האלה לשתי קבוצות כאלה, p ${fp(p)}.`,
  },
  known: {
    title: 'איוב ושיר השירים: עשירים במילים יחידאיות',
    rank: (book: string, rank: number | null, atMost: number) =>
      `${book}: ${rank === null ? '–' : `במקום ה־${numHe(rank)}`} במילים יחידאיות לכל 1,000 מילים (צפוי בין ${numHe(atMost)} הראשונים)`,
  },
  described: (words: number, lemmas: number, hapax: number, k: number, b: number) =>
    `${numHe(words)} מילים של ${numHe(lemmas)} ערכים (עברית, בלי שמות פרטיים ובלי ארמית); ${numHe(hapax)} ערכים יחידאיים. חוק היפס על פני המקרא: V = ${k.toFixed(2)} N^${b.toFixed(3)}.`,
  oneCorpus: (torah: number, prophets: number, writings: number) =>
    `ערכים שנמצאים בחלק אחד בלבד של המקרא: תורה ${numHe(torah)}, נביאים ${numHe(prophets)}, כתובים ${numHe(writings)}.`,
  chartTitle: 'חידוש, ספר אחר ספר',
  chartLede: 'בכמה יותר (ימינה) או פחות (שמאלה) מילים חדשות ספר מביא ממה שחוק היפס צופה לאורכו, בממוצע על סדרים אקראיים של הספרים (יחס לוגריתמי).',
  chartLabel: 'החידוש של כל ספר לפי סדר הספרים, הספרים המוקדמים והמאוחרים בצבע',
  legend: { early: 'ספרים מוקדמים', late: 'ספרים מאוחרים', other: 'לא בהשוואה' },
  readout: (book: string, n: number, exp: number, nov: number) =>
    `${book}: ${numHe(n)} ערכים חדשים לפי סדר הספרים, ${exp.toFixed(1)} צפויים; חידוש ${x2(nov)}`,
  tableTitle: 'כל ספר',
  cols: {
    book: 'ספר',
    words: 'מילים',
    lemmas: 'ערכים',
    new: 'חדשים',
    perK: 'חדשים ל־1,000',
    expected: 'צפויים',
    novelty: 'חידוש',
    hapax: 'יחידאיות',
    hapaxK: 'יחידאיות ל־1,000',
    one: 'בחלק אחד בלבד',
  },
  limits: 'הערך הוא של OSHB, כך שמילה שנכתבת בשתי דרכים או הומונים שחולקו אחרת נספרים כשניים; נספרות רק המילים של הספר (בלי שמותיו), ושיעורים של ספר קצר משתנים מאוד.',
  first: (ref: string) => `שימוש ראשון ב־${ref}`,
  firstSection: { Torah: 'נמצא בתורה בלבד', Prophets: 'נמצא בנביאים בלבד', Writings: 'נמצא בכתובים בלבד' } as Record<string, string>,
  hapaxNote: 'נמצא פעם אחת במקרא',
  books: (n: number) => (n === 1 ? 'בספר אחד' : `ב־${numHe(n)} ספרים`),
}
