// The Hebrew half of `../etiologies.ts` (loaded with the Hebrew interface only).
import { countHe, numHe } from '../../fmt'
import { etyEn, fp, pct } from '../etiologies'

export const etyHe: typeof etyEn = {
  title: 'מדרשי שמות',
  lede: '"ותקרא שמו ראובן כי אמרה כי ראה יהוה בעניי." כשהכתוב קורא שם לאדם או למקום, הוא אומר פעמים רבות גם מדוע, במילים שנשמעות כמו השם. כאן נמצאות כל נוסחאות הקריאה בשם (ויקרא שמו, ויקרא שם המקום, קרא למקום), ובפסוק של כל אחת נחפשת המילה שמהדהדת את השם יותר מכול.',
  notComputed: 'מדרשי השמות לא חושבו בבנייה זו (הריצו bsim etiologies).',
  checksTitle: 'בדיקות שנקבעו מראש',
  holds: 'מתאשר',
  fails: 'לא מתאשר',
  echo: {
    title: 'השם מהדהד את ההסבר שלו',
    text: (own: number, chance: number, n: number, p: number) =>
      `בממוצע ${pct(own, 'he-IL')} מעיצורי השם עומדים לפי הסדר במילה אחת של הפסוק שלו, לעומת ${pct(chance, 'he-IL')} כשההסברים מעורבבים בין ${countHe(n, 'קריאת השם האחת', 'שתי קריאות השם', 'קריאות השם')} (p ${fp(p)}).`,
  },
  known: {
    title: 'המדרשים שהכול מסכימים עליהם',
    text: (found: number, echo: number, n: number, rank: number, share: number) =>
      `הנוסחה מוצאת ${numHe(found)} מתוך ${numHe(n)} שנקבעו מראש (בני יעקב, נח, שת, משה, באר שבע, בית אל); ${numHe(echo)} מהם מהדהדים את שמם טוב יותר מכל ההסברים האחרים מלבד ${pct(rank, 'he-IL')}. הבדיקה דרשה ${pct(share, 'he-IL')}.`,
    missing: (refs: string) => `לא נמצאו: ${refs}.`,
  },
  listTitle: 'קריאות השם',
  show: { label: 'הצגה', all: (n: number) => `הכול (${numHe(n)})`, leads: (n: number) => `מעבר למקרה (${numHe(n)})`, known: (n: number) => `שנקבעו מראש (${numHe(n)})` },
  order: { label: 'סדר', canon: 'סדר המקרא', strongest: 'החזקים תחילה' },
  kind: { person: 'אדם', place: 'מקום' },
  echoedBy: 'מהדהד במילה',
  noEcho: 'אין מילה בפסוק שמהדהדת אותו',
  score: (s: number) => `${pct(s, 'he-IL')} מאותיותיו`,
  chance: (c: number) => `בדרך כלל ${pct(c, 'he-IL')}`,
  pq: (p: number, q: number) => `p ${fp(p)}, q ${fp(q)}`,
  knownTag: 'נקבע מראש',
  empty: 'אין כאן קריאת שם.',
  method:
    'קריאת שם: צורה של קרא, ואחריה בתוך שלוש מילים שמו / שם + שם עצם, למקום או כינוי מושא, ואחריהם שם פרטי (לא שם של האל; לא אחרי לא). ההסבר: שאר מילות התוכן של הפסוק, בלי תחיליותיהן. ההדהוד: מרב עיצורי מילה של השם שנמצאים לפי הסדר באחת מהן. p: ההדהוד מול 9,999 פסוקים בלי קריאת שם; q: בנג׳מיני–הוכברג על פני קריאות השם.',
}
