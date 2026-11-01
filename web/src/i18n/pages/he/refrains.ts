// The Hebrew half of `../refrains.ts` (loaded with the Hebrew interface only).
import { countHe, numHe } from '../../fmt'
import { fp, pct, refEn, x2 } from '../refrains'

export const refHe: typeof refEn = {
  title: 'פזמונים חוזרים',
  lede: (minTokens: number, minCount: number, maxGap: number) =>
    `פזמון חוזר הוא צירוף שקטע חוזר עליו במרווחים: ולא שבתם עדי נאם יהוה חותם כל מכה בעמוס ד, כי לעולם חסדו כל פסוק בתהלים קלו. כאן זהו צירוף של ${numHe(minTokens)} מילים או יותר (בלי אותיות השימוש) החוזר ב־${numHe(minCount)} פסוקים או יותר של ספר, כל אחד בטווח ${numHe(maxGap)} פסוקים מקודמו, בצפיפות שהשכיחות של הצירוף בספרו אינה מסבירה. רוב מה שנמצא הוא רשימות — יוחסין, המפקד, הקורבנות — שפריטיהן חוזרים על נוסחם; הפזמונים של השירה והנבואה עומדים ביניהן.`,
  noData: 'לא חושב בבנייה זו: יש להריץ `bsim refrains` ואחר כך `bsim build-db`.',
  detect: (observed: number, expected: number, shuffles: number, distinct: number) =>
    `${countHe(observed, 'פזמון חוזר אחד', 'שני פזמונים חוזרים', 'פזמונים חוזרים')}, לעומת ${expected.toFixed(0)} רצפים חזקים כמותם כשפסוקי כל ספר מעורבבים (${numHe(shuffles)} ערבובים); ${numHe(distinct)} כשנשאר רק החזק מכל קבוצה החולקת פסוק.`,
  knownTitle: 'פזמונים שנקבעו מראש',
  knownLede: (found: number, n: number) =>
    `נמצאו ${numHe(found)} מתוך ${numHe(n)}. פזמון נחשב נמצא כשצירוף אחד חוזר לפחות בשלושה מן הפסוקים שנמנו; פזמון שחזרותיו רחוקות זו מזו יותר מן המרווח המותר מוחמץ מעצם ההגדרה.`,
  knownCols: { name: 'פזמון', where: 'נמנה מ־', found: 'נמצא', k: 'פסוקים', q: 'q' },
  notFound: 'לא נמצא',
  regularTitle: 'במרווחים שווים?',
  regular: (regular: number, testable: number, share: number | null, p: number | null) =>
    `${numHe(regular)} מתוך ${numHe(testable)} פזמונים שאפשר לבחון חוזרים במרווחים שווים יותר ממספר זהה של חזרות שהונחו באקראי בטווח שלהם (${pct(share)} לעומת 5%, p ${fp(p)}). השווים הם בעיקר רשימות — היוחסין של בראשית ה ו־יא, הקורבנות של במדבר ז ו־כח–כט — ובראשית א. פזמון בן שלוש חזרות קרובות אינו ניתן לבחינה ונשאר בחוץ.`,
  turnsTitle: 'במפנים?',
  turns: (observed: number | null, expected: number | null, p: number | null, n: number) =>
    `ליד פסוק של פזמון הטקסט מתחלף בחדות רבה יותר מאשר ליד פסוקים אחרים באותו טווח: החד מבין שני המעברים שלו מקבל ${x2(observed)} לעומת ${x2(expected)} (אחוזון בתוך הספר, §16.29; p ${fp(p)} על פני ${numHe(n)} פסוקים). פזמונים עומדים היכן שקטעים מתחלפים, אם כי לא בהרבה.`,
  listTitle: 'הפזמונים',
  strongestOnly: 'החזק מכל קבוצה',
  strongestTitle: 'פזמונים החולקים פסוק הם קבוצה אחת; רק החזק בה מוצג',
  knownOnly: 'רק אלה שנקבעו מראש',
  count: (n: number) => countHe(n, 'פזמון חוזר אחד', 'שני פזמונים חוזרים', 'פזמונים חוזרים'),
  verses: (k: number) => countHe(k, 'פסוק אחד', 'שני פסוקים', 'פסוקים'),
  span: (first: string, last: string) => `${first} – ${last}`,
  even: (p: number) => `מרווחים שווים (p ${fp(p)})`,
  uneven: 'מרווחים לא שווים',
  turn: (x: number) => `מפנה ${x2(x)}`,
  turnTitle: 'ממוצע המעבר החד ליד כל אחד מפסוקיו (אחוזון בתוך הספר)',
  q: (q: number) => `q ${fp(q)}`,
  qValue: (q: number) => fp(q),
  named: 'נקבע מראש: ',
  read: 'קריאה בקטע',
  readTitle: 'הפרק בקורא השכבות, והפזמון מסומן',
  more: (n: number) => `ועוד ${countHe(n, 'פסוק אחד', 'שני פסוקים', 'פסוקים')}`,
  empty: 'אין פזמון המתאים לסינון זה.',
}
