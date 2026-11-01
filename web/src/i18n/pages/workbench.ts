// Interface strings of the workbench: two sets of verses contrasted value by value, and a pattern
// checked on a set against its shuffled surroundings (DESIGN.md §16.64). English first, Hebrew
// typed against it. Sets and patterns are code, so they are not translated.

import type { SetErrorCode, WorkbenchFeature, WorkbenchWithin } from '../../api/types'
import { countEn, numEn } from '../fmt'

type SetItemKind = 'book' | 'chapters' | 'section' | 'collection' | 'pattern' | 'only'

export const q = (t: string) => (t ? ` “${t}”` : '')
export const qh = (t: string) => (t ? ` ”${t}“` : '')
export const dec = (x: number, locale: string) => x.toLocaleString(locale, { maximumFractionDigits: x < 10 ? 2 : 1 })

export const wbEn = {
  title: 'Workbench',
  lede: 'Ask the text your own question. Contrast two sets of verses to see which words, roots, domains and forms one uses more than the other, or check whether a pattern of your own is denser in a set than in the verses around it.',
  tabsLabel: 'What to do',
  tabs: { contrast: 'Contrast two sets', check: 'Check a pattern' },
  // sets
  setA: 'Set A',
  setB: 'Set B',
  set: 'The set',
  restHint: 'Leave set B empty to compare A with every other word of the Bible.',
  kindLabel: 'Add to the set',
  kinds: { book: 'A book', chapters: 'Chapters', section: 'A section', collection: 'A collection', pattern: 'A pattern', only: 'Words' } satisfies Record<SetItemKind, string>,
  book: 'Book',
  fromChapter: 'From chapter',
  toChapter: 'to chapter',
  sections: { torah: 'Torah', prophets: 'Prophets', writings: 'Writings' } as Record<string, string>,
  only: { speech: 'Only words in direct speech', narration: 'Only words of the narration' } as Record<string, string>,
  collection: 'Collection',
  noCollections: 'Your notebook has no collections yet: make one on the Notebook page.',
  collectionName: (name: string) => `Collection “${name}”`,
  collectionId: (id: string) => `Collection ${id}`,
  unit: (id: string) => `Unit ${id}`,
  chapters: (book: string, range: string) => `${book} ${range}`,
  books: (a: string, b: string) => `${a} to ${b}`,
  patternLabel: 'Pattern (verses where it matches)',
  patternPlaceholder: '[lemma=430] ..2 [lemma=3068]',
  add: 'Add',
  remove: (what: string) => `Remove ${what}`,
  empty: 'Nothing in this set yet.',
  emptyB: 'Every other word',
  asText: 'Edit as text',
  textLabel: (set: string) => `${set} as text`,
  apply: 'Apply',
  syntaxTitle: 'How a set is written',
  syntax: [
    'Items separated by ; join their verses: book:26; chapters:27:42-83.',
    'book:ID or book:ID-ID (canon order, Genesis is 0); chapters:BOOK:FROM-TO; section:torah, prophets or writings.',
    'unit:ID for any verse, chapter, pericope or parasha (v:0, c:0:1, p:Noach); collection:ID for a collection of your notebook.',
    'pattern:QUERY for the verses where a pattern search query matches.',
    'only:speech or only:narration keeps only those words of the verses (contrast only).',
  ],
  // contrast
  feature: 'Compare by',
  features: {
    lemma: 'Lemma',
    root: 'Root',
    domain: 'Semantic domain',
    pos: 'Part of speech',
    stem: 'Verb stem',
    form: 'Verb form',
    person: 'Person',
    function: 'Phrase function',
    clause: 'Clause type',
  } satisfies Record<WorkbenchFeature, string>,
  promptA: 'Build set A to begin: add a book, chapters, a collection of your notebook or a pattern.',
  setCount: (verses: number, words: number) => `${countEn(verses, 'verse', 'verses')}, ${countEn(words, 'word', 'words')}`,
  partWords: 'part of their words',
  summary: (tested: number, a: number, b: number) =>
    `${countEn(tested, 'value', 'values')} scored; ${numEn(a)} commoner in A and ${numEn(b)} commoner in B at q ≤ 0.05.`,
  overlap: (n: number) => `${countEn(n, 'word is', 'words are')} in both sets and counted for A only.`,
  overA: 'Commoner in A',
  overB: 'Commoner in B',
  cols: { value: 'Value', a: 'A', b: 'B', ratio: 'Ratio', g2: 'G²', q: 'q', verses: 'Verses' },
  perThousand: (rate: number) => `${dec(rate, 'en-US')} per 1,000`,
  ratio: (log2: number) => (log2 >= 0 ? `×${dec(2 ** log2, 'en-US')}` : `÷${dec(2 ** -log2, 'en-US')}`),
  ratioTitle: 'How many times commoner on its side, per word that has the feature',
  none: 'Nothing scored on this side.',
  find: 'Search',
  findTitle: 'Open this value in pattern search',
  method:
    'Each value is counted in A and in B among the words that have the feature (verbs only for stem, form and person) and scored by G² over the 2 × 2 table, with p from χ² and q corrected for every value scored (Benjamini–Hochberg). Values with fewer than 5 words over both sets are left out. A high G² with a small count is a lead to read, not a finding.',
  export: 'Export (CSV)',
  // check
  query: 'Pattern',
  queryLabel: 'Pattern search query',
  run: 'Check',
  within: 'Draw again within',
  withins: { book: 'each book', chapter: 'each chapter', corpus: 'the whole Bible' } satisfies Record<WorkbenchWithin, string>,
  checkPrompt: 'Write a pattern and build a set, then check.',
  found: (matches: number, verses: number, words: number, rate: number) =>
    `${countEn(matches, 'match', 'matches')} in the set's ${countEn(verses, 'verse', 'verses')} (${countEn(words, 'word', 'words')}): ${dec(rate, 'en-US')} per 1,000 words.`,
  null: (within: WorkbenchWithin, draws: number, mean: number, low: number, high: number) =>
    `The set's verses drawn again at random within ${wbEn.withins[within]}, ${numEn(draws)} times: ${dec(mean, 'en-US')} per 1,000 on average, 95 % of the draws between ${dec(low, 'en-US')} and ${dec(high, 'en-US')}.`,
  denser: (p: string) => `Denser than chance: p = ${p}.`,
  sparser: (p: string) => `Sparser than chance: p = ${p}.`,
  chance: (high: string, low: string) => `Within chance: p = ${high} for denser, ${low} for sparser.`,
  rest: (rate: number, matches: number, words: number) =>
    `The other verses around it: ${dec(rate, 'en-US')} per 1,000 (${countEn(matches, 'match', 'matches')} in ${countEn(words, 'word', 'words')}).`,
  fixed: (n: number) => `${countEn(n, 'verse of the set fills', 'verses of the set fill')} a whole group and ${n === 1 ? 'stays' : 'stay'} in place in every draw.`,
  untestable: 'Every verse of the set fills its whole group, so there is nothing to draw it against. Draw within a wider group.',
  byBook: 'By book',
  bookCols: { book: 'Book', matches: 'Matches', words: 'Words', rate: 'Per 1,000' },
  checkMethod:
    'One-sided p with the +1 correction over the draws; both directions are shown, so read the one you asked about before you looked. A pattern chosen after seeing where it is common will look dense there: check it on a set you did not look at.',
  setErrors: {
    empty: () => 'Add something to the set first.',
    too_long: () => 'The set is too long.',
    bad_item: (t: string) => `An item is kind:value:${q(t)}.`,
    unknown_kind: (t: string) => `There is no kind${q(t)}; see “How a set is written”.`,
    unknown_book: (t: string) => `No book${q(t)}.`,
    bad_range: (t: string) => `This number or range does not read:${q(t)}.`,
    unknown_unit: (t: string) => `No unit${q(t)} in this build.`,
    unknown_collection: (t: string) => `No collection${q(t)} in your notebook.`,
    pattern: (t: string) => `The pattern${q(t)} cannot run.`,
    no_words: () => 'The set has no words.',
    filter_in_check: (t: string) => `A check counts whole verses, so it takes no filter:${q(t)}.`,
  } satisfies Record<SetErrorCode, (token: string) => string>,
  inSet: (set: string) => `${set}: `,
}
