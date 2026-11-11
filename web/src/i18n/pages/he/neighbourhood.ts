// The Hebrew half of `../neighbourhood.ts` (loaded with the Hebrew interface only).
import { countHe, numHe } from '../../fmt'
import type { nbhEn } from '../neighbourhood'

export const nbhHe: typeof nbhEn = {
  title: (label) => `השכנים של ${label}`,
  lede: 'הקטעים הדומים ביותר לקטע הזה, והקטעים הדומים ביותר להם, כשכל זוג מחובר במה שקושר אותו: ניסוח משותף, משמעות משותפת, צירוף משותף, מקבילה שכבר נרשמה, רצף מקביל, מילים נדירות משותפות, ציטוט, הד בין פרקים. לחצו על קטע כדי להציב אותו במרכז.',
  k: 'תוצאות לכל קטע',
  hops: 'צעדים החוצה',
  hopNames: { 1: 'אחד', 2: 'שניים' },
  kindsLabel: 'הקשרים המוצגים',
  kinds: {
    lexical: 'ניסוח משותף',
    semantic: 'משמעות משותפת',
    phrase: 'צירוף משותף',
    known: 'מקבילה שכבר נרשמה',
    sequence: 'רצף מקביל',
    allusion: 'מילים נדירות משותפות',
    citation: 'ציטוט',
    borrowing: 'שאילה בין פרקים',
    echo: 'הד בין פרקים',
    fused: 'רק ברשימה המשולבת',
  },
  colourNote: 'קשר מצויר בצבע של הסוג הראשון שלו ברשימה הזאת.',
  graphLabel: 'השכנים כגרף',
  nodeTitle: (label, hop) => (hop === 0 ? `${label}: הקטע שבמרכז` : `${label}: ${countHe(hop, 'צעד אחד', 'שני צעדים', 'צעדים')} החוצה`),
  truncated: (n) => `מוצגים רק ${n} הקטעים הראשונים; פחות תוצאות לכל קטע או צעד אחד החוצה יראו את השאר.`,
  none: 'לא נשמר דבר כדומה לקטע הזה.',
  zoomIn: 'הגדלה',
  zoomOut: 'הקטנה',
  reset: 'חזרה לגרף כולו',
  svg: 'הורדת הגרף (SVG)',
  open: 'פתיחת הקטע',
  tableTitle: (n) => `הקטעים המוצגים (${numHe(n)})`,
  cols: { passage: 'קטע', hop: 'צעדים החוצה', kinds: 'הקשר למרכז', centre: 'הצבה במרכז' },
  centreIt: 'במרכז',
  link: 'השכנים שלו כגרף',
}
