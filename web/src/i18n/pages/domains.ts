// Interface strings of the semantic-domain views (DESIGN.md §16.22): the Domains page, a unit's
// themes, domain chips. English first, Hebrew typed against it (see ../en.ts).
// Domain names are SDBH data (English); the two top levels are also named here, so the Hebrew
// interface can show them in Hebrew (D56). Deeper domains keep their English name in both.

import { countEn, countHe, numEn, numHe } from '../fmt'

/** The two top levels of the SDBH lexical domains. */
const TOP_EN = {
  '001': 'Objects',
  '001001': 'Beings',
  '001002': 'Natural World',
  '001003': 'Human-Made World',
  '002': 'Events',
  '002001': 'Description',
  '002002': 'Position',
  '002003': 'Connection',
  '002004': 'Perception',
  '003': 'Referents',
  '003001': 'Object Referents',
  '003002': 'Event Referents',
  '004': 'Markers',
  '004001': 'Affirmers',
  '004002': 'Contrastors',
  '004003': 'Identifiers',
  '004004': 'Extenders',
  '004005': 'Evaluators',
  '004006': 'Negators',
  '004007': 'Restrictors',
  '004008': 'Stipulators',
  '004009': 'Timers',
}

export const domEn = {
  top: TOP_EN as Record<string, string>,
  title: 'Semantic domains',
  lede: 'Every word of the text in its sense there, sorted into the semantic domains of the UBS Dictionary of Biblical Hebrew (SDBH): objects (beings, the natural and the human-made world), events (description, position, connection, perception), referents and markers, each divided further. Choose a domain to see where the Tanakh speaks of it, whatever the words.',
  source: 'Senses and domains: UBS Dictionary of Biblical Hebrew (SDBH), CC BY-SA 4.0. No glosses or translations are shown.',
  verses: (n: number) => countEn(n, 'verse', 'verses'),
  versesIn: (book: string) => `Verses in ${book}`,
  allVerses: 'Verses',
  byBook: 'By book',
  subdomains: 'Subdomains',
  broader: 'Broader domains',
  occurrences: (words: number, verses: number, books: number) =>
    `${numEn(Math.round(words))} words in ${numEn(verses)} verses of ${countEn(books, 'book', 'books')}.`,
  empty: 'No verses.',
  open: (label: string) => `Verses in the domain ${label}`,
  // a unit's themes
  themes: 'Themes',
  themesLede: 'Semantic domains this passage uses far more than the Tanakh as a whole (log-likelihood), from the sense of each word in context.',
  themeTitle: (weight: string, expected: string, lift: string) => `${weight} words here, ${expected} expected (${lift}×)`,
  noThemes: 'No domain stands out here.',
  noLexicon: 'No word senses in this build (run `bsim lexicon`).',
  broad: 'By broad domain',
  // the word panel
  wordDomains: 'Domains',
  wordDomainTitle: 'Every verse with a word in this domain',
}

export const domHe: typeof domEn = {
  top: {
    '001': 'עצמים',
    '001001': 'יצורים',
    '001002': 'עולם הטבע',
    '001003': 'מעשי ידי אדם',
    '002': 'אירועים',
    '002001': 'תיאור',
    '002002': 'מקום ותנועה',
    '002003': 'קשר',
    '002004': 'תפיסה',
    '003': 'כינויים',
    '003001': 'כינויים לעצמים',
    '003002': 'כינויים לאירועים',
    '004': 'סמנים',
    '004001': 'מאשרים',
    '004002': 'מנגידים',
    '004003': 'מזהים',
    '004004': 'מרחיבים',
    '004005': 'מעריכים',
    '004006': 'שוללים',
    '004007': 'מגבילים',
    '004008': 'מתנים',
    '004009': 'סמני זמן',
  },
  title: 'תחומי משמעות',
  lede: 'כל מילה בטקסט במובנה במקומה, ממוינת לתחומי המשמעות של המילון הסמנטי לעברית מקראית של חבר אגודות התנ״ך (SDBH): עצמים (יצורים, עולם הטבע ומעשי ידי אדם), אירועים (תיאור, מקום ותנועה, קשר, תפיסה), כינויים וסמנים, וכל אחד מתחלק הלאה. בחרו תחום כדי לראות היכן התנ״ך עוסק בו, בכל מילים.',
  source: 'מובנים ותחומים: UBS Dictionary of Biblical Hebrew ‏(SDBH), ‏CC BY-SA 4.0. אין כאן פירושי מילים או תרגומים.',
  verses: (n: number) => countHe(n, 'פסוק אחד', 'שני פסוקים', 'פסוקים'),
  versesIn: (book: string) => `פסוקים ב${book}`,
  allVerses: 'פסוקים',
  byBook: 'לפי ספר',
  subdomains: 'תת־תחומים',
  broader: 'תחומים רחבים יותר',
  occurrences: (words: number, verses: number, books: number) =>
    `${numHe(Math.round(words))} מילים ב־${numHe(verses)} פסוקים ב${countHe(books, 'ספר אחד', 'שני ספרים', 'ספרים')}.`,
  empty: 'אין פסוקים.',
  open: (label: string) => `פסוקים בתחום ${label}`,
  themes: 'נושאים',
  themesLede: 'תחומי משמעות שהקטע משתמש בהם הרבה יותר מהתנ״ך כולו (יחס נראות), לפי מובן כל מילה בהקשרה.',
  themeTitle: (weight: string, expected: string, lift: string) => `${weight} מילים כאן, ${expected} צפויות (פי ${lift})`,
  noThemes: 'אין תחום הבולט כאן.',
  noLexicon: 'אין מובני מילים בבנייה זו (הריצו `bsim lexicon`).',
  broad: 'לפי תחום רחב',
  wordDomains: 'תחומים',
  wordDomainTitle: 'כל הפסוקים שיש בהם מילה בתחום זה',
}
