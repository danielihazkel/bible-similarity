// Interface strings of the Late Biblical Hebrew profile (DESIGN.md §16.24): the Language page and
// the line on chapter pages. English first, Hebrew typed against it.

import { numEn } from '../fmt'
import { register } from '../en'

/** What each feature measures, phrased the way it pushes a chapter towards "late". */
const FEATURES_EN = {
  lbh_lexemes: 'late words (מלכות, מדינה, אגרת, דת, התיחש…)',
  anokhi: 'אני rather than אנכי',
  inf_abs: 'few infinitive absolutes',
  et_suffix: 'object suffix on the verb rather than את (ויקחהו, not ויקח אתו)',
  directional_he: 'few directional ה (מצרימה)',
  cohortative_wayyiqtol: 'ואשלחה-type first-person forms',
  david_plene: 'David spelled דויד',
  yah_short: 'names ending ‑יה rather than ‑יהו (ירמיה, not ירמיהו)',
}

export const datEn = {
  features: FEATURES_EN as Record<string, string>,
  title: 'Language',
  lede: "How much each chapter's Hebrew resembles the late books (Chronicles, Ezra–Nehemiah, Esther, Daniel) rather than Genesis–Kings, from features the linguistic-dating literature lists: late words, the decline of אנכי, of the infinitive absolute, of את with a suffix and of the directional ה, ואשלחה-type forms, and the spelling דויד. A model learns them from the undisputed books and scores every chapter (0 = like Genesis–Kings, 1 = like the late books).",
  caveat: 'A profile, not a date: whether such features can date a text is debated (Young, Rezetko and Ehrensvärd against Hurvitz). Poetry drops את and the directional ה whatever its date, so poetic chapters are marked out of domain; a late-looking chapter can be an archaizing or a late scribe\'s copy.',
  check: (auc: string, aucG: string) =>
    `Check: a book the model never saw is told apart chapter by chapter with AUC ${auc} (${aucG} without the late words).`,
  synoptic: (later: number, pairs: number, p: string, laterG: number) =>
    `The hardest test: trained without Samuel, Kings and Chronicles, the model scores both sides of their ${numEn(pairs)} parallel passages — the same content in two states of the language. Chronicles comes out later in ${numEn(later)} (sign test p = ${p}; ${numEn(laterG)} without the late words).`,
  examplesTitle: 'Largest gaps between a passage and its Chronicles parallel',
  byBook: 'Books',
  byBookLede: 'Mean chapter score with the 10th–90th percentile range of its chapters.',
  roles: { early: 'trained as early', late: 'trained as late' } as Record<'early' | 'late', string>,
  outOfDomain: 'poetry: out of domain',
  chapters: (book: string) => `Chapters of ${book}`,
  chapter: 'Chapter',
  words: 'Hebrew words',
  score: 'Profile',
  drivers: 'Pushed up by',
  tooShort: 'too short',
  heldOut: 'scored by a model that did not see this book',
  noData: 'No language profile in this build (run `bsim dating`).',
  unitLine: (score: string) => `Language profile: ${score} on a scale from Genesis–Kings (0) to the late books (1)`,
  unitDrivers: 'pushed up by',
  unitPoetry: ' (poetry: out of the model\'s domain)',
}

register('dat', datEn)
