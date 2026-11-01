// The Hebrew half of `../forms.ts` (loaded with the Hebrew interface only).
import { countHe, numHe } from '../../fmt'
import { fmEn, fp, pct, x1, x2 } from '../forms'

export const fmHe: typeof fmEn = {
  title: 'מספרים ורשימות',
  lede: 'שתי צורות קטנות. המשל המספרי המדורג מונה מספר ואחריו את הבא: על שלשה פשעי דמשק ועל ארבעה (עמוס א ג), שש הנה שנא יהוה ושבע (משלי ו טז). רשימה חוזרת על תבנית פסוק אחת: תולדות בראשית ה, מסעי במדבר לג, המלכים שהכה יהושע.',
  noData: 'לא חושב בבנייה זו: הריצו `bsim forms` ואחריו `bsim build-db`.',
  view: 'הצגה',
  sayingsView: 'משלים מספריים',
  listsView: 'רשימות',
  verdict: { holds: 'עומדת', fails: 'אינה עומדת' },
  checksTitle: 'בדיקות שנקבעו מראש',
  summary: (numbers: number, free: number, sayings: number, pairs: number, window: number) =>
    `${numHe(numbers)} מילות מספר; ${numHe(free)} עומדות לבדן (השאר חלקים של מספרים מורכבים כגון שלשים ושנים). ${countHe(sayings, 'פסוק אחד מכיל', 'שני פסוקים מכילים', 'פסוקים מכילים')} מספר ואת הבא אחריו בתוך ${numHe(window)} מילים (${countHe(pairs, 'זוג מדורג אחד', 'שני זוגות מדורגים', 'זוגות מדורגים')}).`,
  known: (found: number, n: number) =>
    `המשלים שהמחקר מונה (Roth 1962; Haran 1972) נמצאים: ${numHe(found)} מתוך ${numHe(n)}. תשובה ידועה.`,
  chance: (obs: number, exp: number, p: number | null, shuffles: number) =>
    `זוגות מדורגים שכיחים יותר ממה שמספרי הספר עצמו, מפוזרים באקראי, נותנים: ${numHe(obs)} לעומת ${x1(exp)} (ערכי מילות המספר העומדות לבדן מעורבבים בתוך כל ספר, ${numHe(shuffles)} פעמים; p ${fp(p)}). רוב הזוגות אינם משלים: שני אדנים תחת הקרש האחד וכיוצא בו, במידות המשכן והמקדש, שכיחים כפי שהמקרה נותן ומטביעים את המשלים.`,
  without: (steps: string, obs: number, exp: number, p: number | null) =>
    `תיאור שנוסף אחרי הריצה הראשונה: בלי ${steps}, ${numHe(obs)} זוגות מדורגים לעומת ${x1(exp)} (p ${fp(p)}).`,
  parallel: (sp: number, op: number, sProb: number, oProb: number, p: number | null, sayings: number, others: number) =>
    `פסוק שיש בו זוג מדורג הוא צלע מקבילה (§16.9) יותר מפסוק שיש בו זוג מספרים אחר: ${pct(sp)} מתוך ${numHe(sayings)} לעומת ${pct(op)} מתוך ${numHe(others)} (הסתברות ממוצעת ${x2(sProb)} לעומת ${x2(oProb)}; התוויות מעורבבות, p ${fp(p)}). רות כינה את התבנית אמצעי של התקבולת.`,
  stepsTitle: 'מדרגות',
  step: (step: string, n: number) => `${step}: ${numHe(n)}`,
  knownTitle: 'משלים שנמנו מראש',
  knownCols: { name: 'משל', where: 'מקום', found: 'נמצא' },
  hits: (hits: number, n: number) => (n === 1 ? (hits ? 'נמצא' : 'לא נמצא') : `${numHe(hits)} מתוך ${numHe(n)} פסוקים`),
  sayingsTitle: 'המשלים',
  knownOnly: 'רק שנמנו מראש',
  sayingCount: (n: number) => countHe(n, 'פסוק אחד', 'שני פסוקים', 'פסוקים'),
  parallelTag: (prob: number) => `צלעות מקבילות ${x2(prob)}`,
  named: 'נמנה מראש: ',
  emptySayings: 'אין משל המתאים לסינון זה.',
  listsSummary: (observed: number, expected: number, shuffles: number, verses: number, minVerses: number) =>
    `${countHe(observed, 'רשימה אחת', 'שתי רשימות', 'רשימות')} של ${numHe(minVerses)} פסוקים לפחות, ${numHe(verses)} פסוקים בסך הכול, לעומת ${x1(expected)} כשפסוקי כל ספר מעורבבים (${numHe(shuffles)} ערבובים). פסוק דומה־רשימה כשתבניות מילותיו (הדקדוק של כל מילה, לא הערך) תואמות פסוק עד שלושה לפניו או אחריו טוב מ־99% מההתאמות בסדר מעורבב.`,
  listsCheck: (found: number, n: number, observed: number, expected: number) =>
    `הרשימות שנמנו מראש נמצאות, בין יותר רשימות ממה שהמקרה נותן: ${numHe(found)} מתוך ${numHe(n)}; ${numHe(observed)} רשימות לעומת ${x1(expected)}.`,
  knownListsTitle: 'רשימות שנמנו מראש',
  knownListsCols: { name: 'רשימה', span: 'פסוקים', covered: 'בתוך רשימה שנמצאה' },
  covered: (c: number, n: number) => `${numHe(c)} מתוך ${numHe(n)}`,
  kindsTitle: 'סוגים',
  kindsLede: 'תיאור ולא מבחן: רשימה היא יחס, מסעות, מפקד, קרבנות או מלכים כשהמילה (ילד; נסע או חנה; פקד; קרבן; מלך) מופיעה במחצית פסוקיה, ורשימת שמות כששמות הם שליש ממילותיה.',
  kind: {
    genealogy: 'יחס',
    itinerary: 'מסעות',
    census: 'מפקד',
    offering: 'קרבנות',
    kings: 'מלכים',
    names: 'שמות',
    other: 'אחר',
  },
  kindFilter: 'סוג',
  allKinds: 'כל הסוגים',
  listsTitle: 'הרשימות',
  listCount: (n: number) => countHe(n, 'רשימה אחת', 'שתי רשימות', 'רשימות'),
  span: (first: string, last: string) => `${first} – ${last}`,
  verses: (n: number, like: number) => `${countHe(n, 'פסוק אחד', 'שני פסוקים', 'פסוקים')}, ${numHe(like)} דומי־רשימה`,
  likeness: (x: number) => `דמיון ${x2(x)}`,
  more: (n: number) => `+ ${countHe(n, 'פסוק נוסף', 'שני פסוקים נוספים', 'פסוקים נוספים')}`,
  read: 'קריאת הפרק',
  emptyLists: 'אין רשימה המתאימה לסינון זה.',
}
