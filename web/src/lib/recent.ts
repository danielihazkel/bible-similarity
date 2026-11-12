// The pages the viewer pinned, and the pages and passages they opened last: per-viewer (not view
// state), so they live in localStorage (`bsim.pins`, `bsim.recent`). The top bar, the Pinned menu,
// the jump box and the All pages index read them through the two hooks, which follow every write
// (and a write from another tab).

import { useMemo, useSyncExternalStore } from 'react'
import { readLink, unitLink } from './links'
import { NAV_PAGES } from './nav'

export const PINS_KEY = 'bsim.pins'
export const RECENT_KEY = 'bsim.recent'
export const MAX_RECENT_PAGES = 8
export const MAX_RECENT_PASSAGES = 8

/** A passage opened on its unit page or in the reader, with its label in both languages. */
export interface RecentPassage {
  to: string
  en: string
  he: string
}
export interface Recent {
  pages: string[] // nav paths, the last opened first
  passages: RecentPassage[] // the last opened first, one entry per passage
}

// the pages that can be pinned or listed as recent: the nav's, without the home page (the brand)
const PINNABLE: ReadonlySet<string> = new Set(NAV_PAGES.map((p) => p.to).filter((to) => to !== '/'))
export const isNavPage = (pathname: string): boolean => PINNABLE.has(pathname)

/** The passage a path shows (`/unit/…`, `/read/…`), or nothing. */
export function passageOf(pathname: string): { view: 'unit' | 'read'; id: string } | undefined {
  const m = /^\/(unit|read)\/([^/]+)$/.exec(pathname)
  if (!m) return undefined
  try {
    return { view: m[1] as 'unit' | 'read', id: decodeURIComponent(m[2]) }
  } catch {
    return undefined // a malformed escape
  }
}

/** A passage's path in its view, as the links write it. */
export const passageLink = (view: 'unit' | 'read', id: string) => (view === 'read' ? readLink(id) : unitLink(id))

// storage, with a copy in memory for a browser that refuses it (the lists then last the visit)
const memory = new Map<string, string>()
const listeners = new Set<() => void>()

function read(key: string): string | null {
  try {
    return localStorage.getItem(key)
  } catch {
    return memory.get(key) ?? null
  }
}

function write(key: string, value: unknown) {
  const s = JSON.stringify(value)
  try {
    localStorage.setItem(key, s)
  } catch {
    memory.set(key, s)
  }
  for (const f of listeners) f()
}

function subscribe(f: () => void): () => void {
  listeners.add(f)
  window.addEventListener('storage', f)
  return () => {
    listeners.delete(f)
    window.removeEventListener('storage', f)
  }
}

function parse(raw: string | null): unknown {
  if (!raw) return undefined
  try {
    return JSON.parse(raw)
  } catch {
    return undefined
  }
}

const isText = (x: unknown): x is string => typeof x === 'string'

function parsePins(raw: string | null): string[] {
  const v = parse(raw)
  return Array.isArray(v) ? [...new Set(v.filter(isText).filter(isNavPage))] : []
}

function parseRecent(raw: string | null): Recent {
  const v = parse(raw) as { pages?: unknown; passages?: unknown } | undefined
  const pages = Array.isArray(v?.pages) ? v.pages.filter(isText).filter(isNavPage) : []
  const passages = Array.isArray(v?.passages)
    ? v.passages.filter((p): p is RecentPassage => !!p && isText(p.to) && isText(p.en) && isText(p.he) && !!passageOf(p.to))
    : []
  return { pages: pages.slice(0, MAX_RECENT_PAGES), passages: passages.slice(0, MAX_RECENT_PASSAGES) }
}

export const loadPins = (): string[] => parsePins(read(PINS_KEY))
export const loadRecent = (): Recent => parseRecent(read(RECENT_KEY))

/** Pins a nav page (at the end of the list) or takes its pin away. */
export function togglePin(to: string) {
  if (!isNavPage(to)) return
  const pins = loadPins()
  write(PINS_KEY, pins.includes(to) ? pins.filter((p) => p !== to) : [...pins, to])
}

/** A nav page was opened: first of the recent pages. */
export function visitPage(to: string) {
  if (!isNavPage(to)) return
  const r = loadRecent()
  if (r.pages[0] === to) return
  write(RECENT_KEY, { ...r, pages: [to, ...r.pages.filter((p) => p !== to)].slice(0, MAX_RECENT_PAGES) })
}

/** A passage was opened: first of the recent passages, in the view it was opened in. */
export function visitPassage(p: RecentPassage) {
  const id = passageOf(p.to)?.id
  if (id === undefined) return
  const r = loadRecent()
  const first = r.passages[0]
  if (first && first.to === p.to && first.en === p.en && first.he === p.he) return
  const others = r.passages.filter((x) => passageOf(x.to)?.id !== id)
  write(RECENT_KEY, { ...r, passages: [p, ...others].slice(0, MAX_RECENT_PASSAGES) })
}

/** The pinned pages, in the order they were pinned. */
export function usePins(): string[] {
  const raw = useSyncExternalStore(subscribe, () => read(PINS_KEY))
  return useMemo(() => parsePins(raw), [raw])
}

/** The pages and passages opened last. */
export function useRecent(): Recent {
  const raw = useSyncExternalStore(subscribe, () => read(RECENT_KEY))
  return useMemo(() => parseRecent(raw), [raw])
}
