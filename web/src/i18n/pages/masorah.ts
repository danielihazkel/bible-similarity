// Interface strings of Patterns → The Masorah's counts: the middle letter, words and verse of the
// Torah and each book's verses, counted on this text (DESIGN.md §16.55). English first, Hebrew
// typed against it.

import type { MasorahReason, MasorahText } from '../../api/types'
import { countEn, countHe, numEn, numHe } from '../fmt'

type Unit = 'letter' | 'word' | 'verse'
type TotalUnit = 'verses' | 'words' | 'letters'
type Source = 'masorah' | 'talmud' | 'soferim' | 'printed'

/** A distance in units, whole or with its half. */
const fd = (d: number, num: (n: number) => string) => num(Math.abs(d))
const ordEn = (k: number) => {
  const s = k % 100 >= 11 && k % 100 <= 13 ? 'th' : ({ 1: 'st', 2: 'nd', 3: 'rd' } as Record<number, string>)[k % 10] ?? 'th'
  return `${numEn(k)}${s}`
}
const unitEn: Record<Unit, [string, string]> = { letter: ['letter', 'letters'], word: ['word', 'words'], verse: ['verse', 'verses'] }
const unitHe: Record<Unit, [string, string, string]> = {
  letter: ['אות אחת', 'שתי אותיות', 'אותיות'],
  word: ['תיבה אחת', 'שתי תיבות', 'תיבות'],
  verse: ['פסוק אחד', 'שני פסוקים', 'פסוקים'],
}

export const msrEn = {
  title: 'The Masorah’s counts',
  lede: 'The first scribes were called soferim, counters, “because they counted all the letters of the Torah” (Kiddushin 30a): the ו of גחון is its middle letter, דרש דרש its middle words. The Masorah’s notes give the middle verse of each book and how many verses each book holds. Here the same things are counted on this text, in its letters as written (ketiv) and as read (qere): where each middle falls against ours, and why a total differs. It checks the text and its verse division; it is not a test against chance.',
  noData: 'Not computed in this build: run `bsim masorah`, then `bsim build-db`.',
  summary: (verses: number, wk: number, lk: number, wq: number, lq: number) =>
    `Counted here, the Torah has ${numEn(verses)} verses: as written, ${numEn(wk)} words and ${numEn(lk)} letters; as read, ${numEn(wq)} words and ${numEn(lq)} letters.`,
  kq: (pairs: number, k: number, q: number) =>
    `The two texts differ at the ${numEn(pairs)} places where the Leningrad Codex writes one thing and reads another. The text shown here reads the qere but keeps the written letters of some words, so ${countEn(k, 'word was', 'words were')} rewritten for the written text and ${numEn(q)} for the read one.`,
  text: 'Letters',
  texts: { ketiv: 'As written', qere: 'As read' } satisfies Record<MasorahText, string>,
  middlesTitle: 'The middles',
  middlesLede: (tol: number) =>
    `A span of n letters, words or verses has its middle halfway, between two of them when n is even. A middle the tradition names lands when it is at most ${countEn(tol, 'unit', 'units')} from ours.`,
  torah: 'The Torah',
  units: { letter: 'the middle letter', word: 'the middle words', verse: 'the middle verse' } satisfies Record<Unit, string>,
  heading: (span: string, unit: string) => `${span}: ${unit}`,
  sources: { masorah: 'the Masorah', talmud: 'Kiddushin 30a', soferim: 'Tractate Soferim 9:3', printed: 'the count printed at the end of Deuteronomy' } satisfies Record<Source, string>,
  verdict: { holds: 'lands', fails: 'off' },
  tradLetter: (k: number, word: string) => `the ${ordEn(k)} letter of ${word}`,
  tradWords: (words: string) => {
    const w = words.split(' ')
    return w.length === 2 ? `between ${w[0]} and ${w[1]}` : words
  },
  says: (source: string) => `According to ${source}:`,
  ours: 'Here:',
  oursLetter: (k: number, word: string) => `the ${ordEn(k)} letter of ${word}`,
  position: (unit: Unit, pos: number, n: number, even: boolean) =>
    even
      ? `between ${unitEn[unit][0]} ${numEn(pos)} and ${numEn(pos + 1)} of ${numEn(n)}`
      : `${unitEn[unit][0]} ${numEn(pos)} of ${numEn(n)}`,
  distance: (unit: Unit, d: number, verses: number) =>
    d === 0
      ? 'It is ours exactly.'
      : `It falls ${fd(d, numEn)} ${unitEn[unit][Math.abs(d) === 1 ? 0 : 1]} ${d > 0 ? 'after' : 'before'} ours${unit !== 'verse' && verses !== 0 ? `, ${countEn(Math.abs(verses), 'verse', 'verses')} ${verses > 0 ? 'on' : 'back'}` : ''}.`,
  tradVerse: 'The tradition’s place',
  ourVerse: 'Ours',
  // totals
  totalsTitle: 'Verses in each book',
  totalsLede:
    'The Masorah closes each book with the number of its verses; Samuel, Kings, the Twelve, Ezra–Nehemiah and Chronicles are one book each. The figures are those most manuscripts give, as Ginsburg collates them; other figures they give are listed.',
  cols: { book: 'Book', tradition: 'The Masorah', ours: 'Here', diff: 'Difference', why: 'Why', also: 'Other manuscripts' },
  groups: {
    samuel: 'Samuel',
    kings: 'Kings',
    twelve: 'The Twelve',
    ezra: 'Ezra–Nehemiah',
    chronicles: 'Chronicles',
    torah: 'Torah',
    prophets: 'Prophets',
    writings: 'Writings',
    bible: 'The whole Bible',
  } as Record<string, string>,
  reasons: {
    split: 'The Masorah counts this verse as two (it carries two sets of accents):',
    decalogue: 'The Ten Commandments are divided otherwise: 12 verses in the Masorah’s count, 13 here:',
    absent: 'The Masorah’s count leaves out two verses this text has (manuscripts that have them give the same total):',
    untraced: 'Counting chapter by chapter gives this text’s figure; where the Masorah’s differs is not known.',
    witnesses: 'The manuscripts disagree, and another figure they give is this text’s.',
  } satisfies Record<MasorahReason, string>,
  agree: 'agrees',
  booksAgree: (agree: number, n: number) => `${numEn(agree)} of ${numEn(n)} books have the Masorah’s total.`,
  sectionsTitle: 'Sections and the whole',
  sectionsLede:
    'The totals given for the sections and the whole, and for the Torah in words and letters. Where the Masorah gives the totals of a section’s books, their sum is shown: the section totals do not always add up from them.',
  sectionCols: { section: 'Section', count: 'Count', source: 'Given by', tradition: 'Given', ours: 'Here', diff: 'Difference', bookSum: 'Its books added' },
  totalUnits: { verses: 'Verses', words: 'Words', letters: 'Letters' } satisfies Record<TotalUnit, string>,
  countOf: (unit: string, text: string | null) => (text ? `${unit} (${text.toLowerCase()})` : unit),
  booksTitle: 'Each book, counted',
  booksCols: { book: 'Book', verses: 'Verses', wordsK: 'Words written', wordsQ: 'Words read', lettersK: 'Letters written', lettersQ: 'Letters read' },
}

export const msrHe: typeof msrEn = {
  title: 'מניין המסורה',
  lede: 'הראשונים נקראו סופרים „שהיו סופרים כל האותיות שבתורה” (קידושין ל ע״א): וא״ו דגחון חציין של אותיות, דרש דרש חציין של תיבות. הערות המסורה מוסרות את הפסוק שבאמצע כל ספר ואת מספר פסוקיו. כאן אותם דברים נמנים בנוסח הזה, באותיות הכתיב ובאותיות הקרי: היכן נופל כל אמצע לעומת האמצע שלנו, ומדוע סכום שונה. זו בדיקה של הנוסח ושל חלוקת הפסוקים, לא מבחן מול המקרה.',
  noData: 'לא חושב בבנייה זו: יש להריץ `bsim masorah` ואחר כך `bsim build-db`.',
  summary: (verses: number, wk: number, lk: number, wq: number, lq: number) =>
    `כפי שנמנים כאן, בתורה ${numHe(verses)} פסוקים: בכתיב ${numHe(wk)} תיבות ו־${numHe(lk)} אותיות; בקרי ${numHe(wq)} תיבות ו־${numHe(lq)} אותיות.`,
  kq: (pairs: number, k: number, q: number) =>
    `שני הנוסחים נבדלים ב־${numHe(pairs)} המקומות שבהם כתר לנינגרד כותב דבר אחד וקורא אחר. הנוסח המוצג כאן קורא את הקרי אבל שומר על אותיות הכתיב של מילים אחדות, ולכן ${countHe(k, 'מילה אחת נכתבה', 'שתי מילים נכתבו', 'מילים נכתבו')} מחדש בנוסח הכתיב ו־${numHe(q)} בנוסח הקרי.`,
  text: 'אותיות',
  texts: { ketiv: 'כתיב', qere: 'קרי' },
  middlesTitle: 'האמצעים',
  middlesLede: (tol: number) =>
    `אמצעו של רצף של n אותיות, תיבות או פסוקים הוא במחציתו, בין שתיים מהן כש־n זוגי. אמצע שהמסורת מונה פוגע כשהוא רחוק לכל היותר ${countHe(tol, 'יחידה אחת', 'שתי יחידות', 'יחידות')} מהאמצע שלנו.`,
  torah: 'התורה',
  units: { letter: 'האות שבאמצע', word: 'התיבות שבאמצע', verse: 'הפסוק שבאמצע' },
  heading: (span: string, unit: string) => `${span}: ${unit}`,
  sources: { masorah: 'המסורה', talmud: 'קידושין ל ע״א', soferim: 'מסכת סופרים ט:ג', printed: 'המניין הנדפס בסוף ספר דברים' },
  verdict: { holds: 'פוגע', fails: 'רחוק' },
  tradLetter: (k: number, word: string) => `האות ה־${numHe(k)} של ${word}`,
  tradWords: (words: string) => {
    const w = words.split(' ')
    return w.length === 2 ? `בין ${w[0]} ל־${w[1]}` : words
  },
  says: (source: string) => `לפי ${source}:`,
  ours: 'כאן:',
  oursLetter: (k: number, word: string) => `האות ה־${numHe(k)} של ${word}`,
  position: (unit: Unit, pos: number, n: number, even: boolean) => {
    const name = { letter: 'אות', word: 'תיבה', verse: 'פסוק' }[unit]
    return even ? `בין ${name} ${numHe(pos)} ל־${numHe(pos + 1)} מתוך ${numHe(n)}` : `${name} ${numHe(pos)} מתוך ${numHe(n)}`
  },
  distance: (unit: Unit, d: number, verses: number) =>
    d === 0
      ? 'הוא האמצע שלנו בדיוק.'
      : `הוא נופל ${Number.isInteger(d) ? countHe(Math.abs(d), ...unitHe[unit]) : `${fd(d, numHe)} ${unitHe[unit][2]}`} ${d > 0 ? 'אחרי' : 'לפני'} האמצע שלנו${unit !== 'verse' && verses !== 0 ? `, ${countHe(Math.abs(verses), 'פסוק אחד', 'שני פסוקים', 'פסוקים')} ${verses > 0 ? 'הלאה' : 'אחורה'}` : ''}.`,
  tradVerse: 'מקומו לפי המסורת',
  ourVerse: 'האמצע שלנו',
  totalsTitle: 'הפסוקים בכל ספר',
  totalsLede:
    'המסורה חותמת כל ספר במספר פסוקיו; שמואל, מלכים, תרי עשר, עזרא–נחמיה ודברי הימים הם ספר אחד כל אחד. המספרים הם אלה שמוסרים רוב כתבי היד, כפי שגינצבורג מקבץ אותם; מספרים אחרים שהם מוסרים מצוינים.',
  cols: { book: 'ספר', tradition: 'המסורה', ours: 'כאן', diff: 'הפרש', why: 'מדוע', also: 'כתבי יד אחרים' },
  groups: {
    samuel: 'שמואל',
    kings: 'מלכים',
    twelve: 'תרי עשר',
    ezra: 'עזרא–נחמיה',
    chronicles: 'דברי הימים',
    torah: 'תורה',
    prophets: 'נביאים',
    writings: 'כתובים',
    bible: 'המקרא כולו',
  },
  reasons: {
    split: 'המסורה מונה את הפסוק הזה כשניים (יש בו שני טעמים):',
    decalogue: 'עשרת הדברות מחולקים אחרת: 12 פסוקים במניין המסורה, 13 כאן:',
    absent: 'מניין המסורה אינו כולל שני פסוקים שיש בנוסח הזה (כתבי יד שיש בהם אותם מוסרים אותו סכום):',
    untraced: 'מניין הפרקים נותן את המספר שבנוסח הזה; מהיכן ההפרש במסורה אינו ידוע.',
    witnesses: 'כתבי היד חלוקים, ומספר אחר שהם מוסרים הוא שבנוסח הזה.',
  },
  agree: 'שווה',
  booksAgree: (agree: number, n: number) => `ב־${numHe(agree)} מתוך ${numHe(n)} הספרים הסכום הוא של המסורה.`,
  sectionsTitle: 'החלקים והמקרא כולו',
  sectionsLede:
    'הסכומים שנמסרו לחלקי המקרא ולמקרא כולו, ולתורה גם בתיבות ובאותיות. כשהמסורה מוסרת את סכומי ספרי החלק, סכומם מוצג: סכומי החלקים לא תמיד מתקבלים מהם.',
  sectionCols: { section: 'חלק', count: 'מניין', source: 'מוסר', tradition: 'נמסר', ours: 'כאן', diff: 'הפרש', bookSum: 'ספריו יחד' },
  totalUnits: { verses: 'פסוקים', words: 'תיבות', letters: 'אותיות' },
  countOf: (unit: string, text: string | null) => (text ? `${unit} (${text})` : unit),
  booksTitle: 'כל ספר, במניין',
  booksCols: { book: 'ספר', verses: 'פסוקים', wordsK: 'תיבות בכתיב', wordsQ: 'תיבות בקרי', lettersK: 'אותיות בכתיב', lettersQ: 'אותיות בקרי' },
}
