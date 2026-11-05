// The Hebrew half of `../gematriaLinks.ts` (loaded with the Hebrew interface only).
import type { LinkProperty } from '../../../api/types'
import { countHe, numHe, pct } from '../../fmt'
import { glEn, moreVersesHe } from '../gematriaLinks'

export const glHe: typeof glEn = {
  title: 'שווים במספר, קרובים במשמעות?',
  lede: 'הגימטריה מצמידה מילים ששוות בערכן (נחש = משיח = 358, יין = סוד = 70) וקוראת בכך קשר של משמעות. האם מילים שוות ערך קרובות במשמעותן יותר ממילים שרק דומות להן: באורכן ובשכיחותן? והאם המספרים שנאמרו על בראשית א:א נדירים יותר משל כל פסוק אחר?',
  noData: 'לא חושב בבנייה זו: יש להריץ `bsim gematria-links` ואחר כך `bsim build-db`.',
  verdict: { holds: 'עומדת', fails: 'אינה עומדת' },
  summary: (lemmas: number, pairs: number, same: number, draws: number) =>
    `${numHe(lemmas)} מילים (לממות שנזכרות שלוש פעמים לפחות, בלי שמות) יוצרות ${numHe(pairs)} זוגות שווי ערך במספר הרגיל; ${numHe(same)} מהם נכתבים באותן אותיות ואינם נבדקים. כל זוג אחר נמדד מול ${numHe(draws)} סדרות של זוגות מותאמים: מילה אחת נשארת, והאחרת מוחלפת במילה באותו מספר אותיות ובאותה שכיחות, שערכה שונה.`,
  testTitle: 'האם ערכים שווים מקשרים מילים קרובות?',
  checkTitle: 'האם המדדים רואים קרבה? (בדיקה)',
  checkLede: 'זוגות ממשפחת שורש אחת, מותאמים באותה הדרך: המדדים אמורים למצוא אותם קרובים, וכך הם מוצאים.',
  measures: { domains: 'אותם תחומי משמעות', root: 'אותה משפחת שורש', vector: 'שימוש דומה (BEREL)' },
  measureHints: {
    domains: 'הקוסינוס בין פרופילי תחומי SDBH של שתי המילים (0: אין תחום משותף, 1: זהים)',
    root: 'שיעור הזוגות שמילותיהם ממשפחת שורש אחת',
    vector: 'הקוסינוס בין וקטורי BEREL של שתי המילים, כל אחד ממוצע שימושי מילתו בהקשר',
  },
  cols: { measure: 'מדד', pairs: 'זוגות אלה', matched: 'זוגות מותאמים', range: '90% מההגרלות', p: 'p' },
  testVerdict: (alpha: number) =>
    `הטענה עומדת כשהזוגות קרובים יותר מהזוגות המותאמים באחד המדדים ב־p ≤ ${(alpha / 3).toFixed(3)} (${alpha} מחולק בין שלושה).`,
  eqTitle: 'השקילויות שבמסורת',
  eqLede: 'כל זוג, ומקומו בין כל הזוגות שווי הערך: ״קרוב יותר מ־74%״ פירושו שמילותיו משמשות בדומה יותר מאשר ב־74% מהם.',
  eqCols: { pair: 'זוג', value: 'ערך', domains: 'תחומים', root: 'שורש', vector: 'שימוש דומה' },
  same: 'זהה',
  differ: 'שונה',
  rank: (r: number) => `קרוב יותר מ־${pct(r)}`,
  notFound: 'אינו בין המילים שנבדקו',
  verseTitle: (ref: string) => `המספרים של ${ref}`,
  props: (p: LinkProperty) =>
    ({
      words: `${p.n} מילים`,
      letters: `${p.n} אותיות`,
      multiple: `ערך המתחלק ב־${p.n}`,
      triangular: 'ערך משולש (1 + 2 + 3 + …)',
      prime_factors: `ערך בן ${p.n} גורמים ראשוניים`,
    })[p.kind],
  propCols: { prop: 'תכונה', here: 'כאן', verses: 'פסוקים שיש להם' },
  allLine: (ref: string, all: number, expected: number) =>
    `${all === 1 ? `רק ל־${ref} יש` : `ל־${numHe(all)} פסוקים יש`} את כולן; לו היו בלתי תלויות, היו צפויים ${expected.toFixed(3)}. אבל הן נבחרו מתוך התבוננות בו.`,
  ownLine: (ref: string, words: number, letters: number, prime: number, twins: number, share: number) =>
    `שאלה הוגנת יותר: האם ${ref} יחיד במספריו שלו? בתיאור לפיהם (${numHe(words)} מילים, ${numHe(letters)} אותיות, ערך שגורמו הראשוני הגדול ביותר הוא ${numHe(prime)}) ${twins ? `הוא חולק את תיאורו עם ${moreVersesHe(twins)}` : 'הוא הפסוק היחיד בתיאורו'}, ואילו ${pct(share)} מכל הפסוקים יחידים בתיאור שלהם.`,
  twins: 'תאומיו',
  pairsTitle: 'הזוגות',
  sort: 'סדר',
  sorts: { vector: 'השימוש הדומה ביותר', domains: 'הכי הרבה תחומים משותפים', value: 'לפי ערך' },
  sameLetters: 'כולל זוגות שנכתבים באותן אותיות',
  valueFilter: 'ערך',
  allValues: 'כל ערך',
  pairsSummary: (n: number) => countHe(n, 'זוג אחד', 'שני זוגות', 'זוגות'),
  pageOf: (page: number, pages: number) => `עמוד ${numHe(page)} מתוך ${numHe(pages)}`,
  emptyPairs: 'אין זוגות.',
  pairLine: (vector: number, domains: number) => `שימוש דומה ${vector.toFixed(2)} · תחומים ${pct(domains)}`,
  oneRoot: 'שורש אחד',
  spelledAlike: 'אותן אותיות',
  valueTitle: (v: number) => `כל מה ששווה ${numHe(v)}`,
}
