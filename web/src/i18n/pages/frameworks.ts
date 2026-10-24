// Interface strings of the frameworks page (DESIGN.md §16.71): the judges' cycle and the kings'
// regnal accounts. English first, Hebrew typed against it. The formulas are quoted in Hebrew,
// isolated in the English sentences.

import { numEn, numHe } from '../fmt'

const fp = (p: number) => (p < 0.001 ? '< 0.001' : p < 0.01 ? p.toFixed(3) : p.toFixed(2))
const x2 = (x: number) => x.toFixed(2)

export const fwEn = {
  title: 'Narrative frameworks',
  lede: 'Judges tells its deliverances in one frame: Israel did evil in the eyes of the LORD, he gave them into an enemy’s hand for so many years, they cried out, he raised them a deliverer, and the land was at rest. Kings frames every reign alike: the accession, the king’s age and his mother, the verdict, the high places, the sins of Jeroboam, the burial. Here each frame is looked for, slot by slot, in the words of the text.',
  notComputed: 'The frameworks were not computed in this build (run bsim frameworks).',
  checksTitle: 'Checks fixed in advance',
  holds: 'Borne out',
  fails: 'Not borne out',
  cycle: {
    title: 'The cycle breaks down through Judges',
    text: (rho: number, n: number, p: number) =>
      `Does each judge’s share of the cycle’s slots fall through the book? Spearman’s rho with the book’s order ${x2(rho)}, against every order of the ${numEn(n)} episodes (p ${fp(p)}).`,
  },
  cycleKnown: {
    title: 'Othniel whole, Samson broken',
    text: (othniel: string, samson: string) => `Othniel’s cycle has every slot (missing: ${othniel}); Samson’s has no cry and no rest (missing: ${samson}).`,
  },
  verdicts: {
    title: 'Each kingdom’s verdicts have their own wording',
    text: (n: number, within: number, between: number, p: number) =>
      `The ${numEn(n)} verdicts with the verses that follow them, compared word by word: verdicts of one kingdom ${x2(within)} alike on average, of different kingdoms ${x2(between)}, with the kingdoms shuffled (p ${fp(p)}).`,
  },
  verdictsKnown: {
    title: 'The verdicts are read right',
    text: (found: number, n: number, list: string) => `${numEn(found)} of ${numEn(n)} verdicts named in advance read as expected: ${list}.`,
    row: (name: string, expected: string, found: string) => `${name} ${found}${found === expected ? '' : ` (not ${expected})`}`,
  },
  none: 'nothing',
  slot: {
    evil: 'Did evil',
    oppression: 'Given into a hand',
    years: 'Years of servitude',
    cry: 'Cried out',
    deliverer: 'A deliverer raised',
    rest: 'The land at rest',
    age: 'Age',
    mother: 'Mother',
    high_places: 'High places',
    jeroboam: 'Sins of Jeroboam',
    burial: 'Burial',
    verdict_vid: 'Verdict',
  } as Record<string, string>,
  formulas: 'The formulas: ⁨ויעשו בני ישראל הרע בעיני יהוה⁩ · ⁨וימכרם ביד⁩ · ⁨ויעבדו ... שנה⁩ · ⁨ויזעקו אל יהוה⁩ · ⁨ויקם יהוה מושיע⁩ · ⁨ותשקט הארץ⁩.',
  cycleTitle: 'The judges’ cycle',
  cycleLede: (open: number) => `The opening slots are looked for in an episode’s first ${numEn(open)} verses, the rest in the whole episode. A tick links to the verse.`,
  episode: 'Judge',
  share: 'Slots',
  found: (ref: string) => `found in ${ref}`,
  absent: 'absent',
  kingsTitle: 'The kings’ verdicts',
  kingsLede: 'The verdict is the first verse after a king’s regnal formula that says he did evil, or what was right, in the eyes of the LORD. Choose a king to read it.',
  wording: (judah: number | undefined, israel: number | undefined, between: number | null) =>
    `How alike the verdicts are worded: within Judah ${judah === undefined ? '–' : x2(judah)}, within Israel ${israel === undefined ? '–' : x2(israel)}, across the kingdoms ${between === null ? '–' : x2(between)}.`,
  king: 'King',
  kingdom: { judah: 'Judah', israel: 'Israel' } as Record<string, string>,
  verdict: 'Verdict',
  verdictTag: { good: 'right', bad: 'evil' } as Record<string, string>,
  noVerdict: 'none found',
  showKing: (name: string) => `The account of ${name}`,
  kingTitle: (name: string) => `${name}: the verdict`,
  close: 'Close',
  byKingdomTitle: 'What each kingdom’s accounts hold',
  byKingdomLede: 'The share of each kingdom’s kings whose account holds the slot:',
}

export const fwHe: typeof fwEn = {
  title: 'המסגרות של הסיפור',
  lede: 'ספר שופטים מספר את התשועות שלו במסגרת אחת: בני ישראל עשו הרע בעיני יהוה, הוא נתן אותם ביד אויב שנים כך וכך, הם זעקו, הוא הקים להם מושיע, והארץ שקטה. ספר מלכים ממסגר כל מלכות באותו אופן: העלייה לכס, גיל המלך ושם אמו, ההערכה, הבמות, חטאות ירבעם, הקבורה. כאן כל מסגרת נבדקת, רכיב אחר רכיב, במילות הכתוב.',
  notComputed: 'המסגרות לא חושבו בבנייה הזו (הריצו bsim frameworks).',
  checksTitle: 'בדיקות שנקבעו מראש',
  holds: 'אושש',
  fails: 'לא אושש',
  cycle: {
    title: 'המחזור מתפרק לאורך ספר שופטים',
    text: (rho: number, n: number, p: number) =>
      `האם החלק של כל שופט מרכיבי המחזור יורד לאורך הספר? מקדם ספירמן עם סדר הספר ${x2(rho)}, מול כל הסדרים של ${numHe(n)} הסיפורים (p ${fp(p)}).`,
  },
  cycleKnown: {
    title: 'עתניאל שלם, שמשון שבור',
    text: (othniel: string, samson: string) => `במחזור של עתניאל כל הרכיבים (חסרים: ${othniel}); בשל שמשון אין זעקה ואין שקט (חסרים: ${samson}).`,
  },
  verdicts: {
    title: 'להערכות של כל ממלכה ניסוח משלה',
    text: (n: number, within: number, between: number, p: number) =>
      `${numHe(n)} ההערכות, עם הפסוקים שאחריהן, מושוות מילה במילה: הערכות של אותה ממלכה דומות ${x2(within)} בממוצע, של ממלכות שונות ${x2(between)}, מול ממלכות מעורבבות (p ${fp(p)}).`,
  },
  verdictsKnown: {
    title: 'ההערכות נקראות נכון',
    text: (found: number, n: number, list: string) => `${numHe(found)} מתוך ${numHe(n)} ההערכות שנקבעו מראש נקראות כצפוי: ${list}.`,
    row: (name: string, expected: string, found: string) => `${name} ${found}${found === expected ? '' : ` (לא ${expected})`}`,
  },
  none: 'אין',
  slot: {
    evil: 'עשו הרע',
    oppression: 'נתנם ביד',
    years: 'שנות שעבוד',
    cry: 'זעקו',
    deliverer: 'הקים מושיע',
    rest: 'שקטה הארץ',
    age: 'גיל',
    mother: 'שם האם',
    high_places: 'הבמות',
    jeroboam: 'חטאות ירבעם',
    burial: 'קבורה',
    verdict_vid: 'הערכה',
  } as Record<string, string>,
  formulas: 'הנוסחאות: ויעשו בני ישראל הרע בעיני יהוה · וימכרם ביד · ויעבדו ... שנה · ויזעקו אל יהוה · ויקם יהוה מושיע · ותשקט הארץ.',
  cycleTitle: 'מחזור השופטים',
  cycleLede: (open: number) => `רכיבי הפתיחה נבדקים ב־${numHe(open)} הפסוקים הראשונים של הסיפור, והשאר בכל הסיפור. סימן מקשר לפסוק.`,
  episode: 'שופט',
  share: 'רכיבים',
  found: (ref: string) => `נמצא ב${ref}`,
  absent: 'חסר',
  kingsTitle: 'הערכות המלכים',
  kingsLede: 'ההערכה היא הפסוק הראשון אחרי נוסחת המלכות שאומר שהמלך עשה הרע, או הישר, בעיני יהוה. בחרו מלך כדי לקרוא אותה.',
  wording: (judah: number | undefined, israel: number | undefined, between: number | null) =>
    `עד כמה ניסוח ההערכות דומה: בתוך יהודה ${judah === undefined ? '–' : x2(judah)}, בתוך ישראל ${israel === undefined ? '–' : x2(israel)}, בין הממלכות ${between === null ? '–' : x2(between)}.`,
  king: 'מלך',
  kingdom: { judah: 'יהודה', israel: 'ישראל' } as Record<string, string>,
  verdict: 'הערכה',
  verdictTag: { good: 'הישר', bad: 'הרע' } as Record<string, string>,
  noVerdict: 'לא נמצאה',
  showKing: (name: string) => `הסיפור של ${name}`,
  kingTitle: (name: string) => `${name}: ההערכה`,
  close: 'סגירה',
  byKingdomTitle: 'מה יש בסיפורי כל ממלכה',
  byKingdomLede: 'החלק ממלכי כל ממלכה שבסיפורם מופיע הרכיב:',
}
