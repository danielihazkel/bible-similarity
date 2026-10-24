// Interface strings of the haftarot page (DESIGN.md §16.69): each parasha's reading from the
// Prophets and where the systems rank it among all the chapters of the Prophets. English first,
// Hebrew typed against it.

import { countEn, numEn, numHe } from '../fmt'

const fp = (p: number) => (p < 0.001 ? '< 0.001' : p < 0.01 ? p.toFixed(3) : p.toFixed(2))
const pct = (x: number) => `${Math.round(x * 100)}%`

export const hfEn = {
  title: 'Haftarot',
  lede: 'Each Sabbath the Torah reading is followed by a reading from the Prophets chosen to match it: Noach is read with Isaiah 54, where God swears by the waters of Noah; Vayera with II Kings 4, a son promised to a woman who had none. The sages’ pairing is an independent judgement of which passages belong together. Here every parasha is set against all 380 chapters of the Prophets, as the site’s own systems rank them, and its haftarah is looked for in the list.',
  notComputed: 'The haftarot were not computed in this build (run bsim haftarot).',
  checksTitle: 'Checks fixed in advance',
  holds: 'Borne out',
  fails: 'Not borne out',
  claim: {
    title: 'The haftarah ranks high among the Prophets',
    text: (n: number, own: number, shuffled: number, p: number) =>
      `The ${numEn(n)} haftarot chosen for their parasha stand at percentile ${pct(own)} of the 380 chapters on average (0: the first), against ${pct(shuffled)} with the haftarot shuffled among those parashot (p ${fp(p)}).`,
  },
  calendar: {
    title: 'The calendar’s haftarot rank lower',
    text: (cal: number, own: number, p: number) =>
      `The ten fixed by the calendar, three of rebuke before the Ninth of Av and seven of consolation after, stand at percentile ${pct(cal)}, against ${pct(own)} for the rest (p ${fp(p)}).`,
  },
  known: {
    title: 'Noah’s waters and the Shunammite’s son',
    text: (k: number, ranks: string) => `Both within the first ${numEn(k)} chapters for their parasha? Ranked ${ranks}.`,
    rank: (name: string, r: number) => `${name} ${numEn(r)}`,
  },
  modesTitle: 'How each system finds the haftarah',
  modesLede: (n: number) => `Each list of the ${countEn(n, 'parasha', 'parashot')} whose haftarah follows it, scored with the haftarah as the right answer: the first gold the parashot have had.`,
  modes: { lexical: 'Words (TF-IDF)', semantic: 'Meaning (BEREL)', fused: 'Both (fused)' } as Record<string, string>,
  cols: {
    system: 'System',
    mrr: 'MRR',
    hits: (k: number) => `In the first ${numEn(k)}`,
    median: 'Median rank',
    pct: 'Mean percentile',
    num: '#',
    parasha: 'Parasha',
    haftarah: 'Haftarah',
    rank: 'Rank (words · meaning)',
  },
  calendarTag: { admonition: 'rebuke', consolation: 'consolation' } as Record<string, string>,
  calendarHint: 'Fixed by the calendar, not chosen for the parasha',
  sephardi: (refs: string) => `Sephardi: ${refs}`,
  of: (r: number, lex: number, sem: number) => `${numEn(r)} (${numEn(lex)} · ${numEn(sem)})`,
  showList: (name: string) => `The chapters of the Prophets for ${name}`,
  listTitle: (name: string) => `${name}: the first chapters of the Prophets`,
  listLede: (haft: string) => `The haftarah: ${haft}. Ranked by both systems together; the chapters holding the haftarah are marked.`,
  inHaftarah: 'the haftarah',
  compare: 'compare',
  close: 'Close',
  credit: 'The pairings: Hebcal leyning, Copyright (c) 2020, hebcal (BSD 2-Clause License), the Ashkenazi haftarot.',
}

export const hfHe: typeof hfEn = {
  title: 'הפטרות',
  lede: 'בכל שבת קוראים אחרי התורה קטע מן הנביאים שנבחר להתאים לה: את נח קוראים עם ישעיה נד, שבו האל נשבע במי נח; את וירא עם מלכים ב ד, בן שהובטח לאשה שלא היה לה. הזיווג של חז״ל הוא שיפוט עצמאי של אילו קטעים שייכים זה לזה. כאן כל פרשה מוצבת מול כל 380 פרקי הנביאים, כפי שהמערכות של האתר מדרגות אותם, וההפטרה שלה מחופשת ברשימה.',
  notComputed: 'ההפטרות לא חושבו בבנייה זו (הריצו bsim haftarot).',
  checksTitle: 'בדיקות שנקבעו מראש',
  holds: 'מתאשר',
  fails: 'לא מתאשר',
  claim: {
    title: 'ההפטרה מדורגת גבוה בין הנביאים',
    text: (n: number, own: number, shuffled: number, p: number) =>
      `${numHe(n)} ההפטרות שנבחרו בגלל הפרשה עומדות בממוצע באחוזון ${pct(own)} מתוך 380 הפרקים (0: הראשון), לעומת ${pct(shuffled)} כשההפטרות מעורבבות בין אותן פרשות (p ${fp(p)}).`,
  },
  calendar: {
    title: 'הפטרות לוח השנה מדורגות נמוך יותר',
    text: (cal: number, own: number, p: number) =>
      `עשר ההפטרות שלוח השנה קובע, שלוש דפורענותא לפני תשעה באב ושבע דנחמתא אחריו, עומדות באחוזון ${pct(cal)}, לעומת ${pct(own)} לשאר (p ${fp(p)}).`,
  },
  known: {
    title: 'מי נח ובן השונמית',
    text: (k: number, ranks: string) => `שתיהן בין ${numHe(k)} הפרקים הראשונים לפרשתן? בדירוג ${ranks}.`,
    rank: (name: string, r: number) => `${name} ${numHe(r)}`,
  },
  modesTitle: 'איך כל מערכת מוצאת את ההפטרה',
  modesLede: (n: number) => `הרשימה של כל אחת מ־${numHe(n)} הפרשות שההפטרה שלהן הולכת אחריהן, כשההפטרה היא התשובה הנכונה: התקן הראשון שיש לפרשות.`,
  modes: { lexical: 'מילים (TF-IDF)', semantic: 'משמעות (BEREL)', fused: 'שתיהן (משולב)' },
  cols: {
    system: 'מערכת',
    mrr: 'MRR',
    hits: (k: number) => `בין ${numHe(k)} הראשונים`,
    median: 'דירוג חציוני',
    pct: 'אחוזון ממוצע',
    num: '#',
    parasha: 'פרשה',
    haftarah: 'הפטרה',
    rank: 'דירוג (מילים · משמעות)',
  },
  calendarTag: { admonition: 'פורענותא', consolation: 'נחמתא' },
  calendarHint: 'נקבעה בלוח השנה, לא נבחרה בגלל הפרשה',
  sephardi: (refs: string) => `ספרדים: ${refs}`,
  of: (r: number, lex: number, sem: number) => `${numHe(r)} (${numHe(lex)} · ${numHe(sem)})`,
  showList: (name: string) => `פרקי הנביאים לפרשת ${name}`,
  listTitle: (name: string) => `${name}: פרקי הנביאים הראשונים`,
  listLede: (haft: string) => `ההפטרה: ${haft}. מדורגים בשתי המערכות יחד; הפרקים שבהם ההפטרה מסומנים.`,
  inHaftarah: 'ההפטרה',
  compare: 'השוואה',
  close: 'סגירה',
  credit: 'הזיווגים: Hebcal leyning, Copyright (c) 2020, hebcal (BSD 2-Clause License), הפטרות האשכנזים.',
}
