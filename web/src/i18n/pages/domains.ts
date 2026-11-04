// Interface strings of the semantic-domain views (DESIGN.md §16.22): the Domains page, a unit's
// themes, domain chips. English first, Hebrew typed against it (see ../en.ts).
// Domain names are SDBH data (English); the two top levels are also named here, so the Hebrew
// interface can show them in Hebrew (D56). Deeper domains keep their English name in both.

import { countEn, numEn } from '../fmt'
import { register } from '../en'

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

register('dom', domEn)
