// The Hebrew half of `../psalms.ts` (loaded with the Hebrew interface only).
import { countHe, numHe } from '../../fmt'
import { fp, per100, psaEn, x2, x3 } from '../psalms'

export const psaHe: typeof psaEn = {
  title: 'תהלים',
  lede: 'ביקורת הצורות ממיינת את המזמורים לפי צורתם: מזמור השבח קורא לקהל להלל ומדבר על האל; הקינה פונה אל האל בגוף ראשון, מתוך מצוקה, ולעתים קרובות פונה אל השבח לפני סופה — "ודאות ההיענות" (תה׳ ו 9, יג 6, כב 23). כאן הצורה נמנית ממילות כל מזמור, בלי הכותרת: גופים, ציוויים ושאלות (מן המורפולוגיה) ומילות המצוקה והשבח (מתחומי SDBH). האם הצורה הנמנית מחזירה את הסוגים שמנה גונקל, והיכן פונות הקינות?',
  noData: 'לא חושב במבנה זה: הריצו `bsim psalms` ואחר כך `bsim build-db`.',
  genres: {
    hymn: 'מזמור שבח',
    lament_individual: 'קינת יחיד',
    lament_communal: 'קינת ציבור',
    royal: 'מזמור מלכות',
    thanksgiving: 'מזמור תודה',
    trust: 'שיר ביטחון',
    wisdom: 'מזמור חכמה',
  },
  unlabelled: 'מעורב או שנוי במחלוקת',
  features: {
    first_singular: 'אני',
    first_plural: 'אנחנו',
    second: 'אתה',
    imperative: 'ציוויים',
    imperative_plural: 'ציוויים ברבים',
    question: 'שאלות',
    distress: 'מצוקה',
    praise: 'שבח',
  },
  per100: 'ל־100 מילים',
  genreTitle: 'האם הצורה מחזירה את הסוגים?',
  genreLede: (labelled: number, k: number, titleWords: number) =>
    `ל־${numHe(labelled)} מזמורים יש אחד מסוגי גונקל (המקרים המובהקים; מזמור מעורב או שנוי במחלוקת הושמט). שמונה הספירות, מתוקננות, מקבצות את כל 150 המזמורים ל־${numHe(k)} אשכולות (Ward), כמספר הסוגים, בלי לראות את הסוגים; ${numHe(titleWords)} מילות כותרת הושמטו.`,
  genreResult: (nmi: number, nul: number, p: number) =>
    `האשכולות מתאימים לסוגים במידע הדדי מנורמל ${x3(nmi)}, לעומת ${x3(nul)} כשהסוגים מעורבבים בין המזמורים (p ${fp(p)}).`,
  robustGenres: (formOnly: number, formP: number, domainsOnly: number, domainsP: number, kept: number) =>
    `הצורה לבדה (גופים, ציוויים, שאלות) נותנת ${x3(formOnly)} (p ${fp(formP)}), מילות המצוקה והשבח לבדן ${x3(domainsOnly)} (p ${fp(domainsP)}); עם הכותרות, ${x3(kept)}.`,
  crosstabTitle: 'סוגים לפי אשכול',
  cluster: (c: number) => `אשכול ${numHe(c)}`,
  clusterHead: 'אשכול',
  genreHead: 'סוג',
  profileTitle: 'מה כל אשכול מונה',
  checksTitle: 'הצורות שנקבעו מראש',
  checksLede: (held: number, n: number) =>
    `${numHe(held)} מתוך ${numHe(n)} מתקיימות: ממוצע הסוג לעומת שאר המזמורים המסווגים, כשהסוגים מעורבבים (חד־צדדי, q של בנימיני–הוכברג).`,
  checkCols: { genre: 'סוג', feature: 'ספירה', expected: 'צפוי', mean: 'ממוצע', rest: 'האחרים', q: 'q' },
  higher: 'גבוה יותר',
  lower: 'נמוך יותר',
  turnTitle: 'היכן פונה הקינה?',
  turnLede: (minSide: number) =>
    `מצב הרוח של פסוק הוא מילות השבח שבו פחות מילות המצוקה. המפנה של מזמור הוא החלוקה של פסוקיו (לפחות ${numHe(minSide)} מכל צד) שבה מצב הרוח למילה עולה הכי הרבה מלפני לאחרי; ה־p שלו מסדר פסוקים מעורבב בתוך המזמור.`,
  knownLede: (found: number, n: number, expected: number, p: number, tol: number) =>
    `מפנים שהמחקר מונה: ${numHe(found)} מתוך ${numHe(n)} נמצאו בטווח ${countHe(tol, 'פסוק אחד', 'שני פסוקים', 'פסוקים')}, לעומת ${expected.toFixed(1)} לחלוקה אקראית (p ${fp(p)}).`,
  robustTolerance: (rows: { tol: string; found: number; expected: number; p: number }[]) =>
    `בטווח ${rows.map((r) => `${r.tol}: ${numHe(r.found)} לעומת ${r.expected.toFixed(1)} (p ${fp(r.p)})`).join('; ')} פסוקים — התוצאה תלויה בטווח.`,
  knownCols: { named: 'המפנה הנקוב', found: 'המפנה שנמצא', p: 'p', chance: 'סיכוי' },
  tooShort: 'קצר מדי',
  lvh: (laments: number, nLaments: number, hymns: number, nHymns: number, p: number) =>
    `האם קינות פונות יותר ממזמורי שבח? ל־${numHe(laments)} מתוך ${numHe(nLaments)} קינות יחיד יש מפנה מעל המקרה, לעומת ${numHe(hymns)} מתוך ${numHe(nHymns)} מזמורי שבח (פישר, p ${fp(p)}). רוב המזמורים קצרים מכדי שמפנה יבלוט בכל אחד לבדו.`,
  listTitle: 'המזמורים',
  allGenres: 'כל הסוגים',
  allClusters: 'כל האשכולות',
  turnedOnly: 'רק מפנה מעל המקרה',
  sortLabel: 'סדר',
  sorts: { chapter: 'לפי הסדר', turn: 'המפנה הברור תחילה' },
  count: (n: number) => countHe(n, 'מזמור אחד', 'שני מזמורים', 'מזמורים'),
  words: (n: number) => countHe(n, 'מילה אחת', 'שתי מילים', 'מילים'),
  turnAt: (label: string, p: number, before: number, after: number) =>
    `פונה ב־${label} (p ${fp(p)}; מצב רוח ${x2(before)} ← ${x2(after)} למילה)`,
  noTurn: 'קצר מכדי לפנות',
  read: 'קריאה עם מצב הרוח',
  readTitle: 'המזמור בקורא השכבות, מילות המצוקה והשבח מסומנות',
  moodLabel: (label: string) => `מצב הרוח של ${label}, פסוק אחר פסוק`,
  moodTitle: (verse: number, praise: number, distress: number) => `פסוק ${numHe(verse)}: ${numHe(praise)} שבח, ${numHe(distress)} מצוקה`,
  empty: 'אין מזמור שמתאים לסינון.',
  per100Value: per100,
}
