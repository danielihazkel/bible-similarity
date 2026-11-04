// The Hebrew half of `../sourceFind.ts` (loaded with the Hebrew interface only).
import { countHe, numHe } from '../../fmt'
import type { sfEn } from '../sourceFind'

export const sfHe: typeof sfEn = {
  title: 'מאתר המקורות',
  lede: 'הדביקו טקסט עברי, תפילה, משנה, מכתב, והצירופים שהוא לוקח מן המקרא יסומנו, כל אחד עם הפסוק שלו. הכתיב, הניקוד ושם ה׳ הכתוב ה׳ או יי אינם משנים.',
  label: 'טקסט עברי',
  placeholder: 'אשרי יושבי ביתך…',
  submit: 'איתור המקורות',
  examples: 'נסו',
  exampleNames: { ashrei: 'אשרי', aleinu: 'עלינו', priestly: 'ברכת כהנים', mishnah: 'משנה ברכות א:ג' } as Record<string, string>,
  chars: (n: number, max: number) => `${numHe(n)} מתוך ${numHe(max)} תווים`,
  tooLong: (max: number) => `הטקסט ארוך מ־${numHe(max)} תווים; קצרו אותו כדי לחפש.`,
  none: 'לא נמצא בטקסט הזה צירוף מן המקרא.',
  found: (n: number, words: number) => `${countHe(n, 'קטע אחד', 'שני קטעים', 'קטעים')} מן המקרא, ${countHe(words, 'מילה אחת', 'שתי מילים', 'מילים')} של הטקסט.`,
  textTitle: 'הטקסט, וצירופי המקרא שבו מסומנים',
  listTitle: 'הקטעים',
  passageLabel: (i: number) => `קטע ${numHe(i)}`,
  matched: (n: number) => countHe(n, 'מילה אחת תואמת', 'שתי מילים תואמות', 'מילים תואמות'),
  alsoIn: 'אותן מילים גם ב',
  how: 'כל זוג מילים סמוכות מחופש בפסוקים; פסוק שיש בו הזוג מיושר עם הטקסט סביבו, ומילים נדירות שוקלות יותר. צירופים נפוצים עד שהם בפסוקים רבים אינם פותחים חיפוש, כך שנוסחה לבדה אינה מקור.',
}
