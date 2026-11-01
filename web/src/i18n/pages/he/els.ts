// The Hebrew half of `../els.ts` (loaded with the Hebrew interface only).
import { countHe, numHe } from '../../fmt'
import { elsEn, fp, ratio, sr } from '../els'

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
