// The Hebrew half of `../week.ts` (loaded with the Hebrew interface only).
import { numHe } from '../../fmt'
import type { wkEn } from '../week'

export const wkHe: typeof wkEn = {
  title: 'פרשת השבוע',
  lede: 'הפרשה שנקראת בשבת הקרובה, עם ההפטרה שלה ועם מה שהניתוחים של האתר מצאו בה. הלוח מחושב כאן, לארץ ישראל או לחוץ לארץ; בחרו כל תאריך כדי לראות את השבת שלו.',
  place: { label: 'קריאה', abroad: 'חוץ לארץ', israel: 'ארץ ישראל' },
  dateLabel: 'תאריך',
  prev: 'השבת הקודמת',
  next: 'השבת הבאה',
  today: 'השבוע',
  shabbat: (gregorian: string, hebrew: string) => `שבת, ${hebrew} · ${gregorian}`,
  festival: (gregorian: string) => `בשבת הזו קריאת החג באה במקום פרשת השבוע. פרשת השבוע הבאה נקראת בשבת, ${gregorian}:`,
  together: 'השבוע קוראים שתי פרשות מחוברות.',
  read: 'לקריאה',
  unitPage: 'קטעים דומים',
  haftarah: 'הפטרה',
  haftarahOf: (refs: string) => `ההפטרה: ${refs}`,
  sephardi: (refs: string) => `מנהג הספרדים: ${refs}`,
  theme: { admonition: 'אחת מתלתא דפורענותא, שהלוח קובע', consolation: 'אחת משבע דנחמתא, שהלוח קובע' } as Record<string, string>,
  rank: (r: number) => `בין 380 פרקי הנביאים, הדירוג המשולב של האתר לפרשה הזו מעמיד אותה במקום ה־${numHe(r)}.`,
  haftarotLink: 'ההפטרות ופרשותיהן',
  noHaftarah: 'ההפטרות לא חושבו בבנייה הזו.',
  foundTitle: 'מה שהניתוחים מצאו כאן',
  homeTitle: 'השבוע',
  homeLine: (names: string, gregorian: string) => `${names}, לקריאה בשבת ${gregorian}`,
  homeFestival: (names: string, gregorian: string) => `חג בשבת הזו; אחריה ${names} ב־${gregorian}`,
  open: 'פרשת השבוע',
}
