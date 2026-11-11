// The site's pages as the nav lists them: the topbar menus and the jump box (Ctrl+K) read the
// same list, so a page added here is found by both.

import type { Messages } from '../i18n'

export type GroupKey = 'parallels' | 'patterns' | 'overview'
export type NavKey = Exclude<keyof Messages['nav'], GroupKey>
export type SectionKey = keyof Messages['navSections']

export interface NavItem {
  to: string
  key: NavKey
}
export interface NavSection {
  key: SectionKey
  items: NavItem[]
}
export interface NavGroup {
  key: GroupKey
  items: NavItem[] // every page of the group (its sections' pages, in order)
  sections?: NavSection[] // a big group's pages under headings
}

/** A group whose pages sit under headings. */
const sectioned = (key: GroupKey, sections: NavSection[]): NavGroup => ({
  key,
  sections,
  items: sections.flatMap((s) => s.items),
})
export type NavEntry = NavItem | NavGroup

export const NAV: NavEntry[] = [
  { to: '/', key: 'browse' },
  { to: '/findings', key: 'findings' },
  { to: '/search', key: 'search' },
  { to: '/compare', key: 'compare' },
  { to: '/notebook', key: 'notebook' },
  {
    key: 'parallels',
    items: [
      { to: '/discoveries', key: 'discoveries' },
      { to: '/labels', key: 'labels' },
      { to: '/phrases', key: 'phrases' },
      { to: '/sequences', key: 'sequences' },
      { to: '/synopses', key: 'synopses' },
      { to: '/laws', key: 'laws' },
      { to: '/changes', key: 'changes' },
      { to: '/borrowing', key: 'borrowing' },
      { to: '/typescenes', key: 'typescenes' },
      { to: '/citations', key: 'citations' },
      { to: '/source', key: 'sourceFind' },
    ],
  },
  sectioned('patterns', [
    {
      key: 'poetryForm',
      items: [
        { to: '/query', key: 'query' },
        { to: '/workbench', key: 'workbench' },
        { to: '/poetry', key: 'poetry' },
        { to: '/structure', key: 'structure' },
        { to: '/acrostics', key: 'acrostics' },
        { to: '/refrains', key: 'refrains' },
        { to: '/forms', key: 'forms' },
        { to: '/psalms', key: 'psalms' },
        { to: '/prophetic', key: 'prophetic' },
        { to: '/wordplay', key: 'wordplay' },
        { to: '/brackets', key: 'brackets' },
        { to: '/divisions', key: 'divisions' },
      ],
    },
    {
      key: 'wordsNames',
      items: [
        { to: '/roots', key: 'roots' },
        { to: '/binomials', key: 'binomials' },
        { to: '/vocabulary', key: 'vocabulary' },
        { to: '/domains', key: 'domains' },
        { to: '/names', key: 'names' },
        { to: '/divine', key: 'divine' },
        { to: '/etiologies', key: 'etiologies' },
        { to: '/ketiv', key: 'ketiv' },
        { to: '/witnesses', key: 'witnesses' },
      ],
    },
    {
      key: 'lettersNumbers',
      items: [
        { to: '/gematria', key: 'gematria' },
        { to: '/gematria-links', key: 'gematriaLinks' },
        { to: '/els', key: 'els' },
        { to: '/ciphers', key: 'ciphers' },
        { to: '/masorah', key: 'masorah' },
        { to: '/sums', key: 'sums' },
      ],
    },
    {
      key: 'narrative',
      items: [
        { to: '/retold', key: 'retold' },
        { to: '/mainline', key: 'mainline' },
        { to: '/chronology', key: 'chronology' },
        { to: '/frameworks', key: 'frameworks' },
        { to: '/haftarot', key: 'haftarot' },
        { to: '/reception', key: 'reception' },
      ],
    },
  ]),
  {
    key: 'overview',
    items: [
      { to: '/map', key: 'map' },
      { to: '/places', key: 'places' },
      { to: '/place-lists', key: 'placeLists' },
      { to: '/place-arc', key: 'placeArc' },
      { to: '/place-links', key: 'placeLinks' },
      { to: '/genealogy', key: 'genealogy' },
      { to: '/network', key: 'network' },
      { to: '/style', key: 'style' },
      { to: '/shifts', key: 'shifts' },
      { to: '/language', key: 'language' },
      { to: '/pentateuch', key: 'pentateuch' },
      { to: '/speech', key: 'speech' },
      { to: '/eval', key: 'eval' },
      { to: '/week', key: 'week' },
      { to: '/tours', key: 'tours' },
      { to: '/glossary', key: 'glossary' },
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

/** Your labels and notebook: left out where the server keeps nothing personal (a public deploy,
 * `useServer().personal`). */
export const PERSONAL_PAGES: ReadonlySet<string> = new Set(['/labels', '/notebook'])

/** The nav as this server offers it: without the personal pages when `personal` is off. */
export function navFor(personal: boolean): NavEntry[] {
  if (personal) return NAV
  const keep = (it: NavItem) => !PERSONAL_PAGES.has(it.to)
  return NAV.flatMap((e): NavEntry[] => {
    if (!isGroup(e)) return keep(e) ? [e] : []
    const sections = e.sections?.map((s) => ({ ...s, items: s.items.filter(keep) }))
    return [{ ...e, items: e.items.filter(keep), ...(sections ? { sections } : {}) }]
  })
}

/** Pages whose label, hint or path contains the query (label matches first, at most `max`). */
export function matchPages(
  m: Messages,
  q: string,
  max: number,
  personal = true,
): { to: string; label: string; hint?: string }[] {
  const s = q.trim().toLowerCase()
  if (s.length < 2) return []
  const scored = NAV_PAGES.filter((p) => personal || !PERSONAL_PAGES.has(p.to)).flatMap((p) => {
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
