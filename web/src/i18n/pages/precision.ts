// Interface strings of the detectors' precision by Claude's reading (DESIGN.md §16.86, D147),
// shown on each audited page and on Findings. English first, Hebrew typed against it.

import { countEn, numEn } from '../fmt'
import { register } from '../en'

const range = (lo: number | null, hi: number | null) => (lo === null || hi === null ? '' : ` [${lo.toFixed(2)}, ${hi.toFixed(2)}]`)

export const prcEn = {
  head: 'How often it is right, by Claude’s reading',
  /** The headline: the share right of what this page lists. */
  summary: (precision: number, lo: number | null, hi: number | null) =>
    `${Math.round(precision * 100)}% right${range(lo, hi)} of what this page lists, by Claude’s reading of a sample`,
  /** One population judged. `population` null: M152's run, whose list size was not kept. */
  rows: {
    shown: (judged: number, population: number | null) =>
      judged === population ? `All ${numEn(judged)} listed here` : `${numEn(judged)} drawn from the ${numEn(population ?? 0)} listed here`,
    marked: (judged: number, population: number | null) =>
      judged === population ? `All ${numEn(judged)} marked strong` : `${numEn(judged)} drawn from the ${numEn(population ?? 0)} marked strong`,
    strongest: (judged: number, population: number | null) =>
      population === null ? `${numEn(judged)} drawn from its strongest findings` : `${numEn(judged)} drawn from its ${numEn(population)} strongest`,
  } as Record<string, (judged: number, population: number | null) => string>,
  result: (right: number, wrong: number, unsure: number, precision: number | null, lo: number | null, hi: number | null) =>
    `${countEn(right, 'right', 'right')}, ${countEn(wrong, 'wrong', 'wrong')}${unsure ? `, ${numEn(unsure)} unsure` : ''}` +
    (precision === null ? '' : `: precision ${precision.toFixed(2)}${range(lo, hi)}`),
  ci: 'The range is a 95% confidence interval; an unsure answer counts neither way.',
  run: (model: string, date: string, places: string, known: string) =>
    `${model}, ${date}. Its calibration: the owner’s hand-checked places ${places} right, the known answers ${known}.`,
  caveat: 'A check by one model with the verses in view, not a gold standard.',
  tableTitle: 'How often the analyses are right',
  tableLede:
    'For each analysis below, Claude judged a sample of what its page lists by default, and of what the page marks as strong: the share judged right, with its 95% confidence interval. A check by one model with the verses in view, not a gold standard.',
  cols: { detector: 'Analysis', listed: 'Listed', shown: 'Right of what is listed', marked: 'Right of those marked strong' },
  share: (precision: number | null, lo: number | null, hi: number | null, judged: number) =>
    precision === null ? '–' : `${Math.round(precision * 100)}%${range(lo, hi)} (${numEn(judged)} judged)`,
  detectors: {
    etiologies: 'Naming etiologies',
    brackets: 'Resumptive repetition',
    retold: 'Retold speech',
    binomials: 'Word pairs',
    typescenes: 'Action sequences',
    acrostics: 'Acrostics',
    wordplay: 'Wordplay',
    allusions: 'Rare words over a few verses',
    refrains: 'Refrains',
    sayings: 'Graded numerical sayings',
    lists: 'Lists',
    mirrors: 'Chiasm within a verse',
    ciphers: 'Atbash and albam',
    seams: 'Style shifts',
    mainline: 'Main line',
    prophetic: 'Prophetic forms',
  } as Record<string, string>,
}

register('prc', prcEn)
