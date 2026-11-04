// Interface strings of the Citations page: verses that say they quote or fulfil another
// (DESIGN.md §16.31). English first, Hebrew typed against it.

import type { CitationFamily } from '../../api/types'
import { countEn, numEn, pct } from '../fmt'
import { register } from '../en'

export const fp = (p: number | null) => (p == null ? '–' : p < 0.001 ? '< 0.001' : p < 0.01 ? p.toFixed(3) : p.toFixed(2))

export const citEn = {
  title: 'Citations',
  lede: 'Some verses say that they repeat or fulfil another text: "as it is written in the book of the law of Moses", "according to the word of the LORD which he spoke by his servant", "as the LORD commanded Moses". For each one the source is sought among the texts it may point to (the Torah, or anything earlier) by its words and its meaning. A source is resolved when the two searches agree on it.',
  noData: 'Not computed in this build: run `bsim citations`, then `bsim build-db`.',
  summary: (n: number, resolved: number) =>
    `${countEn(n, 'verse with a formula of reference', 'verses with a formula of reference')}; ${numEn(resolved)} resolved to one source.`,
  families: {
    written: { label: 'As it is written', hint: 'ככתוב, ככל הכתוב, כתוב בספר: sought in the Torah' },
    word: { label: 'The word fulfilled', hint: 'דבר יהוה אשר דבר (ביד …): sought in anything earlier' },
    command: { label: 'As commanded', hint: 'כאשר צוה יהוה את משה: sought in the Torah' },
  } satisfies Record<CitationFamily, { label: string; hint: string }>,
  familyLine: (label: string, k: number, n: number, share: number, nul: number, p: number | null) =>
    `${label}: ${numEn(k)} of ${numEn(n)} resolved (${pct(share)}), against ${pct(nul)} of random verses of the same books (p ${fp(p)}).`,
  familyNote:
    'A best match alone proves little: almost any verse finds a close one among ten thousand, because the corpus repeats its formulas. So each family is measured against random verses held to the same rules. Where a family does no better than they do, its formula mostly points to a law or a promise in general, not to one verse.',
  gold: (top1: number, found: number, topK: number, k: number, right: number, resolved: number) =>
    `Check: of ${countEn(found, 'citation', 'citations')} whose source scholarship names, ${numEn(top1)} find it first and ${numEn(topK)} within the best ${numEn(k)}; ${numEn(right)} of the ${numEn(resolved)} resolved ones are right.`,
  lag: (verses: number) => `A fulfilled word comes a median ${countEn(verses, 'verse', 'verses')} after its source.`,
  booksTitle: 'Who cites whom',
  booksLede: 'Resolved citations by book: the one direction between passages the text itself states.',
  bookPair: (a: string, b: string, n: number) => `${a} → ${b}: ${numEn(n)}`,
  listTitle: 'Every citation',
  filters: { family: 'Formula', any: 'Any', resolved: 'Resolved only', book: 'Book' },
  page: (total: number, page: number, pages: number) =>
    `${countEn(total, 'citation', 'citations')} · page ${numEn(page)} of ${numEn(pages)}`,
  none: 'None here.',
  resolvedTag: 'resolved',
  unresolvedTag: 'no single source',
  namedTag: (rank: number | null) => (rank == null ? 'named source missed' : rank === 1 ? 'named source found' : `named source at ${rank}`),
  source: 'Source',
  others: 'Other candidates:',
  compare: 'Compare',
}

register('cit', citEn)
