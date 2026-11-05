// The Hebrew half of `../sums.ts` (loaded with the Hebrew interface only).
import { countHe, numHe } from '../../fmt'
import { fp, pct, smEn } from '../sums'

export const smHe: typeof smEn = {
  title: 'האם החשבון מסתדר?',
  lede: 'הכתוב סופר ומחבר. במדבר א מונה את אנשי כל שבט ואחר כך את כולם; עזרא ב מונה את המשפחות שעלו ואחר כך את כל הקהל, סכום שהמשפחות אינן מגיעות אליו. כאן כל רשימה מחוברת מול הסכום שהכתוב נותן, והמספרים של כתובים מקבילים מוצגים זה לצד זה.',
  notComputed: 'החשבונות לא חושבו בבנייה הזו (הריצו bsim sums).',
  checksTitle: 'בדיקות שנקבעו מראש',
  holds: 'אושש',
  fails: 'לא אושש',
  lists: {
    title: 'כל רשימה מסתכמת, או לא, כידוע',
    text: (adding: number, n: number) =>
      `${numHe(adding)} מתוך ${numHe(n)} הרשימות מסתכמות בסכום שהכתוב נותן. המפקדים היו צריכים להסתכם; הלויים של במדבר ג, כלי המקדש של עזרא א והעולים של עזרא ב ונחמיה ז לא. בדיקה של קריאת המספרים.`,
  },
  step: {
    title: 'המקבילות נבדלות בצעד אחד',
    text: (k: number, n: number, share: number | null, expected: number | null, p: number) =>
      `מתוך ${numHe(n)} המספרים ששונים בין פסוקים מקבילים בספרים שונים, ${numHe(k)} (${pct(share)}) רחוקים זה מזה בצעד אחד: חזקה של עשר (40,000 / 4,000) או ספרה אחת (18 / 8), כמו שמעתיק עשוי לשנות. אילו נבחר המספר השני באקראי מספרו, היו כאלה ${pct(expected)} (p ${fp(p)}).`,
    every: (share: number | null, expected: number | null, p: number) =>
      `הריצה הראשונה ספרה גם צמדים בתוך ספר אחד (רובם נוסחאות חוזרות): ${pct(share)} מול ${pct(expected)} (p ${fp(p)}).`,
  },
  known: {
    title: 'מפקד דוד, אורוות שלמה, גיל יהויכין',
    found: (a: number, b: number) => `${numHe(a)} / ${numHe(b)}`,
    oneStep: 'צעד אחד',
    notOneStep: 'לא צעד אחד',
    missing: 'לא נמצא',
  },
  listsTitle: 'הרשימות',
  name: {
    gen46: 'בית יעקב היורד מצרימה',
    num1: 'המפקד בסיני',
    num2_east: 'המחנה קדמה',
    num2_south: 'המחנה תימנה',
    num2_west: 'המחנה ימה',
    num2_north: 'המחנה צפונה',
    num2: 'ארבעת המחנות',
    num3: 'פקודי הלויים',
    num4: 'הלויים בעבודה',
    num26: 'המפקד בערבות מואב',
    ezra1: 'כלי המקדש',
    ezra2: 'העולים (עזרא)',
    neh7: 'העולים (נחמיה)',
  } as Record<string, string>,
  cols: {
    list: 'רשימה',
    items: 'מספרים',
    sum: 'בחיבור',
    total: 'הסכום בכתוב',
    diff: 'הפרש',
    adds: 'מסתכם',
    known: 'כידוע',
  },
  yes: 'כן',
  no: 'לא',
  showItems: (name: string) => `המספרים של ${name}`,
  itemsTitle: (name: string) => `${name}: כל מספר`,
  totalVerse: 'הסכום',
  close: 'סגירה',
  parallelsTitle: 'מספרים בפסוקים מקבילים',
  parallelsLede: 'המספרים של כל פסוק, מיושרים לפי הסדר ולפי היחידה (מניין, שנים, חודשים, ימים) מול המספרים של המקביל לו. הצמדים באים מרצפי המקבילות, מן המקבילות של ETCBC ומן הקישורים של ספריא.',
  scope: { label: 'צמדים', across: 'ספרים שונים', every: 'כל הצמדים' },
  step3: { label: 'שוני', all: 'הכול', yes: 'צעד אחד', no: 'רחוקים יותר' },
  unit: { count: 'מניין', year: 'שנים', month: 'חודשים', day: 'ימים' } as Record<string, string>,
  pairCount: (n: number) => countHe(n, 'מספר אחד שונה', 'שני מספרים שונים', 'מספרים שונים'),
  pageOf: (p: number, n: number) => `עמוד ${numHe(p)} מתוך ${numHe(n)}`,
  empty: 'אין כאן מספרים.',
  limits: 'המספרים נקראים מן המילים (מספרים יסודיים; מספרים סודרים אינם מניין). המספרים מוצמדים לפי הסדר ולפי היחידה בלבד, כך שצמד יכול להעמיד זה מול זה שני מספרים שאינם מונים את אותו הדבר.',
}
