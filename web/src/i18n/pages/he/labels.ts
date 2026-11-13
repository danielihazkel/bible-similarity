// The Hebrew half of `../labels.ts` (loaded with the Hebrew interface only).
import { numHe } from '../../fmt'
import type { labEn } from '../labels'

export const labHe: typeof labEn = {
  group: 'השיפוט שלכם לזוג הזה',
  values: { real: 'קשר', not: 'לא', unsure: 'לא בטוח' },
  titles: {
    real: 'קשר שראוי לתעד (לחיצה נוספת מבטלת)',
    not: 'צירוף מקרים של מילים או משמעות (לחיצה נוספת מבטלת)',
    unsure: 'עוד לא בטוח (לחיצה נוספת מבטלת)',
  },
  removed: 'הסימון הוסר',
  noteSaved: 'ההערה נשמרה',
  title: 'התוויות שלכם',
  lede: 'זוגות ששפטתם בתגליות וברשימות הקטעים הדומים: קשרים אמיתיים, צירופי מקרים, ואלה שאינכם בטוחים בהם. יחד הם מערך זהב שלישי, לצד קישורי ספריא והפניות OpenBible, והיחיד שאומר אילו מהזוגות המוצעים אינם קשרים.',
  caveat: 'הם מתארים את מה שהוצג לכם — בעיקר ראש הרשימות של שיטה אחת — ולא את המקרא כולו. `bsim eval-labels` מעריך את המערכות הסופיות על זוגות הפסוקים של חלוקת הפיתוח, ושום דבר לא מכוונן עליהם. זוגות בין שני ספרי אימון יכולים לאמן גרסה של מודל המשמעות (ראו את התור). הסימונים נשמרים במחשב הזה (data/labels.sqlite), בנפרד מהתוצאות.',
  readOnly: 'השרת הזה מציג סימונים לקריאה בלבד.',
  counts: (real: number, not: number, unsure: number) =>
    `קשר: ${numHe(real)} · לא: ${numHe(not)} · לא בטוח: ${numHe(unsure)}`,
  none: 'אין עדיין סימונים: סמנו זוגות כקשר או לא בתגליות או ברשימת הקטעים הדומים של קטע.',
  evalTitle: 'עד כמה כל שיטה מבחינה בין הזוגות שלכם',
  evalLede: (k: number, min: number) =>
    `שיטה מוצאת זוג כשאחד הקטעים מדרג את האחר בין ${numHe(k)} הראשונים שלו. דיוק: החלק ממה שהיא מוצאת שסימנת כקשר. AUC: באיזו תדירות זוג שסימנת כקשר מדורג מעל זוג שסימנת כלא־קשר (0.5 = מקרי; מוצג עם ${numHe(min)} לפחות מכל סוג).`,
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
  views: { labels: 'התוויות שלכם', queue: 'מה לשפוט עכשיו' },
  queueMode: 'התור',
  queueLede:
    'זוגות ששתי דרכי הקריאה חלוקות עליהם יותר מכול: שיטה אחת מדרגת את הזוג בראש, והאחרת נמוך או בכלל לא. השיפוט שלכם אומר איזו מהן צדקה, ולכן מזוגות אלה לומדים הכי הרבה. מוצעים רק זוגות פסוקים בין שני ספרי אימון, כדי שהסימונים יוכלו לאמן את מודל המשמעות בלי שהמודל יראה את ספרי הפיתוח והמבחן.',
  queueTraining: (real: number, need: number) =>
    `יש לכם ${numHe(real)} זוגות קשר בין ספרי אימון. אימון עליהם (bsim supervision-exp --only labels) דורש ${numHe(need)}; זוגות ה״לא״ שלכם נעשים הדוגמאות השליליות שהמודל לומד לדרג נמוך. הגרסה נשמרת רק אם היא עומדת בכלל האימוץ על מערכי הזהב של הפיתוח.`,
  queueSide: 'מדורג גבוה יותר לפי',
  either: 'כל אחת',
  queueCounts: (total: number, pool: number, labelled: number) =>
    `${total === 1 ? 'זוג אחד' : `${numHe(total)} זוגות`} לשיפוט · ${numHe(labelled)} מתוך ${numHe(pool)} נשפטו`,
  ranks: (lex: string, sem: string) => `דרגה מילולית ${lex} · דרגה סמנטית ${sem}`,
  beyond: (k: number) => `מעבר ל־${numHe(k)}`,
  queueNone: 'לא נשאר כאן מה לשפוט.',
  queueMore: 'הזוגות הבאים',
  queueMoreTitle: 'הצגת הזוגות הבאים; אלה ששפטתם יוצאים מהתור',
  queueMissing: 'התור צריך את חלוקת הספרים: הריצו bsim build-links.',
  llmLine: (model: string, auc: string, min: string, n: number, hebrew: boolean) =>
    `הצעות של ${model} ל־${numHe(n)} הזוגות הראשונים בתור (bsim llm-triage). נבדק תחילה על קישורי הפיתוח של ספריא מול זוגות אקראיים מספרי הפיתוח: AUC ${auc} (מוצג החל מ־${min}). אלה הצעות בלבד: שום דבר לא מסומן עד שתלחצו, והנימוקים שלו הם שלו, ב${hebrew ? 'עברית' : 'אנגלית'}.`,
  llmHidden: (auc: string, min: string) =>
    `ההצעות של Claude מוסתרות: על קישורי הפיתוח של ספריא מול זוגות אקראיים ה־AUC שלו היה ${auc}, מתחת ל־${min} שנקבע מראש.`,
  onlySuggested: 'רק זוגות עם הצעה',
  suggests: (verdict: string, p: string, kind: string) => `Claude מציע: ${verdict} (p ${p}, ${kind}).`,
  kinds: {
    quotation: 'ציטוט',
    allusion: 'רמז',
    parallel_account: 'סיפור מקביל',
    shared_formula: 'נוסחה משותפת',
    shared_phrase: 'צירוף משותף',
    thematic: 'נושאי',
    none: 'אין קשר',
  },
}
