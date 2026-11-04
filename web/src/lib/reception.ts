// Rabbinic reception (DESIGN.md §16.77): a chapter's colour step, and a count's parts by corpus.

import type { Corpus, CorpusChoice } from '../i18n/pages/reception'

export const CORPORA: readonly Corpus[] = ['mishnah', 'tosefta', 'bavli', 'yerushalmi']
export const STEPS = 5 // colour steps of a cited chapter (0: not cited)
const QUANTILES = [0.2, 0.4, 0.6, 0.8] // the steps' bounds among the cited chapters' rates

export type Counts = Record<Corpus | 'total', number>

/** A choice of corpus from the URL (`?corpus=`), else all four. */
export const parseCorpus = (v: string | null): CorpusChoice => (CORPORA as readonly string[]).includes(v ?? '') ? (v as Corpus) : 'all'

/** The count a choice reads: one corpus's, or the total. */
export const countOf = (c: Counts, corpus: CorpusChoice) => (corpus === 'all' ? c.total : c[corpus])

/** The lower bounds of steps 2..STEPS: quantiles of the rates above 0 (each step about a fifth of
 * the cited chapters), so that one corpus's scale is not another's. */
export function bounds(rates: number[]): number[] {
  const cited = rates.filter((r) => r > 0).sort((a, b) => a - b)
  if (cited.length === 0) return []
  return QUANTILES.map((q) => cited[Math.min(cited.length - 1, Math.floor(q * cited.length))])
}

/** A rate's step: 0 not cited, 1..STEPS by `bounds`. */
export function step(rate: number, b: number[]): number {
  if (rate <= 0) return 0
  let s = 1
  for (const x of b) if (rate >= x) s++
  return Math.min(STEPS, s)
}

/** "Mishnah 2 · Bavli 7": a count's corpora that cite, in order. */
export function parts(c: Counts, names: Record<Corpus, string>, num: (n: number) => string): string {
  return CORPORA.filter((k) => c[k] > 0)
    .map((k) => `${names[k]} ${num(c[k])}`)
    .join(' · ')
}
