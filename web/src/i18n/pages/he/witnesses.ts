// The Hebrew half of `../witnesses.ts` (loaded with the Hebrew interface only).
import { countHe, numHe } from '../../fmt'
import { fp, wtEn, type WitnessOp } from '../witnesses'

export const wtHe: typeof wtEn = {
  title: 'עדי נוסח אחרים',
  lede: 'התורה השומרונית ומגילות מדבר יהודה מול נוסח המסורה, מילה במילה: היכן הן כותבות מילה בכתיב אחר, קוראות מילה אחרת, או מוסיפות מילים שאין בנוסח המסורה. מילה במגילה נספרת רק כשאף אחת מאותיותיה אינה השלמה של עורך.',
  sources: 'התורה השומרונית של מפעל Samaritanus בהאלה (DT-UCPH / CACCHT) והמגילות המקראיות מנתוניו של מרטין אבג (ETCBC), שניהם',
  licence: 'CC BY-NC 4.0',
  sourcesNote: ': לשימוש שאינו מסחרי.',
  notComputed: 'עדי הנוסח האחרים לא הושוו בבנייה הזו (הריצו bsim download --only witnesses ואחר כך bsim witnesses).',
  described: (spVerses: number, scrolls: number, scrollVerses: number, read: number) =>
    `התורה השומרונית ב־${countHe(spVerses, 'פסוק אחד', 'שני פסוקים', 'פסוקים')}; ${countHe(scrolls, 'מגילה אחת', 'שתי מגילות', 'מגילות')} ב־${countHe(scrollVerses, 'עותק פסוק אחד', 'שני עותקי פסוקים', 'עותקי פסוקים')}, ${countHe(read, 'מילה אחת', 'שתי מילים', 'מילים')} מהן קריאות במלואן.`,
  checksTitle: 'בדיקות שנקבעו מראש',
  holds: 'אושש',
  fails: 'לא אושש',
  parallel: {
    title: 'השומרוני מוסיף בעיקר היכן שיש לתורה מקבילה',
    text: (inPar: number, elsewhere: number, ratio: number, nullMean: number, p: number, shifts: number, n: number) =>
      `מתוך ${numHe(n)} פסוקי התורה שיש להם מקבילה במקום אחר בתורה, ב־${(inPar * 100).toFixed(1)}% יש תוספת שומרונית, מול ${(elsewhere * 100).toFixed(1)}% בשאר: פי ${ratio.toFixed(2)}, מול ${nullMean.toFixed(2)} כשהמקבילות מוזזות בתוך ספריהן ${numHe(shifts)} פעמים (p ${fp(p)}).`,
  },
  known: {
    title: 'קריאות שידוע שיש בעדים',
    found: 'נמצא',
    missing: 'לא נמצא',
    plus: (n: number) => `תוספת של ${numHe(n)} מילים לפחות`,
    reads: 'קורא',
    flood: (year: number | null, expected: number) => `המבול בשומרוני בשנת ${year === null ? '—' : numHe(year)} לבריאה (ידוע: ${numHe(expected)})`,
  },
  sp: 'השומרוני',
  scrolls: 'המגילות',
  kindLabel: 'עד',
  ops: {
    same: 'זהה',
    spelling: 'כתיב',
    form: 'צורה',
    substitution: 'מילה אחרת',
    omitted: 'חסר',
    added: 'נוסף',
    moved: 'הוזז',
  } as Record<WitnessOp, string>,
  opsHint: 'כתיב: אמות קריאה אחרות (ו, י). צורה: אות תחילית או סופית אחת יותר או פחות. מילה אחרת: מילה שונה במקומה. נוסף: מילים שיש רק בעד; חסר: מילים שיש רק בנוסח המסורה.',
  plusesTitle: 'התוספות הגדולות',
  plusesHint: 'הפסוקים שבהם לעד יש הכי הרבה מילים שאין בנוסח המסורה.',
  plusOf: (n: number) => countHe(n, 'מילה אחת', 'שתי מילים', 'מילים'),
  chronTitle: 'שתי כרונולוגיות',
  chronHint: 'השנים לבריאה, מתוך הגילים של בראשית ה ו־יא בכל נוסח. בשומרוני ירד, מתושלח ולמך מתים כולם בשנת המבול.',
  chronCols: { event: 'אירוע', verse: 'פסוק', mt: 'המסורה', sp: 'השומרוני', gap: 'הפרש' },
  booksTitle: 'ספר אחר ספר',
  cols: { book: 'ספר', verses: 'פסוקים', words: 'מילים', read: 'קריאות', variants: 'חילופים ל־100 מילים', pluses: 'תוספות', scroll: 'מגילה' },
  scrollsTitle: 'המגילות שבהן הכי הרבה טקסט',
  scrollsHint: (n: number) => `${numHe(n)} המגילות שבהן הכי הרבה מילים קריאות במלואן; חילופים ל־100 מילים כאלה, בלי הכתיב.`,
  unitTitle: (label: string) => `עדי הנוסח של ${label}`,
  unitNone: 'לאף עד אחר אין את הפסוקים האלה.',
  allVerses: 'חזרה לכל העדים',
  readWith: 'לקריאה עם העדים',
  mt: 'המסורה',
  lacks: 'חסר',
  unread: 'השלמת עורך או ספק',
  legend: 'מקרא',
  limits: (plusMin: number, maxUnc: number) =>
    `תוספת היא ${numHe(plusMin)} מילים או יותר ברצף שיש בעד ואין בנוסח המסורה. מילה במגילה קריאה כשאף אות שלה אינה השלמה ואף אחת אינה מסופקת יותר מדרגה ${numHe(maxUnc)}; מילים משלימות עוזרות ליישור אך אינן נספרות לעולם. נוסח המסורה מושווה כפי שהוא נקרא (הקרי). שני מאגרי הנתונים נותחו במכונה; מילה שחולקה או חוברה אחרת נראית כשינוי.`,
  layerTitle: (sp: number | undefined, scrolls: number | undefined, scrollVariants: number | undefined) =>
    [sp !== undefined ? `השומרוני: ${countHe(sp, 'חילוף אחד', 'שני חילופים', 'חילופים')}` : null, scrolls ? `${countHe(scrolls, 'מגילה אחת', 'שתי מגילות', 'מגילות')}: ${countHe(scrollVariants ?? 0, 'חילוף אחד', 'שני חילופים', 'חילופים')}` : null].filter(Boolean).join('; '),
  layerKey: 'ליד כל פסוק, החילופים של התורה השומרונית (ש) ושל המגילות (ק), בלי הכתיב; בחרו כדי להשוות.',
  layerNone: 'לאף עד אחר אין את הפסוקים האלה.',
  layerSp: 'ש',
  layerScroll: 'ק',
}
