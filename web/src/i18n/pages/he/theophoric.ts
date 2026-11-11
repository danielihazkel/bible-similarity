// The Hebrew half of `../theophoric.ts` (loaded with the Hebrew interface only).
import { countHe, numHe, pct } from '../../fmt'
import type { theoEn } from '../theophoric'

export const theoHe: typeof theoEn = {
  title: 'שמות הבנויים על שם האל',
  lede: 'שמות רבים נושאים את שם האל: ירמיהו או ירמיה, יהורם או יורם, ישמעאל. הסיום הארוך ‑יהו הוא הכתיב הקדום והקצר ‑יה המאוחר, אף שרוב הספרים כותבים את שניהם. כאן כל מופע של שם שמילון HebrewStrong גוזר מן יה, יהוה או אל, לפי הצורה שבה הוא כתוב.',
  claim: (late, early, names, p) =>
    `באותם שמות, הספרים המאוחרים (דברי הימים, עזרא–נחמיה, אסתר, דניאל) כותבים את הסיום בקיצור ב־${pct(late)} מן המקרים, בראשית–מלכים ב־${pct(early)} (${countHe(names, 'שם אחד', 'שני שמות', 'שמות')} המופיעים בשני הצדדים; p ${p}, כשהכתיבים של כל שם מעורבבים בין שני הצדדים).`,
  verdict: { holds: 'מתאשר', fails: 'לא מתאשר' },
  knownTitle: 'שנקבעו מראש',
  known: (books, side, short, endings, holds) =>
    `${books}: בעיקר ${side === 'long' ? 'ארוך (‑יהו)' : 'קצר (‑יה)'}: ${short === null ? 'אין סיומים' : `${pct(short)} קצרים מתוך ${countHe(endings, 'סיום אחד', 'שני סיומים', 'סיומים')}`} · ${holds ? 'מתקיים' : 'אינו מתקיים'}`,
  notInModel:
    'הסיום הקצר נמדד גם כמאפיין של פרופיל הלשון המאוחרת, אבל הושאר מחוץ למודל: איתו הפרופיל הבחין בין הספרים פחות טוב (דברי הימים ב שומר על הכתיבים הארוכים של מלכים).',
  booksTitle: 'לפי ספר',
  cols: { book: 'ספר', yahu: '‑יהו', yah: '‑יה', short: 'קצר', yeho: 'יהו‑', yo: 'יו‑', el: 'עם אל' },
  namesTitle: 'השמות השכיחים ביותר',
  namesCols: { name: 'שם', n: 'מופעים', forms: 'צורות' },
  forms: { yahu: '‑יהו', yah: '‑יה', yeho: 'יהו‑', yo: 'יו‑', el_first: 'אל‑', el_last: '‑אל' },
  line: (divine, forms) => `בנוי על ${divine === 'el' ? 'אל' : 'יה'}: ${forms}.`,
  times: (form, n) => `${form} ${numHe(n)} פעמים`,
}
