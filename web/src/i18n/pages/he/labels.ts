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
  caveat: 'הם מתארים את מה שהוצג לך — בעיקר ראש הרשימות של שיטה אחת — ולא את המקרא כולו. `bsim eval-labels` מדרג את המערכות הסופיות על זוגות הפסוקים של חלוקת הפיתוח, ושום דבר לא מכוונן עליהם. זוגות בין שני ספרי אימון יכולים לאמן גרסה של מודל המשמעות (ראו את התור). הסימונים נשמרים במחשב הזה (data/labels.sqlite), בנפרד מהתוצאות.',
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
  view: 'תצוגה',
  views: { labels: 'הסימונים שלך', queue: 'מה לשפוט עכשיו' },
  queueMode: 'התור',
  queueLede:
    'זוגות ששתי דרכי הקריאה חלוקות עליהם יותר מכול: שיטה אחת מדרגת את הזוג בראש, והאחרת נמוך או בכלל לא. השיפוט שלך אומר איזו מהן צדקה, ולכן מזוגות אלה לומדים הכי הרבה. מוצעים רק זוגות פסוקים בין שני ספרי אימון, כדי שהסימונים יוכלו לאמן את מודל המשמעות בלי שספרי הפיתוח והמבחן ייראו.',
  queueTraining: (real: number, need: number) =>
    `יש לך ${numHe(real)} זוגות קשר בין ספרי אימון. אימון עליהם (bsim supervision-exp --only labels) דורש ${numHe(need)}; זוגות ה״לא״ שלך נעשים הדוגמאות השליליות שהמודל לומד לדרג נמוך. הגרסה נשמרת רק אם היא עומדת בכלל האימוץ על מערכי הזהב של הפיתוח.`,
  queueSide: 'מדורג גבוה יותר לפי',
  either: 'כל אחת',
  queueCounts: (total: number, pool: number, labelled: number) =>
    `${total === 1 ? 'זוג אחד' : `${numHe(total)} זוגות`} לשיפוט · ${numHe(labelled)} מתוך ${numHe(pool)} נשפטו`,
  ranks: (lex: string, sem: string) => `דירוג מילולי ${lex} · דירוג משמעות ${sem}`,
  beyond: (k: number) => `מעבר ל־${numHe(k)}`,
  queueNone: 'לא נשאר כאן מה לשפוט.',
  queueMore: 'הזוגות הבאים',
  queueMoreTitle: 'הצגת הזוגות הבאים; אלה ששפטת יוצאים מהתור',
  queueMissing: 'התור צריך את חלוקת הספרים: הריצו bsim build-links.',
}
