// Interface strings of Patterns → Letters at equal skips (DESIGN.md §16.62). English first,
// Hebrew typed against it.

import type { ElsControlKey } from '../../api/types'
import { countEn, countHe, numEn, numHe } from '../fmt'

const fp = (p: number) => (p < 0.001 ? '< 0.001' : p < 0.01 ? p.toFixed(3) : p.toFixed(2))
const sr = (x: number) => `${x >= 0 ? '+' : '−'}${Math.abs(x).toFixed(3)}`
const ratio = (x: number) => `×${x.toFixed(2)}`

export const elsEn = {
  title: 'Letters at equal skips',
  lede: 'Read every 50th letter from the ת of Genesis 1:1 and you get תורה (Rabbenu Bahya); since the 1990s “Bible codes” have read names and dates at skips in the thousands. Any long text holds such sequences by chance. Does the Torah hold more of them than its own letters shuffled, its verses shuffled, or a stretch of the other books as long? Counts against controls, not codes.',
  noData: 'Not computed in this build: run `bsim els`, then `bsim build-db`.',
  verdict: { holds: 'holds', fails: 'does not hold' },
  // the tradition's
  knownTitle: 'What the tradition read',
  knownLede: 'The sequences read at the start of each book of the Torah, found in our letters: a check of the letter string. How often the same word turns up at the same skip anywhere in the Torah says how special they are.',
  kcols: { verse: 'From', term: 'Word', skip: 'Skip', found: 'In our letters', torah: 'At this skip in the Torah' },
  found: (offset: number | null) => (offset == null ? 'not found' : `from letter ${numEn(offset + 1)} of the verse`),
  inTorah: (n: number, expected: number) => `${numEn(n)} times (${numEn(Math.round(expected))} expected by chance)`,
  // a scope
  scope: 'Text',
  scopes: { torah: 'The Torah', genesis: 'Genesis' } as Record<string, string>,
  summary: (terms: number, lo: number, hi: number, hits: number, letters: number, expected: number, r: number) =>
    `${numEn(terms)} names at skips of ${numEn(lo)} to ${numEn(hi)} letters, forwards and backwards: ${numEn(hits)} hits in ${numEn(letters)} letters, against ${numEn(Math.round(expected))} expected if the same letters were shuffled. Over the names, the hits run at ${sr(r)} on a log scale against that expectation (R).`,
  claim: (alpha: number) => `The claim, fixed in advance: the text has no more hits than its controls; it holds when no control has p ≤ ${alpha}.`,
  controlsTitle: 'Against the controls',
  ccols: { control: 'Control', n: 'Draws', mean: 'Its R (90%)', p: 'p', verdict: 'No more than the control' },
  controls: {
    letters: 'The same letters, shuffled',
    verses: 'The same verses, shuffled',
    blocks: 'Stretches of the other books, as long',
  } satisfies Record<ElsControlKey, string>,
  range: (mean: number, q05: number, q95: number) => `${sr(mean)} (${sr(q05)} to ${sr(q95)})`,
  r: sr,
  stripLabel: (r: number) => `Each control draw’s R as a dot, one row per control; the text’s R, ${sr(r)}, is the line.`,
  stripText: 'the text',
  stripRows: { letters: 'Letters shuffled', verses: 'Verses shuffled', blocks: 'Other books' } satisfies Record<ElsControlKey, string>,
  blocksTitle: 'The other books’ stretches',
  block: (label: string, r: number) => `${label}: R ${sr(r)}`,
  // terms
  termsTitle: 'Name by name',
  termsLede: 'Each name’s hits against its exact expectation under a shuffle of the letters, and against the shuffles themselves. Short names turn up hundreds of thousands of times; longer ones a handful.',
  tcols: { term: 'Name', fwd: 'Forwards', back: 'Backwards', hits: 'Hits', expected: 'Expected', ratio: 'Ratio', letters: 'Shuffled letters (90%)', p: 'p', verses: 'Shuffled verses', blocks: 'Other books' },
  ratio,
  num: (n: number) => numEn(Math.round(n)),
  lettersRange: (q05: number, q95: number) => `${numEn(Math.round(q05))}–${numEn(Math.round(q95))}`,
  p: fp,
  draws: (n: number) => countEn(n, 'draw', 'draws'),
}

export const elsHe: typeof elsEn = {
  title: 'אותיות בדילוג שווה',
  lede: 'מי שקורא כל אות חמישים מן ה־ת של בראשית א:א מוצא תורה (רבנו בחיי); מאז שנות התשעים „צופני התורה” קוראים שמות ותאריכים בדילוגים של אלפים. בכל טקסט ארוך יש רצפים כאלה במקרה. האם יש בתורה יותר מהם מאשר באותיותיה שלה מעורבבות, בפסוקיה מעורבבים, או בקטע מן הספרים האחרים באורך שווה? ספירות מול ביקורות, לא צפנים.',
  noData: 'לא חושב בבנייה זו: יש להריץ `bsim els` ואחר כך `bsim build-db`.',
  verdict: { holds: 'עומדת', fails: 'אינה עומדת' },
  knownTitle: 'מה שקראה המסורת',
  knownLede: 'הרצפים שנקראו בראש כל אחד מחומשי התורה, כפי שהם נמצאים באותיות שלנו: בדיקה של רצף האותיות. כמה פעמים אותה מילה מופיעה באותו דילוג בכל התורה מלמד עד כמה הם מיוחדים.',
  kcols: { verse: 'מן', term: 'מילה', skip: 'דילוג', found: 'באותיות שלנו', torah: 'בדילוג זה בכל התורה' },
  found: (offset: number | null) => (offset == null ? 'לא נמצא' : `מן האות ה־${numHe(offset + 1)} של הפסוק`),
  inTorah: (n: number, expected: number) => `${numHe(n)} פעמים (${numHe(Math.round(expected))} צפויות במקרה)`,
  scope: 'טקסט',
  scopes: { torah: 'התורה', genesis: 'בראשית' },
  summary: (terms: number, lo: number, hi: number, hits: number, letters: number, expected: number, r: number) =>
    `${numHe(terms)} שמות בדילוגים של ${numHe(lo)} עד ${numHe(hi)} אותיות, קדימה ואחורה: ${numHe(hits)} מופעים ב־${numHe(letters)} אותיות, לעומת ${numHe(Math.round(expected))} צפויים אילו אותן האותיות היו מעורבבות. על פני השמות, המופעים עומדים על ${sr(r)} בסולם לוגריתמי מול הצפוי (R).`,
  claim: (alpha: number) => `הטענה, שנקבעה מראש: אין בטקסט יותר מופעים מאשר בביקורות; היא עומדת כשלאף ביקורת אין p ≤ ${alpha}.`,
  controlsTitle: 'מול הביקורות',
  ccols: { control: 'ביקורת', n: 'הגרלות', mean: 'ה־R שלה (90%)', p: 'p', verdict: 'לא יותר מן הביקורת' },
  controls: {
    letters: 'אותן האותיות, מעורבבות',
    verses: 'אותם הפסוקים, מעורבבים',
    blocks: 'קטעים מן הספרים האחרים, באורך שווה',
  },
  range: (mean: number, q05: number, q95: number) => `${sr(mean)} (${sr(q05)} עד ${sr(q95)})`,
  r: sr,
  stripLabel: (r: number) => `ה־R של כל הגרלה כנקודה, שורה לכל ביקורת; ה־R של הטקסט, ${sr(r)}, הוא הקו.`,
  stripText: 'הטקסט',
  stripRows: { letters: 'אותיות מעורבבות', verses: 'פסוקים מעורבבים', blocks: 'ספרים אחרים' },
  blocksTitle: 'הקטעים מן הספרים האחרים',
  block: (label: string, r: number) => `${label}: R ${sr(r)}`,
  termsTitle: 'שם אחר שם',
  termsLede: 'המופעים של כל שם מול הצפוי בדיוק כשהאותיות מעורבבות, ומול ההגרלות עצמן. שמות קצרים מופיעים מאות אלפי פעמים; ארוכים, קומץ.',
  tcols: { term: 'שם', fwd: 'קדימה', back: 'אחורה', hits: 'מופעים', expected: 'צפוי', ratio: 'יחס', letters: 'אותיות מעורבבות (90%)', p: 'p', verses: 'פסוקים מעורבבים', blocks: 'ספרים אחרים' },
  ratio,
  num: (n: number) => numHe(Math.round(n)),
  lettersRange: (q05: number, q95: number) => `${numHe(Math.round(q05))}–${numHe(Math.round(q95))}`,
  p: fp,
  draws: (n: number) => countHe(n, 'הגרלה אחת', 'שתי הגרלות', 'הגרלות'),
}
