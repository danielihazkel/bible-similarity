// The Hebrew half of `../borrowing.ts` (loaded with the Hebrew interface only).
import { numHe } from '../../fmt'
import type { borEn } from '../borrowing'

export const borHe: typeof borEn = {
  title: 'מי שאל ממי',
  lede: 'בקטעים מקבילים בשני ספרים: איזה צד נראה מאוחר, ולכן השואל. ארבעה סימנים, שנקבעו לפני שנראתה תוצאה כלשהי, משווים בין שני הצדדים; אלה שעוברים את הבדיקה שלמטה מצביעים.',
  caveat:
    'טקסט שנראה מאוחר הוא ראיה ולא הוכחה: שניהם עשויים לשאוב ממקור משותף, ומעתיקים עדכנו כתיב ודקדוק. כל כיוון שהחוקרים מקבלים הולך מספר מוקדם בסדר הכתובים לספר מאוחר בו, ולכן הבדיקה אינה מבחינה בין הסימנים לבין סדר הספרים (הם אינם רואים אותו).',
  signs: { language: 'לשון', spelling: 'כתיב', smoothing: 'החלקה', expansion: 'הרחבה' },
  signHints: {
    language: 'סימני עברית מקראית מאוחרת בכל צד (מילים מאוחרות, אני במקום אנכי, פחות מקורות מוחלטים …)',
    spelling: 'איזה צד כותב ו ו־י בכתיב מלא יותר במילים הזהות',
    smoothing: 'במקום שמילה הוחלפה: האם מילה נדירה הוחלפה במילה שכיחה',
    expansion: 'האם צד אחד מוסיף יותר מילים משהוא משמיט',
  },
  allSigns: 'כל הארבעה, בהצבעה',
  checkTitle: 'בדיקה: מקבילות שכיוונן מקובל',
  checkLede: (n: number) =>
    `${numHe(n)} מקבילות בין ספרים שרוב החוקרים מקבלים את כיוון השאילה ביניהם: שמואל–מלכים ← דברי הימים, בראשית ויהושע ← דברי הימים א, תהלים ← דברי הימים א טז, מלכים ב ← ירמיהו נב, שמות ← דברים.`,
  right: (a: number, n: number, p: string) => `${numHe(a)} מתוך ${numHe(n)} נכונים (מבחן סימנים p = ${p})`,
  votes: 'מצביע',
  noVote: 'מוצג, אינו מצביע',
  heldOut: (a: number, n: number, u: number) =>
    `הסימנים המצביעים נבחרו בלי כל זוג ספרים ונבדקו עליו: ${numHe(a)} מתוך ${numHe(n)} נכונים, ${numHe(u)} לא הוכרעו.`,
  pairs: 'זוגות ספרים',
  flow: (src: string, dst: string) => `${src} ← ${dst}`,
  unclear: 'לא ברור',
  accepted: 'כיוון מקובל',
  counts: (n: number, ab: number, ba: number) =>
    `${numHe(n)} מקבילות: ${numHe(ab)} מצביעות לכיוון אחד, ${numHe(ba)} לאחר`,
  later: (side: string) => `${side} מאוחר`,
  parallel: 'מקבילה',
  direction: 'כיוון',
  noData: 'אין הערכות כיוון בבנייה זו (הריצו `bsim borrowing`).',
  line: (src: string, dst: string, votes: number) =>
    `מי שאל ממי? ${src} ← ${dst} (${numHe(votes)} סימנים; הצד שנראה מאוחר שאב מן האחר)`,
  lineUnclear: (a: string, b: string) => `מי שאל ממי? ${a} ↔ ${b}: הסימנים חלוקים או שותקים`,
}
