// View state lives in the URL (DESIGN.md §11): /unit/v:123?mode=fused&k=20&exclude=neighbors
import { useCallback } from 'react'
import { useSearchParams } from 'react-router'
import type { Exclude, Mode, UnitType } from '../api/types'

export const MODES: Mode[] = ['lexical', 'semantic', 'fused']
export const K_OPTIONS = [10, 20, 50] as const
export const EXCLUDES: Exclude[] = ['neighbors', 'chapter', 'book']

export const DEFAULT_MODE: Mode = 'fused'
export const DEFAULT_K = 10

export function parseMode(v: string | null): Mode {
  return MODES.includes(v as Mode) ? (v as Mode) : DEFAULT_MODE
}

export function parseK(v: string | null): number {
  const k = Number(v)
  return (K_OPTIONS as readonly number[]).includes(k) ? k : DEFAULT_K
}

/** Filters that `/similar` accepts for a unit type: neighbours / chapter are verse-only. */
export function allowedExcludes(type: UnitType): Exclude[] {
  return type === 'verse' ? EXCLUDES : ['book']
}

/**
 * `exclude` absent → the default (verses hide their ±2 neighbours, as in evaluation; larger
 * units hide nothing); `exclude=` → none. Unknown or inapplicable filters are dropped.
 */
export function parseExclude(v: string | null, type: UnitType): Exclude[] {
  if (v === null) return type === 'verse' ? ['neighbors'] : []
  const allowed = allowedExcludes(type)
  return EXCLUDES.filter((e) => allowed.includes(e) && v.split(',').includes(e))
}

/** Read and update a set of query parameters, replacing the history entry for toggles. */
export function useQueryParams() {
  const [params, setParams] = useSearchParams()
  const update = useCallback(
    (changes: Record<string, string | null>, replace = true) =>
      setParams(
        (prev) => {
          const next = new URLSearchParams(prev)
          for (const [k, v] of Object.entries(changes)) {
            if (v === null) next.delete(k)
            else next.set(k, v)
          }
          return next
        },
        { replace },
      ),
    [setParams],
  )
  return [params, update] as const
}
