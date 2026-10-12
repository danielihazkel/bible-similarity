// Interface strings of Patterns → Refrains: phrases that come back inside a passage, their spacing
// and the turns they mark (DESIGN.md §16.40). English first, Hebrew typed against it.

import { countEn, countHe, numEn, numHe } from '../fmt'

const fp = (p: number | null | undefined) => (p == null ? '–' : p < 0.001 ? '< 0.001' : p < 0.01 ? p.toFixed(3) : p.toFixed(2))
const pct = (x: number | null | undefined) => (x == null ? '–' : `${Math.round(x * 100)}%`)
const x2 = (x: number | null | undefined) => (x == null ? '–' : x.toFixed(2))

export const refEn = {
  title: 'Refrains',
  lede: (minTokens: number, minCount: number, maxGap: number) =>
    `A refrain is a phrase a passage repeats at intervals: ולא שבתם עדי נאם יהוה closes each blow in Amos 4, כי לעולם חסדו every verse of Psalm 136. Here it is ${numEn(minTokens)} or more words (prefixes aside) that come back in ${numEn(minCount)} or more verses of a book, each within ${numEn(maxGap)} verses of the last, more densely than the phrase's rate in its book allows. Most of what is found is lists — genealogies, the census, offerings — whose items repeat their wording; the refrains of poems and prophecy stand among them.`,
  noData: 'Not computed in this build: run `bsim refrains`, then `bsim build-db`.',
  detect: (observed: number, expected: number, shuffles: number, distinct: number) =>
    `${countEn(observed, 'refrain', 'refrains')}, against ${expected.toFixed(0)} runs as strong with the verses of each book shuffled (${numEn(shuffles)} shuffles); ${numEn(distinct)} once only the strongest of each group sharing a verse is kept.`,
  // the tests
  knownTitle: 'Refrains named in advance',
  knownLede: (found: number, n: number) =>
    `${numEn(found)} of ${numEn(n)} found. A refrain counts as found when one phrase comes back in at least three of the verses named; one whose repeats lie farther apart than the gap allowed is missed by design.`,
  knownCols: { name: 'Refrain', where: 'Named from', found: 'Found', k: 'Verses', q: 'q' },
  notFound: 'not found',
  regularTitle: 'At even intervals?',
  regular: (regular: number, testable: number, share: number | null, p: number | null) =>
    `${numEn(regular)} of ${numEn(testable)} refrains that can be tested come back at more even intervals than the same number of repeats placed at random in their span (${pct(share)} against 5%, p ${fp(p)}). The even ones are mostly lists — the genealogies of Genesis 5 and 11, the offerings of Numbers 7 and 28–29 — and Genesis 1. A refrain with three repeats close together cannot be tested and is left out.`,
  turnsTitle: 'At the turns?',
  turns: (observed: number | null, expected: number | null, p: number | null, n: number) =>
    `Next to a refrain's verse the text turns more sharply than next to other verses of the same span: the sharper of its two gaps scores ${x2(observed)} against ${x2(expected)} (a within-book percentile, §16.29; p ${fp(p)} over ${numEn(n)} verses). Refrains stand where passages turn, though not by much.`,
  // the list
  listTitle: 'The refrains',
  strongestOnly: 'Strongest of each group',
  strongestTitle: 'Refrains sharing a verse are one group; only its strongest is listed',
  knownOnly: 'Named in advance only',
  count: (n: number) => countEn(n, 'refrain', 'refrains'),
  verses: (k: number) => countEn(k, 'verse', 'verses'),
  span: (first: string, last: string) => `${first} – ${last}`,
  even: (p: number) => `even intervals (p ${fp(p)})`,
  uneven: 'uneven intervals',
  turn: (x: number) => `turn ${x2(x)}`,
  turnTitle: "Mean of the sharper gap next to each of its verses (a within-book percentile)",
  q: (q: number) => `q ${fp(q)}`,
  qValue: (q: number) => fp(q),
  named: 'named in advance: ',
  read: 'Read in the passage',
  readTitle: 'The chapter in the layered reader, the refrain marked',
  more: (n: number) => `+ ${countEn(n, 'more verse', 'more verses')}`,
  empty: 'No refrain matches these filters.',
}

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
