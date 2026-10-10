// The site's pages as the nav lists them: the topbar menus and the jump box (Ctrl+K) read the
// same list, so a page added here is found by both.

import type { Messages } from '../i18n'

export type GroupKey = 'parallels' | 'patterns' | 'overview'
export type NavKey = Exclude<keyof Messages['nav'], GroupKey>

export interface NavItem {
  to: string
  key: NavKey
}
export interface NavGroup {
  key: GroupKey
  items: NavItem[]
}
export type NavEntry = NavItem | NavGroup

export const NAV: NavEntry[] = [
  { to: '/', key: 'browse' },
  { to: '/search', key: 'search' },
  { to: '/compare', key: 'compare' },
  {
    key: 'parallels',
    items: [
      { to: '/discoveries', key: 'discoveries' },
      { to: '/labels', key: 'labels' },
      { to: '/phrases', key: 'phrases' },
      { to: '/sequences', key: 'sequences' },
      { to: '/changes', key: 'changes' },
      { to: '/borrowing', key: 'borrowing' },
      { to: '/typescenes', key: 'typescenes' },
      { to: '/citations', key: 'citations' },
    ],
  },
  {
    key: 'patterns',
    items: [
      { to: '/structure', key: 'structure' },
      { to: '/acrostics', key: 'acrostics' },
      { to: '/divisions', key: 'divisions' },
      { to: '/ketiv', key: 'ketiv' },
      { to: '/poetry', key: 'poetry' },
      { to: '/wordplay', key: 'wordplay' },
      { to: '/names', key: 'names' },
      { to: '/domains', key: 'domains' },
    ],
  },
  {
    key: 'overview',
    items: [
      { to: '/map', key: 'map' },
      { to: '/network', key: 'network' },
      { to: '/style', key: 'style' },
      { to: '/shifts', key: 'shifts' },
      { to: '/language', key: 'language' },
      { to: '/speech', key: 'speech' },
      { to: '/eval', key: 'eval' },
    ],
  },
  { to: '/about', key: 'about' },
]

export const isGroup = (e: NavEntry): e is NavGroup => 'items' in e

/** A nav entry's label and hint (top-level links have no hint). */
export function navText(m: Messages, key: NavKey): { label: string; hint?: string } {
  const v = m.nav[key]
  return typeof v === 'string' ? { label: v } : v
}

/** Pages whose label, hint or path contains the query (label matches first, at most `max`). */
export function matchPages(m: Messages, q: string, max: number): { to: string; label: string; hint?: string }[] {
  const s = q.trim().toLowerCase()
  if (s.length < 2) return []
  const scored = NAV_PAGES.flatMap((p) => {
    const { label, hint } = navText(m, p.key)
    const l = label.toLowerCase()
    const rank = l.startsWith(s)
      ? 0
      : l.includes(s)
        ? 1
        : (hint ?? '').toLowerCase().includes(s) || p.to.slice(1).startsWith(s)
          ? 2
          : -1
    return rank < 0 ? [] : [{ rank, page: { to: p.to, label, hint } }]
  })
  return scored
    .sort((a, b) => a.rank - b.rank)
    .slice(0, max)
    .map((x) => x.page)
}

/** Every page of the nav, groups flattened, with the group it sits in. */
export const NAV_PAGES: (NavItem & { group?: GroupKey })[] = NAV.flatMap((e) =>
  isGroup(e) ? e.items.map((i) => ({ ...i, group: e.key })) : [e],
)
