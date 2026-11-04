// Interface strings of Patterns → Equal values, related words? (DESIGN.md §16.59). English first,
// Hebrew typed against it.

import type { GematriaPairSort, LinkMeasure, LinkProperty } from '../../api/types'
import { countEn, countHe, numEn, pct } from '../fmt'
import { register } from '../en'

export const moreVersesHe = (n: number) => countHe(n, 'פסוק אחד נוסף', 'שני פסוקים נוספים', 'פסוקים נוספים')

export const glEn = {
  title: 'Equal values, related words?',
  lede: 'Gematria pairs words of equal letter value (נחש and משיח are both 358, יין and סוד both 70) and reads the pairing as a link in meaning. Are words of equal value any closer in meaning than words that merely look alike: of the same length and about as common? And are the numbers claimed for Genesis 1:1 rarer than any verse’s own?',
  noData: 'Not computed in this build: run `bsim gematria-links`, then `bsim build-db`.',
  verdict: { holds: 'holds', fails: 'does not hold' },
  summary: (lemmas: number, pairs: number, same: number, draws: number) =>
    `${numEn(lemmas)} words (lemmas named at least three times, names left out) make ${numEn(pairs)} pairs of equal standard value; ${numEn(same)} of them are spelled with the same letters and left out. Each remaining pair is set against ${numEn(draws)} sets of matched pairs: one word kept, the other replaced by a word of the same letter count and frequency whose value differs.`,
  testTitle: 'Do equal values link related words?',
  checkTitle: 'Do the measures see relatedness? (a check)',
  checkLede: 'Pairs of one root family, matched the same way: the measures should find them closer, and they do.',
  measures: {
    domains: 'Same semantic domains',
    root: 'Same root family',
    vector: 'Used alike (BEREL)',
  } satisfies Record<LinkMeasure, string>,
  measureHints: {
    domains: 'The cosine of the two words’ SDBH domain profiles (0: no domain shared, 1: the same)',
    root: 'The share of pairs whose words are of one root family',
    vector: 'The cosine of the two words’ BEREL vectors, each the mean of its uses in context',
  } satisfies Record<LinkMeasure, string>,
  cols: { measure: 'Measure', pairs: 'These pairs', matched: 'Matched pairs', range: '90% of draws', p: 'p' },
  testVerdict: (alpha: number) =>
    `The claim holds when the pairs are more related than the matched pairs on any measure at p ≤ ${(alpha / 3).toFixed(3)} (${alpha} shared by three).`,
  // the traditional equivalences
  eqTitle: 'The tradition’s equivalences',
  eqLede: 'Each pair, and where it stands among all the pairs of equal value: “closer than 74%” means its words are used more alike than in 74% of them.',
  eqCols: { pair: 'Pair', value: 'Value', domains: 'Domains', root: 'Root', vector: 'Used alike' },
  same: 'same',
  differ: 'different',
  rank: (r: number) => `closer than ${pct(r)}`,
  notFound: 'not among the words tested',
  // Genesis 1:1
  verseTitle: (ref: string) => `The numbers of ${ref}`,
  props: (p: LinkProperty) =>
    ({
      words: `${p.n} words`,
      letters: `${p.n} letters`,
      multiple: `a value divisible by ${p.n}`,
      triangular: 'a triangular value (1 + 2 + 3 + …)',
      prime_factors: `a value of ${p.n} prime factors`,
    })[p.kind],
  propCols: { prop: 'Property', here: 'Here', verses: 'Verses with it' },
  allLine: (ref: string, all: number, expected: number) =>
    `${all === 1 ? `Only ${ref} has` : `${numEn(all)} verses have`} all of them; ${expected.toFixed(3)} would, were they independent. But they were chosen by looking at it.`,
  ownLine: (ref: string, words: number, letters: number, prime: number, twins: number, share: number) =>
    `A fairer question: is ${ref} singular by its own numbers? Described by them (${numEn(words)} words, ${numEn(letters)} letters, a value whose largest prime factor is ${numEn(prime)}), ${twins ? `it shares its description with ${countEn(twins, 'other verse', 'other verses')}` : 'it is the only verse with its description'}, while ${pct(share)} of all verses are the only one with their own.`,
  twins: 'Its twins',
  // the pairs
  pairsTitle: 'The pairs',
  sort: 'Order',
  sorts: { vector: 'Used most alike', domains: 'Most domains shared', value: 'By value' } satisfies Record<GematriaPairSort, string>,
  sameLetters: 'With pairs spelled alike',
  valueFilter: 'Value',
  allValues: 'Any value',
  pairsSummary: (n: number) => countEn(n, 'pair', 'pairs'),
  pageOf: (page: number, pages: number) => `page ${numEn(page)} of ${numEn(pages)}`,
  emptyPairs: 'No pairs.',
  pairLine: (vector: number, domains: number) => `used alike ${vector.toFixed(2)} · domains ${pct(domains)}`,
  oneRoot: 'one root',
  spelledAlike: 'spelled alike',
  valueTitle: (v: number) => `Everything worth ${numEn(v)}`,
}

register('gl', glEn)
