// The Hebrew half of `../haftarot.ts` (loaded with the Hebrew interface only).
import { numHe } from '../../fmt'
import { fp, hfEn, pct } from '../haftarot'

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
