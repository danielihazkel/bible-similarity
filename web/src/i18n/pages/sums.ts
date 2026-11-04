// Interface strings of the sums page (DESIGN.md §16.75): lists against their stated totals, and
// the numbers of parallel passages. English first, Hebrew typed against it.

import { numEn } from '../fmt'
import { register } from '../en'

export const fp = (p: number) => (p < 0.001 ? '< 0.001' : p < 0.1 ? p.toFixed(3) : p.toFixed(2))
export const pct = (x: number | null) => (x === null ? '–' : `${Math.round(x * 100)}%`)

export type SmScope = 'across' | 'every'
export type SmStep = 'all' | 'yes' | 'no'

export const smEn = {
  title: 'Do the sums add up?',
  lede: 'The text counts and adds. Numbers 1 gives each tribe’s men and then all of them; Ezra 2 lists the families who came back and then the whole assembly, a total the families do not reach. Here each list is added up against the total the text states, and the numbers of parallel passages are set side by side.',
  notComputed: 'The sums were not computed in this build (run bsim sums).',
  checksTitle: 'Checks fixed in advance',
  holds: 'Borne out',
  fails: 'Not borne out',
  lists: {
    title: 'Each list adds up, or does not, as known',
    text: (adding: number, n: number) =>
      `${numEn(adding)} of the ${numEn(n)} lists add up to the total the text states. The censuses were to add up; the Levites of Numbers 3, the temple vessels of Ezra 1 and the returnees of Ezra 2 and Nehemiah 7 were not. A check of the reading of the numbers.`,
  },
  step: {
    title: 'Parallels differ by one step',
    text: (k: number, n: number, share: number | null, expected: number | null, p: number) =>
      `Of the ${numEn(n)} numbers that differ between parallel verses in different books, ${numEn(k)} (${pct(share)}) are one step apart: a power of ten (40,000 / 4,000) or one decimal place (18 / 8), as a copyist might change them. With the second number drawn from its book at random, ${pct(expected)} would be (p ${fp(p)}).`,
    every: (share: number | null, expected: number | null, p: number) =>
      `The first run counted pairs inside one book too (mostly repeated formulae): ${pct(share)} against ${pct(expected)} (p ${fp(p)}).`,
  },
  known: {
    title: 'David’s census, Solomon’s stalls, Jehoiachin’s age',
    found: (a: number, b: number) => `${numEn(a)} / ${numEn(b)}`,
    oneStep: 'one step',
    notOneStep: 'not one step',
    missing: 'not found',
  },
  listsTitle: 'The lists',
  name: {
    gen46: 'Jacob’s house going down to Egypt',
    num1: 'The census at Sinai',
    num2_east: 'The camp on the east',
    num2_south: 'The camp on the south',
    num2_west: 'The camp on the west',
    num2_north: 'The camp on the north',
    num2: 'The four camps',
    num3: 'The Levites counted',
    num4: 'The Levites at work',
    num26: 'The census in Moab',
    ezra1: 'The temple vessels',
    ezra2: 'The returnees (Ezra)',
    neh7: 'The returnees (Nehemiah)',
  } as Record<string, string>,
  cols: {
    list: 'List',
    items: 'Counts',
    sum: 'Added up',
    total: 'Stated total',
    diff: 'Difference',
    adds: 'Adds up',
    known: 'As known',
  },
  yes: 'yes',
  no: 'no',
  showItems: (name: string) => `The counts of ${name}`,
  itemsTitle: (name: string) => `${name}: each count`,
  totalVerse: 'The total',
  close: 'Close',
  parallelsTitle: 'Numbers of parallel verses',
  parallelsLede: 'Each verse’s numbers, aligned in order by unit (a count, years, months, days) with the numbers of its parallel. Pairs come from the parallel sequences, ETCBC’s parallel passages and Sefaria’s links.',
  scope: { label: 'Pairs', across: 'Different books', every: 'Every pair' },
  step3: { label: 'Differ', all: 'All', yes: 'One step apart', no: 'Further apart' },
  unit: { count: 'count', year: 'years', month: 'months', day: 'days' } as Record<string, string>,
  pairCount: (n: number) => `${numEn(n)} differing numbers`,
  pageOf: (p: number, n: number) => `page ${numEn(p)} of ${numEn(n)}`,
  empty: 'No numbers here.',
  limits: 'Numbers are read from the words (cardinals; ordinals are not counts). Numbers are paired in order by unit only, so a pair can set side by side two numbers that do not stand for the same thing.',
}

register('sm', smEn)
