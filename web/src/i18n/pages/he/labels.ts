// The Hebrew half of `../labels.ts` (loaded with the Hebrew interface only).
import { numHe } from '../../fmt'
import { labEn } from '../labels'

export const labHe: typeof labEn = {
  group: 'השיפוט שלך לזוג הזה',
  values: { real: 'קשר', not: 'לא', unsure: 'לא בטוח' },
  titles: {
    real: 'קשר שראוי לתעד (לחיצה נוספת מבטלת)',
    not: 'צירוף מקרים של מילים או משמעות (לחיצה נוספת מבטלת)',
    unsure: 'עוד לא בטוח (לחיצה נוספת מבטלת)',
  },
  saveFailed: (msg: string) => `לא ניתן לשמור את הסימון (${msg})`,
  title: 'הסימונים שלך',
  lede: 'זוגות ששפטת בתגליות וברשימות הקטעים הדומים: קשרים אמיתיים, צירופי מקרים, ואלה שאינך בטוח בהם. יחד הם מערך זהב שלישי, לצד קישורי ספריא והפניות OpenBible, והיחיד שאומר אילו מהזוגות המוצעים אינם קשרים.',
  caveat: 'הם מתארים את מה שהוצג לך — בעיקר ראש הרשימות של שיטה אחת — ולא את המקרא כולו. `bsim eval-labels` מדרג את המערכות הסופיות על זוגות הפסוקים של חלוקת הפיתוח; שום דבר לא מכוונן עליהם. הסימונים נשמרים במחשב הזה (data/labels.sqlite), בנפרד מהתוצאות.',
  readOnly: 'השרת הזה מציג סימונים לקריאה בלבד.',
  counts: (real: number, not: number, unsure: number) =>
    `${numHe(real)} קשר · ${numHe(not)} לא · ${numHe(unsure)} לא בטוח`,
  none: 'אין עדיין סימונים: סמנו זוגות כקשר או לא בתגליות או ברשימת הקטעים הדומים של קטע.',
  evalTitle: 'עד כמה כל שיטה מבחינה בין הזוגות שלך',
  evalLede: (k: number, min: number) =>
    `שיטה מוצאת זוג כשאחד הקטעים מדרג את האחר בין ${numHe(k)} הראשונים שלו. דיוק: החלק ממה שהיא מוצאת שסימנת כקשר. AUC: כמה פעמים זוג אמיתי מדורג מעל זוג שאינו (0.5 = מקרי; מוצג עם ${numHe(min)} לפחות מכל סוג).`,
  unitType: 'יחידה',
  mode: 'שיטה',
  realFound: 'קשרים שנמצאו',
  notFound: 'לא־קשרים שנמצאו',
  precision: 'דיוק',
  auc: 'AUC',
  show: 'הצג',
  all: 'הכול',
  pairs: 'זוגות מסומנים',
  judgedIn: (mode: string, score: string) => `נשפט ב־${mode} (ציון ${score})`,
  note: 'הערה',
  notePlaceholder: 'למה (לא חובה)',
}
