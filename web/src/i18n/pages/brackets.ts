// Interface strings of the resumptive repetition page (DESIGN.md §16.67): clauses said again after
// a block, and whether the block interrupts the text around it. English first, Hebrew typed
// against it.

import { countEn, countHe, numEn, numHe } from '../fmt'

const fp = (p: number) => (p < 0.001 ? '< 0.001' : p < 0.01 ? p.toFixed(3) : p.toFixed(2))
const x2 = (x: number) => x.toFixed(2)

export const brkEn = {
  title: 'Resumptive repetition',
  lede: 'An editor who sets a block into a story often comes back to it by repeating the clause that stood before the block: Genesis 37:36 and 39:1 tell twice that Joseph was sold to Potiphar, and Judah and Tamar stand between. Every clause said again 3 to 40 verses later in the same book is found here, and the verses between are weighed against the text around them.',
  notComputed: 'The resumptive repetitions were not computed in this build (run bsim brackets).',
  checksTitle: 'Checks fixed in advance',
  holds: 'Borne out',
  fails: 'Not borne out',
  claim: {
    title: 'The block interrupts its surroundings',
    text: (n: number, mean: number, mean0: number, p: number, leads: number, strong: number) =>
      `${countEn(n, 'repetition', 'repetitions')}. Their bracket score (how much the text before and after belongs together, beyond the block between) averages ${x2(mean)}, against ${x2(mean0)} for random brackets of the same spans in the same books (p ${fp(p)}). One by one, ${numEn(strong)} beat their random brackets at p ≤ 0.05; ${numEn(leads)} after correction for the number of brackets.`,
  },
  known: {
    title: 'The editors’ brackets the commentaries name',
    text: (found: number, beat: number, n: number) =>
      `The alignment finds ${numEn(found)} of the ${numEn(n)} named in advance; ${numEn(beat)} ${beat === 1 ? 'beats its' : 'beat their'} random brackets. The check asked for all of them.`,
    found: 'found',
    missing: 'not found',
    beats: (p: number) => `p ${fp(p)}`,
  },
  listTitle: 'The repetitions',
  show: { label: 'Show', all: 'All', strong: 'p ≤ 0.05', known: 'Named in advance' },
  order: { label: 'Order', canon: 'Canon', strongest: 'Strongest first' },
  between: (n: number) => countEn(n, 'verse between', 'verses between'),
  score: (s: number) => `bracket ${x2(s)}`,
  parts: (lex: number, sem: number) => `words ${x2(lex)}, meaning ${x2(sem)}`,
  pq: (p: number, q: number | null) => (q === null ? `p ${fp(p)}` : `p ${fp(p)}, q ${fp(q)}`),
  knownTag: 'named in advance',
  read: 'read the block',
  compare: 'compare the two',
  count: (n: number) => countEn(n, 'repetition', 'repetitions'),
  pageOf: (p: number, pages: number) => `page ${numEn(p)} of ${numEn(pages)}`,
  empty: 'No repetition here.',
  method:
    'A repetition: two verses of a book 3 to 40 apart whose content words align (Smith–Waterman on lemmas or on forms without prefixes, rare words weighing most, at least three words), each the other’s best partner. Its bracket score: the cosine of the 4 verses before the first and the 4 after the repeat, less the cosine of the block and those 8, on words (idf-weighted lemmas) and on meaning (verse embeddings), averaged. p: against 999 random brackets of the same span in the book; q: Benjamini–Hochberg over the repetitions.',
}

export const brkHe: typeof brkEn = {
  title: 'חזרה מסגרת',
  lede: 'עורך ששם קטע בתוך סיפור חוזר אליו פעמים רבות בחזרה על המשפט שעמד לפני הקטע: בראשית לז:לו ו־לט:א מספרים פעמיים שיוסף נמכר לפוטיפר, ויהודה ותמר עומדים ביניהם. כאן נמצא כל משפט שנאמר שוב 3 עד 40 פסוקים אחר כך באותו ספר, והפסוקים שביניהם נשקלים מול הטקסט שסביבם.',
  notComputed: 'החזרות המסגרות לא חושבו בבנייה זו (הריצו bsim brackets).',
  checksTitle: 'בדיקות שנקבעו מראש',
  holds: 'מתאשר',
  fails: 'לא מתאשר',
  claim: {
    title: 'הקטע קוטע את סביבתו',
    text: (n: number, mean: number, mean0: number, p: number, leads: number, strong: number) =>
      `${countHe(n, 'חזרה אחת', 'שתי חזרות', 'חזרות')}. ציון המסגרת שלהן (כמה הטקסט שלפני ושאחרי שייך זה לזה, יותר מן הקטע שביניהם) בממוצע ${x2(mean)}, לעומת ${x2(mean0)} למסגרות אקראיות באותם אורכים באותם ספרים (p ${fp(p)}). כל אחת לעצמה, ${numHe(strong)} עולות על המסגרות האקראיות שלהן ב־p ≤ 0.05; ${numHe(leads)} אחרי תיקון למספר המסגרות.`,
  },
  known: {
    title: 'מסגרות העורכים שהפרשנים מונים',
    text: (found: number, beat: number, n: number) => `היישור מוצא ${numHe(found)} מתוך ${numHe(n)} שנקבעו מראש; ${numHe(beat)} עולות על המסגרות האקראיות שלהן. הבדיקה דרשה את כולן.`,
    found: 'נמצאה',
    missing: 'לא נמצאה',
    beats: (p: number) => `p ${fp(p)}`,
  },
  listTitle: 'החזרות',
  show: { label: 'הצגה', all: 'הכול', strong: 'p ≤ 0.05', known: 'שנקבעו מראש' },
  order: { label: 'סדר', canon: 'סדר המקרא', strongest: 'החזקות תחילה' },
  between: (n: number) => countHe(n, 'פסוק אחד ביניהם', 'שני פסוקים ביניהם', 'פסוקים ביניהם'),
  score: (s: number) => `מסגרת ${x2(s)}`,
  parts: (lex: number, sem: number) => `מילים ${x2(lex)}, משמעות ${x2(sem)}`,
  pq: (p: number, q: number | null) => (q === null ? `p ${fp(p)}` : `p ${fp(p)}, q ${fp(q)}`),
  knownTag: 'נקבעה מראש',
  read: 'לקריאת הקטע',
  compare: 'השוואת השניים',
  count: (n: number) => countHe(n, 'חזרה אחת', 'שתי חזרות', 'חזרות'),
  pageOf: (p: number, pages: number) => `עמוד ${numHe(p)} מתוך ${numHe(pages)}`,
  empty: 'אין כאן חזרה.',
  method:
    'חזרה: שני פסוקים של ספר בהפרש של 3 עד 40 שמילות התוכן שלהם מתיישרות (סמית׳–ווטרמן על הלמות או על הצורות בלי תחיליות, המילים הנדירות שוקלות יותר, שלוש מילים לפחות), וכל אחד מהם בן הזוג הטוב ביותר של השני. ציון המסגרת: הקוסינוס בין 4 הפסוקים שלפני הראשון ל־4 שאחרי החוזר, פחות הקוסינוס בין הקטע לשמונה אלה, במילים (למות משוקללות idf) ובמשמעות (שיכוני פסוקים), בממוצע. p: מול 999 מסגרות אקראיות באותו אורך בספר; q: בנג׳מיני–הוכברג על פני החזרות.',
}
