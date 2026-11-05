// The Hebrew half of `../binomials.ts` (loaded with the Hebrew interface only).
import { numHe } from '../../fmt'
import { bnEn, fp, pct } from '../binomials'

export const bnHe: typeof bnEn = {
  title: 'צמדי מילים',
  lede: 'העברית מצמדת מילים מסוימות בסדר קבוע: שמים וארץ, איש ואשה, כסף וזהב. יש סדרים קפואים ויש שמתהפכים. כאן הצמדים של שמות עצם, שמות פרטיים או תארים שמחוברים בו׳ וחוזרים, עם מידת הקביעות של כל סדר, אורך כל מילה, והיכן הסדר מתהפך.',
  notComputed: 'צמדי המילים לא חושבו בבנייה הזו (הריצו bsim binomials).',
  checksTitle: 'בדיקות שנקבעו מראש',
  holds: 'אושש',
  fails: 'לא אושש',
  short: {
    title: 'המילה הקצרה באה ראשונה',
    text: (lk: number, lm: number, lp: number, sk: number, sm: number, sp: number) =>
      `מן הצמדים שמילותיהם שונות באורכן, הקצרה עומדת ראשונה ב־${numHe(lk)} מתוך ${numHe(lm)} כשסופרים אותיות (p ${fp(lp)}) וב־${numHe(sk)} מתוך ${numHe(sm)} כשסופרים הברות (p ${fp(sp)}). שתיהן היו צריכות להתקיים.`,
  },
  late: {
    title: 'הספרים המאוחרים הופכים את הצמדים',
    text: (early: number | null, late: number | null, p: number, without: number) =>
      `צמד עומד בסדרו הנדיר ב־${pct(early)} מהפעמים בספרים המוקדמים (בראשית עד מלכים) וב־${pct(late)} במאוחרים (דברי הימים, עזרא, נחמיה, אסתר, דניאל), מול תקופות מעורבבות בתוך כל צמד (p ${fp(p)}). בלי כסף וזהב: p ${fp(without)}.`,
  },
  known: {
    title: 'שמים וארץ, איש ואשה, זהב וכסף',
    text: (sky: number | null, man: number | null, early: number | null, late: number | null) =>
      `שמים וארץ בסדר הזה ב־${pct(sky)} מהפעמים, איש ואשה ב־${pct(man)}; זהב וכסף במקום כסף וזהב ב־${pct(early)} מהפעמים בספרים המוקדמים, ב־${pct(late)} במאוחרים.`,
  },
  listTitle: (n: number, min: number) => `${numHe(n)} הצמדים שנמצאו ${numHe(min)} פעמים לפחות`,
  show: { label: 'הצגה', all: 'הכול', both: 'בשני הסדרים' },
  order: { label: 'סדר', common: 'השכיחים', turned: 'המתהפכים' },
  kind: { noun: 'שמות עצם', name: 'שמות פרטיים', adjective: 'תארים' } as Record<string, string>,
  cols: {
    pair: 'הצמד, בסדרו',
    kind: 'סוג',
    n: 'נמצא',
    fixed: 'בסדר הזה',
    letters: 'אותיות',
    syll: 'הברות',
    early: 'הפוך, ספרים מוקדמים',
    late: 'הפוך, ספרים מאוחרים',
  },
  of: (k: number, n: number) => (n ? `${numHe(k)} / ${numHe(n)}` : '–'),
  showPair: (pair: string) => `היכן נמצא ${pair}`,
  pairTitle: (pair: string) => `${pair}: היכן הוא נמצא`,
  ownOrder: 'בסדרו',
  rarerOrder: 'הפוך',
  listed: (n: number) => `(עד ${numHe(n)} מכל סדר)`,
  close: 'סגירה',
  empty: 'אין כאן צמד.',
  limits: 'צמד הוא שתי מילים סמוכות: את השמים ואת הארץ, שבו המילה "את" מפרידה ביניהן, אינו נספר.',
}
