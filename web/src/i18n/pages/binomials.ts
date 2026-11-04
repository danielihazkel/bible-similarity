// Interface strings of the word-pairs page (DESIGN.md §16.72): fixed pairs of words (שמים וארץ),
// their order, their words' lengths and the late books' turns. English first, Hebrew typed
// against it. The pairs are quoted in Hebrew, isolated in the English sentences.

import { numEn } from '../fmt'
import { register } from '../en'

// three places below 0.1, so that a p just above 0.05 does not print as 0.05
export const fp = (p: number) => (p < 0.001 ? '< 0.001' : p < 0.1 ? p.toFixed(3) : p.toFixed(2))
export const pct = (x: number | null) => (x === null ? '–' : `${Math.round(x * 100)}%`)

export type BnShow = 'all' | 'both'
export type BnOrder = 'common' | 'turned'

export const bnEn = {
  title: 'Word pairs',
  lede: 'Hebrew pairs some words in a set order: ⁨שמים וארץ⁩, ⁨איש ואשה⁩, ⁨כסף וזהב⁩. Some orders are frozen, some turn round. Here are the pairs of nouns, names or adjectives joined by ⁨ו⁩ that recur, with how fixed each order is, the length of each word, and where the order turns.',
  notComputed: 'The word pairs were not computed in this build (run bsim binomials).',
  checksTitle: 'Checks fixed in advance',
  holds: 'Borne out',
  fails: 'Not borne out',
  short: {
    title: 'The shorter word comes first',
    text: (lk: number, lm: number, lp: number, sk: number, sm: number, sp: number) =>
      `Of the pairs whose words differ in length, the shorter word stands first in ${numEn(lk)} of ${numEn(lm)} counted in letters (p ${fp(lp)}) and ${numEn(sk)} of ${numEn(sm)} counted in syllables (p ${fp(sp)}). Both were to hold.`,
  },
  late: {
    title: 'The late books turn the pairs',
    text: (early: number | null, late: number | null, p: number, without: number) =>
      `A pair stands in its rarer order ${pct(early)} of the time in the early books (Genesis to Kings) and ${pct(late)} in the late (Chronicles, Ezra, Nehemiah, Esther, Daniel), with the periods shuffled within each pair (p ${fp(p)}). Without ⁨כסף וזהב⁩: p ${fp(without)}.`,
  },
  known: {
    title: 'Heaven and earth, man and woman, gold and silver',
    text: (sky: number | null, man: number | null, early: number | null, late: number | null) =>
      `⁨שמים וארץ⁩ in that order ${pct(sky)} of the time, ⁨איש ואשה⁩ ${pct(man)}; ⁨זהב וכסף⁩ rather than ⁨כסף וזהב⁩ ${pct(early)} of the time in the early books, ${pct(late)} in the late.`,
  },
  listTitle: (n: number, min: number) => `The ${numEn(n)} pairs found at least ${numEn(min)} times`,
  show: { label: 'Show', all: 'All', both: 'Found both ways' },
  order: { label: 'Order', common: 'Commonest', turned: 'Most turned' },
  kind: { noun: 'nouns', name: 'names', adjective: 'adjectives' } as Record<string, string>,
  cols: {
    pair: 'Pair, in its own order',
    kind: 'Kind',
    n: 'Found',
    fixed: 'In this order',
    letters: 'Letters',
    syll: 'Syllables',
    early: 'Turned, early books',
    late: 'Turned, late books',
  },
  of: (k: number, n: number) => (n ? `${numEn(k)} / ${numEn(n)}` : '–'),
  showPair: (pair: string) => `Where ${pair} is found`,
  pairTitle: (pair: string) => `${pair}: where it is found`,
  ownOrder: 'In its own order',
  rarerOrder: 'Turned round',
  listed: (n: number) => `(up to ${numEn(n)} of each listed)`,
  close: 'Close',
  empty: 'No pair here.',
  limits: 'A pair is two words side by side: ⁨את השמים ואת הארץ⁩, with ⁨את⁩ between, is not counted.',
}

register('bn', bnEn)
