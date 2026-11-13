// Interface strings of a lemma's senses and uses across the canon (DESIGN.md §16.23): the Shifts
// page and the senses panel of the concordance. English first, Hebrew typed against it.

import { numEn } from '../fmt'
import { register } from '../en'

/** Corpus groups of `senses.groups` (configs/default.yaml); an unknown key is shown as is. */
const GROUPS_EN = {
  torah: 'Torah',
  former_prophets: 'Former Prophets',
  latter_prophets: 'Latter Prophets',
  poetry: 'Psalms, Proverbs, Job',
  scrolls: 'Scrolls',
  late: 'Late books',
}

export const senEn = {
  groups: GROUPS_EN as Record<string, string>,
  groupsTitle: 'Late books: Daniel, Ezra, Nehemiah, Chronicles. Scrolls: Song, Ruth, Lamentations, Ecclesiastes, Esther.',
  title: 'Shifts',
  lede: "Words whose senses or uses differ across the canon. Each frequent word is compared over six groups of books in two ways: its dictionary senses (the SDBH meaning tagged on each occurrence) and its uses in context (its BEREL vectors in their verses, clustered). The score is how much knowing the group tells about the sense (mutual information, minus what shuffled groups give); q corrects for testing hundreds of words.",
  caveat: 'Uses in context also carry genre and style: a shift there means "used differently", a shift in dictionary senses means "means something else".',
  by: 'Compare',
  bys: { sense: 'Dictionary senses', use: 'Uses in context' } as Record<'sense' | 'use', string>,
  check: (nmi: string, nul: string) => `Check: the contextual clusters match the dictionary senses with NMI ${nmi} on average (shuffled clusters: ${nul}).`,
  ranked: (n: number) => `${numEn(n)} words, the most shifted first`,
  word: 'Word',
  occurrences: 'Occurrences',
  shift: 'Shift',
  shiftTitle: 'Bits of mutual information between group and sense above the shuffled mean',
  q: 'q',
  senses: 'Senses',
  uses: 'Uses',
  empty: 'No words match.',
  // concordance panel
  panel: 'Senses across the canon',
  panelLede: 'Each row is one sense; the cells give its share of the word in each group of books.',
  notCompared: 'Too rare to compare across the canon (or a name).',
  dictionary: 'Dictionary senses (SDBH)',
  inContext: 'Uses in context (clusters of its BEREL vectors)',
  use: (i: number) => `Use ${i + 1}`,
  meaning: (i: number) => `Meaning ${i + 1}`,
  withWords: 'with',
  examples: 'Examples',
  stats: (sense: string, use: string) => `Shift of the senses: ${sense}; of the uses: ${use}.`,
  bits: (x: number, q: number) => `${x.toFixed(2)} bits (q ${q < 0.001 ? '< 0.001' : q.toFixed(3)})`,
  untested: 'not tested',
}

register('sen', senEn)
