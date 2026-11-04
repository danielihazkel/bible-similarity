// Interface strings of Patterns → Numbers and lists: graded numerical sayings, lists of verses
// shaped alike and the checks fixed in advance (DESIGN.md §16.45). English first, Hebrew typed
// against it.

import type { FormsKind } from '../../api/types'
import { countEn, numEn } from '../fmt'
import { register } from '../en'

export const fp = (p: number | null | undefined) => (p == null ? '–' : p < 0.001 ? '< 0.001' : p < 0.01 ? p.toFixed(3) : p.toFixed(2))
export const pct = (x: number | null | undefined) => (x == null ? '–' : `${Math.round(x * 100)}%`)
export const x1 = (x: number | null | undefined) => (x == null ? '–' : x.toFixed(1))
export const x2 = (x: number | null | undefined) => (x == null ? '–' : x.toFixed(2))

export const fmEn = {
  title: 'Numbers and lists',
  lede: 'Two small forms. The graded numerical saying names a number and then the next: על שלשה פשעי דמשק ועל ארבעה (Amos 1:3), שש הנה שנא יהוה ושבע (Prov 6:16). A list repeats one verse shape: the genealogy of Genesis 5, the stations of Numbers 33, the kings Joshua struck.',
  noData: 'Not computed in this build: run `bsim forms`, then `bsim build-db`.',
  view: 'Show',
  sayingsView: 'Numerical sayings',
  listsView: 'Lists',
  verdict: { holds: 'holds', fails: 'does not hold' },
  checksTitle: 'Checks fixed in advance',
  // sayings
  summary: (numbers: number, free: number, sayings: number, pairs: number, window: number) =>
    `${numEn(numbers)} number words; ${numEn(free)} stand alone (the rest are parts of compound numbers such as שלשים ושנים). ${countEn(sayings, 'verse holds', 'verses hold')} a number and the next within ${numEn(window)} words (${countEn(pairs, 'graded pair', 'graded pairs')}).`,
  known: (found: number, n: number) =>
    `The sayings scholars name (Roth 1962; Haran 1972) are found: ${numEn(found)} of ${numEn(n)}. A known answer.`,
  chance: (obs: number, exp: number, p: number | null, shuffles: number) =>
    `Graded pairs are more common than the book's own numbers placed at random give: ${numEn(obs)} against ${x1(exp)} (the values of the free number words shuffled within each book, ${numEn(shuffles)} times; p ${fp(p)}). Most pairs are not sayings: שני אדנים תחת הקרש האחד and the like, in the measurements of the Tabernacle and the Temple, are as common as chance makes them and drown the sayings.`,
  without: (steps: string, obs: number, exp: number, p: number | null) =>
    `Described, added after the first run: without ${steps}, ${numEn(obs)} graded pairs against ${x1(exp)} (p ${fp(p)}).`,
  parallel: (sp: number, op: number, sProb: number, oProb: number, p: number | null, sayings: number, others: number) =>
    `A verse with a graded pair is a parallel line (§16.9) more often than a verse with another pair of numbers: ${pct(sp)} of ${numEn(sayings)} against ${pct(op)} of ${numEn(others)} (mean probability ${x2(sProb)} against ${x2(oProb)}; the labels shuffled, p ${fp(p)}). Roth called the pattern a device of parallelism.`,
  stepsTitle: 'Steps',
  step: (step: string, n: number) => `${step}: ${numEn(n)}`,
  knownTitle: 'Sayings named in advance',
  knownCols: { name: 'Saying', where: 'Where', found: 'Found' },
  hits: (hits: number, n: number) => (n === 1 ? (hits ? 'found' : 'not found') : `${numEn(hits)} of ${numEn(n)} verses`),
  sayingsTitle: 'The sayings',
  knownOnly: 'Named in advance only',
  sayingCount: (n: number) => countEn(n, 'verse', 'verses'),
  parallelTag: (prob: number) => `parallel halves ${x2(prob)}`,
  named: 'named in advance: ',
  emptySayings: 'No saying matches these filters.',
  // lists
  listsSummary: (observed: number, expected: number, shuffles: number, verses: number, minVerses: number) =>
    `${countEn(observed, 'list', 'lists')} of at least ${numEn(minVerses)} verses, ${numEn(verses)} verses in all, against ${x1(expected)} with the verses of each book shuffled (${numEn(shuffles)} shuffles). A verse is list-like when its word shapes (the grammar of each word, not its lemma) match a verse up to three before or after it better than 99% of matches in shuffled order.`,
  listsCheck: (found: number, n: number, observed: number, expected: number) =>
    `The lists named in advance are found, among more lists than chance gives: ${numEn(found)} of ${numEn(n)}; ${numEn(observed)} lists against ${x1(expected)}.`,
  knownListsTitle: 'Lists named in advance',
  knownListsCols: { name: 'List', span: 'Verses', covered: 'In a list found' },
  covered: (c: number, n: number) => `${numEn(c)} of ${numEn(n)}`,
  kindsTitle: 'Kinds',
  kindsLede: 'Described, not tested: a list is a genealogy, an itinerary, a census, offerings or kings when the word (ילד; נסע or חנה; פקד; קרבן; מלך) is in half its verses, a list of names when names are a third of its words.',
  kind: {
    genealogy: 'genealogy',
    itinerary: 'itinerary',
    census: 'census',
    offering: 'offerings',
    kings: 'kings',
    names: 'names',
    other: 'other',
  } satisfies Record<FormsKind, string>,
  kindFilter: 'Kind',
  allKinds: 'All kinds',
  listsTitle: 'The lists',
  listCount: (n: number) => countEn(n, 'list', 'lists'),
  span: (first: string, last: string) => `${first} – ${last}`,
  verses: (n: number, like: number) => `${countEn(n, 'verse', 'verses')}, ${numEn(like)} list-like`,
  likeness: (x: number) => `likeness ${x2(x)}`,
  more: (n: number) => `+ ${countEn(n, 'more verse', 'more verses')}`,
  read: 'Read the chapter',
  emptyLists: 'No list matches these filters.',
}

register('fm', fmEn)
