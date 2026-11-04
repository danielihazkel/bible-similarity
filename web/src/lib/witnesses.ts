// Helpers of the other witnesses page (§16.78).
import type { OpCounts } from '../api/types'
import type { WitnessKind } from '../i18n/pages/witnesses'

/** The ops a variant is (spelling left out). */
export const VARIANT_OPS = ['form', 'substitution', 'omitted', 'added', 'moved'] as const

export const parseKind = (s: string | null): WitnessKind => (s === 'scroll' ? 'scroll' : 'sp')

/** Variants per 100 words read, to one decimal. */
export function variantsPer100(c: OpCounts, read: number): string {
  if (!read) return '—'
  const n = VARIANT_OPS.reduce((a, op) => a + c[op], 0)
  return ((100 * n) / read).toFixed(1)
}

/** `/witnesses` with a unit or a witness kind. */
export function witnessUrl(p: { unit?: string; kind?: WitnessKind }): string {
  const q = new URLSearchParams()
  if (p.kind && p.kind !== 'sp') q.set('kind', p.kind)
  if (p.unit) q.set('unit', p.unit)
  const s = q.toString()
  return s ? `/witnesses?${s}` : '/witnesses'
}
