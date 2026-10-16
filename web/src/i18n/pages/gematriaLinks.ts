// Interface strings of Patterns → Equal values, related words? (DESIGN.md §16.59). English first,
// Hebrew typed against it.

import type { GematriaPairSort, LinkMeasure, LinkProperty } from '../../api/types'
import { countEn, countHe, numEn, numHe, pct } from '../fmt'

const moreVersesHe = (n: number) => countHe(n, 'פסוק אחד נוסף', 'שני פסוקים נוספים', 'פסוקים נוספים')

export const glEn = {
  title: 'Equal values, related words?',
  lede: 'Gematria pairs words of equal letter value (נחש and משיח are both 358, יין and סוד both 70) and reads the pairing as a link in meaning. Are words of equal value any closer in meaning than words that merely look alike: of the same length and about as common? And are the numbers claimed for Genesis 1:1 rarer than any verse’s own?',
  noData: 'Not computed in this build: run `bsim gematria-links`, then `bsim build-db`.',
  verdict: { holds: 'holds', fails: 'does not hold' },
  summary: (lemmas: number, pairs: number, same: number, draws: number) =>
    `${numEn(lemmas)} words (lemmas named at least three times, names left out) make ${numEn(pairs)} pairs of equal standard value; ${numEn(same)} of them are spelled with the same letters and left out. Each remaining pair is set against ${numEn(draws)} sets of matched pairs: one word kept, the other replaced by a word of the same letter count and frequency whose value differs.`,
  testTitle: 'Do equal values link related words?',
  checkTitle: 'Do the measures see relatedness? (a check)',
  checkLede: 'Pairs of one root family, matched the same way: the measures should find them closer, and they do.',
  measures: {
    domains: 'Same semantic domains',
    root: 'Same root family',
    vector: 'Used alike (BEREL)',
  } satisfies Record<LinkMeasure, string>,
  measureHints: {
    domains: 'The cosine of the two words’ SDBH domain profiles (0: no domain shared, 1: the same)',
    root: 'The share of pairs whose words are of one root family',
    vector: 'The cosine of the two words’ BEREL vectors, each the mean of its uses in context',
  } satisfies Record<LinkMeasure, string>,
  cols: { measure: 'Measure', pairs: 'These pairs', matched: 'Matched pairs', range: '90% of draws', p: 'p' },
  testVerdict: (alpha: number) =>
    `The claim holds when the pairs are more related than the matched pairs on any measure at p ≤ ${(alpha / 3).toFixed(3)} (${alpha} shared by three).`,
  // the traditional equivalences
  eqTitle: 'The tradition’s equivalences',
  eqLede: 'Each pair, and where it stands among all the pairs of equal value: “closer than 74%” means its words are used more alike than in 74% of them.',
  eqCols: { pair: 'Pair', value: 'Value', domains: 'Domains', root: 'Root', vector: 'Used alike' },
  same: 'same',
  differ: 'different',
  rank: (r: number) => `closer than ${pct(r)}`,
  notFound: 'not among the words tested',
  // Genesis 1:1
  verseTitle: (ref: string) => `The numbers of ${ref}`,
  props: (p: LinkProperty) =>
    ({
      words: `${p.n} words`,
      letters: `${p.n} letters`,
      multiple: `a value divisible by ${p.n}`,
      triangular: 'a triangular value (1 + 2 + 3 + …)',
      prime_factors: `a value of ${p.n} prime factors`,
    })[p.kind],
  propCols: { prop: 'Property', here: 'Here', verses: 'Verses with it' },
  allLine: (ref: string, all: number, expected: number) =>
    `${all === 1 ? `Only ${ref} has` : `${numEn(all)} verses have`} all of them; ${expected.toFixed(3)} would, were they independent. But they were chosen by looking at it.`,
  ownLine: (ref: string, words: number, letters: number, prime: number, twins: number, share: number) =>
    `A fairer question: is ${ref} singular by its own numbers? Described by them (${numEn(words)} words, ${numEn(letters)} letters, a value whose largest prime factor is ${numEn(prime)}), ${twins ? `it shares its description with ${countEn(twins, 'other verse', 'other verses')}` : 'it is the only verse with its description'}, while ${pct(share)} of all verses are the only one with their own.`,
  twins: 'Its twins',
  // the pairs
  pairsTitle: 'The pairs',
  sort: 'Order',
  sorts: { vector: 'Used most alike', domains: 'Most domains shared', value: 'By value' } satisfies Record<GematriaPairSort, string>,
  sameLetters: 'With pairs spelled alike',
  valueFilter: 'Value',
  allValues: 'Any value',
  pairsSummary: (n: number) => countEn(n, 'pair', 'pairs'),
  pageOf: (page: number, pages: number) => `page ${numEn(page)} of ${numEn(pages)}`,
  emptyPairs: 'No pairs.',
  pairLine: (vector: number, domains: number) => `used alike ${vector.toFixed(2)} · domains ${pct(domains)}`,
  oneRoot: 'one root',
  spelledAlike: 'spelled alike',
  valueTitle: (v: number) => `Everything worth ${numEn(v)}`,
}

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
    vector: 'הקוסינוס בין וקטורי BEREL של שתי המילים, כל אחד ממוצע שימושיה בהקשרם',
  },
  cols: { measure: 'מדד', pairs: 'זוגות אלה', matched: 'זוגות מותאמים', range: '90% מההגרלות', p: 'p' },
  testVerdict: (alpha: number) =>
    `הטענה עומדת כשהזוגות קרובים יותר מהזוגות המותאמים באחד המדדים ב־p ≤ ${(alpha / 3).toFixed(3)} (${alpha} מחולק בין שלושה).`,
  eqTitle: 'השקילויות שבמסורת',
  eqLede: 'כל זוג, ומקומו בין כל הזוגות שווי הערך: ״קרוב מ־74%״ פירושו שמילותיו משמשות בדומה יותר מאשר ב־74% מהם.',
  eqCols: { pair: 'זוג', value: 'ערך', domains: 'תחומים', root: 'שורש', vector: 'שימוש דומה' },
  same: 'אחד',
  differ: 'שונה',
  rank: (r: number) => `קרוב מ־${pct(r)}`,
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
  propCols: { prop: 'תכונה', here: 'כאן', verses: 'פסוקים שבהם' },
  allLine: (ref: string, all: number, expected: number) =>
    `${all === 1 ? `רק ל־${ref} יש` : `ל־${numHe(all)} פסוקים יש`} את כולן; ${expected.toFixed(3)} היו, לו היו בלתי תלויות. אבל הן נבחרו מתוך התבוננות בו.`,
  ownLine: (ref: string, words: number, letters: number, prime: number, twins: number, share: number) =>
    `שאלה הוגנת יותר: האם ${ref} יחיד במספריו שלו? בתיאור לפיהם (${numHe(words)} מילים, ${numHe(letters)} אותיות, ערך שגורמו הראשוני הגדול הוא ${numHe(prime)}) ${twins ? `הוא חולק את תיאורו עם ${moreVersesHe(twins)}` : 'הוא הפסוק היחיד בתיאורו'}, ואילו ${pct(share)} מכל הפסוקים יחידים בתיאור שלהם.`,
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
