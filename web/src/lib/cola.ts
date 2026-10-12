import type { VerseHalves } from '../api/types'

/** Display indexes ending a colon (every colon but the last). */
export function colonBreaks(h: VerseHalves | undefined): Set<number> | undefined {
  return h && h.n_cola > 1 ? new Set(h.cola.slice(0, -1).map(([, end]) => end)) : undefined
}

/** Display indexes ending a clause that are not colon ends (every clause but the last). */
export function clauseBreaks(h: VerseHalves | undefined): Set<number> | undefined {
  if (!h?.clauses || h.clauses.length < 2) return undefined
  const major = colonBreaks(h) ?? new Set<number>()
  return new Set(h.clauses.slice(0, -1).map(([, end]) => end).filter((e) => !major.has(e)))
}
