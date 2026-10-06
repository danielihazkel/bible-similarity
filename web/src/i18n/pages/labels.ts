// Interface strings of your labels (DESIGN.md §16.25): the buttons on proposed pairs and the
// Labels page. English first, Hebrew typed against it.

import { numEn, numHe } from '../fmt'

type LabelValue = 'real' | 'not' | 'unsure'

export const labEn = {
  group: 'Your judgement of this pair',
  values: { real: 'Real', not: 'Not', unsure: 'Unsure' } as Record<LabelValue, string>,
  titles: {
    real: 'A connection worth recording (click again to clear)',
    not: 'A coincidence of words or meaning (click again to clear)',
    unsure: 'Not sure yet (click again to clear)',
  } as Record<LabelValue, string>,
  saveFailed: (msg: string) => `Could not save the label (${msg})`,
  title: 'Your labels',
  lede: 'Pairs you judged on Discoveries and in the lists of similar passages: real connections, coincidences, and the ones you are unsure of. Together they are a third gold set, beside the Sefaria links and the OpenBible cross-references, and the only one that says which proposed pairs are not connections.',
  caveat: 'They describe what you were shown — mostly the top of one mode’s lists — not the whole canon. `bsim eval-labels` scores the final systems on the dev-split verse pairs; nothing is tuned on them. Labels are stored on this machine (data/labels.sqlite), apart from the results.',
  readOnly: 'This server shows labels read-only.',
  counts: (real: number, not: number, unsure: number) =>
    `${numEn(real)} real · ${numEn(not)} not · ${numEn(unsure)} unsure`,
  none: 'No labels yet: mark pairs as real or not on Discoveries or in a passage’s list of similar passages.',
  evalTitle: 'How each mode separates your pairs',
  evalLede: (k: number, min: number) =>
    `A mode finds a pair when either passage ranks the other within its top ${numEn(k)}. Precision: the share of what it finds that you marked real. AUC: how often a real pair ranks above a not pair (0.5 = chance; shown with at least ${numEn(min)} of each).`,
  unitType: 'Unit',
  mode: 'Mode',
  realFound: 'Real found',
  notFound: 'Not found',
  precision: 'Precision',
  auc: 'AUC',
  show: 'Show',
  all: 'All',
  pairs: 'Labelled pairs',
  judgedIn: (mode: string, score: string) => `judged in ${mode} (score ${score})`,
  note: 'Note',
  notePlaceholder: 'Why (optional)',
}

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
