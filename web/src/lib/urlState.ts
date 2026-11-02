// View state lives in the URL (DESIGN.md §11): /unit/v:123?mode=fused&k=20&exclude=neighbors
import { useCallback } from 'react'
import { useSearchParams } from 'react-router'
import type { Exclude, Mode, UnitType } from '../api/types'

export const MODES: Mode[] = ['lexical', 'semantic', 'fused', 'structural', 'domain', 'syntax']
/** Free-text search has no morphology or word senses, so no structural or domain mode. */
export const SEARCH_MODES: Mode[] = ['lexical', 'semantic', 'fused']
export const K_OPTIONS = [10, 20, 50] as const
/** Search ranks past the stored lists (API: up to `serve.search.max_k`). */
export const SEARCH_K_OPTIONS = [10, 20, 50, 100, 200] as const
export const EXCLUDES: Exclude[] = ['neighbors', 'chapter', 'book', 'known']

export const DEFAULT_MODE: Mode = 'fused'
export const DEFAULT_K = 10

export function parseMode(v: string | null, modes: Mode[] = MODES): Mode {
  return modes.includes(v as Mode) ? (v as Mode) : DEFAULT_MODE
}

export function parseK(v: string | null, options: readonly number[] = K_OPTIONS): number {
  const k = Number(v)
  return options.includes(k) ? k : DEFAULT_K
}

/** 1-based page from a `page` parameter (anything invalid → 1). */
export function parsePage(v: string | null): number {
  const n = Number(v)
  return Number.isInteger(n) && n > 1 ? n : 1
}

/** Filters that `/similar` accepts for a unit type: neighbours / chapter are verse-only. */
export function allowedExcludes(type: UnitType): Exclude[] {
  return type === 'verse' ? EXCLUDES : ['book', 'known']
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

/** A whole number kept in one query parameter (a selection: a cluster, a chapter, a place). Set
 * with a new history entry, so Back undoes it; `undefined` removes it. */
export function useIntParam(name: string) {
  const [params, update] = useQueryParams()
  const raw = params.get(name)
  const n = raw === null ? NaN : Number(raw)
  const value = Number.isInteger(n) ? n : undefined
  const set = useCallback((v: number | undefined) => update({ [name]: v === undefined ? null : String(v) }, false), [name, update])
  return [value, set] as const
}

/** The open `<details>` of a page in one `open` parameter (comma-separated ids), so a section
 * opened by hand stays open on Back and in a shared link: `{...openProps('help')}`. */
export function useOpenSections() {
  const [params, update] = useQueryParams()
  const open = new Set((params.get('open') ?? '').split(',').filter(Boolean))
  return (id: string) => ({
    open: open.has(id),
    onToggle: (e: { currentTarget: HTMLDetailsElement }) => {
      const now = e.currentTarget.open
      if (now === open.has(id)) return
      const next = new Set(open)
      if (now) next.add(id)
      else next.delete(id)
      update({ open: next.size ? [...next].sort().join(',') : null })
    },
  })
}
