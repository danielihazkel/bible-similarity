// Interface strings of the Network page's Directions view: a direction on the cross-book echoes
// (DESIGN.md §16.36). English first, Hebrew typed against it.

import type { EchoBasis } from '../../api/types'
import { countEn, numEn } from '../fmt'
import { register } from '../en'

export const fp = (p: number) => (p < 0.001 ? '< 0.001' : p < 0.01 ? p.toFixed(3) : p.toFixed(2))
export const gapEn = (g: number) => (g > 0 ? '+' : '−') + Math.abs(g).toFixed(2)

export const echoEn = {
  viewLabel: 'View',
  views: { communities: 'Communities', directions: 'Directions' },
  title: 'Who echoes whom',
  lede: 'The network links chapters that resemble each other; it does not say which drew on which. Three analyses can give a pair of chapters from two books a direction, from the strongest evidence to the weakest: a citation that names its source, a parallel passage whose borrower the language and spelling point to, and, for the rest, the Late Biblical Hebrew profile — the later-looking chapter is taken to echo the earlier-looking one. A pair takes the first of these that decides it.',
  noData: 'Not computed in this build: run `bsim echoes`, then `bsim build-db`.',
  summary: (pairs: number, directed: number) =>
    `${countEn(pairs, 'pair of chapters from two books', 'pairs of chapters from two books')}; ${numEn(directed)} given a direction.`,
  bases: {
    cited: { label: 'Cited', hint: 'a resolved citation in one chapter points to a verse of the other' },
    borrowed: { label: 'Borrowed', hint: 'a parallel passage whose language and spelling point to the borrower' },
    language: { label: 'Language', hint: 'the late-language profiles of the two chapters differ enough' },
    conflict: { label: 'Conflict', hint: 'a citation and a parallel passage point opposite ways' },
    none: { label: 'Undecided', hint: 'no layer decides: out of the profile’s domain, or too close' },
  } satisfies Record<EchoBasis, { label: string; hint: string }>,
  basisCount: (label: string, n: number) => `${label} ${numEn(n)}`,
  checksTitle: 'Checks fixed in advance',
  check: {
    cited: 'Language against the citations',
    spelling: 'Language against the spelling of the parallels',
    borrowed: 'Language against the borrowing estimates',
  },
  checkLine: (label: string, agree: number, n: number, p: number) =>
    `${label}: the same direction in ${numEn(agree)} of ${numEn(n)} (sign test p ${fp(p)}).`,
  underpowered: (label: string, n: number) => `${label}: ${countEn(n, 'case', 'cases')}, too few to judge.`,
  checkNote:
    'The borrowing estimates already use the same language features, so that agreement is expected; the spelling check is the independent one (only the full spelling דויד is on both sides). Every check leans on the canon order too: the accepted borrowings run from the earlier book to the later, and citations look only backwards.',
  backward: (n: number, of: number, gap: number) =>
    `${numEn(n)} of the ${countEn(of, 'language direction', 'language directions')} (profiles at least ${gap} apart) run against the canon order: the earlier book looks later. Leads, not findings — one feature can carry a score.`,
  cycles: (pairs: string[]) =>
    pairs.length === 0
      ? 'Citations and borrowing estimates never point both ways between two books.'
      : `Citations and borrowing estimates point both ways between ${pairs.join('; ')}.`,
  booksTitle: 'Book to book',
  booksLede: 'Directed pairs of chapters, from the book drawn on to the book echoing it.',
  bookPair: (a: string, b: string) => `${a} → ${b}`,
  sourcesTitle: 'Chapters drawn on most',
  sourcesLede: 'Cited or borrowed from first, then by any layer.',
  chapter: 'Chapter',
  lends: 'Drawn on',
  borrows: 'Echoes',
  explicit: 'Cited / borrowed',
  listTitle: 'Every pair',
  filters: { basis: 'Evidence', any: 'Any', backward: 'Against the canon order only', book: 'Book' },
  page: (total: number, page: number, pages: number) =>
    `${countEn(total, 'pair', 'pairs')} · page ${numEn(page)} of ${numEn(pages)}`,
  none: 'None here.',
  /** drawn on → echoing (reading direction) */
  arrow: '→',
  cited: (n: number) => countEn(n, 'citation', 'citations'),
  gap: (g: number) => `late-language profile ${gapEn(g)}`,
  gapTitle: 'The late-language score of the echo minus that of its source (of b minus a when undecided)',
  againstCanon: 'against the canon order',
  compare: 'Compare',
}

register('echo', echoEn)
